from pipeline.naming import resume_filename


def test_slugifies_company_and_title_into_tex_filename():
    assert resume_filename("Acme Corp", "Senior Backend Engineer") == "acme-corp-senior-backend-engineer.tex"


def test_strips_punctuation_and_collapses_whitespace():
    assert resume_filename("Acme, Inc.", "Staff Eng. (Platform)") == "acme-inc-staff-eng-platform.tex"
