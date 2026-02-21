# Feature Specification: Silver Tier Reasoning & Planning System

**Feature Branch**: `003-silver-reasoning`
**Created**: 2026-02-21
**Status**: Draft
**Tier**: Silver
**Input**: Upgrade Personal AI Employee with autonomous reasoning loops and structured Plan.md files

## Overview

The Silver Tier Reasoning & Planning System enables the AI Employee to autonomously reason about complex tasks by creating structured, auditable `Plan.md` files in the vault. This system implements the "Reconciliation-First" operational model where multi-step workflows are tracked, progress is persisted across sessions, and human approval gates all external actions.

---

## User Scenarios & Testing

### User Story 1 - Agent Receives Complex Request (Priority: P1)

The AI Employee receives a complex multi-step task (e.g., "Generate an invoice for Client A, send it via email, and log the transaction"). Instead of executing immediately, the agent must evaluate whether the task requires structured reasoning.

**Why this priority**: Multi-step task handling is the core Silver Tier capability. Without this, autonomous reasoning cannot function.

**Independent Test**: Agent can be tested by providing a multi-step request and verifying that a Plan.md is created in `/Plans/` with the correct schema before any external actions occur.

**Acceptance Scenarios**:

1. **Given** a request with multiple sequential steps, **When** the agent detects complexity keywords (#high, invoice, client, payment), **Then** the agent suggests creating a plan and initializes a `Plan.md` file in `/Plans/`
2. **Given** a simple single-step task (e.g., "read dashboard"), **When** the agent evaluates it, **Then** no plan is created and the task executes directly
3. **Given** a Plan.md file already exists for this task, **When** the agent receives a similar request, **Then** the agent resumes from the last checkpoint instead of creating a duplicate

---

### User Story 2 - Agent Tracks Progress Across Sessions (Priority: P1)

The AI Employee's reasoning persists across multiple sessions. When a session terminates and is later resumed, the agent must be able to determine what work was in progress and resume from the exact checkpoint.

**Why this priority**: Multi-session persistence is essential for the "Reconciliation-First" model. Without it, plans would be lost or restarted unnecessarily.

**Independent Test**: A plan is created with multiple steps, several steps are marked complete, the session ends, a new session begins, and the agent correctly identifies the plan and resumes from the incomplete steps.

**Acceptance Scenarios**:

1. **Given** an incomplete plan in `/Plans/`, **When** a new session starts, **Then** the agent scans `/Plans/`, identifies the most recent incomplete plan, and loads it as the "Current Mission"
2. **Given** a plan with checkboxes (`- [x] Step 1`, `- [ ] Step 2`), **When** the agent updates progress, **Then** the checkboxes are atomically updated and visible in the dashboard
3. **Given** multiple plans in `/Plans/`, **When** the agent starts, **Then** it prioritizes by Status (Active > Blocked > Draft) and then by Creation Date (most recent first)

---

### User Story 3 - Agent Drafts External Actions for Approval (Priority: P1)

When the agent needs to send an email, post to social media, or make a payment (any external action), it must create a draft approval request in `/Pending_Approval/` rather than executing directly.

**Why this priority**: Human-in-the-Loop safety is non-negotiable for Silver Tier. This prevents accidental or misaligned external actions.

**Independent Test**: Agent is instructed to send an email. An approval request file is created in `/Pending_Approval/` with full details, the email is NOT sent, and when the file is moved to `/Approved/`, the action executes.

**Acceptance Scenarios**:

1. **Given** an agent task that requires sending an email, **When** the agent detects the external action, **Then** it creates a file in `/Pending_Approval/` with the email draft, rationale, and a reference to the Plan.md step
2. **Given** an approval file in `/Pending_Approval/`, **When** the human moves it to `/Approved/`, **Then** the agent re-reads the file, confirms approval, and executes the external action via MCP
3. **Given** an approval file in `/Pending_Approval/`, **When** the human moves it to `/Rejected/`, **Then** the agent logs the rejection, updates the plan's Reasoning Logs, and waits for next steps

---

### User Story 4 - Dashboard Reflects Current Mission Status (Priority: P2)

The Dashboard.md file displays the current plan status, blocked items, and active steps so the human can see at a glance what the agent is working on.

**Why this priority**: Visibility into agent work-in-progress enables human oversight and intervention.

**Independent Test**: A plan is created with multiple steps and status updates occur. The dashboard is regenerated and displays the correct "Current Mission" and block status.

**Acceptance Scenarios**:

1. **Given** an active plan with Status: Active, **When** the dashboard is updated, **Then** the "Current Mission" section displays the plan's objective and current step
2. **Given** a plan where all steps have a ✋ (HITL) marker in `/Pending_Approval/`, **When** the dashboard is regenerated, **Then** the status is marked as "Blocked: Awaiting Human Approval"
3. **Given** a completed plan moved to `/Done/Plans/`, **When** the dashboard is updated, **Then** the plan is archived and a new active plan (if any) becomes the "Current Mission"

---

### User Story 5 - Agent Resolves Blocked Plans (Priority: P2)

When a plan is blocked (waiting for human approval or external feedback), the agent must detect the block, provide context about what is waiting, and resume when the block is resolved.

**Why this priority**: Unblocking workflows is critical for autonomous operation at scale.

**Independent Test**: A plan contains an approval request that is moved to `/Approved/`. The agent detects the unblock, resumes the plan, and continues to the next step.

**Acceptance Scenarios**:

1. **Given** a plan with Reasoning Logs indicating a block ("Awaiting human approval for email send"), **When** the human approves the action, **Then** the agent detects the block resolution and continues execution
2. **Given** a plan blocked for more than 24 hours, **When** the dashboard is regenerated, **Then** a warning is displayed ("Plan blocked for X hours")

---

### Edge Cases

- What happens if a Plan.md file is corrupted or has incomplete YAML frontmatter? → Agent MUST detect and log an error without crashing; human is alerted to review the file
- How does the system handle if two plans are created for the same task simultaneously? → The agent MUST detect and consolidate, moving duplicates to a /Archive folder with a note
- What if a ✋ (HITL) step is moved to `/Approved/` but the corresponding MCP server is offline? → Agent MUST detect MCP failure, update Reasoning Logs with error details, and move the approval file back to `/Pending_Approval/` with failure reason
- How are plan conflicts resolved if the human edits a plan while the agent is executing it? → Plan.md MUST be atomically read before each step; changes are immediately visible to the agent on the next step

---

## Requirements

### Functional Requirements

**Plan.md Creation & Schema:**

- **FR-001**: Agent MUST create a `Plan.md` file in `/Plans/` when detecting a complex task (multi-step, high-priority, or contains keywords: invoice, client, payment, async, schedule, report, audit)
- **FR-002**: Plan.md MUST follow this rigid schema:
  ```yaml
  ---
  task_id: [UUID or sequential ID, e.g., PLAN-2026-001]
  source_link: [mandatory - URL, file path, or email reference that triggered the plan]
  created_date: [ISO-8601 timestamp, e.g., 2026-02-21T10:30:00Z]
  priority: [high | medium | low]
  status: [Draft | Active | Blocked | Done]
  blocked_reason: [only if status is Blocked, e.g., "Awaiting human approval for email send"]
  ---
  ```
- **FR-003**: Plan.md MUST contain these sections in order:
  - `# Objective` — single-sentence mission statement describing the end-state
  - `## Context` — problem statement, dependencies, constraints (2-3 sentences)
  - `## Roadmap` — numbered list of steps with checkboxes and ✋ emoji for HITL steps
  - `## Reasoning Logs` — timestamped entries (ISO-8601) documenting why steps were added or altered

**Session Persistence & Reconciliation:**

- **FR-004**: At every session start, agent MUST scan `/Plans/` to find the most recent incomplete plan (status: Active or Blocked)
- **FR-005**: Agent MUST display to the human: "Resuming plan [task_id]: [Objective]" before executing any other work
- **FR-006**: Agent MUST load the incomplete plan's last Reasoning Log entry to determine the checkpoint and resume from there

**External Action Drafting & Approval Routing:**

- **FR-007**: Agent MUST NOT execute any external action (email, social post, API call, payment, etc.) directly
- **FR-008**: Agent MUST create an approval request file in `/Pending_Approval/` with filename format: `<ISO-timestamp>_<action-type>_<brief-slug>.md`
- **FR-009**: Approval request file MUST contain:
  - Metadata section with `action_type`, `target_recipient`, `approval_required_by` (human), `rationale` (referencing the Plan.md step)
  - Full draft content (email body, social post text, API payload, etc.)
  - Clear instructions: "Move this file to `/Approved/` to execute" or "Move to `/Rejected/` to deny"
- **FR-010**: Agent MUST NOT proceed with the external action until the file is moved to `/Approved/`
- **FR-011**: Before invoking the MCP action, agent MUST re-read the file in `/Approved/` to confirm approval status

**Dashboard & Status Visibility:**

- **FR-012**: Agent MUST update `Dashboard.md` after every significant file operation (create plan, move step, complete plan, etc.)
- **FR-013**: Dashboard MUST include a "Current Mission" section displaying:
  - Task ID and Objective of the active plan
  - Current step number and description
  - Status (Active | Blocked: [reason] | Completed [X] of [Y] steps)
  - Pending approvals count (e.g., "2 approvals awaiting in /Pending_Approval/")
- **FR-014**: Dashboard MUST include a "Recent Activity" section with timestamped entries (last 10 significant events)

**Blocked Plan Detection & Alerts:**

- **FR-015**: Agent MUST scan `/Pending_Approval/` and identify which plans are waiting for approval
- **FR-016**: If a plan contains one or more ✋ (HITL) steps with corresponding files in `/Pending_Approval/`, agent MUST mark the plan status as "Blocked: Awaiting Human" and log the reason in Reasoning Logs
- **FR-017**: If a plan is blocked for more than [NEEDS CLARIFICATION: time threshold for block warning - suggest: 24, 12, or 4 hours?], agent MUST log a warning in Reasoning Logs and display an alert in the Dashboard

**Checkpoint Atomicity:**

- **FR-018**: Plan.md updates MUST be atomic — never leave the file in an incomplete state (incomplete YAML, missing sections, etc.)
- **FR-019**: If an agent session terminates unexpectedly, the next session MUST be able to resume from the last complete checkpoint without data loss

**Reasoning Logs & Decision Trails:**

- **FR-020**: Agent MUST append timestamped entries to the `## Reasoning Logs` section whenever:
  - A step is marked complete
  - An external action is drafted for approval
  - A block is detected or resolved
  - A decision was made to skip a step or take an alternative path
- **FR-021**: Each Reasoning Log entry MUST include: timestamp (ISO-8601), actor (agent), action, and brief rationale

### Key Entities

- **Plan**: A multi-step workflow stored as a markdown file in `/Plans/`. Contains task metadata, objective, roadmap, and reasoning history. Survives across sessions.
- **Step**: An individual action within a Plan's Roadmap. Can be autonomous (no ✋) or gated by human approval (has ✋).
- **Approval Request**: A draft external action file stored in `/Pending_Approval/`, waiting for human review and movement to `/Approved/` or `/Rejected/`.
- **Reasoning Log Entry**: A timestamped record of why a step was added, modified, or skipped. Enables transparency and debugging.
- **Current Mission**: The most recent incomplete plan, determined by Reconciliation-First logic at session start.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Agent successfully creates a Plan.md with valid schema in under 3 seconds for any task trigger
- **SC-002**: Agent accurately resumes from the last checkpoint 100% of the time when a session resumes (verified by checkpoint log matching)
- **SC-003**: All external actions are drafted to `/Pending_Approval/` with 100% compliance — zero cases of direct external execution without approval
- **SC-004**: Dashboard reflects current plan status within 5 seconds of an update (Plan.md change, approval move, step completion)
- **SC-005**: Blocked plans are correctly identified and marked with status "Blocked: Awaiting Human" 100% of the time
- **SC-006**: Human can track full reasoning history for any plan decision via Reasoning Logs (all decisions logged with timestamps and rationale)
- **SC-007**: System handles multi-session workflows without data loss or duplicate plan creation, verified by audit logs

### Qualitative Outcomes

- **SC-008**: Reasoning is transparent — any human can understand why the agent took a step or is waiting for approval by reading the Plan.md and Reasoning Logs
- **SC-009**: Agent autonomy is bounded — all external actions are gated by human approval, preventing unintended external communications
- **SC-010**: Plan tracking enables human oversight without requiring constant monitoring — dashboard provides status at a glance

---

## Assumptions

1. **File System Atomicity**: The Obsidian vault uses a filesystem that supports atomic writes (standard on macOS, Linux, Windows). Partial writes will not corrupt Plan.md files.
2. **Human Responsiveness**: Humans review and move approval files within a reasonable time window (assumed: hours, not days). The system does not force or timeout approvals.
3. **Plan Complexity**: Plans are assumed to have 3-20 steps. Plans with >20 steps may benefit from sub-planning (not in scope for Silver Tier).
4. **UTF-8 Encoding**: All vault files are UTF-8 encoded. File encoding issues are not in scope.
5. **Single Agent**: Only one Claude Code session operates on the vault at a time. Concurrent multi-agent writes are not in scope for Silver Tier.
6. **Obsidian Vault Availability**: The vault folder is always accessible and writable. Network/permission issues are handled by the operating system.

---

## Dependencies & Constraints

**Dependencies:**
- Silver Law Constitution v2.0 (principles VI-IX: Reasoning Integrity, Authorized Autonomy, Multi-Sensory Integration, Brand & Privacy Stewardship)
- Obsidian Vault structure (existing Bronze Tier `/Inbox`, `/Needs_Action`, `/Done`, `/Logs` folders)
- MCP Server gating for all external actions (existing or to be built during implementation)
- `managing-obsidian-vault` skill (to be extended with Reasoning section)

**Constraints:**
- No external planning tools (e.g., Jira, Asana) — all reasoning must stay in the vault
- No autonomous execution of external actions — all HITL steps must be explicitly approved
- Plan.md files MUST adhere to the rigid schema — flexible schemas would lose auditability
- Session persistence is file-based only — no database or cloud state

---

## Out of Scope (Gold+ Tier)

- Automated financial reconciliation with Odoo or external accounting systems
- Real-time event automation or auto-responses
- Direct database mutations without plan tracking
- Multi-agent parallel reasoning (only single-agent at Silver Tier)
- Plan templates or macros (all plans manually crafted per task)

---

## Testing & Validation Strategy

### Unit-Level Tests

- Plan.md creation: Valid schema generated for various task triggers
- Session resumption: Correct plan loaded from `/Plans/` on session start
- Approval routing: Draft files created in `/Pending_Approval/` and MCP actions execute only when moved to `/Approved/`
- Dashboard updates: Current Mission reflects active plan status correctly

### Integration-Level Tests

- End-to-end workflow: Multi-step task → Plan creation → Step execution → Approval request → Human approval → MCP action → Plan completion
- Multi-session persistence: Create plan → End session → Resume session → Verify checkpoint → Continue execution
- Block detection: Create approval file → Mark plan as Blocked → Human approves → Plan resumes

### Edge Case Tests

- Corrupted Plan.md file → Agent error handling and human alerting
- Duplicate plan creation → Consolidation and archival logic
- MCP server offline during approval execution → Fallback to manual retry

---

## Acceptance Criteria

A feature is considered complete when:

1. ✅ All Functional Requirements (FR-001 through FR-021) are implemented and passing unit tests
2. ✅ All User Scenarios (Stories 1-5) are testable and demonstrable
3. ✅ All Success Criteria (SC-001 through SC-010) are measurable and verified
4. ✅ Plan.md schema is rigidly enforced (no partial or malformed files written)
5. ✅ Dashboard reflects Current Mission and block status in real-time
6. ✅ Zero cases of external actions executed without approval
7. ✅ Multi-session persistence verified with audit logs
8. ✅ No [NEEDS CLARIFICATION] markers remain in spec
9. ✅ Documentation and demo video show Plan creation, session resumption, and approval gating

---

## Clarifications Needed

- **FR-017 Block Warning Threshold**: After how many hours should a blocked plan trigger a warning? (Suggest: 24 hours for non-critical, 4 hours for high-priority plans)

---

## Related Features & History

- **Bronze Tier**: Vault initialization, inbox triage, dashboard updates (`001-vault-manager`)
- **Bronze Tier Implementation**: File system watcher for vault ingestion (`002-sentinel-watcher`)
- **Silver Tier**: This feature — Reasoning & Planning (`003-silver-reasoning`)
- **Future Gold Tier**: Autonomous financial reconciliation, multi-agent coordination, real-time automation

