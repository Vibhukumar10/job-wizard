# Specify the merged tailor agent, its ATS gate, and its retry policy

Type: grilling
Status: open
Blocked by: —
Map: ../map.md

## Question

`resume-packager` merges into `resume-tailor`, and the ATS keyword check moves out of
the LLM into a deterministic orchestrator step over the existing `check-resume-pdf`.
That removes a whole agent spin-up and a redundant `pdflatex` per job — 21 of each on
the last run — while keeping the gate independent of the agent that inserted the
keywords, which is what ADR 0005's shift-left reasoning was protecting.

Still open:

- **Where the ATS check runs.** The orchestrator calling `check-resume-pdf` once per
  tailored job is 8 fast subprocess calls. Confirm that, and confirm it happens after
  the whole wave finishes rather than per-job inline.
- **What happens when the ATS check fails.** Today `resume-packager` owns a bounded
  fix-and-recompile retry. With the packager gone, does the orchestrator re-dispatch
  the tailor agent with the missing keywords, or does the job just take a
  `pdf_error`? Note the tailor already spends its own single fix-and-recompile
  attempt on the page-count check before handing off.
- **The retry budget overall.** `/job-hunt` currently retries a failed tailor once,
  and the tailor has one internal fix-and-recompile. With one wave of 8 rather than
  batches, does a retry rejoin the same wave or run after it — and does head-of-line
  blocking come back if it rejoins?
- **What `pdf_error` means now.** It was defined in `CONTEXT.md` as the packager
  failing after its one retry. With no packager, the term needs redefining or
  retiring.
