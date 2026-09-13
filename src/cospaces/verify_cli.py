"""CLI surface for repository-declared verification."""

from __future__ import annotations

import argparse


def add_verify_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    verify = subparsers.add_parser("verify", help="run a repository verification plan")
    verify.add_argument("plan", nargs="?", default="default")
    verify.add_argument("--codespace")
    verify.add_argument("--repo")
    verify.add_argument("--ref")
    verify.add_argument("--root", default=".")
    verify.add_argument("--task-id")
    verify.add_argument("--correlation-id")
    verify.add_argument("--json", action="store_true", dest="json_output")
