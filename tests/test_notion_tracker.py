import json

from pipeline.notion_tracker import (
    build_notion_properties,
    load_tracker_state,
    save_tracker_state,
)


def _job(**overrides):
    job = {
        "job_id": "123",
        "title": "Backend Engineer",
        "company": "Acme Corp",
        "location": "Remote - India",
        "score": 8.5,
        "apply_link": "https://linkedin.com/jobs/123",
    }
    job.update(overrides)
    return job


def test_new_job_sets_date_shortlisted_and_applied_false():
    properties = build_notion_properties(_job(), is_new=True, today="2026-08-16")

    assert properties["date:Date Shortlisted:start"] == "2026-08-16"
    assert properties["Applied"] == "__NO__"
    assert properties["Title"] == "Backend Engineer"
    assert properties["Score"] == 8.5
    assert properties["Job ID"] == "123"


def test_existing_job_never_touches_date_shortlisted_or_applied():
    properties = build_notion_properties(_job(), is_new=False, today="2026-08-16")

    assert "date:Date Shortlisted:start" not in properties
    assert "Applied" not in properties
    assert properties["Company"] == "Acme Corp"


def test_failed_tailor_job_carries_error_into_notes():
    properties = build_notion_properties(_job(error="tailoring failed twice: timeout"), is_new=True, today="2026-08-16")

    assert properties["Notes"] == "tailoring failed twice: timeout"


def test_job_without_error_gets_blank_notes():
    properties = build_notion_properties(_job(), is_new=True, today="2026-08-16")

    assert properties["Notes"] == ""


def test_load_tracker_state_returns_empty_dict_when_file_missing(tmp_path):
    path = tmp_path / "notion-tracker.json"
    assert load_tracker_state(path) == {}


def test_save_and_load_tracker_state_roundtrip(tmp_path):
    path = tmp_path / "notion-tracker.json"

    save_tracker_state({"database_id": "abc123"}, path)

    assert load_tracker_state(path) == {"database_id": "abc123"}
    assert json.loads(path.read_text()) == {"database_id": "abc123"}
