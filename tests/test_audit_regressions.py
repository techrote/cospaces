from pathlib import Path

import pytest

from cospaces.domain.checkpoint import CheckpointDocument, checkpoint_from_dict
from cospaces.domain.run import RunRequest
from cospaces.services.run_service import RunService
from cospaces.verification_config import load_verification_plan


class UnexpectedWorkspace:
    def describe(self, name: str):
        raise AssertionError(f"workspace lookup must not occur: {name}")

    def resolve(self, repository: str, *, ref=None, name=None):
        raise AssertionError(f"workspace resolution must not occur: {repository} {ref} {name}")


class UnexpectedTransport:
    def execute(self, codespace: str, argv: tuple[str, ...], *, timeout_seconds: float):
        raise AssertionError(f"transport must not occur: {codespace} {argv} {timeout_seconds}")


def test_checkpoint_v1_rejects_unknown_root_fields() -> None:
    document = CheckpointDocument(
        task_id="audit",
        created_at="2026-09-13T20:00:00Z",
        updated_at="2026-09-13T20:00:01Z",
    )
    payload = document.to_dict()
    payload["unexpected"] = "silently ignored before audit"

    with pytest.raises(ValueError, match="unsupported keys"):
        checkpoint_from_dict(payload)


@pytest.mark.parametrize("literal", ["nan", "inf", "+inf", "-inf"])
def test_verification_rejects_nonfinite_timeouts(tmp_path: Path, literal: str) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[verify.default]\n"
        "[[verify.default.checks]]\n"
        'name = "tests"\n'
        'command = ["true"]\n'
        f"timeout_seconds = {literal}\n",
        encoding="utf-8",
    )

    result = load_verification_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "verification_configuration_error"
    assert "finite" in result.failure.message


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf")])
def test_run_rejects_nonfinite_timeout_before_workspace_lookup(timeout: float) -> None:
    service = RunService(
        workspace=UnexpectedWorkspace(),  # type: ignore[arg-type]
        transport=UnexpectedTransport(),  # type: ignore[arg-type]
    )

    result = service.execute(
        RunRequest(argv=("true",), codespace="space-one", timeout_seconds=timeout)
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "invalid_timeout"
    assert int(result.failure.exit_status) == 2


def test_run_rejects_nul_argv_before_workspace_lookup() -> None:
    service = RunService(
        workspace=UnexpectedWorkspace(),  # type: ignore[arg-type]
        transport=UnexpectedTransport(),  # type: ignore[arg-type]
    )

    result = service.execute(
        RunRequest(argv=("printf", "bad\x00value"), codespace="space-one")
    )

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "invalid_remote_argv"
    assert int(result.failure.exit_status) == 2
