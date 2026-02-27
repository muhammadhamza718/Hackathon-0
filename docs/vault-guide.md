# Vault Usage Guide

This guide explains how to use the Obsidian Vault as the AI Employee's workspace.

## Quick Start

1. Open your Obsidian Vault in the project root (or `test-vault/` for testing)
2. Drop a `.md` file into `/Inbox/`
3. The Sentinel Watcher detects it and the Vault Manager triages it

## Vault Folders

### `/Inbox/`
Drop new tasks here. The AI Employee monitors this folder continuously.

**Supported file types:** `.md`, `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.png`

### `/Needs_Action/`
Tasks that have been triaged and are ready for execution. Review and prioritize here.

### `/Done/`
Completed tasks are moved here automatically. Read-only in normal operation.

### `/Pending_Approval/` *(Silver Tier)*
Tasks requiring human approval before the agent can take external action.

**To approve:** Move the file to `/Approved/`
**To reject:** Move the file to `/Rejected/`

### `/Plans/` *(Silver Tier)*
Structured plan files created by the Silver Reasoning Agent.

Each plan file (`PLAN-YYYY-NNN.md`) contains:
- YAML frontmatter: `task_id`, `status`, `priority`, `created_date`
- Objective section
- Roadmap with step checkboxes
- Reasoning logs with timestamps

### `/Logs/`
Append-only audit log. Do not modify manually.

### `Dashboard.md`
Live status overview. Updated automatically after each operation.

## Writing Effective Inbox Tasks

```markdown
# Task Title

Priority: high | medium | low

## Description
Clear description of what needs to be done.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```
