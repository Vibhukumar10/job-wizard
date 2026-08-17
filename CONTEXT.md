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

**Target Company**:
A company on the user's preferred-employer list (`target_companies`). Every job at a target company gets a qualitative boost in relevance scoring; it does not bypass the relevance threshold on its own.
_Avoid_: Preferred company, priority company

**Wider-Net Company**:
A Target Company the user has additionally opted into dedicated search profiles (`wider_net_companies`, a config-editable subset of `target_companies`) — added because `search_jobs` has no company filter, so a scoring boost alone can't surface postings the generic profiles never fetched.
_Avoid_: Priority search company

**Blacklisted Company**:
A company on the user's exclusion list. A job at a blacklisted company is dropped before scoring — it never reaches the Shortlist, is never resume-tailored, and never reaches the Job Tracker.
_Avoid_: Excluded company, banned company

**Experience Cap**:
The maximum years of experience a job may require (currently 4) before it's rejected outright during scoring, regardless of relevance score. Read from the job description's core-role requirement — a range or a secondary/preferred-skill callout above the cap doesn't trigger rejection on its own.
_Avoid_: Seniority limit, years filter
