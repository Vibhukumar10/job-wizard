import re

from pipeline.shortlist import render_shortlist_markdown


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

    assert "| Title | Company | Location | Score | Apply Link | Resume |" in markdown
    assert "| Backend Engineer | Acme Corp | Remote - US | 8.5 | https://linkedin.com/jobs/1 | resumes/acme-corp-backend-engineer.tex |" in markdown
    assert "## Failures" not in markdown


def test_renders_failures_section_when_present():
    failures = [{"title": "Staff Engineer", "company": "Globex", "error": "tailoring failed twice: timeout"}]

    markdown = render_shortlist_markdown([], failures)

    assert "## Failures" in markdown
    assert "Staff Engineer" in markdown
    assert "Globex" in markdown
    assert "tailoring failed twice: timeout" in markdown


def test_empty_jobs_and_failures_still_renders_header():
    markdown = render_shortlist_markdown([], [])
    assert "| Title | Company | Location | Score | Apply Link | Resume |" in markdown


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
    assert unescaped_delimiters == 7  # 6 cells -> 7 delimiters, once the literal pipe is escaped
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
