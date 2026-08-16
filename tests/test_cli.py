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
