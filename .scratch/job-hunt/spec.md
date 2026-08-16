# job-hunt

Status: ready-for-agent

## Problem Statement

Applying to jobs well takes two things that don't scale by hand: (1) noticing relevant new postings the moment they appear, and (2) tailoring a resume to each one so it actually reads as a strong match. Doing both manually, every day, across enough postings to matter, isn't sustainable — postings get missed, and the resume sent is either generic (weak match) or hand-tailored for only a handful of jobs (low volume).

The user wants relevant jobs surfaced automatically within a day of posting, each with a resume tailored specifically to it, without spending their own time searching or editing.

## Solution

A Claude Code skill, `/job-hunt`, runs automatically once a day (7am, via `/schedule`) and:

1. Searches LinkedIn for jobs posted in the last 24 hours, across a set of user-configured search profiles.
2. Filters out anything already seen on a previous run, then judges the remainder for relevance against the user's resume, scoring on experience-level fit, tech-stack/domain fit, and product-vs-service company (as a soft preference).
3. Shortlists everything scoring ≥ 7.5/10, up to a safety cap of 50/day.
4. For each shortlisted job, tailors a copy of the user's LaTeX resume — rewording/reordering the professional summary, skills, and work-experience bullets to match the posting, inserting JD keywords honestly, and updating the location to match the posting (the user works remotely) — without touching education/achievements or fabricating anything not evidenced in the base resume.
5. Writes a dated run folder containing a curated `shortlist.md` (job, company, location, score, apply link, path to that job's tailored resume) and one tailored `.tex` file per shortlisted job, ready to upload when applying.

## User Stories

1. As a job seeker, I want jobs posted in the last 24 hours to be searched automatically every morning, so that I never have to remember to go looking myself.
2. As a job seeker, I want to define my own search profiles (keywords, location, work type, experience level), so that the search matches the roles I actually want.
3. As a job seeker, I want jobs I've already seen on a previous run excluded from future runs, so that I don't get duplicate entries or redundant tailored resumes for the same posting.
4. As a job seeker, I want each candidate job judged for relevance against my actual resume, so that irrelevant postings never reach my shortlist.
5. As a job seeker, I want relevance judged primarily on experience-level fit, then tech-stack/domain fit, then whether the company is product-based, so that the shortlist reflects what actually matters to me in a role.
6. As a job seeker, I want a product-based company preference to be a soft scoring signal rather than a hard filter, so that an excellent service-based-company match isn't silently dropped.
7. As a job seeker, I want the shortlist capped at a safety limit (50/day) even if more jobs clear the relevance bar, so that an unusually broad day doesn't trigger runaway tailoring work.
8. As a job seeker, I want every job that clears the 7.5 relevance threshold included, with no smaller artificial cap, so that I see the full breadth of what's actually relevant on a normal day.
9. As a job seeker, I want a tailored resume generated for every shortlisted job, so that I can apply with a resume that speaks directly to that posting.
10. As a job seeker, I want the tailoring agent to only edit my professional summary, skills, and work-experience bullets, so that my education and achievements are never altered.
11. As a job seeker, I want the tailoring agent to never invent employers, titles, dates, degrees, or skills I don't actually have, so that every tailored resume remains honest and defensible in an interview.
12. As a job seeker, I want relevant keywords from the job description worked into my resume where truthful, so that I score better against ATS keyword matching.
13. As a job seeker, I want the location on my resume updated to match each job posting's location, so that a remote application doesn't look geographically mismatched.
14. As a job seeker, I want the tailored output to stay in LaTeX (`.tex`), matching my base resume's format, so that I retain full control over final formatting and can compile it myself.
15. As a job seeker, I want each shortlisted job tailored independently in its own subagent invocation, so that details from one job's posting never bleed into another job's resume edits.
16. As a job seeker, I want tailoring to run with bounded concurrency (5 at a time), so that a big day completes in reasonable time without overwhelming rate limits or making failures hard to trace.
17. As a job seeker, I want a failed tailoring attempt retried once automatically, so that transient failures don't cost me a good match.
18. As a job seeker, I want a job that fails twice to be skipped and logged rather than aborting the whole run, so that one bad job never costs me the rest of the day's shortlist.
19. As a job seeker, I want a single curated `shortlist.md` per run listing every shortlisted job with its apply link, relevance score, and a path to its tailored resume, so that I can scan and act on a day's results in one place.
20. As a job seeker, I want each day's run output (shortlist + tailored resumes) kept in its own dated folder, so that historical runs stay self-contained and easy to review or prune later.
21. As a job seeker, I want the run to trigger automatically every day at a fixed time via a scheduled routine, so that I don't have to remember to invoke it myself.
22. As a job seeker, I want to also be able to trigger a run manually, so that I can re-run or test the pipeline on demand outside the schedule.
23. As a job seeker, I want my base resume kept at a fixed, version-controlled path (`resume/main.tex`), so that I can update my real resume over time and have every future run reflect the latest version.
24. As a job seeker, I want the deterministic parts of the pipeline (config loading, dedup filtering, batching, output rendering, state updates) covered by real unit tests, so that the plumbing around the agentic steps is verifiably correct and safe to refactor.

## Implementation Decisions

- **Orchestration**: A Claude Code skill, `/job-hunt`, coordinates two subagent roles via the Agent tool:
  - **job-finder subagent**: runs the search + two-stage relevance funnel, produces the shortlist for the run.
  - **resume-tailor subagent**: one invocation per shortlisted job, given that job's description and the base resume, produces a tailored `.tex` file. Dispatched in batches of 5 concurrent invocations.
- **Job source**: LinkedIn only, via the existing `mcp-server-linkedin` MCP tools (`search_jobs`, `get_job_details`). `search_jobs` is called with `date_posted: past_24_hours`.
- **Search configuration**: `config/search.yaml` holds a list of search profiles (`keywords`, `location`, `work_type`, `experience_level`), plus pipeline-wide settings: `relevance_threshold: 7.5`, `max_shortlist: 50`.
- **Two-stage relevance funnel** (job-finder subagent):
  1. Cheap pre-filter over raw search results (title/company/snippet only) to drop obvious non-matches before spending a `get_job_details` call on them.
  2. For survivors: `get_job_details` to fetch the full description, then an LLM relevance score (1–10) against `resume/main.tex`, weighted experience-level fit > tech-stack/domain fit > product-based-company (soft signal, not a filter).
- **Dedup**: a persistent `state/seen-jobs.json` log, structured as `job_id → {first_seen_date, title, company}`. Checked before stage 1 of every run to exclude previously-seen jobs; appended with the run's shortlisted job_ids at the end of the run.
- **Shortlisting**: jobs scoring ≥ `relevance_threshold` are shortlisted, up to `max_shortlist` per run. No smaller cap.
- **Resume-tailor subagent scope**:
  - Editable: professional summary, skills, work-experience bullets, and the location field (updated to match the job posting's location).
  - Untouched: education/achievements sections, `resume/resume.cls`.
  - Constraint: no fabricated employers, titles, dates, degrees, or skills — only rewording, reordering, emphasis shifts, and JD-keyword insertion where truthful.
  - Output: a `.tex` file only. No PDF compilation in this version.
- **Failure handling**: a failed resume-tailor subagent invocation is retried once automatically; a second failure is logged (job + error) and the batch continues.
- **Run output**: `runs/<YYYY-MM-DD>/` per run, containing:
  - `shortlist.md` — table of title, company, location, score, apply link, tailored-resume path; a separate section lists any failed jobs.
  - `resumes/<company>-<job-title-slug>.tex` — one tailored file per shortlisted job.
- **Scheduling**: triggered automatically once daily at 7am via the `/schedule` cron skill; also manually invokable as `/job-hunt` on demand.
- **Base resume**: fixed path, `resume/main.tex` (+ supporting `resume/resume.cls`), user-maintained between runs.
- **Deterministic pipeline module (Python)**: the single test seam for this feature. Exposes pure functions consumed by the skill's orchestration:
  - `load_search_config()` — parses and validates `config/search.yaml`.
  - `load_seen_jobs()` / `append_seen_jobs(seen_log, new_jobs)` — read/update `state/seen-jobs.json`.
  - `filter_unseen_jobs(jobs, seen_log)` — dedup a batch of search results against the seen-jobs log.
  - `batch_jobs(jobs, size=5)` — chunk shortlisted jobs into concurrency-bounded groups.
  - `render_shortlist_markdown(jobs, failures)` — produce the `shortlist.md` content.
  - `resume_filename(company, title)` — deterministic slug generation for tailored-resume filenames.

## Testing Decisions

- Only the deterministic pipeline module (Python) is covered by automated tests — these are unit tests over pure functions with no LLM or network calls involved.
- Good tests here assert external behavior of each function (given this input, this output), not internals — e.g. `filter_unseen_jobs` is tested by asserting which job_ids survive given a seen-jobs log, not by inspecting how it iterates.
- No prior art in this repo (greenfield) — tests should follow standard Python conventions (e.g. `pytest`, one test module per pipeline module function group).
- The agentic pieces (search-result relevance judgment, resume tailoring edits) are explicitly **not** unit-tested — they're LLM reasoning steps within subagent prompts, with no deterministic expected output to assert against. These are validated by running the pipeline for real (a live `/job-hunt` run, or a scoped prototype) and reviewing output quality, not by automated tests.

## Out of Scope

- PDF compilation of tailored resumes (stays as `.tex` output for now).
- Google Sheets sync.
- Google Calendar reminders for applying.
- Sub-24-hour search windows (blocked on LinkedIn's `date_posted` filter only supporting fixed buckets: `past_hour`, `past_24_hours`, `past_week`, `past_month`) — a future move to a tighter window will likely mean switching to `past_hour` on a more frequent schedule, or filtering client-side on a posted-timestamp if one is exposed via `get_job_details`.
- Indeed (or any other job source beyond LinkedIn).
- Hard filters on company, salary, or visa/work-authorization requirements — not part of this version's relevance scoring.

## Further Notes

- The user works remotely; every tailored resume's location is rewritten to match the target posting's location rather than reflecting the user's actual location.
- `runs/<date>/` is intentionally self-contained per day, anticipating a later integration with Google Sheets (tracking applied status) and Google Calendar (apply reminders) — output structure should stay easy to parse/sync from external tooling when that's built.
- Concurrency (5) and the relevance threshold (7.5) / shortlist cap (50) are config-driven, not hardcoded, so they can be tuned without a code change.
