# 🧠 Silver Tier Agent Dashboard

**Last Updated**: `{{ISO_TIMESTAMP}}`
**Vault**: Silver Tier Reasoning System
**Agent**: obsidian-vault-agent

---

## ⚡ Current Missions

> This section is **auto-generated** by `ReconcileDashboard`. Do not edit manually.

### {{PLAN_ID}} — {{OBJECTIVE}}

| Field | Value |
|-------|-------|
| **Status** | 🟢 Active |
| **Priority** | High |
| **Progress** | [████░░░░░░] 40% |
| **Current Step** | {{CURRENT_STEP_DESCRIPTION}} |
| **Pending Approvals** | ⏸ 1 action(s) awaiting review in `/Pending_Approval/` |

---

## 📊 Plan Statistics

| Metric | Value |
|--------|-------|
| 🟢 Active Plans | {{ACTIVE_COUNT}} |
| 🔴 Blocked Plans | {{BLOCKED_COUNT}} |
| ⚪ Draft Plans | {{DRAFT_COUNT}} |
| ✅ Completed Plans | {{DONE_COUNT}} |
| 📈 Step Completion | {{DONE_STEPS}}/{{TOTAL_STEPS}} ({{PCT}}%) |

---

## 🚨 Alerts

> Plans that have been **Blocked for more than 24 hours** appear here.

- 🔴 **{{PLAN_ID}}** blocked for {{HOURS}}h — '{{OBJECTIVE_TRUNCATED}}' requires human action.

_If no alerts: "No active alerts."_

---

## 🕐 Recent Activity

> Last 10 agent actions across all active plans, newest first.

- [{{ISO_TIMESTAMP}}] Agent: {{ACTION}} — {{RATIONALE}}
- [{{ISO_TIMESTAMP}}] Agent: {{ACTION}} — {{RATIONALE}}
- ...

_If no activity: "No activity recorded yet."_

---

## Schema Notes

### How to Read This Dashboard

| Section | Source | Auto-Updated? |
|---------|--------|--------------|
| ⚡ Current Missions | `/Plans/PLAN-*.md` frontmatter + Roadmap | ✅ Yes |
| 📊 Plan Statistics | Scan `/Plans/` and `/Done/Plans/` | ✅ Yes |
| 🚨 Alerts | Blocked plans with `created_date` > 24h ago | ✅ Yes |
| 🕐 Recent Activity | Reasoning Logs from all active plans | ✅ Yes |

### Status Badges

| Badge | Meaning |
|-------|---------|
| 🟢 Active | Plan in progress; agent executing steps |
| 🔴 Blocked: Awaiting Human Approval | ✋ step reached; approval file in `/Pending_Approval/` |
| ⚪ Draft | Plan created but not started |
| ✅ Done | Plan archived to `/Done/Plans/` |

### Trigger Events

`ReconcileDashboard` is called automatically after:
- `InitializePlan` — new plan created
- `UpdatePlanStep` — step marked complete
- `DraftExternalAction` — approval request filed
- `ExecuteApprovedAction` — external action executed
- `ArchivePlan` — plan moved to Done

### Customisation

To add vault-specific sections (e.g., project names, client lists), edit
`Dashboard.md` **below** the `## 🕐 Recent Activity` section. The agent
preserves all content after that marker during reconciliation.
