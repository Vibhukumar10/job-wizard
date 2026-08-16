from dataclasses import dataclass, field
from pathlib import Path

import yaml

REQUIRED_PROFILE_FIELDS = ("keywords", "location", "work_type", "experience_level")
REQUIRED_TOP_LEVEL_FIELDS = ("relevance_threshold", "max_shortlist", "profiles")


@dataclass(frozen=True)
class SearchProfile:
    keywords: str
    location: str
    work_type: str
    experience_level: str


@dataclass(frozen=True)
class SearchConfig:
    relevance_threshold: float
    max_shortlist: int
    profiles: list[SearchProfile]
    location_preference: list[str] = field(default_factory=list)


def load_search_config(path: Path | str) -> SearchConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Search config not found: {path}")

    raw = yaml.safe_load(path.read_text()) or {}

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in raw:
            raise ValueError(f"Search config is missing required field: {field}")

    if not raw["profiles"]:
        raise ValueError("Search config must define at least one profile in 'profiles'")

    profiles = []
    for i, raw_profile in enumerate(raw["profiles"]):
        for field in REQUIRED_PROFILE_FIELDS:
            if field not in raw_profile:
                raise ValueError(f"Search config profile {i} is missing required field: {field}")
        profiles.append(SearchProfile(**{field: raw_profile[field] for field in REQUIRED_PROFILE_FIELDS}))

    return SearchConfig(
        relevance_threshold=raw["relevance_threshold"],
        max_shortlist=raw["max_shortlist"],
        profiles=profiles,
        location_preference=raw.get("location_preference", []),
    )
