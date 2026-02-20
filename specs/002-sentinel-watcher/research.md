# Research: Sentinel File System Watcher

**Feature**: 002-sentinel-watcher
**Date**: 2026-02-20

## R1: Watchdog Library — Observer Pattern & Event Handling

**Decision**: Use `watchdog.observers.Observer` with a custom `FileSystemEventHandler` subclass. Listen to `on_created` events only (not `on_modified`), then apply a stability check before processing.

**Rationale**:
- `on_created` fires when a file first appears. The file may not be fully written yet.
- `on_modified` fires multiple times per file save (editors write temp file then rename), causing duplicate processing.
- Best approach: capture `on_created`, then poll file size at 1-second intervals until stable for 2 seconds.
- Filter `event.is_directory` immediately to ignore directory events.

**Alternatives considered**:
- Listening to both `on_created` + `on_modified`: Rejected — causes duplicate processing and complexity.
- Polling (no watchdog): Rejected — wasteful and slow compared to OS-native file system events.

## R2: Stability Check for Partial Writes

**Decision**: After `on_created` fires, schedule a deferred check. Poll the file size every 1 second. If size is unchanged after 2 consecutive checks (2 seconds stable), the file is ready. Use a `threading.Timer` or a dedicated processing queue with a worker thread.

**Rationale**:
- `on_created` fires before the file is fully written for large files.
- File locking is unreliable cross-platform (Windows locks differ from Unix).
- Size-based stability check is simple, portable, and sufficient for Bronze Tier.

**Alternatives considered**:
- Try-open-with-exclusive-lock: Rejected — platform-specific and unreliable for read-only checks.
- Wait for `on_closed` event: Rejected — watchdog doesn't have a reliable close event on all platforms.

## R3: Graceful Shutdown

**Decision**: Use `signal.signal(SIGINT, handler)` combined with `observer.stop()` + `observer.join()`. The standard pattern is a `while observer.is_alive(): observer.join(1)` loop inside a `try/except KeyboardInterrupt`.

**Rationale**: Observer runs as a daemon thread. Without explicit stop/join, the process may hang or leave the observer in a dirty state.

**Alternatives considered**:
- `atexit` handler: Rejected — doesn't reliably fire on SIGINT.
- Daemon thread auto-exit: Works for immediate exit but doesn't allow in-flight file moves to complete.

## R4: Non-Recursive Monitoring

**Decision**: Pass `recursive=False` to `observer.schedule()`.

**Rationale**: FR-015 requires top-level only. This is a single parameter. Default is `False` in watchdog but we set it explicitly for clarity.

## R5: Threading Model

**Decision**: Observer runs in a background thread (daemon thread by default). File processing (stability check + move + sidecar) runs in a separate worker thread to avoid blocking the observer's event dispatch.

**Rationale**:
- The observer's event handler callbacks run in the observer's thread. Blocking them delays event delivery.
- A `queue.Queue` between the event handler and a worker thread decouples detection from processing.

**Alternatives considered**:
- `asyncio`: Rejected — watchdog is thread-based; mixing async adds complexity with no benefit at Bronze Tier.
- Process in observer thread directly: Rejected — stability check sleeps would block event delivery.

## R6: Event Deduplication

**Decision**: Use a `set` of currently-pending file paths. When `on_created` fires, check if the path is already pending. If yes, skip. Remove from the set after successful processing.

**Rationale**:
- Some platforms fire multiple `on_created` events for the same file.
- The pending set prevents duplicate processing without a complex debounce timer.

## R7: uv Package Manager

**Decision**: Use `uv init --package sentinel` with `src/` layout. Dependencies managed via `uv add`. Run with `uv run sentinel`.

**Rationale**:
- uv is the user's preferred tool (explicitly stated in requirements).
- `--package` flag creates proper `src/` layout with `pyproject.toml` and `[project.scripts]` entry point.
- `uv.lock` committed to git for reproducible installs.
- `.venv/` auto-managed and gitignored.

**Key details**:
- Build backend: `hatchling` (uv default).
- Dependencies: `watchdog`, `python-dotenv` via `uv add`.
- Dev dependencies: `pytest` via `uv add --dev`.
- Run: `uv run sentinel` (CLI entry point) or `uv run python -m sentinel`.

## R8: Configuration via .env

**Decision**: Use `python-dotenv` to load `.env` file at startup. Three config variables: `WATCH_DIRECTORY`, `VAULT_INBOX_PATH`, `ALLOWED_EXTENSIONS` (optional, with defaults).

**Rationale**:
- FR-012 requires configurability. `.env` is simple and follows Bronze Law (no external config services).
- `python-dotenv` is well-established, local-only, no network calls.
- Constitution Principle I: secrets/paths must use env vars, never hardcoded.

## R9: Logging Strategy

**Decision**: Use Python standard `logging` module with `StreamHandler` (console) and optional `FileHandler` (to `sentinel.log` outside the vault). ISO-8601 timestamps in log format.

**Rationale**:
- FR-009 requires console logging with timestamps.
- Standard `logging` supports multiple handlers, levels, and formatting out of the box.
- Log file stored outside the vault to avoid polluting vault state (not a vault file).
