# Company targeting via score boost + widened search; experience cap via LLM judgment

The user wants more postings from a list of preferred companies, a blacklist of companies that should never reach the Job Tracker, and jobs requiring more than a configured number of years of experience rejected outright. `search_jobs` (the LinkedIn MCP tool) has no company-name filter — only `keywords`/`location`/`work_type`/`experience_level` — so a target company can only be acted on if it's already in the candidate pool one of the existing generic profiles happened to fetch.

We split company targeting into two mechanisms: every `target_companies` entry gets a qualitative boost in job-finder's relevance scoring (ranked above location fit, below tech-stack/domain fit — no hardcoded points, consistent with how location fit is already judged); a user-editable subset, `wider_net_companies`, is additionally auto-expanded (deterministic `pipeline/` code) into dedicated per-company search profiles (company name folded into `keywords`, mirroring the existing remote + 3-city shape), because the boost alone can't help with jobs that were never fetched in the first place. `blacklist_companies` is dropped before Stage 1, via a new deterministic filter matched on a normalized (lowercased, corporate-suffix-stripped) company name.

The experience cap (`max_years_experience`) is enforced as a hard gate inside job-finder's existing Stage 2 LLM scoring, not a regex-based deterministic pipeline function — years-required text is unstructured (ranges, per-skill breakdowns, "5+ years preferred" bullets), and Stage 2 already reads the full description for relevance scoring.

## Considered options

- **Dedicated search profiles for every target company** — rejected: multiplies scrape volume/run time by the full target list every day. `wider_net_companies` reserves that cost for a config-editable subset the user actually opts in.
- **Deterministic regex years-extraction** — rejected: job descriptions state required years in too many shapes for a regex to reliably isolate "the" number; the LLM already reads the description in Stage 2 anyway.
- **Blacklist enforced only at the Notion-push step** (matching `CONTEXT.md`'s literal "Job Tracker" = Notion DB definition) — rejected: would waste resume-tailor subagent invocations on companies already ruled out, and blacklisted jobs would still clutter the dated `shortlist.md`.

## Consequences

- `config/search.yaml` gains four new optional, default-empty fields: `target_companies`, `wider_net_companies`, `blacklist_companies`, `max_years_experience` — omitting all four is a no-op, so existing configs keep working unchanged.
- `wider_net_companies` must be a subset of `target_companies`, validated at config-load time — adding a company to the wider net without first adding it to the target list is a config error, not silently ignored.
