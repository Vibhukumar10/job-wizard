---
name: job-hunt-dry-run
description: Runs a fast, minimal end-to-end pass of the job-hunt pipeline against a small capped pool of real LinkedIn postings, to validate the pipeline works without a full daily run's time/token cost. Use when the user runs /job-hunt-dry-run, or wants to sanity-check the pipeline (search, scoring, tailoring, PDF packaging, Notion push) without running it for real.
---

# /job-hunt-dry-run

A fast, minimal pass through the same pipeline `/job-hunt` runs (see
[`.claude/skills/job-hunt/SKILL.md`](../job-hunt/SKILL.md)) — sized for
validating the pipeline end-to-end, not for a real day's job search. It uses
real LinkedIn data and pushes to the real Notion Job Tracker, just against a
much smaller pool of jobs.

Follow `/job-hunt`'s steps 1–9 exactly, with these differences:

- **Step 2 (run date/output folder):** create `runs/<date>-dryrun/` and
  `runs/<date>-dryrun/resumes/` instead of `runs/<date>/`. Use this path
  everywhere the rest of `/job-hunt`'s steps would use `runs/<date>/` — this
  keeps dry-run output fully isolated from any real run happening the same
  day, so neither can overwrite the other's `shortlist.md` or resumes.
- **Step 3 (get the shortlist):** dispatch `job-finder` with a raw-result cap
  of **15** (its documented dry-run input — see
  [`.claude/agents/job-finder.md`](../../agents/job-finder.md)) instead of no
  special input. This limits job-finder's own search step to the first
  profile or two in `config/search.yaml`, at `max_pages: 1`, stopping once
  ~15 raw postings have been gathered — instead of querying every configured
  profile. Everything downstream of the search (dedup, blacklist filtering,
  stage-1/stage-2 scoring, shortlist selection) proceeds exactly as
  `/job-hunt` describes, just against a much smaller candidate pool.
- **Step 6 (Notion push):** unchanged — push for real, exactly as `/job-hunt`
  does. Dry-run jobs land in the real Job Tracker like any other run's.
- **Step 8 (update seen-jobs log):** skip entirely. Dry-run jobs are never
  appended to `state/seen-jobs.json`, so the same small pool of jobs stays
  available to re-test against, and a job seen only during a dry run is
  never suppressed from surfacing on a real `/job-hunt` run later.
- **Step 9 (report):** state plainly that this was a dry run, and that the
  counts reflect a capped 15-job search pool, not a real day's coverage.

## Notes

- This skill exists purely to validate the pipeline quickly and cheaply — it
  is not a substitute for `/job-hunt`'s daily coverage, and its numbers
  shouldn't be read as a real day's job-market signal.
- With only ~15 raw postings feeding stage-1/stage-2 filtering, falling
  short of `config/search.yaml`'s `min_shortlist` is expected, not a bug —
  `select-shortlist` already degrades gracefully when too few candidates
  clear the bar (see
  [ADR 0004](../../../docs/adr/0004-min-shortlist-backfill.md)). Don't
  interpret a small or backfill-short shortlist here as a pipeline failure.
- `job-finder`, `resume-tailor`, and `resume-packager` are shared, unchanged,
  with `/job-hunt` — if you find yourself changing scoring, tailoring, or
  packaging behavior specifically for dry-run, stop. Only the search-scope
  cap, output path, seen-jobs skip, and reporting differ from a real run.
