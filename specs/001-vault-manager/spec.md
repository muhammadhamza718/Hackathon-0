# Feature Specification: Vault Manager — Bronze Tier

**Feature Branch**: `001-vault-manager`
**Created**: 2026-02-19
**Status**: Draft
**Input**: User description: "Design the core Vault Management system for the Personal AI Employee (Bronze Tier)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize a New Vault (Priority: P1)

A user sets up their Personal AI Employee for the first time. They point Claude Code at an empty directory and ask it to "set up my vault." The system creates the complete folder structure, generates a default `Dashboard.md` with empty-state sections, and generates a default `Company_Handbook.md` with Bronze Tier rules. The user opens Obsidian and sees a fully organized, ready-to-use vault.

**Why this priority**: Without a properly initialized vault, no other feature can operate. This is the foundation for all subsequent operations.

**Independent Test**: Can be fully tested by running vault initialization on an empty directory and verifying all folders and files exist with correct content.

**Acceptance Scenarios**:

1. **Given** an empty directory, **When** the user requests vault initialization, **Then** all required folders (/Inbox, /Needs_Action, /Done, /Logs) are created and both core files (Dashboard.md, Company_Handbook.md) are generated with default content.
2. **Given** a partially initialized vault (some folders exist, some missing), **When** the user requests vault initialization, **Then** only missing folders and files are created; existing content is preserved.
3. **Given** a fully initialized vault, **When** the user requests vault initialization, **Then** the system reports "vault healthy" without modifying any existing files.

---

### User Story 2 - Triage Inbox Items (Priority: P1)

