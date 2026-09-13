from pathlib import Path

import pytest

from cospaces.domain.checkpoint import CheckpointDocument, checkpoint_from_dict
from cospaces.verification_config import load_verification_plan


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
