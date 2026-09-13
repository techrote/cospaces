# Execution Contract

This document defines the intended external behaviour of the CLI and machine-readable records. It is a design contract for implementation issues; exact field names may be refined during the corresponding PR only if this document and tests are updated in the same change.

## CLI shape

Single top-level executable/package:

```text
cospaces <tool> <operation> [options]
```

Planned tools:

```text
cospaces workspace ...
cospaces run ...
cospaces checkpoint ...
cospaces verify ...
cospaces capabilities ...
cospaces fixture ...
cospaces evidence ...
cospaces matrix ...
```

Every implemented tool must expose `--help` and support a JSON mode for operations intended for automation.

## Global automation rules

- never require an interactive selector in JSON/automation mode;
- stdout in JSON mode is one valid JSON document unless a command explicitly documents JSON Lines;
- human diagnostics belong on stderr;
- timestamps are UTC ISO 8601 with timezone indication;
- controller failures produce non-zero process exit status;
- operation-specific domain failure must be represented structurally and also produce an appropriate non-zero controller exit unless an explicit option requests observation-only semantics;
- do not collect controller secrets/environment material merely for diagnostics.

## Common result envelope

Target shape:

```json
{
  "schema": "cospaces.result/v1",
  "operation": "run",
  "ok": true,
  "started_at": "2026-09-13T17:00:00Z",
  "finished_at": "2026-09-13T17:00:01Z",
  "workspace": {},
  "result": {},
  "error": null
}
```

On controller/infrastructure failure the envelope has `ok: false` and an error object. Operations such as T2 and T4 may still include a partial/failed `result` record when that record is diagnostically meaningful.

The user-facing message may evolve; error `code` values should be treated as compatibility-sensitive once tests use them.

## Workspace identity

Minimum machine representation should include available values for:

```json
{
  "name": "...",
  "repository": "owner/repo",
  "ref": "branch-or-ref-if-known",
  "state": "available|shutdown|starting|unknown",
  "display_name": "...",
  "machine": "..."
}
```

Do not fabricate fields that GitHub cannot establish. Unknown information should be absent/null rather than guessed.

## T1 `workspace`

```text
cospaces workspace list --repo owner/repo --json
cospaces workspace describe --codespace NAME --json
cospaces workspace ensure --repo owner/repo [--ref BRANCH] [--create] --json
cospaces workspace create --repo owner/repo [creation options] --json
cospaces workspace stop --codespace NAME --json
```

Later explicit operations may add rebuild/delete, but neither should occur implicitly.

Selection precedence for `ensure` prefers explicit Codespace name when supplied, otherwise filters by repository/ref according to documented policy. More than one equally valid candidate is an ambiguity error, not permission to choose randomly. When a ref is requested, incomplete candidate ref metadata is also a selection failure if it prevents proving that exactly one candidate matches; a known match is not selected while another candidate could still match but has an unknown ref.

T1 GitHub Codespaces control-plane calls are bounded by a controller timeout. Expiry is reported as retryable infrastructure failure (`codespaces_control_plane_timeout`, exit category `3`) rather than waiting indefinitely. This bound is a controller safeguard, not evidence that GitHub cancelled an operation server-side.

## T2 `run`

```text
cospaces run --codespace NAME -- command arg1 arg2
cospaces run --repo owner/repo [--ref BRANCH] -- command arg1 arg2
cospaces run --codespace NAME --timeout 10m --json -- command arg1
```

The `--` task boundary is mandatory. T2 preserves caller argv as tokens, quotes each token for the remote POSIX shell, and sends one fixed `set -- ...; "$@"` remote command through `gh codespace ssh`. Caller text is never interpreted by a local shell.

Run payload:

```json
{
  "run_id": "uuid",
  "command": ["command", "arg1"],
  "task_id": null,
  "correlation_id": null,
  "timeout_seconds": 600.0,
  "exit_code": 0,
  "timed_out": false,
  "remote_completion": "success",
  "transport": "gh-codespace-ssh",
  "stdout": "...",
  "stderr": "...",
  "stderr_mixed": true,
  "duration_seconds": 0.42,
  "started_at": "...",
  "finished_at": "..."
}
```

`remote_completion` is `success`, `failed`, `unknown`, or `not_started`. OpenSSH status `255` is classified as transport/ambiguous rather than a trustworthy remote-program status. Timeout also leaves remote completion unknown because terminating the local SSH transport does not prove the remote process ended.

The captured stderr stream may mix remote stderr with SSH/GitHub CLI diagnostics; `stderr_mixed: true` records that limitation explicitly. T2 does not claim byte-perfect provenance for stderr.

Failure categories include:
- invocation/configuration failure: exit category 2;
- workspace selection failure: exit category 4;
- GitHub CLI/SSH transport failure: exit category 3;
- remote non-zero completion or timeout: exit category 5;
- remote success: exit 0.

T2 validates the timeout and argv before workspace lookup. Direct API callers therefore cannot use non-finite/non-positive timeouts or NUL-bearing argv to trigger controller/transport work before an eventual usage failure.

T2 performs no implicit retry. Every invocation gets a unique run ID; caller task/correlation IDs are preserved separately.

T2 does not inspect or serialize controller credential stores or environment variables. It does capture caller-selected task argv/stdout/stderr by design. A caller that executes a secret-printing task can therefore place that task-controlled data in the run record; such commands should not be used when the record will be persisted or shared.

### T2 v0.1 resource limitation

The current process adapter captures stdout/stderr through `subprocess.run`. Output volume is therefore not bounded at the adapter layer, and a controller timeout cannot prove descendant/remote process termination. Remote completion remains `unknown` on timeout for this reason. A future process-adapter hardening change should bound/spool output and improve local process-tree cleanup without pretending it can prove remote termination.

