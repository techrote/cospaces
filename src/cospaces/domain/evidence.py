"""T7 evidence bundle domain model."""

from dataclasses import dataclass

SCHEMA = "cospaces.evidence/v1"
VALIDATION_SCHEMA = "cospaces.evidence-validation/v1"


@dataclass(frozen=True)
class EvidenceItemRecord:
    index: int
    kind: str
    source_path: str
    stored_path: str | None
    required: bool
    status: str
    size_bytes: int | None
    sha256: str | None
    content_type: str | None
    source_schema: str | None
    provenance: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "kind": self.kind,
            "source_path": self.source_path,
            "stored_path": self.stored_path,
            "required": self.required,
            "status": self.status,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "content_type": self.content_type,
            "source_schema": self.source_schema,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class EvidenceManifest:
    evidence_id: str
    plan: str
    created_at: str
    controller_version: str
    capture_root: str
    items: tuple[EvidenceItemRecord, ...]
    notes: tuple[str, ...]
    total_captured_bytes: int
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "evidence_id": self.evidence_id,
            "plan": self.plan,
            "created_at": self.created_at,
            "controller_version": self.controller_version,
            "capture_root": self.capture_root,
            "items": [item.to_dict() for item in self.items],
            "notes": list(self.notes),
            "total_captured_bytes": self.total_captured_bytes,
        }


@dataclass(frozen=True)
class EvidenceCreateRecord:
    evidence_id: str
    plan: str
    bundle_path: str
    manifest: EvidenceManifest
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "evidence_id": self.evidence_id,
            "plan": self.plan,
            "bundle_path": self.bundle_path,
            "manifest": self.manifest.to_dict(),
        }


@dataclass(frozen=True)
class EvidenceValidationRecord:
    bundle_path: str
    evidence_id: str | None
    valid: bool
    checked_files: int
    schema: str = VALIDATION_SCHEMA

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "bundle_path": self.bundle_path,
            "evidence_id": self.evidence_id,
            "valid": self.valid,
            "checked_files": self.checked_files,
        }
