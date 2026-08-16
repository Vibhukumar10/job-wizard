import json

from pipeline.seen_jobs import append_seen_jobs, load_seen_jobs


def test_load_seen_jobs_returns_empty_log_when_file_missing(tmp_path):
    path = tmp_path / "seen-jobs.json"
    assert load_seen_jobs(path) == {}


def test_load_seen_jobs_reads_existing_log(tmp_path):
    path = tmp_path / "seen-jobs.json"
    path.write_text(json.dumps({"1": {"first_seen_date": "2026-08-01", "title": "A", "company": "Acme"}}))
    assert load_seen_jobs(path) == {
        "1": {"first_seen_date": "2026-08-01", "title": "A", "company": "Acme"}
    }


def test_append_seen_jobs_adds_new_entries_and_persists(tmp_path):
    path = tmp_path / "seen-jobs.json"
    seen_log = {}
    new_jobs = [{"job_id": "1", "title": "A", "company": "Acme"}]

    updated = append_seen_jobs(seen_log, new_jobs, path, today="2026-08-16")

    assert updated == {
        "1": {"first_seen_date": "2026-08-16", "title": "A", "company": "Acme"}
    }
    assert load_seen_jobs(path) == updated


def test_append_seen_jobs_merges_with_existing_log(tmp_path):
    path = tmp_path / "seen-jobs.json"
    seen_log = {"1": {"first_seen_date": "2026-08-01", "title": "A", "company": "Acme"}}
    new_jobs = [{"job_id": "2", "title": "B", "company": "Globex"}]

    updated = append_seen_jobs(seen_log, new_jobs, path, today="2026-08-16")

    assert updated == {
        "1": {"first_seen_date": "2026-08-01", "title": "A", "company": "Acme"},
        "2": {"first_seen_date": "2026-08-16", "title": "B", "company": "Globex"},
    }
