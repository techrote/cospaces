import json
import subprocess
import sys

from cospaces.cli import main
from cospaces.services.tool_registry import PLANNED_TOOLS


def test_no_tool_prints_help(capsys) -> None:
    status = main([])

    captured = capsys.readouterr()
    assert status == 0
    assert "usage: cospaces" in captured.out
    assert captured.err == ""


def test_deferred_tool_json_is_parseable_and_prose_free(capsys) -> None:
    status = main(["fixture", "--json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert status == 1
    assert captured.err == ""
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "fixture"
    assert payload["ok"] is False
    assert payload["error"]["code"] == "not_implemented"


def test_capabilities_parser_is_registered() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "cospaces", "capabilities", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--codespace" in completed.stdout
    assert "--repo" in completed.stdout


def test_all_eight_tool_names_are_registered() -> None:
    assert PLANNED_TOOLS == (
        "workspace",
        "run",
        "checkpoint",
        "verify",
        "capabilities",
        "fixture",
        "evidence",
        "matrix",
    )


def test_python_module_help_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "cospaces", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "usage: cospaces" in completed.stdout


def test_python_module_version_smoke() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "cospaces", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip() == "cospaces 0.0.1"
