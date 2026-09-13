from cospaces.domain.contracts import DomainFailure, ExitStatus, FailureKind


def test_domain_failure_exit_mapping() -> None:
    expected = {
        FailureKind.USAGE: ExitStatus.USAGE,
        FailureKind.INFRASTRUCTURE: ExitStatus.INFRASTRUCTURE,
        FailureKind.SELECTION: ExitStatus.SELECTION,
        FailureKind.REMOTE: ExitStatus.REMOTE,
        FailureKind.PERSISTENCE: ExitStatus.PERSISTENCE,
        FailureKind.VERIFICATION: ExitStatus.VERIFICATION,
        FailureKind.INTERNAL: ExitStatus.INTERNAL,
        FailureKind.NOT_IMPLEMENTED: ExitStatus.INTERNAL,
    }

    for kind, status in expected.items():
        failure = DomainFailure(code="test", kind=kind, message="test")
        assert failure.exit_status is status
