# Implementation Plan: Vault Manager — Bronze Tier

**Branch**: `001-vault-manager` | **Date**: 2026-02-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-vault-manager/spec.md`

## Summary

Build a local-only Obsidian Vault management system operating as an Agent Skill. The system handles vault initialization, inbox triage with priority classification, live dashboard generation, task lifecycle management, audit logging, and HITL approval routing. All operations are file-based, use Claude Code's native tools (Read, Write, Edit, Glob, Bash), and produce immutable audit trails. No external APIs, no network calls, no autonomous loops.

## Technical Context

**Language/Version**: Agent Skill (Markdown procedural instructions + Claude Code tool calls). No compiled language — Claude Code interprets SKILL.md and executes via native tools.
**Primary Dependencies**: Claude Code native tools (Read, Write, Edit, Glob, Bash for `mkdir`/`mv`/`ls`), Obsidian (passive GUI layer).
**Storage**: Local file system — Markdown files + daily JSON log files in vault directory.
**Testing**: Manual verification via test scenarios in `tests/scenarios.md`. End-to-end green path test defined below.
**Target Platform**: Windows 10+ (user's local machine), Claude Code CLI.
**Project Type**: Agent Skill (not a traditional software project — no src/tests structure).
**Performance Goals**: Vault initialization < 5 seconds. Triage of 10 files < 30 seconds. Dashboard rebuild < 5 seconds.
**Constraints**: Local-only, no network, Bronze Tier autonomy limits, all operations logged.
**Scale/Scope**: Single user, single vault, ~100 files max at Bronze Tier.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Verification |
|-----------|--------|--------------|
| I. Local-First Privacy | PASS | All operations are local file read/write. No network calls. No cloud services. Secrets excluded from vault files. |
| II. HITL Safety | PASS | Zero external actions. Payment/email/social items routed to /Pending_Approval/. Human must approve before any external step. |
| III. Vault Architectural Integrity | PASS | Required folders: /Inbox, /Needs_Action, /Done, /Logs. Dashboard.md rebuilt from actual state. Company_Handbook.md read before every triage. ISO-8601 timestamps. |
| IV. Meticulous Audit Logging | PASS | Every operation logged to /Logs/YYYY-MM-DD.json. Schema: {timestamp, action, source_file, details, result}. Errors logged before reporting. |
| V. Operational Boundaries | PASS | In scope: read, summarize, organize, plan, log. Out of scope: external APIs, browser automation, autonomous loops, MCP servers. |

**Gate result: PASS — proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/001-vault-manager/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity schemas
├── quickstart.md        # Phase 1: setup guide
├── contracts/           # Phase 1: operation contracts
│   └── operations.md    # Vault operation definitions
└── tasks.md             # Phase 2 output (/sp.tasks)
```

### Source Code (repository root)

```text
.agents/skills/managing-obsidian-vault/
├── SKILL.md                        # Core procedures (already exists)
├── references/
│   ├── vault-structure.md          # Folder/file schema (exists)
│   ├── triage-rules.md             # Priority keywords (exists)
│   ├── dashboard-template.md       # Dashboard.md template (exists)
│   ├── handbook-template.md        # Company_Handbook.md template (exists)
│   └── log-format.md               # Audit log JSON schema (exists)
└── tests/
    └── scenarios.md                # Test scenarios (exists)
```

**Structure Decision**: This is an Agent Skill, not a traditional codebase. The "source code" is the SKILL.md file and its references, which Claude Code reads and follows as procedural instructions. No compiled code, no `src/` directory.

## Component Architecture

### Module Decomposition

Five logical modules, each mapping to a SKILL.md procedure:

| Module | SKILL.md Section | Reference Files | Priority |
|--------|-----------------|-----------------|----------|
| **M1: Vault Initializer** | Section 1 | vault-structure.md, dashboard-template.md, handbook-template.md | P1 |
| **M2: Inbox Scanner & Parser** | Section 2 (steps 1-3) | triage-rules.md | P1 |
| **M3: Priority & Routing Engine** | Section 2 (steps 4-6) + Section 6 | triage-rules.md, handbook-template.md | P1 |
| **M4: Dashboard Generator** | Section 3 | dashboard-template.md | P2 |
| **M5: Audit Logger** | Section 5 | log-format.md | P1 (cross-cutting) |

