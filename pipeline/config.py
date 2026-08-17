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
    target_companies: list[str] = field(default_factory=list)
    wider_net_companies: list[str] = field(default_factory=list)
    blacklist_companies: list[str] = field(default_factory=list)
    max_years_experience: float | None = None
    min_shortlist: int = 0


def _expand_wider_net_profiles(
    companies: list[str], profiles: list[SearchProfile], location_preference: list[str]
) -> list[SearchProfile]:
    """Auto-generate the remote + per-city profile shape for each wider-net company.

    Mirrors the base profile's keywords/experience_level (search_jobs has no
    company filter, so the company name is folded into keywords instead).
    """
    if not companies:
        return []

    base_keywords = profiles[0].keywords
    base_experience_level = profiles[0].experience_level

    expanded = []
    for company in companies:
        keywords = f"{base_keywords} {company}"
        expanded.append(
            SearchProfile(keywords=keywords, location="Remote", work_type="remote", experience_level=base_experience_level)
        )
        for city in location_preference:
            expanded.append(
                SearchProfile(keywords=keywords, location=city, work_type="on_site,hybrid", experience_level=base_experience_level)
            )
    return expanded


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

    location_preference = raw.get("location_preference", [])
    target_companies = raw.get("target_companies", [])
    wider_net_companies = raw.get("wider_net_companies", [])
    blacklist_companies = raw.get("blacklist_companies", [])

    unknown_wider_net = set(wider_net_companies) - set(target_companies)
    if unknown_wider_net:
        raise ValueError(
            f"Search config's wider_net_companies must be a subset of target_companies, "
            f"found companies not in target_companies: {sorted(unknown_wider_net)}"
        )

    profiles = profiles + _expand_wider_net_profiles(wider_net_companies, profiles, location_preference)

    min_shortlist = raw.get("min_shortlist", 0)
    if min_shortlist > raw["max_shortlist"]:
        raise ValueError(
            f"Search config's min_shortlist ({min_shortlist}) cannot exceed max_shortlist ({raw['max_shortlist']})"
        )

    return SearchConfig(
        relevance_threshold=raw["relevance_threshold"],
        max_shortlist=raw["max_shortlist"],
        profiles=profiles,
        location_preference=location_preference,
        target_companies=target_companies,
        wider_net_companies=wider_net_companies,
        blacklist_companies=blacklist_companies,
        max_years_experience=raw.get("max_years_experience"),
        min_shortlist=min_shortlist,
    )
