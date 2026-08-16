# 04 — `/job-hunt` orchestration skill

**What to build:** The `/job-hunt` Claude Code skill that ties the whole pipeline together: invokes the job-finder subagent to get the day's shortlist, dispatches the resume-tailor subagent per shortlisted job at a concurrency of 5, writes the complete dated run folder, and updates the seen-jobs log. Invoking `/job-hunt` manually is the first point at which the whole feature is demoable end-to-end.

**Blocked by:** 01, 02, 03

**Status:** needs-info

- [x] `/job-hunt` invokes the job-finder subagent (ticket 02) to produce the run's shortlist
- [x] Dispatches the resume-tailor subagent (ticket 03) once per shortlisted job, batched via `batch_jobs` (ticket 01) at 5 concurrent invocations at a time
- [x] Writes `runs/<YYYY-MM-DD>/shortlist.md` via `render_shortlist_markdown` (ticket 01), including a failures section for any job whose tailoring failed twice
- [x] Writes `runs/<YYYY-MM-DD>/resumes/<company>-<title-slug>.tex` for every successfully tailored job
- [x] Updates `state/seen-jobs.json` via `append_seen_jobs` (ticket 01) with the run's shortlisted job_ids
- [ ] A full manual `/job-hunt` invocation produces a complete, correct dated run folder against real LinkedIn postings

## Comments

Built (2026-08-16): `.claude/skills/job-hunt/SKILL.md`. Orchestrates job-finder → batched (5-concurrent) resume-tailor dispatch with retry-once-then-log semantics → `shortlist.md` + seen-jobs update, all via the ticket-01 CLI wrapper rather than reimplementing logic inline. Blocked on the same missing `resume/main.tex` as tickets 02/03 for a real end-to-end run — do that once the resume is in place.
