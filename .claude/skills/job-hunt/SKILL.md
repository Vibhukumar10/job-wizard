---
name: job-hunt
description: Runs the full daily job-hunt pipeline — searches LinkedIn for new postings, scores them for relevance, tailors a resume per shortlisted job, and writes a dated run folder. Use when the user runs /job-hunt, or asks to search for jobs / refresh their shortlist / tailor resumes for new postings.
---

# /job-hunt

Ties together the job-finder and resume-tailor subagents into one dated run. This is the orchestration layer described in `.scratch/job-hunt/spec.md` — read that file first if it's present and you need the full rationale behind a step below.

## Steps

1. **Verify the PDF toolchain is available.** Run `command -v pdflatex`. If it's not found, stop and tell the user clearly — installing it (`brew install --cask basictex`, a small pdfTeX distribution) is a one-time environment setup step, not something this run can work around. `pdflatex` specifically (not `xelatex`/`tectonic`) is required — `resume.cls` depends on the pdfTeX-only `glyphtounicode` mechanism for ATS-correct text extraction. This check happens once, up front, rather than letting every job independently discover the same missing binary.

2. **Determine the run date.** Use today's date, `YYYY-MM-DD`. Create `runs/<date>/` and `runs/<date>/resumes/` if they don't exist.

3. **Get the shortlist.** Dispatch the `job-finder` subagent (via the Agent tool) with no special input beyond its own instructions — it reads `config/search.yaml`, `state/seen-jobs.json`, and `resume/main.tex` itself. It returns a JSON list of shortlisted jobs (see `.claude/agents/job-finder.md` for the schema).

   If `job-finder` reports that `resume/main.tex` is missing, stop and tell the user — the pipeline cannot proceed without it.

   If the shortlist is empty, skip to step 6 with an empty jobs list (still write a `shortlist.md` — an empty day is a valid outcome, not an error).

