# Roadmap and Dependency Plan

## Phase 0 — repository/CLI foundation

Create the minimal Python package, test harness, formatting/linting/type/test automation, configuration loader skeleton, domain error model, GitHub CLI adapter seam, and CI workflow needed by all tools.

This is a prerequisite issue, not one of the eight programme tools.

## Phase 1 — MVP tranche

1. **T1 `workspace`** — deterministic workspace discovery/selection and lifecycle control.
2. **T2 `run`** — remote execution and structured run records.
3. **T3 `checkpoint`** — durable continuation and handoff state.
4. **T4 `verify`** — repository-declared verification plans and aggregate results.

T1–T4 are implemented and complete the minimum loop: acquire a workspace, execute work, survive interruption, and determine whether declared checks pass.

## Phase 1 hardening and remaining evidence

Issue #18 converted hardening into executable repository machinery and issue #20/PR #21 performed the repository-wide corrective audit. Automated/network-free hardening remains enforced in ordinary CI.

The real disposable-Codespace smoke remains **pending** and may only be executed deliberately against an explicitly selected existing Codespace. Issue #22 separately tracks bounded/spooled T2 output and stronger local timeout/process-tree cleanup. Issue #23 provides supporting foreign-host qualification machinery through `tools/external_workload.py` and is not one of the eight tools.

On 2026-09-14 the user explicitly instructed implementation of **T5, then T6, then T7**. D026 activated those three tools despite the pending live smoke. That implementation sequence is now complete; the pending smoke remains evidence debt and is not considered passed. T8 remains deferred unless separately activated.

## Phase 2 — implemented subset

### 5. T5 `capabilities` — implemented
Reports live controller/workspace capability truth while separating repository-declared intent from observed state. T5 composes T1/T2 and does not install or repair missing tools.

### 6. T6 `fixture` — implemented
Runs reproducible repository-declared experiments through T2 with canonical definition digests, pre-execution remote HEAD provenance, physically contained working/input/output paths, explicit seed/parameter propagation, optional scalar JSON metrics, and structured assertions.

### 7. T7 `evidence` — implemented
Creates local, explicitly allowlisted provenance-bearing bundles for selected run/verify/fixture/checkpoint records and artifacts. T7 uses bounded capture plans, physical path containment, secret-prone path/content rejection, post-copy destination scanning and SHA-256 hashing, visible optional omissions, recognized-record provenance extraction, and independent exact-file validation. The concrete contract is `docs/EVIDENCE_BUNDLES.md`.

### 8. T8 `matrix` — deferred
Compose workspace/run/fixture capabilities into bounded comparative execution only after a separate activation decision.

## Current programme boundary

T1–T7 are implemented. No further product tool is currently activated. The outstanding programme items are:
- T8/#9, deferred until separately activated;
- the explicit real-Codespace smoke, still pending evidence debt;
- issue #22, open hardening debt around T2 output/process-tree resource handling.

## Suggested release progression

- `0.0.x`: foundation/internal contract iterations.
- `0.1.0`: T1–T4 functional MVP.
- `0.1.x`: hardening, compatibility, integration tests.
- `0.2.0`: implemented Phase 2 subset T5–T7.
- later: matrix maturity and optional richer orchestration.

Version numbers are guidance, not a compatibility promise until the project declares a stable public API.

## Issue execution ordering

Repository issues should declare dependencies explicitly. An autonomous agent may complete multiple ready issues in one run, but must not merge a dependent implementation against contracts that have not landed yet.

If a later issue exposes a flaw in an earlier contract, prefer a small corrective PR that updates code, tests, and canonical docs together rather than silently compensating downstream.
