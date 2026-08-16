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
from pipeline.config import load_search_config
from pipeline.dedup import filter_unseen_jobs
from pipeline.naming import resume_filename
from pipeline.seen_jobs import append_seen_jobs, load_seen_jobs
from pipeline.shortlist import render_shortlist_markdown


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


def _cmd_batch(args: argparse.Namespace) -> None:
    jobs = _read_json_arg_or_stdin(args.jobs)
    print(json.dumps(batch_jobs(jobs, size=args.size)))


def _cmd_render_shortlist(args: argparse.Namespace) -> None:
    jobs = json.loads(args.jobs) if args.jobs else []
    failures = json.loads(args.failures) if args.failures else []
    print(render_shortlist_markdown(jobs, failures))


def _cmd_resume_filename(args: argparse.Namespace) -> None:
    print(resume_filename(args.company, args.title))


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

    p = subparsers.add_parser("batch", help="Chunk jobs into concurrency-bounded batches")
    p.add_argument("--size", type=int, default=5)
    p.add_argument("--jobs", help="JSON list of jobs; reads stdin if omitted")
    p.set_defaults(func=_cmd_batch)

    p = subparsers.add_parser("render-shortlist", help="Render shortlist.md content")
    p.add_argument("--jobs", help="JSON list of shortlisted jobs", default="[]")
    p.add_argument("--failures", help="JSON list of failures", default="[]")
    p.set_defaults(func=_cmd_render_shortlist)

    p = subparsers.add_parser("resume-filename", help="Deterministic tailored-resume filename")
    p.add_argument("company")
    p.add_argument("title")
    p.set_defaults(func=_cmd_resume_filename)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
