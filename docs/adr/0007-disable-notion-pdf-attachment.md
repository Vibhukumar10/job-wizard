# Stop uploading Resume PDFs to the Notion Job Tracker

[ADR 0003](0003-resume-pdf-generation.md) added a `Resume PDF` Files column to the Job Tracker, attached via a three-call Notion MCP dance per PDF-bearing job: `notion-create-file-upload` + a `curl` upload, a `notion-create-pages` call embedding the file in page content to mint a usable attachment reference, then a `notion-fetch` + `notion-update-page` to set the `Resume PDF` property from that reference. On a full run this multiplies Notion tool calls by roughly 3x per PDF-bearing job, on top of `notion-query-data-sources` and the once-per-run schema-migration check (fetch the data source, `ADD COLUMN` if `Resume PDF` was missing) that existed solely to support it. The user asked to disable the feature outright to cut this cost — the Job Tracker's job is to be a cross-run status board, not a resume file store; `shortlist.md`'s `resume_path` column already points at the same PDF (or the `.tex` fallback on `pdf_error`) on disk.

We removed `Resume PDF` from `DATABASE_SCHEMA` (`pipeline/notion_tracker.py`) and dropped the `resume_pdf_file_id` branch from `build_notion_properties`, so a fresh database created by `notion-database-schema` never gets the column, and no job's properties ever reference a PDF file. `/job-hunt`'s step 6 in `SKILL.md` lost the file-upload sub-step and the "does this existing database need the column added" check entirely — every job, PDF or not, now goes through a single create-or-update call built from `notion-properties`, matching what a `pdf_error` job's Notion write already looked like before this change.

This only touches the *upload* path. `resume-packager` still compiles and ATS-validates a PDF per job (ADR 0003's other half, and the reason `pdflatex` stays a hard dependency) — that PDF just never leaves the local `runs/<date>/resumes/` directory into Notion.

## Considered options

- **Keep the column but stop populating it going forward** — rejected: leaves dead schema and a half-supported code path (`build_notion_properties` still branching on a field nothing ever sets) for no benefit; a clean removal is simpler to reason about.
- **Drop the `Resume PDF` column from the user's live database** (via `notion-update-data-source ... DROP COLUMN`) — rejected: destructive to already-existing Notion data (rows from prior runs carry real attached PDFs); this ADR disables new uploads, it doesn't retroactively delete anything the user already has in their workspace. If the user wants the column gone too, that's a separate, explicit action.
- **Make PDF upload conditional/configurable** (a `search.yaml` toggle) — rejected as unnecessary: nothing else in the pipeline needs both states, and an unused toggle is its own maintenance cost; if the user wants it back, re-adding the ADR 0003 flow is straightforward since it's fully documented there.

## Consequences

- Every Notion push for a run now costs exactly one `notion-query-data-sources` + one `notion-create-pages`/`notion-update-page` call per job, regardless of whether that job has a PDF — down from up to three extra calls per PDF-bearing job.
- The Job Tracker no longer shows a resume file inline in Notion; reaching a job's tailored resume means opening `shortlist.md` (or the run's `resumes/` folder) instead of the Notion row.
- Pre-existing Job Tracker rows created before this change keep whatever `Resume PDF` attachment they already have — this ADR stops new uploads, it doesn't touch history.
- `docs/adr/0003-resume-pdf-generation.md` is now partially superseded: its PDF-generation rationale (pdflatex vs. tectonic, ATS keyword check, etc.) still holds; its Notion-attachment section (the three-call upload flow) no longer reflects current behavior.
