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

Why first: every remote operation needs an unambiguous target.

### 2. T2 `run`
Establish remote execution and structured run records.

Why second: verification and later experiment tools build on it.

### 3. T3 `checkpoint`
Persist continuation state and task handoff records.

Why before `verify`: checkpointing is intentionally a first-class long-horizon primitive, not cleanup added later. It can initially record run/workspace state even before verification reports exist.

### 4. T4 `verify`
Add repository-declared verification plans and aggregate results.

MVP milestone after T4:
An agent can acquire a Codespace, run work, checkpoint state, and run authoritative repository checks through machine-readable interfaces.

## Phase 1 hardening gate

Before starting broad Phase 2 implementation, perform at least:
- contract review of JSON schema/versioning;
- integration smoke test against a real disposable Codespace;
- ambiguity/failure-path tests;
- checkpoint stop/reconnect/resume exercise;
- verify-pass and verify-fail exercises;
- documentation reconciliation.

A separate hardening issue may be created after T4 if evidence warrants it.

## Phase 2 — planned tools

### 5. T5 `capabilities`
Add live environment introspection once the controller/workspace contracts are stable.

### 6. T6 `fixture`
Add reproducible experiment/benchmark definitions using T2 run records.

### 7. T7 `evidence`
Package provenance-bearing results from run/verify/fixture/checkpoint state.

### 8. T8 `matrix`
Compose workspace/run/fixture capabilities into bounded comparative execution.

## Why these four are deferred

They are valuable, but none is required to prove the central hypothesis. Implementing them before the MVP works would expand schema and orchestration surface prematurely.

## Suggested release progression

- `0.0.x`: foundation/internal contract iterations.
- `0.1.0`: T1–T4 functional MVP.
- `0.1.x`: hardening, compatibility, integration tests.
- `0.2.0`: first coherent subset of T5–T8, likely capabilities + fixture.
- later: evidence/matrix maturity and optional richer orchestration.

Version numbers are guidance, not a compatibility promise until the project declares a stable public API.

## Issue execution ordering

Repository issues should declare their dependencies explicitly. An autonomous agent may complete multiple ready issues in one run, but must not merge a dependent implementation against contracts that have not landed yet.

If a later issue exposes a flaw in an earlier contract, prefer a small corrective PR that updates code, tests, and canonical docs together rather than silently compensating downstream.
