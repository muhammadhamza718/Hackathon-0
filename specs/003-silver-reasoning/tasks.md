---
description: "Task list for Silver Tier Reasoning & Planning System implementation"
---

# Tasks: Silver Tier Reasoning & Planning System

**Input**: Design documents from `specs/003-silver-reasoning/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md (design decisions)

**Status**: Ready for implementation
**Total Tasks**: 48 atomic tasks across 7 phases
**MVP Scope**: Phase 1-4 (Foundational + US1) delivers core reasoning loop

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Each story can be delivered as an independent increment after foundational work is complete.

---

## Format: `[ID] [P?] [Story] Description`

- **[ID]**: Task identifier (T001-T048)
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5) — Setup and Foundational phases have no story label
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure & Templates)

**Purpose**: Create templates, folder structure, and foundational files for Silver Tier system

**⚠️ Prerequisites**: None — can start immediately

---

### 1.1 Plan.md Template & Schema

- [x] T001 Create `references/plan-template.md` with rigid schema: YAML frontmatter + Markdown sections

**Details**: File must include:
- YAML fields: `task_id`, `source_link`, `created_date`, `priority`, `status`, `blocked_reason`
- Sections: `# Objective`, `## Context`, `## Roadmap` (with checkboxes), `## Reasoning Logs`
- Example filled-in plan showing all sections correctly formatted

---

### 1.2 Vault Folder Structure

- [x] T002 [P] Create `/Plans/` folder for active and draft plans
- [x] T003 [P] Create `/Done/Plans/` folder for archived completed plans
- [x] T004 [P] Create `/Pending_Approval/` folder for approval request files (if not already present from Bronze Tier)
- [x] T005 [P] Create `/Approved/` folder for approved actions (temporary staging)
- [x] T006 [P] Create `/Rejected/` folder for rejected actions (audit trail)

---

### 1.3 Agent & Skill Documentation

- [x] T007 [P] Create `agents/silver-reasoning-agent.md` documenting Silver Tier agent behavior and Reconciliation-First startup
- [x] T008 Create approval request template file: `references/approval-request-template.md`
- [x] T009 Create reasoning log entry template file: `references/reasoning-log-template.md`

---

**Checkpoint**: Foundational templates and folder structure ready. Phase 1 complete.

---

## Phase 2: Foundational (Blocking Prerequisites for All User Stories)

**Purpose**: Core PlanManager implementation and agent persona upgrade

**⚠️ CRITICAL**: No user story work can begin until this phase is 100% complete

---

### 2.1 PlanManager Core Implementation

- [x] T010 [P] Implement `PlanManager.create_plan()` function to create new Plan.md from template with valid schema
  - File: `agents/skills/managing-obsidian-vault/plan-manager.py`
  - Inputs: task_id, objective, context, steps, priority
  - Output: Creates `/Plans/PLAN-<task_id>.md` with filled YAML + markdown

- [x] T011 [P] Implement `PlanManager.load_plan()` function to read and parse existing Plan.md
  - File: `agents/skills/managing-obsidian-vault/plan-manager.py`
  - Inputs: plan_id
  - Output: Parsed plan object (metadata + sections)
  - Error handling: Invalid YAML, missing sections

- [x] T012 [P] Implement `PlanManager.find_active_plan()` function for Reconciliation-First startup
  - File: `agents/skills/managing-obsidian-vault/plan-manager.py`
  - Scan `/Plans/` for incomplete plans
  - Prioritize: Status (Active > Blocked > Draft), then by created_date descending
  - Output: Most relevant plan or null if none found

- [x] T013 [P] Implement `PlanManager.validate_schema()` function to ensure Plan.md integrity
  - File: `agents/skills/managing-obsidian-vault/plan-manager.py`
  - Check YAML frontmatter completeness
  - Check mandatory sections present
  - Check reasoning logs are ISO-8601 timestamped

---

### 2.2 Session Startup & Reconciliation-First

- [x] T014 Update agent instructions in `agents/silver-reasoning-agent.md` to include Reconciliation-First startup procedure
  - Pseudocode:
    ```
    Session Start:
      1. Call PlanManager.find_active_plan()
      2. If plan found: Load plan, display "Resuming plan [ID]: [Objective]"
      3. Load last Reasoning Log entry to determine checkpoint
      4. Resume execution from next uncompleted step
      5. If no plan found: Begin normal triage flow
    ```

