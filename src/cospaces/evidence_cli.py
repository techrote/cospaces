"""CLI parser for T7 evidence bundles."""

from __future__ import annotations

import argparse


def add_evidence_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("evidence", help="create or validate an evidence bundle")
    commands = parser.add_subparsers(dest="evidence_action", required=True)

    create = commands.add_parser("create", help="create an allowlisted evidence bundle")
    create.add_argument("plan")
    create.add_argument("--root", default=".")
    create.add_argument("--output", dest="output_directory")
    create.add_argument("--json", action="store_true", dest="json_output")

    validate = commands.add_parser("validate", help="validate an existing evidence bundle")
    validate.add_argument("bundle")
    validate.add_argument("--root", default=".")
    validate.add_argument("--json", action="store_true", dest="json_output")
