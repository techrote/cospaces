"""T5 live capability introspection composed from T1 and T2."""

import re
from dataclasses import dataclass
from pathlib import Path

from cospaces import __version__
from cospaces.adapters.github_cli import GitHubCliAdapter
from cospaces.capabilities_config import CapabilityConfig, CapabilityProbe, load_capability_config
from cospaces.domain.capabilities import (
    CapabilityObservation,
    CapabilityReport,
    CapabilityState,
)
from cospaces.domain.contracts import DomainFailure, FailureKind
from cospaces.domain.run import RunRequest
from cospaces.services.run_service import RunActionResult, RunService
from cospaces.services.run_transport import parse_gh_version
from cospaces.services.workspace_service import WorkspaceActionResult, WorkspaceService


@dataclass(frozen=True)
class CapabilityRequest:
    repository: str | None = None
    ref: str | None = None
    codespace: str | None = None
    root: Path = Path(".")


@dataclass(frozen=True)
class CapabilityActionResult:
    report: CapabilityReport | None = None
    failure: DomainFailure | None = None

    @property
    def ok(self) -> bool:
        return self.report is not None and self.failure is None


_BUILTIN_PROBES = (
    CapabilityProbe("remote_os", ("uname", "-s"), timeout_seconds=10.0),
    CapabilityProbe("remote_architecture", ("uname", "-m"), timeout_seconds=10.0),
)


def _bounded_line(text: str, limit: int = 256) -> str | None:
    for line in text.splitlines():
        value = line.strip()
        if value:
            return value[:limit]
    return None


class CapabilityService:
    def __init__(
        self,
        *,
        workspace: WorkspaceService | None = None,
        run: RunService | None = None,
        github: GitHubCliAdapter | None = None,
    ) -> None:
        self._workspace = workspace or WorkspaceService()
        self._run = run or RunService(workspace=self._workspace)
        self._github = github or GitHubCliAdapter()

    def _github_cli(self) -> CapabilityObservation:
        try:
            result = self._github.capture(("--version",), timeout_seconds=10.0)
        except OSError:
            return CapabilityObservation(
                name="github_cli",
                state=CapabilityState.ABSENT,
                reason="executable_unavailable",
            )
        if result.timed_out:
            return CapabilityObservation(
                name="github_cli",
                state=CapabilityState.UNAVAILABLE,
                reason="version_probe_timeout",
            )
        if result.returncode != 0:
            return CapabilityObservation(
                name="github_cli",
                state=CapabilityState.UNAVAILABLE,
                reason="version_probe_failed",
            )
        version = parse_gh_version(result.stdout)
        if version is None:
            return CapabilityObservation(
                name="github_cli",
                state=CapabilityState.UNKNOWN,
                reason="version_parse_failed",
            )
        return CapabilityObservation(
            name="github_cli",
            state=CapabilityState.PRESENT,
            version=".".join(str(item) for item in version),
        )

    def _resolve(self, request: CapabilityRequest) -> WorkspaceActionResult:
        if request.codespace is not None:
            if request.repository is not None:
                return self._workspace.resolve(
                    request.repository,
                    ref=request.ref,
                    name=request.codespace,
                )
            described = self._workspace.describe(request.codespace)
            if not described.ok or request.ref is None:
                return described
            workspace = described.workspace
            assert workspace is not None
            if workspace.ref is None:
                return WorkspaceActionResult(
                    failure=DomainFailure(
                        code="workspace_ref_unknown",
                        kind=FailureKind.SELECTION,
                        message="Cannot establish the selected workspace ref",
                    )
                )
            if workspace.ref != request.ref:
                return WorkspaceActionResult(
                    failure=DomainFailure(
                        code="workspace_ref_mismatch",
                        kind=FailureKind.SELECTION,
                        message="Selected workspace does not match the requested ref",
                    )
                )
            return described
        if request.repository is None:
            return WorkspaceActionResult(
                failure=DomainFailure(
                    code="workspace_target_required",
                    kind=FailureKind.USAGE,
                    message="Either --codespace or --repo is required",
                )
            )
        return self._workspace.resolve(request.repository, ref=request.ref)

    @staticmethod
    def _version(probe: CapabilityProbe, output: str) -> tuple[str | None, str | None]:
        if probe.version_regex is None:
            return None, None
        match = re.search(probe.version_regex, output)
        if match is None:
            return None, "version_parse_failed"
        value = match.group(1) if match.lastindex else match.group(0)
        return value[:128], None

    def _observe_run(self, probe: CapabilityProbe, result: RunActionResult) -> CapabilityObservation:
        record = result.record
        combined = "\n".join(part for part in (record.stdout, record.stderr) if part)
        if result.failure is None:
            version, reason = self._version(probe, combined)
            state = CapabilityState.UNKNOWN if reason is not None else CapabilityState.PRESENT
            return CapabilityObservation(
                name=probe.name,
                state=state,
                value=_bounded_line(record.stdout) or _bounded_line(record.stderr),
                version=version,
                reason=reason,
                run_id=record.run_id,
                command=probe.command,
            )
        failure = result.failure
        if failure.code == "remote_task_failed" and record.exit_code == 127:
            state = CapabilityState.ABSENT
            reason = "executable_unavailable"
        else:
            state = CapabilityState.UNAVAILABLE
            reason = failure.code
        return CapabilityObservation(
            name=probe.name,
            state=state,
            reason=reason,
            run_id=record.run_id,
            command=probe.command,
        )

    def inspect(self, request: CapabilityRequest) -> CapabilityActionResult:
        config_result = load_capability_config(request.root)
        if not config_result.ok:
            assert config_result.failure is not None
            return CapabilityActionResult(failure=config_result.failure)
        config = config_result.config
        assert config is not None

        resolved = self._resolve(request)
        if not resolved.ok:
            assert resolved.failure is not None
            return CapabilityActionResult(failure=resolved.failure)
        workspace = resolved.workspace
        assert workspace is not None

        observations: list[CapabilityObservation] = [
            CapabilityObservation(
                name="codespaces_access",
                state=CapabilityState.PRESENT,
                value="target_resolved",
            )
        ]
        for probe in (*_BUILTIN_PROBES, *config.probes):
            run_result = self._run.execute(
                RunRequest(
                    argv=probe.command,
                    repository=workspace.repository,
                    ref=workspace.ref,
                    codespace=workspace.name,
                    timeout_seconds=probe.timeout_seconds,
                    task_id="capabilities",
                    correlation_id=probe.name,
                )
            )
            observations.append(self._observe_run(probe, run_result))

        return CapabilityActionResult(
            report=CapabilityReport(
                controller_version=__version__,
                github_cli=self._github_cli(),
                workspace=workspace,
                declared_support=config.declared_support,
                observations=tuple(observations),
            )
        )
