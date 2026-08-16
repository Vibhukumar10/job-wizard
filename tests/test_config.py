import pytest

from pipeline.config import SearchConfig, SearchProfile, load_search_config

VALID_YAML = """
relevance_threshold: 7.5
max_shortlist: 50
profiles:
  - keywords: "Backend Engineer"
    location: "United States"
    work_type: "remote"
    experience_level: "mid-senior"
"""


def test_parses_valid_config(tmp_path):
    path = tmp_path / "search.yaml"
    path.write_text(VALID_YAML)

    config = load_search_config(path)

    assert config == SearchConfig(
        relevance_threshold=7.5,
        max_shortlist=50,
        profiles=[
            SearchProfile(
                keywords="Backend Engineer",
                location="United States",
                work_type="remote",
                experience_level="mid-senior",
            )
        ],
    )


def test_raises_on_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_search_config(tmp_path / "does-not-exist.yaml")


def test_raises_on_missing_required_top_level_field(tmp_path):
    path = tmp_path / "search.yaml"
    path.write_text("max_shortlist: 50\nprofiles: []\n")

    with pytest.raises(ValueError, match="relevance_threshold"):
        load_search_config(path)


def test_raises_on_missing_required_profile_field(tmp_path):
    path = tmp_path / "search.yaml"
    path.write_text(
        """
relevance_threshold: 7.5
max_shortlist: 50
profiles:
  - keywords: "Backend Engineer"
    location: "United States"
    work_type: "remote"
"""
    )

    with pytest.raises(ValueError, match="experience_level"):
        load_search_config(path)


def test_raises_on_empty_profiles_list(tmp_path):
    path = tmp_path / "search.yaml"
    path.write_text("relevance_threshold: 7.5\nmax_shortlist: 50\nprofiles: []\n")

    with pytest.raises(ValueError, match="profiles"):
        load_search_config(path)
