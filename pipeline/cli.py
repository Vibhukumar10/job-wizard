"""Command-line wiring around the pipeline module's pure functions.

Lets the /job-hunt skill and its subagents (which operate via shell commands,
not in-process Python) invoke the tested pipeline functions without
duplicating their logic. Each subcommand reads/writes JSON so callers can
pipe data between steps.
"""

import argparse
import dataclasses
import json
import sys
from typing import Any

from pipeline.batching import batch_jobs
from pipeline.companies import filter_blacklisted_jobs
from pipeline.config import load_search_config
from pipeline.dedup import filter_unseen_jobs
from pipeline.naming import resume_filename
from pipeline.notion_tracker import (
    DATABASE_SCHEMA,
    DATABASE_TITLE,
    build_notion_properties,
    load_tracker_state,
    save_tracker_state,
)
from pipeline.pdf import check_resume_pdf, compile_resume_pdf
from pipeline.seen_jobs import append_seen_jobs, load_seen_jobs
from pipeline.shortlist import render_shortlist_markdown, select_shortlist


def _read_json_arg_or_stdin(value: str | None) -> Any:
    if value is None:
        return json.load(sys.stdin)
    return json.loads(value)


def _cmd_load_config(args: argparse.Namespace) -> None:
    config = load_search_config(args.path)
    print(json.dumps(dataclasses.asdict(config)))


def _cmd_load_seen(args: argparse.Namespace) -> None:
    print(json.dumps(load_seen_jobs(args.path)))


def _cmd_append_seen(args: argparse.Namespace) -> None:
    seen_log = load_seen_jobs(args.path)
    new_jobs = _read_json_arg_or_stdin(args.jobs)
    updated = append_seen_jobs(seen_log, new_jobs, args.path)
    print(json.dumps(updated))


def _cmd_filter_unseen(args: argparse.Namespace) -> None:
    seen_log = load_seen_jobs(args.path)
    jobs = _read_json_arg_or_stdin(args.jobs)
    print(json.dumps(filter_unseen_jobs(jobs, seen_log)))


def _cmd_filter_blacklisted(args: argparse.Namespace) -> None:
    jobs = _read_json_arg_or_stdin(args.jobs)
    blacklist = json.loads(args.companies)
    print(json.dumps(filter_blacklisted_jobs(jobs, blacklist)))


def _cmd_batch(args: argparse.Namespace) -> None:
    jobs = _read_json_arg_or_stdin(args.jobs)
    print(json.dumps(batch_jobs(jobs, size=args.size)))


def _cmd_select_shortlist(args: argparse.Namespace) -> None:
    scored_jobs = _read_json_arg_or_stdin(args.jobs)
    result = select_shortlist(
        scored_jobs,
        relevance_threshold=args.relevance_threshold,
        max_shortlist=args.max_shortlist,
        min_shortlist=args.min_shortlist,
    )
    print(json.dumps(result))


def _cmd_render_shortlist(args: argparse.Namespace) -> None:
    jobs = json.loads(args.jobs) if args.jobs else []
    failures = json.loads(args.failures) if args.failures else []
    notion_failures = json.loads(args.notion_failures) if args.notion_failures else []
    print(render_shortlist_markdown(jobs, failures, notion_failures))


def _cmd_resume_filename(args: argparse.Namespace) -> None:
    print(resume_filename(args.company, args.title))


def _cmd_notion_database_schema(args: argparse.Namespace) -> None:
    print(json.dumps({"title": DATABASE_TITLE, "properties": DATABASE_SCHEMA}))


def _cmd_notion_properties(args: argparse.Namespace) -> None:
    job = json.loads(args.job)
    print(json.dumps(build_notion_properties(job, is_new=args.is_new, today=args.today)))


def _cmd_load_notion_tracker(args: argparse.Namespace) -> None:
    print(json.dumps(load_tracker_state(args.path)))


def _cmd_save_notion_tracker(args: argparse.Namespace) -> None:
    state = save_tracker_state(
        {"database_id": args.database_id, "data_source_id": args.data_source_id}, args.path
    )
    print(json.dumps(state))


def _cmd_compile_resume_pdf(args: argparse.Namespace) -> None:
    pdf_path = compile_resume_pdf(args.tex, args.cls_dir)
    print(json.dumps({"pdf_path": str(pdf_path)}))


