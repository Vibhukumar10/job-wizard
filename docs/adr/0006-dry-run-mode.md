# A separate /job-hunt-dry-run skill, capped search scope, real Notion push, no seen-jobs writes

Validating the pipeline end-to-end previously meant running `/job-hunt` for real: searching every configured profile (dozens, after [ADR 0002](0002-company-targeting-and-experience-cap.md)'s company targeting), scoring every survivor, and tailoring+packaging every shortlisted job — expensive in both wall-clock time and tokens for what is often just "does this still work." The user wanted a minimal dry-run: 10-15 raw postings instead of the full search, fast enough to run repeatedly during development.

We added a separate skill, `/job-hunt-dry-run`, rather than a flag on `/job-hunt`. It's a thin delta document against `job-hunt/SKILL.md`'s steps rather than a duplicate — it names which steps change and leaves the rest to the real skill, to keep drift risk low despite being a second file.

The 15-job cap is enforced at the search step itself, not by fetching everything and truncating afterward — `job-finder` gained an optional, documented raw-result-cap input: when passed, it searches only as many profiles as needed (typically the first one or two, in config order) at `max_pages: 1`, stopping once the cap is reached, then truncates the merge. This was chosen over post-fetch truncation because the goal is reducing actual search-call time, not just downstream LLM cost — most of a real run's wall-clock time is the search step across every profile, so shrinking *that* is what makes a dry run fast.

Two choices favor realism over isolation: the Notion push still happens for real (dry-run jobs land in the actual Job Tracker, upserted by `job_id` like any other run), and PDF generation/tailoring runs unmodified — full pipeline coverage was the point. The one thing dry-run does *not* do for real is write `state/seen-jobs.json`: unlike Notion (idempotent upsert, and validating the sync path was an explicit goal), polluting the dedup log would consume the small test pool across repeated runs and could suppress a real job from tomorrow's actual `/job-hunt` run — a correctness risk with no corresponding validation benefit, since dedup logic itself is already covered by `pipeline/dedup.py`'s unit tests.

Dry-run output (`shortlist.md`, tailored `.tex`/`.pdf`) writes to `runs/<date>-dryrun/`, not `runs/<date>/`, so a same-day dry run and real run can't overwrite each other.

## Considered options

- **A `--dry-run` flag on `/job-hunt`** — considered, but the user chose a separate skill instead: more file surface, but a fully independent artifact rather than conditional branches threaded through every step of the real skill.
- **Search every profile, then truncate the merged list** — rejected: doesn't save any LinkedIn-side call time, which is most of a real run's wall-clock cost; only shrinks downstream scoring/tailoring work.
- **Skip the Notion push during dry-run** — considered (avoids any real-database writes during testing) but rejected: the user chose to push for real, treating the Notion sync path as part of what "end-to-end" needs to validate; upserts are naturally idempotent per `job_id`, so repeat dry-run testing doesn't accumulate duplicate rows.
- **Write `state/seen-jobs.json` for real, same as a normal run** — rejected: would shrink the test pool over repeated dry-runs and risks hiding a real job from a future real run purely because a dry-run test happened to see it first.
- **A configurable cap (numeric argument to the skill invocation)** — rejected in favor of a fixed, hardcoded 15: simplest, matches the requested "10-15" range, no argument-parsing needed for what's meant to be a quick sanity check.

## Consequences

- `job-finder.md` gains one new optional input (a raw-result cap) and a second branch in its search step — a small, additive change to its contract; a normal `/job-hunt` run (no cap passed) is unaffected.
- With only ~15 raw postings, `config/search.yaml`'s `min_shortlist` will typically not be reached after dedup/filtering/thresholding — expected and already handled gracefully by `select-shortlist` ([ADR 0004](0004-min-shortlist-backfill.md)), not a dry-run-specific bug.
- Two skill files now describe overlapping orchestration. `job-hunt-dry-run/SKILL.md` is written as an explicit delta against `job-hunt/SKILL.md` specifically to keep them from silently diverging as the real pipeline evolves — a step added to the real skill needs a decision (does dry-run inherit it or not) but not a blind copy-paste.
