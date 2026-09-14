"""CLI parser for T5 capabilities."""

from __future__ import annotations

import argparse


def add_capabilities_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "capabilities",
        help="inspect live controller and Codespace capabilities",
    )
    parser.add_argument("--codespace")
    parser.add_argument("--repo")
    parser.add_argument("--ref")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true", dest="json_output")
