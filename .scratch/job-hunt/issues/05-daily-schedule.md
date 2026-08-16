# 05 — Daily schedule wiring

**What to build:** A `/schedule` cron routine that triggers `/job-hunt` automatically once a day at 7am, with no manual invocation required — while leaving the manual invocation path (ticket 04) intact for on-demand runs.

**Blocked by:** 04

**Status:** needs-info

- [ ] A scheduled cron routine is registered that fires `/job-hunt` daily at 7am
- [ ] The routine runs unattended and produces the same dated run-folder output as a manual invocation
- [ ] Manually invoking `/job-hunt` outside the schedule still works unchanged

## Comments

Deferred (2026-08-16): asked the user whether to register the live 7am cron now vs. after a verified manual run. They chose to wait — add `resume/main.tex`, run `/job-hunt` manually once to confirm the pipeline works for real, then use `/schedule` to register the daily 7am routine calling `/job-hunt`. Ticket 04's manual path is otherwise unaffected either way.
