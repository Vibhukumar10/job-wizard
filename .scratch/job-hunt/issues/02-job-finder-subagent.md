# 02 — Job-finder subagent (search + relevance funnel)

**What to build:** A subagent that, given the search config and the dedup log, searches LinkedIn for jobs posted in the last 24 hours across all configured search profiles, filters out already-seen jobs, runs a two-stage relevance funnel against the base resume, and returns a scored shortlist — jobs at or above the relevance threshold, capped at the configured maximum. Runnable and verifiable on its own, independent of the tailoring step.

**Blocked by:** 01

**Status:** needs-info

**Note:** requires `resume/main.tex` to already exist (user-provided; not built by this or any other ticket).

- [x] Adds an example `config/search.yaml` with at least one placeholder search profile (`keywords`, `location`, `work_type`, `experience_level`), plus `relevance_threshold: 7.5` and `max_shortlist: 50`
- [x] Calls LinkedIn `search_jobs` per configured profile with `date_posted: past_24_hours`
- [x] Applies `filter_unseen_jobs` (from ticket 01) against `state/seen-jobs.json` before any relevance judgment
- [x] Stage 1: cheap pre-filter on title/company/snippet drops obvious non-matches before spending a `get_job_details` call
- [x] Stage 2: for survivors, fetches full details via `get_job_details` and produces an LLM relevance score (1–10) against `resume/main.tex`, weighted experience-level fit > tech-stack/domain fit > product-based-company (soft preference, not a hard filter)
- [x] Returns the shortlist: jobs scoring ≥ `relevance_threshold`, capped at `max_shortlist`
- [ ] Running the subagent standalone against a real or sample config produces a correctly scored, deduped, capped shortlist

## Comments

Built (2026-08-16): `.claude/agents/job-finder.md` (subagent definition) and `config/search.yaml` (example profile + `relevance_threshold: 7.5` + `max_shortlist: 50`). The subagent is wired to the ticket-01 pipeline module via `uv run python -m pipeline.cli` for config-loading and dedup filtering, and to the LinkedIn MCP tools for search + detail fetch.

Live-verified the same day once `resume/main.tex` was added: ran the search+funnel steps manually (the `job-finder` custom agent type isn't picked up by the Agent tool until the session restarts) against real LinkedIn results for "Software Engineer" / United States / remote / mid_senior. Caught and fixed a real bug in the process — `search_jobs`'s `experience_level`/`work_type` params are underscore-separated enums (`mid_senior`, not `mid-senior`); the example config and the subagent's own instructions were wrong about this and are now fixed. Scored 8 real postings; only Chime's "Software Engineer, Infrastructure" cleared the 7.5 threshold (8.5) — the funnel correctly down-weighted several strong tech-stack matches (NinjaOne, McKesson, Cleerly) that required 5-12 years of experience against the resume's 3, confirming experience-level fit dominates the score as specified.

Search location has since been changed to India in `config/search.yaml` per the user's actual preference (2026-08-16) — not re-verified against that location yet, by user's choice.
