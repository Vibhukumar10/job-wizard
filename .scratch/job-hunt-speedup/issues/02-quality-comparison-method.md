# Decide what "quality unchanged" actually measures

Type: grilling
Status: resolved
Blocked by: 01
Map: ../map.md

## Question

Given the frozen corpus, how do you compare a tailored resume produced *after* a
speedup against the reference produced *before*, and what result counts as "quality
held constant"?

The deterministic proxies already exist in `pipeline/` — compiles cleanly, fits one
page, inserted keywords survive PDF text extraction (`check-resume-pdf`). They are
cheap and should be the automatic gate. But they are entirely blind to whether the
prose is any good: a resume can pass all three and read worse.

So what closes that gap? A human read of the diff? An LLM judge scoring both outputs
blind? A keyword-coverage delta against the JD? Some combination, with the expensive
check reserved for changes that actually touch the tailoring prompt?

Note this is blocked by the corpus for a real reason, not bookkeeping: if only two of
the five postings survive re-fetch, a statistical method over five samples isn't
available and the answer changes.

Also decide who runs it and when — every change, or only changes touching the
resume path.

## Added by ticket 01

The corpus now exists at `tests/fixtures/golden/` and the contingency this ticket
worried about did not happen — **all five postings were still live and every
description was recovered**, so a five-sample method is available.

One new constraint instead: the descriptions were re-fetched 2026-09-05 rather than
captured during the 2026-08-18 run, and every posting was marked "Reposted 2 weeks
ago." The comparison method must tolerate small diffs caused by the posting text
drifting, rather than reading every difference as a pipeline regression.

## Answer

**Deterministic proxies plus a structural comparison. No LLM judge — not yet.**

### The reasoning that decides this

None of the build items from tickets 03, 04 and 05 touch the tailoring prompt. They
change orchestration, file layout, retry sequencing, and where the ATS gate runs.
`resume-tailor`'s actual editing instructions — what it may reword, what it must never
invent — come through unchanged. The prose-generating half of the system is not being
modified, so the prose-regression risk for *this* build is low, and heavy evaluation
apparatus aimed at it would be speculative infrastructure.

The LLM judge is the right tool for a different change: a cheaper or faster tailoring
model, or a rewritten prompt. That is explicitly deferred in the map's **Not yet
specified**, and this ticket's answer is where the judge gets built when it graduates.

### What "structural comparison" checks

Shape, never prose:

- Same sections present as the reference `.tex`.
- Bullet counts per role within tolerance of the reference.
- Compiles clean, exactly one page.
- JD-keyword coverage at or above the reference's.

**Never a word-for-word diff.** The corpus descriptions were re-fetched on 2026-09-05
rather than captured during the run, and every posting was marked "Reposted 2 weeks
ago" (see [ticket 01](01-freeze-quality-golden-set.md)). Textual diffing would fire
constantly on posting drift, and a check that cries wolf is one you learn to ignore —
which is worse than no check.

### Trigger — tiered

| Tier | When | What |
| --- | --- | --- |
| Proxies | Every test run | `pytest` over the committed corpus |
| Full regenerate + compare | Tailor prompt, model, or `resume.cls` changes | Script, run by hand |

Running the full comparison on every change would cost agent invocations for changes
that provably can't affect prose.

### What gets committed

`tests/test_golden.py` — compile all five reference `.tex` files, assert one page each,
assert the manifest resolves to files that exist. Fast, fits the existing `tests/`
layout alongside `test_pdf.py`, and it is a genuine regression guard on `resume.cls` and
the pdflatex toolchain, independent of anything in this map.

The regeneration-and-compare half is a **script, not `pytest`** — it requires agent
invocations to re-tailor, which don't belong in a unit test suite.

### Build items this settles

1. `tests/test_golden.py` as described.
2. A regenerate-and-compare script covering the four structural checks.
3. The LLM-judge design stays deferred, and its trigger is written down: a change to the
   tailoring prompt, the model, or `resume.cls`.
