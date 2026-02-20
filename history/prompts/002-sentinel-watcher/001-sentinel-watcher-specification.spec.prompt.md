---
id: 001
title: Sentinel Watcher Specification
stage: spec
date: 2026-02-20
surface: agent
model: claude-opus-4-6
feature: 002-sentinel-watcher
branch: 002-sentinel-watcher
user: human
command: /sp.specify
labels: ["spec", "sentinel", "watcher", "file-system", "bronze-tier", "perception-layer"]
links:
  spec: specs/002-sentinel-watcher/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-sentinel-watcher/spec.md
  - specs/002-sentinel-watcher/checklists/requirements.md
tests:
  - Spec Quality Checklist: 12/12 PASS (all items validated)
  - No [NEEDS CLARIFICATION] markers (0 remaining)
  - Content Quality: PASS (no implementation details in FR/SC)
  - Success Criteria technology-agnostic: PASS
---

## Prompt

sentinel "Design the first Sentinel (Watcher) script for the Personal AI Employee (Bronze Tier)."
GOAL:
Define the technical specification for the sensation layer. This component is an external Python script that monitors a "Source" directory and automatically moves work items into the Obsidian Vault's '/Inbox/' folder.
CONSTRAINTS (BRONZE TIER):
1. Written in Python 3.10+.
2. Uses standard libraries or well-known packages like 'watchdog'.
3. Follows the 'Bronze Law' Constitution (Local-First, No External API Leakage).
4. Treatment: The sentinel is a "dumb" feeder — it does not perform triage (that's the agent's job).
REQUIREMENTS TO SPECIFY:
1. CORE MONITORING (FileSystem):
   - Monitor a specified local directory (e.g., 'C:/Users/User/Desktop/AI_Employee_Drop/').
   - Detect new files (.md, .txt, .pdf, .jpg).
   - Atomic Move: Ensure file is fully written before processing.
2. INBOX INGESTION:
   - Move detected files to 'obsidian-vault/Inbox/'.
   - Sidecar Generation: For non-markdown files (like .pdf), generate a companion '.md' file with basic metadata (timestamp, original_name, source_path) to allow the agent to "see" it.
3. ROBUSTNESS:
   - Handle directory missing/access errors.
   - Ignore temporary files (e.g., .tmp, .~lock).
   - Logging: Simple console logging of file discovery and movement.
4. BASE CLASS (Future-Proofing):
   - Define a 'BaseWatcher' abstract class to allow later implementation of Gmail/WhatsApp watchers in Silver Tier.

## Response snapshot

Created full specification for the Sentinel File System Watcher (002-sentinel-watcher). Spec covers 4 user stories (P1-P4): (1) automatic file ingestion from drop folder with 5-second detection SLA, (2) sidecar .md generation for non-markdown files with metadata (filename, source path, file size, ISO-8601 timestamp), (3) robust error handling — ignore temp files, handle missing dirs, survive I/O errors, (4) BaseWatcher abstract class with start()/stop()/on_new_item() for Silver Tier extensibility. 17 functional requirements, 8 measurable success criteria, 5 edge cases (filename collision, mid-write detection, subdirectories, unsupported extensions, interrupted transfers). All technology-agnostic in FR/SC sections. Assumptions section documents Python 3.10+ and watchdog as user-provided constraints. Quality checklist 12/12 PASS.

## Outcome

- Impact: Full specification created for sentinel-watcher feature. Ready for /sp.plan or /sp.clarify.
- Tests: Quality checklist 12/12 PASS. Zero [NEEDS CLARIFICATION] markers. Content quality validated.
- Files: 2 new files (spec.md, checklists/requirements.md). 1 new directory (history/prompts/002-sentinel-watcher/).
- Next prompts: Run /sp.plan to create architectural plan. Or /sp.clarify to refine requirements.
- Reflection: User provided exceptionally clear requirements with explicit constraints, making all functional requirements derivable without clarification. The Bronze Law Constitution provided strong guardrails (FR-010, FR-011).

## Evaluation notes (flywheel)

- Failure modes observed: None. All spec sections completed on first pass.
- Graders run and results (PASS/FAIL): Quality checklist 12/12 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add sequence diagram for file detection → stability check → move → sidecar flow in /sp.plan
