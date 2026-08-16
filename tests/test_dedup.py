import pytest

from pipeline.dedup import filter_unseen_jobs


def test_drops_jobs_whose_job_id_is_in_seen_log():
    jobs = [
        {"job_id": "1", "title": "A"},
        {"job_id": "2", "title": "B"},
        {"job_id": "3", "title": "C"},
    ]
    seen_log = {
        "2": {"first_seen_date": "2026-08-01", "title": "B", "company": "Acme"},
    }
    assert filter_unseen_jobs(jobs, seen_log) == [
        {"job_id": "1", "title": "A"},
        {"job_id": "3", "title": "C"},
    ]


def test_empty_seen_log_returns_all_jobs():
    jobs = [{"job_id": "1", "title": "A"}]
    assert filter_unseen_jobs(jobs, {}) == jobs


def test_all_seen_returns_empty_list():
    jobs = [{"job_id": "1", "title": "A"}]
    seen_log = {"1": {"first_seen_date": "2026-08-01", "title": "A", "company": "Acme"}}
    assert filter_unseen_jobs(jobs, seen_log) == []


def test_job_missing_job_id_raises_clear_error():
    jobs = [{"title": "A"}]
    with pytest.raises(ValueError, match="job_id"):
        filter_unseen_jobs(jobs, {})
