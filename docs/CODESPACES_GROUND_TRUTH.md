# GitHub Codespaces Ground Truth

This document records the external platform facts the implementation may rely on.

## Current control plane

The initial implementation uses GitHub CLI (`gh`) for Codespaces operations. Relevant commands include `gh codespace create`, `list`, `view`, `ssh`, `stop`, `delete`, `rebuild`, `logs`, `cp`, and `ports`.

`gh codespace create` supports explicit repository, branch, devcontainer path, display name, idle timeout, location, machine, and retention-period options. A successful non-web creation prints the created Codespace name to stdout.

`gh codespace list --json` and `gh codespace view --json` expose machine-readable workspace data including `name`, `repository`, `gitStatus`, `state`, `displayName`, and `machineName`. T1 uses `gitStatus.ref` as the current ref when GitHub supplies it; missing values remain unknown rather than inferred.

## Non-interactive behaviour

GitHub CLI documents `GH_PROMPT_DISABLED`: when set, interactive prompting is disabled. `cospaces` sets it for controller-side `gh` invocations so autonomous operations cannot fall through to interactive repository, machine, devcontainer, or Codespace selectors.

Codespace creation can otherwise prompt when multiple machine or devcontainer choices exist. Callers should provide enough explicit creation options to make creation unambiguous. If GitHub CLI cannot proceed with prompts disabled, `cospaces` reports the control-plane failure rather than choosing implicitly.

T1 passes `--default-permissions` to `gh codespace create`. This accepts the devcontainer's default permissions without prompting; it does not grant requested additional permissions.

After selection, lifecycle operations use an explicit Codespace name.

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
- https://docs.github.com/en/codespaces/about-codespaces/understanding-the-codespace-lifecycle
- https://docs.github.com/en/codespaces/prebuilding-your-codespaces/configuring-prebuilds

Implementation agents should verify material CLI behaviour against current official documentation when an issue depends on a flag or lifecycle behaviour not covered by tests.