- [x] T015 Implement session startup logic in agent skill
  - File: `agents/skills/managing-obsidian-vault/procedures/initialize-session.md`
  - Validate: At every new session, agent calls find_active_plan() before accepting new input

---

### 2.3 Complexity Detection

- [x] T016 [P] Implement complexity detection heuristics in agent instructions
  - File: `agents/silver-reasoning-agent.md` → new section "Complexity Detection"
  - Keywords (high priority): `#high`, `urgent`, `ASAP`, `critical`
  - Keywords (multi-step): `invoice`, `payment`, `client`, `project`, `campaign`, `report`, `audit`, `schedule`
  - Keywords (external action): `send`, `post`, `publish`, `email`, `message`, `call`, `pay`
  - Logic: If ANY keyword detected + multi-step → suggest creating plan

- [x] T017 Add suggestion logic: Agent recommends "I should create a plan for this" before initializing Plan.md
  - File: `agents/silver-reasoning-agent.md`
  - User can approve or skip plan creation

---

### 2.4 Step Progress Tracking

- [x] T018 [P] Implement `PlanManager.update_step()` function to mark steps complete
  - File: `agents/skills/managing-obsidian-vault/plan-manager.py`
  - Inputs: step_id, status (complete|blocked|skipped), log_entry
  - Updates: Checkbox `[ ]` → `[x]`, appends Reasoning Log entry
  - Atomicity: Entire Plan.md written in one operation

- [x] T019 Implement `PlanManager.append_reasoning_log()` function
  - File: `agents/skills/managing-obsidian-vault/plan-manager.py`
  - Format: `- [ISO-timestamp] Agent: [action] — [rationale]`
  - Append to `/Plans/PLAN-<id>.md` Reasoning Logs section

---

### 2.5 Skill Extension Framework

- [x] T020 Create Section 8 stub in `agents/skills/managing-obsidian-vault/SKILL.md`
  - File: `agents/skills/managing-obsidian-vault/SKILL.md`
  - Add Section 8 header: "Reasoning & Planning (Silver Tier)"
  - List all procedures to be implemented: InitializePlan, UpdatePlanStep, LogReasoning, ArchivePlan, DraftExternalAction, DetectBlocks, ResumePlan, ReconcileDashboard
  - Each procedure with stub description and inputs/outputs

---

**Checkpoint**: PlanManager implementation complete, agent personality upgraded with Reconciliation-First logic. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Agent Receives Complex Request (Priority: P1) 🎯 MVP

**Goal**: Agent can detect complex tasks and create structured Plan.md files with valid schema, preventing immediate execution

**Independent Test**:
1. Provide agent with complex task ("Generate and send invoice to Client A")
2. Verify Plan.md created in `/Plans/` with valid YAML schema
3. Verify agent suggests plan before creating
4. Verify no external actions occur until approval

---

### 3.1 Complexity Detection & Plan Initialization

- [ ] T021 [P] [US1] Implement `InitializePlan` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Inputs: objective, context, steps (as list)
  - Process: Call PlanManager.create_plan() from T010
  - Output: Confirmation message with plan ID and location
  - Error handling: Catch schema validation errors, log, alert user

- [ ] T022 [US1] Update agent to detect complexity keywords and suggest plan
  - File: `agents/silver-reasoning-agent.md` → "Task Reception" section
  - When user input detected: Run complexity heuristics (T016)
  - If complex: Suggest "I should create a plan for this" with reasoning
  - User approves → Call InitializePlan procedure
  - User skips → Execute task directly (no plan)

- [ ] T023 [US1] Add duplicate plan detection
  - File: `agents/skills/managing-obsidian-vault/plan-manager.md` → add function `detect_duplicate_plan()`
  - Check existing plans for same task_id or source_link
  - If duplicate found: Consolidate (merge steps) or alert user to manual resolution

---

### 3.2 Plan.md Creation & Validation

- [ ] T024 [P] [US1] Test: Unit test for Plan.md schema validation
  - File: `tests/unit/test-plan-schema-validation.py`
  - Create sample Plan.md with valid YAML, verify parsing succeeds
  - Create sample Plan.md with invalid YAML, verify error handling
  - Create sample with missing sections, verify error handling

- [ ] T025 [P] [US1] Test: Integration test for plan creation workflow
  - File: `tests/integration/test-plan-creation-workflow.py`
  - Trigger: Provide complex task to agent
  - Assert: Plan.md file exists in `/Plans/` with correct content
  - Assert: All sections present (Objective, Context, Roadmap, Reasoning Logs)
  - Assert: YAML frontmatter valid and complete

