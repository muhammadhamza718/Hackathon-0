# Operation Contracts: Vault Manager — Bronze Tier

**Date**: 2026-02-19 | **Branch**: `001-vault-manager`

These contracts define the input/output/side-effects for each vault operation. Since this is an Agent Skill (not a REST API), contracts are defined as operation signatures rather than HTTP endpoints.

---

## OP-1: Initialize Vault

**Trigger**: User requests vault setup
**Input**: Vault root path (directory)
**Preconditions**: Directory exists and is writable

**Steps**:
1. Create folders: /Inbox, /Needs_Action, /Done, /Logs, /Pending_Approval
2. Create Dashboard.md (if not exists) from template
3. Create Company_Handbook.md (if not exists) from template
4. Run health check

**Output**: Health check report (pass/fail with item list)
**Side effects**: Folders and files created on disk. Audit log entry (action: create).
**Idempotency**: Yes — re-running on initialized vault changes nothing.
**Error**: Missing items listed, offer to create them.

---

## OP-2: Triage Inbox

**Trigger**: User requests inbox processing
**Input**: All files in /Inbox/
**Preconditions**: Vault initialized, Company_Handbook.md readable

**Steps**:
1. Read Company_Handbook.md for priority rules
2. For each file in /Inbox/:
   a. Parse frontmatter + body
   b. Classify priority (#high/#medium/#low)
   c. Determine actionable vs informational
   d. Route to /Needs_Action/, /Done/, or /Pending_Approval/
3. Update Dashboard
4. Log all decisions

**Output**: Triage summary (N files processed, routing breakdown)
**Side effects**: Files moved/created. Dashboard.md rewritten. Log entries appended.
**Idempotency**: No — running twice on same inbox would find empty inbox on second run (files already moved).
**Error**: Malformed files skipped with warning. Missing handbook uses defaults.

---

## OP-3: Update Dashboard

**Trigger**: After triage, completion, or manual request
**Input**: Current vault folder contents
**Preconditions**: Vault initialized

**Steps**:
1. Count files in each folder
2. Read /Needs_Action/ for pending items (extract priority, date)
3. Read /Done/ for last 10 completed items
4. Compute alerts (#high > 24h)
5. Write Dashboard.md from template

**Output**: Updated Dashboard.md
**Side effects**: Dashboard.md overwritten. Log entry appended.
**Idempotency**: Yes — regeneration from actual state is idempotent.
**Error**: Write failure logged, user notified.

---

## OP-4: Complete Task

**Trigger**: User marks task as done
**Input**: Task identifier (filename or description)
**Preconditions**: Task exists in /Needs_Action/

**Steps**:
1. Identify source file in /Inbox/ (via wiki-link)
2. Move source file /Inbox/ → /Done/
3. Move related /Plans/ files → /Done/ (if any)
4. Remove from /Needs_Action/
5. Update Dashboard
6. Log completion

**Output**: Completion confirmation
**Side effects**: Files moved. Dashboard rewritten. Log entry appended.
**Idempotency**: No — already-completed task would not be found in /Needs_Action/.
**Error**: Task not found → report to user, no files moved.

---

## OP-5: Append Audit Log

**Trigger**: Every vault operation (internal, called by all other operations)
**Input**: Action type, source file, details, result

**Steps**:
1. Compute filename: /Logs/YYYY-MM-DD.json
2. Read existing file (or initialize [])
3. Parse JSON array
4. Append entry object
5. Write back

**Output**: None (internal side effect)
**Side effects**: Log file updated on disk.
**Idempotency**: No — each call appends a new entry.
**Error**: Malformed JSON → backup .bak, fresh start, error logged as first entry.

---

## OP-6: Route for Approval

**Trigger**: Restricted action detected during triage
**Input**: Source file, detected action, priority
**Preconditions**: /Pending_Approval/ exists

**Steps**:
1. Create approval request file in /Pending_Approval/
2. Log routing (action: create)
3. HALT — do not proceed with restricted action

**Output**: Approval request file path
**Side effects**: File created in /Pending_Approval/. Log entry appended.
**Idempotency**: No — each trigger creates a new approval file.
**Error**: Write failure → log error, report to user.

---

## Cross-Cutting Constraints

All operations MUST:
- Use ISO-8601 timestamps
- Log via OP-5 before returning
- Check Constitution Principle II (HITL Safety) for restricted actions
- Never access network or external services
- Never delete files permanently (move to /Done/ only)
