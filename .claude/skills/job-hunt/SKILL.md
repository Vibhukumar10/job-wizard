---
name: job-hunt
description: Runs the whole daily job hunt in one call — searches LinkedIn for new postings, scores them, pushes them to the Notion Job Tracker, and tailors a resume for every shortlisted job. Use when the user runs /job-hunt, asks to search for jobs, or asks for today's resumes.
---

# /job-hunt

**One call does the whole run**: search, score, record, and tailor a resume for
**every** shortlisted job. There is no separate step the user has to remember.

This matches the original spec — story 9, "a tailored resume generated for every
shortlisted job", and story 16, "bounded concurrency (5 at a time)". An earlier
revision split the run into an unattended search and an attended tailor phase, and
tailored only the top 8; both are reversed. See
[ADR 0009](../../../docs/adr/0009-single-phase-run.md).

`/job-hunt-tailor` still exists, but only as a **recovery tool** — retrying jobs this
run failed on, or reaching a job from an earlier run. A normal day never needs it.

The search half is irreducibly slow: LinkedIn tool calls are serialized globally by
`mcp-server-linkedin` (an `asyncio.Lock` plus a cross-process profile lease), so it
runs at roughly one call every 15 seconds — about 14 minutes — and no amount of
parallelism helps. The tailor half touches neither LinkedIn nor Notion, so it is not
subject to that lock and runs concurrently.

Read `.scratch/job-hunt/spec.md` if you need the full rationale behind a step below.

## Steps

1. **Determine the run date and check the guard.** Use today's date, `YYYY-MM-DD`.
   ```
   uv run python -m pipeline.cli run-status runs/<date>
   ```
   - `missing` — no search yet today. Run every step below. (A crashed earlier run
     reports `missing` once its `.tmp` is over 45 minutes old, so a dead search never
     wedges the pipeline.)
   - `in_flight` — another run is searching right now. Stop; don't start a second one
     against the same LinkedIn browser profile.
   - `complete` — today's search already ran. **Do not re-search.** Instead check
     whether its tailoring finished:
     ```
     uv run python -m pipeline.cli pending runs --today <date>
     ```
     - Jobs still pending for today's run → **skip to step 9** and tailor them. This is
       the normal path when a previous invocation searched but died during tailoring, and
       it is what makes re-running `/job-hunt` safe and resumable.
     - Nothing pending → the run is genuinely finished. Say so and stop.

2. **Verify the PDF toolchain.** Run `command -v pdflatex`. If missing, stop and tell
   the user plainly — installing it (`brew install --cask basictex`) is one-time
   environment setup, not something a run can work around. `pdflatex` specifically, not
   `xelatex`/`tectonic`: `resume.cls` depends on the pdfTeX-only `glyphtounicode`
   mechanism for ATS-correct text extraction.

   Check it **here, before the 14-minute search**, not later. A missing binary
   discovered after the search has run costs the user the whole search over again.

3. **Create the run folders.** `runs/<date>/` and `runs/<date>/resumes/`.

4. **Get the shortlist.** Dispatch the `job-finder` subagent (via the Agent tool) with no
   special input beyond its own instructions — it reads `config/search.yaml`,
   `state/seen-jobs.json`, and `resume/main.tex` itself. It returns a JSON list of
   shortlisted jobs (schema in `.claude/agents/job-finder.md`).

   If it reports `resume/main.tex` is missing, stop and tell the user — the pipeline
   cannot score relevance without it.

   An empty shortlist is a valid outcome, not an error. Continue with an empty list;
   the steps below all handle it, and steps 9-13 simply do nothing.

5. **Write `jobs.json`.** It carries each job's full `description`, so tailoring never
   needs a second LinkedIn call:
   ```
   uv run python -m pipeline.cli write-jobs runs/<date> --run-date <date> --jobs '<json shortlist>'
   ```
   The command writes a `.tmp` and atomically renames it, so `jobs.json` only ever
   exists complete. That rename is what marks the search done — do not write this file
   any other way.

