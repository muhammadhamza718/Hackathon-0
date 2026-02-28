# Deployment Guide

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- An Obsidian Vault directory

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/muhammadhamza718/Hackathon-0.git
cd Hackathon-0
```

### 2. Create the vault structure
Create these directories in your Obsidian Vault:
```
mkdir -p Inbox Needs_Action Done Pending_Approval Approved Rejected Plans Logs
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your paths:
#   WATCH_DIRECTORY=/path/to/watch
#   VAULT_INBOX_PATH=/path/to/vault/Inbox
```

### 4. Install sentinel dependencies
```bash
cd sentinel
uv sync
```

### 5. Start the sentinel watcher
```bash
cd sentinel
uv run python -m sentinel
```

## Verification

1. Drop a `.md` file into your `WATCH_DIRECTORY`
2. Check that it appears in your vault's `/Inbox/`
3. Verify `Dashboard.md` updates

## Running Tests
```bash
# From project root
pytest tests/ -v
```

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Sentinel won't start | Check `.env` paths exist |
| Files not detected | Verify `ALLOWED_EXTENSIONS` includes your file type |
| Permission errors | Ensure write access to vault directories |
