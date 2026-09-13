# Architecture

## Overview

`cospaces` is a controller-side CLI with a narrow remote-execution contract. It should remain usable by humans, scripts, and autonomous agents without requiring an always-running service.

```text
agent / human / orchestrator
          |
          v
      cospaces CLI
          |
          +--> config + repository metadata
          |
          +--> GitHub CLI adapter ----> GitHub Codespaces control plane
          |                                  |
          |                                  v
          |                            selected Codespace
          |                                  |
          +------------------------ SSH command execution
                                             |
                                             v
                                   repository/workspace files
```

## Component boundaries

### CLI layer
Responsibilities:
- parse commands and arguments;
- select human vs JSON output;
- validate mutually exclusive options;
- map domain errors to stable non-zero exit codes;
- avoid interactive prompts in automation mode.

The CLI must not contain GitHub-specific parsing logic that cannot be unit tested separately.

### Domain/service layer
Responsibilities:
- resolve workspace selection policy;
- coordinate lifecycle operations;
- define run/checkpoint/verify records;
- enforce safety invariants;
- compose lower-level adapters.

This is the primary unit-test target.

### GitHub/Codespaces adapter
Initial implementation wraps `gh codespace ...` and related `gh` commands.

Responsibilities:
- locate the `gh` executable;
- validate authentication/capability preconditions where practical;
- execute subprocesses without shell-string interpolation;
- parse supported JSON output where available;
- map GitHub CLI failures into domain errors;
- never leak secrets in debug/error logs.

All command construction must be explicit argument arrays, not untrusted strings passed through a local shell.

### Remote executor
Initial transport is `gh codespace ssh` with an explicit Codespace selector and a non-interactive remote command.

Responsibilities:
- run against exactly one resolved Codespace;
- preserve remote exit status;
- capture stdout and stderr separately when technically practical;
- apply controller-side timeout/cancellation policy;
- return a structured run record.

The remote command itself is caller-controlled by design. Local interpolation must not accidentally transform it.

### Persistence layer
Used primarily by checkpoint/resume and run/verification history.

MVP rule: durable task state must be representable as repository/workspace files and must use atomic write/replace patterns where possible.

Do not require a database for v0.1.

## Repository-local configuration

Plan for a repository-local file such as `.cospaces.toml` to declare defaults and verification commands. The exact schema is owned by `docs/EXECUTION_CONTRACT.md` and may be introduced incrementally by the implementation issues.

Configuration precedence should be explicit and testable. Recommended order, highest first:

1. CLI argument;
2. environment variable explicitly documented for `cospaces`;
3. repository `.cospaces.toml`;
4. safe built-in default.

Never infer destructive behaviour from a default.

## Stable identifiers

A workspace identity record should distinguish at least:
- GitHub Codespace name;
- repository `owner/name`;
- source ref/branch when available;
- lifecycle state;
- machine/display metadata when available.

Task identity is separate from workspace identity. Multiple tasks may use the same workspace over time, and a task may resume in a replacement workspace after deliberate migration.

## Error model

Use typed/domain errors internally and stable CLI categories externally. At minimum distinguish:
- invalid invocation/configuration;
- missing dependency/authentication;
- no matching workspace;
- ambiguous workspace selection;
- Codespaces lifecycle/control-plane failure;
- remote command timeout;
- remote command non-zero exit;
- persistence/checkpoint corruption;
- verification failure;
- internal/unclassified error.

A remote program exiting `1` is not the same failure category as being unable to reach the Codespace.

## Output model

All MVP tools must support a JSON result mode. JSON objects should include:
- schema/version identifier;
- operation name;
- success boolean;
- timestamp(s) in UTC ISO 8601;
- relevant workspace identity;
- operation-specific payload;
- explicit error object on controller/infrastructure failure.

Do not put human prose on stdout when `--json` is requested. Diagnostics may go to stderr, but secrets must be redacted.

## Idempotency expectations

- `workspace describe/list`: read-only and idempotent.
- `workspace ensure`: should reuse an unambiguous matching workspace according to policy; creation only when requested/allowed.
- `workspace stop`: stopping an already stopped target should be treated as a successful no-op where GitHub behaviour allows.
- `checkpoint save`: replacing the same task checkpoint is expected.
- `checkpoint show`: read-only.
- `verify`: may create result/evidence files, but repeated runs must be independently identifiable.

## Explicit non-goals for v0.1

- hosted control plane;
- multi-tenant service;
- browser dashboard;
- arbitrary job queue;
- automatic parallel fleet scaling;
- secret manager;
- background daemon requirement;
- opaque AI decision engine;
- generic SSH replacement.

## Extensibility

Second-tranche tools should compose through domain interfaces rather than parse CLI text from MVP tools. For example, `matrix` should call workspace/run/fixture services internally, not shell out to `cospaces run` and scrape output.
