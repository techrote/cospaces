import json

from cospaces.domain import results
from cospaces.domain.checkpoint import SCHEMA as CHECKPOINT_SCHEMA
from cospaces.domain.contracts import DomainFailure, ExitStatus, FailureKind
from cospaces.domain.verification import SCHEMA as VERIFY_SCHEMA


def test_schema_versions_are_explicit_and_stable() -> None:
    assert results.SCHEMA == "cospaces.result/v1"
    assert CHECKPOINT_SCHEMA == "cospaces.checkpoint/v1"
    assert VERIFY_SCHEMA == "cospaces.verify/v1"


def test_all_documented_exit_categories_are_locked() -> None:
    assert [int(status) for status in ExitStatus] == list(range(8))
    assert ExitStatus.SUCCESS == 0
    assert ExitStatus.USAGE == 2
    assert ExitStatus.INFRASTRUCTURE == 3
    assert ExitStatus.SELECTION == 4
    assert ExitStatus.REMOTE == 5
    assert ExitStatus.PERSISTENCE == 6
    assert ExitStatus.VERIFICATION == 7


def test_failure_kinds_keep_their_exit_categories() -> None:
    expected = (
        (FailureKind.USAGE, 2),
        (FailureKind.INFRASTRUCTURE, 3),
        (FailureKind.SELECTION, 4),
        (FailureKind.REMOTE, 5),
        (FailureKind.PERSISTENCE, 6),
        (FailureKind.VERIFICATION, 7),
    )
    for kind, status in expected:
        failure = DomainFailure(code="example", kind=kind, message="example")
        assert int(failure.exit_status) == status


def test_common_json_envelope_is_one_versioned_document() -> None:
    envelope = results.ResultEnvelope(
        operation="hardening.example",
        ok=True,
        started_at="2026-09-13T20:00:00Z",
        finished_at="2026-09-13T20:00:01Z",
        workspace={"name": "space-one"},
        result={"value": 1},
    )
    payload = json.loads(envelope.to_json())

    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "hardening.example"
    assert payload["ok"] is True
    assert payload["workspace"] == {"name": "space-one"}
    assert payload["result"] == {"value": 1}
    assert payload["error"] is None
