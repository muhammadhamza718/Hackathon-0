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
4. Run health check:
   - Verify 5 folders exist: `/Inbox`, `/Needs_Action`, `/Done`, `/Pending_Approval`, `/Logs`
   - Verify `Dashboard.md` exists and is non-empty
   - Verify `Company_Handbook.md` exists and is non-empty
   - Report: "7 items verified" (5 folders + 2 core files)
   - If any items missing, list them explicitly
5. Write audit log entry with action: `create` and details listing all items created

**Idempotency:** If a file or folder already exists, do NOT overwrite. Only create missing items. If all 7 items are present, report "vault healthy — 7 items verified" with no modifications.

**On failure:** Log error, report which items are missing, and offer to create them.

## 2. Inbox Triage

Process every file in `/Inbox/` using classification and priority assessment.

**Always read `Company_Handbook.md` FIRST** for current priority definitions before triaging. Extract VIP contacts, blocked senders, and any custom keyword overrides. If handbook is missing or empty, fall back to defaults in [references/triage-rules.md](references/triage-rules.md).

**For each file in `/Inbox/`:**

1. **Read** the file contents
2. **Check frontmatter** for `type:` field (email, whatsapp, file_drop)
   - No frontmatter? Treat as `file_drop`, log warning, continue processing
   - Malformed file? Log error with filename, skip to next file
3. **Assess priority** using keyword matching — see [references/triage-rules.md](references/triage-rules.md)
4. **Classify** as actionable or informational
5. **Check for restricted actions:** Scan body for restricted action keywords (see Section 6). If found, route to `/Pending_Approval/` instead of `/Needs_Action/` — follow Approval Routing procedure
6. **If actionable (no restricted actions):** Create entry in `/Needs_Action/` with format:
   ```
   - [ ] [[Inbox/FILENAME]] | One-line summary | #priority | @YYYY-MM-DD
   ```
7. **If informational:** Move file to `/Done/`
8. **Update Dashboard** (see procedure 3)
9. **Write audit log** entry with action: `triage`

**Empty inbox:** If `/Inbox/` is empty, log with action: `triage`, result: `skipped`, details: "Inbox empty. No items to triage." Update Dashboard stats. Done — do not proceed further.

## 3. Dashboard Update

Rebuild `Dashboard.md` from actual vault state. **ALWAYS count actual files via Glob. NEVER reuse counts from a previous operation. Dashboard MUST reflect reality.**

1. **Glob each folder** for file counts: Inbox, Needs_Action, Done, Pending_Approval, Logs
2. **Read `/Needs_Action/`** for pending items — sort `#high` first, then `#medium`, then `#low`; within same priority, oldest first
3. **Read `/Done/`** for last 10 completed items by date (most recent first)
4. **Compute alerts:** For each `#high` item in `/Needs_Action/`, check `@date`. If date is > 24 hours old, add to Alerts section with age in hours
5. **Write `Dashboard.md`** from template with ISO-8601 timestamps (`YYYY-MM-DDTHH:MM:SSZ`)
6. **Log** action: `update_dashboard` with stats summary in details

Full template: [references/dashboard-template.md](references/dashboard-template.md)

## 4. Task Completion

When user says a task is done (e.g., "I finished [task]"):

**Identify the task:**
1. Match user's description against `/Needs_Action/` entries by filename or summary text
2. If ambiguous (multiple matches), list all matches and ask user to choose
3. If no match found in `/Needs_Action/`, report to user — do not proceed

**Complete the task:**
1. **Move** source file from `/Inbox/` → `/Done/` (if source already in `/Done/`, skip move but continue)
2. **Remove** the task entry from `/Needs_Action/`
3. **Update Dashboard** — rebuild via procedure 3 (never manual edit)
4. **Write audit log** entry with action: `complete`, details including source_file and completion rationale

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

**Restricted action keywords** (case-insensitive scan of file body):
`send email`, `send message`, `payment`, `transfer`, `post to`, `delete permanently`, `contact`, `call`, `invoice payment`, `wire`, `publish`

1. **Check** `Company_Handbook.md` autonomy rules
2. **Scan** file body for restricted action keywords
3. **If restricted action detected:** Create structured approval file in `/Pending_Approval/` with:
   - Action needed (what and why)
   - Context (source file, priority)
   - Detected restricted keyword(s)
   - Approve / Deny prompt for the user
4. **HALT** — do NOT proceed with the restricted action until user approves
5. **Log** the routing with action: `create`, details mentioning restricted action detection

**Bronze Tier restrictions:** Cannot send emails, make payments, post to social media, delete files permanently, or contact external parties.

See [references/handbook-template.md](references/handbook-template.md) for full autonomy boundaries.

## 7. Log Review

When user asks "what happened today?" or requests audit log review:

1. **Determine date:** Use today's date unless user specifies another date
2. **Read** `/Logs/YYYY-MM-DD.json`
   - If file doesn't exist: report "No actions recorded for [date]."
   - If file exists: parse JSON array
3. **Present** entries in human-readable format:
   ```
   timestamp | action | file | result | details
   ```
4. **Summarize** totals: N actions, breakdown by type (triaged: X, completed: Y, etc.)

## Vault Structure

Complete folder and file schema: [references/vault-structure.md](references/vault-structure.md)

## Error Handling

- Always log errors before reporting them
- Never silently skip files — warn and continue
- If vault health check fails mid-operation, stop and report
- Malformed JSON in log files: back up the file, create fresh log, report to user
