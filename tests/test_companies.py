import pytest

from pipeline.companies import filter_blacklisted_jobs, normalize_company_name


def test_normalize_lowercases_and_trims():
    assert normalize_company_name("  Acme  ") == "acme"


def test_normalize_strips_corporate_suffixes():
    assert normalize_company_name("Acme Inc.") == "acme"
    assert normalize_company_name("Acme Corp.") == "acme"
    assert normalize_company_name("Acme LLC") == "acme"
    assert normalize_company_name("Acme, Ltd.") == "acme"


def test_normalize_only_strips_trailing_suffix():
    assert normalize_company_name("Acme Co Software") == "acme co software"


def test_filter_drops_jobs_matching_blacklist_case_insensitively():
    jobs = [
        {"job_id": "1", "company": "Acme Inc."},
        {"job_id": "2", "company": "Wells Fargo"},
    ]
    assert filter_blacklisted_jobs(jobs, ["acme"]) == [{"job_id": "2", "company": "Wells Fargo"}]


def test_empty_blacklist_returns_all_jobs():
    jobs = [{"job_id": "1", "company": "Acme"}]
    assert filter_blacklisted_jobs(jobs, []) == jobs


def test_job_missing_company_raises_clear_error():
    jobs = [{"job_id": "1"}]
    with pytest.raises(ValueError, match="company"):
        filter_blacklisted_jobs(jobs, ["Acme"])
