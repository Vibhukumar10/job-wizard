from typing import Any

SHORTLIST_HEADER = "| Title | Company | Location | Score | Apply Link | Resume |"
SHORTLIST_DIVIDER = "| --- | --- | --- | --- | --- | --- |"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_shortlist_markdown(
    jobs: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    notion_failures: list[dict[str, Any]] | None = None,
) -> str:
    lines = ["# Shortlist", "", SHORTLIST_HEADER, SHORTLIST_DIVIDER]
    for job in jobs:
        cells = [job["title"], job["company"], job["location"], job["score"], job["apply_link"], job["resume_path"]]
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
