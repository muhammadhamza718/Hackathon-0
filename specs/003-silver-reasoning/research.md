# Research Phase: Silver Tier Reasoning System Design Decisions

**Date**: 2026-02-21 | **Feature**: 003-silver-reasoning

This document consolidates design research and decisions for key technical aspects of the Silver Tier Reasoning System.

---

## 1. Plan.md Schema Design

**Topic**: How should Plan.md files be structured in markdown to balance auditability, readability, and parser robustness?

### Decision

**Rigid Schema** with YAML frontmatter + Markdown sections:

```yaml
---
task_id: PLAN-2026-001
source_link: /Inbox/EMAIL_client-a-invoice.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Active
blocked_reason: null
---

# Objective
Generate and send January invoice to Client A for $1,500.

## Context
Client A requested invoice via WhatsApp. Amount is $1,500 (from rate card).
Dependency: Rate card in /Accounting/Rates.md exists. No external factors blocking.

## Roadmap
- [x] Identify client: Client A (client_a@example.com)
- [x] Calculate amount: $1,500 (from /Accounting/Rates.md)
- [ ] Generate invoice PDF
- [ ] ✋ Send email (requires human approval)
- [ ] Log transaction in /Accounting/Current_Month.md

## Reasoning Logs
- 2026-02-21T10:30:00Z Agent: Created plan from WhatsApp message. Objective: Generate and send invoice.
- 2026-02-21T10:35:00Z Agent: Identified rate: $1,500. Completed steps 1-2.
- 2026-02-21T10:40:00Z Agent: Generated invoice PDF in /Invoices/2026-01_Client_A.pdf. Marked step 3 complete.
```

### Rationale

- **YAML frontmatter** enables metadata queries (priority, status, creation date) without parsing markdown sections
- **Markdown sections** are human-readable and editable in Obsidian
- **Checkboxes** provide visual progress indicators and integrate with Obsidian's checkbox toggle feature
- **✋ emoji** signals HITL steps at a glance (no parsing needed)
- **Reasoning Logs** create an immutable audit trail (append-only, timestamped)
- **Rigid structure** ensures parsers never encounter malformed files

### Alternatives Considered

1. **Fully YAML**: Would be machine-friendly but unreadable in Obsidian. Rejected because humans need to review and edit plans.
2. **Flexible markdown**: Sections optional, varied naming. Would break parser robustness and auditability. Rejected per Silver Law Principle VI (Reasoning Integrity).
3. **Database (Odoo/Notion)**: Violates Local-First Privacy (Principle I). Rejected.

---

## 2. Session Resumption Logic (Reconciliation-First)

**Topic**: How should the agent determine what work to resume at session startup?

### Decision

**Reconciliation-First Algorithm**:

```
At session start:
1. Scan /Plans/ for all *.md files
2. Parse YAML frontmatter to extract status, created_date
3. Filter for incomplete plans (status ∉ [Done])
4. Prioritize by:
   a. Status: Active > Blocked > Draft
   b. If tied: created_date descending (most recent first)
5. Load the highest-priority plan
6. Read last Reasoning Log entry to determine checkpoint
7. Load plan as "Current Mission"
8. Display to user: "Resuming plan [ID]: [Objective]"
9. Begin execution at next uncompleted step
```

### Rationale

- **Reconciliation-First** ensures no hidden state outside the vault. The session always asks "what work is waiting?" from the vault, not from internal memory.
- **Status prioritization** ensures the most urgent work (Active, then Blocked) resumes first
- **Recent-first ordering** gives precedence to recently-started work (likely more relevant context still in agent memory)
- **Checkpoint from logs** avoids re-executing completed steps or making assumptions
- **User-facing message** provides transparency and confirms correct plan loaded

### Alternatives Considered

