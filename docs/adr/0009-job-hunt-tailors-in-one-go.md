# `/job-hunt` tailors every shortlisted job in the same run

The search/tailor split (`.scratch/job-hunt-speedup/map.md`) made `/job-hunt` stop after writing `jobs.json`, leaving tailoring to a separate `/job-hunt-tailor` the user ran by hand later. In practice that second call was just friction: the user wants resumes every day, and forgetting it meant an empty Resume column.

`/job-hunt` now runs the tailor phase as its last step, against the run it just wrote — every shortlisted job, using `/job-hunt-tailor`'s default-mode steps with selection widened from the top 8 to all (one wave, retry wave, deterministic ATS check, keyword-fix wave, `tailored.json`, re-rendered `shortlist.md`). Since the LaunchAgent invokes `/job-hunt`, the unattended morning run now produces resumes too.

The phases stay separate files and separate concepts. `jobs.json` is still the handoff, and is still written atomically before any tailoring starts, so a tailor-phase failure never loses the search. `/job-hunt-tailor` stays for the on-demand cases: one named job, `--pending`, an earlier run, or `--force`.

## Consequences

- `/job-hunt` checks `pdflatex` up front. If it's missing, the search still runs and tailoring is skipped with a clear message, rather than failing every agent.
- The once-per-day guard gets one more branch: a `complete` run with an empty `tailored.json` (search finished, tailoring didn't) resumes at the tailor step instead of stopping.
- The unattended run is longer — search plus one tailor wave — but still off the user's clock.
- `/job-hunt-dry-run` is unchanged in shape; it already ran both phases back to back.
- Tailoring every job rather than the top 8: the user wants a resume for every opening, not just the best eight. The tailor wave grows to the shortlist size (`max_shortlist`, 50), so the unattended run costs more agent time and tokens. `select-eager` stays, now used only by `/job-hunt-tailor`'s standalone default and the dry run.