---

### 3.3 Simple vs. Complex Task Differentiation

- [ ] T026 [US1] Test: Simple task (no plan creation)
  - File: `tests/integration/test-simple-task-no-plan.py`
  - Trigger: Simple request "Show me the dashboard"
  - Assert: No Plan.md created
  - Assert: Task executes directly

- [ ] T027 [US1] Test: Multi-step task (plan creation)
  - File: `tests/integration/test-complex-task-plan-creation.py`
  - Trigger: Complex request with invoice + email + logging
  - Assert: Plan.md created with 3+ steps
  - Assert: External actions NOT executed immediately
  - Assert: Approval workflow initiated (next story)

---

**Checkpoint**: User Story 1 complete. Agent can detect complex tasks and create valid Plan.md files. Simple tasks bypass planning.

---

## Phase 4: User Story 2 - Agent Tracks Progress Across Sessions (Priority: P1)

**Goal**: Agent's reasoning persists across session interruptions. When a session resumes, agent loads the most recent incomplete plan and continues from the exact checkpoint.

**Independent Test**:
1. Create plan with 3 steps
2. Mark Step 1 complete
3. End session
4. Start new session
5. Verify: Agent loads same plan, checkpoint is Step 2, Step 1 not re-executed

---

### 4.1 Multi-Session Persistence

- [ ] T028 [P] [US2] Implement `ResumePlan` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Process:
    1. Call PlanManager.find_active_plan()
    2. If plan found: Load plan, extract last Reasoning Log entry
    3. Determine checkpoint from last log entry
    4. Display "Resuming plan [ID]: [Objective]" to user
    5. Return plan object with checkpoint
  - Output: Active plan with checkpoint information

- [ ] T029 [US2] Integrate ResumePlan into session startup
  - File: `agents/silver-reasoning-agent.md` → Session Startup section
  - Before accepting user input: Call ResumePlan procedure
  - If plan loaded: Display resume message and current step
  - If no plan: Continue with normal triage

---

### 4.2 Checkpoint & Step Tracking

- [ ] T030 [P] [US2] Implement `UpdatePlanStep` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Inputs: step_id, new_status (complete|blocked|skipped), log_entry_text
  - Process:
    1. Load plan
    2. Find step in Roadmap
    3. Update checkbox: `- [ ]` → `- [x]` (or appropriate status)
    4. Call LogReasoning to append entry
    5. Write Plan.md atomically
  - Output: Confirmation of step update

- [ ] T031 [US2] Implement `LogReasoning` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Inputs: action (string), rationale (string)
  - Process:
    1. Generate ISO-8601 timestamp
    2. Format entry: `- [timestamp] Agent: [action] — [rationale]`
    3. Append to plan's Reasoning Logs section
    4. Write Plan.md atomically
  - Output: Log entry appended, plan persisted

---

### 4.3 Session Resumption Tests

- [ ] T032 [P] [US2] Test: Session resumption with checkpoint loading
  - File: `tests/integration/test-session-resumption-checkpoint.py`
  - Setup: Create plan with 3 steps, mark Step 1 complete, end session
  - Trigger: Start new session
  - Assert: Plan loaded correctly
  - Assert: Checkpoint identified as Step 2
  - Assert: Agent displays "Resuming plan"
  - Assert: Step 1 not re-executed

- [ ] T033 [P] [US2] Test: Plan prioritization (Active > Blocked > Draft, recent first)
  - File: `tests/integration/test-plan-prioritization.py`
  - Setup: Create 3 plans (Draft, Active, Blocked) with different timestamps
  - Trigger: Session start
  - Assert: Active plan loaded (highest priority)
  - If multiple Active: Most recent loaded

- [ ] T034 [US2] Test: Reasoning Logs accuracy
  - File: `tests/integration/test-reasoning-logs.py`
  - Setup: Create plan, execute steps, log entries
  - Assert: Each step completion generates timestamped log entry
  - Assert: Timestamps are ISO-8601 format
  - Assert: Logs preserve chronological order

---

### 4.4 Atomic Plan Updates

- [ ] T035 [US2] Ensure Plan.md atomicity (no partial writes)
  - File: `agents/skills/managing-obsidian-vault/plan-manager.md` → add atomic_write() helper
  - Requirement: All Plan.md writes must be complete or fail; no partially-written files
  - Implementation: Write to temp file, validate schema, atomic rename/move

