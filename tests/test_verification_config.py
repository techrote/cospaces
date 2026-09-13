from pathlib import Path

from cospaces.verification_config import load_verification_plan


def write_config(root: Path, body: str) -> None:
    (root / ".cospaces.toml").write_text(body, encoding="utf-8")


def test_plan_parses_required_optional_workdir_and_environment(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
[cospaces]
schema_version = 1

[verify.default]
[[verify.default.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]
timeout_seconds = 30
required = true
working_directory = "tests"
environment = { MODE = "ci" }

[[verify.default.checks]]
name = "advisory"
command = ["python", "-V"]
required = false
""".strip()
        + "\n",
    )

    result = load_verification_plan(tmp_path, "default")

    assert result.ok
    assert result.plan is not None
    assert [check.name for check in result.plan.checks] == ["tests", "advisory"]
    first = result.plan.checks[0]
    assert first.command == ("python", "-m", "pytest", "-q")
    assert first.timeout_seconds == 30.0
    assert first.required is True
    assert first.working_directory == "tests"
    assert first.environment == (("MODE", "ci"),)
    assert result.plan.checks[1].required is False
    assert result.plan.checks[1].timeout_seconds == 600.0


def test_empty_non_executable_arg_and_environment_value_are_preserved(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
[verify.default]
[[verify.default.checks]]
name = "args"
command = ["printf", ""]
environment = { EMPTY = "" }
""".strip()
        + "\n",
    )

    result = load_verification_plan(tmp_path, "default")

    assert result.ok
    assert result.plan is not None
    assert result.plan.checks[0].command == ("printf", "")
    assert result.plan.checks[0].environment == (("EMPTY", ""),)


def test_unknown_plan_is_usage_failure(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        "[cospaces]\nschema_version = 1\n[verify.default]\n"
        "[[verify.default.checks]]\nname = \"tests\"\ncommand = [\"true\"]\n",
    )

    result = load_verification_plan(tmp_path, "release")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "verification_plan_not_found"
    assert int(result.failure.exit_status) == 2


def test_missing_verify_section_is_configuration_failure(tmp_path: Path) -> None:
    write_config(tmp_path, "[cospaces]\nschema_version = 1\n")

    result = load_verification_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "verification_config_missing"


def test_unknown_check_key_is_rejected(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
[verify.default]
[[verify.default.checks]]
name = "tests"
command = ["true"]
requried = true
""".strip()
        + "\n",
    )

    result = load_verification_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert result.failure.code == "verification_configuration_error"
    assert "unknown keys" in result.failure.message


def test_duplicate_check_names_are_rejected(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        """
[verify.default]
[[verify.default.checks]]
name = "tests"
command = ["true"]
[[verify.default.checks]]
name = "tests"
command = ["true"]
""".strip()
        + "\n",
    )

    result = load_verification_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert "unique" in result.failure.message


def test_working_directory_must_remain_repository_relative(tmp_path: Path) -> None:
    for working_directory in ("../outside", "/absolute"):
        write_config(
            tmp_path,
            "[verify.default]\n[[verify.default.checks]]\n"
            f'name = "tests"\ncommand = ["true"]\nworking_directory = "{working_directory}"\n',
        )

        result = load_verification_plan(tmp_path, "default")

        assert not result.ok
        assert result.failure is not None
        assert result.failure.code == "verification_configuration_error"


def test_command_must_be_nonempty_array(tmp_path: Path) -> None:
    write_config(
        tmp_path,
        "[verify.default]\n[[verify.default.checks]]\nname = \"tests\"\ncommand = []\n",
    )

    result = load_verification_plan(tmp_path, "default")

    assert not result.ok
    assert result.failure is not None
    assert "non-empty array" in result.failure.message
