# Implementation Plan: Sentinel File System Watcher

**Branch**: `002-sentinel-watcher` | **Date**: 2026-02-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-sentinel-watcher/spec.md`

## Summary

Build an external Python script ("Sentinel") that monitors a local drop folder for new files and moves them into the Obsidian Vault's `/Inbox/` folder. The sentinel is a "dumb feeder" — it detects, waits for file stability, moves, and generates sidecar `.md` files for non-markdown items. It does not triage or classify. Built on `watchdog` for OS-native file system events, managed with `uv`, and designed with a `BaseWatcher` abstract class for future Silver Tier extensions (Gmail, WhatsApp).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `watchdog` (file system events), `python-dotenv` (configuration)
**Storage**: Local file system only (source directory → vault `/Inbox/`)
**Testing**: `pytest` with `tmp_path` fixtures for isolated file system tests
**Target Platform**: Windows 10+ (primary), cross-platform compatible (macOS, Linux)
**Project Type**: Single CLI package with `src/` layout managed by `uv`
**Performance Goals**: File detection and ingestion within 5 seconds of write completion
**Constraints**: Zero network calls (Bronze Law I), zero triage logic (FR-011), single-directory top-level monitoring only
**Scale/Scope**: Single watcher instance, one source directory, ~10-50 files/day expected throughput

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Local-First Privacy | No external APIs, no cloud services, no network calls | PASS — watchdog and python-dotenv are fully local. Config via `.env`. No network code. |
| II. HITL Safety | No autonomous external actions | PASS — Sentinel only moves files within local file system. No emails, payments, or external comms. |
| III. Vault Integrity | Respect vault folder structure | PASS — Writes only to `/Inbox/`. Does not modify Dashboard, Handbook, or other vault state. |
| IV. Audit Logging | Log all file operations | PASS — FR-009 requires console logging of all operations. Vault audit logs (`/Logs/`) are the agent's responsibility, not the sentinel's. |
| V. Operational Boundaries | Stay within Bronze Tier scope | PASS — No autonomous loops (runs as user-started process), no MCP, no external services. |

**Post-Phase 1 Re-check**: All gates still PASS. The `BaseWatcher` abstract class is forward-looking but does not introduce Silver Tier functionality — it only defines the interface.

## Project Structure

### Documentation (this feature)

```text
specs/002-sentinel-watcher/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research decisions
├── data-model.md        # Entity definitions and sidecar template
├── quickstart.md        # Setup and run instructions
├── contracts/
│   └── base-watcher-interface.md  # BaseWatcher contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /sp.tasks)
```

### Source Code (repository root)

```text
sentinel/
├── pyproject.toml           # uv project: name, version, deps, entry points
├── uv.lock                  # Locked dependency versions (committed)
├── .python-version          # Python version pin (3.10+)
├── .env.example             # Configuration template (committed)
├── .env                     # User's local config (gitignored)
├── src/
│   └── sentinel/
│       ├── __init__.py      # Package: __version__, public exports
│       ├── __main__.py      # `python -m sentinel` entry point
│       ├── cli.py           # CLI: parse args, load config, start watcher
│       ├── config.py        # WatcherConfig dataclass, .env loading
│       ├── base.py          # BaseWatcher ABC (start, stop, on_new_item)
│       ├── filesystem.py    # FileSystemWatcher (watchdog Observer, handler, queue)
│       └── sidecar.py       # Sidecar .md generation for non-markdown files
└── tests/
    ├── __init__.py
    ├── conftest.py          # Shared fixtures: temp source/inbox dirs
    ├── test_config.py       # Config loading, validation, defaults
    ├── test_filesystem.py   # Watcher integration: detect, stability, move
    ├── test_sidecar.py      # Sidecar generation, template, metadata
    └── test_ignore.py       # Ignore patterns: .tmp, .~lock, dot-files
```

**Structure Decision**: Single `src/` layout package (`uv init --package sentinel`). This is a standalone CLI tool, not a web app or library. The `src/` layout prevents accidental imports of uninstalled code and is uv's recommended structure for packages.

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     sentinel (Python)                    │
│                                                         │
│  ┌──────────┐    ┌────────────────┐    ┌─────────────┐ │
│  │  cli.py   │───→│  config.py      │    │  base.py    │ │
│  │ (entry)   │    │ (WatcherConfig) │    │ (ABC)       │ │
│  └─────┬─────┘    └───────┬────────┘    └──────┬──────┘ │
│        │                  │                     │        │
│        ▼                  ▼                     │        │
│  ┌──────────────────────────────────────┐      │        │
│  │         filesystem.py                 │◄─────┘        │
│  │  ┌──────────────┐  ┌──────────────┐  │               │
│  │  │ EventHandler  │  │ WorkerThread │  │               │
│  │  │ (on_created)  │──→ (Queue)      │  │               │
│  │  └──────────────┘  └──────┬───────┘  │               │
│  └──────────────────────────┬───────────┘               │
│                              │                           │
│                              ▼                           │
│                     ┌──────────────┐                     │
│                     │  sidecar.py   │                     │
│                     │  (generate)   │                     │
│                     └──────────────┘                     │
└──────────────────────────┬──────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Source   │ │  Vault   │ │  Console │
        │  Dir      │ │  /Inbox/ │ │  Log     │
        └──────────┘ └──────────┘ └──────────┘
```

