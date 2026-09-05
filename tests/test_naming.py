from pipeline.naming import resume_filename


def test_slugifies_company_and_appends_job_id():
    assert resume_filename("Acme Corp", "4455266391") == "acme-corp-4455266391.tex"


def test_strips_punctuation_and_collapses_whitespace():
    assert resume_filename("Acme, Inc.", "123") == "acme-inc-123.tex"


def test_same_company_and_title_stay_distinct_by_job_id():
    """Amazon posts several identically-titled roles; the id keeps them apart."""
    assert resume_filename("Amazon", "111") != resume_filename("Amazon", "222")
