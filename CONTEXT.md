# job-wizard

Automates a daily job search: finds new postings, scores them, tailors a resume per shortlisted job, and tracks whether the user has applied.

## Language

**Shortlist**:
The set of jobs a single `/job-hunt` run surfaces after scoring — written to `runs/<date>/shortlist.md` as that run's dated, point-in-time artifact.
_Avoid_: Results, matches

**Job Tracker**:
The single Notion database holding every job ever shortlisted, across all runs, upserted by `job_id`. It supplements the per-run `Shortlist` rather than replacing it — it's the cumulative, cross-run view; `shortlist.md` is the dated snapshot.
_Avoid_: Central store, dashboard, sheet

**Applied**:
A binary property on a Job Tracker row, set by hand by the user — the pipeline only ever writes it (never reads it back for scoring or dedup decisions).
_Avoid_: Status, state
