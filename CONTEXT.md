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
The compiled, one-page PDF rendering of a tailored resume, produced by `resume-tailor` alongside the `.tex` it writes. Lives alongside the `.tex` in `runs/<date>/resumes/`, and — when successfully generated — is the path `shortlist.md`'s Resume column points to. Never uploaded to the Job Tracker; the Tracker holds job data only.
_Avoid_: PDF resume, compiled resume

**ATS Check**:
The deterministic pass/fail run against a Resume PDF: every keyword `resume-tailor` honestly inserted must survive text extraction from the compiled PDF. Performed by the orchestrating skill, outside any agent, so the agent that inserted the keywords never grades whether they survived. Distinct from, but gates a Resume PDF equally alongside, the one-page limit.
_Avoid_: ATS score, ATS pass

**PDF Error**:
The failure state recorded on a shortlisted job when a Run can't produce a passing one-page, ATS-clean Resume PDF after its bounded retries. The job stays in the run — the `.tex` resume remains the fallback artifact — but no usable PDF is produced. Not a failed job: a failed job has no tailored resume at all.
_Avoid_: PDF failure, packaging error

**Backfilled Job**:
A shortlisted job that scored below `relevance_threshold` but was included anyway because fewer than `min_shortlist` jobs cleared the threshold organically. Still a real stage-2 candidate that passed the experience cap and blacklist — never a hard-gate exception. Marked in `shortlist.md` so it's never mistaken for one that cleared the bar on its own merits.
_Avoid_: Filler job, padded result

**Blacklisted Company**:
A company on the user's exclusion list. A job at a blacklisted company is dropped before scoring — it never reaches the Shortlist, is never resume-tailored, and never reaches the Job Tracker.
_Avoid_: Excluded company, banned company

**Dry Run**:
A `/job-hunt-dry-run` invocation: the same pipeline as a real run, but `job-finder`'s search is capped to ~15 raw postings (fewer profiles queried, not a truncated full search) and only 3 jobs are tailored rather than every shortlisted one. That 3-job cap is the only top-N selection left anywhere in the system. Uses real LinkedIn data and pushes to the real Job Tracker, but never writes `state/seen-jobs.json` and writes output to `runs/<date>-dryrun/`.
_Avoid_: Test run, sample run

**Experience Cap**:
The maximum years of experience a job may require (currently 4) before it's rejected outright during scoring, regardless of relevance score. Read from the job description's core-role requirement — a range or a secondary/preferred-skill callout above the cap doesn't trigger rejection on its own.
_Avoid_: Seniority limit, years filter

**Run**:
One `/job-hunt` invocation, which does the whole hunt: search LinkedIn, score for relevance, write `jobs.json`, push to the Job Tracker, record every shortlisted job as a Seen Job, then tailor a resume for *every* shortlisted job in concurrency-bounded waves of 5 and re-render `shortlist.md` with the resume paths. Fires unattended from a LaunchAgent on wake, and is safe to re-invoke: a run whose tailoring was interrupted resumes where it stopped rather than re-searching. See [ADR 0009](docs/adr/0009-single-phase-run.md).
_Avoid_: Search phase, tailor phase, two-phase run

**Recovery Tailoring**:
A `/job-hunt-tailor` invocation — not part of a normal day. It exists only to pick up what a Run couldn't finish: a job whose tailoring failed twice, one job re-tailored with `--force`, a job from an earlier run inside the 7-day window, or a `--pending` listing. Refuses to run against an incomplete `jobs.json`.
_Avoid_: Tailor phase, resume step, second phase

**Seen Job**:
A job recorded in `state/seen-jobs.json`, meaning a Run *scored* it — not that anything was done with it. A Seen Job may never have been tailored. The log exists solely to stop the same posting being re-fetched and re-scored on later runs, and says nothing about whether a resume was produced.
_Avoid_: Processed job, handled job

**Pending Job**:
A shortlisted job inside the 7-day retention window with no tailored resume yet — derived by diffing a run's `jobs.json` against its `tailored.json` rather than tracked in a file of its own. Now an exception rather than the norm: a Run tailors every shortlisted job, so a Pending Job means tailoring failed or was interrupted. Reachable via Recovery Tailoring, and also picked up automatically by re-invoking `/job-hunt`. Once the window passes it becomes unreachable: it stays a Seen Job, so it never resurfaces in a future search.
_Avoid_: Untailored job, skipped job, backlog
