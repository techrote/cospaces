from pathlib import Path

from cospaces.config import load_config
from cospaces.domain.contracts import ExitStatus, FailureKind


def test_missing_config_uses_safe_default(tmp_path: Path) -> None:
    result = load_config(tmp_path / "missing.toml")

    assert result.ok is True
    assert result.config is not None
    assert result.config.schema_version == 1
    assert result.config.extra_sections == {}
    assert result.failure is None


def test_valid_config_preserves_unclaimed_sections(tmp_path: Path) -> None:
    path = tmp_path / ".cospaces.toml"
    path.write_text(
        "[cospaces]\nschema_version = 1\n\n[future]\nenabled = true\n",
        encoding="utf-8",
    )

    result = load_config(path)

    assert result.ok is True
    assert result.config is not None
    assert result.config.extra_sections == {"future": {"enabled": True}}


def test_malformed_toml_returns_usage_failure(tmp_path: Path) -> None:
    path = tmp_path / ".cospaces.toml"
    path.write_text("[cospaces\n", encoding="utf-8")

    result = load_config(path)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.code == "configuration_error"
    assert result.failure.kind is FailureKind.USAGE
    assert result.failure.exit_status is ExitStatus.USAGE


def test_unknown_control_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / ".cospaces.toml"
    path.write_text("[cospaces]\nunknown = true\n", encoding="utf-8")

    result = load_config(path)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.code == "configuration_error"


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / ".cospaces.toml"
    path.write_text("[cospaces]\nschema_version = 2\n", encoding="utf-8")

    result = load_config(path)

    assert result.ok is False
    assert result.failure is not None
    assert result.failure.code == "configuration_error"
