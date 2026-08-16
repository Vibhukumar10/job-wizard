import re


def resume_filename(company: str, title: str) -> str:
    slug = f"{company}-{title}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"{slug}.tex"
