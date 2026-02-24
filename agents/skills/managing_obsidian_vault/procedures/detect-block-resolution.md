# Procedure: DetectBlockResolution

**Tier**: Silver
**Trigger**: After `ExecuteApprovedAction` completes, or when agent detects file in `/Approved/`
**Related**: T055

---

## Purpose

When a human moves an approval file to `/Approved/`, this procedure detects
the resolution, updates plan status from `Blocked` → `Active`, appends a
Reasoning Log entry, and returns the next step for immediate execution.

---

## Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approval_filename` | string | Yes | Filename in `/Approved/` (e.g. `2026-02-24T10-00-00Z_email_foo.md`) |

---

## Process

```
DetectBlockResolution(approval_filename):
  1. Read file from /Approved/<approval_filename>
     → Validate YAML frontmatter (plan_id, step_id)
  2. Call BlockManager.resolve_block(approval_filename)
     → Internally: re-runs detect_blocks() on the plan
     → If no more pending approvals: plan status → "Active"
     → blocked_reason cleared
  3. Call LogReasoning:
     → "Approval received for step [N] — resuming plan [plan_id]"
  4. Call ReconcileDashboard:
     → Dashboard reflects Active status immediately
  5. Return next_step_description to agent
  6. Agent resumes execution at next incomplete step
     (or announces "Plan complete" if all steps done)
```

---

## Outputs

| Result | Outcome |
|--------|---------|
| `next_step` returned | Plan unblocked; agent continues at returned step |
| `None` returned | More approvals still pending; plan remains Blocked |
| `"All steps complete"` | Plan is done; call ArchivePlan |

---

## Python Implementation

```python
from pathlib import Path
from agents.skills.managing_obsidian_vault.block_manager import BlockManager
from agents.skills.managing_obsidian_vault.dashboard_reconciler import DashboardReconciler

vault = Path("/vault")
block_mgr = BlockManager(vault_root=vault)
reconciler = DashboardReconciler(vault_root=vault)

filename = "2026-02-24T10-00-00Z_email_client.md"

next_step = block_mgr.resolve_block(filename)

if next_step:
    print(f"Block resolved! Resuming plan. Next step: {next_step}")
    reconciler.reconcile()
else:
    print("Plan still has pending approvals. Remaining blocked.")
```

---

## Integration with Session Startup

During Reconciliation-First startup:

```
Session Start:
  1. Call find_active_plan()
  2. Scan /Approved/ for any unprocessed approval files
  3. For each: call DetectBlockResolution
  4. After resolution loop: load plan, proceed from next step
```

This ensures that even if the agent was offline when the human approved,
the plan resumes correctly on next session start.

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|-----------|
| `FileNotFoundError` | Approval file not in `/Approved/` | Check if file was moved elsewhere |
| `ValueError` | Malformed YAML in approval file | Log error; alert user to manual fix |
| Plan not found | plan_id in approval file invalid | Log warning; skip resolution |