A watcher script drops new files into the `/Inbox/` folder. The user asks Claude to "process my inbox." The system reads each file, checks `Company_Handbook.md` for priority rules, classifies items by priority (#high, #medium, #low), and routes actionable items to `/Needs_Action/` and informational items to `/Done/`. Every triage decision is logged.

**Why this priority**: Inbox triage is the core "Perception-to-State" bridge — the primary value of the vault manager. Without it, incoming data just sits unprocessed.

**Independent Test**: Can be tested by placing 3 files with different content types in /Inbox/ and verifying correct classification, routing, and logging.

**Acceptance Scenarios**:

1. **Given** 3 files in /Inbox/ (one urgent email, one meeting request, one newsletter), **When** the user triggers inbox triage, **Then** the urgent email is routed to /Needs_Action/ as #high, the meeting request to /Needs_Action/ as #medium, and the newsletter to /Done/ as informational.
2. **Given** a file in /Inbox/ with no YAML frontmatter, **When** triage runs, **Then** the file is treated as a file_drop, a warning is logged, and processing continues without error.
3. **Given** an empty /Inbox/, **When** triage runs, **Then** a "no items to triage" message is logged and the Dashboard stats are updated.
4. **Given** a file containing keywords like "payment" or "send email", **When** triage runs, **Then** the system identifies the item as requiring higher-tier autonomy and routes it to /Pending_Approval/ instead.

---

### User Story 3 - View Live Dashboard (Priority: P2)

After triage or task completion, the user opens `Dashboard.md` in Obsidian and sees an up-to-date summary: pending actions sorted by priority, the 10 most recently completed items, real-time file counts per folder, and alerts for overdue high-priority items. All timestamps are in ISO-8601 format.

**Why this priority**: The Dashboard is the user's primary interface to the vault state. Without it, the user cannot see what the AI Employee has done or what needs attention.

**Independent Test**: Can be tested by populating vault folders with known items, triggering a dashboard update, and verifying all sections match actual folder contents.

**Acceptance Scenarios**:

1. **Given** 2 items in /Needs_Action/ (one #high, one #medium) and 5 items in /Done/, **When** the dashboard is rebuilt, **Then** Pending Actions shows both items sorted #high first, Recently Completed shows 5 items, and Stats show correct counts for all folders.
2. **Given** a #high item in /Needs_Action/ older than 24 hours, **When** the dashboard is rebuilt, **Then** the Alerts section lists this item with its age.
3. **Given** all folders are empty, **When** the dashboard is rebuilt, **Then** empty-state messages are displayed for each section and Stats show zero counts.

---

### User Story 4 - Complete a Task (Priority: P2)

The user says "I finished the invoice task." The system identifies the relevant files, moves the source from /Inbox/ to /Done/, removes the task from the Dashboard "Pending Actions," adds it to "Recently Completed," recalculates all stats from actual folder contents, and writes an audit log entry.

**Why this priority**: Task completion closes the lifecycle loop. Without it, the vault accumulates stale tasks and the Dashboard becomes unreliable.

**Independent Test**: Can be tested by placing a known task in /Needs_Action/, marking it complete, and verifying all file movements, Dashboard updates, and log entries.

**Acceptance Scenarios**:

1. **Given** a task in /Needs_Action/ with a source in /Inbox/, **When** the user marks it complete, **Then** the source moves to /Done/, the task is removed from Pending Actions, appears in Recently Completed, stats are recalculated, and an audit log entry with action "complete" is written.
2. **Given** a task with related files in /Plans/, **When** the user marks it complete, **Then** related plan files also move to /Done/.

---

### User Story 5 - Review Audit Logs (Priority: P3)

The user asks "what actions were taken today?" The system reads the current day's log file and presents a human-readable summary of all actions, including triage decisions, task completions, and any errors encountered.

**Why this priority**: Audit visibility is essential for trust in the AI Employee, but it's a read-only operation that depends on other stories generating log data first.

**Independent Test**: Can be tested by performing a series of operations (triage, complete), then querying the log and verifying all actions appear with correct timestamps and details.

**Acceptance Scenarios**:

1. **Given** a day's log file with 6 entries (3 triages, 2 dashboard updates, 1 completion), **When** the user asks for a log summary, **Then** all 6 entries are presented with timestamps, actions, files affected, and results.
2. **Given** no log file for today, **When** the user asks for a log summary, **Then** the system reports "no actions recorded today."

---

### Edge Cases

- What happens when a file in /Inbox/ is binary (PDF, image) rather than markdown?
  - System creates a markdown wrapper summarizing the file metadata, tags it #medium, and routes to /Needs_Action/.
- What happens when the daily log file contains malformed JSON?
  - System backs up the corrupted file as `YYYY-MM-DD.json.bak`, creates a fresh log, records the error as the first entry, and alerts the user.
- What happens when two triage runs occur simultaneously?
  - The system processes files sequentially. A file already moved from /Inbox/ during a prior run is silently skipped.
- What happens when Company_Handbook.md is missing or empty?
  - System uses built-in default priority keywords (same as handbook template) and logs a warning recommending handbook restoration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create all required vault folders (/Inbox, /Needs_Action, /Done, /Logs) if they do not exist when initialization is requested.
- **FR-002**: System MUST generate a default `Dashboard.md` with four sections (Pending Actions, Recently Completed, Stats, Alerts) when one does not exist.
- **FR-003**: System MUST generate a default `Company_Handbook.md` with Bronze Tier rules (Communication, Priority Definitions, Approval Thresholds, Autonomy Boundaries) when one does not exist.
- **FR-004**: System MUST read and parse every file in /Inbox/ during a triage operation, extracting content and optional YAML frontmatter.
- **FR-005**: System MUST classify each inbox item as #high, #medium, or #low priority using keyword matching against the rules defined in `Company_Handbook.md`.
- **FR-006**: System MUST route actionable items to /Needs_Action/ and informational items to /Done/ based on content analysis.
- **FR-007**: System MUST identify items requiring higher-tier autonomy (payments, emails, external actions) and route them to /Pending_Approval/ with a structured approval request.
- **FR-008**: System MUST rebuild `Dashboard.md` from actual folder contents after every significant file operation (triage, completion, manual trigger).
- **FR-009**: Dashboard MUST include: Pending Actions (sorted #high first), Recently Completed (last 10 by date), Stats (actual file counts per folder), and Alerts (#high items older than 24 hours).
- **FR-010**: System MUST use ISO-8601 timestamps (`YYYY-MM-DDTHH:MM:SSZ`) for all dates in Dashboard and logs.
- **FR-011**: System MUST append a JSON log entry to `/Logs/YYYY-MM-DD.json` for every file operation, including: timestamp, action type, source file, details (with decision rationale), and result.
- **FR-012**: System MUST handle missing frontmatter gracefully by treating the file as `type: file_drop` and logging a warning.
- **FR-013**: System MUST handle malformed log files by backing up the corrupted file, creating a fresh log, and recording the error.
- **FR-014**: System MUST preserve existing vault content during initialization — never overwrite files that already exist.
- **FR-015**: System MUST NOT perform any external actions (send emails, make API calls, access the internet). All operations are limited to local file system read/write within the vault.

### Key Entities

- **Inbox Item**: A markdown file deposited in /Inbox/ by an external watcher, containing optional YAML frontmatter (type, from, date, subject) and body text.
- **Needs Action Entry**: A structured markdown entry in /Needs_Action/ containing a task checklist line with wiki-link to source, summary, priority tag, and date.
- **Dashboard**: The `Dashboard.md` file at vault root — authoritative state summary rebuilt from actual folder contents.
- **Company Handbook**: The `Company_Handbook.md` file at vault root — defines priority keywords, VIP contacts, autonomy boundaries, and operational rules.
- **Audit Log Entry**: A JSON object in the daily log file with fields: timestamp, action, source_file, details, result.
- **Approval Request**: A structured markdown file in /Pending_Approval/ containing action needed, context, priority, and approval prompt.

## Constraints *(mandatory)*

- **Bronze Law Constitution**: All operations MUST comply with the 5 principles defined in `.specify/memory/constitution.md` (Local-First Privacy, HITL Safety, Vault Integrity, Audit Logging, Operational Boundaries).
- **Local-Only**: No network calls, no external APIs, no cloud services. All data stays on the local file system.
- **HITL Safety**: Any action that would require Bronze Tier-restricted capabilities (email, payment, social media, file deletion) MUST be routed to /Pending_Approval/ and halted.
- **Audit Completeness**: Every file operation MUST produce a log entry. Logging MUST NOT be skipped, even on errors.
- **Idempotent Initialization**: Running vault initialization multiple times on the same directory MUST produce the same result without data loss.

## Assumptions

- Watcher scripts are external processes managed independently. They write files to /Inbox/ and the vault manager reads them. No direct integration is required.
- The vault root path is provided by the user or inferred from the current working directory.
- File encoding is UTF-8 for all markdown and JSON files.
- The system processes inbox items sequentially (no concurrent triage).
- Binary files in /Inbox/ (PDF, images) receive a markdown metadata wrapper rather than content extraction.
- Retention policy for /Done/ and /Logs/ is indefinite unless the user explicitly configures cleanup.

## Out of Scope

- External API calls of any kind (Gmail, browser, social media, banking).
- Watcher script implementation or management (treated as independent external writers).
- Ralph Wiggum autonomous loop patterns (Gold Tier and above).
- MCP server integration (Silver Tier and above).
- Cloud-based session storage or vault sync.
- Multiple concurrent watcher management.
- Content extraction from binary files (only metadata wrapping).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vault initialization completes in under 5 seconds and produces all 4 required folders + 2 core files with correct default content.
- **SC-002**: Inbox triage correctly classifies 95%+ of items by priority when tested against a set of 20 sample files with known expected outcomes.
- **SC-003**: Dashboard accurately reflects actual vault state — file counts match actual folder contents with zero discrepancy after every update.
- **SC-004**: Every file operation produces exactly one audit log entry with all required fields (timestamp, action, source_file, details, result).
- **SC-005**: Items requiring higher-tier autonomy are correctly identified and routed to /Pending_Approval/ 100% of the time — the system never attempts a restricted action directly.
- **SC-006**: The system gracefully handles all edge cases (no frontmatter, malformed logs, empty inbox, missing handbook) without crashing or losing data.
- **SC-007**: A user can go from an empty directory to a fully functional vault, triage 5 inbox items, complete 2 tasks, and view an accurate dashboard — all within 10 minutes of interaction.