## T3 `checkpoint`

```text
cospaces checkpoint save --task TASK-ID [fields/options] --json
cospaces checkpoint show --task TASK-ID --json
cospaces checkpoint list --json
cospaces checkpoint validate --task TASK-ID --json
```

Target storage location:

```text
.cospaces/checkpoints/<task-id>.json
```

Exact checkpoint data and bounded prior-revision semantics are defined in `docs/CHECKPOINT_RESUME.md`.

## T4 `verify`

```text
cospaces verify [PLAN] --codespace NAME --json
cospaces verify [PLAN] --repo owner/repo [--ref BRANCH] --json
```

The default plan name is `default`. Verification requires an explicit Codespace or repository target. It reads `.cospaces.toml` from `--root` (default current directory), validates the complete plan before remote execution, and executes checks sequentially through the T2 `RunService`. T4 does not implement another SSH/GitHub transport.

### Verification configuration

Named plans use this schema:

```toml
[cospaces]
schema_version = 1

[verify.default]

[[verify.default.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]
timeout_seconds = 600
required = true
working_directory = "."
environment = { MODE = "ci" }

[[verify.default.checks]]
name = "advisory"
command = ["python", "-V"]
required = false
```

Rules:
- a plan contains 1–64 checks;
- check names are unique and use the same bounded identifier grammar as plan names;
- `command` is a non-empty argv array, not a shell string;
- the executable (`command[0]`) must be non-empty; later argv items may be empty strings;
- timeout defaults to 600 seconds and must be finite and within `(0, 86400]`;
- `required` defaults to true;
- `working_directory` is optional, POSIX, repository-relative, bounded, and cannot contain `..` or be absolute;
- `environment` is optional and contains at most 64 explicit POSIX variable-name/string-value pairs;
- unknown plan/check keys are configuration errors rather than being silently ignored;
- duplicate check names are configuration errors.

Checks execute from the Codespace repository checkout root by default. A configured working directory is first resolved to its physical path (`pwd -P`) beneath the physical repository root, so a repository symlink cannot escape the checkout. The configured directory and command remain positional argv data rather than being interpolated into controller shell text.

Failure to establish the repository root, enter the requested directory, or prove physical containment is `verification_environment_error`: an infrastructure failure with an incomplete verification record, not a repository check assertion failure.

### Verification record

Schema `cospaces.verify/v1`:

```json
{
  "schema": "cospaces.verify/v1",
  "verification_id": "uuid",
  "plan": "default",
  "task_id": "issue-42",
  "correlation_id": "agent-pass-3",
  "repository": "owner/repo",
  "ref": "main",
  "head": null,
  "workspace": {"name": "codespace-name"},
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
      "run_id": "uuid",
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

Environment **values** are not copied into verification records. Per-check stdout/stderr is owned by the underlying T2 run record; the T4 aggregate keeps its `run_id` and bounded outcome summary rather than duplicating logs.

Every verification receives a unique `verification_id`. That ID is used as the T2 correlation ID for each check; caller `task_id` remains separate. After the first check resolves a repository-selected workspace, subsequent checks target that exact Codespace name.

### Aggregate and failure semantics

- every required check succeeds => `complete=true`, `passed=true`, controller exit `0`;
- required remote non-zero or timeout => check remains visible, later checks continue, aggregate `passed=false`, final `verification_failed`, exit category `7`;
- optional remote non-zero or timeout => check remains visible but does not fail the required aggregate;
- malformed configuration/unknown plan => no remote work, exit category `2`;
- T1 selection/not-found/ambiguity => preserve exit category `4`;
- T2 dependency/auth/transport/control-plane failure => stop the sequence, `complete=false`, preserve exit category `3` (or the lower-layer category actually returned);
- T4 repository-root/working-directory setup or containment failure => stop the sequence, `complete=false`, exit category `3`;
- only genuine T2 remote-task failures are treated as check outcomes; controller/environment failures are not relabelled as assertion failures.

Repository/ref provenance is taken from the resolved workspace when available. **T4 v1 does not currently observe the remote Git commit SHA**, so `head` is null. The controller checkout HEAD must never be copied into a remote verification record merely because repository/ref strings happen to match. Unknown provenance remains null rather than guessed.

For v0.1 the JSON result on stdout is authoritative; T4 does not automatically create a persistent report file. T3 may reference the `verification_id` in `records.last_verification_id`.

## Configuration

Repository file:

```text
.cospaces.toml
```

`[cospaces]` currently accepts only `schema_version = 1`; unknown keys in that control table are rejected. T4 claims the `[verify]` top-level section and validates its selected plan strictly. Other top-level sections remain uninterpreted/reserved for later tools.

## Exit-code policy

- `0`: operation succeeded / verification passed;
- `2`: invocation/configuration error;
- `3`: dependency/auth/control-plane/transport/environment unavailable;
- `4`: selection/not-found/ambiguity error;
- `5`: standalone T2 remote command completed unsuccessfully or timed out;
- `6`: checkpoint/persistence error;
- `7`: required verification failed;
- `1`: unexpected internal failure.

The mapping is compatibility-sensitive and covered by tests.

## Correlation

Every remote run and verification has a generated ID. If the caller supplies a task ID/correlation ID, preserve it separately rather than replacing the unique operation ID. T4 uses its `verification_id` as the correlation ID of constituent T2 runs so they can be grouped mechanically.

## Logging

Human logs may be verbose with an explicit flag. Machine JSON must stay parseable. Avoid collecting sensitive controller environment/configuration in the first place. Verification environment values are repository-controlled executable inputs and are intentionally omitted from aggregate verification records.
