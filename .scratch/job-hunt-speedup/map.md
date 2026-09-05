# Cut /job-hunt attended time to 15 minutes

Label: wayfinder:map

## Destination

A **decided plan** — not code — for cutting the time you personally sit through a
`/job-hunt` run from ~43 minutes to **≤ 15 minutes**, with resume quality provably
unchanged rather than merely promised. Done when every open ticket is resolved and
one build session could execute the result without further decisions.

## Notes

**Domain**: the `job-wizard` daily job-hunt pipeline. Read `CONTEXT.md` for the
glossary and `.scratch/job-hunt/spec.md` for the original rationale before
resolving any ticket. Skills to consult every session: `/grilling` and
`/domain-modeling`.

**Plan, don't do.** This map produces decisions. No ticket here delivers working
code — the build is a separate session after the map is clear.

**Measured baseline** (`runs/2026-08-18`, 21 shortlisted jobs, ~42m45s total):

| Phase | Duration | Share |
| --- | --- | --- |
| job-finder (search + 2-stage scoring) | ~14 min | 33% |
| tailor + package (5 sequential batches) | ~25 min | 59% |
| Notion push (21 jobs, ~42 serial calls) | ~3 min | 7% |

Single sample; mtimes shift when `resume-packager` rewrites a `.tex` on retry, so
treat as ± rather than stopwatch.

**Hard constraint — LinkedIn calls are globally serialized.** `mcp-server-linkedin`
ships `sequential_tool_middleware.py`, which serializes tool execution both inside
the process (`asyncio.Lock`) *and across processes* (a profile lease over one shared
Chromium profile). Fanning `job-finder` out into parallel subagents buys nothing —
they queue on the lease. At ~14 min for ~50-60 calls that phase runs at roughly one
LinkedIn call per 15 seconds, and the only lever on it is making fewer calls.

**What may be traded, in order**: completeness (redundant compiles, per-job Notion
round-trips) → money (concurrency, token burn) → breadth (fewer pages/profiles).
**Resume quality is never traded** — and per the destination, that has to be
*checkable*, not asserted.

**Standing constraints on every ticket**:

- `/job-hunt-dry-run` must keep working end-to-end. It is a consequence to protect,
  never a target to optimize.
- Notion stays write-only (ADR 0001). Nothing may read the Job Tracker back.
- `resume/main.tex` and `resume/resume.cls` are user-owned; no ticket changes them.

**Settled while charting** (context for every ticket, not decisions to revisit):

- The enemy is *attended* time, not wall-clock. `job-finder` moves to an unattended
  trigger, so its ~14 min stops counting — and its call volume therefore stops being
  worth cutting.
- `resume-packager` merges into `resume-tailor`; the ATS keyword check becomes a
  deterministic orchestrator step over the existing `check-resume-pdf`, so the gate
  stays independent of the agent that inserted the keywords.
- Only the top **8** shortlisted jobs get tailored eagerly; the rest are tailorable
  on demand. This is not a breadth cut — every job still reaches `shortlist.md`.
- One wave of 8 concurrent tailors, not batches of 5.
- The Notion push moves wholesale into the unattended phase; `Notes` loses the
  tailoring-error text (`shortlist.md` still reports every failure).
- Surfaces after the split: `/job-hunt` = unattended search phase, `/job-hunt-tailor`
  = attended phase, `/job-hunt-dry-run` = both, end-to-end, against its capped pool.
- The unattended trigger is a **local LaunchAgent, not `/schedule`** — corrected by
  ticket 06. Claude Code routines run in Anthropic's cloud and cannot reach the local
  stdio MCP server that drives the logged-in Chromium profile.

## Decisions so far

<!-- one line per closed ticket: gist + link. -->

- [Does the unattended trigger actually fire on a closed MacBook?](issues/06-unattended-trigger-on-sleeping-mac.md)
  — Not with the lid shut, and `/schedule` is out entirely (cloud routines can't reach
  the local browser MCP). But a *locked* screen is fine, so the split survives: either
  keep the Mac awake on AC with the lid open, or fire on wake via launchd's catch-up.
  Choosing between them is ticket 07.

