# Implementation Plan: Platinum Distributed AI Employee

**Branch**: `codex/005-distributed-ai-employee` | **Date**: 2026-03-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-distributed-ai-employee/spec.md`

## Summary

Implement Platinum Tier as a distributed cloud-local operating model on top of the existing Bronze, Silver, and Gold stack. The design keeps the vault as the shared source of truth, uses Git as the synchronization backbone, enforces claim-by-move ownership before any execution, preserves local-only control for secret-bearing and high-risk actions, hardens the cloud Odoo path behind HTTPS and health checks, and extends `Dashboard.md` into a local-authored executive view of both nodes. The implementation is organized as modular Agent Skills, led by a `cloud-orchestrator` skill for always-on perception and a `git-sync-manager` skill for deterministic vault synchronization.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase standard)
**Primary Dependencies**: Existing `agents/` and `agents/gold/` modules, `requests`, `python-dotenv`, `pydantic`, Git CLI, Browser MCP client, Odoo JSON-RPC over HTTPS
**Storage**: Obsidian Markdown vault + JSON logs, Git remote for shared state replication, cloud-hosted Odoo Community for accounting data, no new database
**Testing**: pytest unit/integration/e2e suites, distributed workflow fixtures, contract validation for Markdown-based skill interfaces
**Target Platform**: Linux cloud VM for always-on orchestration plus Windows/Linux/macOS local workstation for executive execution
**Project Type**: Single Python project extended with a new `agents/platinum/` package and Platinum-specific Agent Skills
**Performance Goals**: Cloud perception actions surfaced within 5 minutes, sync loop convergence within 2 minutes under nominal conditions, dashboard status refresh within 1 minute, zero duplicate execution events
**Constraints**: Vault remains source of truth; Git is primary sync; `Dashboard.md` is local-only writer; all high-risk actions remain behind HITL; secrets and private sessions never sync; cloud credentials are lower privilege than local credentials
**Scale/Scope**: Single operator, 2 active nodes (cloud/local), 1 Git remote, 1 Odoo instance, shared vault state for inbox, plans, approvals, updates, and audit records

## Constitution Check

_Gate: Must pass before Phase 0 research. Re-check after Phase 1 design._

- **Platinum Boundary Check**: PASS. Cloud responsibilities are limited to triage, monitoring, and drafting. Local remains the sole executor for `/Approved/`, WhatsApp, payments, and final send/post actions.
- **HITL Check**: PASS. All high-risk actions still require `/Approved/` and local execution. No cloud-side bypass path is introduced.
- **Secret Isolation Check**: PASS. Sync scope excludes `.env`, tokens, cookies, browser profiles, and any security sidecars. Cloud uses separate low-privilege credentials.
- **Single-Writer Dashboard Check**: PASS. `Dashboard.md` remains local-authored only. Cloud writes merge candidates into `/Updates/`.
- **Claim-by-Move Check**: PASS. Ownership is established via `/In_Progress/<agent>/` plus upstream sync confirmation before execution is allowed.
- **Cloud Odoo Draft-Only Check**: PASS. Cloud Odoo access is limited to monitoring, heartbeat, and draft creation. Final accounting mutation remains local-only.

**Post-Phase-1 Re-check**: PASS. Research, data model, contracts, and quickstart all preserve the Platinum constitution without introducing conflicting write paths or secret-sync leakage.

## Project Structure

### Documentation (this feature)

```text
specs/005-distributed-ai-employee/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- cloud-orchestrator.md
|   |-- git-sync-manager.md
|   |-- claim-manager.md
|   |-- local-executive.md
|   `-- odoo-health-monitor.md
`-- tasks.md
```

### Source Code (repository root)

```text
agents/
|-- constants.py                 # Extend with Platinum tier, folders, statuses, action types
|-- dashboard_writer.py          # Extend to render node heartbeats, sync lag, ownership
|-- reconciler.py                # Reuse for plan/task visibility
|-- hitl_gate.py                 # Reuse for local approval enforcement
|-- gold/
|   |-- odoo_rpc_client.py       # Reuse for Odoo read/draft execution paths
|   |-- social_bridge.py         # Reuse for drafting flows
|   `-- safety_gate.py           # Reuse threshold enforcement
|-- platinum/
|   |-- __init__.py
|   |-- cloud_orchestrator.py    # Always-on cloud perception and drafting
|   |-- local_executive.py       # Local-only execution router
|   |-- git_sync_manager.py      # Pull-rebase-push orchestration and exclusion policy
|   |-- claim_manager.py         # Claim-by-move ownership, leases, handoffs
|   |-- heartbeat_monitor.py     # Node heartbeat publishing and outage detection
|   |-- dashboard_federator.py   # Local dashboard merge from updates and heartbeats
|   |-- sync_policy.py           # Conflict rules and file ownership classification
|   |-- odoo_health_monitor.py   # HTTPS heartbeat, backup checks, credential scoping
|   |-- config.py                # Platinum node configuration loading
|   `-- models.py                # Shared Platinum data models
`-- skills/
    |-- platinum_cloud_orchestrator/
    |   `-- SKILL.md
    |-- git_sync_manager/
    |   `-- SKILL.md
    |-- local_executive_control/
    |   `-- SKILL.md
    `-- distributed_claim_manager/
        `-- SKILL.md

