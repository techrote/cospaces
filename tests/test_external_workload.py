import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "external_workload.py"


def run_tool(*arguments: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        (sys.executable, str(SCRIPT), *arguments),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def test_dry_run_core_is_deterministic_json() -> None:
    result = run_tool("--profile", "core", "--dry-run", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema"] == "cospaces.external-workload/v1"
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["profile"] == "core"
    assert [stage["name"] for stage in payload["plan"]] == ["hardening", "build"]
    assert payload["iterations"] == []
    assert payload["summary"] == {}
    assert result.stderr == ""


def test_smoke_profile_executes_real_bounded_stage() -> None:
    result = run_tool("--profile", "smoke", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert len(payload["iterations"]) == 1
    stage = payload["iterations"][0]["stages"][0]
    assert stage["name"] == "module_help"
    assert stage["ok"] is True
    assert stage["returncode"] == 0
    assert stage["stdout_bytes"] > 0
    assert stage["stdout_tail"] is None
    assert stage["stderr_tail"] is None


def test_invalid_repetition_count_is_structured_usage_failure() -> None:
    result = run_tool("--repetitions", "0", "--json")

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_arguments"
    assert payload["iterations"] == []


def test_environment_values_are_not_serialized() -> None:
    secret = "do-not-leak-this-environment-value"
    result = run_tool(
        "--profile",
        "smoke",
        "--dry-run",
        "--json",
        extra_env={"COSPACES_TEST_SECRET": secret},
    )

    assert result.returncode == 0
    assert secret not in result.stdout
    payload = json.loads(result.stdout)
    assert "COSPACES_TEST_SECRET" not in json.dumps(payload)


def test_profile_plans_do_not_embed_absolute_python_or_scratch_paths() -> None:
    result = run_tool("--profile", "full", "--dry-run", "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    encoded = json.dumps(payload["plan"])
    assert sys.executable not in encoded
    assert "<scratch>/build" in encoded
    assert [stage["name"] for stage in payload["plan"]][-2:] == [
        "module_help",
        "console_help",
    ]
