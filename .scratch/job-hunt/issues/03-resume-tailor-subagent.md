# 03 — Resume-tailor subagent

**What to build:** A subagent that, given one job description and the base LaTeX resume, produces a tailored `.tex` copy scoped to that job — editing only the professional summary, skills, and work-experience bullets, updating the location to match the posting, and inserting job-description keywords honestly. Never touches education/achievements or `resume/resume.cls`, and never fabricates employers, titles, dates, degrees, or skills not evidenced in the base resume. Verifiable standalone against a sample job description.

**Blocked by:** 01

**Status:** needs-info

**Note:** requires `resume/main.tex` (and `resume/resume.cls`) to already exist (user-provided; not built by this or any other ticket).

- [x] Accepts a single job description + the base resume as input and produces a tailored `.tex` file named via `resume_filename` (from ticket 01)
- [x] Only the professional summary, skills, and work-experience bullets are modified
- [x] Location is updated everywhere in the resume to match the job posting's location
- [x] Job-description keywords are worked into the resume only where truthful (no fabricated skills, employers, titles, dates, or degrees)
- [x] Education/achievements sections and `resume/resume.cls` are left untouched
- [x] On failure, the subagent invocation is retried once automatically; a second failure is reported as a failure (job + error) rather than raising past the caller
- [ ] Running the subagent standalone against a sample job description produces a correctly scoped tailored `.tex` file

## Comments

Built (2026-08-16): `.claude/agents/resume-tailor.md`. Scoped to summary/skills/work-experience bullets + location, explicit exclusions for education/achievements/resume.cls and fabrication, uses `pipeline.cli resume-filename` for output naming. Not yet verified against a real resume — `resume/main.tex` (user-provided) doesn't exist yet. Run standalone against a sample job description once it does.
