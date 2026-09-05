# Design the search/tailor handoff contract

Type: grilling
Status: resolved
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

## Answer

**Two files, one writer each, addressed by `job_id`.**

### The contract

`runs/<date>/jobs.json` — written by the **search phase**, never rewritten by anything.
Holds the run date plus every shortlisted job in `job-finder`'s existing output schema
(`job_id`, `title`, `company`, `location`, `score`, `apply_link`, `description`,
`backfilled`).

`runs/<date>/tailored.json` — written by the **tailor phase**. Maps `job_id` to that
job's outcome: `tex_path`, `pdf_path`, the keywords inserted, and any error.

Nothing is shared mutable state, which is the whole point: running the tailor phase
twice, or running two of them concurrently, cannot corrupt the search phase's output.
Tailoring progress is never inferred from files lying around in `resumes/`.

### Complete vs in-flight — one mechanism, not two

The search phase writes `jobs.json.tmp` and **atomically renames** it on completion. So:

| On disk | Means |
| --- | --- |
| `jobs.json` | Search finished; safe to tailor |
| only `jobs.json.tmp` | Search in flight; tailor blocks and says so |
| neither | Search never ran today |

That same existence check is the **once-per-day guard** ticket 07 asked for — no
separate guard file. A `.tmp` older than ~45 minutes is a dead run rather than an
in-flight one, and should be treated as "never ran" so a crashed search doesn't wedge
the pipeline permanently.

### Addressing

`job_id` is the contract — it's already the dedup key in `state/seen-jobs.json` and
already a Notion column, so nothing new is invented. Because `4444888908` is unusable by
hand, `/job-hunt-tailor` also accepts a company or title fragment and resolves it against
`jobs.json`, erroring on an ambiguous match rather than guessing.

Run selection: **today by default**, `--date` to override, and a bare `job_id` searches
backwards up to **7 days**. That 7 is deliberately the same number as the retention
window in [Redefine "seen"](04-seen-semantics-and-retention.md) — one concept, not two
independent knobs that can drift apart.

### `shortlist.md` — the one thing that breaks today

`render_shortlist_markdown` (`pipeline/shortlist.py`) indexes `job["resume_path"]`
directly, so it raises `KeyError` on a job that hasn't been tailored. Under the split the
search phase writes `shortlist.md` before any resume exists.

Decision: the **search phase writes it with `resume_path` as `—`**, and the **tailor
phase re-renders the whole file** from `jobs.json` + `tailored.json`. The code change is
one line — `job.get("resume_path", "—")` — plus a test.

This is a genuine improvement rather than just damage control: `shortlist.md` becomes
useful the moment the search finishes, so you can read the day's jobs and pick which to
tailor before anything has been tailored.

### Failure modes

- **Search never ran today** — say so plainly and offer to run it, rather than erroring
  on a missing file.
- **Search ran, shortlisted nothing** — a valid outcome, not an error. Empty
  `shortlist.md`, matching what `/job-hunt` step 3 already does today.
- **A `.tex` already exists for the requested job** — skip by default, `--force` to
  redo. Protects the lazy path from silently re-burning an agent on work already done.

### Build items this settles

1. `render_shortlist_markdown` tolerates a missing `resume_path`.
2. Search phase writes `jobs.json` via tmp-and-rename, and `shortlist.md` with `—`.
3. Tailor phase writes `tailored.json` and re-renders `shortlist.md`.
4. `job_id` resolution helper (exact, then unambiguous fragment match), probably
   deterministic enough to live in `pipeline/` with tests.
