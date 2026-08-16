# Notion Job Tracker via MCP connector, alongside the per-run shortlist

`/job-hunt` had no way to know whether the user actually applied to a shortlisted job, and no cross-run view — each day's results lived only in that day's `runs/<date>/shortlist.md`, disconnected from every other day's. We decided to push every shortlisted job (both successfully tailored and resume-tailor failures) into a single Notion database — the Job Tracker, created under the user's "Upskill 2k26" page — upserted by `job_id`, with a hand-set `Applied` checkbox the pipeline never reads back. The push is a new `/job-hunt` orchestration step that calls the Notion MCP connector directly, rather than a deterministic `pipeline/` function backed by a stored API token. The Job Tracker supplements `shortlist.md`; it doesn't replace it.

## Considered options

- **Google Sheets** instead of Notion — rejected: a flat grid doesn't give the filtered/kanban views a "central place for all openings" wants, and Notion's relational model has room to grow past a binary `Applied` field later.
- **Deterministic Python + Notion REST API with a stored token**, keeping the "everything but the two agentic subagents lives in `pipeline/`" invariant — rejected: the MCP connector already has to be authorized for this feature to exist at all, so a token would be a second, redundant credential to manage for zero benefit, given the push itself involves no LLM judgment either way.
- **Replacing `shortlist.md`** with the Notion tracker entirely — rejected: `shortlist.md` is the per-run, git-trackable audit artifact (with resume paths); the tracker is the cumulative cross-run view. They answer different questions.
- **Reading `Applied` back into the pipeline** (e.g. to influence future scoring or exclusion) — rejected: dedup already runs off `job_id` in `seen-jobs.json` independent of application status, so there's no pipeline behavior that needs it. Keeping it write-only avoids a sync-direction bug class entirely.

## Consequences

- Switching Notion→Sheets, or MCP→API-token, later means rebuilding this step — that's the lock-in this ADR is flagging.
- `/job-hunt` now has an implicit dependency on the Notion MCP connector staying authorized, including during the unattended 7am scheduled run.