6. **Write an interim `shortlist.md`** with no resume paths yet:
   ```
   uv run python -m pipeline.cli render-shortlist --jobs '<json shortlist>' > runs/<date>/shortlist.md
   ```
   Every Resume column renders as `—`. This is deliberately written *before* tailoring:
   if tailoring later dies, the user still has a readable shortlist of the day's jobs
   rather than nothing. Step 14 overwrites it with resume paths filled in.

7. **Push every shortlisted job to the Notion Job Tracker.** Write-only, upserted by
   `job_id`, and it never blocks the rest of the run — see
   [ADR 0001](../../../docs/adr/0001-notion-job-tracker.md). The Job Tracker row is job
   data only and needs nothing tailoring produces (see
   [ADR 0007](../../../docs/adr/0007-disable-notion-pdf-attachment.md)), so it runs here,
   before tailoring, and is never held up by it.
   - Load tracker state: `uv run python -m pipeline.cli load-notion-tracker state/notion-tracker.json`.
   - If it returns `{}`, no database exists yet — create one:
     - Get title + schema: `uv run python -m pipeline.cli notion-database-schema`.
     - Create it under the "Upskill 2k26" page via `mcp__claude_ai_Notion__notion-create-database`.
       Its result includes a `<data-source url="collection://...">` — that id, not the
       database page id alone, is what you query and create pages against.
     - Persist both: `uv run python -m pipeline.cli save-notion-tracker state/notion-tracker.json --database-id '<id>' --data-source-id '<collection://... id>'`.
   - Query `mcp__claude_ai_Notion__notion-query-data-sources` (SQL mode, against the
     saved `data_source_id`) **once** for every shortlisted `job_id` — a single
     `WHERE "Job ID" IN (...)`, not one query per job. The result tells you which rows
     already exist.
   - Shape properties per job: `uv run python -m pipeline.cli notion-properties --job '<json job>' --today <date> [--is-new if no page was found]`.
   - Create the new ones in **one batched** `notion-create-pages` call
     (`parent: {data_source_id: ...}`, up to 100 pages); update existing ones
     individually with `notion-update-page`.
   - On failure, retry once, then record a Notion sync failure and continue. One job's
     Notion failure never stops the rest, and never blocks step 8 or the tailoring.

   `Notes` carries no tailoring error — the row is written before tailoring runs.
   `shortlist.md` still reports every failure.

8. **Update the seen-jobs log** with every shortlisted job:
   ```
   uv run python -m pipeline.cli append-seen state/seen-jobs.json --jobs '<json list of {job_id,title,company}>'
   ```
   **`seen` means *scored*, not *tailored*.** The log exists only to stop the same
   posting being re-fetched and re-scored tomorrow. See the `Seen Job` entry in
   `CONTEXT.md`.

   **Skip this step entirely on a dry run.** `/job-hunt-dry-run` reuses this skill's
   steps, and its seen-log exclusion lives here.

