---
name: job-hunt-dry-run
description: Runs a fast, minimal end-to-end pass of the whole job-hunt pipeline — both the search phase and the tailor phase — against a small capped pool of real LinkedIn postings, to validate the pipeline works without a full day's time and token cost. Use when the user runs /job-hunt-dry-run, or wants to sanity-check search, scoring, tailoring, PDF packaging, and the Notion push end to end.
---

# /job-hunt-dry-run

A fast, minimal pass through the pipeline, sized for validating it end-to-end rather
than for a real day's job search. Real LinkedIn data, a real push to the Notion Job
Tracker, just a much smaller pool of jobs.

**This skill deliberately runs both phases back to back.** The real pipeline is split —
[`/job-hunt`](../job-hunt/SKILL.md) searches unattended and
[`/job-hunt-tailor`](../job-hunt-tailor/SKILL.md) tailors later — but a smoke test that
only exercised half of it would miss exactly the handoff most likely to break. Run
`/job-hunt`'s steps, then `/job-hunt-tailor`'s, with the differences below.

## Search-phase differences (`/job-hunt` steps 1–8)

- **Step 1 (run date / guard):** use `runs/<date>-dryrun/` everywhere the real skill uses
  `runs/<date>/`. This keeps dry-run output fully isolated, so a dry run and a real run
  on the same day cannot overwrite each other's `jobs.json`, `shortlist.md`, or resumes.
  The `run-status` guard applies to the dry-run folder, so a second dry run on the same
  day is refused unless the folder is cleared first.
- **Step 3 (shortlist):** dispatch `job-finder` with a raw-result cap of **15** — its
  documented dry-run input, see [`job-finder`](../../agents/job-finder.md). That limits
  the search to the first profile or two at `max_pages: 1`, stopping once ~15 raw
  postings are gathered, instead of querying every configured profile. Everything
  downstream of the search — dedup, blacklist filtering, stage-1/stage-2 scoring,
  shortlist selection — runs exactly as normal against the smaller pool.
- **Step 6 (Notion push):** unchanged. Dry-run jobs land in the real Job Tracker like any
  other run's.
- **Step 7 (seen-jobs log):** **skip entirely.** Dry-run jobs are never appended to
  `state/seen-jobs.json`, so the same small pool stays available to re-test against, and
  a job seen only in a dry run is never suppressed from a later real `/job-hunt`.

  This is the single easiest thing to get wrong now that the append lives inside the
  search phase rather than in a separate orchestration step. If you are following
  `/job-hunt`'s steps and reach `append-seen`, stop and skip it.

## Tailor-phase differences (`/job-hunt-tailor`)

- Operate on `runs/<date>-dryrun/`, not today's real run.
- **Tailor at most 3 jobs**, not the usual top 8 — enough to exercise the wave dispatch,
  the ATS check, and the `shortlist.md` re-render without paying for eight agents. Use
  `select-eager --count 3`.
- Everything else is unchanged: one wave, the retry wave, the deterministic ATS check,
  the keyword-fix pass, `tailored.json`, and the re-render.

## Reporting

State plainly that this was a dry run, that the counts reflect a capped 15-job search
pool rather than a real day's coverage, and that only the top 3 were tailored.

## Notes

- This skill exists purely to validate the pipeline quickly and cheaply. It is not a
  substitute for `/job-hunt`'s daily coverage, and its numbers shouldn't be read as a
  real job-market signal.
- With only ~15 raw postings feeding stage-1/stage-2 filtering, falling short of
  `config/search.yaml`'s `min_shortlist` is expected, not a bug — `select-shortlist`
  degrades gracefully when too few candidates clear the bar (see
  [ADR 0004](../../../docs/adr/0004-min-shortlist-backfill.md)). A small or
  backfill-short shortlist here is not a pipeline failure.
- `job-finder` and `resume-tailor` are shared, unchanged, with the real skills. If you
  find yourself changing scoring or tailoring behaviour specifically for a dry run,
  stop. Only the search-scope cap, the output path, the seen-jobs skip, the tailor count,
  and the reporting differ.
