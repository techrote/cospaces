# Checkpoint and Resume Contract

Checkpointing is a first-class programme primitive. It exists because Codespaces may stop, controller processes may disappear, chats may lose context, and implementation may be handed to another agent.

A checkpoint is **not** a process snapshot. It is a durable, structured continuation record.

## Storage

Default repository-relative location:

```text
.cospaces/checkpoints/<task-id>.json
```

Task IDs must be sanitised/validated so a caller cannot escape the checkpoint directory through path traversal.

Checkpoint state may be committed when appropriate, or left as workspace state for short-lived continuation. The tool must make that distinction visible. Valuable implementation work should ultimately be committed and pushed; a checkpoint alone is not a substitute for source control.

## Minimum schema intent

A checkpoint should be capable of recording:

```json
{
  "schema": "cospaces.checkpoint/v1",
  "task_id": "issue-17",
  "created_at": "...",
  "updated_at": "...",
  "repository": "owner/repo",
  "ref": "feature/issue-17",
  "head": "git-sha-or-null",
  "workspace": {
    "name": "..."
  },
  "working_tree": {
    "dirty": true,
    "summary": "machine-generated bounded summary"
  },
  "progress": {
    "completed": ["..."],
    "current": "...",
    "next": "..."
  },
  "records": {
    "last_run_id": "...",
    "last_verification_id": null,
    "paths": []
  },
  "notes": "bounded human/agent continuation note"
}
```

Field names can be refined in the implementation PR, but the semantic distinctions must remain.

## Save semantics

`checkpoint save` should:
1. validate task ID and input;
2. gather safe repository state when requested/available;
3. construct a complete new checkpoint document;
4. write it atomically where practical (temporary sibling + replace);
5. preserve enough previous-state evidence to recover from accidental replacement or corruption;
6. validate the file just written;
7. emit structured success/failure.

Do not partially rewrite the live checkpoint in place if a crash can leave malformed JSON.

## Resume semantics

The MVP does not automatically execute the `next` instruction. Resume means recovering and presenting validated continuation context.

A later agent should be able to establish:
- which task this is;
- which repository/ref/commit the checkpoint describes;
- whether the current workspace still matches it;
- whether there were uncommitted changes;
- what had been completed;
- what was in progress;
- what the intended next step was;
- where relevant run/verification/evidence records live.

If the current repo/HEAD differs materially from the checkpoint, report the mismatch. Do not silently declare the checkpoint resumed.

## Secret avoidance

Never capture:
- full environment dumps;
- GitHub tokens;
- SSH keys;
- credential-helper output;
- arbitrary `.env` content;
- command output unless explicitly supplied as a bounded note/reference.

Prefer references to result files over embedding large logs.

## History

MVP must retain at least one prior valid version or otherwise make accidental overwrite diagnosable. Acceptable simple designs include:
- a `.history/` sibling with timestamped previous versions;
- append-only checkpoint revisions plus a current pointer;
- bounded previous-document backup.

Avoid a database.

## Validation

`checkpoint validate` should detect at least:
- malformed JSON;
- missing required fields;
- unsupported schema version;
- invalid task ID/path;
- impossible basic types;
- optionally, repo/workspace mismatch when live context is requested.

## Tests required

- fresh save;
- overwrite/update;
- history/backup behaviour;
- atomic-write failure simulation where practical;
- invalid/malicious task IDs;
- malformed checkpoint;
- unsupported schema;
- dirty vs clean working-tree representation;
- no secret/environment capture by default;
- show/list behaviour;
- mismatch reporting.
