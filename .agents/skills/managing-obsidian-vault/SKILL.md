---
name: managing-obsidian-vault
description: Step-by-step procedures for managing an Obsidian Vault used by a Digital FTE (Personal AI Employee). Covers vault initialization, inbox triage, dashboard updates, task completion lifecycle, audit logging, and approval routing. Use when the user mentions vault, inbox, triage, dashboard, needs action, obsidian, FTE, AI employee, or when working with .md files in /Inbox/, /Needs_Action/, /Done/, /Pending_Approval/, or /Logs/ folders. Bronze Tier only — no external APIs, no autonomous loops.
---

# Managing Obsidian Vault

Procedural knowledge for operating an Obsidian Vault as a Digital FTE's source of truth. This is the "training manual" — follow these procedures for all vault operations.

## Prerequisites

Before any operation, verify the vault root path. All paths below are relative to the vault root.

## 1. Vault Initialization

Create the full folder structure, core files, and verify health.

1. Create Bronze Tier folders using `Bash(mkdir -p)` for idempotent creation: `/Inbox`, `/Needs_Action`, `/Done`, `/Pending_Approval`, `/Logs`
2. Create `Dashboard.md` from template — see [references/dashboard-template.md](references/dashboard-template.md)
3. Create `Company_Handbook.md` from template — see [references/handbook-template.md](references/handbook-template.md)
4. Run health check: verify all 5 folders exist + both core files are present and non-empty (7 items total)

**On failure:** Log error, report which items are missing, and offer to create them.

## 2. Inbox Triage

Process every file in `/Inbox/` using classification and priority assessment.

**Always read `Company_Handbook.md` FIRST** for current priority definitions before triaging.

**For each file in `/Inbox/`:**

1. **Read** the file contents
2. **Check frontmatter** for `type:` field (email, whatsapp, file_drop)
   - No frontmatter? Treat as `file_drop`, log warning, continue processing
   - Malformed file? Log error with filename, skip to next file
3. **Assess priority** using keyword matching — see [references/triage-rules.md](references/triage-rules.md)
4. **Classify** as actionable or informational
5. **If actionable:** Create entry in `/Needs_Action/` with format:
   ```
   - [ ] [[Inbox/FILENAME]] | One-line summary | #priority | @YYYY-MM-DD
   ```
6. **If informational:** Move file to `/Done/`
7. **Update Dashboard** (see procedure 3)
8. **Write audit log** entry with action: `triage`

**Empty inbox:** Log "no items to triage", update Dashboard stats, done.

## 3. Dashboard Update

Rebuild `Dashboard.md` from actual vault state. **Never use cached values.**

1. **Count files** in each Bronze Tier folder (Inbox, Needs_Action, Done, Pending_Approval, Logs) by reading directory contents
2. **Build sections:**
   - Pending Actions — list all items from `/Needs_Action/`
   - Recently Completed — last 10 items from `/Done/` by date
   - Stats — actual file counts per folder
   - Alerts — any `#high` items older than 24 hours
3. **Write** using ISO-8601 timestamps (`YYYY-MM-DDTHH:MM:SSZ`)
4. **Log** action: `update_dashboard`

Full template: [references/dashboard-template.md](references/dashboard-template.md)

## 4. Task Completion

When a task is marked `[x]` or user says a task is done:

1. **Move** source file from `/Inbox/` → `/Done/`
2. **Remove** the task entry from `/Needs_Action/`
3. **Remove** the task from Dashboard "Pending Actions"
4. **Add** to Dashboard "Recently Completed" (prepend, keep max 10)
5. **Recalculate** all Dashboard stats from actual folder counts
6. **Write audit log** entry with action: `complete`

## 5. Audit Logging

**Never skip logging, even on errors.** One file per day.

- **File:** `/Logs/YYYY-MM-DD.json` (JSON array, append to existing)
- **Entry format:** `{"timestamp", "action", "source_file", "details", "result"}`
- **Valid actions:** `triage`, `complete`, `move`, `create`, `update_dashboard`, `error`

**Read-parse-append-write pattern:**
1. Compute filename: `/Logs/YYYY-MM-DD.json`
2. If file doesn't exist, create with `[]`
3. Read and parse existing JSON array
4. Append new entry object
5. Write full array back with 2-space indentation

**Malformed JSON recovery:** If JSON parse fails, rename to `.bak`, create fresh `[]`, log the error as first entry, report to user.

Full schema and examples: [references/log-format.md](references/log-format.md)

## 6. Approval Routing

For actions beyond Bronze Tier autonomy boundaries:

1. **Check** `Company_Handbook.md` autonomy rules
2. **If restricted:** Create file in `/Pending_Approval/` with:
   - Action needed (what and why)
   - Context (source file, priority)
   - Yes/No prompt for the user
3. **Do NOT proceed** with the action until approved
4. **Log** the routing with action: `create`

**Bronze Tier restrictions:** Cannot send emails, make payments, post to social media, delete files permanently, or contact external parties.

See [references/handbook-template.md](references/handbook-template.md) for full autonomy boundaries.

## Vault Structure

Complete folder and file schema: [references/vault-structure.md](references/vault-structure.md)

## Error Handling

- Always log errors before reporting them
- Never silently skip files — warn and continue
- If vault health check fails mid-operation, stop and report
- Malformed JSON in log files: back up the file, create fresh log, report to user
