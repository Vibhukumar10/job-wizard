from unittest.mock import MagicMock, patch

import pytest

from pipeline.pdf import PdfCompileError, check_resume_pdf, compile_resume_pdf


def test_compile_resume_pdf_returns_pdf_path_on_success(tmp_path):
    tex_path = tmp_path / "acme-backend-engineer.tex"
    tex_path.write_text("\\documentclass{resume}")

    with patch("pipeline.pdf.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        pdf_path = compile_resume_pdf(tex_path, tmp_path / "resume")

    assert pdf_path == tex_path.with_suffix(".pdf")


def test_compile_resume_pdf_sets_texinputs_to_cls_dir(tmp_path):
    tex_path = tmp_path / "acme-backend-engineer.tex"
    tex_path.write_text("\\documentclass{resume}")
    cls_dir = tmp_path / "resume"

    with patch("pipeline.pdf.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        compile_resume_pdf(tex_path, cls_dir)

    called_env = mock_run.call_args.kwargs["env"]
    assert str(cls_dir.resolve()) in called_env["TEXINPUTS"]


def test_compile_resume_pdf_raises_with_stderr_on_failure(tmp_path):
    tex_path = tmp_path / "acme-backend-engineer.tex"
    tex_path.write_text("\\documentclass{resume}")

    with patch("pipeline.pdf.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="! Undefined control sequence.", stdout="")
        with pytest.raises(PdfCompileError, match="Undefined control sequence"):
            compile_resume_pdf(tex_path, tmp_path / "resume")


class _FakePage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class _FakeReader:
    def __init__(self, pages):
        self.pages = pages


def test_check_resume_pdf_reports_page_count_and_no_missing_keywords(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-fake")

    with patch("pipeline.pdf.PdfReader", return_value=_FakeReader([_FakePage("Python AWS Docker")])):
        result = check_resume_pdf(pdf_path, ["Python", "AWS"])

    assert result == {"pages": 1, "missing_keywords": []}


def test_check_resume_pdf_reports_missing_keywords_case_insensitively(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-fake")

    with patch("pipeline.pdf.PdfReader", return_value=_FakeReader([_FakePage("python developer")])):
        result = check_resume_pdf(pdf_path, ["Python", "Kubernetes"])

    assert result["missing_keywords"] == ["Kubernetes"]


def test_check_resume_pdf_counts_multiple_pages(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    pdf_path.write_bytes(b"%PDF-fake")

    with patch("pipeline.pdf.PdfReader", return_value=_FakeReader([_FakePage("a"), _FakePage("b")])):
        result = check_resume_pdf(pdf_path, [])

    assert result["pages"] == 2
