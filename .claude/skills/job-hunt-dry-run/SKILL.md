---
name: job-hunt-dry-run
description: Runs a fast, minimal end-to-end pass of the whole job-hunt pipeline against a small capped pool of real LinkedIn postings, to validate the pipeline works without a full day's time and token cost. Use when the user runs /job-hunt-dry-run, or wants to sanity-check search, scoring, tailoring, PDF packaging, and the Notion push end to end.
---

# /job-hunt-dry-run

A fast, minimal pass through the pipeline, sized for validating it end-to-end rather
than for a real day's job search. Real LinkedIn data, a real push to the Notion Job
Tracker, just a much smaller pool of jobs — and only a few resumes.

Run [`/job-hunt`](../job-hunt/SKILL.md)'s steps 1-15 exactly as written, with the
differences below. `/job-hunt` is a single skill that searches *and* tailors, so
following it end to end already exercises the whole pipeline.

## Differences

- **Step 1 (run date / guard):** use `runs/<date>-dryrun/` everywhere the real skill uses
  `runs/<date>/`. This keeps dry-run output fully isolated, so a dry run and a real run
  on the same day cannot overwrite each other's `jobs.json`, `shortlist.md`, or resumes.
  The `run-status` guard applies to the dry-run folder, so a second dry run on the same
  day is refused unless the folder is cleared first — and its `complete`-with-pending
  resume path works the same way against the dry-run folder.

- **Step 2 (pdflatex check):** unchanged. A dry run compiles real PDFs; that's most of
  what it's validating.

- **Step 4 (shortlist):** dispatch `job-finder` with a raw-result cap of **15** — its
  documented dry-run input, see [`job-finder`](../../agents/job-finder.md). That limits
  the search to the first profile or two at `max_pages: 1`, stopping once ~15 raw
  postings are gathered, instead of querying every configured profile. Everything
  downstream of the search — dedup, blacklist filtering, stage-1/stage-2 scoring,
  shortlist selection — runs exactly as normal against the smaller pool.

- **Step 7 (Notion push):** unchanged. Dry-run jobs land in the real Job Tracker like any
  other run's.

- **Step 8 (seen-jobs log):** **skip entirely.** Dry-run jobs are never appended to
  `state/seen-jobs.json`, so the same small pool stays available to re-test against, and
  a job seen only in a dry run is never suppressed from a later real `/job-hunt`.

  This is the single easiest thing to get wrong, since you are otherwise following
  `/job-hunt`'s steps verbatim. If you reach `append-seen`, stop and skip it.

- **Step 9 (tailoring):** tailor **at most 3 jobs**, not every shortlisted job. Use
  `select-eager --count 3` to pick them, then batch as normal. Three is enough to
  exercise wave dispatch, the ATS check, and the `shortlist.md` re-render without paying
  for a full day's agents. The remaining shortlisted jobs stay untailored and render as
  `—`; that is expected here and is **not** the behaviour of a real run.

- **Steps 10-14:** unchanged.

## Reporting

State plainly that this was a dry run, that the counts reflect a capped 15-job search
pool rather than a real day's coverage, and that only 3 jobs were tailored where a real
run would have tailored every one.

## Notes

- This skill exists purely to validate the pipeline quickly and cheaply. It is not a
  substitute for `/job-hunt`'s daily coverage, and its numbers shouldn't be read as a
  real job-market signal.
- The 3-job tailoring cap is the **only** place a top-N selection still exists. Real runs
  tailor everything ([ADR 0009](../../../docs/adr/0009-single-phase-run.md)); this cap is
  cost control for a smoke test, not a product rule.
- With only ~15 raw postings feeding stage-1/stage-2 filtering, falling short of
  `config/search.yaml`'s `min_shortlist` is expected, not a bug — `select-shortlist`
  degrades gracefully when too few candidates clear the bar (see
  [ADR 0004](../../../docs/adr/0004-min-shortlist-backfill.md)). A small or
  backfill-short shortlist here is not a pipeline failure.
- `job-finder` and `resume-tailor` are shared, unchanged, with the real skill. If you
  find yourself changing scoring or tailoring behaviour specifically for a dry run,
  stop. Only the search-scope cap, the output path, the seen-jobs skip, the tailor count,
  and the reporting differ.
