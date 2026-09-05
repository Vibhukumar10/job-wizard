"""The cheap half of the resume-quality check.

Ticket 02 of the job-hunt speedup map split quality checking in two: deterministic
proxies that run every time (here), and a regenerate-and-compare pass that needs
agent invocations and therefore can't live in a unit test suite
(`scripts/compare_golden.py`).

What this file guards is narrow but real: that `resume/resume.cls` and the
pdflatex toolchain still compile every reference resume to exactly one page. It
is blind to whether the prose is any good — that is the point, and why it isn't
the whole story.
"""

import json
import shutil
from pathlib import Path

import pytest

from pipeline.pdf import check_resume_pdf, compile_resume_pdf

GOLDEN = Path(__file__).parent / "fixtures" / "golden"
MANIFEST = json.loads((GOLDEN / "manifest.json").read_text())
CLS_DIR = Path(__file__).parent.parent / "resume"

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="pdflatex not installed; the golden set's compile checks need it",
)


def _slugs():
    return [job["slug"] for job in MANIFEST["jobs"]]


def test_manifest_covers_a_spread_of_scores():
    """A corpus clustered at one score would not exercise the tailoring range."""
    scores = [job["score"] for job in MANIFEST["jobs"]]

    assert len(scores) >= 5
    assert max(scores) - min(scores) >= 2.0


def test_manifest_includes_the_pdf_error_case():
    """The failure path needs covering too, not just the happy one."""
    assert any(job["pdf_error"] for job in MANIFEST["jobs"])


@pytest.mark.parametrize("slug", _slugs())
def test_every_job_has_a_description_and_a_reference(slug):
    assert (GOLDEN / "jobs" / f"{slug}.md").is_file()
    assert (GOLDEN / "reference" / f"{slug}.tex").is_file()


def test_base_resume_is_present():
    assert (GOLDEN / "reference" / "BASE-main.tex").is_file()


@pytest.mark.parametrize("slug", _slugs())
def test_reference_resume_compiles_to_exactly_one_page(slug, tmp_path):
    """Guards resume.cls and the pdflatex toolchain, independent of the pipeline.

    Compiled in a temp copy so the fixture directory never accumulates build
    artifacts (.aux/.log/.out/.pdf).
    """
    tex = tmp_path / f"{slug}.tex"
    tex.write_text((GOLDEN / "reference" / f"{slug}.tex").read_text())

    pdf = compile_resume_pdf(tex, CLS_DIR)
    result = check_resume_pdf(pdf, [])

    assert result["pages"] == 1
