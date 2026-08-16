import pytest

from pipeline.batching import batch_jobs


def test_chunks_jobs_into_groups_of_default_size_five():
    jobs = list(range(12))
    batches = batch_jobs(jobs)
    assert batches == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11]]


def test_chunks_jobs_into_groups_of_given_size():
    jobs = list(range(7))
    batches = batch_jobs(jobs, size=3)
    assert batches == [[0, 1, 2], [3, 4, 5], [6]]


def test_empty_input_produces_no_batches():
    assert batch_jobs([]) == []


def test_zero_or_negative_size_raises():
    with pytest.raises(ValueError, match="positive"):
        batch_jobs([1, 2, 3], size=0)
    with pytest.raises(ValueError, match="positive"):
        batch_jobs([1, 2, 3], size=-1)
