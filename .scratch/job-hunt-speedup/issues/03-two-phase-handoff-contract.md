# Design the search/tailor handoff contract

Type: grilling
Status: open
Blocked by: —
Map: ../map.md

## Question

The run splits into an unattended search phase and an attended tailor phase. They
need a handoff artifact, and its shape drives most of the rest of the map.

Settled already: descriptions land in the run folder as `jobs.json` rather than being
re-fetched (a re-fetch costs a serialized LinkedIn call and fails outright if the
posting is pulled) or read back from Notion (write-only, ADR 0001). Dropping them out
of the orchestrator's context is itself a speedup — it currently carries 21 full job
descriptions through steps 4-8.

Still open:

- **What exactly `jobs.json` holds.** The full `job-finder` output schema — `job_id`,
  title, company, location, score, `apply_link`, `description`, `backfilled` — or
  more? Does it record which jobs the tailor phase has already handled, or is that
  inferred from files on disk in `resumes/`?
- **How `/job-hunt-tailor` picks its work.** Top 8 by score is the default, but it
  also serves the lazy path — tailoring one job you name. What's the addressing
  scheme: `job_id`, a row number in `shortlist.md`, company+title?
- **Which run it operates on.** Today's by default — but the lazy path means reaching
  back into an older run folder. Does it take an explicit date, or search backwards?
- **Failure modes.** What happens when `jobs.json` is missing, when the search phase
  never ran today, when it ran but shortlisted nothing, or when a `.tex` already
  exists for a requested job.

## Added by ticket 07

The trigger is now **fire-on-wake**, so the search phase starts when the lid opens and
you may well invoke `/job-hunt-tailor` while it is still running. That adds two
requirements to the contract:

- `jobs.json` must be distinguishable as **complete vs in-flight** — the tailor phase
  blocks rather than tailoring a partial scored set. Write-to-temp-then-rename is the
  obvious mechanism, but the tailor phase also needs to tell "still running" apart from
  "never started today."
- A **date-stamped guard file** caps the search phase at one run per calendar day.
  Decide whether that's a separate file or a field inside `jobs.json`.
