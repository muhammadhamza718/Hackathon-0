# Tasks: Sentinel File System Watcher

**Input**: Design documents from `/specs/002-sentinel-watcher/`
**Prerequisites**: plan.md (4-phase roadmap), spec.md (4 user stories P1-P4), research.md (tech decisions), data-model.md (entities), quickstart.md (setup guide)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

**Format**: `[ID] [P?] [Story?] Description`
- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3, US4) for story-phase tasks only

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure. All projects begin here.

- [ ] T001 Initialize Python 3.10+ project with `uv init --package sentinel` at repository root
- [ ] T002 Create `pyproject.toml` with project metadata, `watchdog` and `python-dotenv` dependencies, and CLI entry point `[project.scripts] sentinel = "sentinel.cli:main"`
- [ ] T003 [P] Create `.env.example` with template variables: `WATCH_DIRECTORY`, `VAULT_INBOX_PATH`, `STABILITY_SECONDS`, `LOG_LEVEL`
- [ ] T004 Create `.gitignore` with Python patterns: `__pycache__/`, `.venv/`, `*.pyc`, `.env` (local only), `sentinel.log`
- [ ] T005 [P] Create project directories: `src/sentinel/`, `tests/`, `tests/fixtures/`
- [ ] T006 Create `src/sentinel/__init__.py` with `__version__ = "0.1.0"`

**Checkpoint**: Project scaffolding complete. Dependencies declarable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

⚠️ **CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T007 Implement `src/sentinel/config.py`: `WatcherConfig` dataclass with fields from `.env` (WATCH_DIRECTORY, VAULT_INBOX_PATH, STABILITY_SECONDS, ALLOWED_EXTENSIONS, LOG_LEVEL); load via `load_from_env()` function using `python-dotenv`
- [ ] T008 Implement `src/sentinel/config.py`: Add validation in `WatcherConfig.__post_init__()` — fail if WATCH_DIRECTORY or VAULT_INBOX_PATH missing; convert to `Path` objects; validate STABILITY_SECONDS >= 1.0
- [ ] T009 Create `tests/test_config.py`: Test loading from `.env`, defaults for optional fields, validation errors for missing required paths
- [ ] T010 Implement `src/sentinel/base.py`: Abstract base class `BaseWatcher` with abstract methods `start() -> None`, `stop() -> None`, `on_new_item(path: Path) -> None`; add properties `name: str` and `is_running: bool`
- [ ] T011 Implement `src/sentinel/logging.py`: Configure Python `logging` with `StreamHandler` (console) and optional `FileHandler` (sentinel.log outside vault); use ISO-8601 timestamp format in logs
- [ ] T012 Implement `src/sentinel/__main__.py` and `src/sentinel/cli.py`: Entry point that loads `.env` via `WatcherConfig`, instantiates `FileSystemWatcher`, and calls `start()`; handle `KeyboardInterrupt` for graceful shutdown

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Automatic File Ingestion from Drop Folder (Priority: P1) 🎯 MVP

**Goal**: Detect new files in source directory, wait for stability (file fully written), move to vault `/Inbox/`, log all operations. Core perception layer.

**Independent Test**: Start sentinel with test source and vault directories, save a `.md` file into source, verify file appears in vault's `/Inbox/` within 5 seconds with correct name.

### Implementation for User Story 1

- [ ] T013 [P] [US1] Implement `src/sentinel/filesystem.py`: `FileSystemWatcher` class extending `BaseWatcher` with `__init__(config: WatcherConfig)` storing config, pending set (dedup), processing queue (stability check + move workers)
- [ ] T014 [P] [US1] Implement watchdog observer in `FileSystemWatcher.start()`: Create `watchdog.observers.Observer`, create custom `EventHandler(FileSystemEventHandler)` with `on_created(event)` that filters directories, checks ignore patterns, enqueues ready-to-check paths
- [ ] T015 [P] [US1] Implement ignore pattern check in `FileSystemWatcher._is_ignored(path: Path) -> bool`: Return `True` for `.tmp`, `.~lock`, dot-files (leading `.`), and `~` prefix files
- [ ] T016 [P] [US1] Implement extension filter in `FileSystemWatcher._is_allowed(path: Path) -> bool`: Check extension against `config.allowed_extensions` (default: `.md,.txt,.pdf,.jpg,.jpeg,.png`)
- [ ] T017 [US1] Implement stability check in `FileSystemWatcher._wait_for_stability(path: Path, timeout: float = 10.0) -> bool`: Poll file size every 1 second; return `True` if size unchanged for `config.stability_seconds` consecutive checks (default 2 checks = 2 seconds); log each poll attempt; timeout after 10 seconds
- [ ] T018 [US1] Implement file move in `FileSystemWatcher._move_to_inbox(source: Path) -> Path`: Move `source` to `config.vault_inbox_path / source.name`; if collision exists, resolve with timestamp suffix before extension (e.g., `report_20260220T120000.md`); return destination path
- [ ] T019 [US1] Implement collision resolution in `FileSystemWatcher._resolve_collision(dest: Path) -> Path`: If `dest` exists, append `_YYYYMMDDTHHMMSS` before extension; return new path; do NOT overwrite
- [ ] T020 [US1] Implement worker thread in `FileSystemWatcher.start()`: Spawn background thread reading from processing queue; call stability check → move → log for each item; handle exceptions (log, continue, do not crash)
- [ ] T021 [US1] Implement graceful shutdown in `FileSystemWatcher.stop()`: Signal observer to stop, join observer thread, drain processing queue by waiting for all pending moves to complete, log shutdown summary
- [ ] T022 [US1] Add logging: Every event (detected, moved, skipped, error) logged with timestamp and clear description; use `logging.info()`, `logging.debug()` for normal flow, `logging.error()` for failures
- [ ] T023 [US1] Create `tests/test_filesystem.py`: Unit tests for file detection, stability check (mock time + file size), file move, collision handling; use `tmp_path` pytest fixture for isolated source/inbox directories

