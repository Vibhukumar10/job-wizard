# Redefine "seen" and decide how long a lazy remainder stays tailorable

Type: grilling
Status: open
Blocked by: 03
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
