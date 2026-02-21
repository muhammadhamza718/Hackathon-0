# Implementation Plan: Silver Tier Reasoning & Planning System

**Branch**: `003-silver-reasoning` | **Date**: 2026-02-21 | **Spec**: [specs/003-silver-reasoning/spec.md](spec.md)

**Input**: Feature specification from `specs/003-silver-reasoning/spec.md`

---

## Summary

Upgrade the Personal AI Employee from a "Triage Bot" (Bronze Tier) to a "Functional Assistant" (Silver Tier) by implementing autonomous reasoning loops using structured `Plan.md` files in the Obsidian vault. The system enables the agent to:

1. **Detect complex tasks** and create auditable plans with multi-step roadmaps
2. **Persist work across sessions** using a reconciliation-first startup model
3. **Gate external actions** through human-in-the-loop approval workflows
4. **Track progress** with real-time dashboard visibility and reasoning logs

**Technical Approach**: Extend the existing `managing-obsidian-vault` skill with new Reasoning procedures. Implement a PlanManager component that reads/parses/updates markdown-based plan files. Integrate with existing MCP server infrastructure for approval routing. No database or external tools — all state lives in the vault.

---

## Technical Context

**Language/Version**: Python 3.11+ (for agent extensions) + Markdown (vault format)

**Primary Dependencies**:
- Claude Code (existing reasoning engine)
- Obsidian (vault storage, markdown parser)
- MCP servers (existing infrastructure for external actions)
- Managing-obsidian-vault skill (to be extended)

**Storage**: File-based (Obsidian vault markdown files, no database)

**Testing**:
- Unit: Plan.md schema validation, state transitions
- Integration: Multi-step workflows, session resumption, approval routing
- End-to-end: Complex task → Plan creation → Execution → Completion