- [Choose the unattended trigger](issues/07-choose-unattended-trigger.md) — Fire on
  wake, not on the clock: a LaunchAgent whose missed 7am firing catches up when the lid
  opens, once daily via a guard file. Tailoring blocks rather than running on a partial
  search; failures surface at point of use; `caffeinate -i` wraps the run; a locked
  Chromium profile fails loudly.

- [Freeze the resume-quality golden set](issues/01-freeze-quality-golden-set.md) — Done:
  `tests/fixtures/golden/` holds 5 jobs (scores 8.5-6.0, one `pdf_error` case), their
  descriptions, the reference `.tex` each produced, and the verified base resume. All
  five postings were still live. Caveat: descriptions were re-fetched, not captured, so
  small diffs may be posting drift.

- [Design the search/tailor handoff contract](issues/03-two-phase-handoff-contract.md) —
  Immutable `jobs.json` (search) + `tailored.json` (tailor), one writer each, addressed
  by `job_id`. Completion signalled by atomic tmp-rename, which doubles as the
  once-daily guard. `shortlist.md` is written by search with `resume_path` as `—` and
  re-rendered by tailor — the one place existing code breaks.

- [Redefine "seen" and decide how long a lazy remainder stays tailorable](issues/04-seen-semantics-and-retention.md)
  — `seen` means *scored*, not handled; appended at search time. Remainders stay
  tailorable for 7 days (the same number as 03's lookback) and are then genuinely lost,
  which is accepted rather than engineered around. `--pending` lists them; three
  `CONTEXT.md` terms change.

- [Specify the merged tailor agent, its ATS gate, and its retry policy](issues/05-merged-tailor-agent-scope.md)
  — `resume-packager` deleted; the orchestrator runs `check-resume-pdf` against the PDF
  the tailor already compiled, so it's 1 compile per job instead of 2 with the keyword
  gate still independent. Wave of 8 → retry wave → ATS check → keyword-fix wave. Three
  bounded retry budgets. Needs ADR 0008.

- [Decide what "quality unchanged" actually measures](issues/02-quality-comparison-method.md)
  — Deterministic proxies plus a *structural* comparison (sections, bullet counts, page
  count, keyword coverage), never a prose diff, because the corpus descriptions were
  re-fetched and drift. No LLM judge: no build item on this map touches the tailoring
  prompt, so the prose-generating half is unchanged. `tests/test_golden.py` runs the
  cheap half every time.

## Not yet specified

- **Whether `min_shortlist: 15` still earns its keep** once only 8 jobs are tailored
  eagerly. It interacts with the backfill rule in ADR 0004, whose whole argument was
  about shortlist *volume* — an argument that may not survive the eager/lazy split.
  Can't sharpen until the handoff contract exists.
- **Whether 8 is the right N.** It's a starting guess, not a measured number. Needs
  data nobody has yet: how many of a day's shortlist you actually apply to. Revisit
  after a few real runs under the new shape.
- **Whether the tailor phase can go faster still** — a cheaper/faster model for
  tailoring, or splitting tailoring into a cheap draft plus a quality pass. This is the
  one change that would genuinely move prose quality, and ticket 02 deliberately left
  the LLM-judge design unbuilt until it does. Picking this up means building that judge
  first.
- **Run-folder pruning.** Ticket 04 settled that the 7-day window governs
  *reachability*, not disk — nothing deletes `runs/` today, and with one run folder in
  existence it isn't yet a real problem. What should actually be deleted, and when,
  stays unspecified until there's enough accumulation to judge.
- **Whether `shortlist.md` should distinguish tailored from pending jobs**, and what
  a reader does with that column. Depends on the handoff contract's shape.

## Out of scope

- **Reducing LinkedIn call volume / search breadth** (fewer `max_pages`, fewer
  profiles, a tighter stage-1 filter). Once `job-finder` runs unattended its duration
  no longer counts against the destination, so cutting breadth would spend something
  you value for a benefit you'd never feel.
- **Collapsing `/job-hunt-dry-run` into the real run.** If the real run gets fast
  enough the dry-run's justification partly evaporates — but that's a fresh effort
  with its own destination, not a step on this route.
- **The dead `linkedin-official` MCP entry** (`LINKEDIN_CLIENT_ID: REPLACE_ME` in
  `~/.claude.json`), which costs a 30s connect timeout on every session. A real and
  trivially cheap win, but it's session startup cost, not run time — it sits outside
  this destination.
