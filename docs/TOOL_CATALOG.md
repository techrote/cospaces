# Tool Catalog

The programme defines eight composable utilities. They may share one `cospaces` executable and internal package; “tool” means a coherent command/service contract, not necessarily a separate binary.

## T1 — `workspace` — MVP

### Purpose
Resolve, inspect, create, start/reuse, stop, and explicitly manage the Codespace intended for a task.

### Required v0.1 capabilities
- list/describe accessible Codespaces for a repository;
- deterministic non-interactive selection;
- `ensure` semantics: reuse an unambiguous suitable workspace or create one when creation is explicitly allowed;
- explicit create options for repository/ref and supported machine/devcontainer/lifecycle settings;
- stop a selected workspace;
- expose JSON workspace identity/state;
- fail safely on ambiguity.

### Safety rules
- deletion/rebuild may be exposed only as explicit operations, never as automatic recovery;
- do not force-delete work by default;
- do not silently switch to a workspace for a different repository/ref because the preferred one is unavailable.

### Non-goals
Scheduling, fleet scaling, billing optimisation, prebuild management.

## T2 — `run` — MVP

### Purpose
Execute one non-interactive command inside exactly one resolved Codespace and return a structured run record.

### Required v0.1 capabilities
- explicit workspace target or deterministic resolution through T1;
- remote execution via supported transport (`gh codespace ssh` initially);
- command timeout;
- capture exit outcome and output;
- distinguish remote program non-zero exit from controller/transport failure;
- JSON result mode;
- optional run metadata such as task ID/correlation ID.

### Safety rules
- no local shell interpolation of caller-provided remote command;
- no automatic retry of commands that may have side effects unless the retry is explicitly requested/idempotent;
- redact obvious authentication material from controller diagnostics.

### Non-goals
Persistent interactive terminals, PTY emulation, general SSH replacement.

## T3 — `checkpoint` — MVP

### Purpose
Persist task continuation state so a stopped Codespace, lost controller process, or new chat/agent can resume intentionally.

### Required v0.1 capabilities
- create/update checkpoint for a task ID;
- show/list checkpoints;
- validate schema/version;
- record repository/ref/HEAD, workspace identity, dirty-state summary, completed/current/next step, relevant result/evidence paths, and timestamps;
- atomic writes where practical;
- machine-readable output;
- preserve previous state/history sufficiently to diagnose accidental overwrite or corruption.

### Safety rules
- checkpointing must not claim work is committed when it is only dirty/untracked;
- checkpoint files must not capture secrets or entire environment dumps;
- resumption is advisory/contextual, not arbitrary code execution from untrusted checkpoint text.

### Non-goals
Full chat-memory persistence or process snapshotting.

## T4 — `verify` — MVP

### Purpose
Execute repository-declared checks as an explicit acceptance operation and emit a structured result.

### Required v0.1 capabilities
- define a small verification-plan schema in `.cospaces.toml` or an associated repository file;
- named checks with command, timeout, and required/optional semantics;
- sequential execution in MVP unless there is a compelling simpler design;
- preserve each check's run result;
- aggregate overall status;
- JSON report written to stdout and optionally to a file;
- non-zero process status when required verification fails.

### Safety rules
- configuration is repository-controlled executable intent: show what is being run and do not silently add commands;
- optional checks must be visibly optional, not silently ignored failures.

### Non-goals
General CI replacement, code-review judgement, flaky-test prediction.

---

## T5 — `capabilities` — Phase 2

### Purpose
Report what the current controller/workspace can actually do, separating documented intent from live environment truth.

Candidate output includes:
- controller version/schema versions;
- `gh` presence/version/auth viability;
- Codespaces access;
- workspace OS/architecture;
- configured repository capabilities;
- presence/version of declared executables;
- support flags for build/test/benchmark/headless-render operations declared by the target repo.

Capabilities should be declarative facts, not promises inferred from RAG prose.

### Non-goals
Installing missing tools automatically in the first implementation.

## T6 — `fixture` — Phase 2

### Purpose
Run reproducible, declarative experiments/benchmarks inside a workspace.

A fixture should identify inputs, seed/configuration, command or runner, timeout, expected assertions/metrics, and output locations. It should produce a result record suitable for comparison and evidence collection.

This is particularly useful for simulation/engine repositories where correctness and performance need repeatable scenarios.

### Non-goals
Notebook platform, scientific workflow engine, or arbitrary DAG system.

## T7 — `evidence` — Phase 2

### Purpose
Create a provenance-bearing evidence bundle for a task/run/verification.

Candidate contents:
- manifest with schema version;
- repository/ref/commit/workspace identity;
- timestamps and controller version;
- run/verification JSON records;
- selected logs/artifacts;
- hashes and sizes;
- explicit exclusions/redactions.

Evidence should be deterministic enough to inspect and archive, but must avoid secrets and unbounded directory capture.

### Non-goals
Long-term artifact hosting service.

## T8 — `matrix` — Phase 2

### Purpose
Execute comparable operations across explicit dimensions and aggregate results.

Candidate dimensions:
- git refs;
- repository configurations;
- fixture parameters;
- Codespaces machine profiles where available.

MVP of this later tool should begin with bounded sequential execution; parallel fleet management is optional future work.

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

## Initial implementation commitment

Only T1–T4 are committed for the first implementation tranche. T5–T8 receive executable planning issues now so they are ready for later autonomous execution, but those issues should remain deferred until the MVP is stable unless a later explicit decision changes sequencing.
