import json
from pathlib import Path

from cospaces.cli import build_parser
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.run_service import RunActionResult
from cospaces.services.verification_service import VerificationService
from cospaces.verify_dispatch import run_verify