tests/
|-- unit/
|   |-- test_platinum_claim_manager.py
|   |-- test_platinum_git_sync_manager.py
|   |-- test_platinum_heartbeat_monitor.py
|   |-- test_platinum_dashboard_federator.py
|   `-- test_platinum_odoo_health_monitor.py
|-- integration/
|   |-- test_platinum_cloud_local_boundary.py
|   |-- test_platinum_claim_conflict_resolution.py
|   |-- test_platinum_sync_rebase_flow.py
|   |-- test_platinum_cloud_failover.py
|   `-- test_platinum_odoo_draft_workflow.py
`-- e2e/
    `-- test_platinum_distributed_workflow.py
```

**Structure Decision**: Extend the current single-project Python layout with a dedicated `agents/platinum/` package that composes existing Bronze/Silver/Gold modules instead of replacing them. This keeps current behavior stable while isolating the new distributed-system concerns into explicit modules and skills.

---

## Architecture: Distributed Component Design

### 1. Distributed Work-Zone Orchestration

**Primary skills**: `cloud-orchestrator`, `local-executive-control`

The orchestration boundary is capability-based, not folder-presence-based. Both nodes can read shared vault state, but only the Cloud node can perform always-on perception and only the Local node can execute secret-bearing or high-risk actions.

**Cloud-owned behaviors**:
- Scan `/Inbox/` and route new items into actionable state.
- Monitor Odoo for business events and prepare accounting drafts or alerts.
- Draft social content and approval artifacts.
- Publish heartbeat and sync status into `/Updates/heartbeats/` and `/Updates/sync/`.
- Create merge candidates for dashboard-relevant updates without touching `Dashboard.md`.

**Local-owned behaviors**:
- Execute all `/Approved/` items.
- Own WhatsApp sessions, browser sessions with personal identity, and bank-level payment flows.
- Publish final send/post actions after approval.
- Merge `/Updates/` into the authoritative `Dashboard.md`.
- Detect cloud outage and enter temporary single-node mode.

**Boundary rule**:
- Cloud stops at `drafted`, `pending_approval`, `monitoring`, or `update-proposed` state.
- Local starts at `approved`, `execute-now`, or any secret-bound workflow.
- Any action involving reputation, money, identity, or live credentials is automatically routed to Local.

**Execution flow**:
1. Cloud detects work.
2. Cloud claims or drafts work when allowed by policy.
3. Cloud syncs its new state upstream.
4. Local receives synced state.
5. Local merges updates, handles approvals, and performs final execution.

### 2. Git-Sync Infrastructure

**Primary skill**: `git-sync-manager`

Each node runs the same sync loop against the shared vault repository, but with different file ownership rules.

**Sync loop**:
1. Preflight: verify working tree contains only allowed tracked changes; reject if excluded files are staged.
2. Stage only allowed shared-state files.
3. Commit with a node-scoped message such as `sync(cloud): triage and drafts` or `sync(local): approvals and dashboard`.
4. `git fetch --all --prune`
5. `git pull --rebase origin <branch>`
6. Apply conflict policy:
   - `Dashboard.md`: local version always wins; cloud must never commit direct edits.
   - `/Plans/`: only current owner may append or change active steps; non-owner changes are diverted to `/Updates/plans/`.
   - `/In_Progress/`: conflicting claims are resolved by earliest upstream-visible claim commit; loser must stand down.
   - `/Approved/`, `/Rejected/`, `/Done/Actions/`: local is authoritative.
7. Push only after conflict policy passes.
8. Emit sync result and lag metrics to `/Updates/sync/<node>.json`.

**Conflict-prevention strategy**:
- File ownership matrix enforced before commit.
- Cloud writes proposals to `/Updates/` instead of editing local-owned files.
- Execution may not begin until a claim commit has rebased cleanly and been pushed successfully.
- On unresolved conflict, node enters read-only safe mode for the affected artifact and raises an alert instead of guessing.

### 3. Atomic Action Locking (Claim-by-Move)

**Primary skill**: `distributed-claim-manager`

A task is not executable until it is both moved into `/In_Progress/<agent>/` and the claim is visible upstream.

**Claim protocol**:
1. Candidate task starts in `/Needs_Action/`.
2. Agent moves the file into `/In_Progress/<agent>/`.
3. Agent writes a small claim sidecar with node id, claim timestamp, claim nonce, and lease expiry.
4. Agent syncs the claim commit upstream.
5. Only after successful push may the claiming node execute the next irreversible step.

**High-latency prevention**:
- If both nodes claim concurrently before syncing, the first claim visible on the rebased branch wins.
- The losing node must move its duplicate claim into `/Updates/conflicts/` and may not execute.
- Lease heartbeat refresh extends active ownership while work is in progress.
- Stale claims can only be reclaimed after lease expiry plus a grace window, and the takeover must be logged with the original owner preserved in history.

**No-double-execution rule**:
- Final actions require both a valid local approval decision and an active, upstream-confirmed claim.
- Cloud is never permitted to execute final actions, so only local duplicate-execution risk remains for `/Approved/`, which is prevented by claim confirmation and approval consumption.

### 4. Secret and PII Isolation

**Primary skills**: `git-sync-manager`, `local-executive-control`

The sync root contains only shareable state. Secrets and sensitive session material live outside the synchronized path or inside gitignored runtime directories.

**Isolation strategy**:
- `.env`, token files, SSH keys, browser profiles, WhatsApp sessions, cookie jars, and auth caches live in unsynced runtime paths such as `.runtime/local/`, `.runtime/cloud/`, or OS-native secret stores.
- Sensitive sidecars produced during automation are stored in gitignored runtime directories and referenced indirectly from shareable Markdown state when necessary.
- Cloud credentials are separate service accounts with read and draft permissions only.
- PII sanitation happens before content is written into the shared vault; raw sensitive payloads stay in local runtime storage when retention is necessary.
- Sync preflight blocks commit when a secret-bearing path or forbidden pattern is detected.

### 5. Cloud Odoo Security and Health

**Primary skills**: `odoo-health-monitor`, `cloud-orchestrator`

The cloud Odoo path is a hardened service boundary, not a direct open application.

**Deployment path**:
- Reverse proxy terminates HTTPS and forwards only approved traffic to the Odoo service.
- Odoo is reachable through a restricted network policy and protected service account.
- Automated backups run on a fixed schedule with retention policy and restore verification.
- JSON-RPC heartbeat monitor calls a safe read endpoint such as version or authenticated lightweight read to confirm health.

**Cloud Odoo rule set**:
- Cloud performs read, monitor, and draft-only workflows.
- Draft accounting packages are written into the vault for local approval.
- Any write that would mutate financial truth is deferred until Local executes after approval.
- Health checks publish status into `/Updates/heartbeats/odoo-cloud.json` and dashboard merge candidates.

### 6. High-Availability Logic

**Primary skills**: `heartbeat-monitor`, `local-executive-control`, `dashboard-federator`

Both nodes publish heartbeats, but the Local node is responsible for interpreting cloud outages for operational continuity.

**Heartbeat design**:
- Cloud writes `node=cloud`, role, software version, last sync time, last successful Odoo heartbeat, and current queue counts.
- Local writes equivalent local heartbeat state for dashboard completeness.
- Heartbeats refresh on a fixed interval and are merged into `Dashboard.md` only by Local.

**Outage handling**:
- If the cloud heartbeat exceeds the stale threshold, Local marks the cloud node as degraded.
- Local enters temporary single-node mode and resumes cloud-safe perception duties such as inbox triage, Odoo monitoring, and drafting, while preserving local-only execution rules.
- When cloud returns, it first performs a sync-only catch-up cycle and remains read-only until its state converges and no claim conflicts remain.
- Dashboard shows one of: healthy, degraded, offline, recovering.

---

## Research Output Summary

Phase 0 resolves the planning questions with six decisions captured in [research.md](./research.md): boundary enforcement, Git workflow, claim conflict handling, secret isolation, cloud Odoo hardening, and cloud-failover logic.

## Data Model and Contracts

Phase 1 introduces the distributed entities in [data-model.md](./data-model.md) and the operational contracts in `contracts/`:
- [cloud-orchestrator.md](./contracts/cloud-orchestrator.md)
- [git-sync-manager.md](./contracts/git-sync-manager.md)
- [claim-manager.md](./contracts/claim-manager.md)
- [local-executive.md](./contracts/local-executive.md)
- [odoo-health-monitor.md](./contracts/odoo-health-monitor.md)

## Agent Skill Definitions

| Skill | Purpose | Allowed Actions | Blocked Actions | Primary Modules |
|---|---|---|---|---|
| `cloud-orchestrator` | Run always-on perception, Odoo monitoring, and draft generation in the cloud | Triage, draft, monitor, publish heartbeat, write `/Updates/` | `/Approved/` execution, WhatsApp, payments, final send/post, direct dashboard writes | `agents/platinum/cloud_orchestrator.py`, `agents/platinum/heartbeat_monitor.py`, `agents/platinum/odoo_health_monitor.py` |
| `git-sync-manager` | Keep cloud and local vaults synchronized through deterministic Git workflows | Preflight, stage allowed files, fetch, rebase, push, emit sync metrics, open conflict alerts | Sync secret paths, auto-resolve prohibited ownership conflicts, overwrite local-owned files from cloud | `agents/platinum/git_sync_manager.py`, `agents/platinum/sync_policy.py` |
| `local-executive-control` | Own final execution, approvals, dashboard merge, and outage fallback | Execute `/Approved/`, merge `/Updates/`, maintain dashboard, perform local-only actions | Delegate local-only actions back to cloud, bypass HITL, sync secrets | `agents/platinum/local_executive.py`, `agents/platinum/dashboard_federator.py` |
| `distributed-claim-manager` | Establish and reconcile task ownership across nodes | Claim, lease refresh, handoff, release, stale-takeover logging | Execute without upstream-confirmed claim, silently override another owner | `agents/platinum/claim_manager.py`, `agents/platinum/models.py` |
| `odoo-health-monitor` | Verify Odoo health and create draft accounting work for Local review | HTTPS heartbeat, backup verification, draft package creation | Financial finalization, approval bypass, privilege escalation | `agents/platinum/odoo_health_monitor.py`, `agents/gold/odoo_rpc_client.py` |

## Quickstart and Validation

[quickstart.md](./quickstart.md) defines the validation path for local and cloud setup, sync verification, conflict testing, stale-heartbeat detection, and draft-only Odoo workflows.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New `agents/platinum/` package | Distributed orchestration, sync policy, and node health are cross-cutting concerns that do not fit cleanly into existing Bronze/Silver/Gold modules | Mixing Platinum behavior into existing modules would blur local/cloud boundaries and make ownership rules harder to test |
| Git-based synchronization loop | Platinum requires shared vault state across cloud and local nodes | Manual copy or ad hoc sync cannot provide deterministic conflict handling or auditable ownership history |
| Lease-backed claim protocol | High-latency distributed execution can produce simultaneous claims | A plain folder move without upstream confirmation cannot safely prevent double-execution |
| Local-only dashboard writer with `/Updates/` merge path | Platinum constitution forbids shared writes to `Dashboard.md` | Allowing both nodes to edit the dashboard directly would create recurring sync conflicts and stale executive summaries |
