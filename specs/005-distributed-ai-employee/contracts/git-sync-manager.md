# Contract: Git Sync Manager

## Skill

`git-sync-manager`

## Purpose

Synchronize cloud and local vault state through a deterministic Git workflow with ownership-aware conflict handling.

## Inputs

- Repository root
- Node identity (`cloud` or `local`)
- Sync policy rules
- Current working tree state

## Workflow

1. Preflight repository and excluded-path checks
2. Stage allowed tracked changes only
3. Create node-scoped sync commit
4. Fetch remote state
5. Rebase local changes on remote head
6. Apply ownership conflict policy
7. Push if clean
8. Emit sync result record

## Interface

### `preflight(repo_state) -> SyncPreflightResult`
Fails if excluded files are staged or ownership policy is already violated.

### `sync_once(node_id) -> SyncState`
Runs one full pull-rebase-push cycle and returns the sync result.

### `resolve_conflicts(conflicts) -> ConflictResolution`
Applies policy for dashboard, plan, claim, and approval conflicts.

### `emit_sync_status(sync_state) -> SyncState`
Writes node sync metrics for dashboard consumption.

## Conflict Rules

- Local wins `Dashboard.md`
- Only the active owner may update claimed work and active plans
- Local wins `/Approved/`, `/Rejected/`, and final execution records
- Unhandled conflicts stop push and create an explicit conflict artifact
