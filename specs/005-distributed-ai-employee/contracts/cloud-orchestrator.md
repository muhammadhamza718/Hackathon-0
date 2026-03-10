# Contract: Cloud Orchestrator

## Skill

`cloud-orchestrator`

## Purpose

Run always-on Platinum perception on the cloud node while respecting the Local execution boundary.

## Inputs

- Shared vault root
- Cloud node runtime configuration
- Odoo monitoring configuration
- Social drafting triggers
- Sync status and claim visibility

## Allowed Operations

- Scan `/Inbox/`
- Create triage outputs in shared state
- Monitor Odoo and prepare draft accounting packages
- Draft social and communication artifacts
- Publish node heartbeat and sync summaries
- Write merge candidates to `/Updates/`

## Forbidden Operations

- Execute `/Approved/` items
- Publish final messages or posts
- Initiate WhatsApp sessions
- Execute payments or financial mutations
- Write `Dashboard.md` directly
- Sync or expose secrets

## Interface

### `run_cycle(context) -> CloudCycleResult`
Performs one orchestration cycle and returns created drafts, alerts, heartbeats, and skipped actions.

### `triage_inbox(item) -> TriageArtifact`
Routes a new inbox item into shared vault state.

### `prepare_accounting_draft(event) -> AccountingDraft`
Creates a local-approval-ready accounting package without mutating Odoo.

### `publish_heartbeat(status) -> NodeHeartbeat`
Writes cloud heartbeat state into the updates area.

## Guarantees

- Every irreversible action is deferred to Local.
- Every created artifact is auditable in the shared vault.
- Any local-only task is reported as deferred, never executed.
