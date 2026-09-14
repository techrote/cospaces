# Tool Catalog

The programme defines eight composable utilities. They may share one `cospaces` executable and internal package; “tool” means a coherent command/service contract, not necessarily a separate binary.

## T1 — `workspace` — implemented
Resolve, inspect, create/reuse, stop, and explicitly manage the Codespace intended for a task. Selection is deterministic, non-interactive, bounded at the controller, and fail-closed when metadata cannot prove a unique repository/ref target.

## T2 — `run` — implemented
Execute one non-interactive argv inside exactly one resolved Codespace and return a structured run record. T2 preserves remote/controller failure distinctions, never retries implicitly, and does not claim timeout proves remote termination; #22 tracks bounded output/process-tree hardening.

## T3 — `checkpoint` — implemented
Persist bounded continuation state so a stopped Codespace, lost controller process, or new session can resume intentionally. Checkpoints are strict-schema, atomic where practical, keep one prior valid revision, and never imply commit/push or execute continuation text.

## T4 — `verify` — implemented
Execute repository-declared checks sequentially through T2 in one pinned Codespace and emit `cospaces.verify/v1`. Verification preserves required/optional semantics, physical repository containment, truthful provenance, and the distinction between repository assertion failure and inability to run the check.

## T5 — `capabilities` — implemented
Report what the current controller and one selected Codespace can actually do while keeping repository-declared intent separate from live observations.

```bash
cospaces capabilities --codespace NAME --json
cospaces capabilities --repo owner/repo [--ref REF] --json
```

T5 emits `cospaces.capabilities/v1`; observations are `present`, `absent`, `unavailable`, or `unknown`. Repository `[capabilities.supports]` declarations remain separate from live evidence, and configured probes execute only through T2 in one T1-selected workspace.

Non-goals: package management, automatic repair/install, environment dumps, or treating declared support as observed truth.

## T6 — `fixture` — implemented

### Purpose
Run bounded, reproducible repository-declared experiments and benchmarks in exactly one Codespace and emit provenance-bearing structured results.

### Interface

```bash
cospaces fixture NAME --codespace NAME --json
cospaces fixture NAME --repo owner/repo [--ref REF] --json
```

The nested result schema is `cospaces.fixture/v1`.

### Definition
`.cospaces.toml` `[fixture.<name>]` supports:
- command argv and finite timeout;
- repository-relative working directory;
- tags;
- optional seed and scalar parameters;
- declared repository-relative inputs/outputs;
- metrics format `none` or `json-last-line`;
- scalar metric assertions using `==`, `!=`, `>`, `>=`, `<`, `<=`.

T6 computes a canonical SHA-256 definition digest. Seed/parameters are passed as explicit `COSPACES_FIXTURE_*` environment assignments; they are configuration metadata and must not contain secrets.

### Provenance and safety
- observe remote Git HEAD through T2 **before** running the experiment; provenance failure prevents task execution;
- physically contain working directory and input paths under the selected checkout;
- verify declared output existence/containment after successful execution;
- pin all T2 calls to one selected workspace;
- implement no duplicate Codespaces/SSH transport;
- keep configuration, provenance/setup/input, task, output, metrics parse and assertion failures distinct.

### Result
The fixture record includes fixture/run IDs, definition digest, task/support T2 run IDs, repository/ref/remotely-observed HEAD, workspace, declared reproducibility metadata, output references, metrics, assertion outcomes, timing and complete/passed/failure state.

T6 references output paths; it does not copy artifact bytes. T7 owns later allowlisted evidence capture.

### Non-goals
Notebook platform, arbitrary DAG/workflow engine, distributed scheduler, domain-specific scientific semantics, or automatic result interpretation.

## T7 — `evidence` — implemented

### Purpose
Create a bounded, provenance-bearing local evidence bundle for explicitly selected run/verification/fixture/checkpoint records and artifacts.

### Interface

```bash
cospaces evidence create PLAN --root . --json
cospaces evidence create PLAN --root . --output .cospaces/evidence --json
cospaces evidence validate BUNDLE --root . --json
```

Creation emits `cospaces.evidence/v1`; validation emits `cospaces.evidence-validation/v1` inside the normal `cospaces.result/v1` envelope.

### Capture model
- repository-controlled `[evidence.<plan>]` configuration;
- explicit local `capture_root` and per-item paths;
- bounded per-item and total byte limits;
- required/optional items and typed record/artifact kinds;
- only regular files are captured; T7 does not crawl directories or SSH into a Codespace;
- physical containment and symlink-escape rejection;
- secret-prone path/content rejection;
- destination bytes are scanned, sized, and SHA-256 hashed after copy;
- optional omissions remain explicit in the manifest;
- recognized cospaces record schemas contribute bounded per-item provenance;
- fresh bundle creation uses `manifest.json` plus indexed `files/NNNN` payloads and atomic finalization;
- independent validation checks schema, safe stored paths, exact file set, no symlinks, size/hash integrity, and secret markers.

The complete implemented contract is `docs/EVIDENCE_BUNDLES.md`.

### Non-goals
Long-term artifact hosting, automatic third-party upload, workspace snapshots, remote workspace crawling, or secret backup.

## T8 — `matrix` — deferred

Execute comparable operations across explicit dimensions such as refs, repository configurations, fixture parameters, or Codespaces machine profiles and aggregate comparable outcomes. It is not a general distributed scheduler or CI farm. T8 requires a separate activation decision.

## Dependency graph

```text
workspace ---> run ---> verify
    |           |         |
    |           +------> fixture ---> matrix
    |                       |
    +--> checkpoint         +------> evidence
    |
    +--> capabilities

run/checkpoint/verify may all contribute records later consumed by evidence.
```

## Current implementation commitment

T1–T7 are implemented. The real Codespace smoke remains pending evidence debt and #22 remains open T2 hardening debt. T8 remains deferred unless separately activated.
