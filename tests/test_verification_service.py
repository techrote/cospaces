from pathlib import Path
from uuid import UUID

from cospaces.domain.checkpoint import WorkingTreeState
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRecord
from cospaces.domain.workspace import WorkspaceIdentity
from cospaces.services.checkpoint_service import CheckpointSaveRequest, CheckpointService
from cospaces.services.repository_probe import RepositoryContext, RepositoryProbeResult
from cospaces.services.run_service import RunActionResult
from cospaces.services.verification_service import VerificationRequest, VerificationService
