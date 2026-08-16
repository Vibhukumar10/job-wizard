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

Built (2026-08-16): `.claude/skills/job-hunt/SKILL.md`. Orchestrates job-finder → batched (5-concurrent) resume-tailor dispatch with retry-once-then-log semantics → `shortlist.md` + seen-jobs update, all via the ticket-01 CLI wrapper rather than reimplementing logic inline.

Partially live-verified the same day: manually walked through the full orchestration (job-finder step from ticket 02 → resume-tailor step from ticket 03 → `render-shortlist` → wrote `runs/2026-08-16/shortlist.md` and the tailored resume) against real LinkedIn data. Did not exercise the actual `/job-hunt` skill invocation or dispatch the subagents via the Agent tool, since neither `job-finder` nor `resume-tailor` nor the `job-hunt` skill itself are recognized mid-session — they were created after the session started, so the harness needs a restart to pick up new `.claude/agents/` and `.claude/skills/` entries. Did not run `append-seen` (by user's choice, since the search profile changed to India right after this verification — no point marking a US-region job as "seen" against a search that will no longer target that region).

**Follow-up for the user**: after restarting the Claude Code session, run `/job-hunt` for real to verify the skill invocation and subagent dispatch path itself, not just the underlying logic.
