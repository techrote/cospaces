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

## T5 — `capabilities` — Phase 2 — implemented

### Purpose
Report what the current controller and one selected Codespace can actually do while keeping repository-declared intent separate from live observations.

### Interface

```bash
cospaces capabilities --codespace NAME --json
cospaces capabilities --repo owner/repo [--ref REF] --json
```

The nested result schema is `cospaces.capabilities/v1`.

### Live observations
- controller cospaces version;
- controller GitHub CLI presence/version when observable;
- successful T1 target resolution / Codespaces access;
- remote OS and architecture through bounded T2 probes;
- repository-configured bounded argv probes with optional version regex extraction.

Each observation is explicitly one of:
- `present` — the requested fact was positively established;
- `absent` — the probe established the executable/capability is missing;
- `unavailable` — the probe could not complete because of timeout/lower-layer failure;
- `unknown` — the probe ran but the requested fact could not be established, such as an unparseable required version.

### Repository declarations
`.cospaces.toml` may declare `[capabilities.supports]` booleans and `[[capabilities.probes]]`. Declared support remains a separate `declared_support` object and is never promoted to observed fact.

Example:

```toml
[capabilities.supports]
build = true
headless_render = false

[[capabilities.probes]]
name = "python"
command = ["python", "--version"]
timeout_seconds = 10
version_regex = "Python ([0-9.]+)"
```

### Safety rules
- resolve one workspace through T1 and pin all remote probes to it;
- execute remote probes only through T2; no duplicate transport;
- no automatic install/repair;
- no environment dump or credential inspection;
- finite bounded timeouts/argv/config sizes;
- do not infer capabilities from documentation or prose.

### Non-goals
Package management, environment repair, dependency installation, or claiming repository-declared support is live evidence.

## T6 — `fixture` — Phase 2 — activated next

### Purpose
Run reproducible, declarative experiments/benchmarks inside a workspace.

A fixture identifies inputs, seed/configuration, command, timeout, expected assertions/metrics, and output locations. It produces a provenance-bearing result suitable for comparison and later evidence collection while using existing T1/T2 transport semantics.

### Non-goals
Notebook platform, scientific workflow engine, arbitrary DAG system, or automatic scientific interpretation.

## T7 — `evidence` — Phase 2 — activated after T6

### Purpose
Create a provenance-bearing, allowlisted evidence bundle for selected run/verification/fixture/checkpoint records and artifacts.

Bundles must use deterministic manifests, explicit capture roots/paths, hashes/sizes, traversal and symlink protections, and visible optional omissions. They must never default to broad workspace/home capture or secret-prone content.

### Non-goals
Long-term artifact hosting, automatic third-party upload, workspace snapshots, or secret backup.

## T8 — `matrix` — Phase 2 — deferred

### Purpose
Execute comparable operations across explicit dimensions such as refs, repository configurations, fixture parameters, or Codespaces machine profiles and aggregate comparable outcomes.

### Non-goals
General distributed scheduler or CI farm.

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

T1–T4 are the completed MVP. D026 explicitly activates the Phase 2 sequence T5 → T6 → T7 while leaving the real Codespace smoke pending as evidence debt; T8 remains deferred unless separately activated.
