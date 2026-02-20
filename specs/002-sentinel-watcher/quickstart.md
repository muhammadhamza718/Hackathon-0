# Quickstart: Sentinel File System Watcher

**Feature**: 002-sentinel-watcher
**Date**: 2026-02-20

## Prerequisites

- Python 3.10+
- `uv` package manager (install: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- An initialized Obsidian Vault with an `/Inbox/` folder

## Setup

```bash
# 1. Navigate to the sentinel directory
cd sentinel/

# 2. Install dependencies (uv creates .venv automatically)
uv sync

# 3. Create .env file from template
cp .env.example .env

# 4. Edit .env with your paths
#    WATCH_DIRECTORY=C:/Users/YourName/Desktop/AI_Employee_Drop
#    VAULT_INBOX_PATH=C:/Users/YourName/ObsidianVault/Inbox
```

## Configuration (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WATCH_DIRECTORY` | Yes | — | Path to the source/drop folder to monitor |
| `VAULT_INBOX_PATH` | Yes | — | Path to the vault's `/Inbox/` folder |
| `ALLOWED_EXTENSIONS` | No | `.md,.txt,.pdf,.jpg,.jpeg,.png` | Comma-separated allowed extensions |
| `STABILITY_SECONDS` | No | `2` | Seconds a file must be stable before processing |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | No | *(none)* | Optional path to log file (outside vault) |

## Run

```bash
# Start the sentinel
uv run sentinel

# Or directly with Python
uv run python -m sentinel
```

## Verify It Works

1. Start the sentinel (terminal should show "Watching: C:/Users/.../AI_Employee_Drop")
2. Copy or save any `.md` file into the watch directory
3. Within 5 seconds, the file should appear in your vault's `/Inbox/` folder
4. The terminal should log: `[INFO] Moved: example.md → Inbox/example.md`

## Stop

Press `Ctrl+C` to gracefully shut down the sentinel.

## Project Structure

```
sentinel/
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Locked dependency versions
├── .env.example            # Configuration template
├── .env                    # Your local configuration (gitignored)
├── src/
│   └── sentinel/
│       ├── __init__.py     # Package init
│       ├── __main__.py     # Entry point (python -m sentinel)
│       ├── cli.py          # CLI entry point
│       ├── config.py       # Configuration loading from .env
│       ├── base.py         # BaseWatcher abstract class
│       ├── filesystem.py   # FileSystemWatcher implementation
│       └── sidecar.py      # Sidecar .md generation
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_filesystem.py
    ├── test_sidecar.py
    └── conftest.py         # Shared fixtures (temp dirs, etc.)
```
