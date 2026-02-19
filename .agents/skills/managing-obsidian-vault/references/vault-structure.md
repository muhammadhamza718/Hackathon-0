# Vault Structure

Complete folder and file schema for the Digital FTE Obsidian Vault.

## Folder Structure

```
vault-root/
├── Inbox/              # [Bronze] Raw incoming items (emails, messages, file drops)
├── Needs_Action/       # [Bronze] Triaged items requiring attention
├── Done/               # [Bronze] Completed or informational items (archive)
├── Pending_Approval/   # [Bronze] Items awaiting user approval (beyond autonomy)
├── Logs/               # [Bronze] Daily JSON audit logs
├── Plans/              # [Silver+] Draft plans, proposals, strategies in progress
├── Approved/           # [Silver+] User-approved plans ready for execution
├── Dashboard.md        # [Bronze] Live status overview (auto-rebuilt)
└── Company_Handbook.md # [Bronze] Rules, priorities, autonomy boundaries
```

**Tier Legend:**
- **[Bronze]** — Required at Bronze Tier. Created during vault initialization.
- **[Silver+]** — Available at Silver Tier and above. Not created at Bronze Tier.

## Folder Descriptions

### `/Inbox/`
- **Purpose:** Landing zone for all new items
- **Contents:** Markdown files with optional YAML frontmatter
- **Lifecycle:** Files are triaged → moved to `/Needs_Action/` or `/Done/`
- **Expected frontmatter:**
  ```yaml
  ---
  type: email | whatsapp | file_drop
  from: sender name or identifier
  date: YYYY-MM-DD
  subject: brief description
  ---
  ```

### `/Needs_Action/`
- **Purpose:** Actionable items awaiting processing
- **Contents:** Markdown files with task checklist format
- **Entry format:**
  ```markdown
  - [ ] [[Inbox/FILENAME]] | One-line summary | #priority | @YYYY-MM-DD
  ```
- **Priority tags:** `#high`, `#medium`, `#low`

### `/Done/`
- **Purpose:** Archive of completed and informational items
- **Contents:** All processed files from Inbox (Bronze Tier); completed Plans at Silver+ Tier
- **Retention:** Indefinite unless user specifies cleanup policy

### `/Plans/` [Silver+]
- **Tier:** Silver and above
- **Purpose:** Draft plans, proposals, and strategies in progress
- **Contents:** Markdown files with structured plan format
- **Lifecycle:** Created during task processing → `/Done/` on completion, or → `/Pending_Approval/` if beyond autonomy

### `/Pending_Approval/`
- **Purpose:** Items requiring explicit user approval before execution
- **Contents:** Markdown files with action description and yes/no prompt
- **Required format:**
  ```markdown
  # Approval Required: [Action Title]

  **Action:** What needs to be done
  **Context:** Why this needs approval (references source file)
  **Priority:** #high | #medium | #low
  **Source:** [[Inbox/FILENAME]]

  ## Decision
  - [ ] Approve
  - [ ] Deny

  **Notes:** (user fills in)
  ```

### `/Approved/` [Silver+]
- **Tier:** Silver and above
- **Purpose:** User-approved items ready for execution
- **Contents:** Approved plans moved from `/Pending_Approval/`
- **Lifecycle:** Executed → moved to `/Done/`

### `/Logs/`
- **Purpose:** Immutable daily audit trail
- **Contents:** One JSON file per day: `YYYY-MM-DD.json`
- **Format:** JSON array of log entry objects
- **Retention:** Indefinite (never delete logs)

## Core Files

### `Dashboard.md`
- **Purpose:** Live status overview, rebuilt from actual vault state
- **Location:** Vault root
- **Update trigger:** After every triage, completion, or state change
- **Sections:** Pending Actions, Recently Completed, Stats, Alerts

### `Company_Handbook.md`
- **Purpose:** Rules governing FTE behavior and autonomy
- **Location:** Vault root
- **Read trigger:** Before every triage operation
- **Sections:** Communication Rules, Priority Definitions, Approval Thresholds, Autonomy Boundaries

## Health Check Criteria

A vault is healthy when (Bronze Tier):
1. All 5 Bronze folders exist and are accessible (Inbox, Needs_Action, Done, Pending_Approval, Logs)
2. `Dashboard.md` exists and is non-empty
3. `Company_Handbook.md` exists and is non-empty
4. No orphaned files outside the folder structure
5. Current day's log file exists in `/Logs/`
6. Total: 7 items verified (5 folders + 2 core files)
