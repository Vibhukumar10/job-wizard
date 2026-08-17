# Guaranteeing shortlist volume via score-ordered backfill, not a lowered bar

The user wants at least 15 shortlisted jobs a day to maximize applies, but `relevance_threshold` exists specifically as a hard quality gate — nothing below it reaches the shortlist, full stop. A volume floor and a quality gate are in direct tension: on a day where fewer than 15 jobs clear the threshold, something has to give.

We resolved this with `min_shortlist`: after job-finder finishes stage-2 scoring (now keeping every score, not just the ones clearing threshold), a new deterministic function, `select_shortlist` (`pipeline/shortlist.py`, exposed via `pipeline.cli select-shortlist`), takes the full scored list and decides the final shortlist. Jobs at or above `relevance_threshold` are always included, highest-scoring first, capped at `max_shortlist`. If that's fewer than `min_shortlist`, the next-highest-scoring jobs *below* threshold are added — still real stage-2 candidates, already past the experience-cap hard gate and blacklist filter — until `min_shortlist` is reached or candidates run out. No further quality floor applies to backfill beyond having survived stage 1 and stage 2 at all: a job weak enough to fail stage-1's "obviously not a match" bar never reaches stage 2 to begin with, so anything stage-2 scored is already a legitimate, if lower-ranked, candidate.

The experience cap and blacklist are never relaxed for backfill — they're explicit exclusion rules, not quality signals to trade against volume. Backfilled jobs are marked (`backfilled: true` on job-finder's output, a "Backfill" column in `shortlist.md`) so a job included to hit the volume floor is never visually indistinguishable from one that cleared the bar on its own merits — the user is trading quality for volume deliberately, and should be able to tell which is which when deciding where to spend application effort.

This selection logic was previously described in `job-finder.md`'s prose (a simple threshold-filter-and-cap). Adding real branching (backfill) was the point at which it stopped being reasonable to hand-roll in agent instructions and moved into `pipeline/`, consistent with the project's existing rule that deterministic logic doesn't belong in agent prose.

## Considered options

- **Widen the search instead of backfilling** (more profiles, more locations, wider date window) when short of `min_shortlist` — rejected: a same-day empirical check found 800+ raw "Software Engineer" results in India alone within the 24-hour window, meaning the actual bottleneck is scoring strictness, not search volume. Widening the search wouldn't reliably produce more good candidates on a day where the existing search already surfaced the available pool; it would only add latency and LinkedIn call volume for no guaranteed benefit.
- **Soft target, no enforcement** (report against 15 without acting on it) — rejected: doesn't serve the user's actual stated goal of maximizing apply volume; a number the pipeline doesn't act on isn't a floor.
- **A numeric backfill floor score** (e.g. never backfill below a 4/10) — rejected in favor of reusing the existing stage-1 pre-filter bar: a second, disconnected numeric threshold would be one more knob to tune with no clearer meaning than "already passed stage 1."
- **Relaxing the experience cap or blacklist for backfill** — rejected: these are the user's explicit "never show me this" rules, not soft quality signals; diluting them for volume defeats their purpose.

## Consequences

- `config/search.yaml` gains one new optional field, `min_shortlist` (default `0`, meaning no floor — existing configs are unaffected). Validated at load time to be `<= max_shortlist`.
- `job-finder`'s stage-2 scoring must now retain every score, not discard sub-threshold ones early, since step 6 (`select-shortlist`) needs the full ranked candidate pool to backfill from.
- `job-finder`'s output schema and `shortlist.md` both gain a `backfilled` field/column — a small, additive change to an existing contract.
- On a day where even backfill can't reach `min_shortlist` (genuinely too few stage-2 candidates existed), the shortlist simply falls short — `select_shortlist` degrades gracefully rather than erroring, and the run report should surface the shortfall rather than hide it.
