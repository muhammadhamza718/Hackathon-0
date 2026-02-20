---
id: 002
title: Sentinel Watcher Implementation Plan
stage: plan
date: 2026-02-20
surface: agent
model: claude-opus-4-6
feature: 002-sentinel-watcher
branch: 002-sentinel-watcher
user: human
command: /sp.plan
labels: ["plan", "sentinel", "watcher", "file-system", "bronze-tier", "architecture", "watchdog", "uv"]
links:
  spec: specs/002-sentinel-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-sentinel-watcher/plan.md
  - specs/002-sentinel-watcher/research.md
  - specs/002-sentinel-watcher/data-model.md
  - specs/002-sentinel-watcher/quickstart.md
  - specs/002-sentinel-watcher/contracts/base-watcher-interface.md
tests:
  - Constitution Check: 5/5 principles PASS (pre- and post-design)
  - Research phase: 9 decisions documented with rationale and alternatives
---

## Prompt

sentinel "Develop the technical implementation strategy for the Sentinel (Watcher) component (Bronze Tier)."
GOAL:
Outline the engineering plan to build the 'sentinel' component. This plan must describe the Python project structure, dependency management, class hierarchy, and the event-driven logic for file ingestion into the vault.
CONTEXT:
Base your plan on 'specs/002-sentinel-watcher/spec.md' and the 'Bronze Law' constitution.
PLANNING REQUIREMENTS:
1. ARCHITECTURAL PATTERN:
   - Implement a 'Sentinel' package structure.
   - Define 'sentinel/base.py': Abstract 'BaseWatcher' class with 'start()', 'stop()', and 'on_event()' methods.
   - Define 'sentinel/filesystem.py': 'FileSystemWatcher' implementing 'BaseWatcher' using the 'watchdog' library.
2. INGESTION LOGIC:
   - File Discovery: How to ignore partial writes and temporary files (e.g., '.tmp', '.crdownload').
   - Atomic Move: Move logic from 'source' to 'obsidian-vault/Inbox/'.
   - Sidecar Generation: Template and logic for creating '[filename].md' companion files for binary types (.pdf, .png, etc.) with metadata.
3. ENVIRONMENT & DEPENDENCIES:
   - Use 'uv' for dependency management.
   - Plan the 'requirements.txt' or 'pyproject.toml' (principally 'watchdog' and 'python-dotenv').
   - Use '.env' for configuring the 'WATCH_DIRECTORY' and 'VAULT_INBOX_PATH'.
4. ROBUSTNESS & LOGGING:
   - Graceful shutdown on Ctrl+C.
   - Re-attachment logic if the watch directory is temporarily unavailable.
   - Logging strategy: Standard Python 'logging' to console and optionally to a local 'sentinel.log' (outside the vault).
5. PYTHON BEST PRACTICES:
   - Type hinting, PEP 8, and Pathlib for all paths.
   - Multithreading/Async considerations for the watchdog observer.
OUTPUT:
Create 'specs/sentinel/plan.md' following the SDD standard. Ensure the plan includes a clear directory tree and an incremental implementation roadmap.

## Response snapshot

Created complete implementation plan with 5 Phase 0 research artifacts and Phase 1 design. Key decisions: (1) Use `on_created` events only (not `on_modified`) to avoid duplicates, with size-based stability check (2s); (2) Queue + worker thread architecture to decouple detection from processing; (3) `uv init --package sentinel` with `src/` layout and `hatchling` build backend; (4) `.env` via `python-dotenv` for WATCH_DIRECTORY and VAULT_INBOX_PATH configuration; (5) `BaseWatcher` ABC with `start()`, `stop()`, `on_new_item()` for Silver Tier extensibility; (6) Sidecar `.md` files with YAML frontmatter for non-markdown files. 4-phase implementation roadmap: Foundation → Core Watcher → Sidecar → Robustness. Constitution check 5/5 PASS both pre- and post-design.

## Outcome

- Impact: Full implementation plan created. 5 design artifacts: plan.md, research.md, data-model.md, quickstart.md, base-watcher-interface.md (contract).
- Tests: Constitution Check 5/5 PASS. Research phase: 9 decisions with rationale. No NEEDS CLARIFICATION remaining.
- Files: 5 new files in specs/002-sentinel-watcher/. 1 new directory (contracts/).
- Next prompts: Run /sp.tasks to generate task breakdown from plan. Then /sp.implement to build.
- Reflection: User's detailed planning requirements made this straightforward. The watchdog research confirmed that `on_created` + stability check is the right pattern — avoids the duplicate `on_modified` problem. The Queue+worker thread pattern cleanly separates concerns.

## Evaluation notes (flywheel)

- Failure modes observed: Agent context update script failed (looked for plan at specs/main/plan.md instead of specs/002-sentinel-watcher/plan.md due to branch mismatch). Non-blocking.
- Graders run and results (PASS/FAIL): Constitution Check 5/5 PASS (pre and post design)
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add a sequence diagram in Mermaid format to the plan for the file detection → move → sidecar flow
