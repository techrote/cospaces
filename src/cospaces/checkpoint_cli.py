"""CLI surface for durable checkpoint metadata."""

from __future__ import annotations

import argparse


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", default=".", help="repository root containing .cospaces")
    parser.add_argument("--json", action="store_true", dest="json_output")


def add_checkpoint_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    checkpoint = subparsers.add_parser("checkpoint", help="persist resumable task metadata")
    operations = checkpoint.add_subparsers(dest="checkpoint_operation", required=True)

    save = operations.add_parser("save", help="create or update one checkpoint")
    save.add_argument("--task", required=True)
    save.add_argument("--repo")
    save.add_argument("--ref")
    save.add_argument("--head")
    save.add_argument("--codespace")
    save.add_argument("--no-git", action="store_true")
    save.add_argument("--completed", action="append")
    save.add_argument("--current")
    save.add_argument("--next", dest="next_step")
    save.add_argument("--last-run-id")
    save.add_argument("--last-verification-id")
    save.add_argument("--record-path", action="append")
    save.add_argument("--notes")
    _common(save)

    show = operations.add_parser("show", help="show one validated checkpoint")
    show.add_argument("--task", required=True)
    _common(show)

    list_parser = operations.add_parser("list", help="list current checkpoint files")
    _common(list_parser)

    validate = operations.add_parser("validate", help="validate checkpoint data and context")
    validate.add_argument("--task", required=True)
    validate.add_argument("--live", action="store_true")
    validate.add_argument("--codespace")
    _common(validate)
