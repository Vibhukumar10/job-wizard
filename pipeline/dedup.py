from typing import Any


def filter_unseen_jobs(jobs: list[dict[str, Any]], seen_log: dict[str, Any]) -> list[dict[str, Any]]:
    unseen = []
    for i, job in enumerate(jobs):
        if "job_id" not in job:
            raise ValueError(f"job at index {i} is missing required field: job_id")
        if job["job_id"] not in seen_log:
            unseen.append(job)
    return unseen
