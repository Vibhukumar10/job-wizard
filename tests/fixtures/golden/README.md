# Resume-quality golden set

The frozen baseline for checking that a speedup to `/job-hunt` didn't quietly make
tailored resumes worse. Created by
[ticket 01](../../../.scratch/job-hunt-speedup/issues/01-freeze-quality-golden-set.md)
of the [job-hunt speedup map](../../../.scratch/job-hunt-speedup/map.md).

The destination of that map is "cut the run to ≤15 minutes **without losing resume
quality**." Nothing in this repo could previously detect a quality regression — the
README says tailoring "is validated by running the pipeline for real, not by automated
tests." This corpus is what makes that claim checkable.

## Layout

| Path | What it is |
| --- | --- |
| `manifest.json` | The five jobs, their scores, and which one is the `pdf_error` case |
| `jobs/<slug>.md` | Job description — the input to `resume-tailor` |
| `reference/<slug>.tex` | The tailored resume the **current** pipeline produced, on 2026-08-18 |
| `reference/BASE-main.tex` | The base resume those references were tailored from |

## How to use it

Tailor each `jobs/<slug>.md` against `reference/BASE-main.tex`, then compare the output
against `reference/<slug>.tex`. The comparison method itself is deliberately not
specified here — that's
[ticket 02](../../../.scratch/job-hunt-speedup/issues/02-quality-comparison-method.md).

The deterministic gates (`compile-resume-pdf`, `check-resume-pdf`) already exist in
`pipeline/` and should run regardless; they catch broken LaTeX, page overruns, and lost
keywords, but they are blind to whether the prose actually reads well.

## Why these five

Spread across the reference run's score range (8.5, 8.5, 7.5, 6.5, 6.0), and including
one `pdf_error` job (Akamai) so the failure path is covered too. Company mix is
deliberate: two Adobe (a `target_company`), one Amazon (also target), one Canonical and
one Akamai, so a change that only helps target-company jobs can't hide.

## Caveats — read before trusting a diff

- **The job descriptions were re-fetched on 2026-09-05, not captured on 2026-08-18.**
  The original run held them in the orchestrator's context and dropped them; only the
  apply link survived in `shortlist.md`. All five postings were still live and every
  description was recovered — but each was marked "Reposted 2 weeks ago," so the text
  may differ slightly from what `resume-tailor` actually saw. A small unexplained diff
  against a reference `.tex` may be this, not a regression.
- **LinkedIn page chrome was trimmed.** The stored descriptions keep the job body and
  qualifications and drop candidate-insight panels, company boilerplate, and apply
  statistics. What the pipeline passes through is the raw `get_job_details` text, so
  these files are slightly cleaner than production input.
- **`BASE-main.tex` is verified correct.** `resume/main.tex` last changed in commit
  `1d5f8fb` on 2026-08-16, before the reference run — so this is exactly the base that
  produced the references. If `resume/main.tex` is edited later, this corpus's
  references become stale and the whole set needs regenerating.
- **Akamai has no reference PDF.** It hit `pdf_error` in the reference run, so only the
  `.tex` exists. That's the point of including it.
- **Two postings no longer accept applications** (Akamai, Amazon TFS). Irrelevant for a
  test corpus — the description text is what matters — but it's why they shouldn't be
  re-fetched again expecting the same result.
- **This lives outside `runs/`** deliberately: `runs/` is gitignored as PII-bearing
  runtime output and gets pruned, so a corpus there would be neither durable nor
  version-controlled.