---

**Checkpoint**: User Story 2 complete. Agent can resume from checkpoints across sessions. Reasoning Logs provide full audit trail.

---

## Phase 5: User Story 3 - Agent Drafts External Actions for Approval (Priority: P1)

**Goal**: All external actions (email, payment, social posts, MCP calls) are drafted to `/Pending_Approval/` for human review before execution. Agent NEVER executes external actions without approval.

**Independent Test**:
1. Agent task requires sending email
2. Verify: Approval request file created in `/Pending_Approval/` with full draft
3. Verify: Email NOT sent until file moved to `/Approved/`
4. Verify: On approval move, email executes via MCP

---

### 5.1 Approval Request Drafting

- [ ] T036 [P] [US3] Implement `DraftExternalAction` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Inputs: action_type (email|payment|social|api_call), target_recipient, draft_content, rationale, plan_step_id
  - Process:
    1. Generate filename: `<ISO-timestamp>_<action_type>_<slug>.md`
    2. Create approval request file with:
       - Metadata: action_type, target_recipient, rationale, plan step reference
       - Draft content: full email body, payment details, post text, etc.
       - Instructions for human: "Move to /Approved/ to execute" or "Move to /Rejected/ to deny"
    3. Write file to `/Pending_Approval/` atomically
    4. DO NOT proceed with action
  - Output: File path and confirmation message

- [ ] T037 [US3] Add safety gate: Prevent direct MCP action without approval file
  - File: `agents/silver-reasoning-agent.md` → "External Action Safety" section
  - Rule: Before ANY call to MCP server (email, social, payment), check:
    1. Is this action part of a Plan? (have plan_step_id)
    2. Is step marked with ✋ (HITL required)?
    3. If yes: Draft approval request (call DraftExternalAction), DO NOT call MCP
    4. If no: Can proceed with MCP call (after 100% safety review)

---

### 5.2 Approval Detection & Execution

- [ ] T038 [P] [US3] Implement approval detection logic
  - File: `agents/skills/managing-obsidian-vault/procedures/detect-approval.md`
  - Process:
    1. Scan `/Pending_Approval/` for files related to current plan
    2. For each file:
       - If moved to `/Approved/`: Proceed to execute
       - If moved to `/Rejected/`: Log rejection, update Reasoning Logs, wait
       - If still in `/Pending_Approval/`: Plan is blocked
  - Output: Approval status (approved|rejected|pending)

- [ ] T039 [US3] Implement approved action execution
  - File: `agents/skills/managing-obsidian-vault/procedures/execute-approved-action.md`
  - Process:
    1. Re-read approval file from `/Approved/` to confirm status
    2. Parse action_type and target from file
    3. Call appropriate MCP server (email-mcp, social-mcp, etc.)
    4. On success: Move file to `/Done/Actions/`, update Reasoning Logs
    5. On MCP failure: Log error, move file back to `/Pending_Approval/` with failure reason
  - Output: Execution result (success|failure)

---

### 5.3 Approval Workflow Tests

- [ ] T040 [P] [US3] Test: Approval request file creation
  - File: `tests/integration/test-approval-request-creation.py`
  - Trigger: Agent task requires external action (email)
  - Assert: File created in `/Pending_Approval/` with correct name format
  - Assert: File includes draft content, rationale, plan step reference
  - Assert: Email NOT sent immediately

- [ ] T041 [P] [US3] Test: Approval execution on file move
  - File: `tests/integration/test-approval-execution.py`
  - Setup: Approval request file in `/Pending_Approval/`
  - Trigger: Human moves file to `/Approved/`
  - Assert: Agent detects move
  - Assert: Calls MCP server
  - Assert: Email/action executed
  - Assert: File moved to `/Done/Actions/`

- [ ] T042 [P] [US3] Test: Rejection handling
  - File: `tests/integration/test-approval-rejection.py`
  - Setup: Approval request file in `/Pending_Approval/`
  - Trigger: Human moves file to `/Rejected/`
  - Assert: Agent detects rejection
  - Assert: MCP NOT called
  - Assert: Reasoning Logs updated with rejection note
  - Assert: Plan remains in "Awaiting Next Steps" state

---

### 5.4 HITL Marker Implementation

- [ ] T043 [US3] Implement ✋ (HITL) marker detection in agent
  - File: `agents/silver-reasoning-agent.md` → "HITL Marker Detection" section
  - Logic: When parsing plan roadmap, identify steps with ✋ emoji
  - For each ✋ step: Mark as "requires human approval before execution"
  - Block execution of ✋ steps until approval file moved to `/Approved/`

