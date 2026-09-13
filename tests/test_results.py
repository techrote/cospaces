import json

from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.results import failure_result, success_result


def test_success_result_is_stable_json() -> None:
    envelope = success_result(
        "foundation.test",
        result={"value": 7},
        workspace={"name": "example"},
        started_at="2026-09-13T18:00:00Z",
        finished_at="2026-09-13T18:00:01Z",
    )
    payload = json.loads(envelope.to_json())
    assert payload["schema"] == "cospaces.result/v1"
    assert payload["operation"] == "foundation.test"
    assert payload["ok"] is True
    assert payload["workspace"] == {"name": "example"}
    assert payload["result"] == {"value": 7}
    assert payload["error"] is None


def test_failure_result_is_stable_json() -> None:
    failure = DomainFailure("configuration_error", FailureKind.USAGE, "bad config")
    envelope = failure_result(
        "foundation.test",
        failure,
        started_at="2026-09-13T18:00:00Z",
        finished_at="2026-09-13T18:00:01Z",
    )
    payload = json.loads(envelope.to_json())
    assert payload["ok"] is False
    assert payload["result"] is None
    assert payload["error"] == {
        "code": "configuration_error",
        "message": "bad config",
        "retryable": False,
    }
