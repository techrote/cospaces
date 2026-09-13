from cospaces.domain.verification import VerificationCheck
from cospaces.verification_command import VERIFY_SETUP_MARKER, build_check_argv


def test_check_runs_from_repository_root_by_default() -> None:
    check = VerificationCheck(
        name="tests",
        command=("python", "-m", "pytest"),
        timeout_seconds=60,
    )

    argv = build_check_argv(check)

    assert argv[:4] == ("sh", "-c", argv[2], "cospaces-verify")
    assert argv[4] == "."
    assert argv[5:] == ("python", "-m", "pytest")
    assert "/workspaces/$repo_name" in argv[2]
    assert "pwd -P" in argv[2]
    assert '"$root_real"/*' in argv[2]
    assert VERIFY_SETUP_MARKER in argv[2]


def test_working_directory_is_positional_data_not_script_text() -> None:
    check = VerificationCheck(
        name="tests",
        command=("printf", "%s", "hello"),
        timeout_seconds=60,
        working_directory="sub dir;literal",
    )

    argv = build_check_argv(check)

    assert argv[4] == "sub dir;literal"
    assert "sub dir;literal" not in argv[2]
    assert argv[5:] == ("printf", "%s", "hello")


def test_environment_values_are_passed_as_env_arguments() -> None:
    check = VerificationCheck(
        name="tests",
        command=("python", "-V"),
        timeout_seconds=60,
        environment=(("MODE", "ci value"), ("COUNT", "2")),
    )

    argv = build_check_argv(check)

    assert argv[4] == "."
    assert argv[5:] == ("env", "MODE=ci value", "COUNT=2", "python", "-V")
