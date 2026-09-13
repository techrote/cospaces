"""CLI surface for structured remote execution."""

from __future__ import annotations

import argparse


def add_run_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    run = subparsers.add_parser("run", help="execute one task in a selected Codespace")
    run.add_argument("--codespace")
    run.add_argument("--repo")
    run.add_argument("--ref")
    run.add_argument("--timeout", default="10m")
    run.add_argument("--task-id")
    run.add_argument("--correlation-id")
    run.add_argument("--json", action="store_true", dest="json_output")
    run.add_argument("remote_argv", nargs=argparse.REMAINDER)
