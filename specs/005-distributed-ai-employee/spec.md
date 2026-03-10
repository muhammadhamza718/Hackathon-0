# Feature Specification: Platinum Distributed AI Employee

**Feature Branch**: `codex/005-distributed-ai-employee`  
**Created**: 2026-03-09  
**Status**: Draft  
**Input**: User description: "Implement Platinum Tier: The Distributed AI Employee. The goal is to evolve the system into a 24/7 Cloud-Local Hybrid architecture.

Technical Requirements:
1. Cloud Engine (24/7 Always-On): Configure the AI Orchestrator to run on a Cloud VM (e.g., Oracle/AWS) for continuous perception (Inbox triage, Odoo monitoring, and social media drafting).
2. Local Executive Engine: Define the 'Local-Only' action boundaries. The Local agent owns WhatsApp sessions, bank-level payments, and final execution of all /Approved items.
3. Git-Based Vault Sync: Implement Git as the primary synchronization mechanism between Cloud and Local vaults. Define 'Conflict Resolution' rules for Markdown state files.
4. Security Gating (Secret Isolation): Prohibit the synchronization of .env files and security tokens to the cloud. Cloud agent MUST operate using its own distinct, lower-privilege credentials.
5. Atomic Ownership (Claim-by-move): Implement a folder-based locking system (/In_Progress/<agent>/) to prevent race conditions during distributed execution.
6. Cloud-Hardened Odoo Integration: Finalize the cloud-deployment of Odoo Community via HTTPS, ensuring the Cloud agent can draft accounting entries for Local approval.
7. Executive Dashboard: Update Dashboard.md to reflect the status of both Cloud and Local nodes, including health heartbeats and sync-latency indicators.

All features must be implemented as modular [Agent Skills] compliant with the Platinum Law Constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Continuous Cloud Perception (Priority: P1)

As an operator, I want the cloud node to monitor incoming work and business signals continuously so that inbox items, Odoo changes, and social drafting opportunities are triaged without waiting for the local machine to be online.

**Why this priority**: Continuous perception is the foundation of the Platinum model. Without it, the system remains session-bound and cannot deliver 24/7 value.

**Independent Test**: Can be fully tested by introducing new inbox items, accounting events, and social drafting prompts while the local node is offline and verifying that the cloud node creates the expected triage, draft, and monitoring artifacts.

**Acceptance Scenarios**:

1. **Given** a new item enters `/Inbox/`, **When** the cloud node detects it, **Then** the item is triaged into the shared vault with the required metadata and next-step state.
2. **Given** Odoo monitoring detects a business event that needs review, **When** the cloud node processes it, **Then** it creates a draft or alert artifact without executing a financial mutation.
3. **Given** a social publishing request is present, **When** the cloud node prepares content, **Then** it saves a draft artifact for later approval instead of publishing it.

---

### User Story 2 - Local Executive Control (Priority: P2)

As the executive operator, I want the local node to remain the only node allowed to execute high-risk and private actions so that cloud autonomy never bypasses human safety or secret custody.

**Why this priority**: The Platinum architecture only remains safe if execution authority stays local for reputation-sensitive, payment-sensitive, and secret-bearing actions.

**Independent Test**: Can be fully tested by presenting approved actions, WhatsApp tasks, and payment tasks to both nodes and verifying that only the local node may execute them while the cloud node stops at draft or monitoring state.

**Acceptance Scenarios**:

1. **Given** an item is moved into `/Approved/`, **When** execution is attempted, **Then** the local node can execute it and the cloud node cannot.
2. **Given** a WhatsApp, payment, or final send/post task exists, **When** the cloud node encounters it, **Then** it records the need for local handling and does not execute the task.
3. **Given** a cloud-drafted accounting entry is ready, **When** local review is completed, **Then** final execution happens only through the local node after approval.

---

### User Story 3 - Reliable Shared Vault Synchronization (Priority: P3)

As an operator managing both nodes, I want the cloud and local vaults to synchronize through a controlled Git workflow with deterministic conflict handling so that shared Markdown state stays trustworthy and secret material never leaves the local trust boundary.

**Why this priority**: A distributed system only works if both nodes share consistent state without syncing secrets or silently losing edits.

**Independent Test**: Can be fully tested by editing the two vaults independently, running synchronization, and verifying that business state merges correctly, secret-bearing files are excluded, and conflicts are surfaced or resolved by policy.

**Acceptance Scenarios**:

1. **Given** one node creates new task and draft state files, **When** synchronization runs, **Then** the other node receives those shared-state changes without receiving excluded secret files.
2. **Given** both nodes edit the same Markdown state file, **When** synchronization detects the overlap, **Then** the system resolves it according to the declared ownership rules or creates an explicit conflict artifact for review.
3. **Given** `Dashboard.md` changes on both nodes, **When** synchronization occurs, **Then** the local version remains authoritative and the cloud-side update is preserved as a merge candidate rather than overwriting the dashboard.

---

### User Story 4 - Distributed Ownership and Visibility (Priority: P4)

As an operator, I want task ownership, node health, and sync freshness to be visible in one executive dashboard so that I can trust which node owns each task and quickly detect degraded distributed behavior.

**Why this priority**: Distributed execution introduces coordination risk; clear ownership and health visibility prevent duplicate work and unnoticed failures.

