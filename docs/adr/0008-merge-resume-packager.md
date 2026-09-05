# Merge resume-packager into resume-tailor, and take the ATS check out of the LLM

Every shortlisted job used to be compiled twice. `resume-tailor` compiled a PDF to validate its own one-page constraint ([ADR 0005](0005-shift-left-page-validation.md)), then `resume-packager` — a separate subagent, with its own spin-up cost and its own context — compiled the same `.tex` again from scratch to run the ATS keyword check ([ADR 0003](0003-resume-pdf-generation.md)). On the 2026-08-18 run that was 21 redundant `pdflatex` invocations and 21 redundant agent dispatches, and the tailor+package phase accounted for ~25 of the run's ~43 minutes.

`resume-packager` is deleted. `resume-tailor` keeps the compile it was already doing, and the PDF it produces is now the final artifact rather than a validation throwaway. The ATS keyword check moves to the orchestrating skill (`/job-hunt-tailor`), which runs the existing deterministic `check-resume-pdf` against that PDF once the whole wave of tailors has finished.

The adversarial property ADR 0005 was protecting survives, and is arguably strengthened. The concern with folding the check into the tailoring agent is that the agent which inserted the keywords would be grading whether they survived — marking its own homework. Moving the check into deterministic Python rather than into the agent avoids that entirely: `check_resume_pdf` extracts text with `pypdf` and does a substring match, with no judgment involved at all. The gate is now more independent than it was when another *LLM* held it.

Page validation stays inside `resume-tailor`, unchanged. ADR 0005's reasoning for shifting it left still holds exactly: the tailor is the only party that can trim a resume intelligently while preserving the keywords it inserted, whereas an orchestrator can only report a number. The orchestrator's check reads `pages` too, but only as a cheap backstop it gets for free while reading the PDF anyway.

Retries are now three bounded, distinct budgets rather than two overlapping ones: one fix-and-recompile inside the tailor (covering either a compile error or a page overrun), one re-dispatch of a failed tailor invocation, and one narrow keyword-restore pass when the ATS check finds an inserted keyword missing. The keyword-restore invocation is deliberately not a re-tailor — the agent is handed back its own `.tex` and only the missing terms, because a keyword usually vanishes when a later trim cuts the bullet carrying it, so restoring the original phrasing is the fix and inventing a new claim is not.

## Considered options

- **Keep `resume-packager` but have it reuse the tailor's PDF instead of recompiling** — rejected: it removes the redundant `pdflatex` but keeps the redundant agent, which is the larger cost. Once the packager stops compiling, everything it does is a deterministic check that never needed an LLM around it.
- **Fold the ATS check into `resume-tailor` itself** — rejected: this is the "marking its own homework" case. A tailor that both inserts keywords and certifies their survival can quietly drop an awkward keyword and report success.
- **Run the ATS check inline per job, as each tailor returns** — rejected as pointless: it's `pypdf` text extraction, milliseconds per job, and nothing mid-wave depends on the result. Checking once after the wave keeps the orchestration simple and produces one consolidated report.
- **Drop the ATS check entirely** — rejected. Honest keyword insertion is the entire reason tailoring exists; a resume that silently loses its keywords in a trim is the exact failure the check was built for.

## Consequences

- One `pdflatex` invocation and one agent dispatch per job instead of two of each, on the phase that dominated the run's wall-clock.
- `.claude/agents/resume-packager.md` is deleted. [ADR 0003](0003-resume-pdf-generation.md)'s packaging half is superseded — its PDF-generation rationale (pdflatex over tectonic, the ATS keyword check, why `resume.cls` needs `glyphtounicode`) still holds, but the agent it describes no longer exists. [ADR 0005](0005-shift-left-page-validation.md) is revised rather than superseded: its shift-left argument stands, its "packager is the independent backstop" framing does not.
- `PDF Error` is redefined in `CONTEXT.md`: it now means the tailor phase couldn't produce a passing one-page, ATS-clean PDF after the bounded retries, with no packager in the definition. Its user-visible meaning is unchanged — the job stays in the run and the `.tex` remains the fallback artifact.
- `resume-tailor` gains a second, narrow mode. That is a real increase in the agent's surface area, accepted because the alternative was keeping a whole agent alive to own one deterministic substring check.
