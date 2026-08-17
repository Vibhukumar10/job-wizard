import re
from typing import Any

_CORP_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "llc", "ltd", "co", "plc", "gmbh"}


def normalize_company_name(name: str) -> str:
    normalized = re.sub(r"[.,]", "", name.strip().lower())
    words = normalized.split()
    while words and words[-1] in _CORP_SUFFIXES:
        words.pop()
    return " ".join(words)


def filter_blacklisted_jobs(jobs: list[dict[str, Any]], blacklist: list[str]) -> list[dict[str, Any]]:
    normalized_blacklist = {normalize_company_name(company) for company in blacklist}
    if not normalized_blacklist:
        return list(jobs)

    kept = []
    for i, job in enumerate(jobs):
        if "company" not in job:
            raise ValueError(f"job at index {i} is missing required field: company")
        if normalize_company_name(job["company"]) not in normalized_blacklist:
            kept.append(job)
    return kept