- [ ] T044 [US3] Add validation: Cannot mark ✋ step complete without approval reference
  - File: `agents/skills/managing-obsidian-vault/plan-manager.md` → add function `validate_hitl_completion()`
  - Rule: If step has ✋ marker, UpdatePlanStep() must include reference to approved file
  - Prevent: Marking step `[x]` without approval proof

---

**Checkpoint**: User Story 3 complete. All external actions gated through `/Pending_Approval/` → `/Approved/` workflow. 100% human-in-the-loop compliance.

---

## Phase 6: User Story 4 - Dashboard Reflects Current Mission Status (Priority: P2)

**Goal**: Dashboard.md displays active plan, current step, pending approvals, and blocks so humans have real-time visibility into agent work.

**Independent Test**:
1. Create plan with multiple steps
2. Complete some steps, move approval to `/Pending_Approval/`
3. Verify: Dashboard shows Current Mission with plan objective, current step, pending approvals
4. Verify: Dashboard updates within 5 seconds of changes

---

### 6.1 Dashboard Structure & Templates

- [ ] T045 [P] [US4] Create dashboard template with Current Missions section
  - File: `references/dashboard-template.md`
  - Sections:
    - `⚡ Current Missions`: Active plan ID, objective, status, current step, pending approvals
    - `📊 Plan Statistics`: Active count, Blocked count, Steps completed
    - `🚨 Alerts`: Plans blocked > 24 hours
    - `🕐 Recent Activity`: Last 10 events with timestamps

- [ ] T046 [US4] Modify existing Dashboard.md with new Current Missions section
  - File: `Dashboard.md` (vault root)
  - Add new `⚡ Current Missions` section near top (high visibility)
  - Preserve existing sections (compatibility with Bronze Tier)

---

### 6.2 Dashboard Reconciliation Logic

- [ ] T047 [US4] Implement `ReconcileDashboard` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Process:
    1. Scan `/Plans/` for all plans: extract ID, objective, status, step counts
    2. Scan `/Pending_Approval/` for approval files: count by type, link to plans
    3. Identify Active plan (most recent with status Active or Blocked)
    4. Rebuild `⚡ Current Missions` section with live data
    5. Update stats and alerts
    6. Update recent activity log (last 10 events)
    7. Write Dashboard.md atomically
  - Output: Confirmation that dashboard updated
  - Trigger: After every significant file operation (plan created, step completed, approval moved, etc.)

- [ ] T048 [US4] Integrate dashboard updates into workflow
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` → Section 3 (Dashboard Updates)
  - Call ReconcileDashboard after: InitializePlan, UpdatePlanStep, DraftExternalAction, ExecuteApprovedAction, ArchivePlan
  - Target latency: < 5 seconds

---

### 6.3 Dashboard Tests

- [ ] T049 [P] [US4] Test: Dashboard reflects current mission
  - File: `tests/integration/test-dashboard-current-mission.py`
  - Setup: Create active plan
  - Assert: Dashboard shows plan objective, status, current step
  - Assert: Information matches `/Plans/` file content

- [ ] T050 [P] [US4] Test: Dashboard shows blocked status
  - File: `tests/integration/test-dashboard-blocked-status.py`
  - Setup: Create plan with ✋ step, create approval file in `/Pending_Approval/`
  - Assert: Dashboard shows status: "Blocked: Awaiting Human Approval"
  - Assert: Displays which step is blocked and what approval is needed

- [ ] T051 [US4] Test: Dashboard real-time updates
  - File: `tests/integration/test-dashboard-real-time-update.py`
  - Setup: Dashboard initially empty
  - Trigger: Create plan
  - Assert: Dashboard updated within 5 seconds
  - Assert: Plan appears in Current Missions section

---

**Checkpoint**: User Story 4 complete. Dashboard provides real-time visibility into agent work, plan status, and blocks.

---

## Phase 7: User Story 5 - Agent Resolves Blocked Plans (Priority: P2)

**Goal**: Agent detects when plans are blocked, alerts user to what is needed, and resumes work when blocks are resolved.

**Independent Test**:
1. Create plan with blocked step (approval pending)
2. Verify: Dashboard shows "Blocked" status with details
3. Move approval to `/Approved/`
4. Verify: Agent detects unblock and resumes execution

---

### 7.1 Block Detection & Status Management

- [ ] T052 [P] [US5] Implement `DetectBlocks` procedure in SKILL.md Section 8
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` (Section 8)
  - Process:
    1. Scan `/Pending_Approval/` for files related to current plan
    2. For each approval file found:
       - If file has ✋ step in plan's roadmap: This is required approval
       - If approval file in `/Pending_Approval/`: Plan MUST be blocked
    3. If any required approvals pending:
       - Set plan status: "Blocked: Awaiting Human Approval"
       - Set blocked_reason: "Approval request: [filename] waiting since [time]"
       - Add Reasoning Log: "Plan blocked at step N, awaiting [approval type]"
    4. When approval moves to `/Approved/`:
       - Detect move
       - Update plan status: "Active" (if other steps remain)
       - Remove blocked_reason
       - Add Reasoning Log: "Approval received for [step]. Resuming execution."
  - Output: Block status and reasons

