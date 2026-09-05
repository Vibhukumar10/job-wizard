import json

import pytest

from pipeline.run_store import (
    AmbiguousJobQueryError,
    JobsNotReadyError,
    STALE_TMP_AFTER_SECONDS,
    age_out_warning,
    jobs_path,
    pending_jobs,
    read_jobs,
    read_tailored,
    record_tailored,
    resolve_job,
    run_status,
    select_eager,
    write_jobs,
)


def _job(job_id, *, company="Acme", title="Engineer", score=7.0):
    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": "Remote",
        "score": score,
        "apply_link": f"https://example.com/{job_id}",
        "description": "...",
        "backfilled": False,
    }


def test_write_jobs_publishes_atomically_and_leaves_no_tmp(tmp_path):
    run_dir = tmp_path / "2026-09-05"

    write_jobs(run_dir, [_job("1")], run_date="2026-09-05")

    assert jobs_path(run_dir).exists()
    assert not jobs_path(run_dir).with_suffix(".json.tmp").exists()
    assert json.loads(jobs_path(run_dir).read_text())["run_date"] == "2026-09-05"


def test_run_status_missing_when_nothing_written(tmp_path):
    assert run_status(tmp_path / "2026-09-05") == "missing"


def test_run_status_complete_after_write(tmp_path):
    run_dir = tmp_path / "2026-09-05"
    write_jobs(run_dir, [_job("1")], run_date="2026-09-05")

    assert run_status(run_dir) == "complete"


def test_run_status_in_flight_while_tmp_is_fresh(tmp_path):
    run_dir = tmp_path / "2026-09-05"
    run_dir.mkdir()
    jobs_path(run_dir).with_suffix(".json.tmp").write_text("{}")

    assert run_status(run_dir) == "in_flight"


def test_run_status_treats_stale_tmp_as_missing(tmp_path):
    """A search that died mid-write must not wedge the tailor phase forever."""
    run_dir = tmp_path / "2026-09-05"
    run_dir.mkdir()
    tmp = jobs_path(run_dir).with_suffix(".json.tmp")
    tmp.write_text("{}")

    future = tmp.stat().st_mtime + STALE_TMP_AFTER_SECONDS + 1

    assert run_status(run_dir, now=future) == "missing"


def test_read_jobs_refuses_an_incomplete_run(tmp_path):
    run_dir = tmp_path / "2026-09-05"
    run_dir.mkdir()
    jobs_path(run_dir).with_suffix(".json.tmp").write_text("{}")

    with pytest.raises(JobsNotReadyError):
        read_jobs(run_dir)


def test_select_eager_takes_highest_scores_only(tmp_path):
    jobs = [_job(str(i), score=float(i)) for i in range(10)]

    result = select_eager(jobs, 3)

    assert [j["job_id"] for j in result] == ["9", "8", "7"]


def test_select_eager_handles_fewer_jobs_than_requested():
    assert len(select_eager([_job("1")], 8)) == 1


def test_resolve_job_by_exact_id():
    jobs = [_job("111"), _job("222")]

    assert resolve_job(jobs, "222")["job_id"] == "222"


def test_resolve_job_by_company_fragment_case_insensitively():
    jobs = [_job("1", company="Adobe"), _job("2", company="Akamai")]

    assert resolve_job(jobs, "adob")["job_id"] == "1"


def test_resolve_job_raises_when_fragment_is_ambiguous():
    jobs = [_job("1", company="Adobe"), _job("2", company="Adobe")]

    with pytest.raises(AmbiguousJobQueryError):
        resolve_job(jobs, "Adobe")


def test_resolve_job_prefers_exact_id_over_fragment():
    """A job_id that also appears inside another job's title must not go ambiguous."""
    jobs = [_job("777"), _job("1", title="Engineer 777 Platform")]

    assert resolve_job(jobs, "777")["job_id"] == "777"


def test_resolve_job_raises_keyerror_when_nothing_matches():
    with pytest.raises(KeyError):
        resolve_job([_job("1")], "nope")


def test_record_tailored_merges_rather_than_replacing(tmp_path):
    run_dir = tmp_path / "2026-09-05"
    run_dir.mkdir()

    record_tailored(run_dir, "1", {"tex_path": "a.tex"})
    record_tailored(run_dir, "2", {"tex_path": "b.tex"})

    assert set(read_tailored(run_dir)) == {"1", "2"}


def test_read_tailored_is_empty_before_any_tailoring(tmp_path):
    assert read_tailored(tmp_path) == {}


def test_pending_excludes_already_tailored_jobs(tmp_path):
    run_dir = tmp_path / "2026-09-05"
    write_jobs(run_dir, [_job("1"), _job("2")], run_date="2026-09-05")
    record_tailored(run_dir, "1", {"tex_path": "a.tex"})

    pending = pending_jobs(tmp_path, today="2026-09-05")

    assert [j["job_id"] for j in pending] == ["2"]


def test_pending_ignores_runs_outside_the_window(tmp_path):
    write_jobs(tmp_path / "2026-08-01", [_job("old")], run_date="2026-08-01")
    write_jobs(tmp_path / "2026-09-05", [_job("new")], run_date="2026-09-05")

    pending = pending_jobs(tmp_path, today="2026-09-05")

    assert [j["job_id"] for j in pending] == ["new"]


def test_pending_ignores_dry_run_folders(tmp_path):
    write_jobs(tmp_path / "2026-09-05-dryrun", [_job("dry")], run_date="2026-09-05")

    assert pending_jobs(tmp_path, today="2026-09-05") == []


def test_pending_ignores_incomplete_runs(tmp_path):
    run_dir = tmp_path / "2026-09-05"
    run_dir.mkdir()
    jobs_path(run_dir).with_suffix(".json.tmp").write_text("{}")

    assert pending_jobs(tmp_path, today="2026-09-05") == []


def test_pending_returns_empty_when_runs_root_absent(tmp_path):
    assert pending_jobs(tmp_path / "nope") == []


def test_pending_marks_the_oldest_run_as_expiring_first(tmp_path):
    write_jobs(tmp_path / "2026-08-30", [_job("oldest")], run_date="2026-08-30")
    write_jobs(tmp_path / "2026-09-05", [_job("newest")], run_date="2026-09-05")

    pending = {j["job_id"]: j["days_left"] for j in pending_jobs(tmp_path, today="2026-09-05")}

    assert pending["oldest"] == 1
    assert pending["newest"] == 7


def test_age_out_warning_is_silent_when_nothing_is_expiring():
    assert age_out_warning([{**_job("1"), "days_left": 5}]) is None


def test_age_out_warning_names_the_expiring_jobs():
    pending = [{**_job("1", company="Adobe"), "days_left": 1}]

    warning = age_out_warning(pending)

    assert warning is not None
    assert "Adobe" in warning
