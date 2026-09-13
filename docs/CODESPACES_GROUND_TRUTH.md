# GitHub Codespaces Ground Truth

This document records the external platform facts the implementation may rely on. Keep it narrow and update it when GitHub behaviour or CLI contracts change.

## Current control plane

The initial implementation uses GitHub CLI as the supported controller interface.

Relevant commands currently include:
- `gh codespace create`
- `gh codespace list`
- `gh codespace view`
- `gh codespace ssh`
- `gh codespace stop`
- `gh codespace delete`
- `gh codespace rebuild`
- `gh codespace logs`
- `gh codespace cp`
- `gh codespace ports`

`gh codespace create` currently supports explicit repository, branch, devcontainer path, display name, idle timeout, location, machine, and retention-period options.

`gh codespace ssh` can target a specific Codespace and execute a command non-interactively. A compatible SSH server must exist in the Codespace image; Debian-based devcontainers can add the standard devcontainers SSHD feature if needed.

## Lifecycle facts

GitHub documents Codespaces as persistent cloud development environments whose VM/workspace state survives stopping and reconnecting, but whose running processes stop when the Codespace stops.

Current documented defaults include:
- default idle timeout: 30 minutes, unless changed by user/org policy;
- stopped Codespaces retain saved workspace state;
- inactive Codespaces are normally automatically deleted after the configured retention period, commonly 30 days by default;
- retention is bounded by GitHub policy and may be shorter under organisation policy;
- changes under `/workspaces` are preserved across a devcontainer rebuild, while changes outside it may be cleared;
- deleting the Codespace deletes its unpushed/unexternalised workspace data.

Therefore checkpointing must not depend on a continuously running process, and durable valuable work should eventually be committed/pushed or otherwise exported.

## Prebuilds

GitHub Codespaces prebuilds can prepare devcontainer dependencies/configuration before a Codespace is created. `cospaces` should be compatible with prebuilt environments but does not manage prebuild policy in the MVP.

## Non-interactive safety assumptions

The controller should always pass an explicit Codespace name to lifecycle and SSH operations after selection. Do not rely on GitHub CLI's interactive selector in autonomous flows.

Never use forced deletion as ordinary cleanup when uncommitted work might exist.

## External references

Official sources used for this programme definition:
- https://cli.github.com/manual/gh_codespace
- https://cli.github.com/manual/gh_codespace_create
- https://cli.github.com/manual/gh_codespace_ssh
- https://cli.github.com/manual/gh_codespace_stop
- https://cli.github.com/manual/gh_codespace_delete
- https://docs.github.com/en/codespaces/about-codespaces/understanding-the-codespace-lifecycle
- https://docs.github.com/en/codespaces/prebuilding-your-codespaces/configuring-prebuilds

Implementation agents should verify material CLI behaviour against current official documentation when an issue depends on a flag or lifecycle behaviour not already covered by tests.
