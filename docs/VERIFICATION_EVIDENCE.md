# Verification, Fixtures, Evidence, and Matrix Contracts

This document defines the shared semantics for T4 and the later T6–T8 tools.

## Verification principles

Verification answers a narrow question: **did the repository-declared checks required for this change pass?**

It does not replace code review or product judgement.

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

Each check supports:
- unique bounded name within the plan;
- command argv;
- timeout, default 600 seconds;
- required/optional flag, default required;
- optional repository-relative working directory;
- optional explicit string environment overrides.

Unknown/misspelled keys, duplicate names, invalid timeout/types, empty executable, or unsafe working directory make the plan invalid before any remote command runs.

T4 executes checks sequentially. This gives deterministic order and avoids implicit resource contention. All checks run through T2 `RunService`; T4 contains no second Codespaces/SSH transport.

The first T2 run may resolve the workspace from repository/ref. Once resolved, later checks target that exact Codespace name so one verification cannot silently hop between workspaces.

## Aggregate status

- all required checks pass => verification passes;
- any required check has a remote non-zero result or timeout => verification fails with category `7` after later declared checks are still collected;
- optional remote failure/timeout is recorded prominently but does not fail the required aggregate;
- malformed verification configuration is a usage/configuration failure and performs no remote work;
- inability to select/reach/run in the workspace is a lower-layer selection/infrastructure failure, not a failed check assertion;
- a non-remote T2 failure aborts the sequence and marks the verification record incomplete.

Only failures that T2 classifies as `remote` become check outcomes. This preserves the distinction between “the test failed” and “the test could not be run.”

## Verification record v1

T4 emits schema `cospaces.verify/v1` inside the normal `cospaces.result/v1` envelope.

Semantic fields:

```json
{
  "schema": "cospaces.verify/v1",
  "verification_id": "uuid",
  "plan": "default",
  "task_id": "issue-42",
  "correlation_id": "agent-pass-3",
  "repository": "owner/repo",
  "ref": "main",
  "head": "git-sha-or-null",
  "workspace": {},
  "started_at": "...",
  "finished_at": "...",
  "complete": true,
  "passed": true,
  "checks": [
    {
      "name": "tests",
      "required": true,
      "passed": true,
      "timed_out": false,
      "run_id": "...",
      "exit_code": 0,
      "remote_completion": "success",
      "duration_ms": 1234,
      "failure_code": null,
      "command": ["python", "-m", "pytest", "-q"],
      "working_directory": ".",
      "environment_keys": ["MODE"]
    }
  ]
}
```

Every invocation gets a unique `verification_id`. That ID is also the T2 correlation ID for constituent runs; caller task/correlation metadata remains separately visible at verification level.

Per-check stdout/stderr is not duplicated into the aggregate record. The T2 `run_id` is the evidence reference, accompanied by bounded exit/timeout/completion/duration/failure metadata. Configured environment **values** are not copied into the aggregate; only keys are listed.

Repository/ref/HEAD/workspace provenance is included where established. Unknown values remain null rather than inferred.

For v0.1 the JSON result written to stdout is the authoritative verification report. Automatic report-file persistence is intentionally deferred; T3 can durably reference the `verification_id` in `records.last_verification_id`.

## T6 fixture semantics

A fixture is a reproducible experiment or benchmark definition. Unlike `verify`, a fixture may care about metrics and assertions rather than only exit status.

Candidate fixture fields:
- fixture ID/name;
- command/runner;
- input files/config;
- seed;
- timeout;
- declared outputs;
- metrics parser/format;
- assertions/thresholds;
- tags/suite.

A fixture result must bind to repository/ref/HEAD and workspace identity so comparisons have provenance.

For simulation-engine use, examples include deterministic state hashes, mass conservation, tick-time distributions, active-chunk counts, or benchmark throughput.

Do not invent domain-specific physics semantics in the generic tool; repositories declare their own fixture commands and machine-readable metrics.

## T7 evidence semantics

Evidence packages selected records and artifacts without indiscriminately archiving the workspace.

Manifest should include:
- evidence schema/version;
- evidence ID;
- task/correlation ID when present;
- repository/ref/HEAD;
- workspace identity;
- controller/tool versions;
- timestamps;
- included files with hashes/sizes/content type where practical;
- source run/verification/fixture IDs;
- explicit redaction/exclusion notes.

Security requirements:
- do not include Git credentials, SSH material, `.env` files, or unbounded home-directory content;
- inclusion should be allowlist/config based;
- hash generated artifacts after capture;
- avoid following symlinks outside approved roots unless explicitly safe and documented.

## T8 matrix semantics

A matrix is bounded repeated execution across explicit dimensions. It should consume existing service interfaces rather than shelling out to its own CLI.

Initial useful dimensions:
- refs/branches/commits;
- repository configuration values;
- fixture parameters;
- Codespaces machine profiles.

Matrix result should make each cell independently inspectable and aggregate only comparable metrics/statuses.

Start sequentially. Parallel Codespace fleet management is not required for the first matrix implementation.

## Evidence quality hierarchy

Prefer, in order:
1. machine-readable result generated by the actual command/check;
2. captured immutable-ish output artifact with hash;
3. bounded raw logs;
4. agent-authored prose summary.

Prose is useful context but should not be the only evidence for a claim that can be mechanically checked.
