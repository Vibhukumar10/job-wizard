import json
from pathlib import Path
from typing import Any

DATABASE_TITLE = "Job Search Tracker"

# Notion property-object shapes, keyed by column name, for creating the database.
# See ADR 0001 (docs/adr/0001-notion-job-tracker.md): the pipeline only ever
# shapes data here — the actual Notion API calls happen via the MCP connector
# in the /job-hunt orchestration step, not in this module.
DATABASE_SCHEMA: dict[str, Any] = {
    "Title": {"title": {}},
    "Company": {"rich_text": {}},
    "Location": {"rich_text": {}},
    "Score": {"number": {}},
    "Apply Link": {"url": {}},
    "Job ID": {"rich_text": {}},
    "Date Shortlisted": {"date": {}},
    "Applied": {"checkbox": {}},
    "Notes": {"rich_text": {}},
    "Resume PDF": {"files": {}},
}


def build_notion_properties(job: dict[str, Any], *, is_new: bool, today: str) -> dict[str, Any]:
    """Shape one shortlisted job into Notion page properties.

    Values use the flat "SQLite value" convention the Notion MCP connector's
    create-pages/update-page tools expect (plain strings/numbers, a split
    date:<column>:start key, "__YES__"/"__NO__" for checkboxes) — not the
    raw Notion REST API property-object shape.

    On create (is_new=True), sets every column including the immutable
    Date Shortlisted and a fresh Applied=false. On update (is_new=False),
    only the mutable fields are touched — Date Shortlisted and Applied are
    left alone so a re-upsert never clobbers the user's hand-set status.

    "Resume PDF" is only set when the job carries a resume_pdf_file_id (the
    id returned by uploading the compiled PDF via the Notion MCP connector's
    file-upload flow) — a job with a pdf_error has no PDF to attach.
    """
    properties: dict[str, Any] = {
        "Title": job["title"],
        "Company": job["company"],
        "Location": job["location"],
        "Score": job["score"],
        "Apply Link": job["apply_link"],
        "Job ID": job["job_id"],
        "Notes": job.get("error", ""),
    }
    if job.get("resume_pdf_file_id"):
        properties["Resume PDF"] = [job["resume_pdf_file_id"]]
    if is_new:
        properties["date:Date Shortlisted:start"] = today
        properties["Applied"] = "__NO__"
    return properties


def load_tracker_state(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_tracker_state(state: dict[str, Any], path: Path | str) -> dict[str, Any]:
    path = Path(path)
    path.write_text(json.dumps(state, indent=2))
    return state
