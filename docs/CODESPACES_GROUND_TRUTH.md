# GitHub Codespaces Ground Truth

This document records the external platform facts the implementation may rely on.

## Current control plane

The initial implementation uses GitHub CLI (`gh`) for Codespaces operations. Relevant commands include `gh codespace create`, `list`, `view`, `ssh`, `stop`, `delete`, `rebuild`, `logs`, `cp`, and `ports`.

`gh codespace create` supports explicit repository, branch, devcontainer path, display name, idle timeout, location, machine, and retention-period options. A successful non-web creation prints the created Codespace name to stdout.

`gh codespace list --json` and `gh codespace view --json` expose machine-readable workspace data including `name`, `repository`, `gitStatus`, `state`, `displayName`, and `machineName`. T1 uses `gitStatus.ref` as the current ref when GitHub supplies it; missing values remain unknown rather than inferred.

When a ref-constrained selection sees candidates whose refs are missing, T1 must fail closed if those unknown candidates prevent proving that exactly one candidate matches. A known matching candidate is not sufficient while another candidate could also match but has unknown metadata.

Controller-side T1 control-plane calls are time-bounded. Expiry is reported as retryable infrastructure failure. That controller timeout is a local wait bound; it is not proof that GitHub cancelled any server-side operation.

## Non-interactive behaviour

GitHub CLI documents `GH_PROMPT_DISABLED`: when set, interactive prompting is disabled. `cospaces` sets it for controller-side `gh` invocations so autonomous operations cannot fall through to interactive repository, machine, devcontainer, or Codespace selectors.

Codespace creation can otherwise prompt when multiple machine or devcontainer choices exist. Callers should provide enough explicit creation options to make creation unambiguous. If GitHub CLI cannot proceed with prompts disabled, `cospaces` reports the control-plane failure rather than choosing implicitly.

T1 passes `--default-permissions` to `gh codespace create`. This accepts the devcontainer's default permissions without prompting; it does not grant requested additional permissions.

After selection, lifecycle operations use an explicit Codespace name.

## T2 SSH execution facts

`gh codespace ssh` accepts an explicit Codespace name and an optional remote command. The Codespace image must provide an SSH server; the default devcontainer image does, while custom images may need the standard devcontainers SSHD feature.

T2 encodes caller argv into one POSIX-shell command using individually quoted arguments and a fixed `set -- ...; "$@"` wrapper. The local controller still invokes `gh` with an argv array and `shell=False`; caller text is never interpreted by a local shell.

T2 also passes OpenSSH `-T` and `-oBatchMode=yes` through `gh codespace ssh`. This disables pseudo-terminal allocation and password/passphrase prompting so an autonomous invocation cannot block on an SSH interaction.

OpenSSH returns the remote command's exit status, but reserves status `255` for SSH errors. T2 therefore treats `255` as transport/ambiguous and does not claim that it is a trustworthy remote-program status.

The captured stderr stream may contain both remote stderr and SSH/GitHub CLI transport diagnostics. T2 reports this as mixed rather than claiming perfect separation. Stdout remains the captured stdout stream.

A controller timeout terminates the local `gh codespace ssh` invocation, but that does not prove the remote process was terminated. Timed-out runs therefore report `remote_completion = "unknown"`.

The current controller process adapter captures stdout/stderr in memory and does not yet impose an output-size bound. This is an implementation hardening limitation, not a Codespaces platform fact; callers should avoid intentionally unbounded-output commands until the adapter is hardened.

GitHub published a Codespaces SSH/logs local command-execution vulnerability affecting GitHub CLI versions through 2.61.0, fixed in 2.62.0. T2 refuses live SSH execution when it can establish that `gh` is older than 2.62.0.

## T4 repository-relative verification facts

GitHub Codespaces exposes `GITHUB_REPOSITORY` as a default environment variable in `owner/repository` form. GitHub's Codespaces/CLI documentation also uses `/workspaces/REPOSITORY-NAME` as the repository checkout path.

T4 uses those documented conventions only to establish the checkout root for repository-relative verification working directories. It derives the repository-name component from `GITHUB_REPOSITORY`, requires `/workspaces/<repository-name>` to exist, and resolves both that root and the requested working directory to physical paths before execution. The target physical path must equal the physical root or remain beneath it, so a repository symlink cannot escape the checkout.

The wrapper text is fixed by `cospaces`. The configured relative directory, environment assignments, and command arguments are passed as positional argv data rather than interpolated into controller shell text. Configuration validation rejects absolute working directories, `..` path components, backslash separators, NULs, and non-finite timeouts.

T4 v1 does not currently observe the remote Git commit SHA. Workspace repository/ref data may be reported when GitHub establishes them, but the controller checkout HEAD is not a valid substitute for the remote Codespace HEAD and must not be copied into a verification record.

This does not imply that arbitrary paths outside the repository checkout are valid verification working directories in v0.1.

## Lifecycle facts

Codespaces preserve saved workspace state across stop/reconnect, while running processes stop when the Codespace stops. Current documented defaults commonly include a 30-minute idle timeout and a 30-day inactive retention period, subject to user or organisation policy. Changes under `/workspaces` survive devcontainer rebuilds; data outside the preserved area may not. Deleting a Codespace deletes unpushed/unexternalised workspace data.

Therefore durable task state must not depend on a continuously running process, and destructive deletion/rebuild is never implicit recovery in the MVP.

## Prebuilds

GitHub Codespaces prebuilds can prepare devcontainer dependencies and configuration before creation. `cospaces` is compatible with prebuilt environments but does not manage prebuild policy in the MVP.

## External references

- https://cli.github.com/manual/gh_codespace
- https://cli.github.com/manual/gh_codespace_create
- https://cli.github.com/manual/gh_codespace_list
- https://cli.github.com/manual/gh_codespace_view
- https://cli.github.com/manual/gh_codespace_ssh
- https://cli.github.com/manual/gh_codespace_stop
- https://cli.github.com/manual/gh_codespace_delete
- https://cli.github.com/manual/gh_help_environment
- https://github.com/cli/cli/security/advisories/GHSA-p2h2-3vg9-4p87
- https://man.openbsd.org/ssh
- https://docs.github.com/en/codespaces/about-codespaces/understanding-the-codespace-lifecycle
- https://docs.github.com/en/codespaces/prebuilding-your-codespaces/configuring-prebuilds
- https://docs.github.com/en/codespaces/developing-in-a-codespace/default-environment-variables-for-your-codespace
- https://docs.github.com/en/codespaces/developing-in-a-codespace/using-github-codespaces-with-github-cli

Implementation agents should verify material CLI behaviour against current official documentation when an issue depends on a flag or lifecycle behaviour not covered by tests.
