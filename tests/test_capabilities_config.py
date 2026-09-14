from pathlib import Path

from cospaces.capabilities_config import load_capability_config


def test_missing_capabilities_config_is_empty(tmp_path: Path) -> None:
    result = load_capability_config(tmp_path)

    assert result.ok
    assert result.config is not None
    assert result.config.declared_support == {}
    assert result.config.probes == ()


def test_capabilities_config_parses_declared_support_and_probe(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[capabilities.supports]\n"
        "build = true\n"
        "headless = false\n"
        "[[capabilities.probes]]\n"
        'name = "python"\n'
        'command = ["python", "--version"]\n'
        "timeout_seconds = 5\n"
        'version_regex = "Python ([0-9.]+)"\n',
        encoding="utf-8",
    )

    result = load_capability_config(tmp_path)

    assert result.ok
    assert result.config is not None
    assert result.config.declared_support == {"build": True, "headless": False}
    probe = result.config.probes[0]
    assert probe.name == "python"
    assert probe.command == ("python", "--version")
    assert probe.timeout_seconds == 5.0
    assert probe.version_regex == "Python ([0-9.]+)"


def test_capabilities_config_rejects_duplicate_probe_names(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[[capabilities.probes]]\n"
        'name = "python"\n'
        'command = ["python", "--version"]\n'
        "[[capabilities.probes]]\n"
        'name = "python"\n'
        'command = ["python3", "--version"]\n',
        encoding="utf-8",
    )

    result = load_capability_config(tmp_path)

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "capabilities_configuration_error"
    assert "duplicate" in result.failure.message


def test_capabilities_config_rejects_nonfinite_timeout(tmp_path: Path) -> None:
    (tmp_path / ".cospaces.toml").write_text(
        "[[capabilities.probes]]\n"
        'name = "python"\n'
        'command = ["python", "--version"]\n'
        "timeout_seconds = nan\n",
        encoding="utf-8",
    )

    result = load_capability_config(tmp_path)

    assert not result.ok
    assert result.failure is not None
    assert "finite" in result.failure.message