def _cmd_check_resume_pdf(args: argparse.Namespace) -> None:
    keywords = json.loads(args.keywords)
    print(json.dumps(check_resume_pdf(args.pdf, keywords)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p = subparsers.add_parser("load-config", help="Parse and validate config/search.yaml")
    p.add_argument("path")
    p.set_defaults(func=_cmd_load_config)

    p = subparsers.add_parser("load-seen", help="Read state/seen-jobs.json")
    p.add_argument("path")
    p.set_defaults(func=_cmd_load_seen)

    p = subparsers.add_parser("append-seen", help="Merge new jobs into the seen-jobs log and persist it")
    p.add_argument("path")
    p.add_argument("--jobs", help="JSON list of {job_id,title,company}; reads stdin if omitted")
    p.set_defaults(func=_cmd_append_seen)

    p = subparsers.add_parser("filter-unseen", help="Drop jobs already present in the seen-jobs log")
    p.add_argument("path")
    p.add_argument("--jobs", help="JSON list of jobs; reads stdin if omitted")
    p.set_defaults(func=_cmd_filter_unseen)

    p = subparsers.add_parser("filter-blacklisted", help="Drop jobs whose company is on the blacklist")
    p.add_argument("--companies", required=True, help="JSON list of blacklisted company names")
    p.add_argument("--jobs", help="JSON list of jobs; reads stdin if omitted")
    p.set_defaults(func=_cmd_filter_blacklisted)

    p = subparsers.add_parser("batch", help="Chunk jobs into concurrency-bounded batches")
    p.add_argument("--size", type=int, default=5)
    p.add_argument("--jobs", help="JSON list of jobs; reads stdin if omitted")
    p.set_defaults(func=_cmd_batch)

    p = subparsers.add_parser("select-shortlist", help="Pick the final shortlist from every scored candidate, backfilling to min_shortlist if needed")
    p.add_argument("--jobs", help="JSON list of stage-2-scored jobs (each with a numeric 'score'); reads stdin if omitted")
    p.add_argument("--relevance-threshold", type=float, required=True)
    p.add_argument("--max-shortlist", type=int, required=True)
    p.add_argument("--min-shortlist", type=int, default=0)
    p.set_defaults(func=_cmd_select_shortlist)

    p = subparsers.add_parser("render-shortlist", help="Render shortlist.md content")
    p.add_argument("--jobs", help="JSON list of shortlisted jobs", default="[]")
    p.add_argument("--failures", help="JSON list of failures", default="[]")
    p.add_argument("--notion-failures", help="JSON list of Notion push failures", default="[]")
    p.set_defaults(func=_cmd_render_shortlist)

    p = subparsers.add_parser("resume-filename", help="Deterministic tailored-resume filename")
    p.add_argument("company")
    p.add_argument("title")
    p.set_defaults(func=_cmd_resume_filename)

    p = subparsers.add_parser("notion-database-schema", help="Print the Job Tracker database title + property schema")
    p.set_defaults(func=_cmd_notion_database_schema)

    p = subparsers.add_parser("notion-properties", help="Shape one job into Notion page properties")
    p.add_argument("--job", required=True, help="JSON object for one shortlisted job (or failure)")
    p.add_argument("--today", required=True, help="Run date, YYYY-MM-DD")
    p.add_argument("--is-new", action="store_true", help="Set Date Shortlisted + Applied=false (first write of this job_id)")
    p.set_defaults(func=_cmd_notion_properties)

    p = subparsers.add_parser("load-notion-tracker", help="Read state/notion-tracker.json")
    p.add_argument("path")
    p.set_defaults(func=_cmd_load_notion_tracker)

    p = subparsers.add_parser("save-notion-tracker", help="Persist the created Job Tracker database_id + data_source_id")
    p.add_argument("path")
    p.add_argument("--database-id", required=True)
    p.add_argument("--data-source-id", required=True, help="collection://... id, needed to query/create pages")
    p.set_defaults(func=_cmd_save_notion_tracker)

    p = subparsers.add_parser("compile-resume-pdf", help="Compile a tailored .tex resume to PDF via pdflatex")
    p.add_argument("--tex", required=True, help="Path to the tailored .tex file")
    p.add_argument("--cls-dir", default="resume", help="Directory containing resume.cls (default: resume)")
    p.set_defaults(func=_cmd_compile_resume_pdf)

    p = subparsers.add_parser("check-resume-pdf", help="Check a compiled resume PDF's page count and keyword coverage")
    p.add_argument("--pdf", required=True, help="Path to the compiled PDF")
    p.add_argument("--keywords", required=True, help="JSON list of keywords that must appear in the extracted text")
    p.set_defaults(func=_cmd_check_resume_pdf)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
