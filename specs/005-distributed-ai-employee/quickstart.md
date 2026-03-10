# Quickstart: Platinum Distributed AI Employee

## Purpose

This guide validates the planned Platinum architecture before implementation. It walks through the expected cloud/local setup, synchronization behavior, task claiming, Odoo draft-only flow, and failover handling.

## Prerequisites

- Feature branch `codex/005-distributed-ai-employee` checked out
- Shared vault repository available to both cloud and local nodes
- Separate cloud and local runtime secret stores
- Cloud-accessible Odoo instance behind HTTPS
- Existing Bronze/Silver/Gold vault folders initialized

## Runtime Layout

**Shared (Git-synced)**
- `/Inbox/`, `/Needs_Action/`, `/Plans/`, `/In_Progress/`, `/Updates/`
- `/Pending_Approval/`, `/Approved/`, `/Rejected/`, `/Done/`
- `Dashboard.md` (local-authored only; cloud writes proposals into `/Updates/`)

**Unsynced runtime (local or cloud only)**
- `.runtime/local/` (WhatsApp sessions, browser profiles, payment credentials)
- `.runtime/cloud/` (cloud service tokens, low-privilege credentials)
- `.env`, tokens, private keys, cookie jars, and session files must remain outside Git sync

## 1. Prepare the two-node workspace

1. Provision a cloud working copy of the shared vault repository.
2. Provision a local working copy of the same repository.
3. Confirm both nodes have identical tracked vault state after initial sync.
4. Confirm secret material is absent from the repository and lives only in unsynced runtime storage.

## 2. Validate Cloud Orchestrator boundaries

1. Start the planned cloud orchestration loop.
2. Drop a new file into `/Inbox/`.
3. Confirm the cloud node triages or drafts work into shareable vault state.
4. Move an execution-ready item into `/Approved/`.
5. Confirm the cloud node does not execute it and instead leaves it for Local.

## 3. Validate Git sync behavior

1. Make a cloud-owned change such as a draft or heartbeat update.
2. Run the planned sync workflow: preflight, commit, fetch, rebase, push.
3. Pull the change on Local and confirm it appears cleanly.
4. Create a prohibited cloud-side edit to `Dashboard.md` and confirm the sync policy blocks or diverts it into `/Updates/`.

## 4. Validate claim-by-move ownership

1. Place a task in `/Needs_Action/`.
2. Have Cloud and Local attempt to claim it close together.
3. Confirm only one upstream-visible claim survives after rebase and push.
4. Confirm the losing node records a conflict and does not execute the task.

## 5. Validate draft-only Odoo workflow

1. Simulate an Odoo event that requires accounting review.
2. Confirm the cloud node creates a draft accounting package in shared vault state.
3. Approve the package through the human workflow.
4. Confirm only Local executes the final accounting mutation.

## 6. Validate dashboard federation

1. Publish cloud heartbeat and sync metrics.
2. Publish local heartbeat and approval backlog state.
3. Run the planned Local dashboard merge.
4. Confirm `Dashboard.md` shows cloud health, local health, active claims, and sync latency.

## 7. Validate cloud outage handling

1. Stop cloud heartbeat publication.
2. Wait until the stale threshold is exceeded.
3. Confirm Local marks the cloud node as degraded or offline.
4. Confirm Local temporarily resumes cloud-safe perception tasks while keeping local-only execution boundaries intact.
5. Restart cloud and verify it enters recovery mode, syncs first, and only then resumes normal orchestration.

## Expected Validation Outcomes

- No secret-bearing file is synchronized.
- No `/Approved/` item is executed by Cloud.
- No task is executed by more than one node.
- `Dashboard.md` remains local-authored.
- Odoo activity from Cloud remains draft-only.
- Failover preserves service continuity without violating Local execution authority.
