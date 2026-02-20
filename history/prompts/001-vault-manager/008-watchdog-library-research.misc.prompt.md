---
id: 008
title: Watchdog Library Research for File System Monitoring
stage: misc
date: 2026-02-20
surface: agent
model: claude-sonnet-4-6
feature: 001-vault-manager
branch: main
user: human
command: research
labels: ["watchdog", "file-monitoring", "python", "research", "plan-input"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - history/prompts/001-vault-manager/008-watchdog-library-research.misc.prompt.md
tests:
  - none
---

## Prompt

Research best practices for using the Python `watchdog` library for file system monitoring. I need concrete technical details for a plan document:

1. **Observer pattern**: How does watchdog's `Observer` + `FileSystemEventHandler` work? What events should we listen for (created vs modified vs moved)?
2. **Stability check for partial writes**: What's the recommended approach to detect that a file is fully written before processing? (e.g., polling file size, checking if file is still locked)
3. **Graceful shutdown**: Best practice for handling Ctrl+C / SIGINT with watchdog's Observer thread.
4. **Non-recursive monitoring**: How to configure watchdog to only watch top-level directory (not subdirectories).
5. **Threading model**: Does watchdog's Observer run in a background thread? What threading considerations matter?
6. **Event deduplication**: Does watchdog fire multiple events per file? How to handle that?

Return concise findings formatted as bullet points under each numbered heading. Focus on Python 3.10+ with type hints.

## Response snapshot

Delivered consolidated research findings across all 6 areas:
1. Observer pattern: Observer is threading.Thread subclass; schedule handler with event_filter for efficiency; prefer on_created + on_moved over on_modified for inbox watching
2. Stability check: No built-in mechanism; recommended file-size polling with stability window (0.5-1.0s); on_closed is Linux-only; sentinel files most reliable when controlling writer
3. Graceful shutdown: Use time.sleep() loop with shutdown flag, not bare join(); signal handlers must be minimal (set bool only); always call stop() before join(timeout=5.0)
4. Non-recursive: observer.schedule(handler, path, recursive=False) is the default; OS-level restriction, no additional filtering needed
5. Threading: Observer is background thread; emitter threads push to queue, dispatcher pulls and calls handlers; handlers run on dispatcher thread so long work blocks processing
6. Deduplication: Known open issue #346; OS-level APIs cause duplicates; must implement debounce by path + time window (1.0s cooldown); combine with stability check for implicit dedup

## Outcome

- Impact: Provides concrete technical decisions for all 6 watchdog integration areas needed in the plan document
- Tests: none (research only)
- Files: PHR created
- Next prompts: Incorporate findings into plan.md for file-watcher feature; implement watcher module with stability check and deduplication
- Reflection: FileClosedEvent (on_closed) being Linux-only is a critical cross-platform constraint; the stability-polling approach is the safe universal solution

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A (research task)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
