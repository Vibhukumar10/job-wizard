# Does the unattended trigger actually fire on a closed MacBook?

Type: research
Status: resolved
Blocked by: —
Map: ../map.md

## Question

The whole "move job-finder off the attended clock" plan rests on an assumption nobody
has verified: that a 7am scheduled run *fires* on this machine. It's a laptop, and at
7am it is plausibly asleep with the lid shut. If the trigger silently doesn't fire,
the shortlist isn't waiting when you sit down and the entire split delivers nothing —
you'd just run both phases back-to-back and be where you started.

This is a facts question, resolvable without the user. Establish:

- What Claude Code's `/schedule` cron actually does when the machine is asleep or the
  lid is closed at fire time — skip silently, run late on wake, or never catch up?
- Whether it requires Claude Code to be running, and what happens if it isn't.
- What the alternatives are and what each costs: `launchd` with `StartCalendarInterval`
  (which does have catch-up-on-wake behaviour), `pmset` scheduled wake, or simply
  triggering on wake rather than at a fixed hour.
- Whether a run that fires unattended can complete at all given the LinkedIn MCP
  drives a real Chromium profile — does that need a logged-in GUI session?

That last point matters most and may be the one that decides the ticket: a browser
automation that can't run headless on a locked machine would force the search phase
back onto your clock, and the map would need re-drawing around it.

Note: `.scratch/job-hunt/issues/05-daily-schedule.md` covers the original (never
registered) 7am schedule and is worth reading first.

## Answer

**No — "7am, lid closed, asleep" does not work. But the split survives, via a
different trigger than the one assumed while charting.**

### `/schedule` is out

Claude Code routines run on **Anthropic-managed cloud infrastructure**, not locally.
That sounds like it solves sleep entirely — but it kills the pipeline instead: a cloud
routine cannot reach a locally-configured stdio MCP server. Per the routines docs,
servers added via `claude mcp add` are stored on the machine, not the account, and are
invisible to a routine. `mcp-server-linkedin` drives a local Chromium profile holding
a logged-in LinkedIn session; nothing in the cloud can touch it.

So `.scratch/job-hunt/issues/05-daily-schedule.md`'s original plan — register the run
with `/schedule` — was never going to work for this pipeline. Local scheduling only.

### Two hard blockers on the literal "sleeping laptop" version

1. **Lid closed defeats `launchd`.** `StartCalendarInterval` does catch up after sleep
   — `man launchd.plist`: *"Unlike cron which skips job invocations when the computer
   is asleep, launchd will start the job the next time the computer wakes up. If
   multiple intervals transpire before the computer is woken, those events will be
   coalesced into one event upon wake."* But Apple Developer Forums thread 815034
   isolates lid state as the variable: lid open while asleep → DarkWake runs the job;
   **lid closed → the job does not run until the lid is opened.**
2. **Timed wakes don't stay awake.** `pmset repeat wake` exists, but on this machine
   (M4 Pro, Mac16,8, macOS 26.5.2) `pmset -g log` shows **421 DarkWake vs 5 FullWake**
   over the past week, and every FullWake came from user activity — zero timer-driven
   ones. RTC wakes land in DarkWake and return to sleep within seconds. A browser run
   needs minutes.

### The good news — a locked screen is fine

This was the feared blocker and it isn't one. Screen lock is `loginwindow` drawing over
a still-live Aqua session; it does not tear the session down. A LaunchAgent
(`LimitLoadToSessionType: Aqua`) keeps GUI access, and headed Chromium runs normally on
a **locked but logged-in** Mac. Only *logging out* is fatal — per Apple TN2083, a
LaunchDaemon survives logout but "is not allowed to connect to the window server."

So the run does not need you present or the screen unlocked. It needs the machine
**awake and logged in**.

### Two workable paths

- **Keep it awake.** On AC this Mac already has `sleep 0` / `displaysleep 0` — plugged
  in, it never idle-sleeps. Lid open (display may be dark and screen locked), or
  `sudo pmset -a disablesleep 1` if the lid must shut, since
  `AppleClamshellCausesSleep = Yes`. A LaunchAgent with
  `StartCalendarInterval {Hour: 7}` then fires for real, and `caffeinate -i` around the
  job stops a mid-run idle sleep. This delivers the original promise: shortlist waiting
  when you sit down.
- **Trigger on wake instead of on the clock.** Keep the same LaunchAgent and *exploit*
  the documented catch-up: the job fires the moment the lid opens, coalesced to a single
  run, with a date-stamped guard file to cap it at once per day. Semantics shift from
  "7am" to "7am, or first thing when I open the lid." (`launchd` has no wake-event key;
  a true wake hook needs Homebrew `sleepwatcher`.)

### Caveats on either path

FileVault is on, so any restart parks at pre-boot until someone types the password.
Logging out kills the agent. A Chromium already open on that profile makes
`launch_persistent_context` fail on the profile lock. The LinkedIn session will
eventually need a manual re-login. Headless is not a fix — `mcp-server-linkedin` is
built on patchright, whose own authors specify `headless=False` for undetectability,
and headless wouldn't address sleep anyway.

### Consequence for the map

The destination holds. Choosing between the two paths is a real decision with different
UX, so it becomes its own ticket: **Choose the unattended trigger**. The map's charting
note that "`/job-hunt` is what the cron registers" has been corrected — it's a LaunchAgent,
not `/schedule`.
