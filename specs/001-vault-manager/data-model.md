# Data Model: Vault Manager — Bronze Tier

**Date**: 2026-02-19 | **Branch**: `001-vault-manager`

## Entities

### Inbox Item

A markdown file deposited in `/Inbox/` by an external watcher.

**Fields**:

| Field | Type | Required | Source |
|-------|------|----------|--------|
| type | string (email, whatsapp, file_drop) | No | YAML frontmatter |
| from | string | No | YAML frontmatter |
| date | string (YYYY-MM-DD) | No | YAML frontmatter |
| subject | string | No | YAML frontmatter |
| body | string | Yes | File content after frontmatter |

**State transitions**:
```
/Inbox/ → [triage] → /Needs_Action/ (if actionable)
/Inbox/ → [triage] → /Done/ (if informational)
/Inbox/ → [triage] → /Pending_Approval/ (if restricted action)
```

**Validation rules**:
- Missing frontmatter: treat as `type: file_drop`
- Missing `type` field: default to `file_drop`
- Unreadable content: log error, skip file

---

### Needs Action Entry

A structured markdown file in `/Needs_Action/` representing an actionable task.

**Fields**:

| Field | Type | Required | Source |
|-------|------|----------|--------|
| source_link | wiki-link `[[Inbox/FILE]]` | Yes | Generated from source filename |
| summary | string (one line) | Yes | Extracted/generated from inbox item |
| priority | tag (#high, #medium, #low) | Yes | Classification engine output |
| date_added | string (@YYYY-MM-DD) | Yes | ISO-8601 date of triage |

**File format**:
```markdown
- [ ] [[Inbox/FILENAME]] | One-line summary | #priority | @YYYY-MM-DD
```

**State transitions**:
```
/Needs_Action/ → [complete] → /Done/
```

---

### Audit Log Entry

A JSON object appended to the daily log file.

**Fields**:

| Field | Type | Required | Values |
|-------|------|----------|--------|
| timestamp | string | Yes | ISO-8601 `YYYY-MM-DDTHH:MM:SSZ` |
| action | string | Yes | triage, complete, move, create, update_dashboard, error |
| source_file | string | Yes | Relative path from vault root, or `"none"` |
| details | string | Yes | Human-readable description with decision rationale |
| result | string | Yes | success, failure, warning, skipped |

**Container**: JSON array in `/Logs/YYYY-MM-DD.json`

---

### Approval Request

A structured markdown file in `/Pending_Approval/`.

**Fields**:

| Field | Type | Required | Source |
|-------|------|----------|--------|
| title | string | Yes | Action description |
| action | string | Yes | What needs to be done |
| context | string | Yes | Source file reference + priority |
| priority | tag (#high, #medium, #low) | Yes | From triage classification |
| decision | checklist (Approve/Deny) | Yes | User fills in |

**File format**:
```markdown
# Approval Required: [Action Title]

**Action:** What needs to be done
**Context:** Why this needs approval
**Priority:** #priority
**Source:** [[Inbox/FILENAME]]

## Decision
- [ ] Approve
- [ ] Deny

**Notes:** (user fills in)
```

---

### Dashboard

The `Dashboard.md` file at vault root.

**Sections**:

| Section | Source | Sort Order |
|---------|--------|------------|
| Pending Actions | /Needs_Action/ files | #high → #medium → #low, then oldest first |
| Recently Completed | /Done/ files (last 10) | Most recent first |
| Stats | File counts per folder (all 4+) | Folder order |
| Alerts | #high items in /Needs_Action/ > 24h old | Oldest first |

**Rebuild trigger**: After every triage, completion, or manual request.

---

### Company Handbook

The `Company_Handbook.md` file at vault root.

**Sections**:

| Section | Purpose |
|---------|---------|
| Communication Rules | Response standards, escalation protocol |
| Priority Definitions | Keyword lists for #high, #medium, #low + VIP contacts |
| Approval Thresholds | What requires approval vs. autonomous |
| Autonomy Boundaries | Bronze Tier CAN/CANNOT lists |

**Read trigger**: Before every triage operation (Constitution Principle III).

## Relationships

```
Inbox Item  →[triage]→  Needs Action Entry  →[complete]→  Done (archive)
Inbox Item  →[triage]→  Done (informational)
Inbox Item  →[triage]→  Approval Request (restricted action)

Every transition produces: Audit Log Entry
Every state change triggers: Dashboard rebuild
```
