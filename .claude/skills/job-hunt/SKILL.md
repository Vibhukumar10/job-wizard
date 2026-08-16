---
name: job-hunt
description: Runs the full daily job-hunt pipeline — searches LinkedIn for new postings, scores them for relevance, tailors a resume per shortlisted job, and writes a dated run folder. Use when the user runs /job-hunt, or asks to search for jobs / refresh their shortlist / tailor resumes for new postings.
---

# /job-hunt

Ties together the job-finder and resume-tailor subagents into one dated run. This is the orchestration layer described in `.scratch/job-hunt/spec.md` — read that file first if it's present and you need the full rationale behind a step below.

## Steps

1. **Determine the run date.** Use today's date, `YYYY-MM-DD`. Create `runs/<date>/` and `runs/<date>/resumes/` if they don't exist.

2. **Get the shortlist.** Dispatch the `job-finder` subagent (via the Agent tool) with no special input beyond its own instructions — it reads `config/search.yaml`, `state/seen-jobs.json`, and `resume/main.tex` itself. It returns a JSON list of shortlisted jobs (see `.claude/agents/job-finder.md` for the schema).

   If `job-finder` reports that `resume/main.tex` is missing, stop and tell the user — the pipeline cannot proceed without it.

   If the shortlist is empty, skip to step 5 with an empty jobs list (still write a `shortlist.md` — an empty day is a valid outcome, not an error).

3. **Tailor a resume per shortlisted job.**
   - Chunk the shortlist into concurrency-bounded batches:
     ```
     uv run python -m pipeline.cli batch --size 5 --jobs '<json shortlist>'
     ```
   - For each batch, dispatch one `resume-tailor` subagent invocation per job **concurrently** (multiple Agent tool calls in the same turn), passing that job's title/company/location/description and the run's output directory (`runs/<date>/resumes/`). Wait for the whole batch to finish before starting the next.
   - If an invocation fails, retry it once (still within the same job, not the whole batch). If the retry also fails, record it as a failure (`title`, `company`, `error`) instead of a successful tailor — do not let one job's failure stop the rest of the batch or the run.

4. **Track successes and failures** as you go: a list of successfully tailored jobs (job fields + the resume path returned by the subagent) and a list of failures (job fields + error).

5. **Write `shortlist.md`.**
   ```
   uv run python -m pipeline.cli render-shortlist --jobs '<json successes>' --failures '<json failures>' > runs/<date>/shortlist.md
   ```
   `successes` needs `title`, `company`, `location`, `score`, `apply_link`, `resume_path` per job — build this from the job-finder output plus each job's tailored-resume path.

6. **Update the seen-jobs log** with every job that was shortlisted this run (successes and failures alike — a job that failed tailoring twice was still seen and scored, so it shouldn't resurface tomorrow as "new"):
   ```
   uv run python -m pipeline.cli append-seen state/seen-jobs.json --jobs '<json list of {job_id,title,company} for every shortlisted job>'
   ```

7. **Report back to the user**: how many jobs were found, shortlisted, tailored successfully, and failed, plus the path to `runs/<date>/shortlist.md`.

## Notes

- Steps 2 and 3 are the only agentic (LLM-judgment) parts of this pipeline — everything else routes through the tested `pipeline` module via `uv run python -m pipeline.cli ...` rather than being reimplemented inline. If you find yourself hand-writing dedup, batching, or markdown-rendering logic here, stop — that logic already exists in `pipeline/`.
- This skill is invoked both manually (`/job-hunt`) and by the daily 7am schedule — behavior is identical either way, there is no schedule-only code path.