### Module Dependencies

```text
M5 (Audit Logger) ← used by ALL modules
M1 (Vault Init) ← must run first, no other dependencies
M2 (Scanner) → M3 (Router) → M4 (Dashboard) [sequential pipeline]
M3 (Router) → M6 (HITL) [conditional, only for restricted items]
```

### M1: Vault Initializer

**Purpose**: Create folder structure and default files from templates.

**Strategy**:
1. Use `Bash(mkdir -p)` to create folders idempotently.
2. Use `Glob` to check which files already exist.
3. Use `Write` to create Dashboard.md and Company_Handbook.md from reference templates only if they don't exist.
4. Use `Glob` + `Read` for health check verification.
5. Log initialization via M5.

**Key decisions**:
- Bronze Tier folders: /Inbox, /Needs_Action, /Done, /Logs (required). /Pending_Approval (for HITL routing). /Plans, /Approved optional — create only if not conflicting.
- Idempotent: never overwrite existing files.

### M2: Inbox Scanner & Parser

**Purpose**: Read each file in /Inbox/, extract frontmatter and body text.

**Strategy**:
1. Use `Glob("Inbox/*.md")` to list files. Also `Glob("Inbox/*.txt")` for plain text.
2. Use `Read` for each file.
3. Parse YAML frontmatter: detect `---` delimiters, extract `type`, `from`, `date`, `subject` fields.
4. If no frontmatter: treat as `type: file_drop`, log warning.
5. If file is unreadable/malformed: log error via M5, skip file, continue.
6. Pass parsed content to M3.

**Frontmatter parsing approach**: Split file content on first two `---` lines. Content between them is YAML frontmatter. Content after is body. This is done by Claude Code reading the file and interpreting the structure — no external YAML parser needed.

### M3: Priority & Routing Engine

**Purpose**: Classify items by priority and route to correct folder.

**Strategy**:
1. Read `Company_Handbook.md` FIRST (constitution requirement III).
2. Extract priority keywords from handbook. Fall back to defaults from triage-rules.md if handbook is missing.
3. Scan subject + body text for keyword matches (case-insensitive).
4. Apply classification hierarchy: #high keywords → #high, #medium keywords → #medium, else → #low.
5. Determine actionable vs. informational (see triage-rules.md criteria).
6. **If actionable**: Create entry file in /Needs_Action/ via `Write`.
7. **If informational**: Move file to /Done/ via `Bash(mv)`.
8. **If restricted action detected** (payment, email, etc.): Route to /Pending_Approval/ via M6.
9. Log each decision via M5 with rationale in `details`.

### M4: Dashboard Generator

**Purpose**: Rebuild Dashboard.md from actual vault state.

**Strategy (read-then-write pattern)**:
1. Use `Glob` to count files in each folder (never cache).
2. Use `Read` on each /Needs_Action/ file to extract priority and date for sorting.
3. Use `Read` on recent /Done/ files (last 10 by modification date) for Recently Completed.
4. Compute Alerts: filter /Needs_Action/ items where priority=#high AND age > 24h.
5. Assemble Dashboard content using template from dashboard-template.md.
6. Use `Write` to overwrite Dashboard.md with fresh content.
7. Log via M5 with action: `update_dashboard`.

**Important**: Always rebuild entire Dashboard. Never patch — full regeneration ensures consistency.

### M5: Audit Logger

**Purpose**: Append-only daily JSON logging.

**Strategy (read-parse-append-write)**:
1. Compute today's filename: `/Logs/YYYY-MM-DD.json`.
2. Try `Read` on the file:
   - If file doesn't exist: initialize content as `[]`.
   - If file exists: parse JSON array.
   - If JSON is malformed: backup as `.bak`, start fresh `[]`, log the error as first entry.
