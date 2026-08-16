import json
from datetime import date
from pathlib import Path
from typing import Any


def load_seen_jobs(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def append_seen_jobs(
    seen_log: dict[str, Any],
    new_jobs: list[dict[str, Any]],
    path: Path | str,
    today: str | None = None,
) -> dict[str, Any]:
    today = today or date.today().isoformat()
    updated = dict(seen_log)
    for job in new_jobs:
        updated[job["job_id"]] = {
            "first_seen_date": today,
            "title": job["title"],
            "company": job["company"],
        }
    path = Path(path)
    path.write_text(json.dumps(updated, indent=2))
    return updated