**Independent Test**: Can be fully tested by having both nodes claim work, pause heartbeats, and delay synchronization while verifying that ownership, stale node status, and sync lag appear accurately in `Dashboard.md`.

**Acceptance Scenarios**:

1. **Given** both nodes attempt to work the same task, **When** one node claims it by moving it into `/In_Progress/<agent>/`, **Then** that node becomes the only active owner and the other node is blocked from execution.
2. **Given** one node stops reporting health, **When** the heartbeat freshness exceeds the allowed threshold, **Then** the dashboard marks that node as stale or degraded.
3. **Given** synchronization is delayed, **When** the lag exceeds the allowed threshold, **Then** the dashboard shows the sync-latency warning and the affected node states.

---

### Edge Cases

- What happens when Cloud and Local attempt to claim the same `/Needs_Action/` task at nearly the same time?
- How does the system handle conflicting edits to the same Markdown state file during a sync cycle?
- What happens when a secret-bearing file is accidentally placed inside a syncable folder?
- How does the system behave when the cloud node loses Odoo connectivity or its reduced-privilege credentials are insufficient for a requested action?
- What happens when the local node is offline while `/Approved/` items accumulate?
- How does the dashboard represent stale heartbeats, missing syncs, or interrupted ownership handoffs?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a continuously running cloud node that performs perception tasks for inbox triage, Odoo monitoring, and social drafting.
- **FR-002**: The cloud node MUST convert detected work into triage records, drafts, alerts, or approval-ready artifacts without executing local-only actions.
- **FR-003**: The local node MUST be the exclusive executor for WhatsApp sessions, bank-level payments, final send/post actions, and execution of items in `/Approved/`.
- **FR-004**: The system MUST prevent the cloud node from executing any local-only action even when the related task state is visible in the shared vault.
- **FR-005**: The system MUST use Git as the primary synchronization method between cloud and local vaults.
- **FR-006**: The system MUST define deterministic conflict-resolution rules for shared Markdown state files, including explicit ownership rules for `Dashboard.md`, claimed tasks, and approval state.
- **FR-007**: The system MUST exclude `.env` files, security tokens, private keys, session files, and equivalent secret-bearing artifacts from synchronization.
- **FR-008**: The cloud node MUST operate with credentials that are distinct from and lower privilege than the local node credentials.
- **FR-009**: The system MUST require claim-by-move into `/In_Progress/<agent>/` before either node may execute a task from `/Needs_Action/`.
- **FR-010**: The system MUST record task claims, claim conflicts, handoffs, releases, and completions in the shared audit trail.
- **FR-011**: The cloud-facing accounting workflow MUST support secure draft creation and monitoring against a cloud-hosted Odoo deployment over HTTPS.
- **FR-012**: The system MUST require local approval and local execution before any cloud-drafted accounting entry can produce a financial mutation.
- **FR-013**: `Dashboard.md` MUST show the current status of both Cloud and Local nodes, including heartbeat freshness, queue ownership, and synchronization latency.
- **FR-014**: The dashboard MUST surface stale heartbeats, sync failures, and other distributed-operating degradations as visible alerts.
- **FR-015**: The feature MUST preserve existing Bronze, Silver, Gold, and Platinum safety guarantees, including HITL gates for all high-risk actions.
- **FR-016**: Each Platinum capability MUST be deliverable as a modular Agent Skill aligned with the Platinum constitution.

### Key Entities *(include if feature involves data)*

- **Node Status**: A shared record describing each node's identity, role, heartbeat freshness, privilege level, and current availability.
- **Task Claim**: The ownership state created when a task is moved into `/In_Progress/<agent>/`, including owner, claim time, release status, and related audit entries.
- **Sync State**: The shared representation of last successful synchronization, current lag, excluded-file policy, and any unresolved content conflicts.
- **Approval Artifact**: A draft or approval-ready record that can be prepared by the cloud node but only finalized through local approval and local execution.
- **Accounting Draft**: A draft financial entry or reconciliation package prepared from Odoo monitoring for local approval.
- **Executive Dashboard State**: The consolidated view of cloud health, local health, queue ownership, approval backlog, and sync freshness shown in `Dashboard.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of new inbox and monitoring items are triaged, drafted, or surfaced for review within 5 minutes of appearing in the shared system.
- **SC-002**: 100% of WhatsApp, payment, final send/post, and `/Approved/` execution events are performed by the local node, with zero cloud-side execution events in the audit trail.
- **SC-003**: 100% of secret-bearing files identified by policy are excluded from cloud synchronization in validation tests.
- **SC-004**: In distributed claim tests, no task is executed by more than one node.
- **SC-005**: At least 95% of cloud-drafted accounting items reach a local approval-ready state within 10 minutes of the triggering business event.
- **SC-006**: The executive dashboard reflects node heartbeat freshness and last sync latency within 1 minute of a status change.
- **SC-007**: 100% of Markdown state conflicts are either resolved by declared policy or surfaced for explicit review without silent data loss.

## Assumptions

- The Platinum rollout builds on the existing vault-based operating model and keeps the vault as the single source of truth.
- Human approval remains mandatory for all high-risk actions even after cloud-local distribution is introduced.
- Cloud deployment provider choice is out of scope for the specification as long as the cloud node can run continuously within the constitutional safety boundaries.
- Existing Bronze, Silver, Gold, and Platinum constitutional rules remain authoritative where this feature does not explicitly expand behavior.
