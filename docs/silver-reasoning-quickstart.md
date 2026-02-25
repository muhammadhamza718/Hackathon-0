# Silver Tier Reasoning System — Quick Start Guide

**Version**: 1.0
**Last Updated**: 2026-02-25
**Estimated reading time**: 10 minutes

---

## What is the Silver Tier?

The Silver Tier Reasoning System gives the AI Employee the ability to:

1. **Detect** complex, multi-step tasks and create structured Plans.
2. **Persist** plans across sessions (resume where you left off).
3. **Gate** external actions (email, payments, posts) behind human approval.
4. **Track** every decision with timestamped Reasoning Logs and JSON audit trails.

The vault folders involved:

| Folder | Purpose |
|--------|---------|
| `/Plans/` | Active and draft plans |
| `/Done/Plans/` | Archived completed plans |
| `/Pending_Approval/` | Actions awaiting human review |
| `/Approved/` | Approved actions ready to execute |
| `/Rejected/` | Rejected actions (audit trail) |
| `/Done/Actions/` | Successfully executed actions |
| `/Logs/` | JSON audit logs (one file per day) |
| `/Archive/` | Duplicate/corrupted plan archive |

---

## Example 1: Invoice Workflow (Full Loop)

**Scenario**: "Generate and send an invoice to Client A for $1,500."

### Step 1 — Request received

The user submits the task. The agent detects complexity keywords (`invoice`, `send`, `client`) and creates a plan.

```
Plan created: PLAN-2026-001.md
Objective: Generate and send invoice to Client A for $1,500
Steps:
  - [ ] Calculate invoice total and add tax
  - [ ] Generate invoice PDF
  - [ ] Log invoice in accounts ledger
  - [ ] ✋ Send invoice email to client@example.com
```

### Step 2 — Autonomous steps execute

The agent completes steps 1–3 without human involvement:

```
[2026-02-25T10:01:00Z] Agent: Calculated total — $1,500 + $150 tax = $1,650
[2026-02-25T10:01:05Z] Agent: Generated PDF — /Files/invoice-2026-001.pdf
[2026-02-25T10:01:10Z] Agent: Logged invoice in ledger — row 47
```

### Step 3 — HITL gate reached

Step 4 has ✋. The agent:
1. Drafts an approval request to `/Pending_Approval/2026-02-25T10-01-15Z_email_client-a.md`
2. **Halts** — does NOT send the email.
3. Marks the plan `Blocked: Awaiting Human Approval`.

### Step 4 — Human reviews

You open the Obsidian vault and find the file in `/Pending_Approval/`.
The file contains the full email draft, recipient, and rationale.

**To approve**: Drag/move the file to `/Approved/`.
**To reject**: Drag/move the file to `/Rejected/`.

### Step 5 — Agent resumes

On the next agent session, `DetectApproval` finds the file in `/Approved/`.

```
[2026-02-25T14:30:00Z] Agent: Detected approval — executing email via MCP
[2026-02-25T14:30:03Z] Agent: Email sent successfully — message_id=abc123
[2026-02-25T14:30:03Z] Agent: Plan complete — archiving to /Done/Plans/
```

Dashboard is updated. Audit log entry written to `/Logs/2026-02-25.json`.

---

## Example 2: Multi-Session Project (Interrupted & Resumed)

**Scenario**: Complex client project with 6 steps, interrupted mid-way.

### Session 1

- Agent creates plan `PLAN-2026-005.md` with 6 steps.
- Completes steps 1 and 2 (research, drafting).
- Session ends (user closes Claude).

### Session 2

- Agent starts with Reconciliation-First startup.
- Scans `/Plans/`, finds `PLAN-2026-005.md` with status `Active`.
- Reads last Reasoning Log: step 2 was last completed.
- Announces: `"Resuming plan PLAN-2026-005: Client Project. Last checkpoint: Step 2."`
- Proceeds from step 3.

### Session 3 (approval pending)

- Steps 3–4 completed. Step 5 has ✋ — approval drafted, session ends.
- Plan status: `Blocked: Awaiting Human Approval`.

### Session 4 (approval detected)

- Human approved between sessions.
- Agent detects `/Approved/` file, executes MCP action, completes step 5.
- Continues to step 6, completes final step.
- Archives plan to `/Done/Plans/PLAN-2026-005.md`.

---

## Example 3: Safety Breach Prevention

**Scenario**: A badly-configured agent tries to send an email without creating an approval file.

```python
# This is BLOCKED by the safety gate
approval_mgr.execute_approved_action(
    filename="some-file.md",
    mcp_dispatcher=email_dispatcher,
)
# Raises: FileNotFoundError — file not in /Approved/
```

The Silver Tier safety gate enforces:

1. **No file in `/Approved/`** → execution blocked.
2. **HITL step without approval proof** → `PermissionError` raised.
3. **MCP dispatcher receives no request** → no external state change.

The vault remains the single source of truth. No external action can occur without a human-approved file.

---

## Python API Reference (Quick Cheat-Sheet)

```python
from pathlib import Path
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager
from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager
from agents.skills.managing_obsidian_vault.audit_logger import AuditLogger

vault = Path("/path/to/vault")
plan_mgr = PlanManager(vault_root=vault)
approval_mgr = ApprovalManager(vault_root=vault)
audit = AuditLogger(vault_root=vault)

# Create a plan
plan_path = plan_mgr.create_plan(
    task_id="2026-001",
    objective="Generate and send invoice to Client A",
    context="Client A ordered 10 units at $150 each.",
    steps=[
        "Calculate invoice total",
        "Generate PDF",
        "Log in ledger",
        "✋ Send email to client@example.com",
    ],
    priority="high",
)

# Resume active plan on session start
active_plan = plan_mgr.find_active_plan()
if active_plan:
    print(f"Resuming: {active_plan.metadata.task_id}")

# Draft an approval request (before reaching HITL step)
approval_file = approval_mgr.draft_external_action(
    action_type="email",
    target_recipient="client@example.com",
    plan_id="2026-001",
    step_id=4,
    draft_content="Dear Client A, please find attached your invoice...",
    rationale="Step 4 of PLAN-2026-001 requires sending invoice email",
    step_description="Send invoice email to Client A for $1,650",  # T064 traceability
)

# Execute after human approves (file moved to /Approved/)
success, msg = approval_mgr.execute_approved_action(
    filename=approval_file.name,
    mcp_dispatcher=my_mcp_dispatcher,
)

# Archive completed plan
plan_mgr.archive_plan("2026-001")
audit.plan_archived("2026-001")
```

---

## Dashboard Quick Reference

The Dashboard (`Dashboard.md`) shows:

- **Current Mission**: Active plan ID, objective, next step
- **Blocked Plans**: Plans awaiting human approval (with age alert if > 24h)
- **Completed Today**: Plans archived in the last 24 hours

The Dashboard is rebuilt from vault state on every session start via `DashboardReconciler.reconcile()`.

---

## Troubleshooting

See `docs/silver-reasoning-troubleshooting.md` for detailed recovery procedures covering:
- Corrupted plans
- MCP failures
- Forgotten approvals
- Duplicate plans
- Dashboard sync issues
