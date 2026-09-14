"""CLI parser for T6 fixture execution."""

from __future__ import annotations

import argparse


def add_fixture_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("fixture", help="run a repository-declared fixture")
    parser.add_argument("fixture")
    parser.add_argument("--codespace")
    parser.add_argument("--repo")
    parser.add_argument("--ref")
    parser.add_argument("--root", default=".")
    parser.add_argument("--task-id")
    parser.add_argument("--correlation-id")
    parser.add_argument("--json", action="store_true", dest="json_output")
