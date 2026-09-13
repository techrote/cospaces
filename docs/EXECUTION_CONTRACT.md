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
- operation-specific domain failure (for example a remote command returning non-zero) must be represented structurally and also produce an appropriate non-zero controller exit unless an explicit option requests observation-only semantics;
- do not expose secrets in output.

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

On controller/infrastructure failure:

```json
{
  "schema": "cospaces.result/v1",
  "operation": "workspace.ensure",
  "ok": false,
  "started_at": "...",
  "finished_at": "...",
  "workspace": null,
  "result": null,
  "error": {
    "code": "ambiguous_workspace",
    "message": "...",
    "retryable": false
  }
}
```

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

## T1 `workspace` candidate surface

```text
cospaces workspace list --repo owner/repo --json
cospaces workspace describe --codespace NAME --json
cospaces workspace ensure --repo owner/repo [--ref BRANCH] [--create] --json
cospaces workspace create --repo owner/repo [creation options] --json
cospaces workspace stop --codespace NAME --json
```

Later explicit operations may add rebuild/delete, but neither should occur implicitly.

Selection precedence for `ensure` should prefer explicit codespace name when supplied, otherwise filter by repository/ref/task metadata according to documented policy. More than one equally valid candidate is an ambiguity error, not permission to choose randomly.

## T2 `run` candidate surface

```text
cospaces run --codespace NAME -- command arg1 arg2
cospaces run --repo owner/repo [selection options] -- command arg1 arg2
cospaces run --codespace NAME --timeout 10m --json -- command arg1
```

The parser must preserve the remote command argument boundary after `--`. Implementations may encode the command safely for remote execution, but must not accidentally execute it in the local shell.

Target run payload:

```json
{
  "run_id": "uuid-or-equivalent",
  "command": ["command", "arg1"],
  "timeout_seconds": 600,
  "exit_code": 0,
  "timed_out": false,
  "stdout": "...",
  "stderr": "...",
  "transport": "gh-codespace-ssh"
}
```

If the transport cannot reliably separate remote stderr from transport diagnostics in the initial implementation, document the limitation explicitly rather than pretending separation is exact. Preserve enough raw information to diagnose failure.

## T3 `checkpoint` candidate surface

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

History may live under a sibling directory or bounded history array; exact mechanism belongs to implementation, but accidental truncation/corruption must be detectable.

Checkpoint data is defined in `docs/CHECKPOINT_RESUME.md`.

## T4 `verify` candidate surface

```text
cospaces verify [PLAN] --codespace NAME --json
cospaces verify --repo owner/repo --json
```

Repository configuration should support named checks similar to:

```toml
[verify.default]

[[verify.default.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]
timeout_seconds = 600
required = true

[[verify.default.checks]]
name = "lint"
command = ["ruff", "check", "."]
timeout_seconds = 120
required = true
```

Exact TOML syntax may be adjusted for a cleaner parser, but commands should prefer arrays over shell strings.

Verification result should contain each check's run record or reference, required/optional status, duration, and aggregate pass/fail.

## Configuration

Planned repository file:

```text
.cospaces.toml
```

MVP should keep the schema intentionally small. Unknown keys should either be rejected with a useful error or preserved/ignored according to an explicitly tested forward-compatibility policy; do not silently misspell important settings.

## Exit-code policy

Define a small stable mapping during foundation implementation. Recommended categories:

- `0`: operation succeeded / verification passed;
- `2`: invocation/configuration error;
- `3`: dependency/auth/control-plane unavailable;
- `4`: selection/not-found/ambiguity error;
- `5`: remote command completed unsuccessfully or timed out;
- `6`: checkpoint/persistence error;
- `7`: required verification failed;
- `1`: unexpected internal failure.

The exact numeric mapping may be changed once before `0.1.0`, but must then be documented and covered by tests.

## Correlation

Every remote run and verification should have a generated ID. If the caller supplies a task ID/correlation ID, preserve it separately rather than replacing the unique run ID.

## Logging

Human logs may be verbose with an explicit flag. Machine JSON must stay parseable. Redact values that resemble known credential channels; more importantly, avoid collecting sensitive environment/configuration in the first place.