1. **Timestamp-based only**: Simple but doesn't respect urgency (Active plans should resume before Draft plans). Rejected.
2. **Human-explicit selection**: Could work but requires user input at every session, reducing autonomy. Rejected for Silver Tier.
3. **Resume last session's context**: Would require internal state storage outside vault, violating Local-First Privacy. Rejected.

---

## 3. Approval Routing & HITL Workflow

**Topic**: How should approval requests be created, tracked, and executed to ensure human oversight while enabling autonomy?

### Decision

**File-Based Approval Workflow**:

```
When agent detects external action (email, payment, social post, MCP call):

1. Draft Action
   - Create file: /Pending_Approval/<ISO-timestamp>_<action-type>_<slug>.md
   - Include: action_type, target_recipient, rationale (referencing Plan.md step ID)
   - Include: full draft content (email body, payment details, post text, API payload)
   - Include: instructions for human ("Move to /Approved/ to execute or /Rejected/ to deny")

2. Halt Execution
   - Agent does NOT call MCP or take external action
   - Agent logs: "Created approval request, awaiting human decision"
   - Agent waits (may move to next plan if other steps are independent)

3. Human Review
   - User sees file in /Pending_Approval/ folder in Obsidian
   - User reviews content, rationale, and attached context
   - User moves file to /Approved/ (to proceed) or /Rejected/ (to cancel)

4. Detect Approval Status
   - Agent periodically checks: Has file moved from /Pending_Approval/?
   - If moved to /Approved/: Re-read file to confirm, then execute
   - If moved to /Rejected/: Log rejection, update plan's Reasoning Logs, wait for next steps
   - If still in /Pending_Approval/: Remain blocked

5. Execute Approved Action
   - Parse action_type from filename and frontmatter
   - Call appropriate MCP server (email-mcp, social-mcp, etc.)
   - On success: Move file to /Done/Actions/, update Reasoning Logs, resume plan
   - On MCP failure: Log error, move file back to /Pending_Approval/ with failure reason, alert human

6. Block Detection
   - If approval file remains in /Pending_Approval/ for > 24 hours, Dashboard alerts human
```

### Rationale

