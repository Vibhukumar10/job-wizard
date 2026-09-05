#!/usr/bin/env python3
"""Structural comparison of a freshly tailored resume against its golden reference.

The expensive half of the resume-quality check from ticket 02 of the job-hunt
speedup map. Run it by hand after re-tailoring the golden corpus — that is, after
a change to `resume-tailor`'s prompt, the tailoring model, or `resume/resume.cls`.
The cheap half runs in `tests/test_golden.py` on every test run.

Usage:
    # 1. Re-tailor the five golden jobs into a directory, one .tex per slug,
    #    using tests/fixtures/golden/jobs/<slug>.md as the job description and
    #    tests/fixtures/golden/reference/BASE-main.tex as the base resume.
    # 2. Compare:
    uv run python scripts/compare_golden.py --candidates <dir>

**This compares shape, never prose.** The corpus job descriptions were re-fetched
on 2026-09-05 rather than captured during the 2026-08-18 reference run, and every
posting was marked "Reposted" — so the descriptions have drifted from what
produced the references. Word-for-word diffing would fire constantly on that
drift, and a check that cries wolf is one you learn to ignore.
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.pdf import PdfCompileError, check_resume_pdf, compile_resume_pdf  # noqa: E402

GOLDEN = Path(__file__).parent.parent / "tests" / "fixtures" / "golden"
CLS_DIR = Path(__file__).parent.parent / "resume"

#: A candidate may lose or gain this many bullets against the reference before it
#: counts as a structural change. Tailoring legitimately reorders and merges
#: bullets; wholesale loss is what we're looking for.
BULLET_TOLERANCE = 2


def section_names(tex: str) -> set[str]:
    return set(re.findall(r"\\section\*?\{([^}]*)\}", tex))


def bullet_count(tex: str) -> int:
    return len(re.findall(r"^\s*\\item\b", tex, flags=re.MULTILINE))


def keyword_coverage(tex: str, description: str) -> float:
    """Share of the JD's distinctive terms that appear in the resume.

    Crude by design — it is a relative measure, only ever compared between a
    candidate and its own reference, never read as an absolute score.
    """
    terms = {
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z+#.]{3,}", description)
        if word.lower() not in _STOPWORDS
    }
    if not terms:
        return 0.0
    body = tex.casefold()
    return sum(1 for term in terms if term in body) / len(terms)


_STOPWORDS = {
    "with", "that", "this", "from", "have", "will", "your", "you", "our", "and",
    "the", "for", "are", "their", "they", "them", "into", "across", "about",
    "work", "team", "teams", "role", "make", "more", "than", "what", "when",
    "where", "which", "while", "would", "should", "could", "been", "being",
    "such", "also", "other", "these", "those", "each", "every", "including",
}


def compile_pages(tex_path: Path) -> tuple[int | None, str | None]:
    """Compile in a temp dir so the candidate directory stays clean."""
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / tex_path.name
        scratch.write_text(tex_path.read_text())
        try:
            pdf = compile_resume_pdf(scratch, CLS_DIR)
        except PdfCompileError as exc:
            return None, str(exc).splitlines()[-1] if str(exc) else "compile failed"
        return int(check_resume_pdf(pdf, [])["pages"]), None


def compare_one(slug: str, candidate_path: Path) -> dict:
    reference = (GOLDEN / "reference" / f"{slug}.tex").read_text()
    candidate = candidate_path.read_text()
    description = (GOLDEN / "jobs" / f"{slug}.md").read_text()

    ref_sections, cand_sections = section_names(reference), section_names(candidate)
    ref_bullets, cand_bullets = bullet_count(reference), bullet_count(candidate)
    ref_cov = keyword_coverage(reference, description)
    cand_cov = keyword_coverage(candidate, description)
    pages, compile_error = compile_pages(candidate_path)

    failures = []
    if compile_error:
        failures.append(f"does not compile: {compile_error}")
    elif pages != 1:
        failures.append(f"is {pages} pages, not 1")
    if ref_sections - cand_sections:
        failures.append(f"lost sections: {sorted(ref_sections - cand_sections)}")
    if ref_bullets - cand_bullets > BULLET_TOLERANCE:
        failures.append(f"lost {ref_bullets - cand_bullets} bullets (tolerance {BULLET_TOLERANCE})")
    if cand_cov < ref_cov - 0.05:
        failures.append(f"keyword coverage {cand_cov:.0%} vs reference {ref_cov:.0%}")

    return {
        "slug": slug,
        "pages": pages,
        "sections": len(cand_sections),
        "bullets": f"{cand_bullets} (ref {ref_bullets})",
        "coverage": f"{cand_cov:.0%} (ref {ref_cov:.0%})",
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates",
        required=True,
        type=Path,
        help="Directory of freshly tailored <slug>.tex files",
    )
    parser.add_argument("--json", action="store_true", help="Emit raw JSON")
    args = parser.parse_args()

    if shutil.which("pdflatex") is None:
        print("pdflatex not found — install it before running this comparison.", file=sys.stderr)
        return 2

    manifest = json.loads((GOLDEN / "manifest.json").read_text())
    results, missing = [], []
    for job in manifest["jobs"]:
        candidate = args.candidates / f"{job['slug']}.tex"
        if not candidate.is_file():
            missing.append(job["slug"])
            continue
        results.append(compare_one(job["slug"], candidate))

    if args.json:
        print(json.dumps({"results": results, "missing": missing}, indent=2))
    else:
        for r in results:
            mark = "FAIL" if r["failures"] else "ok  "
            print(f"{mark} {r['slug']}")
            print(f"       pages={r['pages']}  bullets={r['bullets']}  coverage={r['coverage']}")
            for failure in r["failures"]:
                print(f"       - {failure}")
        for slug in missing:
            print(f"MISS {slug} — no candidate .tex found")

    failed = [r for r in results if r["failures"]]
    if failed or missing:
        print(f"\n{len(failed)} regression(s), {len(missing)} missing.", file=sys.stderr)
        return 1
    print(f"\nAll {len(results)} candidates structurally match their references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