**Checkpoint**: User Story 1 (P1) complete. MVP: files drop → detect → stabilize → move → log. Ready to verify in test environment.

---

## Phase 4: User Story 2 - Sidecar Generation for Non-Markdown Files (Priority: P2)

**Goal**: Generate `.md` companion files for binary/non-markdown files with metadata (original name, source path, size, timestamp), enabling agent triage.

**Independent Test**: Drop a `.pdf` file into source directory, verify both the original file AND a sidecar `.filename.pdf.md` appear in vault `/Inbox/` with correct metadata frontmatter.

### Implementation for User Story 2

- [ ] T024 [P] [US2] Implement `src/sentinel/sidecar.py`: Function `generate_sidecar(source: Path, dest: Path, config: WatcherConfig) -> Path` that creates sidecar `.md` file alongside binary in inbox
- [ ] T025 [P] [US2] Implement sidecar template in `src/sentinel/sidecar.py`: YAML frontmatter with fields `original_filename`, `source_path`, `file_size_bytes`, `ingestion_timestamp` (ISO-8601), `file_extension`; markdown body with human-readable summary
- [ ] T026 [US2] Integrate sidecar generation into `FileSystemWatcher._move_to_inbox()` (from US1): After successful move, check if source extension is NOT `.md`; if non-markdown, call `generate_sidecar(source, dest, config)` and log sidecar creation
- [ ] T027 [US2] Implement zero-sidecar rule in `_move_to_inbox()`: Do NOT generate sidecar for `.md` files (they are self-describing); log as skipped
- [ ] T028 [US2] Create `tests/test_sidecar.py`: Unit tests for sidecar generation — verify YAML frontmatter correctness, metadata fields, markdown body content; test for `.pdf`, `.jpg`, `.txt`; verify no sidecar for `.md`

**Checkpoint**: User Story 2 (P2) complete. Binary files now visible to agent triage via sidecars.

---

## Phase 5: User Story 3 - Robust Error Handling and Ignored Files (Priority: P3)

**Goal**: Sentinel survives errors, retries gracefully, ignores temporary files, and continues operating unattended.

**Independent Test**: Start sentinel with non-existent source directory → verify error logged + directory auto-created OR graceful exit message; drop `.tmp` file → verify not moved to inbox; simulate inbox inaccessible → verify error logged + retry on next cycle.

### Implementation for User Story 3

- [ ] T029 [P] [US3] Implement directory validation in `FileSystemWatcher.start()`: Check if `config.watch_directory` exists and is readable; if not, log error and either auto-create (if createable) or fail with clear message; check if `config.vault_inbox_path` exists and is writable; fail-fast if inbox missing
- [ ] T030 [P] [US3] Implement I/O error handling in worker thread (T020 callback): Wrap file move in try/except; on exception, log error with traceback, remove path from pending set, continue processing next item (do NOT crash)
- [ ] T031 [P] [US3] Implement re-attachment logic: If inbox becomes inaccessible during processing, catch exception, log "Inbox temporarily unavailable", remove from pending, retry on next `on_created` event (exponential backoff optional but not required)
- [ ] T032 [US3] Create `tests/test_ignore.py`: Unit tests for ignore patterns — verify `.tmp`, `.~lock`, dot-files, `~` prefix are skipped; verify no sidecar or move attempt for these
- [ ] T033 [US3] Create `tests/test_robustness.py`: Integration test for directory validation, I/O error recovery, continuous operation without crash for 5 mock file sequences

**Checkpoint**: User Story 3 (P3) complete. Sentinel robust enough for unattended operation.

---

## Phase 6: User Story 4 - Extensible Watcher Base Class (Priority: P4)

**Goal**: Prove that `BaseWatcher` ABC enables future watcher implementations (Gmail, WhatsApp) without modifying existing code.

**Independent Test**: Verify `BaseWatcher` defines `start()`, `stop()`, `on_new_item()` as abstract methods; verify `FileSystemWatcher` correctly inherits and implements all three; demonstrate that a hypothetical `GmailWatcher` subclass could be created with the same interface.