**Target Platform**: Local (agent running on user's machine with vault access)

**Project Type**: Single (agent skill extension + vault workflow integration)

**Performance Goals**:
- Plan creation: < 3 seconds
- Dashboard update: < 5 seconds
- Session resumption: < 2 seconds (vault scan + plan loading)
- Zero external action execution without approval

**Constraints**:
- No autonomous external actions (all gated by human approval)
- Single-agent operation (no concurrent multi-agent writes)
- File-based state (atomic markdown updates only)
- Obsidian vault must be always accessible

**Scale/Scope**:
- Plans: 3-20 steps per plan, unlimited concurrent plans (though only 1 active)
- Session persistence: survives days/weeks of interruptions
- Complexity detection: keywords-based (#high, invoice, client, payment, etc.)

---

## Constitution Check

**Relevant Principles** (Silver Law Constitution v2.0):

- **VI. Principle of Reasoning Integrity (Plan.md Loops)** ✅
  - GATE: Plan.md MUST follow rigid schema (Objective, Context, Roadmap, Reasoning Logs)
  - GATE: Reconciliation-First startup (scan `/Plans/`, find active plan, resume from checkpoint)
  - GATE: No multi-step task execution without Plan.md
  - STATUS: Implementation will enforce these

- **VII. Principle of Authorized Autonomy (MCP Governance)** ✅
  - GATE: Zero direct execution of external actions (MCP, email, payments, social posts)
  - GATE: All external actions MUST be drafted to `/Pending_Approval/` with rationale
  - GATE: Human MUST move file to `/Approved/` before execution
  - STATUS: Implementation will enforce approval gating

- **VIII. Principle of Multi-Sensory Integration** ✅
  - GATE: Support concurrent watchers writing to `/Inbox/` with JSON sidecars
  - GATE: Agent reads/triages from `/Inbox/`, routes to `/Needs_Action/` or `/Done/`
  - STATUS: Builds on existing Bronze Tier watcher infrastructure

- **IX. Principle of Brand & Privacy Stewardship** ✅
  - GATE: All external communications adhere to persona in `Company_Handbook.md`
  - GATE: PII redaction in vault files (email → `[EMAIL]`, phone → `[PHONE]`)
  - STATUS: Enforced at approval-drafting stage

**Gate Status**: ✅ **PASS** — Implementation plan satisfies all Silver Law principles. No violations.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-silver-reasoning/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (implementation roadmap)
├── research.md          # Phase 0 output (design decisions, patterns)
├── data-model.md        # Phase 1 output (entity schemas, state transitions)
├── quickstart.md        # Phase 1 output (demo workflow, usage guide)
├── contracts/           # Phase 1 output (API/interface specifications)
│   ├── plan-manager.md  # PlanManager API contract
│   ├── approval-routing.md  # Approval workflow contract
│   └── dashboard-sync.md    # Dashboard reconciliation contract
└── checklists/
    └── requirements.md   # Quality checklist (complete)
```

### Source Code (repository root)

**Option: Single Project (Agent Skill Extension)**

This feature is implemented as an extension to the existing `managing-obsidian-vault` skill, not a standalone project. The agent already has file system tools and vault access. We add Reasoning procedures to the existing skill.

```text
agents/skills/managing-obsidian-vault/
├── README.md
├── skill-definition.md   # Existing + Section 8: Reasoning
├── procedures/
│   ├── triage.md         # Existing Bronze procedures
│   ├── dashboard.md      # Existing Bronze procedures
│   ├── reasoning/        # NEW - Silver Tier
│   │   ├── initialize-plan.md
│   │   ├── update-step.md
│   │   ├── log-reasoning.md
│   │   └── archive-plan.md
│   └── approval-routing/ # NEW - Silver Tier
│       ├── draft-external-action.md
│       ├── detect-approval.md
│       └── execute-approved-action.md

tests/
├── unit/
│   ├── test-plan-schema-validation.py
│   ├── test-state-transitions.py
│   └── test-approval-routing.py
├── integration/
│   ├── test-plan-creation-workflow.py
│   ├── test-session-resumption.py
│   └── test-multi-step-execution.py
└── e2e/
    ├── test-invoice-workflow.py  # Demo scenario
    └── test-blocked-plan-resolution.py

vault-templates/
├── plan-template.md     # Template for creating new plans
├── approval-request-template.md  # Template for approval drafts
└── reasoning-log-template.md     # Template for log entries
```

**Structure Decision**: Single-project approach (skill extension) because:
- Agent already exists with necessary capabilities
- Vault operations are localized to the existing skill
- No separate backend/frontend needed
- Incremental testing of each reasoning procedure independently

---

## Implementation Roadmap

### Phase 1: Plan Manager & Core Reasoning Loop

**Goal**: Implement the core ability to create, read, parse, and update Plan.md files.

**Components**:

1. **PlanManager Class** (in skill context)
   - `create_plan(task_id, objective, context, steps)` → Creates Plan.md with valid schema
   - `load_plan(task_id)` → Reads and parses Plan.md YAML + Markdown sections
   - `find_active_plan()` → Scans `/Plans/`, finds most recent incomplete plan (Reconciliation-First)
   - `update_step(step_id, status, log_entry)` → Atomically updates checkpoint and Reasoning Logs
   - `mark_blocked(reason)` → Sets status to "Blocked" with explanation
   - `mark_completed()` → Moves plan to `/Done/Plans/`, archives
   - `validate_schema()` → Ensures YAML frontmatter is complete, sections present

2. **Plan.md Schema Implementation**
   - YAML frontmatter: task_id, source_link, created_date, priority, status, blocked_reason
   - Section: `# Objective` (single sentence)
   - Section: `## Context` (problem, dependencies, constraints)
   - Section: `## Roadmap` (numbered list with checkboxes, ✋ emoji for HITL steps)
   - Section: `## Reasoning Logs` (timestamped entries, actor, action, rationale)

3. **Session Startup Procedure** (`Initialize_Plan` in Reasoning section)
   - At agent session start: scan `/Plans/`, load most recent incomplete plan
   - Display to user: "Resuming plan [ID]: [Objective]"
   - Load last Reasoning Log entry to determine checkpoint
   - Resume execution from next uncompleted step

4. **Step Progress Tracking** (`Update_Step_Progress` procedure)
   - Mark step checkbox `[x]` when complete
   - Append timestamped entry to Reasoning Logs
   - Update Dashboard.md with progress (real-time)
   - Detect dependencies: if step N requires step M, wait for M to complete first

5. **Reasoning Logs** (`Log_Reasoning` procedure)
   - Append entries when: step completed, external action drafted, block detected, decision made
   - Format: `- [2026-02-21T10:30:00Z] Agent: [action] — [rationale]`
   - Enables transparency and debugging

**Output Artifacts**: research.md, data-model.md, plan-manager-contract.md, PlanManager implementation stubs

---

### Phase 2: Approval Routing & HITL Integration

**Goal**: Implement human-in-the-loop safety gates for all external actions.

**Components**:

1. **Approval Request Drafting** (`Draft_External_Action` procedure)
   - When agent detects external action (email, payment, social post, MCP call)
   - Create file in `/Pending_Approval/` with filename: `<ISO-timestamp>_<action-type>_<slug>.md`
   - Include metadata: action_type, target_recipient, rationale (referencing Plan.md step)
   - Include draft content (full email body, social post text, API payload)
   - Include instructions: "Move to `/Approved/` to execute" or "Move to `/Rejected/` to deny"
   - DO NOT proceed with action — stop and wait

2. **Approval Detection** (`Detect_Approval_Status` procedure)
   - Before executing external action: check if file moved from `/Pending_Approval/` to `/Approved/`
   - Re-read file to confirm approval status (double-check)
   - If moved to `/Rejected/`, log rejection in Reasoning Logs and wait for next steps
   - If still in `/Pending_Approval/`, remain blocked

3. **Approved Action Execution** (`Execute_Approved_Action` procedure)
   - Read approved file from `/Approved/`
   - Parse action_type and target
   - Call appropriate MCP server or handler (email-mcp, social-mcp, browser-mcp, etc.)
   - On success: move file to `/Done/Actions/`, update Reasoning Logs
   - On MCP failure: detect error, update Reasoning Logs, move back to `/Pending_Approval/` with failure reason
   - On success: continue to next plan step

4. **Block Detection** (`Detect_Blocked_Status` procedure)
   - Scan `/Pending_Approval/` for files related to current plan
   - If any ✋ (HITL) steps are still pending approval, mark plan as "Blocked: Awaiting Human"
   - If plan blocked > 24 hours (configurable), add warning to Dashboard
   - Provide context: which step is waiting, what approval is needed

**Output Artifacts**: approval-routing-contract.md, Approval Routing implementation stubs

---

### Phase 3: Dashboard Reconciliation & Real-Time Visibility

**Goal**: Implement dashboard updates that reflect current mission and block status in real-time.

**Components**:

1. **Dashboard Structure** (updates to existing Dashboard.md)
   - **⚡ Current Missions** section:
     - Displays active plan (status: Active | Blocked: [reason] | Completed)
     - Shows objective and current step
     - Shows pending approvals count
   - **📊 Plan Statistics** section:
     - Active Plans count
     - Blocked Plans count (and reasons)
     - Total Steps: Completed vs. Pending vs. Awaiting Approval
   - **🚨 Alerts** section (new):
     - Plans blocked > 24 hours
     - MCP failures or approval timeouts
   - **🕐 Recent Activity** section:
     - Last 10 significant events (plan created, step completed, approval rejected, etc.)
     - Timestamped and linked to plan/step

2. **Reconciliation Procedure** (`Reconcile_Dashboard` procedure)
   - Call after every significant file operation: plan creation, step completion, approval move, etc.
   - Scan `/Plans/` for all plans: extract objective, status, current step
   - Scan `/Pending_Approval/` for approval requests: link to plan, count by status
   - Rebuild Current Missions section from live data
   - Detect blocks and generate alerts
   - Update timestamps and recent activity log
   - Update Dashboard.md atomically

3. **Real-Time Update** constraint:
   - Dashboard updates must occur within 5 seconds of plan/step change
   - Implementation must not require external triggers — agent directly updates on file operations

**Output Artifacts**: dashboard-sync-contract.md, Dashboard reconciliation implementation stubs

---

### Phase 4: Skill Extension & Procedures

**Goal**: Extend the `managing-obsidian-vault` skill with new Reasoning section.

**Components**:

1. **Skill Update**: Add Section 8 - Reasoning to skill-definition.md
   - **Procedure**: `InitializePlan` → `create_plan(objective, context, steps, priority)`
   - **Procedure**: `UpdatePlanStep` → `update_step(step_id, status, log_entry)`
   - **Procedure**: `LogReasoning` → `append_reasoning_log(action, rationale)`
   - **Procedure**: `ArchivePlan` → `move_plan_to_done()`
   - **Procedure**: `DraftExternalAction` → `create_approval_request(action_type, draft_content, rationale)`
   - **Procedure**: `DetectBlocks` → `scan_pending_approvals_and_mark_blocked()`
   - **Procedure**: `ResumePlan` → `find_active_plan_and_load_checkpoint()`
   - **Procedure**: `ReconcileDashboard` → `rebuild_dashboard_from_live_plans()`

2. **Procedure Documentation**:
   - Each procedure includes: purpose, inputs, outputs, error handling, examples
   - Each procedure is independently testable
   - Each procedure integrates with existing skills (existing triage, dashboard, logging)

**Output Artifacts**: Updated skill-definition.md with Section 8 (Reasoning)

---

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    SILVER TIER REASONING SYSTEM                 │
├─────────────────────────────────────────────────────────────────┤

Session Start (Reconciliation-First)
  ↓
ResumePlan()
  └─→ Scan /Plans/
      └─→ Find most recent incomplete plan (status: Active | Blocked)
          └─→ Load last Reasoning Log checkpoint
              └─→ Display: "Resuming plan [ID]: [Objective]"
                  ↓
              Current Step Execution
                  ↓
         (Step is autonomous or requires HITL approval?)
                ↙                              ↘
         Autonomous                         HITL Required
             ↓                                  ↓
        Execute directly                DraftExternalAction()
             ↓                              └─→ Create file in /Pending_Approval/
        UpdatePlanStep()                       ├─→ Include rationale
             ↓                                 ├─→ Include draft content
        Mark step [x]                         └─→ STOP & WAIT
             ↓
        LogReasoning()
             ↓
        ReconcileDashboard()
             ↓
        Next Step?
         ↙       ↘
       YES       NO (Plan complete)
        ↓         ↓
     Loop    ArchivePlan()
              └─→ Move to /Done/Plans/
                  ↓
              Find next active plan
              (if any)

┌─ HITL Approval Routing (Parallel) ─┐
│                                     │
│ Human reviews /Pending_Approval/   │
│ Moves file to /Approved/           │
│                ↓                    │
│ DetectBlocks() or             │
│ detect-approval-status()            │
│                ↓                    │
│ ExecuteApprovedAction()             │
│ (call MCP server)                   │
│                ↓                    │
│ LogReasoning()                      │
│ UpdatePlanStep()                    │
│ ReconcileDashboard()                │
│ Resume main loop                    │
│                                     │
└─────────────────────────────────────┘

ReconcileDashboard() runs after every file operation
  → Scans /Plans/ for all plans
  → Updates Dashboard.md with Current Missions, Stats, Alerts
  → Real-time visibility
```

---

## Incremental Testing Strategy

### Test 1: Plan Creation & Schema Validation

**Trigger**: Provide agent with complex task ("Generate and send invoice to Client A")

**Expected**:
1. Agent suggests creating a plan
2. Plan.md created in `/Plans/` with valid YAML schema
3. Schema includes: task_id, source_link, created_date, priority, status, objective, context, roadmap, reasoning logs

**Verification**: Plan.md file exists, YAML parses without errors, all sections present

---

### Test 2: Session Resumption

**Trigger**:
1. Create plan with 3 steps
2. Mark Step 1 complete
3. End session
4. Start new session

**Expected**:
1. Agent scans `/Plans/` at startup
2. Loads the incomplete plan
3. Displays: "Resuming plan PLAN-001: Generate and send invoice"
4. Determines checkpoint: Step 2 is next
5. Continues execution from Step 2 (not re-doing Step 1)

**Verification**: Agent resumes from correct checkpoint, Reasoning Logs show correct step progression

---

### Test 3: Approval Routing (HITL Safety)

**Trigger**: Plan step requires sending an email

**Expected**:
1. Agent drafts email and creates file: `2026-02-21T10:30:00Z_email_client-a-invoice.md`
2. File placed in `/Pending_Approval/`
3. Agent does NOT send email
4. Human reviews file and moves to `/Approved/`
5. Agent detects move, re-reads file, executes email via MCP

**Verification**: Email draft in `/Pending_Approval/`, no actual send until `/Approved/` move, Reasoning Logs show approval and execution

---

### Test 4: Block Detection

**Trigger**: Plan has step with ✋ emoji (HITL required) and approval file in `/Pending_Approval/`

**Expected**:
1. Agent detects step is waiting for approval
2. Marks plan status: "Blocked: Awaiting Human Approval"
3. Dashboard shows alert
4. When human approves, agent resumes plan

**Verification**: Plan status correctly marked as Blocked, Dashboard displays alert, plan resumes when approved

---

### Test 5: Dashboard Real-Time Updates

**Trigger**: Plan progresses through steps, approval requests created/approved

**Expected**:
1. Dashboard updates within 5 seconds of each file operation
2. Current Missions section shows active plan, current step, pending approvals
3. Stats section shows counts: Active, Blocked, Completed steps
4. Alerts section shows blocked plans > 24 hours
5. Recent Activity shows last 10 events with timestamps

**Verification**: Dashboard content matches live `/Plans/` and `/Pending_Approval/` state, updates timely

---

### Test 6: Multi-Step Workflow (End-to-End)

**Trigger**: "Generate invoice for Client A, send via email, log in accounting"

**Expected**:
1. Plan created with 3 steps
2. Step 1 (generate): autonomous, completes immediately
3. Step 2 (email): requires approval, draft created, agent waits
4. Human approves → Step 2 executes via MCP → logs success
5. Step 3 (accounting): autonomous, completes
6. Plan moved to `/Done/Plans/`

**Verification**: All steps execute in order, approvals enforced, final plan in `/Done/Plans/` with complete Reasoning Logs

---

## Complexity Tracking

| Aspect | Why Needed | Simpler Alternative Rejected |
|--------|-----------|------------------------------|
| Plan persistence across sessions | Users may close Claude Code mid-workflow; resuming without data loss is critical for Silver Tier trust model | Stateless model: Would lose all progress, breaking the "Digital FTE" promise of reliability |
| Atomic Plan.md updates | Partial writes would corrupt YAML or leave incomplete sections, breaking parsers | Non-atomic updates: Could leave plans in unparseable state on unexpected termination |
| Approval routing with file moves | File-based approval (move to `/Approved/`) is vault-native and observable by humans; no external state | Database-backed approvals: Would require external service, violating Local-First Privacy principle |
| Real-time dashboard sync | Humans need visibility into agent work; stale dashboard undermines trust | Pull-based updates: Would require polling, introducing latency and complexity |
| Recursive/dependent steps | Complex workflows often have task dependencies (step N requires step M to complete first) | Linear-only steps: Would force awkward workarounds, limiting practical use cases |

---

## Dependencies & Integration Points

**Existing Infrastructure**:
- `managing-obsidian-vault` skill (to be extended with Reasoning procedures)
- MCP servers (email-mcp, social-mcp, browser-mcp, etc. — existing)
- Obsidian vault folder structure (`/Plans/`, `/Pending_Approval/`, `/Done/`, `/Logs/` — existing Bronze Tier)
- Company_Handbook.md (existing Bronze Tier, used for persona and approval thresholds)
- Dashboard.md (existing Bronze Tier, to be extended)

**New Files/Folders**:
- `/Plans/` directory for active and draft plans
- `/Pending_Approval/` directory for approval request files
- `/Done/Plans/` directory for archived completed plans
- `/Approved/` directory for approved actions (temporary, moved to `/Done/Actions/` after execution)
- `/Rejected/` directory for rejected actions (kept for audit trail)

**No External Dependencies**: No new software, APIs, or cloud services required. All processing is local, vault-based.

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|-------------------|
| Plan.md corruption on unexpected exit | File-based checkpoint + atomic writes + session startup validation |
| Duplicate plan creation | Detection logic: scan `/Plans/`, compare task_id/source_link before creating new plan |
| MCP server offline during approval execution | Error handling: detect MCP failure, log in Reasoning Logs, move approval file back to `/Pending_Approval/` with failure reason, alert human |
| Human forgets to approve time-sensitive action | Dashboard alerts for plans blocked > 24 hours; Reasoning Logs show approval timestamp for audit |
| Plan.md file manually edited while agent executing | Atomic reads: load plan at start of each step, detect conflicts, merge or alert human |
| Reasoning Logs grow unbounded | Archival strategy: when plan moved to `/Done/Plans/`, truncate logs to summary or move to separate file |

---

## Success Criteria (From Spec)

✅ Implements SC-001: Agent successfully creates a Plan.md with valid schema in under 3 seconds
✅ Implements SC-002: Agent accurately resumes from the last checkpoint 100% of the time
✅ Implements SC-003: All external actions drafted to `/Pending_Approval/` with 100% compliance
✅ Implements SC-004: Dashboard reflects current plan status within 5 seconds
✅ Implements SC-005: Blocked plans correctly identified and marked 100% of the time
✅ Implements SC-006: Human can track full reasoning history via Reasoning Logs
✅ Implements SC-007: System handles multi-session workflows without data loss

---

## Next Steps

1. **Phase 0 (Research)**: Generate `research.md` documenting design decisions (Plan.md schema structure, session resumption logic, approval routing patterns, dashboard sync strategy)
2. **Phase 1 (Design)**: Generate `data-model.md` with entity schemas, state transitions, and `contracts/` with API specifications
3. **Phase 2 (Tasks)**: Run `/sp.tasks` to generate `tasks.md` with implementation tasks (PlanManager, Approval Routing, Dashboard Reconciliation, Skill Extension)
4. **Phase 3 (Implementation)**: Implement tasks incrementally, testing each component as described in Incremental Testing Strategy
5. **Phase 4 (Review)**: Validate against spec and constitution before merge

---

**Plan Status**: ✅ Ready for Phase 0 Research and Phase 1 Design

