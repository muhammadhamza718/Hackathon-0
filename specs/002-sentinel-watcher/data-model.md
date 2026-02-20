# Data Model: Sentinel File System Watcher

**Feature**: 002-sentinel-watcher
**Date**: 2026-02-20

## Entities

### WatcherConfig

Configuration loaded from `.env` at startup.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| watch_directory | Path | Yes | — | Source directory to monitor |
| vault_inbox_path | Path | Yes | — | Obsidian vault `/Inbox/` path |
| allowed_extensions | set[str] | No | `.md,.txt,.pdf,.jpg,.jpeg,.png` | File extensions to process |
| stability_interval | float | No | 1.0 | Seconds between size checks |
| stability_threshold | int | No | 2 | Consecutive stable checks required |
| log_level | str | No | `INFO` | Python logging level |
| log_file | Path | No | None | Optional log file path (outside vault) |

### WatchedFile

Represents a file detected in the source directory during stability checking.

| Field | Type | Description |
|-------|------|-------------|
| path | Path | Absolute path to the file in source directory |
| name | str | Filename (stem + extension) |
| extension | str | File extension (lowercase, with dot) |
| size | int | File size in bytes (last checked) |
| last_checked | datetime | Timestamp of last size check |
| stable_count | int | Number of consecutive checks with unchanged size |
| is_ready | bool | True when `stable_count >= stability_threshold` |

**State transitions**:
```
DETECTED → CHECKING → READY → MOVED
                    ↘ SKIPPED (if extension not allowed or temp file)
         → ERROR (if I/O failure during check/move)
```

### SidecarMetadata

Content written to sidecar `.md` files for non-markdown files.

| Field | Type | Description |
|-------|------|-------------|
| original_filename | str | Original name of the file |
| source_path | str | Absolute path where the file was found |
| file_size_bytes | int | Size of the original file |
| ingestion_timestamp | str | ISO-8601 timestamp when file was ingested |
| file_extension | str | Original extension |

**Sidecar template**:
```markdown
---
type: sidecar
original_filename: "{original_filename}"
source_path: "{source_path}"
file_size_bytes: {file_size_bytes}
ingestion_timestamp: "{ingestion_timestamp}"
file_extension: "{file_extension}"
---

# {original_filename}

Ingested by Sentinel on {ingestion_timestamp}.

**Source**: `{source_path}`
**Size**: {file_size_bytes} bytes
**Type**: {file_extension}

> This file was automatically generated. The original file is stored alongside this sidecar.
```

### IgnorePatterns

Files matching these patterns are never processed.

| Pattern | Description |
|---------|-------------|
| `*.tmp` | Temporary files |
| `*.~lock*` | Lock files (LibreOffice, etc.) |
| `.*` | Dot-files (hidden/system files) |
| `~*` | Temp files (Microsoft Office, etc.) |
| `*.crdownload` | Chrome partial downloads |
| `*.part` | Firefox partial downloads |

## Relationships

```
WatcherConfig ──configures──→ FileSystemWatcher
FileSystemWatcher ──detects──→ WatchedFile (1:many)
WatchedFile ──generates──→ SidecarMetadata (0..1, only for non-.md files)
WatchedFile ──moves-to──→ InboxDirectory
SidecarMetadata ──written-to──→ InboxDirectory
```

## Validation Rules

1. `watch_directory` MUST exist and be readable at startup (or created with warning).
2. `vault_inbox_path` MUST exist and be writable at startup (fail-fast if not).
3. `allowed_extensions` MUST all start with `.` (dot).
4. File stability requires `stable_count >= stability_threshold` (default: 2 checks at 1-second intervals = 2 seconds stable).
5. Filename collision: if target path exists in inbox, append `_YYYYMMDDTHHMMSS` before extension.
