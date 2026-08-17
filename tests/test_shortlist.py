import re

from pipeline.shortlist import render_shortlist_markdown, select_shortlist


def _scored(job_id, score):
    return {"job_id": job_id, "title": f"Job {job_id}", "score": score}


def test_select_shortlist_keeps_all_above_threshold_when_min_not_set():
    jobs = [_scored("1", 8.0), _scored("2", 7.0), _scored("3", 5.0)]

    result = select_shortlist(jobs, relevance_threshold=6.5, max_shortlist=50)

    assert [j["job_id"] for j in result] == ["1", "2"]
    assert all(j["backfilled"] is False for j in result)


def test_select_shortlist_caps_at_max_shortlist():
    jobs = [_scored(str(i), 9.0 - i) for i in range(5)]

    result = select_shortlist(jobs, relevance_threshold=0, max_shortlist=3)

    assert len(result) == 3
    assert [j["job_id"] for j in result] == ["0", "1", "2"]


def test_select_shortlist_backfills_below_threshold_to_reach_min():
    jobs = [_scored("1", 8.0), _scored("2", 5.0), _scored("3", 4.0), _scored("4", 3.0)]

    result = select_shortlist(jobs, relevance_threshold=6.5, max_shortlist=50, min_shortlist=3)

    assert [j["job_id"] for j in result] == ["1", "2", "3"]
    assert result[0]["backfilled"] is False
    assert result[1]["backfilled"] is True
    assert result[2]["backfilled"] is True


def test_select_shortlist_backfill_falls_short_gracefully_when_too_few_candidates():
    jobs = [_scored("1", 8.0), _scored("2", 5.0)]

    result = select_shortlist(jobs, relevance_threshold=6.5, max_shortlist=50, min_shortlist=10)

    assert len(result) == 2
    assert result[1]["backfilled"] is True


def test_select_shortlist_no_backfill_needed_when_enough_clear_threshold():
    jobs = [_scored("1", 9.0), _scored("2", 8.0), _scored("3", 7.0)]

    result = select_shortlist(jobs, relevance_threshold=6.5, max_shortlist=50, min_shortlist=2)

    assert len(result) == 3
    assert all(j["backfilled"] is False for j in result)


def test_renders_table_row_per_job():
    jobs = [
        {
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "location": "Remote - US",
            "score": 8.5,
            "apply_link": "https://linkedin.com/jobs/1",
            "resume_path": "resumes/acme-corp-backend-engineer.tex",
        }
    ]

    markdown = render_shortlist_markdown(jobs, [])

    assert "| Title | Company | Location | Score | Apply Link | Resume | Backfill |" in markdown
    assert "| Backend Engineer | Acme Corp | Remote - US | 8.5 | https://linkedin.com/jobs/1 | resumes/acme-corp-backend-engineer.tex |  |" in markdown
    assert "## Failures" not in markdown


def test_marks_backfilled_job_in_table():
    jobs = [
        {
            "title": "Backend Engineer",
            "company": "Acme Corp",
            "location": "Remote - US",
            "score": 5.0,
            "apply_link": "https://linkedin.com/jobs/1",
            "resume_path": "resumes/acme-corp-backend-engineer.tex",
            "backfilled": True,
        }
    ]

    markdown = render_shortlist_markdown(jobs, [])

    assert "| Backend Engineer | Acme Corp | Remote - US | 5.0 | https://linkedin.com/jobs/1 | resumes/acme-corp-backend-engineer.tex | Yes |" in markdown


def test_renders_failures_section_when_present():
    failures = [{"title": "Staff Engineer", "company": "Globex", "error": "tailoring failed twice: timeout"}]

    markdown = render_shortlist_markdown([], failures)

    assert "## Failures" in markdown
    assert "Staff Engineer" in markdown
    assert "Globex" in markdown
    assert "tailoring failed twice: timeout" in markdown


def test_empty_jobs_and_failures_still_renders_header():
    markdown = render_shortlist_markdown([], [])
    assert "| Title | Company | Location | Score | Apply Link | Resume | Backfill |" in markdown


def test_escapes_pipe_characters_in_job_fields():
    jobs = [
        {
            "title": "Staff | Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "score": 8.0,
            "apply_link": "https://x/1",
            "resume_path": "resumes/a.tex",
        }
    ]

    markdown = render_shortlist_markdown(jobs, [])

    row = [line for line in markdown.splitlines() if line.startswith("| Staff")][0]
    unescaped_delimiters = len(re.findall(r"(?<!\\)\|", row))
    assert unescaped_delimiters == 8  # 7 cells -> 8 delimiters, once the literal pipe is escaped
    assert "Staff \\| Backend Engineer" in row


def test_escapes_newlines_in_failure_error():
    failures = [{"title": "Eng", "company": "Acme", "error": "line one\nline two"}]

    markdown = render_shortlist_markdown([], failures)

    assert "line one line two" in markdown
    assert "\nline two" not in markdown


def test_renders_notion_sync_failures_section_when_present():
    notion_failures = [{"title": "Staff Engineer", "company": "Initech", "error": "Notion API rate limited"}]

    markdown = render_shortlist_markdown([], [], notion_failures)

    assert "## Notion Sync Failures" in markdown
    assert "Staff Engineer" in markdown
    assert "Initech" in markdown
    assert "Notion API rate limited" in markdown


def test_no_notion_sync_failures_section_when_absent():
    markdown = render_shortlist_markdown([], [])
    assert "## Notion Sync Failures" not in markdown
