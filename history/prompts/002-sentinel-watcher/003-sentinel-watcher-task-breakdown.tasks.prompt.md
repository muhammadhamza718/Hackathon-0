---
id: 003
title: Sentinel Watcher Task Breakdown
stage: tasks
date: 2026-02-20
surface: agent
model: claude-haiku-4-5-20251001
feature: 002-sentinel-watcher
branch: main
user: human
command: /sp.tasks
labels: ["tasks", "sentinel", "watcher", "bronze-tier", "implementation", "granular-tasks"]
links:
  spec: specs/002-sentinel-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-sentinel-watcher/tasks.md
tests:
  - Task count: 45 total (6 setup + 6 foundation + 11 US1 + 5 US2 + 5 US3 + 3 US4 + 9 polish)
  - Format validation: All tasks follow [ID] [P?] [Story?] Description pattern
  - Critical path: Setup → Foundation → US1 (MVP at T28) → US2 → US3 → US4 → Polish
---

## Prompt

sentinel "Generate a granular, testable task list for the Sentinel (Watcher) component (Bronze Tier)."
GOAL:
Break down the 'specs/sentinel/plan.md' into a detailed checklist of implementation tasks. Each task must be small enough to be implemented and tested independently using Python.
CONTEXT:
Use 'specs/sentinel/spec.md' and 'specs/sentinel/plan.md' as the source of truth. All tasks MUST comply with the 'Bronze Law' in '.specify/memory/constitution.md'.
TASK BREAKDOWN REQUIREMENTS:
1. ENVIRONMENT SETUP:
   - Task: Initialize Python project with 'uv'.
   - Task: Create '.env' file with WATCH_DIR and VAULT_INBOX paths.
   - Task: Install 'watchdog' and 'python-dotenv'.
2. BASE ARCHITECTURE:
   - Task: Implement 'sentinel/base.py' (Abstract BaseWatcher).
   - Task: Implement basic logging and error handling.
3. FILESYSTEM WATCHER:
   - Task: Implement 'sentinel/filesystem.py' capturing file creation events.
   - Task: Add debounce/delay logic to ensure files are fully written.
   - Task: Implement the 'Atomic Move' to the vault's /Inbox.
4. METADATA & SIDECARS:
   - Task: Implement logic to detect binary files (.pdf, .png).
   - Task: Implement 'Sidecar Generation' for creating metadata .md files.
5. INTEGRATION & TESTING:
   - Task: Write unit tests for the FileSystemWatcher using 'pytest'.
   - Task: Create a 'mock' watch directory for manual testing.
   - Task: Perform a "Full Loop" test: Drop file -> Sentinel moves to Vault -> Agent triages.
6. POLISH:
   - Task: Implement graceful shutdown (Ctrl+C).
   - Task: Add auto-restart/re-attachment logic for missing directories.
OUTPUT:
Create 'specs/sentinel/tasks.md' following the SDD standard. Ensure the task list is optimized for small, reviewable git commits.

## Response snapshot

Generated 45 granular, testable tasks organized across 7 phases: Phase 1 Setup (6 tasks: uv init, pyproject.toml, .env, .gitignore, directories), Phase 2 Foundation (6 tasks: WatcherConfig, BaseWatcher ABC, logging, CLI entry point), Phase 3 User Story 1/P1 MVP (11 tasks: watchdog observer, on_created handler, ignore patterns, stability check, file move, collision resolution, worker thread, graceful shutdown, logging, tests), Phase 4 User Story 2/P2 (5 tasks: sidecar generation, template, integration, tests), Phase 5 User Story 3/P3 (5 tasks: error handling, directory validation, ignore patterns tests, robustness tests), Phase 6 User Story 4/P4 (3 tasks: verify ABC, create MockWatcher stub), Phase 7 Polish (9 tasks: docstrings, type hints, logging verification, E2E test, Bronze Law compliance grep, public exports, graceful shutdown test, manual verification). MVP scope: 28 tasks (Phases 1–4). Critical path enforces foundation before stories. Parallelization opportunities identified within phases.

## Outcome

- Impact: Complete task breakdown (45 tasks) ready for `/sp.implement`. MVP scope identified (28 tasks for Phases 1–4). All tasks small, testable, independently reviewable.
- Tests: Format validation PASS — all 45 tasks follow strict `[ID] [P?] [Story?] Description` pattern with file paths. Task count breakdown correct (6+6+11+5+5+3+9).
- Files: 1 new file (specs/002-sentinel-watcher/tasks.md). Comprehensive task list with dependencies, parallelization guide, and implementation strategy.
- Next prompts: Run `/sp.implement` to execute tasks. Or `/sp.clarify` to refine task breakdown. Consider running MVP tasks first (Phases 1–4 = 28 tasks), then expand to full scope.
- Reflection: Breaking down at user-story granularity (P1 → MVP, then P2, P3, P4) ensures value delivery at each checkpoint. The 2-task prerequisite for sidecar integration (T024, T025 parallel, then T026 depends) maps cleanly to PR structure.

## Evaluation notes (flywheel)

- Failure modes observed: None. Prerequisite script failed due to branch state (expected, non-blocking). Proceeded with manual artifact loading.
- Graders run and results (PASS/FAIL): Format validation PASS (45/45 tasks follow checklist format)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add Mermaid dependency graph to tasks.md showing explicit blocker relationships (T001→T002, T002→T013, etc.)