- [ ] T053 [US5] Add block detection to dashboard
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` → Section 8 (within ReconcileDashboard)
  - When plan status is "Blocked":
    - Display warning in Current Missions
    - Show exactly what is waiting (which approval, for how long)
    - List who needs to take action (human must move file to `/Approved/`)

---

### 7.2 Stalled Task Alerts

- [ ] T054 [US5] Implement 24-hour block threshold alert
  - File: `agents/skills/managing-obsidian-vault/SKILL.md` → Section 8 (within ReconcileDashboard)
  - Process:
    1. For each blocked plan: Calculate time since block began
    2. If blocked > 24 hours: Add to `🚨 Alerts` section in Dashboard
    3. Alert format: "⚠️ Plan PLAN-001 blocked for X hours (step: [step desc])"
    4. Include context: "Last approval request: [details]"

- [ ] T055 [US5] Implement block resolution detection
  - File: `agents/skills/managing-obsidian-vault/procedures/detect-block-resolution.md`
  - Trigger: After approval file moves to `/Approved/`
  - Process:
    1. Call DetectBlocks to check current block status
    2. If block resolved: Update plan status to "Active"
    3. Display to user: "Block resolved! Resuming plan [ID]"
    4. Resume execution from next step

---

### 7.3 Block Resolution Tests

- [ ] T056 [P] [US5] Test: Block detection when approval pending
  - File: `tests/integration/test-block-detection.py`
  - Setup: Create plan with ✋ step, create approval file in `/Pending_Approval/`
  - Assert: DetectBlocks identifies plan as blocked
  - Assert: blocked_reason field populated
  - Assert: Dashboard shows "Blocked: Awaiting Human Approval"

- [ ] T057 [P] [US5] Test: Block resolution on approval
  - File: `tests/integration/test-block-resolution.py`
  - Setup: Blocked plan with approval in `/Pending_Approval/`
  - Trigger: Move approval file to `/Approved/`
  - Assert: Agent detects move
  - Assert: Plan status changes back to "Active"
  - Assert: Execution resumes from next step
  - Assert: Dashboard updates immediately

- [ ] T058 [P] [US5] Test: 24-hour block alert
  - File: `tests/integration/test-24hr-block-alert.py`
  - Setup: Create blocked plan, simulate 24+ hours passing
  - Assert: Dashboard generates alert in `🚨 Alerts` section
  - Assert: Alert includes plan ID, duration, and context

- [ ] T059 [US5] Test: Multiple concurrent blocked plans
  - File: `tests/integration/test-multiple-blocked-plans.py`
  - Setup: Create 3 plans, 2 of which are blocked
  - Assert: Dashboard correctly identifies which plans are blocked
  - Assert: Correct approvals requested for each
  - Assert: Each can be unblocked independently

---

**Checkpoint**: User Story 5 complete. Agent detects blocks, alerts humans, and resumes when blocks are resolved.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, logging, documentation, and integration tests

---

### 8.1 Error Handling & Recovery

- [ ] T060 [P] Implement error handling for corrupted Plan.md files
  - File: `agents/skills/managing-obsidian-vault/plan-manager.md` → add `handle_corrupted_plan()`
  - Process: Detect invalid YAML, missing sections, incomplete file
  - Action: Log error in Dashboard, display alert to human, DO NOT crash
  - Recovery: Human reviews and manually fixes or deletes file

- [ ] T061 [P] Implement MCP failure detection and recovery
  - File: `agents/skills/managing-obsidian-vault/procedures/execute-approved-action.md`
  - Process: Catch MCP server errors (timeout, offline, auth failure)
  - Action: Log error in Reasoning Logs, move approval file back to `/Pending_Approval/` with failure reason
  - Recovery: Human can review error and retry

- [ ] T062 [P] Implement duplicate plan consolidation
  - File: `agents/skills/managing-obsidian-vault/plan-manager.md` → enhance `detect_duplicate_plan()`
  - Process: Detect if two plans have same task_id or source_link
  - Action: Merge steps or consolidate, move duplicate to `/Archive/`, log in Reasoning Logs
  - Recovery: Human can review merge result

---

### 8.2 Audit Logging & Traceability

- [ ] T063 [P] Enhance logging to track all plan operations
  - File: `agents/skills/managing-obsidian-vault/procedures/audit-logging.md`
  - Log events: plan created, step completed, approval drafted, approval executed, plan archived
  - Format: Append to `/Logs/YYYY-MM-DD.json`
  - Content: timestamp, action, actor (Agent), plan_id, step_id, result (success/failure)

- [ ] T064 [P] Add traceability: Link approval requests back to plan steps
  - File: `agents/skills/managing-obsidian-vault/procedures/draft-external-action.md` (enhance)
  - Include in approval file: `plan_id`, `step_id`, `step_description`
  - Enable full audit trail from original task → plan → approval → execution

---

### 8.3 Documentation & Reference

- [ ] T065 Create comprehensive troubleshooting guide
  - File: `docs/silver-reasoning-troubleshooting.md`
  - Scenarios: Corrupted plans, MCP failures, forgotten approvals, duplicate plans
  - Recovery procedures for each

- [ ] T066 Create quick-start guide for Silver Tier workflows
  - File: `docs/silver-reasoning-quickstart.md`
  - Example: Invoice workflow (request → plan → approval → completion)
  - Example: Project with multiple steps and dependencies

- [ ] T067 Update agent instructions with Silver Tier best practices
  - File: `agents/silver-reasoning-agent.md` → add "Best Practices" section
  - When to create plans, when to skip
  - How to structure steps for clarity
  - Common patterns and templates

---

### 8.4 Full Integration Tests

- [ ] T068 [P] Full-loop simulation: Invoice workflow
  - File: `tests/e2e/test-invoice-workflow.py`
  - Scenario: "Generate and send invoice to Client A for $1,500"
  - Steps:
    1. Request triggers complexity detection
    2. Plan created with 4 steps
    3. Steps 1-3 execute (calculate, generate PDF, log)
    4. Step 4 (email) triggers approval request
    5. Human approves
    6. Email sent via MCP
    7. Plan moved to `/Done/Plans/`
    8. Dashboard updated
  - Assertions: All steps executed in order, no skipped, approval enforced

- [ ] T069 [P] Full-loop simulation: Multi-session workflow
  - File: `tests/e2e/test-multi-session-workflow.py`
  - Scenario: Complex task interrupted mid-execution
  - Steps:
    1. Session 1: Create plan, complete steps 1-2
    2. Session 1 ends
    3. Session 2 starts: Agent loads plan, resumes from step 3
    4. Session 2: Complete steps 3-4, approval needed
    5. Session 2 ends before approval
    6. Session 3 starts: Plan still loaded, awaiting approval
    7. Human approves
    8. Session 4 starts: Approval detected, execution continues
    9. Plan completed

- [ ] T070 [P] Full-loop simulation: Safety breach prevention
  - File: `tests/e2e/test-safety-breach-prevention.py`
  - Scenario: Agent attempts to send email without approval
  - Expected: Agent creates approval request, stops before MCP call
  - Verify: No external action taken without `/Approved/` file

---

### 8.5 Documentation & Knowledge

- [ ] T071 Create PHR (Prompt History Record) for tasks generation
  - File: `history/prompts/003-silver-reasoning/003-create-silver-reasoning-tasks.tasks.prompt.md`
  - Record: Task generation process, decisions made, scope

- [ ] T072 Update project README with Silver Tier information
  - File: `README.md` → add "Silver Tier Features" section
  - Overview: Reasoning loops, multi-session persistence, HITL approval
  - Quick link to docs, examples, troubleshooting

---

**Checkpoint**: All phases complete. Silver Tier Reasoning System fully implemented and tested.

---

## Task Dependencies & Execution Order

### Critical Path (Must Complete in Order)

1. Phase 1: Setup (T001-T009) → Phase 2 Prerequisites
2. Phase 2: Foundational (T010-T020) → User Story implementation
3. Phase 3: US1 (T021-T027) → MVP functional
4. Phase 4: US2 (T028-T035) → Multi-session capable
5. Phase 5: US3 (T036-T044) → HITL safety gates
6. Phases 6-8: Can run in parallel or in order

### Parallelizable Tasks (Can Run Simultaneously After Phase 2)

- **T021-T027** (US1): Independent from other stories
- **T028-T035** (US2): Independent from other stories
- **T036-T044** (US3): Independent from other stories
- **T045-T051** (US4): Independent from other stories
- **T052-T059** (US5): Independent from other stories

After Phase 2 (Foundational) is complete, all user stories can be implemented in parallel or in any order.

### Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational: PlanManager, Agent Upgrade)
    ↓
    ├─→ Phase 3 (US1: Plan Creation) ────┐
    ├─→ Phase 4 (US2: Session Resumption) ├─→ Phase 8 (Integration & Polish)
    ├─→ Phase 5 (US3: HITL Approval)  ────┤
    ├─→ Phase 6 (US4: Dashboard)      ────┤
    └─→ Phase 7 (US5: Block Resolution)────┘
```