### Implementation for User Story 4

- [ ] T034 [US4] Verify `BaseWatcher` ABC (from T010) has all required abstract methods documented with docstrings: `start()`, `stop()`, `on_new_item()`; add `name` and `is_running` properties to contract
- [ ] T035 [US4] Create `tests/test_base_watcher.py`: Verify `FileSystemWatcher` correctly implements `BaseWatcher` — all abstract methods present, callable, and return correct types; instantiate and verify `is_running` behavior
- [ ] T036 [US4] Create stub/example class in `tests/fixtures/mock_watcher.py`: `MockWatcher(BaseWatcher)` that implements all abstract methods with no-ops; verify it can be instantiated without error (proves interface is extensible)

**Checkpoint**: User Story 4 (P4) complete. Architecture future-proofed for Silver Tier watchers.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Robustness, documentation, and final verification.

- [ ] T037 [P] Add docstrings to all public methods and classes: Sphinx-style or Google-style (consistent throughout)
- [ ] T038 [P] Add type hints to all function signatures and return types; use `Path`, `bool`, `Optional[str]`, `Callable` from `typing` and `pathlib`
- [ ] T039 [P] Verify all logging uses ISO-8601 format for timestamps (check `logging.Formatter` config)
- [ ] T040 Implement `tests/conftest.py`: Pytest fixtures for temp source/inbox directories, mock config, cleanup on test teardown
- [ ] T041 Create end-to-end test `tests/test_e2e.py`: Start sentinel, create real `.md` file in source, wait ≤5 seconds, verify in inbox, create `.pdf` file, verify sidecar, verify continuous operation for 30 seconds without crash
- [ ] T042 [P] Verify no external API calls: Grep `src/sentinel/` for `http`, `requests`, `urllib`, `boto`, `google.cloud`; confirm zero matches (Bronze Law I compliance check)
- [ ] T043 [P] Update `src/sentinel/__init__.py` with public exports: `__version__`, `BaseWatcher`, `FileSystemWatcher`, `WatcherConfig`
- [ ] T044 Test graceful shutdown: Start sentinel, send SIGINT (Ctrl+C), verify observer stops cleanly, queue drains, log shows "Shutdown complete"
- [ ] T045 Manual verification: Run `uv run sentinel` with real drop folder + vault, drop 3 files (`.md`, `.txt`, `.pdf`), verify all appear in inbox within 5s with sidecars; check console logs for correct format

**Checkpoint**: All 45 tasks complete. Sentinel ready for integration test with agent triage.

---

## Task Summary

| Phase | Description | Task Count |
|-------|-------------|-----------|
| 1 | Setup | 6 |
| 2 | Foundation | 6 |
| 3 | User Story 1 (P1) | 11 |
| 4 | User Story 2 (P2) | 5 |
| 5 | User Story 3 (P3) | 5 |
| 6 | User Story 4 (P4) | 3 |
| 7 | Polish | 9 |
| **TOTAL** | | **45** |

---

## Dependencies & Parallelization

### Critical Path (Sequential Dependencies)

1. **Phase 1 → Phase 2**: Setup must complete before foundation
2. **Phase 2 → All Stories**: Foundation must complete before US1, US2, US3, US4 can begin
3. **US1 → US2**: US1 (core file move) required before US2 (sidecar generation)

### Parallel Opportunities

- **Within Phase 1**: T003, T004, T005 can run in parallel (different files)
- **Within Phase 2**: T007, T008, T009 can run in parallel (config tests vs base class)
- **Within US1**: T013, T014, T015, T016 can run in parallel (different classes/functions, no cross-deps until T017)
- **Within US2**: T024, T025 can run in parallel (sidecar template vs core function)
- **Within US3**: T029, T030, T031, T032 can run in parallel (different error scenarios)
- **Within Phase 7**: T037–T043 can run mostly in parallel (all documentation/verification)

### MVP Scope (Minimum Viable Product)

**Stop after Phase 4 (US2 complete)** for MVP:
- Phase 1, 2, 3, 4 = 28 tasks
- Delivers: File detection → stability check → move → sidecar generation → logging
- Ready for agent integration test

### Full Scope

**Complete all phases (45 tasks)** for production-ready sentinel:
- Includes robustness, extensibility, comprehensive testing, polish
- Ready for Silver Tier integration and multi-source watcher development

---

## Implementation Strategy

1. **Start with MVP**: Complete Phases 1–4 first (28 tasks, ~2–3 development days)
2. **Test incrementally**: After each user story phase, run corresponding tests
3. **Integrate early**: After US1 complete, test with actual vault inbox
4. **Add robustness**: Phases 5–7 add defensive programming and extensibility
5. **Document as you go**: Docstrings in Phase 7, not as afterthought

**Recommended workflow**: Tasks 1→6 (setup), then 7→12 (foundation), then parallelize US1 (13–23), then US2 (24–28), then test E2E, then US3–4 (29–36), then polish (37–45).
