# Quickstart: Vault Manager — Bronze Tier

**Branch**: `001-vault-manager` | **Date**: 2026-02-19

## Prerequisites

- Claude Code CLI installed and configured
- An empty directory for the Obsidian vault (or an existing Obsidian vault directory)
- Obsidian installed (optional — for GUI viewing)

## Step 1: Initialize the Vault

Tell Claude Code to set up the vault:

```
"Set up my AI employee vault at [path]"
```

**Expected result**:
- 4+ folders created: `/Inbox`, `/Needs_Action`, `/Done`, `/Logs`
- `Dashboard.md` created with empty-state sections
- `Company_Handbook.md` created with Bronze Tier defaults
- Health check reported: "9 items verified"

## Step 2: Customize the Handbook (Optional)

Open `Company_Handbook.md` in Obsidian and:
- Add VIP contact names
- Adjust priority keywords if needed
- Review autonomy boundaries

## Step 3: Set Up a Watcher (External)

Create a watcher script that writes files to `/Inbox/`. For Bronze Tier, choose one:
- **Gmail watcher**: Python script using Gmail API to fetch emails → write to /Inbox/
- **File system watcher**: Python script monitoring a folder → copy new files to /Inbox/

Watcher scripts are external to the vault manager. They just write files.

## Step 4: Process Inbox

When new files appear in `/Inbox/`, tell Claude:

```
"Process my inbox"
```

**Expected result**:
- Each file classified by priority (#high, #medium, #low)
- Actionable items → `/Needs_Action/`
- Informational items → `/Done/`
- Dashboard updated with current state
- Audit log entries written

## Step 5: Complete Tasks

When you finish a task:

```
"I finished the [task name] task"
```

**Expected result**:
- Source file moved to `/Done/`
- Dashboard Pending Actions updated
- Recently Completed updated
- Stats recalculated
- Audit log entry written

## Step 6: Review Status

```
"Show me the current status"
```

Or open `Dashboard.md` in Obsidian directly.

## Verification

After completing steps 1-5, verify:
- [ ] All folders exist and are accessible
- [ ] Dashboard.md shows correct counts
- [ ] `/Logs/YYYY-MM-DD.json` has entries for all operations
- [ ] No files were lost during triage or completion
- [ ] Company_Handbook.md is unmodified (unless you customized it)
