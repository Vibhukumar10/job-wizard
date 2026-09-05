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
The deterministic pass/fail run against a Resume PDF: every keyword `resume-tailor` honestly inserted must survive text extraction from the compiled PDF. Run by the Tailor Phase itself, outside any agent, so the agent that inserted the keywords never grades whether they survived. Distinct from, but gates a Resume PDF equally alongside, the one-page limit.
_Avoid_: ATS score, ATS pass

**PDF Error**:
The failure state recorded on a shortlisted job when the tailor phase can't produce a passing one-page, ATS-clean Resume PDF after its bounded retries. The job stays in the run — the `.tex` resume remains the fallback artifact — but no usable PDF is produced. Not a failed job: a failed job has no tailored resume at all.
_Avoid_: PDF failure, packaging error

**Backfilled Job**:
A shortlisted job that scored below `relevance_threshold` but was included anyway because fewer than `min_shortlist` jobs cleared the threshold organically. Still a real stage-2 candidate that passed the experience cap and blacklist — never a hard-gate exception. Marked in `shortlist.md` so it's never mistaken for one that cleared the bar on its own merits.
_Avoid_: Filler job, padded result

**Blacklisted Company**:
A company on the user's exclusion list. A job at a blacklisted company is dropped before scoring — it never reaches the Shortlist, is never resume-tailored, and never reaches the Job Tracker.
_Avoid_: Excluded company, banned company

**Dry Run**:
A `/job-hunt-dry-run` invocation: the same pipeline as a real run, but `job-finder`'s search is capped to ~15 raw postings (fewer profiles queried, not a truncated full search) and only the top 3 jobs are tailored. Runs both the Search Phase and the Tailor Phase back to back, so the handoff between them is exercised too. Uses real LinkedIn data and pushes to the real Job Tracker, but never writes `state/seen-jobs.json` — a skip that now lives inside the Search Phase — and writes output to `runs/<date>-dryrun/`.
_Avoid_: Test run, sample run

**Experience Cap**:
The maximum years of experience a job may require (currently 4) before it's rejected outright during scoring, regardless of relevance score. Read from the job description's core-role requirement — a range or a secondary/preferred-skill callout above the cap doesn't trigger rejection on its own.
_Avoid_: Seniority limit, years filter

**Search Phase**:
The unattended half of a run, invoked as `/job-hunt`: search LinkedIn, score for relevance, write `jobs.json` and a resume-less `shortlist.md`, push to the Job Tracker, and record every shortlisted job as a Seen Job. Produces no resumes. Runs off the user's clock because LinkedIn tool calls are serialized globally and can't be made faster — only moved.
_Avoid_: Search step, find phase

**Tailor Phase**:
The attended half, invoked as `/job-hunt-tailor`: read a completed run's `jobs.json`, tailor the top 8 untailored jobs (or one named job), ATS-check each compiled PDF, and re-render `shortlist.md`. Refuses to run against an incomplete `jobs.json` — the top-8 selection needs the whole scored set.
_Avoid_: Resume step, tailoring run

**Seen Job**:
A job recorded in `state/seen-jobs.json`, meaning a Search Phase *scored* it — not that anything was done with it. A Seen Job may never have been tailored. The log exists solely to stop the same posting being re-fetched and re-scored on later runs, and says nothing about whether a resume was produced.
_Avoid_: Processed job, handled job

**Pending Job**:
A shortlisted job inside the 7-day retention window with no tailored resume yet — reachable via `/job-hunt-tailor`, and derived by diffing a run's `jobs.json` against its `tailored.json` rather than tracked in a file of its own. Once the window passes it becomes unreachable: it stays a Seen Job, so it never resurfaces in a future search.
_Avoid_: Untailored job, skipped job, backlog
