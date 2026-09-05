"""Files the search phase and the tailor phase use to talk to each other.

The two phases are decoupled: `/job-hunt` searches and scores unattended, and
`/job-hunt-tailor` produces resumes later, when the user is actually there. They
communicate through two files per run, each with exactly one writer:

- ``jobs.json``     — written by the search phase, never rewritten. Every
                      shortlisted job, including the full description the tailor
                      phase needs.
- ``tailored.json`` — written by the tailor phase. One entry per job it handled.

Because neither phase writes the other's file, running the tailor phase twice —
or running two of them at once — cannot corrupt the search phase's output.

See `.scratch/job-hunt-speedup/issues/03-two-phase-handoff-contract.md`.
"""

import json
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

JOBS_FILENAME = "jobs.json"
TAILORED_FILENAME = "tailored.json"

#: A jobs.json.tmp older than this is a crashed search run, not one still going.
#: Without it a search that died mid-write would wedge the tailor phase forever.
STALE_TMP_AFTER_SECONDS = 45 * 60

#: How far back a bare job_id is searched for, and how long a shortlisted job
#: stays tailorable. Deliberately one number rather than two — see
#: `.scratch/job-hunt-speedup/issues/04-seen-semantics-and-retention.md`.
RETENTION_DAYS = 7


class JobsNotReadyError(Exception):
    """Raised when the tailor phase is asked to work from an unusable jobs.json."""


class AmbiguousJobQueryError(Exception):
    """Raised when a job query matches more than one job in a run."""


def jobs_path(run_dir: Path | str) -> Path:
    return Path(run_dir) / JOBS_FILENAME


def tailored_path(run_dir: Path | str) -> Path:
    return Path(run_dir) / TAILORED_FILENAME


def write_jobs(run_dir: Path | str, jobs: list[dict[str, Any]], *, run_date: str) -> Path:
    """Write jobs.json atomically: full content to a .tmp, then rename.

    The rename is what publishes the file, so jobs.json only ever exists in a
    complete state. That single fact does triple duty — it's the completion
    signal, the once-per-day guard, and the thing `run_status` reads.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    target = jobs_path(run_dir)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"run_date": run_date, "jobs": jobs}, indent=2))
    tmp.replace(target)
    return target


def read_jobs(run_dir: Path | str) -> list[dict[str, Any]]:
    """Read a completed run's shortlisted jobs, or raise if it isn't usable."""
    status = run_status(run_dir)
    if status != "complete":
        raise JobsNotReadyError(status)
    return json.loads(jobs_path(run_dir).read_text())["jobs"]


def run_status(run_dir: Path | str, *, now: float | None = None) -> str:
    """Classify a run directory as complete / in_flight / missing.

    A lingering .tmp means a search is still running — unless it's older than
    STALE_TMP_AFTER_SECONDS, in which case that search died and the run counts
    as never having happened, so the next trigger is free to start a fresh one.
    """
    run_dir = Path(run_dir)
    if jobs_path(run_dir).exists():
        return "complete"

    tmp = jobs_path(run_dir).with_suffix(".json.tmp")
    if tmp.exists():
        age = (now if now is not None else time.time()) - tmp.stat().st_mtime
        return "missing" if age > STALE_TMP_AFTER_SECONDS else "in_flight"

    return "missing"


def read_tailored(run_dir: Path | str) -> dict[str, Any]:
    """Read this run's tailoring outcomes, keyed by job_id. Empty if none yet."""
    path = tailored_path(run_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def record_tailored(run_dir: Path | str, job_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    """Merge one job's outcome into tailored.json and persist it."""
    outcomes = read_tailored(run_dir)
    outcomes[job_id] = outcome
    tailored_path(run_dir).write_text(json.dumps(outcomes, indent=2))
    return outcomes


def select_eager(jobs: list[dict[str, Any]], eager_count: int) -> list[dict[str, Any]]:
    """The top N jobs by score — the ones tailored without being asked for.

    Everything below the cut stays in jobs.json and reachable on demand, so this
    trims tailoring work, never the shortlist itself.
    """
    return sorted(jobs, key=lambda job: job["score"], reverse=True)[:eager_count]


def resolve_job(jobs: list[dict[str, Any]], query: str) -> dict[str, Any]:
    """Find one job by job_id, falling back to a company/title fragment.

    job_id is the contract — it's already the dedup key and a Job Tracker column.
    The fragment match exists only because a raw id like "4444888908" is unusable
    by hand. An ambiguous fragment raises rather than picking one.
    """
    for job in jobs:
        if job["job_id"] == query:
            return job

    needle = query.casefold()
    matches = [
        job
        for job in jobs
        if needle in job["company"].casefold() or needle in job["title"].casefold()
    ]
    if not matches:
        raise KeyError(query)
    if len(matches) > 1:
        labels = ", ".join(f"{job['company']} — {job['title']}" for job in matches)
        raise AmbiguousJobQueryError(f"{query!r} matches {len(matches)} jobs: {labels}")
    return matches[0]


def pending_jobs(
    runs_root: Path | str,
    *,
    today: str | None = None,
    retention_days: int = RETENTION_DAYS,
) -> list[dict[str, Any]]:
    """Every shortlisted job inside the window that has no tailored resume yet.

    Derived entirely from jobs.json vs tailored.json across recent run folders —
    there is no third file tracking pending work, so nothing can fall out of sync
    with reality. Dry-run folders are skipped; they aren't real days' work.
    """
    runs_root = Path(runs_root)
    if not runs_root.exists():
        return []

    today_date = date.fromisoformat(today) if today else date.today()
    oldest = today_date - timedelta(days=retention_days - 1)

    pending: list[dict[str, Any]] = []
    for run_dir in sorted(runs_root.iterdir(), reverse=True):
        if not run_dir.is_dir() or run_dir.name.endswith("-dryrun"):
            continue
        try:
            run_date = date.fromisoformat(run_dir.name)
        except ValueError:
            continue
        if not (oldest <= run_date <= today_date):
            continue
        if run_status(run_dir) != "complete":
            continue

        done = read_tailored(run_dir)
        for job in read_jobs(run_dir):
            if job["job_id"] in done:
                continue
            pending.append(
                {
                    **job,
                    "run_date": run_dir.name,
                    "days_left": (run_date - oldest).days + 1,
                }
            )
    return pending


def age_out_warning(pending: list[dict[str, Any]], *, within_days: int = 2) -> str | None:
    """A one-line nudge about pending jobs about to fall out of the window.

    Ticket 04 accepted that an aged-out job is genuinely lost rather than
    resurfacing — this makes that loss visible before it happens instead of
    silently after.
    """
    expiring = [job for job in pending if job["days_left"] <= within_days]
    if not expiring:
        return None
    return (
        f"{len(expiring)} pending job(s) drop out of reach within {within_days} day(s): "
        + ", ".join(f"{job['company']} — {job['title']}" for job in expiring)
    )
