# ADR 0009 — One `/job-hunt` call runs the whole hunt, and tailors every shortlisted job

**Status**: Accepted
**Supersedes**: the two-phase split and the top-8 eager set introduced by
[`.scratch/job-hunt-speedup/map.md`](../../.scratch/job-hunt-speedup/map.md)
(tickets [03](../../.scratch/job-hunt-speedup/issues/03-two-phase-handoff-contract.md)
and [05](../../.scratch/job-hunt-speedup/issues/05-merged-tailor-agent-scope.md))

## Context

The speedup map split a run in two — `/job-hunt` searched unattended from a LaunchAgent,
`/job-hunt-tailor` tailored later while the user was at the machine — and narrowed eager
tailoring to the **top 8** shortlisted jobs, leaving the rest tailorable on demand for 7
days.

Both changes optimised a metric the map chose for itself: *attended* time, the minutes
the user personally sits through a run. Neither was ever a user requirement. The original
spec says the opposite, plainly:

- Story 9 — "I want a tailored resume generated for **every** shortlisted job."
- Story 16 — "I want tailoring to run with **bounded concurrency (5 at a time)**."

The map recorded its own doubt about the split it was making. Under "Not yet specified"
it left open *"whether 8 is the right N — a starting guess, not a measured number"*, and
*"whether `min_shortlist: 15` still earns its keep once only 8 jobs are tailored"*.

In practice the split cost more than it saved:

- **A run stopped producing its deliverable.** `/job-hunt` finished with a `shortlist.md`
  whose every Resume cell read `—`. The thing the pipeline exists to produce required a
  second command the user had to remember.
- **The top-8 cap discarded work already paid for.** The expensive, irreducible half is
  the search (~14 min, globally serialized by `mcp-server-linkedin`). Having paid it for
  29 jobs, tailoring 8 leaves 21 fully-scored matches sitting behind a manual step, in a
  window that silently expires after 7 days.
- **Expiry is one-way.** An untailored job stays in `seen-jobs.json`, so it never
  resurfaces in a later search. A job the user didn't get round to is gone, not deferred.

## Decision

**`/job-hunt` runs the entire hunt in one invocation** — search, score, Notion push,
seen-log, and a tailored resume for **every** shortlisted job — with tailoring dispatched
in **concurrency-bounded waves of 5**, per spec story 16.

`/job-hunt-tailor` is kept, but demoted to a **recovery tool**: retrying a job that failed
during a run, re-tailoring one job with `--force`, reaching an earlier run inside the
7-day window, or answering `--pending`. It has no top-N cap either; its default is every
untailored job in the run.

`/job-hunt-dry-run` keeps a 3-job tailoring cap. That is cost control for a smoke test,
and is now the only top-N selection left anywhere in the system.

### Why waves of 5 rather than one wave of everything

The map settled on "one wave of 8 concurrent tailors, not batches of 5" — correct
reasoning for a fixed set of 8, where batching only adds head-of-line blocking. It does
not survive the cap's removal: `max_shortlist` is **50**, so an unbounded wave means up
to 50 concurrent agents. Bounded waves keep failures traceable and rate limits
respected, which is exactly what story 16 asked for. The tested `pipeline.cli batch`
helper already defaults to 5.

### Why the run stays resumable

Merging the phases makes a single invocation long, so it must survive being killed
partway. Three properties give that:

- `jobs.json` is written by an atomic tmp-rename, so it never exists half-written.
- Notion and the seen-log are written **before** tailoring, so a tailoring crash still
  leaves the day's jobs recorded and reachable.
- `shortlist.md` is rendered once before tailoring and re-rendered after, so an
  interrupted run still leaves a readable list.
- `run-status: complete` no longer means "stop". `/job-hunt` checks `pending` and resumes
  tailoring the jobs `tailored.json` doesn't have, which makes re-running it safe and
  idempotent.

## Consequences

- **A run's cost goes up and its unattended duration goes up a lot.** The LaunchAgent now
  tailors every shortlisted job on wake — dozens of subagent invocations, where it
  previously did none. This is the deliberate trade: the pipeline produces its actual
  deliverable without the user present, at materially higher token cost per run.
- **`pdflatex` is now required on the unattended path**, and is checked *before* the
  14-minute search rather than after, so a missing binary never costs a whole search.
  The LaunchAgent's `PATH` already includes `/Library/TeX/texbin`.
- **The 7-day retention window matters much less.** It still governs `/job-hunt-tailor`'s
  reach for recovery, but nothing routinely relies on it, because nothing is routinely
  left untailored.
- **`min_shortlist: 15` recovers its original meaning.** ADR 0004's argument was about
  shortlist volume; with every shortlisted job tailored, volume once again translates
  directly into resumes. The map's open question about whether the floor still earns its
  keep is closed by this decision.
- **The speedup map's destination is abandoned, not achieved.** "Attended time ≤ 15
  minutes" is no longer the goal; producing every resume in one call is. The map's other
  outcomes stand on their own merits and are unaffected: the LaunchAgent trigger, the
  merged `resume-tailor` (ADR 0008), the deterministic ATS gate, `seen` meaning *scored*,
  and the golden quality corpus.
