# Silver Tier Reasoning System — Troubleshooting Guide

**Version**: 1.0
**Last Updated**: 2026-02-25
**Relates To**: `specs/003-silver-reasoning/spec.md`

---

## Overview

This guide covers the most common failure scenarios in the Silver Tier Reasoning System and provides step-by-step recovery procedures.  Use this document when something appears stuck, missing, or inconsistent in the Obsidian vault.

---

## Scenario 1: Corrupted Plan.md

### Symptoms

- Agent reports "Cannot parse plan" or "Missing YAML frontmatter"
- `find_active_plan()` skips a file with a warning log
- A plan file exists in `/Plans/` but the Dashboard shows no active mission

### Cause

- File was partially written (power loss, disk full)
- YAML frontmatter was manually edited and broke indentation
- Encoding issue (BOM, null bytes)

### Recovery

1. **Check the quarantine folder** — the agent automatically moves corrupted files to `/Archive/Corrupted/`.
2. Open the quarantined file and inspect the raw content.
3. Fix the YAML frontmatter manually:
   ```yaml
   ---
   task_id: 2026-001
   source_link: "null"
   created_date: 2026-02-25T10:00:00Z
   priority: medium
   status: Active
   blocked_reason: null
   ---
   ```
4. Copy the repaired file back to `/Plans/PLAN-<task_id>.md`.
5. Run the agent — it will load the repaired plan on next Reconciliation-First startup.

### Prevention

- Never edit Plan.md files directly unless you know the schema.
- Use the `PlanManager` API programmatically for all writes.

---

## Scenario 2: MCP Server Failure

### Symptoms

- Approval file was in `/Approved/` but disappeared; it is now back in `/Pending_Approval/`
- Agent log shows: `"MCP timeout"` / `"MCP offline"` / `"MCP auth failure"`
- Plan status stuck at `Blocked: Awaiting Human Approval`

### Cause

- MCP server was unreachable (network issue, server restart)
- Authentication token expired
- MCP request timed out (large payload)

### Recovery

1. **Check `/Pending_Approval/`** — the file is returned here with an `execution_result` field describing the failure.
2. Open the file and read the `execution_result` YAML field.
3. Resolve the underlying issue:
   - **Timeout**: Reduce payload size or increase server timeout config.
   - **Offline**: Wait for MCP server to come back online; verify with health-check endpoint.
   - **Auth failure**: Refresh the API token in your `.env` file and restart the agent.
4. Once resolved, move the file back to `/Approved/` to retry execution.

### Prevention

- Monitor MCP server health in your infrastructure dashboard.
- Set reasonable timeouts in your MCP dispatcher configuration.

---

## Scenario 3: Forgotten Approval (Plan Blocked for > 24 Hours)

### Symptoms

- Dashboard shows a `⚠️ BLOCKED > 24h` alert in the "Blocked Plans" section
- Approval file has been in `/Pending_Approval/` for more than 24 hours
- No action taken by human

### Cause

- Human reviewer forgot to action the approval request
- Approval email/notification was missed

### Recovery

1. Open `/Pending_Approval/` in the Obsidian vault.
2. Review the pending approval file(s).
3. Decide: **Approve** or **Reject**.
   - **Approve**: Move file to `/Approved/` — agent will detect and execute on next run.
   - **Reject**: Move file to `/Rejected/` — agent will log rejection and wait for guidance.
4. The 24-hour alert will clear after the file is no longer in `/Pending_Approval/`.

### Prevention

- Set up a notification system (email or Slack) when files appear in `/Pending_Approval/`.
- Review the Dashboard daily as part of your morning routine.

---

## Scenario 4: Duplicate Plans

### Symptoms

- Two plan files exist for the same task: e.g., `PLAN-2026-001.md` and `PLAN-2026-002.md` with identical `source_link`
- Agent is confused about which plan is "active"

### Cause

- Plan creation was triggered twice (e.g., user submitted request twice)
- Session restart created a new plan before reconciling the existing one

### Recovery

1. **Identify the primary plan** — usually the earlier one (lower ID) or the one with more completed steps.
2. Call `PlanManager.consolidate_duplicate_plans(primary_id, duplicate_id)`:
   ```python
   mgr = PlanManager(vault_root=Path("/vault"))
   mgr.consolidate_duplicate_plans("2026-001", "2026-002")
   ```
3. The duplicate is moved to `/Archive/` and its unique steps are merged into the primary.
4. Review the merged plan to ensure steps are in the correct order.

### Prevention

- On session start, always run `find_active_plan()` before creating a new plan.
- Use `detect_duplicate_plan(task_id, source_link)` before calling `create_plan()`.

---

## Scenario 5: Dashboard Out of Sync

### Symptoms

- Dashboard shows old/incorrect plan status
- Completed plans still show as "Active"
- "Current Mission" section is blank despite active plans

### Cause

- Agent crashed before updating the Dashboard
- Manual edits to plan files without running `DashboardReconciler`

### Recovery

1. Run the reconciler manually:
   ```python
   from agents.skills.managing_obsidian_vault.dashboard_reconciler import DashboardReconciler
   reconciler = DashboardReconciler(vault_root=Path("/vault"))
   reconciler.reconcile()
   ```
2. The Dashboard will be rebuilt from the current state of all plan files.

### Prevention

- The agent runs reconciliation on every session start (Reconciliation-First).
- Avoid editing plan files or the Dashboard directly.

---

## Scenario 6: HITL Step Blocked Without Approval File

### Symptoms

- `PermissionError: Cannot mark HITL step N complete`
- Plan step is `✋`-marked but no file exists in `/Pending_Approval/` or `/Approved/`

### Cause

- Approval file was accidentally deleted
- Agent state became inconsistent (file moved to wrong folder)

### Recovery

1. Check all approval folders: `/Pending_Approval/`, `/Approved/`, `/Rejected/`, `/Done/Actions/`
2. If file is in `/Done/Actions/`: The action was already executed — mark the step complete manually in the plan file.
3. If file is missing entirely: Re-draft the approval:
   ```python
   approval_mgr.draft_external_action(
       action_type="email",
       target_recipient="client@example.com",
       plan_id="2026-001",
       step_id=4,
       draft_content="...",
       rationale="...",
       step_description="Send invoice email to Client A",
   )
   ```
4. Move the new file to `/Approved/` if action should proceed.

---

## Audit Log Reference

All events are recorded in `/Logs/YYYY-MM-DD.json` (NDJSON format).

```bash
# View today's audit log
cat Logs/$(date +%Y-%m-%d).json | python -m json.tool

# Find all failures
grep '"result": "failure"' Logs/2026-02-25.json

# Find all events for a specific plan
grep '"plan_id": "2026-001"' Logs/2026-02-25.json
```

---

## Getting Help

- **Specification**: `specs/003-silver-reasoning/spec.md`
- **Architecture Plan**: `specs/003-silver-reasoning/plan.md`
- **Quick Start**: `docs/silver-reasoning-quickstart.md`
- **Agent Instructions**: `agents/silver-reasoning-agent.md`
- **Constitution**: `.specify/memory/constitution.md`
