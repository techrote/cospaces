# Roadmap and Dependency Plan

## Phase 0 — repository/CLI foundation

Create the minimal Python package, test harness, formatting/linting/type/test automation, configuration loader skeleton, domain error model, GitHub CLI adapter seam, and CI workflow needed by all tools.

This is a prerequisite issue, not one of the eight programme tools.

Exit criteria:
- installable/testable package;
- `cospaces --help` works;
- unit test command documented;
- CI runs automatically on PRs;
- tests can stub all `gh`/subprocess behaviour;
- no real Codespace is required for routine unit tests.

## Phase 1 — MVP tranche

Implement in dependency order unless an issue can proceed independently without destabilising contracts.

### 1. T1 `workspace`
Establish deterministic workspace discovery/selection and lifecycle control.

### 2. T2 `run`
Establish remote execution and structured run records.

### 3. T3 `checkpoint`
Persist continuation state and task handoff records.

### 4. T4 `verify`
Add repository-declared verification plans and aggregate results.

MVP milestone after T4: an agent can acquire a Codespace, run work, checkpoint state, and run authoritative repository checks through machine-readable interfaces.

## Phase 1 hardening and remaining evidence

Issue #18 converted the hardening gate into executable repository machinery. Issue #20/PR #21 then performed a repository-wide corrective audit of the implemented MVP and hardened target certainty, provenance truthfulness, physical verification containment, strict schema/config validation, controller wait bounds, and malformed-request preflight.

Automated/network-free hardening remains enforced in ordinary CI. The real disposable-Codespace smoke is still **pending** and may only be executed deliberately against an explicitly selected existing Codespace. Issue #22 separately tracks bounded/spooled T2 output and stronger local timeout/process-tree cleanup.

Issue #23 adds supporting repository machinery for foreign-host qualification through `tools/external_workload.py`; it is not one of the eight tools.

On 2026-09-14 the user explicitly instructed implementation of **T5, then T6, then T7**. D026 activates those three tools despite the pending live smoke; the pending smoke remains evidence debt and is not considered passed. T8 remains deferred unless separately activated.

## Phase 2 — active sequence

### 5. T5 `capabilities` — active/implementing
Report live controller/workspace capability truth while separating repository-declared intent from observed state. T5 composes T1/T2 and does not install or repair missing tools.

### 6. T6 `fixture` — next after T5 merge
Add reproducible repository-declared experiment/benchmark definitions using stable T1/T2/T4 semantics and the landed T5 context where useful.

### 7. T7 `evidence` — next after T6 merge
Package provenance-bearing run/verify/fixture/checkpoint records plus explicitly allowlisted artifacts into bounded evidence bundles.

### 8. T8 `matrix` — deferred
Compose workspace/run/fixture capabilities into bounded comparative execution only after a separate activation decision.

## Suggested release progression

- `0.0.x`: foundation/internal contract iterations.
- `0.1.0`: T1–T4 functional MVP.
- `0.1.x`: hardening, compatibility, integration tests.
- `0.2.0`: activated Phase 2 subset T5–T7.
- later: matrix maturity and optional richer orchestration.

Version numbers are guidance, not a compatibility promise until the project declares a stable public API.

## Issue execution ordering

Repository issues should declare their dependencies explicitly. An autonomous agent may complete multiple ready issues in one run, but must not merge a dependent implementation against contracts that have not landed yet.

If a later issue exposes a flaw in an earlier contract, prefer a small corrective PR that updates code, tests, and canonical docs together rather than silently compensating downstream.
