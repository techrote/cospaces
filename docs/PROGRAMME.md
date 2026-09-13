# Programme Definition

## Goal

Build a small, dependable suite of GitHub Codespaces utilities that make long-horizon autonomous development more reproducible and resumable.

The intended user is an agent or controller that already has repository-level instructions/RAG documentation and needs a prepared remote execution environment. `cospaces` should provide a narrow operational layer between that agent and GitHub Codespaces rather than becoming another general-purpose IDE or agent framework.

## Core proposition

A repository can contain two complementary forms of operational knowledge:

- **semantic instructions**: why and when an agent should perform an operation;
- **machine contracts**: what operations exist, how they are invoked, and what structured result is returned.

`cospaces` supplies the second layer while remaining easy to document in the first.

## MVP success condition

Version 0.1 is successful when an autonomous agent can, without interactive shell selection dialogs:

1. identify or create the intended Codespace for a repository/ref/task;
2. execute a non-interactive command there and receive an unambiguous structured result;
3. record enough durable state that another session can understand what happened and continue;
4. invoke repository-declared verification and receive a structured pass/fail result;
5. handle common failures without corrupting state or silently choosing the wrong workspace.

The MVP does **not** need to be a general orchestration daemon, queue, dashboard, hosted service, or replacement for GitHub CLI.

## Design principles

### Thin wrapper, strong contract
Prefer delegating to supported GitHub CLI/Codespaces behaviour over reimplementing GitHub APIs. Add value through deterministic selection, validation, structured output, persistence, and composition.

### Non-interactive by default
Autonomous execution must never depend on a TTY prompt to choose a repository, Codespace, branch, or destructive action. Ambiguous selection is an error unless an explicit policy resolves it.

### JSON is an interface, not decoration
Every MVP operation must have a stable machine-readable result suitable for another program or agent. Human-readable output may coexist, but structured output must be tested.

### Repository state outranks process state
Important continuation state belongs in files under the workspace/repository or in explicitly exported artifacts. A stopped Codespace, lost SSH session, controller restart, or chat context reset must not make the task unintelligible.

### Safe lifecycle behaviour
Never delete, rebuild, or force-discard a workspace merely to simplify recovery. Destructive operations require explicit user/agent intent and must make unsaved-work risk visible.

### Evidence before confidence
A successful command invocation is not the same as verified work. The verification tool exists to make acceptance explicit.

### Cost-aware, not cost-optimising
Surface machine/lifecycle information relevant to cost, but do not invent an automatic cost optimiser in v0.1.

## Technology direction

The initial implementation should use Python 3.11+ unless an implementation issue documents a compelling reason to change. The command-line surface should be available as a `cospaces` package/console script with subcommands corresponding to the eight programme tools.

GitHub CLI (`gh`) is the initial Codespaces control-plane dependency. Prefer invoking `gh` with machine-readable flags where available and `gh codespace ssh ... <command>` for remote execution. Keep subprocess invocation behind testable adapters so later direct API or SSH implementations remain possible.

## Security boundary

The controller may execute commands inside a Codespace that the caller is already authorised to access. It must not:

- log GitHub tokens, SSH private keys, environment secrets, or authentication headers;
- silently broaden GitHub permissions;
- upload arbitrary local secret files;
- make public port visibility a default;
- treat remote command output as trusted structured data unless parsing is explicit;
- perform destructive lifecycle operations without an explicit operation requesting them.

## Scope boundary

`cospaces` is **not** responsible for deciding product requirements, generating implementation code for target repositories, reviewing arbitrary code quality, or replacing repository-specific RAG documentation. It provides execution primitives those agents can use.

## First implementation tranche

The initial tranche implements exactly four tools:

- `workspace`
- `run`
- `checkpoint`
- `verify`

Later tool issues may refine interfaces during planning, but should not be merged ahead of the MVP dependency chain unless doing so is clearly non-disruptive.