- **File-based**: Completely vault-native, observable by human in Obsidian, no external state
- **Timestamp + action-type + slug**: Enables automatic routing and prevents collisions
- **Rationale field**: Human can understand why agent is asking for approval (traceability)
- **Draft content included**: Human can review before approval (safety gate)
- **Explicit move to /Approved/**: Unmistakable approval signal (no ambiguity)
- **Move-back-on-failure**: If MCP server goes down, approval remains available for retry
- **24-hour alert**: Prevents forgotten approvals that would indefinitely block workflow

### Alternatives Considered

1. **Automatic approval for "safe" actions**: Would violate HITL principle (Principle VII). Rejected.
2. **Database-backed approvals**: Violates Local-First Privacy. Rejected.
3. **Email-based approvals**: Adds external dependency, complicates UX. Rejected.
4. **Timeout-based auto-reject**: Could cause data loss if approval accidentally expires. Rejected.

---

## 4. Block Detection & Plan Status

**Topic**: How should the agent determine whether a plan is "blocked" and what causes blocks?

### Decision

**Block Detection Algorithm**:

```
When updating plan status or detecting block:

1. Scan /Pending_Approval/ for files related to current plan
   - Match by: task_id in file content, or plan step reference

2. For each approval file found:
   - If file has ✋ emoji step in plan's Roadmap: This is a required approval
   - If approval file in /Pending_Approval/: Plan MUST be blocked

3. If any required approvals are pending:
   - Set plan status: "Blocked: Awaiting Human Approval"
   - Set blocked_reason: "Approval request: [filename] waiting since [time]"
   - Add Reasoning Log entry: "Plan blocked at step N, awaiting [specific approval]"

4. If plan blocked > 24 hours:
   - Add Dashboard alert: "⚠️ Plan PLAN-001 blocked for X hours (step: [step desc])"
   - Include context: "Last approval request: [details]"

5. When approval file moves to /Approved/:
   - Detect move (either agent checks or human signals)
   - Update plan status: "Active" (if other steps remain)
   - Remove blocked_reason
   - Add Reasoning Log: "Approval received for [step]. Resuming execution."
   - Continue to next step
```

### Rationale

- **File presence = block**: If approval file exists in `/Pending_Approval/`, it's definitionally blocking
- **24-hour threshold**: Provides enough time for human response, but alerts before a full day passes
- **Explicit unblock**: When approval moves to `/Approved/`, agent explicitly transitions plan back to Active
- **Reasoning Logs**: Audit trail shows exactly when blocks occur and resolve

### Alternatives Considered

1. **Automatic timeout rejections**: Could lose important work. Rejected.
2. **Nested dependencies (plan A blocks on plan B)**: Out of scope for Silver Tier. Rejected for simplicity.
3. **Block cascade (one block stops all steps)**: Plans are linear in Silver Tier; only current step can be blocked. Rejected.

---

## 5. Dashboard Reconciliation & Real-Time Updates

**Topic**: How should Dashboard.md be structured to reflect live plan state, and when/how frequently should it update?

### Decision

**Dashboard Structure & Update Strategy**:

```markdown
# Dashboard

## ⚡ Current Missions

**Active Plan**: PLAN-2026-001
- **Objective**: Generate and send January invoice to Client A
- **Status**: Blocked: Awaiting Human Approval
- **Current Step**: 4 of 5 (Send email)
- **Blocked Since**: 2026-02-21 10:45 (19 minutes ago)
- **Waiting For**: Approval: /Pending_Approval/2026-02-21T10:40:00Z_email_client-a.md
- **Next Step** (pending approval): Send email to client_a@example.com

---

## 📊 Plan Statistics

- **Active Plans**: 1 (PLAN-2026-001)
- **Blocked Plans**: 1 (awaiting approval)
- **Steps Completed**: 3 of 5
- **Pending Approvals**: 1

---

## 🚨 Alerts

- ⚠️ Plan PLAN-2026-001 blocked for 19 minutes (step: Send email)

---

## 🕐 Recent Activity

- 2026-02-21 10:40 Plan PLAN-2026-001: Approval requested for step 4 (email)
- 2026-02-21 10:35 Plan PLAN-2026-001: Step 3 completed (Generate invoice PDF)
- 2026-02-21 10:30 Plan PLAN-2026-001: Created (Objective: Generate and send invoice)

---
```

**Update Trigger**: After every significant file operation:
- Plan created
- Step completed (checkbox marked)
- Approval file moved
- Plan status changed
- Plan archived

**Update Latency**: Within 5 seconds of trigger

**Update Process**:
1. Scan `/Plans/` for all plans: extract ID, objective, status, step counts
2. Scan `/Pending_Approval/` for approval files: count and link to plans
3. Identify Active plan (most recent with status Active or Blocked)
4. Rebuild "Current Missions" section from live data
5. Update stats and alerts
6. Update recent activity log
7. Write Dashboard.md atomically

### Rationale

- **Live data sourcing**: Dashboard is never stale; always reflects current vault state
- **Centralized visibility**: User sees full context in one place (Obsidian)
- **5-second latency**: Fast enough to feel real-time without constant updates
- **Atomic writes**: Prevents partial/corrupted dashboard
- **Linked context**: Human can click from dashboard to approval files or plan files for details

### Alternatives Considered

1. **Agent-internal state**: Would require syncing with vault, risk divergence. Rejected.
2. **Scheduled updates (e.g., every 1 minute)**: Would miss real-time visibility. Rejected.
3. **Database dashboard (separate from vault)**: Violates Local-First Privacy. Rejected.
4. **Human-manual updates**: Defeats purpose of autonomy. Rejected.

---

## 6. Skill Extension: Managing-Obsidian-Vault

**Topic**: How should the existing Reasoning procedures be added to the managing-obsidian-vault skill while maintaining backward compatibility?

### Decision

**Additive Extension to SKILL.md**:

Current skill sections (Bronze Tier):
- Section 1: Vault Initialization
- Section 2: Triage & Prioritization
- Section 3: Dashboard Updates
- Section 4: Audit Logging
- Section 5-7: [Other Bronze procedures]

**New Section 8 - Reasoning (Silver Tier)**:
- Procedure: `InitializePlan` — Create new Plan.md with schema
- Procedure: `UpdatePlanStep` — Mark step complete, update checkpoint
- Procedure: `LogReasoning` — Append entry to Reasoning Logs
- Procedure: `ArchivePlan` — Move completed plan to /Done/Plans/
- Procedure: `DraftExternalAction` — Create approval request in /Pending_Approval/
- Procedure: `DetectBlocks` — Identify and mark blocked plans
- Procedure: `ResumePlan` — Scan /Plans/, load active plan at startup

Each procedure:
- Has clear inputs/outputs
- Is independently testable
- Integrates with existing sections (e.g., LogReasoning calls Section 4 audit logging)
- Follows skill naming and documentation conventions

### Rationale

- **Backward compatible**: Existing Bronze procedures unchanged; new section is additive
- **Modular procedures**: Each can be tested and improved independently
- **Integrated ecosystem**: New procedures call existing ones (e.g., for logging, dashboard updates)
- **Scalable**: Future tiers (Gold, Platinum) can add their own sections

### Alternatives Considered

1. **Separate Reasoning Skill**: Would fragment the vault-management responsibilities. Rejected.
2. **Inline within Bronze procedures**: Would bloat existing procedures. Rejected.
3. **External reasoning system (Python module)**: Violates vault-centric design. Rejected.

---

## 7. State Transitions & Error Handling

**Topic**: What are the valid state transitions for plans, and how should the agent handle errors?

### Decision

**State Transition Diagram**:

```
Draft → Active → Blocked → Active → Done
  ↓                          ↓
  └─────────────→ Cancelled (optional)
```

**Valid Transitions**:
- `Draft → Active`: Human or agent explicitly starts plan
- `Active → Blocked`: One or more ✋ steps waiting for approval
- `Blocked → Active`: Approval received, resume execution
- `Active → Done`: All steps completed, plan archived
- `Any → Cancelled`: Human manually cancels (opt-in, not automatic)

**Error Handling**:

1. **Corrupted Plan.md (invalid YAML)**
   - Detect on load: validation fails
   - Action: Log error in Dashboard, display alert to human
   - Agent does NOT crash; does NOT auto-fix
   - Human reviews and manually fixes or deletes file

2. **MCP Server Offline During Execution**
   - Detect: MCP call returns error
   - Action: Log error in Reasoning Logs, move approval file back to /Pending_Approval/ with error reason
   - Plan status remains "Active" (waiting for human to retry approval)
   - Dashboard alerts human

3. **Duplicate Plan Creation**
   - Detect: Two plans with same task_id or source_link
   - Action: Merge or consolidate, move duplicate to /Archive/, log in Reasoning Logs
   - Agent asks human for guidance if merge is ambiguous

4. **Step Dependency Not Met** (advanced, optional for Silver Tier)
   - Detect: Step N marked [x] but Step M (required by N) not done
   - Action: Log warning, don't proceed with N
   - Human fixes manually or reorders steps

### Rationale

- **Linear state machine**: Simple, predictable, auditable
- **No silent failures**: Errors are logged and visible to human
- **No auto-recovery**: Keeps human in control of critical decisions
- **Audit trail**: All errors and decisions recorded in Reasoning Logs

---

## 8. Complexity Detection: Keywords & Heuristics

**Topic**: How should the agent decide whether a task is "complex" and warrants a Plan.md?

### Decision

**Keyword-Based Detection**:

A task is "complex" and warrants a Plan.md if it contains ANY of:
- **High-priority keywords**: `#high`, `urgent`, `ASAP`, `critical`
- **Multi-step keywords**: `invoice`, `payment`, `client`, `project`, `campaign`, `report`, `audit`, `schedule`, `coordinate`
- **External-action keywords**: `send`, `post`, `publish`, `email`, `message`, `call`, `pay`, `submit`
- **Dependency keywords**: `after`, `once`, `then`, `require`, `depend`, `pipeline`, `sequence`
- **Multi-stakeholder keywords**: `client`, `team`, `manager`, `approval`, `sign-off`

**Simple tasks** (no Plan.md):
- `read`, `show`, `display`, `summarize`, `what is`, `how many`
- Single step, no external actions
- No priority markers

**Example**:
- ✅ "Generate and send invoice to Client A" → COMPLEX (invoice, send, client, external action)
- ❌ "Show me the dashboard" → SIMPLE (read, single step)
- ✅ "Schedule meeting with 3 team members" → COMPLEX (schedule, team, multi-step coordination)

### Rationale

- **Conservative detection**: Better to create plan for non-complex task than miss complex task
- **User-facing suggestion**: Agent says "I should create a plan for this" — user can override
- **Evolving list**: Keywords can be refined based on usage patterns

---

## 9. Reasoning Log Entry Format & Retention

**Topic**: How should Reasoning Log entries be formatted, and when should old entries be archived?

### Decision

**Entry Format**:

```
- [2026-02-21T10:35:00Z] Agent: [Action] — [Rationale]. [Details if needed]

Examples:
- [2026-02-21T10:30:00Z] Agent: Created plan — Complex multi-step task detected (keywords: invoice, client, external action).
- [2026-02-21T10:35:00Z] Agent: Marked step 1 complete — Identified client rate: $1,500 from /Accounting/Rates.md.
- [2026-02-21T10:40:00Z] Agent: Generated invoice PDF — Created /Invoices/2026-01_Client_A.pdf, 2 pages, size 185 KB.
- [2026-02-21T10:45:00Z] Agent: Drafted email for approval — Awaiting human review in /Pending_Approval/2026-02-21T10:40:00Z_email_client-a.md.
- [2026-02-21T11:00:00Z] Agent: Detected approval received — Email approved by human. Proceeding with send.
- [2026-02-21T11:05:00Z] Agent: Email sent successfully — Delivered to client_a@example.com. Status confirmed.
- [2026-02-21T11:10:00Z] Agent: Plan completed — All steps done. Moving to /Done/Plans/.
```

**Retention Strategy**:
- **Append-only**: Logs never deleted from active plan
- **When plan archived** (moved to /Done/Plans/):
  - Logs are preserved in full in /Done/Plans/PLAN-ID.md
  - No truncation or summarization
  - Enables full audit trail for historical review
- **Dashboard "Recent Activity"**: Shows last 10 entries across all plans (not just active plan)

### Rationale

- **Timestamp + ISO-8601**: Enables chronological sorting and filtering
- **Actor label**: "Agent" (future versions could add "Human" entries)
- **Action verb**: Clear what happened
- **Rationale**: Why the action occurred
- **Append-only**: Immutable history, auditable
- **Preserved in archives**: Long-term traceability

---

## Conclusion

These design decisions establish a clear, auditable, vault-native reasoning system that:

1. ✅ Adheres to Silver Law Constitution (all 4 Silver principles satisfied)
2. ✅ Enables multi-session persistence without external state
3. ✅ Gates all external actions through human-in-the-loop approval
4. ✅ Provides transparent reasoning logs for audit trails
5. ✅ Integrates with existing Bronze Tier infrastructure
6. ✅ Remains simple enough to implement incrementally and test thoroughly

All decisions prioritize **Local-First Privacy**, **Transparency**, and **Human Oversight**.

---

**Research Complete**: Ready for Phase 1 (Data Model & Contracts)

