# Audit Log Format

JSON schema and examples for `/Logs/YYYY-MM-DD.json` files.

## File Naming

- One file per day: `YYYY-MM-DD.json` (e.g., `2026-02-19.json`)
- File contains a JSON array of log entry objects
- If file doesn't exist, create with empty array `[]`
- Append new entries to the existing array

## Entry Schema

```json
{
  "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "action": "triage | complete | move | create | update_dashboard | error",
  "source_file": "relative/path/to/file.md",
  "details": "Human-readable description of what happened",
  "result": "success | failure | warning | skipped"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | string | Yes | ISO-8601 UTC timestamp |
| `action` | string | Yes | One of the valid action types |
| `source_file` | string | Yes | Relative path from vault root (use `"none"` if no file involved) |
| `details` | string | Yes | What happened and why |
| `result` | string | Yes | Outcome of the action |

### Valid Actions

| Action | When Used |
|--------|-----------|
| `triage` | Processing an inbox item (classification + routing) |
| `complete` | Marking a task as done and archiving |
| `move` | Moving a file between folders |
| `create` | Creating a new file (approval request, plan, etc.) |
| `update_dashboard` | Rebuilding Dashboard.md |
| `error` | Something went wrong (always log these) |

### Valid Results

| Result | Meaning |
|--------|---------|
| `success` | Action completed as expected |
| `failure` | Action could not be completed |
| `warning` | Action completed with caveats (e.g., missing frontmatter) |
| `skipped` | Action was skipped intentionally (e.g., empty inbox) |

## Examples

### Full day log file: `2026-02-19.json`

```json
[
  {
    "timestamp": "2026-02-19T09:00:00Z",
    "action": "triage",
    "source_file": "Inbox/client-email-feb19.md",
    "details": "Triaged email from client. Rationale: keywords matched 'invoice', 'payment' → #high per triage-rules.md. Classified as actionable. Routed to Needs_Action/.",
    "result": "success"
  },
  {
    "timestamp": "2026-02-19T09:00:15Z",
    "action": "triage",
    "source_file": "Inbox/newsletter-weekly.md",
    "details": "Triaged newsletter. No actionable content. Moved to Done.",
    "result": "success"
  },
  {
    "timestamp": "2026-02-19T09:00:20Z",
    "action": "triage",
    "source_file": "Inbox/malformed-file.md",
    "details": "Could not parse file: invalid YAML frontmatter on line 3. File skipped.",
    "result": "warning"
  },
  {
    "timestamp": "2026-02-19T09:01:00Z",
    "action": "update_dashboard",
    "source_file": "Dashboard.md",
    "details": "Rebuilt dashboard after triage. Pending: 1, Done: 1, Alerts: 0.",
    "result": "success"
  },
  {
    "timestamp": "2026-02-19T14:30:00Z",
    "action": "complete",
    "source_file": "Needs_Action/client-email-feb19.md",
    "details": "Task completed by user. Moved source to Done, updated dashboard.",
    "result": "success"
  },
  {
    "timestamp": "2026-02-19T14:30:30Z",
    "action": "update_dashboard",
    "source_file": "Dashboard.md",
    "details": "Rebuilt dashboard after task completion. Pending: 0, Done: 2, Alerts: 0.",
    "result": "success"
  }
]
```

### Error logging example

```json
{
  "timestamp": "2026-02-19T10:00:00Z",
  "action": "error",
  "source_file": "Logs/2026-02-19.json",
  "details": "Malformed JSON in existing log file. Backed up as 2026-02-19.json.bak, created fresh log.",
  "result": "failure"
}
```

### Move action example

```json
{
  "timestamp": "2026-02-19T11:00:00Z",
  "action": "move",
  "source_file": "Inbox/urgent-client-email.md",
  "details": "Moved source file to Done/ after task completion. Rationale: user confirmed task finished.",
  "result": "success"
}
```

### Create action example (approval routing)

```json
{
  "timestamp": "2026-02-19T09:05:00Z",
  "action": "create",
  "source_file": "Pending_Approval/approve-send-email-2026-02-19.md",
  "details": "Created approval request. Rationale: restricted action detected — 'send email' keyword found in Inbox/client-followup.md. Routed to Pending_Approval per Bronze Tier HITL rules.",
  "result": "success"
}
```

### Create action example (vault initialization)

```json
{
  "timestamp": "2026-02-19T08:00:00Z",
  "action": "create",
  "source_file": "none",
  "details": "Vault initialized. Created 5 Bronze Tier folders (Inbox, Needs_Action, Done, Pending_Approval, Logs) and 2 core files (Dashboard.md, Company_Handbook.md). 7 items total.",
  "result": "success"
}
```

### Empty inbox example

```json
{
  "timestamp": "2026-02-19T09:00:00Z",
  "action": "triage",
  "source_file": "none",
  "details": "Inbox empty. No items to triage.",
  "result": "skipped"
}
```

## Read/Write Procedure

1. **Read:** Parse existing file as JSON array (handle `[]` for new files)
2. **Append:** Push new entry object to the array
3. **Write:** Serialize full array back to file with 2-space indentation
4. **Validate:** Ensure file is valid JSON after write

If parsing fails (corrupted file):
1. Rename existing file to `YYYY-MM-DD.json.bak`
2. Create new file with `[]`
3. Log the error as first entry in new file
4. Report to user
