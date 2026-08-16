from typing import TypeVar

T = TypeVar("T")


def batch_jobs(jobs: list[T], size: int = 5) -> list[list[T]]:
    if size <= 0:
        raise ValueError(f"batch size must be positive, got {size}")
    return [jobs[i : i + size] for i in range(0, len(jobs), size)]
