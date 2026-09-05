import re


def resume_filename(company: str, job_id: str) -> str:
    """Deterministic tailored-resume filename: <company-slug>-<job_id>.tex.

    Keyed on job_id rather than the job title so a filename is unambiguous:
    two postings at the same company with the same title (Amazon runs several)
    would otherwise collide, and the id is the same key jobs.json, tailored.json
    and the Job Tracker use.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    return f"{slug}-{job_id}.tex"
