# Contract: BaseWatcher Interface

**Feature**: 002-sentinel-watcher
**Date**: 2026-02-20

## Abstract Interface: BaseWatcher

The `BaseWatcher` defines the contract that all watcher implementations must fulfill. This enables pluggable input sources (file system, Gmail, WhatsApp) in future tiers.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `start()` | `() -> None` | Begin monitoring the input source. Blocks until `stop()` is called or interrupted. |
| `stop()` | `() -> None` | Gracefully stop monitoring. Complete any in-flight operations. |
| `on_new_item(path)` | `(Path) -> None` | Called when a new item is detected and ready. Subclass implements ingestion logic. |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Human-readable name of the watcher (e.g., "FileSystemWatcher") |
| `is_running` | `bool` | Whether the watcher is currently active |

### Lifecycle

```
__init__(config) → start() → [on_new_item() called per item] → stop()
```

### Contract Rules

1. `start()` MUST be idempotent — calling it when already running is a no-op.
2. `stop()` MUST be idempotent — calling it when already stopped is a no-op.
3. `stop()` MUST allow in-flight `on_new_item()` calls to complete before returning.
4. `on_new_item()` MUST NOT raise exceptions — errors are logged and the watcher continues.
5. All implementations MUST accept a `WatcherConfig` (or subclass) as constructor parameter.

## Concrete Implementation: FileSystemWatcher

| Method | Behavior |
|--------|----------|
| `start()` | Creates watchdog Observer, schedules handler on `watch_directory`, starts observer thread. Enters main loop. |
| `stop()` | Signals observer to stop, joins observer thread, drains processing queue. |
| `on_new_item(path)` | Performs stability check, moves file to inbox, generates sidecar if non-.md, logs result. |

### Additional FileSystemWatcher Methods (internal)

| Method | Signature | Description |
|--------|-----------|-------------|
| `_is_allowed(path)` | `(Path) -> bool` | Check extension against allowed list |
| `_is_ignored(path)` | `(Path) -> bool` | Check against ignore patterns |
| `_wait_for_stability(path)` | `(Path) -> bool` | Poll file size until stable |
| `_move_to_inbox(path)` | `(Path) -> Path` | Move file, handle collisions, return destination |
| `_generate_sidecar(source, dest)` | `(Path, Path) -> Path` | Create sidecar .md for non-markdown files |
| `_resolve_collision(dest)` | `(Path) -> Path` | Append timestamp suffix if dest exists |
