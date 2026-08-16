# 06 — Notion Job Tracker (application-status sync)

**What to build:** A Notion database ("Job Search Tracker") holding every job ever shortlisted across all runs, upserted by `job_id`, with a hand-set `Applied` checkbox the pipeline never reads back. Populated as a new step in `/job-hunt`'s orchestration via the Notion MCP connector — write-only, supplementing `shortlist.md` rather than replacing it. Design captured via `/grill-with-docs` in [`CONTEXT.md`](../../../CONTEXT.md) and [ADR 0001](../../../docs/adr/0001-notion-job-tracker.md).

**Blocked by:** 01, 04

**Status:** needs-info

- [x] `pipeline/notion_tracker.py`: `build_notion_properties(job, is_new, today)` shapes a job into Notion page properties, only setting `Date Shortlisted`/`Applied` on create
- [x] `pipeline/notion_tracker.py`: `load_tracker_state` / `save_tracker_state` persist the created database's id at `state/notion-tracker.json` (gitignored)
- [x] `pipeline.cli` commands: `notion-database-schema`, `notion-properties`, `load-notion-tracker`, `save-notion-tracker`
- [x] `render_shortlist_markdown` / `render-shortlist` CLI: optional `## Notion Sync Failures` section, mirroring the existing `## Failures` section
- [x] `/job-hunt` SKILL.md: new step 5 — create the database on first run (parent: "Upskill 2k26" page), then upsert every shortlisted job (successes and resume-tailor failures alike), retry-once-then-record, never blocking `shortlist.md`/`seen-jobs.json`
- [x] A full manual `/job-hunt` invocation actually creates the Notion database and upserts rows against a live, authorized Notion connector

## Comments

Built (2026-08-16): pipeline module, CLI subcommands, shortlist rendering, and the SKILL.md orchestration step, all unit-tested (`uv run pytest`, `uv run mypy pipeline` both pass). The Notion MCP connector is not authorized in this environment, so the exact MCP tool names for creating a database / querying / creating / updating a page are not pinned in SKILL.md — it points at `ToolSearch` to resolve them once connected, rather than guessing names that might not exist.

Live-verified (2026-08-16), after the user authorized the Notion connector (took several restarts for this session to pick up the connector — unrelated to this ticket): created the "Job Search Tracker" database under "Upskill 2k26" (`notion-create-database`), queried it by `Job ID` (`notion-query-data-sources`, SQL mode), created a test row (`notion-create-pages`), then updated it (`notion-update-page`) and confirmed `Applied`/`Date Shortlisted` stayed untouched while `Score` changed — the upsert invariant from ADR 0001 holds.

This surfaced one real bug, now fixed: `build_notion_properties` originally emitted raw Notion REST API property-value objects (e.g. `{"title": [{"text": {"content": ...}}]}`), but the actual `mcp__claude_ai_Notion__*` tools use a flatter "SQLite value" convention (plain strings/numbers, `date:<column>:start` for dates, `"__YES__"/"__NO__"` for checkboxes) — visible in the created database's own `CREATE TABLE` output. Fixed in `pipeline/notion_tracker.py`, with tests and SKILL.md updated to match. Also added `data_source_id` alongside `database_id` to `state/notion-tracker.json` — the database id alone isn't enough to query or create pages against it.

**Note for the user**: a test row (`Job ID: TEST-001`, "Backend Engineer (Test Row)" / "Acme Test Co") was left in the live "Job Search Tracker" database to verify create+query+update — no delete/archive tool was available in this session's Notion MCP tools to remove it. Delete it manually in Notion whenever convenient; it's clearly labeled as a test row.

**Follow-up for the user**: run `/job-hunt` for real to confirm the full orchestration (job-finder → resume-tailor → Notion push, all together) rather than the individual pieces tested here.

Full-orchestration live test (2026-08-16): ran the entire `/job-hunt` flow by hand (job-finder → resume-tailor batch → Notion push → shortlist.md → seen-jobs), `max_shortlist` temporarily capped to 3 in `config/search.yaml` (reverted to 50 afterward) — a real LinkedIn search surfaced 3 genuine postings (Oracle Software Developer 3, Oracle Core Infra Engineer 2, Wells Fargo Senior Full Stack Engineer), each got a tailored `.tex` resume, all 3 pushed to the Job Tracker as new rows, `runs/2026-08-16/shortlist.md` written, `state/seen-jobs.json` created and populated. Zero failures at any step. This exercised the real orchestration end-to-end, not just individually-tested pieces. One infra hiccup along the way, unrelated to this ticket's code: the LinkedIn MCP browser session was dead (`TargetClosedError`) on the first attempt and needed a full VS Code restart to recover, same class of issue as the earlier Notion connector staleness.
