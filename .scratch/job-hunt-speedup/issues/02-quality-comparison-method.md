# Decide what "quality unchanged" actually measures

Type: grilling
Status: open
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
