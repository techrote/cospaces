"""CLI surface for the workspace tool."""

import argparse


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="json_output")


def _add_creation_options(parser: argparse.ArgumentParser, *, include_branch: bool) -> None:
    if include_branch:
        parser.add_argument("--branch")
    parser.add_argument("--devcontainer-path")
    parser.add_argument("--display-name")
    parser.add_argument("--idle-timeout")
    parser.add_argument("--machine")
    parser.add_argument("--location")
    parser.add_argument("--retention-period")


def add_workspace_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    workspace = subparsers.add_parser("workspace", help="manage task Codespaces")
    operations = workspace.add_subparsers(dest="workspace_operation", required=True)

    list_parser = operations.add_parser("list", help="list repository Codespaces")
    list_parser.add_argument("--repo", required=True)
    _add_json(list_parser)

    describe = operations.add_parser("describe", help="describe one Codespace")
    describe.add_argument("--codespace", required=True)
    _add_json(describe)

    ensure = operations.add_parser("ensure", help="resolve or explicitly create a Codespace")
    ensure.add_argument("--repo", required=True)
    ensure.add_argument("--ref")
    ensure.add_argument("--codespace")
    ensure.add_argument("--create", action="store_true")
    _add_creation_options(ensure, include_branch=False)
    _add_json(ensure)

    create = operations.add_parser("create", help="create one Codespace")
    create.add_argument("--repo", required=True)
    _add_creation_options(create, include_branch=True)
    _add_json(create)

    stop = operations.add_parser("stop", help="stop one Codespace")
    stop.add_argument("--codespace", required=True)
    _add_json(stop)
