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

Built (2026-08-16): `.claude/agents/resume-tailor.md`. Scoped to summary/skills/work-experience bullets + location, explicit exclusions for education/achievements/resume.cls and fabrication, uses `pipeline.cli resume-filename` for output naming.

Live-verified the same day: tailored `resume/main.tex` for the Chime shortlisted job from ticket 02's verification (manually, following the subagent's own instructions — the `resume-tailor` custom agent type isn't picked up by the Agent tool until the session restarts). Output at `runs/2026-08-16/resumes/chime-software-engineer-infrastructure.tex`: summary/skills/bullets reworded and reordered toward infra keywords (Terraform, Kubernetes, Ansible), location updated to the posting's, education/achievements/resume.cls untouched, no fabricated skills (AWS was already present in the base resume's skills list, so keeping it in the tailored version is not a fabrication).
