# 01 — Deterministic pipeline module (Python)

**What to build:** The deterministic plumbing that every other part of job-hunt calls into instead of reimplementing: loading/validating the search config, loading and updating the seen-jobs dedup log, filtering out already-seen jobs, chunking jobs into concurrency-bounded batches, rendering the run's `shortlist.md` output, and generating deterministic tailored-resume filenames. No LLM or network calls — pure, fully unit-tested functions.

**Blocked by:** None — can start immediately

**Status:** done

- [x] `load_search_config()` parses and validates `config/search.yaml` (search profiles, `relevance_threshold`, `max_shortlist`), raising a clear error on malformed/missing required fields
- [x] `load_seen_jobs()` reads `state/seen-jobs.json`, returning an empty log if the file doesn't exist yet
- [x] `append_seen_jobs(seen_log, new_jobs)` adds `job_id → {first_seen_date, title, company}` entries and persists the updated log
- [x] `filter_unseen_jobs(jobs, seen_log)` returns only jobs whose `job_id` is not already in the seen log
- [x] `batch_jobs(jobs, size=5)` chunks a list of jobs into groups of at most `size`
- [x] `render_shortlist_markdown(jobs, failures)` produces a markdown table (title, company, location, score, apply link, tailored-resume path) plus a separate failures section
- [x] `resume_filename(company, title)` deterministically slugifies company + title into a `.tex` filename
- [x] All functions covered by unit tests (pytest) asserting behavior, not internals

## Comments

Implemented via TDD (2026-08-16): `pipeline/{config,seen_jobs,dedup,batching,shortlist,naming}.py`, all seven functions covered by 30 pytest cases (`tests/`), mypy-clean. Added `pipeline/cli.py` as a thin JSON-in/JSON-out CLI wrapper so the agentic layer (subagents, `/job-hunt` skill) can invoke these functions via `Bash` without reimplementing logic in prose. Post-implementation code review caught and fixed three issues: unescaped `|`/newlines in `render_shortlist_markdown` table cells, unvalidated `size<=0` in `batch_jobs`, and an uncaught `KeyError` on jobs missing `job_id` in `filter_unseen_jobs` — all three now raise/handle clearly and are covered by regression tests.