### Event Flow

```
1. User drops file into Source Directory
2. OS notifies watchdog → on_created event fires
3. EventHandler checks:
   a. Is it a directory? → skip
   b. Is it ignored (.tmp, .~lock, dot-file)? → skip + log
   c. Is extension allowed? → if not, skip + log
   d. Is path already pending? → skip (dedup)
4. File path added to processing Queue + pending set
5. Worker thread picks up path:
   a. Stability check: poll size every 1s until stable for 2s
   b. If stable: resolve destination path (handle collisions)
   c. Move file: source → inbox
   d. If non-.md: generate sidecar .md in inbox
   e. Log result
   f. Remove from pending set
6. On error at any step: log error, remove from pending, continue
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Event type | `on_created` only | Avoids duplicate `on_modified` events; stability check handles partial writes |
| Stability check | Size-based polling (2s) | Cross-platform, simple, sufficient for Bronze Tier |
| Processing model | Queue + worker thread | Decouples detection from processing; observer thread stays responsive |
| Deduplication | Pending path set | Prevents duplicate processing from redundant OS events |
| Config | `.env` + `python-dotenv` | Bronze Law compliant; no external config services |
| Package manager | `uv` | User requirement; modern, fast, creates proper `src/` layout |
| Sidecar naming | `{filename}.md` (e.g., `invoice.pdf.md`) | Sits next to original; easily discoverable by agent glob patterns |
| Collision handling | Timestamp suffix before extension | `report_20260220T120000.md`; preserves extension for file type detection |
| Logging | Python `logging` to console | Standard, configurable, supports ISO-8601 format |

### Sidecar Template

For non-markdown files, the sentinel generates a companion markdown file:

```markdown
---
type: sidecar
original_filename: "invoice-march.pdf"
source_path: "C:/Users/User/Desktop/AI_Employee_Drop/invoice-march.pdf"
file_size_bytes: 245760
ingestion_timestamp: "2026-02-20T12:01:30Z"
file_extension: ".pdf"
---

# invoice-march.pdf

Ingested by Sentinel on 2026-02-20T12:01:30Z.

**Source**: `C:/Users/User/Desktop/AI_Employee_Drop/invoice-march.pdf`
**Size**: 245,760 bytes
**Type**: .pdf

> This file was automatically generated. The original file is stored alongside this sidecar.
```

## Implementation Roadmap

### Phase 1: Foundation (config + base class)

1. Initialize `sentinel/` package with `uv init --package sentinel`
2. Create `config.py`: `WatcherConfig` dataclass, `.env` loading, path validation
3. Create `base.py`: `BaseWatcher` ABC with `start()`, `stop()`, `on_new_item()`
4. Create `.env.example` with documented variables
5. Write `test_config.py`: loading, defaults, validation errors

### Phase 2: Core Watcher (detect + move)

6. Create `filesystem.py`: `FileSystemWatcher` extending `BaseWatcher`
7. Implement watchdog `Observer` + `EventHandler` with `on_created`
8. Implement stability check (size polling with `threading.Timer`)
9. Implement file move with collision handling
10. Implement ignore patterns (`.tmp`, `.~lock`, dot-files, `~` prefix)
11. Create `cli.py` + `__main__.py`: wire config → watcher → start
12. Write `test_filesystem.py`: detect, move, collision, ignore patterns

### Phase 3: Sidecar Generation

13. Create `sidecar.py`: template rendering, metadata extraction
14. Integrate sidecar generation into `FileSystemWatcher.on_new_item()`
15. Write `test_sidecar.py`: template correctness, non-.md only, metadata fields

### Phase 4: Robustness + Polish

16. Add graceful shutdown (SIGINT handler, observer stop/join)
17. Add directory validation at startup (create source if missing, fail on bad inbox)
18. Add structured logging with ISO-8601 format
19. Write `test_ignore.py`: comprehensive ignore pattern tests
20. End-to-end test: drop file → detect → stability → move → sidecar → log

## Complexity Tracking

> No complexity violations detected. Single package, 6 modules, no unnecessary abstractions.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Watchdog event duplication on Windows | Duplicate processing of same file | Pending path set for deduplication |
| Large file stability false positive | File moved before fully written | 2-second stability window; configurable via `STABILITY_SECONDS` |
| Source directory deleted while running | Watcher crash | Wrap observer in try/except; log error and retry |
