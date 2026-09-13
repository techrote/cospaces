"""Top-level cospaces command-line interface."""

import argparse
import sys
from collections.abc import Sequence
from typing import cast

from . import __version__
from .checkpoint_cli import add_checkpoint_parser
from .checkpoint_dispatch import run_checkpoint
from .domain.contracts import DomainFailure, FailureKind
from .domain.results import failure_result
from .run_cli import add_run_parser
from .run_dispatch import run_remote
from .services.tool_registry import PLANNED_TOOLS
from .workspace_cli import add_workspace_parser
from .workspace_dispatch import run_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cospaces",
        description="Task-oriented GitHub Codespaces utilities.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="tool", title="tools")
    add_workspace_parser(subparsers)
    add_run_parser(subparsers)
    add_checkpoint_parser(subparsers)
    for tool in PLANNED_TOOLS:
        if tool in {"workspace", "run", "checkpoint"}:
            continue
        child = subparsers.add_parser(tool, help=f"{tool} tool (planned)")
        child.add_argument("--json", action="store_true", dest="json_output")
    return parser


def _planned_tool(tool: str, *, json_output: bool) -> int:
    failure = DomainFailure(
        code="not_implemented",
        kind=FailureKind.NOT_IMPLEMENTED,
        message=f"{tool} is planned but not implemented in the current release",
    )
    if json_output:
        print(failure_result(tool, failure).to_json())
    else:
        print(failure.message, file=sys.stderr)
    return int(failure.exit_status)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(list(argv) if argv is not None else None)
    tool = cast(str | None, namespace.tool)
    if tool is None:
        parser.print_help()
        return 0
    if tool == "workspace":
        return run_workspace(namespace)
    if tool == "run":
        return run_remote(namespace)
    if tool == "checkpoint":
        return run_checkpoint(namespace)
    return _planned_tool(tool, json_output=bool(namespace.json_output))


def entrypoint() -> None:
    raise SystemExit(main())
