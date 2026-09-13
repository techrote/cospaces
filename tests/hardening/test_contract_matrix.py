import json

from cospaces.domain.checkpoint import SCHEMA as CHECKPOINT_SCHEMA
from cospaces.domain.contracts import DomainFailure, ExitStatus, FailureKind
from cospaces.domain.results import SCHEMA as RESULT_SCHEMA, ResultEnvelope
from cospaces.domain.verification import SCHEMA as VERIFY_SCHEMA


def test_schema_versions_are_explicit_and_stable() -> None:
    assert RESULT_SCHEMA == "cospaces.result/v1"
    assert CHECKPOINT_SCHEMA == "cospaces.checkpoint/v1"
    assert VERIFY_SCHEMA == "cospaces.verify/v1"
