---
name: job-hunt
description: Runs the whole daily job hunt in one go — searches LinkedIn for new postings, scores them, writes the run's jobs.json and shortlist, then tailors a resume for every shortlisted job. Use when the user runs /job-hunt, asks to search for jobs, or refreshes their shortlist.
---

# /job-hunt

The **whole daily run**: the search phase (steps 1–7), then the tailor phase (step 8)
for **every** shortlisted job, back to back. No separate `/job-hunt-tailor` call is needed.
`/job-hunt-tailor` still exists for on-demand work — one named job, `--pending`, or an
earlier run. See [ADR 0009](../../../docs/adr/0009-job-hunt-tailors-in-one-go.md).

The search phase is slow because LinkedIn tool calls are serialized globally by
`mcp-server-linkedin` (an `asyncio.Lock` plus a cross-process profile lease), so this
phase is irreducibly slow — roughly one call every 15 seconds — and no amount of
parallelism helps. Rather than making it faster, it was moved off the user's clock:
this skill fires unattended from a LaunchAgent when the machine wakes, so its ~14
minutes cost nobody anything — and now the tailoring happens in that same run. See `.scratch/job-hunt-speedup/map.md`.

Read `.scratch/job-hunt/spec.md` if you need the full rationale behind a step below.

## Steps

1. **Determine the run date and check the guard.** Use today's date, `YYYY-MM-DD`.
   Also run `command -v pdflatex` now and remember the result — step 8 needs it, and a
   missing binary should be known before the 14-minute search, not after.
   ```
   uv run python -m pipeline.cli run-status runs/<date>
   ```
   - `complete` — today's search already ran. **Don't re-search.** This is the
     once-per-day guard, and it is the normal outcome when the LaunchAgent has already
     fired and the user then invokes `/job-hunt` by hand. Check
     `uv run python -m pipeline.cli read-tailored runs/<date>`: if it returns `{}`, the
     search finished but tailoring never did — skip to step 8. Otherwise stop and say
     today's run is done (point at `/job-hunt-tailor` for more).
   - `in_flight` — another search is running right now. Stop; don't start a second one
     against the same LinkedIn browser profile.
   - `missing` — proceed. (A crashed earlier run reports `missing` once its `.tmp` is
     over 45 minutes old, so a dead search never wedges the pipeline.)

2. **Create the run folders.** `runs/<date>/` and `runs/<date>/resumes/`.

3. **Get the shortlist.** Dispatch the `job-finder` subagent (via the Agent tool) with no
   special input beyond its own instructions — it reads `config/search.yaml`,
   `state/seen-jobs.json`, and `resume/main.tex` itself. It returns a JSON list of
   shortlisted jobs (schema in `.claude/agents/job-finder.md`).

   If it reports `resume/main.tex` is missing, stop and tell the user — the pipeline
   cannot score relevance without it.

   An empty shortlist is a valid outcome, not an error. Continue with an empty list;
   the steps below all handle it.

4. **Write `jobs.json`.** This is the handoff artifact the tailor phase reads, and it
   carries each job's full `description` so tailoring never needs a second LinkedIn
   call:
   ```
   uv run python -m pipeline.cli write-jobs runs/<date> --run-date <date> --jobs '<json shortlist>'
   ```
   The command writes a `.tmp` and atomically renames it, so `jobs.json` only ever
   exists complete. That rename is what marks the run done — do not write this file any
   other way.

5. **Write `shortlist.md`** with no resume paths yet:
   ```
   uv run python -m pipeline.cli render-shortlist --jobs '<json shortlist>' > runs/<date>/shortlist.md
   ```
   Every job's Resume column renders as `—` for now. Step 8 re-renders it with resume
   paths; writing it here first means a failed tailor phase still leaves a usable
   shortlist.