9. **Tailor every shortlisted job, in concurrency-bounded waves of 5.**
   ```
   uv run python -m pipeline.cli read-jobs runs/<date>
   uv run python -m pipeline.cli read-tailored runs/<date>
   uv run python -m pipeline.cli batch --size 5 --jobs '<json of untailored jobs>'
   ```
   Drop anything already in `tailored.json` first — that is what makes a resumed run
   (step 1's `complete` path) pick up exactly where it left off instead of re-burning
   agents on finished work.

   Dispatch one `resume-tailor` agent per job, **one wave at a time**: all 5 jobs in a
   batch go out concurrently in a single message, and the next batch starts only once
   that wave returns. Five is the spec's number (story 16) and it matters more now that
   a run tailors everything — a day can shortlist up to `max_shortlist: 50`, and
   dispatching 50 agents at once makes failures untraceable and risks rate limits.

   Pass each agent its job's **`job_id`**, title, company, location, full description
   (from `jobs.json`), and `runs/<date>/resumes/`. The `job_id` is required — the output
   filename is `<company>-<job_id>.tex`.

   Each agent returns `resume_path`, `pdf_path`, and the `keywords` it inserted. It
   compiles and page-validates its own output — the PDF it produces is the final
   artifact and is **not** recompiled downstream.

10. **Retry wave.** Any job whose agent failed gets exactly one retry, dispatched
    **after** all waves complete — never rejoined into a running wave. A second failure
    is recorded as a failure and the run continues.

11. **ATS check — deterministic, outside any agent.** For each successfully tailored job:
    ```
    uv run python -m pipeline.cli check-resume-pdf --pdf <pdf_path> --keywords '<json keywords>'
    ```
    This is the independent gate: the agent that inserted the keywords does not get to
    grade whether they survived. It returns `pages` and `missing_keywords`, so it doubles
    as a free page-count backstop. See
    [ADR 0008](../../../docs/adr/0008-merge-resume-packager.md).

12. **Keyword-fix wave.** For any job with `missing_keywords`, dispatch `resume-tailor`
    once more in its narrow keyword-restore mode, passing the existing `.tex` path and
    only the missing keywords. Re-run step 11's check on the result. Still failing after
    that one attempt is a `pdf_error` — the job keeps its `.tex` as the fallback
    artifact; it is not a failed job.

13. **Record outcomes.** For each job:
    ```
    uv run python -m pipeline.cli record-tailored runs/<date> <job_id> --outcome '<json>'
    ```
    with `tex_path`, `pdf_path` (omit on `pdf_error`), `keywords`, and `error` if any.
    `tailored.json` is the tailoring half's file — never write `jobs.json` here.

    Record each job as it resolves, not in one lump at the end. A run killed midway
    then leaves an accurate `tailored.json`, which is exactly what step 1's resume path
    reads.

14. **Re-render `shortlist.md`** for the whole run, replacing step 6's interim copy:
    ```
    uv run python -m pipeline.cli render-shortlist --jobs '<json>' --failures '<json>' --notion-failures '<json>' > runs/<date>/shortlist.md
    ```
    Each job's `resume_path` is its `pdf_path` when present, falling back to the `.tex`
    on `pdf_error`. Include the `backfilled` flag from `jobs.json` so a `min_shortlist`
    backfill stays visibly marked.

15. **Report**: how many jobs were found and shortlisted (and how many of those were
    `min_shortlist` backfill vs. organically above `relevance_threshold`), how many
    resumes were tailored, how many failed, how many hit `pdf_error`, how many Notion
    syncs failed, and the path to `runs/<date>/shortlist.md`.

    If anything failed, name `/job-hunt-tailor <job_id>` as the way to retry just that
    job — don't suggest re-running `/job-hunt`.

## Notes

- Step 4 is the only LLM-judgment step in the search half; step 9 is the only one in the
  tailor half. Everything else routes through the tested `pipeline` module via
  `uv run python -m pipeline.cli ...`. If you find yourself hand-writing dedup, shortlist
  selection, batching, or markdown rendering, stop — that logic already exists in
  `pipeline/`.
- Step 7's Notion calls involve tool use but no judgment: data is shaped by
  `notion-properties` and the step only decides create-vs-update. It stays outside
  `pipeline/` because it needs the connector's already-authorized access (ADR 0001).
- Retry budgets are bounded and distinct: one fix-and-recompile inside the agent (page
  or compile), one re-dispatch of a failed agent, one keyword-restore pass. No step gets
  a third attempt.
- **The order of steps 7-8 before 9 is deliberate.** Notion and the seen log are cheap
  and must not be hostage to a long tailoring run — if tailoring dies, the day's jobs
  are still recorded and still reachable.
- This skill is invoked by the LaunchAgent on wake, and manually. Behaviour is identical
  either way — step 1's guard is what makes a manual invocation after an automatic one
  safe, and now also lets it finish an interrupted run rather than refusing outright.
