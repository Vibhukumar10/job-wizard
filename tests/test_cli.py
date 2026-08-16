import json

from pipeline.cli import main


def test_resume_filename_command(capsys):
    main(["resume-filename", "Acme Corp", "Backend Engineer"])
    assert capsys.readouterr().out.strip() == "acme-corp-backend-engineer.tex"


def test_load_config_command(tmp_path, capsys):
    path = tmp_path / "search.yaml"
    path.write_text(
        "relevance_threshold: 7.5\nmax_shortlist: 50\n"
        "profiles:\n  - keywords: Eng\n    location: US\n    work_type: remote\n    experience_level: mid\n"
    )

    main(["load-config", str(path)])

    parsed = json.loads(capsys.readouterr().out)
    assert parsed["relevance_threshold"] == 7.5
    assert parsed["max_shortlist"] == 50
    assert parsed["profiles"] == [
        {"keywords": "Eng", "location": "US", "work_type": "remote", "experience_level": "mid"}
    ]


def test_filter_unseen_command_reads_jobs_flag(tmp_path, capsys):
    seen_path = tmp_path / "seen-jobs.json"
    seen_path.write_text(json.dumps({"1": {"first_seen_date": "2026-08-01", "title": "A", "company": "Acme"}}))
    jobs = json.dumps([{"job_id": "1"}, {"job_id": "2"}])

    main(["filter-unseen", str(seen_path), "--jobs", jobs])

    assert json.loads(capsys.readouterr().out) == [{"job_id": "2"}]


def test_append_seen_command_persists_to_disk(tmp_path, capsys):
    seen_path = tmp_path / "seen-jobs.json"
    new_jobs = json.dumps([{"job_id": "1", "title": "A", "company": "Acme"}])

    main(["append-seen", str(seen_path), "--jobs", new_jobs])
    capsys.readouterr()

    on_disk = json.loads(seen_path.read_text())
    assert on_disk["1"]["title"] == "A"


def test_batch_command(capsys):
    jobs = json.dumps([1, 2, 3, 4, 5, 6])

    main(["batch", "--size", "5", "--jobs", jobs])

    assert json.loads(capsys.readouterr().out) == [[1, 2, 3, 4, 5], [6]]


def test_render_shortlist_command(capsys):
    jobs = json.dumps(
        [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "Remote",
                "score": 8.0,
                "apply_link": "https://x/1",
                "resume_path": "resumes/a.tex",
            }
        ]
    )

    main(["render-shortlist", "--jobs", jobs])

    assert "Backend Engineer" in capsys.readouterr().out


def test_render_shortlist_command_includes_notion_failures(capsys):
    notion_failures = json.dumps([{"title": "Staff Eng", "company": "Initech", "error": "rate limited"}])

    main(["render-shortlist", "--notion-failures", notion_failures])

    out = capsys.readouterr().out
    assert "## Notion Sync Failures" in out
    assert "Initech" in out


def test_notion_database_schema_command(capsys):
    main(["notion-database-schema"])

    parsed = json.loads(capsys.readouterr().out)
    assert parsed["title"] == "Job Search Tracker"
    assert parsed["properties"]["Applied"] == {"checkbox": {}}
    assert parsed["properties"]["Job ID"] == {"rich_text": {}}


def test_notion_properties_command_new_job(capsys):
    job = json.dumps(
        {
            "job_id": "1",
            "title": "Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "score": 8.0,
            "apply_link": "https://x/1",
        }
    )

    main(["notion-properties", "--job", job, "--today", "2026-08-16", "--is-new"])

    parsed = json.loads(capsys.readouterr().out)
    assert parsed["date:Date Shortlisted:start"] == "2026-08-16"
    assert parsed["Applied"] == "__NO__"


def test_notion_properties_command_existing_job_omits_immutable_fields(capsys):
    job = json.dumps(
        {
            "job_id": "1",
            "title": "Backend Engineer",
            "company": "Acme",
            "location": "Remote",
            "score": 8.0,
            "apply_link": "https://x/1",
        }
    )

    main(["notion-properties", "--job", job, "--today", "2026-08-16"])

    parsed = json.loads(capsys.readouterr().out)
    assert "date:Date Shortlisted:start" not in parsed
    assert "Applied" not in parsed


def test_save_and_load_notion_tracker_commands(tmp_path, capsys):
    path = tmp_path / "notion-tracker.json"

    main(["save-notion-tracker", str(path), "--database-id", "db123", "--data-source-id", "collection://ds123"])
    capsys.readouterr()

    main(["load-notion-tracker", str(path)])
    assert json.loads(capsys.readouterr().out) == {"database_id": "db123", "data_source_id": "collection://ds123"}
