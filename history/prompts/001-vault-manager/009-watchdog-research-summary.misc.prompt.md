---
id: 009
title: Watchdog Research Summary for Plan Decisions
stage: misc
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 001-vault-manager
branch: main
user: human
command: research
labels: ["watchdog", "file-monitoring", "python", "research-summary", "plan-input"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/001-vault-manager/009-watchdog-research-summary.misc.prompt.md
tests:
  - none
---

## Prompt

Please provide your complete research findings on the Python watchdog library. I need the technical details for all 6 areas you researched: (1) Observer pattern - which events to use, (2) Stability check for partial writes, (3) Graceful shutdown with SIGINT, (4) Non-recursive monitoring, (5) Threading model, (6) Event deduplication. Please output everything you found, formatted as bullet points under each heading.

## Response snapshot

Delivered comprehensive technical findings across all 6 watchdog integration areas with code examples:

1. Observer pattern: Observer is threading.Thread subclass; use on_created + on_moved (not on_modified) for inbox watching; event_filter parameter in schedule() reduces overhead; on_closed is Linux-only
2. Stability check: File-size polling with 0.5-1.0s interval and max timeout; PermissionError retry on Windows; sentinel .done files when controlling writer; concrete wait_for_stable() implementation provided
3. Graceful shutdown: time.sleep(1.0) loop with shutdown_requested flag; signal.signal for SIGINT/SIGTERM; always stop() before join(timeout=5.0); never use bare join() as sole blocker
4. Non-recursive: recursive=False is the default in schedule(); OS-level restriction, no handler filtering needed
5. Threading: Emitter threads (one per watch) push to queue; dispatcher thread pulls and calls handlers under lock; handlers block processing if slow -- offload to worker queue
6. Deduplication: Known issue #346; 2-4 duplicates per operation; debounce by path + time.monotonic() with 1.0s cooldown; prune _last_seen dict periodically

Key architectural takeaway: Combine on_created+on_moved listening, 1s debounce cooldown, and file-size stability polling for a robust cross-platform inbox watcher.

## Outcome

- Impact: Complete technical reference for watchdog integration decisions in plan document
- Tests: none (research summary)
- Files: PHR 009 created
- Next prompts: Use findings to update plan.md with watchdog integration architecture
- Reflection: Consolidating research into actionable decisions with code examples provides direct plan-ready input

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A -- research output
- Prompt variant (if applicable): follow-up summary request after initial research
- Next experiment (smallest change to try): Apply findings to plan.md watchdog section