3. Append new entry object to array.
4. Use `Write` to write entire array back (2-space indented JSON).

**Concurrency note**: At Bronze Tier, operations are sequential (human-triggered, single agent). No lock files needed. If future tiers add concurrency, upgrade to file locking.

### M6: HITL Approval Router

**Purpose**: Route restricted actions to /Pending_Approval/.

**Strategy**:
1. Detect restricted keywords in triaged content: "send email", "payment", "transfer", "post to", "delete permanently", "contact".
2. Create structured approval request file in /Pending_Approval/ via `Write`.
3. Log routing via M5.
4. STOP — do not proceed with the restricted action.

## Verification Strategy

### Incremental Module Tests

| Test | Module | Input | Expected Output |
|------|--------|-------|-----------------|
| T1: Init empty vault | M1 | Empty directory | 4+ folders + 2 core files created, health check passes |
| T2: Init idempotent | M1 | Already-initialized vault | No files modified, "vault healthy" reported |
| T3: Parse with frontmatter | M2 | File with valid YAML frontmatter | type, from, date, subject extracted correctly |
| T4: Parse without frontmatter | M2 | File with no `---` delimiters | Treated as file_drop, warning logged |
| T5: Classify #high | M3 | File with "urgent" and "invoice" | Classified #high, routed to /Needs_Action/ |
| T6: Classify informational | M3 | Newsletter with "No action required" | Routed to /Done/ |
| T7: HITL routing | M3+M6 | File mentioning "send email" | Routed to /Pending_Approval/, action halted |
| T8: Dashboard rebuild | M4 | 2 items in /Needs_Action/, 3 in /Done/ | Dashboard shows correct counts, sorted properly |
| T9: Log append | M5 | Two operations in sequence | Log file has 2 entries in valid JSON array |
| T10: Malformed log recovery | M5 | Corrupted JSON in log file | .bak created, fresh log started, error logged |

### Green Path End-to-End Test

**Scenario**: Full lifecycle from file drop to completion.

1. Initialize vault (M1) → verify folders + files
2. Place 3 test files in /Inbox/ (urgent email, meeting request, newsletter)
3. Run triage (M2+M3) → verify routing (2 to /Needs_Action/, 1 to /Done/)
4. Verify Dashboard (M4) → 2 pending, 1 done, correct stats
5. Mark urgent task complete (Task Completion) → verify file moves, Dashboard update
6. Check audit log (M5) → verify all operations logged with correct schema
7. Verify final Dashboard → 1 pending, 2 done, stats match

## Error & Recovery Strategy

| Error | Module | Recovery | Impact |
|-------|--------|----------|--------|
| Missing frontmatter | M2 | Treat as file_drop, log warning, continue | Low — graceful degradation |
| Unreadable file | M2 | Log error, skip file, continue to next | Low — one file skipped |
| Malformed log JSON | M5 | Backup .bak, create fresh log, log error first | Low — history preserved in backup |
| Missing Company_Handbook.md | M3 | Use built-in defaults from triage-rules.md, log warning | Medium — may classify differently |
| Partial folder structure | M1 | Create only missing items, preserve existing | None — idempotent |
| Dashboard write failure | M4 | Log error, report to user, continue other operations | Medium — stale dashboard until next rebuild |

**Principle**: Never halt the entire operation for a single-file error. Log, warn, continue.

## Complexity Tracking

> No Constitution Check violations. No complexity justifications needed.

## Implementation Order

1. **M5: Audit Logger** — cross-cutting dependency, needed by all other modules
2. **M1: Vault Initializer** — foundation, no other module works without it
3. **M2: Inbox Scanner** — parse input files
4. **M3: Priority & Routing Engine** — classify and route (depends on M2)
5. **M4: Dashboard Generator** — rebuild state view (depends on M3 output)
6. **M6: HITL Router** — conditional branch from M3

This order ensures each module can be tested independently as it's built, and no module depends on one that hasn't been implemented yet.