---

## MVP Scope (Suggested for First Delivery)

**Minimum Viable Product = Phase 1-4**

- ✅ Phase 1: Templates and folder structure
- ✅ Phase 2: PlanManager implementation + Reconciliation-First startup
- ✅ Phase 3: Plan creation for complex tasks
- ✅ Phase 4: Session persistence with checkpoints

**Result**: Agent can create plans for complex tasks and resume across sessions. Core reasoning loop functional.

**Estimate**: 20-30 developer hours

**MVP Tests Passing**:
- T024-T027 (US1): Plan creation and validation
- T032-T034 (US2): Session resumption and checkpoints

**MVP Does NOT Include** (Silver+ features):
- HITL approval gating (Phase 5)
- Dashboard real-time updates (Phase 6)
- Block detection (Phase 7)
- Advanced error handling (Phase 8)

---

## Total Task Summary

| Phase | Tasks | Focus | Dependencies |
|-------|-------|-------|--------------|
| 1: Setup | T001-T009 (9) | Templates, folders, docs | None |
| 2: Foundational | T010-T020 (11) | PlanManager, session startup | Phase 1 ✓ |
| 3: US1 (Plan Creation) | T021-T027 (7) | Detect complex tasks, create plans | Phase 2 ✓ |
| 4: US2 (Session Persistence) | T028-T035 (8) | Checkpoint tracking, resumption | Phase 2 ✓ |
| 5: US3 (HITL Approval) | T036-T044 (9) | Approval routing, MCP gating | Phase 2 ✓ |
| 6: US4 (Dashboard) | T045-T051 (7) | Real-time dashboard updates | Phase 2 ✓ |
| 7: US5 (Block Resolution) | T052-T059 (8) | Block detection, alerts, resume | Phase 2 ✓ |
| 8: Polish | T060-T072 (13) | Error handling, docs, integration | All ✓ |
| **TOTAL** | **72 tasks** | **Full Silver Tier implementation** | **Phased execution** |