6. **Push every shortlisted job to the Notion Job Tracker.** Write-only, upserted by
   `job_id`, and it never blocks the rest of the run — see
   [ADR 0001](../../../docs/adr/0001-notion-job-tracker.md). This lives in the search
   phase, not the tailor phase, because the Job Tracker row is job data only and needs
   nothing tailoring produces (see [ADR 0007](../../../docs/adr/0007-disable-notion-pdf-attachment.md)).
   - Load tracker state: `uv run python -m pipeline.cli load-notion-tracker state/notion-tracker.json`.
   - If it returns `{}`, no database exists yet — create one:
     - Get title + schema: `uv run python -m pipeline.cli notion-database-schema`.
     - Create it under the "Upskill 2k26" page via `mcp__claude_ai_Notion__notion-create-database`.
       Its result includes a `<data-source url="collection://...">` — that id, not the
       database page id alone, is what you query and create pages against.
     - Persist both: `uv run python -m pipeline.cli save-notion-tracker state/notion-tracker.json --database-id '<id>' --data-source-id '<collection://... id>'`.
   - For every shortlisted job:
     - Query `mcp__claude_ai_Notion__notion-query-data-sources` (SQL mode, against the
       saved `data_source_id`) for a row whose `"Job ID"` equals this job's `job_id`.
     - Shape properties: `uv run python -m pipeline.cli notion-properties --job '<json job>' --today <date> [--is-new if no page was found]`.
     - Create (`notion-create-pages` with `parent: {data_source_id: ...}`) or update
       (`notion-update-page`) with those properties.
     - On failure, retry once, then record a Notion sync failure and continue. One job's
       Notion failure never stops the rest, and never blocks step 7.

   `Notes` no longer carries a tailoring error — this phase runs before tailoring
   exists. `shortlist.md` still reports every failure.

7. **Update the seen-jobs log** with every shortlisted job:
   ```
   uv run python -m pipeline.cli append-seen state/seen-jobs.json --jobs '<json list of {job_id,title,company}>'
   ```
   **`seen` means *scored*, not *handled*.** A job recorded here may never be tailored —
   the log exists only to stop the same posting being re-fetched and re-scored tomorrow.
   See the `Seen Job` entry in `CONTEXT.md`.

   **Skip this step entirely on a dry run.** `/job-hunt-dry-run` reuses this skill's
   steps, and its seen-log exclusion now lives *here* rather than in a later
   orchestration step.

8. **Tailor every shortlisted job.** Follow [`/job-hunt-tailor`](../job-hunt-tailor/SKILL.md)'s
   default mode against `runs/<date>/` — its steps 4–10 — with one change to step 4: take
   **all** untailored jobs from `jobs.json`, not `select-eager --count 8`. Then one
   concurrent `resume-tailor` wave (up to `max_shortlist` agents), the retry wave, the deterministic ATS check, the
   keyword-fix wave, `record-tailored`, and the `shortlist.md` re-render. Skip its
   step 3 guard: `jobs.json` was just written complete in step 4.
   - If `pdflatex` was missing in step 1, skip this step and say so plainly —
     installing it (`brew install --cask basictex`) is one-time setup. The search
     results are still saved; `/job-hunt-tailor` picks them up once it's installed.
   - An empty shortlist means nothing to tailor; skip.

9. **Report back**: how many jobs were found and shortlisted (and how many of those were
   `min_shortlist` backfill vs. organically above `relevance_threshold`), how many Notion
   syncs failed, how many were tailored / failed / hit `pdf_error`, how many stay
   pending, and the path to `runs/<date>/shortlist.md`. Finish with the age-out warning
   from `uv run python -m pipeline.cli pending runs` if there is one.

## Notes

- Steps 3 and 8 are the only LLM-judgment steps here. Everything else routes through the tested
  `pipeline` module via `uv run python -m pipeline.cli ...`. If you find yourself
  hand-writing dedup, shortlist selection, or markdown rendering, stop — that logic
  already exists in `pipeline/`.
- Step 6's Notion calls involve tool use but no judgment: data is shaped by
  `notion-properties` and the step only decides create-vs-update. It stays outside
  `pipeline/` because it needs the connector's already-authorized access (ADR 0001).
- A missing `pdflatex` never blocks the search. Step 1 checks it early so step 8 can
  skip cleanly instead of every tailor agent failing on its own.
- This skill is invoked by the LaunchAgent on wake, and manually. Behaviour is identical
  either way — step 1's guard is what makes a manual invocation after an automatic one
  safe.