4. **Tailor a resume, then compile+validate its PDF, per shortlisted job.**
   - Chunk the shortlist into concurrency-bounded batches:
     ```
     uv run python -m pipeline.cli batch --size 5 --jobs '<json shortlist>'
     ```
   - For each batch, and for each job in it **concurrently** (multiple Agent tool calls in the same turn): dispatch `resume-tailor` (passing that job's title/company/location/description and `runs/<date>/resumes/`), and — only if it succeeds — immediately chain a `resume-packager` dispatch for the same job (passing the `resume_path` and `keywords` it returned), before moving on to the next job. Wait for the whole batch (both subagents, every job) to finish before starting the next batch.
   - If `resume-tailor` fails, retry it once. If the retry also fails, record it as a failure (`title`, `company`, `error`) — `resume-packager` is never dispatched for that job.
   - If `resume-packager` reports a `pdf_error`, that does *not* count as a tailoring failure — the job still has a working `.tex`. Record the `pdf_error` alongside the otherwise-successful tailor rather than treating the job as failed.

5. **Track successes and failures** as you go: a list of successfully tailored jobs (job fields, the `.tex` path, the `pdf_path` if `resume-packager` succeeded, and `pdf_error` if it didn't) and a list of failures (job fields + error, from `resume-tailor` failing twice).

   For each success, compute `resume_path` — the path to surface downstream (`shortlist.md`, Notion) — as the `pdf_path` when present, falling back to the `.tex` path on `pdf_error`.

6. **Push every shortlisted job to the Notion Job Tracker.** Write-only, upserted by `job_id`, and never blocks the rest of the run — see [ADR 0001](../../../docs/adr/0001-notion-job-tracker.md) for why.
   - Load tracker state: `uv run python -m pipeline.cli load-notion-tracker state/notion-tracker.json`.
   - If it returns `{}`, no database exists yet — create one:
     - Get the title + property schema: `uv run python -m pipeline.cli notion-database-schema`.
     - Create a database with that title and schema, under the "Upskill 2k26" page, via `mcp__claude_ai_Notion__notion-create-database`. Its result includes a `<data-source url="collection://...">` — that id (not the database page id alone) is what you'll need to query and create pages against.
     - Persist both: `uv run python -m pipeline.cli save-notion-tracker state/notion-tracker.json --database-id '<database url/id>' --data-source-id '<collection://... id>'`.
   - For every job in this run's combined successes + failures list:
     - Query via `mcp__claude_ai_Notion__notion-query-data-sources` (SQL mode, against the saved `data_source_id`) for an existing row where `"Job ID"` equals this job's `job_id`.
     - Shape properties: `uv run python -m pipeline.cli notion-properties --job '<json job>' --today <date> [--is-new if no page was found]`. For a failed-tailor job, include its `error` field in the job JSON — it lands in the `Notes` property. For a `pdf_error` job (still a successful tailor, just no PDF), pass the `pdf_error` text as `error` too, so `Notes` explains why.
     - Create a page (none found, via `mcp__claude_ai_Notion__notion-create-pages` with `parent: {data_source_id: ...}`) or update the existing one (found, via `mcp__claude_ai_Notion__notion-update-page`) with those properties. No PDF is uploaded or attached — the Job Tracker no longer carries a resume file, only the row's data; `shortlist.md`'s `resume_path` column remains the way to reach a job's tailored resume.
     - If the call fails, retry once. If the retry also fails, record it as a Notion sync failure (`title`, `company`, `error`) instead — one job's Notion failure never stops the rest of the batch, and never blocks writing `shortlist.md` or updating `seen-jobs.json`.

7. **Write `shortlist.md`.**
   ```
   uv run python -m pipeline.cli render-shortlist --jobs '<json successes>' --failures '<json failures>' --notion-failures '<json notion sync failures>' > runs/<date>/shortlist.md
   ```
   `successes` needs `title`, `company`, `location`, `score`, `apply_link`, `resume_path`, `backfilled` per job — the PDF-preferring path computed in step 5, plus the `backfilled` flag `job-finder` returned (so a min_shortlist-backfilled job is visibly marked, not indistinguishable from one that cleared the threshold organically).

8. **Update the seen-jobs log** with every job that was shortlisted this run (successes and failures alike — a job that failed tailoring twice was still seen and scored, so it shouldn't resurface tomorrow as "new"):
   ```
   uv run python -m pipeline.cli append-seen state/seen-jobs.json --jobs '<json list of {job_id,title,company} for every shortlisted job>'
   ```

9. **Report back to the user**: how many jobs were found, shortlisted (and how many of those were `min_shortlist` backfill vs. organically above `relevance_threshold`), tailored successfully, tailored-and-failed, PDF-generation-failed (`pdf_error`, still counted as tailored), and Notion-sync-failed, plus the path to `runs/<date>/shortlist.md`.

## Notes

- Steps 3 and 4 (both subagents) are the only LLM-judgment (agentic) parts of this pipeline — everything else routes through the tested `pipeline` module via `uv run python -m pipeline.cli ...` rather than being reimplemented inline. If you find yourself hand-writing dedup, batching, PDF compilation, or markdown-rendering logic here, stop — that logic already exists in `pipeline/`.
- Step 6's Notion calls involve tool use too, but no LLM judgment — data is shaped by `pipeline.cli notion-properties`, and the step just decides create-vs-update and calls the connector. It's deliberately kept outside `pipeline/` rather than a stored-API-token approach, because it needs the connector's already-authorized access — see ADR 0001. Resume PDFs are never uploaded to Notion — see [ADR 0007](../../../docs/adr/0007-disable-notion-pdf-attachment.md).
- This skill is invoked both manually (`/job-hunt`) and by the daily 7am schedule — behavior is identical either way, there is no schedule-only code path. Step 1's `pdflatex` check matters most here: an unattended run should fail loudly on a missing dependency, not silently skip PDF generation for every job.
