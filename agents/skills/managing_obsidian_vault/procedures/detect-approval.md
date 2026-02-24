# Procedure: DetectApproval

**Tier**: Silver
**Trigger**: After drafting external action, at session startup, or on-demand check
**Related**: T038

---

## Purpose

Scan the vault's approval folders to determine the current state of a pending
external action. Returns a status that the agent uses to unblock or remain blocked.

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | string | Yes | Approval file name (e.g. `2026-02-24T10-00-00Z_email_foo.md`) |
| `plan_id` | string | Optional | If provided, filters scan results to this plan only |

---

## Process

```
DetectApproval(filename):
  1. Check /Approved/<filename>
     → If exists: return status=APPROVED
  2. Check /Rejected/<filename>
     → If exists: return status=REJECTED
  3. Check /Done/Actions/<filename>
     → If exists: return status=EXECUTED
  4. Check /Pending_Approval/<filename>
     → If exists: return status=PENDING
  5. File not found in any folder
     → Raise FileNotFoundError
     → Log warning: approval file missing
     → Alert user to check vault manually
```

---

## Outputs

| Status | Meaning | Agent Action |
|--------|---------|-------------|
| `APPROVED` | Human moved file to /Approved/ | Call `ExecuteApprovedAction` |
| `REJECTED` | Human moved file to /Rejected/ | Log rejection, update Reasoning Logs, wait for next steps |
| `EXECUTED` | Action was completed, archived | No action needed |
| `PENDING` | File still in /Pending_Approval/ | Plan remains Blocked; display waiting message |

---

## Python Implementation

```python
from agents.skills.managing_obsidian_vault.approval_manager import ApprovalManager

manager = ApprovalManager(vault_root=Path("/vault"))
status = manager.detect_approval_status(filename="2026-02-24T10-00-00Z_email_foo.md")
```

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|-----------|
| `FileNotFoundError` | File absent from all folders | Alert user; manual vault inspection required |
| `ValueError` | Malformed YAML in approval file | Log error; skip file; alert user |

---

## Notes

- This procedure does NOT move files. File movement is done by the human in Obsidian.
- The agent polls this procedure at each session startup (Reconciliation-First).
- If plan has multiple pending approvals, scan `/Pending_Approval/` filtered by `plan_id`.
