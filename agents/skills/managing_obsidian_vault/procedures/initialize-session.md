# Initialize Session (Silver Tier)

**Procedure**: Reconciliation-First startup logic for agent session initialization.

**Purpose**: On every new session, scan the vault for incomplete plans and resume work from the exact checkpoint (last reasoning log entry). Enables multi-session task persistence.

**Prerequisite**: PlanManager module (plan-manager.py) with `find_active_plan()` function implemented.

---

## Pseudocode

```
SESSION_START:
  1. Call PlanManager.find_active_plan()
     - Scans /Plans/ directory
     - Prioritizes by Status (Active > Blocked > Draft)
     - Sorts by created_date descending (most recent first)
     - Returns most relevant incomplete plan or null

  2. IF plan found:
     a. Log: "Resuming plan [ID]: [Objective]"
     b. Display to user: "[Plan Status Dashboard]"
        - Plan ID and objective
        - Completed/remaining steps
        - Last checkpoint timestamp (from latest reasoning log)
     c. Load last reasoning log entry to determine checkpoint
     d. Identify next uncompleted step
     e. Resume execution from next uncompleted step
     f. Continue to user input acceptance

  3. ELSE (no plan found):
     a. Log: "No active plans found"
     b. Begin normal triage flow
     c. Accept user input
```

---

## Checkpoint Detection Algorithm

After loading the active plan, determine the exact checkpoint where agent should resume:

```
FIND_CHECKPOINT(plan):
  last_reasoning_log = plan.reasoning_logs[-1] if reasoning_logs exists
  extract_timestamp(last_reasoning_log) → CHECKPOINT_TIME

  next_incomplete_step = find first step where:
    - completed == false
    - NOT hitl_required (HITL steps don't auto-resume)

  RETURN {
    checkpoint_time: CHECKPOINT_TIME,
    next_step: next_incomplete_step.number,
    step_description: next_incomplete_step.description,
    plan_status: plan.status
  }
```

---

## Dashboard Display Format

When plan found, display to user before accepting input:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ RESUMING ACTIVE PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plan ID:    PLAN-2026-001
Objective:  Generate and send invoice to Client A
Status:     Active
Priority:   high

Last Checkpoint: 2026-02-21T10:40:00Z
Next Step:  4 (Send email with invoice)

Progress:   3/5 steps complete
Blocked:    No

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## State Transitions

```
Session Load → Find Active Plan
             ├─ Plan Found
             │  ├─ Status: Draft → Resume (user approval may be needed)
             │  ├─ Status: Active → Resume immediately
             │  ├─ Status: Blocked → Display block reason, wait for approval
             │  └─ Status: Done → Display completion summary (shouldn't occur in /Plans/)
             │
             └─ No Plan → Normal triage flow
```

---

## Error Handling

| Error | Recovery |
|-------|----------|
| `/Plans/` directory missing | Create it; proceed to normal triage |
| Plan file corrupted (invalid YAML) | Log error; skip plan; proceed to normal triage |
| Multiple plans with same priority | Sort by created_date; select most recent |
| No write permissions to vault | Log error; display warning; continue read-only |

---

## Agent Instruction Integration

This procedure MUST be called at the very start of each session, BEFORE accepting any user input:

```
## Session Start (EVERY SESSION - MANDATORY)

You MUST execute the following procedure before accepting the first user input:

1. Import PlanManager
2. Call PlanManager.find_active_plan()
3. If plan found:
   - Display checkpoint information to user
   - Resume execution from next incomplete step
   - Log session resumption with timestamp
4. If no plan found:
   - Proceed to normal task reception and triage

**Rationale**: Enables multi-session task persistence. Plans survive across agent restarts.
```

---

## Audit Trail

All session initializations MUST be logged:

```
- [2026-02-21T11:00:00Z] Agent: Session initialized — Scanned /Plans/ for active plans.
- [2026-02-21T11:00:05Z] Agent: Detected active plan — PLAN-2026-001 (Status: Active). Resuming from step 4.
```

Or if no plan:

```
- [2026-02-21T11:00:00Z] Agent: Session initialized — No active plans found. Beginning triage flow.
```
