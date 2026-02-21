# Managing Obsidian Vault Skill

**Tier**: Silver (extends Bronze Tier)
**Status**: Under Development
**Last Updated**: 2026-02-21

---

## Overview

This skill enables autonomous management of the Obsidian Vault used by the Digital FTE (Personal AI Employee). The vault serves as the single source of truth for:

- **Inbox triage**: Processing new requests/information from watchers
- **Task tracking**: Recording work status in `/Needs_Action/` and `/Done/`
- **Approval routing**: Drafting external actions in `/Pending_Approval/` for human review
- **Audit logging**: Maintaining complete history of all agent decisions

**Bronze Tier** (existing): Inbox triage, task completion, dashboard updates
**Silver Tier** (extending): Plan-based reasoning, session persistence, complex workflow management

---

## Table of Contents

1. [Bronze Tier Procedures (Existing)](#bronze-tier-procedures-existing)
2. [Silver Tier Procedures (New)](#silver-tier-procedures-new)
3. [Data Models](#data-models)
4. [Error Handling](#error-handling)
5. [Audit Trail](#audit-trail)

---

## Bronze Tier Procedures (Existing)

> *Placeholder for existing Bronze Tier procedures from previous implementation*

### Sections 1-7

See existing SKILL documentation or `.specify/memory/constitution.md` for:
- Section 1: Vault structure
- Section 2: Inbox processing
- Section 3: Task triage
- Section 4: Dashboard updates
- Section 5: Task completion
- Section 6: Approval routing (Bronze)
- Section 7: Audit logging

---

## Silver Tier Procedures (New)

### Section 8: Reasoning & Planning (Silver Tier)

**Purpose**: Enable autonomous reasoning loops using Plan.md files stored in `/Plans/`. Allows agent to break down complex requests into multi-step workflows, persist work across sessions, and gate external actions.

---

### Procedure 8.1: InitializePlan

**Trigger**: Agent detects complex task and receives user approval

**Inputs**:
- `objective` (string): Single-sentence mission statement
- `context` (string): Problem, dependencies, constraints
- `steps` (list): Ordered list of action items (can include `✋` prefix for HITL steps)
- `priority` (string): high | medium | low
- `source_link` (string, optional): Reference to source document (e.g., `/Inbox/task.md`)

**Process**:
1. Validate inputs (objective and at least 1 step required)
2. Call `PlanManager.create_plan()` with inputs
3. Log in Reasoning Logs: "Created plan — [objective]"
4. Display confirmation: Plan ID, location, step count
5. Set initial status to "Draft"
6. Return plan_id to caller

**Outputs**:
- Plan.md file created in `/Plans/` with rigid schema
- YAML frontmatter: task_id, source_link, created_date, priority, status=Draft, blocked_reason=null
- Markdown sections: Objective, Context, Roadmap (with checkboxes), Reasoning Logs

**Error Handling**:
- If objective empty → Log error, ask user to clarify
- If no steps provided → Log error, suggest minimum 1 step
- If file creation fails → Log IO error, suggest vault permissions issue

**Example**:

```markdown
InitializePlan({
  objective: "Generate and send invoice to Client A for $1,500",
  context: "Client requested via WhatsApp. Rate card: $1,500. No blocking dependencies.",
  steps: [
    "Identify client contact: Client A (client_a@example.com)",
    "Calculate amount: $1,500 (from /Accounting/Rates.md)",
    "Generate invoice PDF",
    "✋ Send email with invoice attachment (requires approval)",
    "Log transaction in /Accounting/Current_Month.md"
  ],
  priority: "high",
  source_link: "/Inbox/whatsapp_client_a.md"
})

→ Returns: PLAN-2026-001
→ Creates: /Plans/PLAN-2026-001.md
```

---

### Procedure 8.2: UpdatePlanStep

**Trigger**: Agent completes a step in active plan

**Inputs**:
- `plan_id` (string): Plan identifier
- `step_number` (integer): Step number (1-indexed)
- `completed` (boolean): true to mark complete, false to mark incomplete
- `log_entry` (string, optional): Reasoning log message (without timestamp)

**Process**:
1. Load plan from `/Plans/` using PlanManager
2. Update step checkbox: `[ ]` → `[x]` (or vice versa)
3. If log_entry provided, append to Reasoning Logs with ISO-8601 timestamp
4. Update step status in plan metadata if needed
5. Write updated plan back to file (atomic operation)

**Outputs**:
- Updated Plan.md file with step marked complete/incomplete
- New reasoning log entry appended

**Error Handling**:
- If plan not found → Log error, return failure
- If step_number out of range → Log error, suggest valid range
- If write fails → Log IO error, suggest vault permissions

**Example**:

```markdown
UpdatePlanStep({
  plan_id: "PLAN-2026-001",
  step_number: 3,
  completed: true,
  log_entry: "Generated invoice PDF — Identified rate: $1,500. Output: /Invoices/2026-01_Client_A.pdf"
})

→ Roadmap updated: "- [x] Generate invoice PDF"
→ Reasoning Logs appended with timestamp
```

---

### Procedure 8.3: LogReasoning

**Trigger**: Agent makes a significant decision requiring audit trail

**Inputs**:
- `plan_id` (string): Plan identifier
- `action` (string): What was done (past tense, concise)
- `rationale` (string): Why it was done

**Process**:
1. Load plan from `/Plans/`
2. Format reasoning log entry: `[ISO-TIMESTAMP] Agent: [action] — [rationale]`
3. Append to Reasoning Logs section
4. Write plan file atomically

**Outputs**:
- New reasoning log entry added to plan

**Format**:
```
- [2026-02-21T10:45:00Z] Agent: Drafted email for approval — Invoice PDF ready; awaiting human approval before sending via MCP email server.
```

---

### Procedure 8.4: ArchivePlan

**Trigger**: Plan completed (all steps done or plan obsolete)

**Inputs**:
- `plan_id` (string): Plan identifier
- `status` (string): Final status (typically "Done" or "Abandoned")

**Process**:
1. Load plan from `/Plans/`
2. Update status in metadata to provided status
3. Move file from `/Plans/PLAN-*.md` to `/Done/Plans/PLAN-*.md`
4. Log: "Plan archived — [plan_id], final status: [status]"

**Outputs**:
- Plan file moved to `/Done/Plans/`
- Source file in `/Plans/` deleted
- Status updated to "Done"

**Error Handling**:
- If plan not found → Log error
- If move fails → Log IO error

---

### Procedure 8.5: DraftExternalAction

**Trigger**: Step requires external action (email, payment, social post, etc.)

**Inputs**:
- `action_type` (string): email | payment | social_post | api_call | other
- `target_recipient` (string): Email, account, API endpoint, etc.
- `plan_id` (string): Reference to containing plan
- `step_id` (integer): Step number triggering this action
- `draft_content` (string): Full content (email body, payment details, post text, etc.)
- `rationale` (string): Why this action is needed (from plan context)

**Process**:
1. Create file in `/Pending_Approval/` with filename: `[ISO-TIMESTAMP]_[action_type]_[slug].md`
2. Write YAML frontmatter with metadata
3. Write draft content below frontmatter
4. Add instructions for human: "Move to /Approved/ to execute" or "Move to /Rejected/ to deny"
5. Return approval file path

**Outputs**:
- Approval request file created in `/Pending_Approval/`
- Contains YAML metadata for agent to re-read after approval

**Example File**: `/Pending_Approval/2026-02-21T10-45-00Z_email_invoice-send.md`

```yaml
---
action_type: email
target_recipient: client_a@example.com
approval_required_by: human
rationale: "Plan PLAN-2026-001, Step 4: Send invoice to Client A for $1,500"
created_date: 2026-02-21T10:45:00Z
status: pending
plan_id: PLAN-2026-001
step_id: 4
---

# Email Approval Request

## To: client_a@example.com

Dear Client A,

Please find attached your invoice for January 2026 services...

[Full email body]
```

---

### Procedure 8.6: DetectBlocks

**Trigger**: Periodic check or after plan update

**Inputs**:
- `plan_id` (string): Plan identifier

**Process**:
1. Load plan
2. Check for steps marked `✋` (HITL required)
3. For each HITL step, check if approval file exists in `/Pending_Approval/`
4. If HITL steps pending → Update plan status to "Blocked: Awaiting Human Approval"
5. If created_date of block > 24 hours → Flag for dashboard alert
6. Return block status

**Outputs**:
- Plan status updated if blocked
- Alert flag returned if block stale

---

### Procedure 8.7: ResumePlan

**Trigger**: Approval detected (file moved to `/Approved/`)

**Inputs**:
- `approval_file_path` (string): Path to file in `/Approved/`

**Process**:
1. Read approval file to extract plan_id, step_id, action_type
2. Re-read approval YAML to confirm approval status
3. Call appropriate external action (email, payment, etc.) via MCP
4. On success: Move approval file to `/Done/` and log execution
5. On failure: Move approval file back to `/Pending_Approval/` with error reason
6. Update plan status to "Active" if was "Blocked"

**Outputs**:
- External action executed
- Approval file moved to appropriate destination
- Plan status updated

---

### Procedure 8.8: ReconcileDashboard

**Trigger**: After plan creation, step completion, or block detection

**Inputs**:
- None (scans vault state)

**Process**:
1. Scan `/Plans/` for all incomplete plans
2. For each plan:
   - Extract plan_id, objective, status, progress (completed/total steps)
   - Calculate next step
   - Detect blocks (HITL steps with pending approvals)
3. Sort by status (Active > Blocked > Draft) and date
4. Update Dashboard.md with "⚡ Current Missions" section
5. Calculate stats: Active Plans, Blocked Plans, Completion %, Oldest Block

**Outputs**:
- Dashboard.md updated with live plan status
- Alert section populated if blocks > 24 hours old

---

## Data Models

### Plan.md Schema

```yaml
---
task_id: PLAN-2026-001
source_link: /Inbox/whatsapp_client_a.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Active
blocked_reason: null
---

# Objective
[Single-sentence mission statement]

## Context
[Problem, dependencies, constraints]

## Roadmap
- [ ] Step 1
- [x] Step 2
- [ ] ✋ Step 3 (requires approval)

## Reasoning Logs
- [2026-02-21T10:30:00Z] Agent: [action] — [rationale]
- [2026-02-21T10:35:00Z] Agent: [action] — [rationale]
```

### Plan Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| Draft | Created but not started | User can edit, no auto-execution |
| Active | In progress | Agent resumes from next incomplete step |
| Blocked | Awaiting external event (human approval, etc.) | Agent waiting for unblock condition |
| Done | Complete | Archived to `/Done/Plans/` |

---

## Error Handling

| Error | Recovery |
|-------|----------|
| Plan file corrupted | Log error, skip, proceed without plan |
| Vault not accessible | Log error, halt agent, alert user |
| Step number invalid | Log error, request valid range |
| External action execution failed | Log error, move approval back to `/Pending_Approval/` with reason |
| Duplicate plan_id | Consolidate steps or alert user |

---

## Audit Trail

All procedures MUST log their actions:

```
- [2026-02-21T10:30:00Z] Agent: Created plan — PLAN-2026-001. Objective: Generate and send invoice. Status: Draft.
- [2026-02-21T10:35:00Z] Agent: Marked step 1 complete — Identified client rate: $1,500.
- [2026-02-21T10:45:00Z] Agent: Detected block — Step 4 (HITL) requires approval. Plan status: Blocked.
- [2026-02-21T11:00:00Z] Agent: Detected approval — Approval moved to /Approved/. Executing email.
- [2026-02-21T11:05:00Z] Agent: Executed external action — Email sent to client_a@example.com.
- [2026-02-21T11:10:00Z] Agent: Plan completed — All steps done. Status: Done. Archived to /Done/Plans/.
```

---

## Next Steps

Phase 2 tasks (T010-T020) implement these procedures:
- T010-T013: Core PlanManager functions (create, load, find, validate)
- T014-T015: Session startup logic
- T016-T017: Complexity detection
- T018-T020: Step tracking and skill framework
