# Choose the unattended trigger

Type: grilling
Status: resolved
Blocked by: —
Map: ../map.md

## Question

Surfaced by [Does the unattended trigger actually fire on a closed MacBook?](06-unattended-trigger-on-sleeping-mac.md),
which established the facts: `/schedule` is unusable (cloud routines can't reach the
local Chromium-driving MCP server), a locked screen is fine, but a *closed lid* stops
a `launchd` job dead and timed RTC wakes fall straight back to sleep.

Two viable paths remain. Pick one:

- **A — Keep the machine awake.** LaunchAgent at `StartCalendarInterval {Hour: 7}`,
  Mac left on AC (where it already never idle-sleeps), lid open, logged in, screen may
  be locked. Delivers the original promise: the shortlist is already waiting when you
  sit down. Cost: a nightly habit — plugged in, lid open. Fails silently the morning
  you forget, or travel, or shut the lid.
- **B — Fire on wake.** Same LaunchAgent, but lean on `launchd`'s documented catch-up:
  the run starts the moment you open the lid, once per day via a date-stamp guard.
  Costs nothing in habit and never silently misses. But the ~14-minute search now
  overlaps the start of your session rather than finishing before it.

The decision turns on a question only you can answer: **does B still meet the
destination?** The map targets ≤15 min of *your* time. Under B the search hasn't
finished when you open the lid — but you also aren't watching it. If you open the lid
and go make coffee, B is as good as A for free. If you open the lid and immediately
want to tailor, B puts up to 14 minutes back on your clock and A is worth the habit.

Also decide:

- **What `/job-hunt-tailor` does when the search phase hasn't finished yet** — hard
  error, wait, or tailor from a partial `jobs.json`? Only matters under B, but it's the
  difference between B being seamless and being annoying.
- **How a missed or failed run surfaces.** Under either path, a run that didn't happen
  is currently invisible until you notice `shortlist.md` is stale or absent.
- **Whether `caffeinate -i` wraps the job** so a mid-run idle sleep can't kill it.
- **The Chromium profile lock.** If a Chromium is already open on that profile,
  `launch_persistent_context` fails. Does the trigger need to detect or handle that?

## Answer

**Option B — fire on wake.**

A LaunchAgent with `StartCalendarInterval {Hour: 7, Minute: 0}`, relying on `launchd`'s
documented catch-up (`man launchd.plist`: missed intervals "will be coalesced into one
event upon wake from sleep"). In practice the search phase starts the moment you open
the lid, at most once per calendar day, guarded by a date-stamped file.

Semantics are "7am, or first thing when I open the lid." Chosen over keeping the Mac
awake on AC with the lid open (option A) because it costs no nightly habit and can
never silently miss a morning. The trade — the ~14-minute search overlapping the start
of your session instead of finishing before it — is acceptable, since nobody is
watching it either way.

### The four consequences

- **Tailoring never runs on a partial search.** Top-8-by-score needs the complete
  scored set, so tailoring from a half-written `jobs.json` would pick the wrong eight.
  `/job-hunt-tailor` checks for a *completed* `jobs.json`; if the search phase is still
  in flight it says so and offers to wait, rather than guessing. This is the single
  decision that makes B feel seamless rather than annoying.
- **Failure surfaces at the point of use, not via notifications.** No alerting
  infrastructure. `/job-hunt-tailor` reports the last successful search date every time
  it runs and says so loudly when that isn't today — which is exactly the moment you'd
  care, since you're already sitting down to use it.
- **The job is wrapped in `caffeinate -i`**, so an idle sleep mid-run can't destroy
  fourteen minutes of serialized LinkedIn calls.
- **A Chromium already open on the profile fails loudly**, reporting the profile lock
  as the actual cause. The pipeline never kills the user's browser. This is a live risk
  under B specifically: you have just opened the lid, and Chromium may have restored on
  login.

### Still to design (belongs to the handoff-contract ticket, not here)

The guard file and the "completed vs in-flight" signal are part of what the search
phase writes and the tailor phase reads — so their concrete shape is settled in
[Design the search/tailor handoff contract](03-two-phase-handoff-contract.md), which
must now account for a `jobs.json` that can be observed mid-write.
