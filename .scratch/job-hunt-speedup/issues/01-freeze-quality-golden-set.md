# Freeze the resume-quality golden set

Type: task
Status: resolved
Blocked by: —
Map: ../map.md

## Question

Nothing to decide here — this is the manual work that unblocks every quality
judgment on this map. The destination promises resume quality is held constant, and
right now the repo has no way to detect a regression: README states plainly that
tailoring "is validated by running the pipeline for real, not by automated tests."

Assemble a frozen corpus:

- Pick **5 jobs** from `runs/2026-08-18/shortlist.md`, spread across the score range
  (8.5 down to 6.0) and including at least one that hit `pdf_error` (Akamai Software
  Engineer II, or Amazon Software Dev Engineer 2) — the retry path needs covering too.
- **The job descriptions no longer exist.** The orchestrator held them in-context and
  dropped them at run end; `shortlist.md` keeps only the apply link. So each JD must
  be re-fetched via `get_job_details` from its LinkedIn URL.
- **Expect some to be gone.** These postings are from 2026-08-18 and it is now
  2026-09-05 — roughly 2.5 weeks. Expired or pulled listings are likely. If fewer
  than 5 survive, take what survives and record how many; do not substitute jobs from
  a different run, because their tailored `.tex` reference wouldn't exist.
- Pair each surviving JD with its **existing tailored `.tex`** from
  `runs/2026-08-18/resumes/` — that file is the reference output, produced by the
  current pipeline, and is what any future change gets diffed against.
- Store the corpus somewhere durable and out of the run folders. Two reasons:
  run-folder pruning would destroy it, and `runs/` is gitignored (as PII-bearing
  runtime output), so a corpus living there is neither version-controlled nor
  shared. Note the reference `.tex` files themselves are gitignored today —
  copying them into the corpus is what makes them a durable baseline.

Record on resolution: how many JDs were recoverable, where the corpus lives, and
which job each `.tex` belongs to.

## Answer

**Done. Corpus lives at `tests/fixtures/golden/`. All five job descriptions were
recovered — none had expired.**

Five jobs from `runs/2026-08-18`, spread across the score range and including the
`pdf_error` case:

| Job | Company | Score | Note |
| --- | --- | --- | --- |
| SDE, Full Stack (AI/Agents) – Developer Platforms | Adobe | 8.5 | |
| Software Engineer II | Akamai | 8.5 | `pdf_error` — `.tex` only, no reference PDF |
| Software Engineer - App Stores | Canonical | 7.5 | |
| Computer Scientist II (Full Stack) | Adobe | 6.5 | |
| System Development Engineer, TFS-Onboarding | Amazon | 6.0 | |

Company mix is deliberate — two Adobe and one Amazon (both `target_companies`) against
Canonical and Akamai, so a change that only helps target-company jobs can't hide behind
the average.

Layout: `manifest.json` (metadata), `jobs/<slug>.md` (the JD, the tailor input),
`reference/<slug>.tex` (current pipeline's output, the baseline),
`reference/BASE-main.tex` (the base resume). Full caveats in
`tests/fixtures/golden/README.md`.

### Facts established

- **All five postings were still live.** The charting note expected losses after ~2.5
  weeks; there were none. Two (Akamai, Amazon TFS) no longer accept applications, but
  their description text is intact, which is all a corpus needs.
- **`BASE-main.tex` is the correct baseline.** `resume/main.tex` last changed in commit
  `1d5f8fb` on 2026-08-16 — before the 2026-08-18 reference run — so the base captured
  here is exactly the one that produced every reference `.tex`. Verified, not assumed.
- **The corpus compiles.** Smoke-tested `canonical-software-engineer-app-stores.tex`
  through `compile-resume-pdf` + `check-resume-pdf`: builds clean at `pages: 1`.
- **Stored outside `runs/`**, which is gitignored as PII-bearing runtime output and gets
  pruned — a corpus there would be neither durable nor version-controlled.

### Caveat that ticket 02 must account for

The descriptions were **re-fetched on 2026-09-05, not captured during the run** — the
orchestrator held them in context and dropped them, leaving only the apply link in
`shortlist.md`. Every posting was marked "Reposted 2 weeks ago," so the text may differ
slightly from what `resume-tailor` actually saw. A small unexplained diff against a
reference `.tex` may be drift in the posting, not a regression in the pipeline. Whatever
comparison method ticket 02 picks has to tolerate that.

Note this is exactly the problem the map's handoff-contract ticket fixes going forward:
once `jobs.json` persists descriptions, a future golden set can be captured rather than
reconstructed.
