# Redefine "seen" and decide how long a lazy remainder stays tailorable

Type: grilling
Status: resolved
Blocked by: —
Map: ../map.md

## Question

Splitting the run changes what `state/seen-jobs.json` means, and the change needs to
be deliberate rather than incidental.

Settled: the append happens at **search** time, so `seen` comes to mean *"scored"*,
not *"handled."* The alternative — appending at tailor time — would resurface every
untailored job daily and re-spend serialized `get_job_details` calls on exactly the
jobs you chose to skip.

Still open:

- **The glossary entry.** `CONTEXT.md` has no term for this today. It needs one, in
  the existing format (definition plus an `_Avoid_:` line), because "seen" silently
  meaning two different things is how this kind of split rots.
- **How long a remainder stays reachable.** Job #14 from three days ago is still in
  that run's `jobs.json` — is it still tailorable? Forever, a fixed window, or until
  the posting expires? A LinkedIn posting that's gone can't be applied to, which
  argues for a shorter window than "forever."
- **How you'd find it.** With remainders spread across dated run folders, is there a
  cross-run view of what's still pending, or does the lazy path require knowing the
  date?
- **Whether the dry-run's skip still holds.** `/job-hunt-dry-run` deliberately never
  writes `seen-jobs.json`. If the append moves to the search phase, confirm that
  exclusion survives the move rather than being quietly dropped.

## Unblocked by ticket 03

The handoff contract is settled: `jobs.json` (immutable, search phase) plus
`tailored.json` (tailor phase), addressed by `job_id`, with a bare `job_id` searching
backwards **7 days** to find its run folder.

That 7 was chosen to be the *same number* as this ticket's retention window, on purpose
— they are one concept. If this ticket lands on a different window, ticket 03's lookback
must move with it rather than drifting into a second independent knob.

## Answer

**`seen` means "scored," and a remainder stays tailorable for 7 days.**

### The window: 7 days

Matching ticket 03's lookback, deliberately one number rather than two. Grounded in
evidence from the golden set: **2 of its 5 postings had stopped accepting applications
within ~2.5 weeks** of being shortlisted. A job left untailored for a week is likely
unapplyable regardless of what the pipeline does.

### Aging out is a real loss, and we accept it

A job that ages out untailored is still in `state/seen-jobs.json`, so it never resurfaces
— it's gone. That is the genuine cost of appending at search time, and it's accepted
rather than engineered around: *not tailoring a job for seven days is itself a decision*.

Rejected: expiring entries out of the seen log so they can resurface. That would re-fetch
and re-score jobs already passed on, re-spending serialized `get_job_details` calls on
exactly the churn that moving the append to search time was meant to eliminate.

The mitigation is a nudge, not a mechanism — the tailor phase reports how many
remainders are about to age out, so a loss is visible before it happens.

### Finding pending work

`/job-hunt-tailor --pending` scans the last 7 run folders and diffs each `jobs.json`
against its `tailored.json`, listing what remains with score and age. Entirely derived
from files ticket 03 already defined — no third state file, nothing extra to keep in
sync, nothing that can drift out of agreement with reality.

### Glossary changes (`CONTEXT.md`)

Two terms added, one amended:

- **Seen Job** — a job recorded in `state/seen-jobs.json`, meaning it was *scored* by a
  search run, not that it was handled. A seen job may never have been tailored. The log
  exists to stop the same posting being re-fetched and re-scored on later runs, and says
  nothing about whether a resume was produced. _Avoid_: processed job, handled job.
- **Pending Job** — a shortlisted job inside the 7-day window with no tailored resume
  yet. Reachable via `/job-hunt-tailor`; drops out of reach when the window passes.
  _Avoid_: untailored job, skipped job, backlog.
- **Dry Run** — amend. Its current text pins the seen-log skip to an orchestrator step
  that is moving into the search phase.

### Run folders are not deleted

The 7 days govern **reachability, not disk**. Nothing prunes `runs/` automatically.
Pruning stays in the map's fog — with one run folder in existence today it isn't a live
problem, and bolting it on here would grow this ticket for no benefit.

### Build items this settles

1. The **search phase** owns the `append-seen` call, and must carry a dry-run flag —
   `/job-hunt-dry-run` still never writes `state/seen-jobs.json`. This is the easiest
   thing in the whole migration to lose silently, because today it's an orchestrator
   step the dry-run simply skips.
2. `--pending` scan across the last 7 run folders.
3. Age-out warning in the tailor phase's report.
4. Three `CONTEXT.md` edits above.
