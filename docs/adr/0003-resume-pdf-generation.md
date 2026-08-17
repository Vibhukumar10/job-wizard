# Resume PDF generation via deterministic compile + bounded LLM retry; Notion attachment via MCP file upload

> **Partially superseded by [ADR 0007](0007-disable-notion-pdf-attachment.md):** the PDF generation/ATS-check rationale below still holds, but the Notion attachment flow it describes (the `Resume PDF` column, the three-call upload dance) was removed — Resume PDFs are no longer uploaded to the Job Tracker.

The original spec explicitly deferred this: "Output: a `.tex` file only. No PDF compilation in this version." It also named ATS keyword matching as a goal ("relevant keywords... so that I score better against ATS keyword matching") without ever building a check for it — the only existing ATS behavior was `resume-tailor` inserting keywords honestly, with nothing verifying they survive into a submittable document. No LaTeX engine was installed locally.

We added a new `resume-packager` subagent, dispatched per job immediately after `resume-tailor` succeeds, within the same batch wave. Compilation and validation are deterministic `pipeline/` functions the subagent shells out to via `pipeline/cli.py`; its only LLM judgment is a single bounded retry — editing the `.tex` (fixing a compile error, or trimming content that overran one page) and recompiling once — before giving up.

`pdflatex` (via BasicTeX, installed with Homebrew) is the compile engine — not `tectonic`, despite that being the initial choice. A smoke test against a real tailored resume showed `tectonic` cannot compile `resume.cls` at all: it relies on the pdfTeX-only `\pdfglyphtounicode` primitive (via `glyphtounicode.tex`) to make ligatures extract as correct text, which `main.tex`'s own header already documents ("Compile with: pdflatex resume.tex — pdfLaTeX, NOT XeLaTeX — keeps glyphtounicode"). `tectonic` runs a XeTeX-based engine and doesn't have that primitive at all — not a missing package, a structural incompatibility. This is exactly the mechanism the ATS check depends on, so silently degrading it (or editing `resume.cls` to route around it) would have undermined the feature this ADR exists to add.

The keyword list an ATS check verifies against comes from `resume-tailor`'s own output — the terms it actually, honestly inserted — not an independently extracted list. `/job-hunt` checks `pdflatex` is on `PATH` once at the start of the run, failing loudly rather than letting every job discover the same missing binary independently.

On unrecoverable failure the job stays in the run with a `pdf_error` noted; the `.tex` remains the fallback resume artifact. The PDF lands at `runs/<date>/resumes/<filename>.pdf` — same stem as the `.tex`, same directory — and both `shortlist.md`'s Resume column and the new Notion "Resume PDF" column prefer it, falling back to the `.tex` path on `pdf_error`.

The Job Tracker gains one column, `Resume PDF` (Files & media), attached via the Notion MCP connector's file-upload flow — consistent with [ADR 0001](0001-notion-job-tracker.md)'s rule that Notion API calls live in the orchestration step, not `pipeline/`. Because a live Job Tracker database already exists (created before this feature), `/job-hunt` checks its schema once per run and adds the missing column via `notion-update-data-source` rather than assuming a fresh `create`.

The upload flow needed one more step than the tool docs implied, discovered on the first live run: a freshly uploaded file's id (from `notion-create-file-upload`) is not directly usable as a Files-property value. It first has to be attached to some page's *content* (`<pdf src="file-upload://...">`), and that page then fetched to read back the real `attachment:<uuid>:<filename>` reference the property actually accepts. So a PDF-bearing job's Notion page is created once (properties minus `Resume PDF`, content holding the PDF embed), fetched to mint the attachment reference, then updated to set `Resume PDF` — three calls instead of one. A job without a PDF still creates in a single call.

## Considered options

- **`tectonic`** — rejected: cannot compile `resume.cls` at all (see above). Not fixable via configuration; it's a different, incompatible TeX engine.
- **Full MacTeX/TeX Live** instead of BasicTeX — rejected: ~4GB install when BasicTeX's much smaller pdfTeX distribution compiles this document just as correctly.
- **Hosted LaTeX-compile API** — rejected: sends resume content to a third party and adds a network dependency the rest of the pipeline doesn't have.
- **Independent deterministic keyword extraction** for the ATS check (parsing the raw job description directly) — rejected: would flag keywords `resume-tailor` deliberately and honestly left out, causing retries that fix nothing.
- **Dropping a job from the shortlist** on unrecoverable PDF failure — rejected: throws away a working `.tex` resume over a packaging problem unrelated to the job's actual relevance.
- **Only supporting Notion attachment on freshly-created databases** — rejected: the user's Job Tracker database already exists; silently no-op'ing the new column for existing users isn't acceptable.

## Consequences

- New system dependency: `pdflatex` (via `brew install --cask basictex`) must be installed wherever `/job-hunt` runs, including the unattended 7am schedule — an environment precondition alongside the existing `resume/main.tex` requirement. BasicTeX's cask installer needs an interactive `sudo` prompt, so this is a manual, one-time setup step — not something `/job-hunt` can install on its own behalf.
- `resume-tailor`'s output changes from a bare path string to a small JSON object (`resume_path` + `keywords`) — a breaking change to its contract, but its only consumer is `/job-hunt`'s orchestration step, updated in the same change.
- Tailored `.tex` files live in `runs/<date>/resumes/`, separate from `resume/resume.cls` — `pipeline/pdf.py` points `pdflatex` at `resume/` via `TEXINPUTS`, which (unlike `tectonic`) it genuinely honors, rather than requiring a copy of `resume.cls` alongside every tailored file.
- New Python dependency: `pypdf`, for page/text extraction during the ATS and page-count checks.
