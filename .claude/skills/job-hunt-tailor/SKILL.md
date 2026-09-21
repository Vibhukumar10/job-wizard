---
name: job-hunt-tailor
description: Recovery tool for resumes /job-hunt didn't produce — retries jobs that failed during a run, tailors a single job named by job_id or company/title, or reaches a job from an earlier run inside the 7-day window. A normal day never needs this; /job-hunt already tailors every shortlisted job. Use when the user runs /job-hunt-tailor, asks to retry a failed resume, wants a resume for one specific job, or asks what's still pending.
---

# /job-hunt-tailor

A **recovery tool**, not a phase of the daily run.

[`/job-hunt`](../job-hunt/SKILL.md) tailors a resume for every shortlisted job in the
same call as the search, so on a normal day there is nothing left for this skill to do.
It exists for the cases `/job-hunt` leaves behind:

- a job whose tailoring failed twice during the run,
- one specific job the user wants re-tailored (`--force`),
- a job from an **earlier** run, still inside the 7-day window,
- answering "what's still missing a resume?" (`--pending`).

If the user invokes this and today's run is complete with nothing pending, say so
rather than re-tailoring work that is already done.

**There is no top-N cap here.** The default is *every* untailored job in the run, which
is the same rule `/job-hunt` follows — see
[ADR 0009](../../../docs/adr/0009-single-phase-run.md).

## Modes

| Invocation | Does |
| --- | --- |
| `/job-hunt-tailor` | Tailor every untailored job in today's run |
| `/job-hunt-tailor <job_id or fragment>` | Tailor that one job |
| `/job-hunt-tailor --pending` | List what's still tailorable, tailor nothing |
| `--date <YYYY-MM-DD>` | Operate on that run instead of today's |
| `--force` | Re-tailor a job that already has a `.tex` |

## Steps

1. **Verify the PDF toolchain.** Run `command -v pdflatex`. If missing, stop and tell
   the user plainly — installing it (`brew install --cask basictex`) is one-time
   environment setup, not something a run can work around. `pdflatex` specifically, not
   `xelatex`/`tectonic`: `resume.cls` depends on the pdfTeX-only `glyphtounicode`
   mechanism for ATS-correct text extraction.

2. **Handle `--pending` and exit.** If asked for pending work:
   ```
   uv run python -m pipeline.cli pending runs
   ```
   Print each job with company, title, score, its run date, and `days_left`. Surface the
   `warning` field prominently if present — it names jobs about to fall out of the 7-day
   window, after which they are genuinely unreachable (they stay in `seen-jobs.json`, so
   they will not resurface in a future search). Then stop.

3. **Find the run and check it's usable.** Default to today; `--date` overrides. For a
   bare `job_id` with no date, search backwards up to 7 days for a run containing it.
   ```
   uv run python -m pipeline.cli run-status runs/<date>
   ```
   - `complete` — proceed.
   - `in_flight` — a run is searching right now, and it will tailor these jobs itself
     when it gets there. **Do not tailor from a partial file.** Tell the user the run is
     still going and offer to wait.
   - `missing` — no run for that date. Say so and offer to run `/job-hunt`, rather than
     erroring on a missing file.

4. **Pick the jobs.**
   - **Named job:** `uv run python -m pipeline.cli resolve-job runs/<date> '<query>'`.
     This matches `job_id` exactly first, then falls back to a company/title fragment,
     and errors if the fragment is ambiguous rather than guessing. Report the ambiguity
     to the user with the candidates so they can be more specific.
   - **Default:** read the run's jobs and its existing outcomes, and take **every** job
     not already in `tailored.json` (unless `--force`):
     ```
     uv run python -m pipeline.cli read-jobs runs/<date>
     uv run python -m pipeline.cli read-tailored runs/<date>
     ```
   - If a chosen job already has a `.tex` and `--force` wasn't given, skip it and say so.
     Silently re-burning an agent on finished work is the failure mode here.

5. **Tailor, in concurrency-bounded waves of 5.**
   ```
   uv run python -m pipeline.cli batch --size 5 --jobs '<json of chosen jobs>'
   ```
   Each batch's agents go out concurrently in a single message; the next batch starts
   only once that wave returns. Pass each agent its job's **`job_id`**, title, company,
   location, full description (from `jobs.json`), and `runs/<date>/resumes/`. The
   `job_id` is required — the output filename is `<company>-<job_id>.tex`.

   Each agent returns `resume_path`, `pdf_path`, and the `keywords` it inserted. It
   compiles and page-validates its own output — the PDF it produces is the final
   artifact and is **not** recompiled downstream.

6. **Retry wave.** Any job whose agent failed gets exactly one retry, dispatched **after**
   the waves complete — never rejoined into a running one. A second failure is recorded
   as a failure and the run continues.

7. **ATS check — deterministic, outside any agent.** For each successfully tailored job:
   ```
   uv run python -m pipeline.cli check-resume-pdf --pdf <pdf_path> --keywords '<json keywords>'
   ```
   This is the independent gate: the agent that inserted the keywords does not get to
   grade whether they survived. It returns `pages` and `missing_keywords`, so it doubles
   as a free page-count backstop. See [ADR 0008](../../../docs/adr/0008-merge-resume-packager.md).

8. **Keyword-fix wave.** For any job with `missing_keywords`, dispatch `resume-tailor`
   once more in its narrow keyword-restore mode, passing the existing `.tex` path and
   only the missing keywords. Re-run step 7's check on the result. Still failing after
   that one attempt is a `pdf_error` — the job stays in the run with its `.tex` as the
   fallback artifact; it is not a failed job.

9. **Record outcomes.** For each job:
   ```
   uv run python -m pipeline.cli record-tailored runs/<date> <job_id> --outcome '<json>'
   ```
   with `tex_path`, `pdf_path` (omit on `pdf_error`), `keywords`, and `error` if any.
   `tailored.json` is this skill's file — never write `jobs.json`.

10. **Re-render `shortlist.md`** for the whole run, so it reflects both tailored and
    still-pending jobs:
    ```
    uv run python -m pipeline.cli render-shortlist --jobs '<json>' --failures '<json>' > runs/<date>/shortlist.md
    ```
    Each job's `resume_path` is its `pdf_path` when present, falling back to the `.tex`
    on `pdf_error`. Jobs not tailored yet keep rendering as `—`. Include the `backfilled`
    flag from `jobs.json` so a `min_shortlist` backfill stays visibly marked.

11. **Report**: how many were tailored, how many failed, how many hit `pdf_error`, how
    many remain pending in this run, and the path to `shortlist.md`. Finish with the
    age-out warning from `pipeline.cli pending` if there is one — a job about to drop out
    of the window is the one thing here the user can't recover later.

## Notes

- **Never tailor from an incomplete `jobs.json`.** Step 3 exists because `/job-hunt`
  fires on machine wake, so the user can easily invoke this while a run is mid-search.
- Retry budgets are bounded and distinct: one fix-and-recompile inside the agent (page
  or compile), one re-dispatch of a failed agent, one keyword-restore pass. No step gets
  a third attempt.
- Everything deterministic routes through `pipeline.cli`. If you find yourself resolving
  a job query by eye, batching by hand, or hand-writing markdown, stop — that logic lives
  in `pipeline/run_store.py` and is tested.
- This skill touches neither LinkedIn nor Notion. Both belong to `/job-hunt`, which means
  this one is not subject to the LinkedIn serialization lock at all.
