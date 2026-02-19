# Research: Vault Manager — Bronze Tier

**Date**: 2026-02-19 | **Branch**: `001-vault-manager`

## R1: Agent Skill vs. Traditional Code

**Decision**: Implement as an Agent Skill (SKILL.md + references) — not as Python/Node scripts.

**Rationale**:
- The hackathon requires "All AI functionality implemented as Agent Skills."
- Claude Code already has native file tools (Read, Write, Edit, Glob, Bash).
- An Agent Skill is a set of procedural instructions Claude follows; it doesn't need a runtime or package manager.
- The `managing-obsidian-vault` skill already exists with complete SKILL.md and 5 reference files.
- No compilation, no dependencies, no deployment — just markdown instructions.

**Alternatives considered**:
- Python scripts for triage/logging: Rejected — adds dependency, violates "all as Agent Skills" requirement, harder to maintain.
- MCP server for file ops: Rejected — Bronze Tier explicitly excludes MCP invocations.

## R2: File Operations Strategy

**Decision**: Use Claude Code native tools directly (Read, Write, Glob, Bash).

**Rationale**:
- `Read` for file content inspection (frontmatter, body).
- `Write` for creating new files (Dashboard, Handbook, log entries, Needs_Action entries).
- `Glob` for directory listing and file discovery.
- `Bash(mkdir -p)` for folder creation (idempotent).
- `Bash(mv)` for moving files between folders.
- No filesystem MCP needed — native tools are sufficient for all Bronze Tier operations.

**Alternatives considered**:
- filesystem MCP tool: Available but unnecessary complexity at Bronze Tier. Native tools cover all use cases.
- Shell-only approach: Rejected — Claude's native tools provide better error handling and are more explicit.

## R3: Frontmatter Parsing Strategy

**Decision**: Claude Code interprets YAML frontmatter natively by reading file content and parsing `---` delimiters.

**Rationale**:
- Markdown YAML frontmatter follows a well-known pattern: content between first two `---` lines.
- Claude Code is capable of reading a file and extracting structured data from YAML blocks without an external parser.
- No edge cases at Bronze Tier that require a formal YAML library (no nested structures, no anchors/aliases).

**Alternatives considered**:
- Python `pyyaml`: Adds dependency for simple key-value extraction. Overkill.
- Regex extraction: Fragile. Claude's natural language understanding is more robust for this task.

## R4: JSON Log Append Strategy

**Decision**: Read-parse-append-write pattern using Claude Code's Read + Write tools.

**Rationale**:
- Daily log files are small (< 100 entries/day at Bronze Tier).
- Read entire file → parse as JSON array → append entry → write back.
- Atomic write (Write tool overwrites entire file) prevents partial writes.
- No concurrent access at Bronze Tier (single human-triggered agent).

**Alternatives considered**:
- Append-only text log: Simpler but loses structured query capability. JSON array supports future features.
- SQLite: Overkill for Bronze Tier; adds dependency.
- JSONL (one JSON per line): Simpler append but harder to parse as valid JSON. Chose full JSON array for spec compliance.

## R5: Dashboard Rebuild Strategy

**Decision**: Full regeneration on every update (never incremental patch).

**Rationale**:
- Constitution Principle III requires "Always rebuild from actual folder contents — never use cached values."
- Full regeneration eliminates state drift between Dashboard and actual vault.
- At Bronze Tier scale (~100 files), full rebuild is fast (< 5 seconds).
- Template-based approach: read template from dashboard-template.md, fill with live data, write.

**Alternatives considered**:
- Incremental patching (Edit tool): Risk of state drift if a patch is missed. Violates constitution.
- Event-driven updates: Too complex for Bronze Tier. No event system exists.

## R6: HITL Routing Detection

**Decision**: Keyword-based detection for restricted actions, checked during triage.

**Rationale**:
- Bronze Tier has a finite list of restricted actions (send email, payment, social media, delete, external contact).
- Keyword matching against this list during triage is simple and reliable.
- Any match routes to /Pending_Approval/ unconditionally (safety-first approach).
- False positives are acceptable at Bronze Tier — better to over-route than under-route.

**Alternatives considered**:
- LLM classification of intent: Unnecessary complexity. Keywords are sufficient for Bronze Tier.
- User-defined rules: Future Silver Tier feature. Bronze uses hardcoded list.
