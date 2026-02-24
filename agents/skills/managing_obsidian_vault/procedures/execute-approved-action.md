# Procedure: ExecuteApprovedAction

**Tier**: Silver
**Trigger**: DetectApproval returns status=APPROVED
**Related**: T039

---

## Purpose

Re-read the approval file from `/Approved/`, confirm its contents, call the
appropriate MCP server, archive the file to `/Done/Actions/`, and update the
plan's Reasoning Logs with the execution result.

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | string | Yes | Approval file name in `/Approved/` |
| `plan_id` | string | Yes | Parent plan identifier (for log update) |
| `step_id` | integer | Yes | Step number being completed |

---

## Process

```
ExecuteApprovedAction(filename, plan_id, step_id):
  1. Read file from /Approved/<filename>
     → Validate YAML frontmatter (action_type, target_recipient, etc.)
     → Confirm status field shows "pending" or "approved"
  2. Route to MCP server based on action_type:
     - email       → call email-mcp (send_email)
     - payment     → call payment-mcp (execute_payment)
     - social_post → call social-mcp (publish_post)
     - api_call    → call generic-mcp (http_request)
     - other       → log for manual execution, mark as dry-run
  3. On MCP success:
     a. Update file status to "executed", add execution_result
     b. Move file to /Done/Actions/<filename>
     c. Delete source from /Approved/
     d. Call UpdatePlanStep(plan_id, step_id, completed=True)
     e. Call LogReasoning(plan_id, action="Executed external action", rationale=result)
     f. Update plan status back to "Active" if was "Blocked"
  4. On MCP failure:
     a. Log error with full exception details
     b. Annotate file with failure reason
     c. Move file BACK to /Pending_Approval/<filename>
     d. Call LogReasoning(plan_id, "External action failed", rationale=error_msg)
     e. Plan status remains "Blocked"
```

---

## Outputs

| Result | Outcome |
|--------|---------|
| `success=True` | Action executed; file in /Done/Actions/; plan step marked [x] |
| `success=False` | MCP failed; file returned to /Pending_Approval/; plan blocked |

---

## Python Implementation

```python
from pathlib import Path
from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager

vault = Path("/vault")
approval_mgr = ApprovalManager(vault_root=vault)
plan_mgr = PlanManager(vault_root=vault)

filename = "2026-02-24T10-00-00Z_email_client-a.md"

success, result_msg = approval_mgr.execute_approved_action(
    filename=filename,
    mcp_dispatcher=my_mcp_dispatcher,  # callable(ApprovalRequest) -> str
)

if success:
    plan_mgr.update_step(
        plan_id="PLAN-2026-001",
        step_number=4,
        completed=True,
        log_entry=f"Executed external action — {result_msg}",
    )
else:
    plan_mgr.append_reasoning_log(
        plan_id="PLAN-2026-001",
        action="External action failed",
        rationale=result_msg,
    )
```

---

## MCP Server Mapping

| action_type | MCP Tool | Parameters |
|-------------|----------|-----------|
| `email` | `email-mcp::send_email` | to, subject, body |
| `payment` | `payment-mcp::execute_payment` | recipient, amount, currency |
| `social_post` | `social-mcp::publish_post` | platform, content |
| `api_call` | `generic-mcp::http_request` | method, url, payload |
| `other` | Manual / Dry-run | Log for human execution |

---

## Safety Guarantees

- Files are NEVER deleted; they are moved to audit trail folders.
- All writes use atomic temp-file-and-rename (no partial writes).
- On failure, the approval file is returned to `/Pending_Approval/` so the human
  can re-review and re-approve after fixing the underlying issue.
- HITL steps are only marked complete after `validate_hitl_step_has_approval()` passes.
