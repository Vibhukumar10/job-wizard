from typing import Any

SHORTLIST_HEADER = "| Title | Company | Location | Score | Apply Link | Resume | Backfill |"
SHORTLIST_DIVIDER = "| --- | --- | --- | --- | --- | --- | --- |"


def select_shortlist(
    scored_jobs: list[dict[str, Any]],
    *,
    relevance_threshold: float,
    max_shortlist: int,
    min_shortlist: int = 0,
) -> list[dict[str, Any]]:
    """Pick the final shortlist from every stage-2-scored candidate.

    Jobs at or above relevance_threshold are always included, highest-scoring
    first, capped at max_shortlist. If that's fewer than min_shortlist, the
    next-highest-scoring jobs below threshold are added (backfilled=True)
    until min_shortlist is reached or candidates run out — score order only,
    since backfill candidates already cleared job-finder's stage-1 pre-filter
    and any hard gates (experience cap, blacklist), so no further quality
    floor applies beyond that. See docs/adr/0004-min-shortlist-backfill.md.
    """
    ranked = sorted(scored_jobs, key=lambda job: job["score"], reverse=True)
    above_threshold = [job for job in ranked if job["score"] >= relevance_threshold]

    if len(above_threshold) >= min_shortlist:
        return [{**job, "backfilled": False} for job in above_threshold[:max_shortlist]]

    below_threshold = [job for job in ranked if job["score"] < relevance_threshold]
    needed = min_shortlist - len(above_threshold)
    backfill = below_threshold[:needed]

    result = [{**job, "backfilled": False} for job in above_threshold]
    result += [{**job, "backfilled": True} for job in backfill]
    return result[:max_shortlist]


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_shortlist_markdown(
    jobs: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    notion_failures: list[dict[str, Any]] | None = None,
) -> str:
    lines = ["# Shortlist", "", SHORTLIST_HEADER, SHORTLIST_DIVIDER]
    for job in jobs:
        cells = [
            job["title"],
            job["company"],
            job["location"],
            job["score"],
            job["apply_link"],
            job["resume_path"],
            "Yes" if job.get("backfilled") else "",
        ]
        lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")

    if failures:
        lines += ["", "## Failures", "", "| Title | Company | Error |", "| --- | --- | --- |"]
        for failure in failures:
            cells = [failure["title"], failure["company"], failure["error"]]
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")

    if notion_failures:
        lines += ["", "## Notion Sync Failures", "", "| Title | Company | Error |", "| --- | --- | --- |"]
        for failure in notion_failures:
            cells = [failure["title"], failure["company"], failure["error"]]
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")

    return "\n".join(lines) + "\n"
