# Specify the merged tailor agent, its ATS gate, and its retry policy

Type: grilling
Status: resolved
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

## Answer

**One agent, one compile per job, with the keyword gate outside the LLM.**

`resume-packager` is deleted. `resume-tailor` absorbs it, and the ATS check becomes a
deterministic orchestrator step over the existing `check-resume-pdf`.

### Why this is free rather than a trade

`resume-tailor` already compiles a PDF to validate the one-page constraint
(`.claude/agents/resume-tailor.md` step 7). The orchestrator runs `check_resume_pdf`
against **that** PDF rather than compiling a fresh one — so the merge drops from two
`pdflatex` runs per job to one, and removes an entire agent spin-up, while the keyword
gate stays independent of the agent that inserted the keywords. Nothing about the
adversarial property ADR 0005 was protecting is lost.

### Division of labour

- **Tailor keeps its page check and its one fix-and-recompile.** It's the only party
  that can trim intelligently while preserving inserted keywords — an orchestrator can
  only report a number. ADR 0005's shift-left reasoning survives intact.
- **Orchestrator owns the keyword gate**, running `check-resume-pdf` with the keywords
  the tailor reported. It gets the page count for free in the same call, as a backstop.

### Sequencing

**Once, after the whole wave** — not inline per job. It's eight subprocess calls of
`pypdf` text extraction, measured in milliseconds, and nothing mid-wave depends on the
result. Inline checking buys no latency and complicates the orchestration.

Full order: **wave of 8 → retry wave → ATS check → keyword-fix wave**.

### Retries — three bounded, distinct budgets

1. **Inside the tailor**, one fix-and-recompile for a broken compile or a page overrun.
   Unchanged from today.
2. **A failed tailor invocation** is retried once, as a *second small wave after* the
   first — never rejoining the original wave, which would reintroduce head-of-line
   blocking through the back door. The retry set is normally zero or one job.
3. **Missing keywords** get one **targeted re-dispatch**: the tailor is handed back its
   own `.tex` plus the specific keywords that vanished, as a narrow "restore these" task
   rather than a re-tailor. Still failing after that is a `pdf_error`.

Budget 3 exists because quality is the one thing this map never trades, and honest
keyword insertion is the entire ATS value proposition — but it's capped at one, and
scoped to only the keywords that actually went missing.

### `pdf_error` is redefined, not retired

Same user-visible meaning — the job stays in the run and the `.tex` remains the fallback
artifact — but it now means *"couldn't produce a passing one-page, ATS-clean PDF after
the bounded retries above,"* with no packager in the definition. A `CONTEXT.md` edit, on
top of the three ticket 04 already requires.

### Build items this settles

1. Delete `.claude/agents/resume-packager.md`; fold compile+page validation into
   `resume-tailor`'s existing step 7 (largely already there).
2. Orchestrator runs `check-resume-pdf` per tailored job after the wave.
3. Keyword-fix re-dispatch path (narrow scope, one attempt).
4. `CONTEXT.md`: redefine **PDF Error**.
5. **ADR 0008** — supersedes ADR 0003's packaging half and revises ADR 0005, whose
   shift-left rationale survives but whose "packager is the independent backstop"
   framing does not. Three ADRs currently describe an agent that will no longer exist.
