# Verification, Fixtures, Evidence, and Matrix Contracts

This document defines the shared semantics for T4 and T6–T8.

## Verification principles

Verification answers a narrow question: **did the repository-declared checks required for this change pass?** It does not replace code review or product judgement.

A verification plan is repository-controlled, explicit, bounded, and machine-readable. Commands are argv arrays rather than shell strings.

## T4 verification plans

T4 reads named plans from `.cospaces.toml`:

```toml
[verify.default]

[[verify.default.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]
timeout_seconds = 600
required = true
working_directory = "."
environment = { MODE = "ci" }
```

Each check supports a unique bounded name, command argv, finite timeout, required/optional flag, repository-relative working directory, and explicit string environment overrides. Unknown keys, duplicate names, invalid timeouts, empty executable, or unsafe working directory fail before remote work.

T4 executes checks sequentially through T2 in one pinned workspace. Before a declared command starts, its fixed wrapper resolves the Codespace checkout root and working directory physically and proves the working directory remains under the repository checkout.

## T4 aggregate/result semantics

- all required checks pass => verification passes;
- required genuine remote non-zero/timeout => category `7`, while later declared checks are still collected;
- optional failures remain visible without failing the required aggregate;
- malformed config => usage/configuration failure;
- selection/transport/setup failure keeps its lower-layer category and does not become a test assertion;
- repository-root/working-directory setup failure => `verification_environment_error`, incomplete verification.

T4 emits `cospaces.verify/v1` inside `cospaces.result/v1`. Per-check stdout/stderr is not duplicated into the aggregate; T2 `run_id` plus bounded outcome metadata is the evidence reference. T4 v1 does not observe remote Git HEAD, so `head` is null rather than borrowing controller-local provenance.

## T6 fixture definition v1

T6 is implemented as `cospaces fixture` and runs repository-controlled reproducible experiments/benchmarks through T2.

```bash
cospaces fixture bench --repo owner/repo --ref main --json
cospaces fixture bench --codespace NAME --json
```

A fixture is defined in `.cospaces.toml`:

```toml
[fixture.bench]
command = ["python", "bench.py"]
timeout_seconds = 60
working_directory = "bench"
tags = ["perf", "smoke"]
seed = 42
inputs = ["fixtures/input.json"]
outputs = ["out/result.bin"]
metrics_format = "json-last-line"

[fixture.bench.parameters]
size = 1000
mode = "fast"

[[fixture.bench.assertions]]
metric = "throughput"
operator = ">="
value = 10
```

Supported fields:
- bounded fixture name and command argv;
- finite positive timeout;
- repository-relative POSIX working directory;
- bounded tags;
- optional string/integer seed;
- bounded scalar parameter table;
- repository-relative input/output path lists;
- metrics format `none` or `json-last-line`;
- bounded scalar assertions using `==`, `!=`, `>`, `>=`, `<`, `<=`.

Unknown keys or malformed values fail before remote fixture execution.

## T6 reproducibility and containment

T6 computes a canonical SHA-256 digest of the normalized fixture definition. Before the task starts it observes the selected remote checkout's Git HEAD through T2; failure to establish a valid remote SHA prevents experiment execution rather than substituting controller-local state.

The task wrapper physically resolves `/workspaces/<repository>`, the declared working directory, and every declared input. Working-directory or input symlink escape is rejected. After a successful task, every declared output is checked for existence and physical containment through another T2 invocation.

All remote actions use T2 and are pinned to the first selected workspace. T6 implements no independent SSH/Codespaces transport.

Seed and parameters are provided to the task as explicit environment assignments:
- `COSPACES_FIXTURE_SEED`;
- `COSPACES_FIXTURE_PARAM_<UPPERCASE_NAME>`.

These values are configuration metadata, not a secret channel. Fixture definitions must not place credentials or secret values in seed/parameters.

## T6 metrics and assertions

With `metrics_format = "json-last-line"`, the final non-empty stdout line must be a bounded JSON object whose keys are bounded strings and whose values are finite scalar JSON values. Earlier stdout may contain ordinary progress text.

Assertions are evaluated against parsed metrics. Numeric ordering operators require numeric, non-boolean values; equality/inequality work on supported scalar values. Missing/incomparable metrics yield explicit failed assertion records rather than implicit coercion.

## T6 result v1

T6 emits `cospaces.fixture/v1` inside `cospaces.result/v1`.

The record includes:
- unique `fixture_run_id`;
- fixture name and canonical `definition_digest`;
- primary task T2 `task_run_id` plus supporting T2 run IDs;
- repository/ref and **remotely observed pre-execution HEAD**;
- workspace identity;
- declared command, working directory, tags, seed, parameters, inputs and outputs;
- metrics format and parsed scalar metrics;
- structured assertion outcomes;
- timestamps/duration;
- `complete`, `passed`, and `failure_code`.

Failure classes remain distinct:
- configuration/name errors;
- provenance/environment/working-directory/input containment errors;
- genuine remote fixture task failure;
- output missing/escape/check failure;
- metrics parse failure;
- assertion failure;
- lower-layer selection/infrastructure failures.

A task/setup/output failure produces an incomplete failed fixture record when a task run exists. Metrics/assertion failure occurs after the task/output work completed and therefore records `complete = true`, `passed = false`.

T6 references declared outputs rather than copying their bytes. T7 is responsible for any later allowlisted evidence capture.

## T7 evidence semantics

Evidence packages selected records and artifacts without indiscriminately archiving the workspace.

A T7 manifest should include:
- evidence schema/version and evidence ID;
- task/correlation metadata where present;
- repository/ref/HEAD where actually established;
- workspace/controller provenance;
- timestamps;
- selected run/verification/fixture/checkpoint records;
- selected artifacts/logs with hashes and sizes;
- explicit optional omissions and exclusion/redaction notes.

Security requirements:
- explicit allowlisted capture roots/paths;
- never broad-capture credential stores, SSH material, GitHub tokens, `.env`, home directories, or entire workspaces;
- reject traversal and symlink escape;
- hash captured destination bytes after capture;
- missing required and optional artifacts remain distinguishable.

## T8 matrix semantics

A matrix is bounded repeated execution across explicit dimensions and should consume existing service interfaces rather than add another transport. Initial useful dimensions include refs/commits, repository configuration, fixture parameters, and Codespaces machine profiles; start sequentially.

## Evidence quality hierarchy

Prefer, in order:
1. machine-readable result generated by the actual command/check;
2. captured artifact with hash;
3. bounded raw logs;
4. agent-authored prose summary.

Prose is context, not a substitute for mechanically obtainable evidence.
