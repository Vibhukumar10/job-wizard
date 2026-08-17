import os
import subprocess
from pathlib import Path

from pypdf import PdfReader


class PdfCompileError(Exception):
    pass


def compile_resume_pdf(tex_path: Path | str, cls_search_dir: Path | str) -> Path:
    """Compile a resume .tex to PDF via pdflatex, same stem/directory as the input.

    pdflatex (not xelatex/tectonic) is required: resume.cls relies on the
    pdfTeX-only \\pdfglyphtounicode primitive (via glyphtounicode.tex) so that
    ligatures extract as correct text — the exact property the ATS keyword
    check depends on. resume.cls lives outside the tailored .tex's directory
    (runs/<date>/resumes/), so cls_search_dir is added to pdflatex's search
    path via TEXINPUTS, which — unlike tectonic — it genuinely honors.
    """
    tex_path = Path(tex_path)
    env = os.environ.copy()
    env["TEXINPUTS"] = f".:{Path(cls_search_dir).resolve()}:" + env.get("TEXINPUTS", "")

    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=tex_path.parent,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PdfCompileError(result.stderr.strip() or result.stdout.strip())

    return tex_path.with_suffix(".pdf")


def check_resume_pdf(pdf_path: Path | str, keywords: list[str]) -> dict[str, object]:
    """Report the compiled PDF's page count and which keywords didn't survive extraction."""
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()

    missing = [kw for kw in keywords if kw.lower() not in text]

    return {"pages": len(reader.pages), "missing_keywords": missing}
