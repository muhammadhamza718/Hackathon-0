# Contract: Local Executive

## Skill

`local-executive-control`

## Purpose

Own all Platinum actions that require approval, identity, money movement, or dashboard authorship.

## Inputs

- Shared vault state including `/Approved/` and `/Updates/`
- Local runtime secrets and session material
- Active claims and node heartbeat data

## Allowed Operations

- Execute `/Approved/` items
- Perform WhatsApp and payment actions
- Publish final send/post actions
- Merge `/Updates/` into `Dashboard.md`
- Enter single-node mode during cloud outage

## Forbidden Operations

- Delegate local-only actions back to Cloud
- Bypass HITL
- Publish secrets into the shared vault

## Interface

### `execute_approved(item) -> ExecutionReceipt`
Consumes an approved artifact and performs the final action.

### `merge_updates(update_batch) -> DashboardMergeResult`
Merges cloud-provided updates into the local dashboard view.

### `enter_single_node_mode(reason) -> NodeHeartbeat`
Expands local behavior during cloud outage without violating Local-only rules.
