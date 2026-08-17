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

**Resume PDF**:
The compiled, one-page PDF rendering of a tailored resume, produced by `resume-packager` from a `resume-tailor` `.tex` output. Lives alongside the `.tex` in `runs/<date>/resumes/`, and — when successfully generated — is attached to the corresponding Job Tracker row.
_Avoid_: PDF resume, compiled resume

**ATS Check**:
The deterministic pass/fail run against a Resume PDF: every keyword `resume-tailor` honestly inserted must survive text extraction from the compiled PDF. Distinct from, but gates a Resume PDF equally alongside, the one-page limit.
_Avoid_: ATS score, ATS pass

**PDF Error**:
The failure state recorded on a shortlisted job when `resume-packager` can't produce a passing Resume PDF, even after its one retry. The job stays in the run — the `.tex` resume remains the fallback artifact — but no PDF is generated or attached to the Job Tracker.
_Avoid_: PDF failure, packaging error

**Backfilled Job**:
A shortlisted job that scored below `relevance_threshold` but was included anyway because fewer than `min_shortlist` jobs cleared the threshold organically. Still a real stage-2 candidate that passed the experience cap and blacklist — never a hard-gate exception. Marked in `shortlist.md` so it's never mistaken for one that cleared the bar on its own merits.
_Avoid_: Filler job, padded result

**Blacklisted Company**:
A company on the user's exclusion list. A job at a blacklisted company is dropped before scoring — it never reaches the Shortlist, is never resume-tailored, and never reaches the Job Tracker.
_Avoid_: Excluded company, banned company

**Dry Run**:
A `/job-hunt-dry-run` invocation: the same pipeline as `/job-hunt`, but `job-finder`'s search is capped to ~15 raw postings (fewer profiles queried, not a truncated full search) to validate the pipeline quickly. Uses real LinkedIn data and pushes to the real Job Tracker, but never writes `state/seen-jobs.json` and writes local output to `runs/<date>-dryrun/` instead of `runs/<date>/`.
_Avoid_: Test run, sample run

**Experience Cap**:
The maximum years of experience a job may require (currently 4) before it's rejected outright during scoring, regardless of relevance score. Read from the job description's core-role requirement — a range or a secondary/preferred-skill callout above the cap doesn't trigger rejection on its own.
_Avoid_: Seniority limit, years filter