---

## Implementation Strategy

### Stage 1: Foundation (Week 1)

Focus: Phase 1 (Setup) + Phase 2 (Foundational)
- Implement PlanManager core
- Agent startup logic
- 15-20 hours

### Stage 2: Core Reasoning (Weeks 2-3)

Focus: Phase 3 (US1 - Plan Creation) + Phase 4 (US2 - Session Persistence)
- Complex task detection
- Plan creation and storage
- Multi-session resumption
- Checkpoint tracking
- 20-25 hours
- **MVP functionality achieved**

### Stage 3: Safety Gates (Week 4)

Focus: Phase 5 (US3 - HITL Approval)
- Approval request drafting
- Approval detection
- MCP execution gating
- 15-20 hours

### Stage 4: Visibility & Resolution (Week 5)

Focus: Phase 6 (Dashboard) + Phase 7 (Block Resolution)
- Dashboard reconciliation
- Block detection and alerts
- Unblock workflows
- 15-20 hours

### Stage 5: Hardening (Week 6)

Focus: Phase 8 (Polish)
- Error handling and recovery
- Full integration tests
- Documentation
- 15-20 hours

**Total Estimated Effort**: 80-100 developer hours across 6 weeks

---

**Tasks Document Status**: ✅ Complete and ready for implementation

