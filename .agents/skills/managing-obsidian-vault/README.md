# Managing Obsidian Vault — Agent Skill

Bronze Tier procedural skill for operating an Obsidian Vault as the single source of truth for a Digital FTE (Personal AI Employee).

## Overview

This skill teaches Claude Code how to manage an Obsidian Vault as an executive assistant. It covers vault initialization, inbox triage with priority classification, live dashboard generation, task lifecycle management, immutable audit logging, and human-in-the-loop approval routing.

**Tier**: Bronze (local-only, no external APIs, no autonomous loops)
**Agent**: `obsidian-vault-agent` (defined in `.claude/agents/obsidian-vault-agent.md`)

## File Structure

```
managing-obsidian-vault/
├── SKILL.md                          # Core procedures (7 sections)
├── README.md                         # This file
├── references/
│   ├── vault-structure.md            # Folder/file schema with tier markers
│   ├── triage-rules.md               # Priority keywords and classification logic
│   ├── dashboard-template.md         # Dashboard.md template with empty states
│   ├── handbook-template.md          # Company_Handbook.md Bronze Tier template
│   └── log-format.md                 # Audit log JSON schema and examples
└── tests/
    └── scenarios.md                  # Test scenarios (Easy, Medium, Hard, Edge-case)
```

## Procedures (SKILL.md)

| Section | Procedure | Trigger |
|---------|-----------|---------|
| 1 | Vault Initialization | "Set up my vault" |
| 2 | Inbox Triage | "Process my inbox" |
| 3 | Dashboard Update | After every triage, completion, or state change |
| 4 | Task Completion | "I finished [task]" |
| 5 | Audit Logging | Every file operation (automatic) |
| 6 | Approval Routing | Restricted action detected during triage |
| 7 | Log Review | "What happened today?" |

## Vault Structure (Bronze Tier)

```
vault-root/
├── Inbox/              # [Bronze] Raw incoming items
├── Needs_Action/       # [Bronze] Triaged actionable items
├── Done/               # [Bronze] Completed/informational archive
├── Pending_Approval/   # [Bronze] Items awaiting human approval
├── Logs/               # [Bronze] Daily JSON audit logs
├── Dashboard.md        # [Bronze] Live status overview
└── Company_Handbook.md # [Bronze] Rules and autonomy boundaries
```

Folders marked `[Silver+]` (Plans/, Approved/) are not created at Bronze Tier.

## Installation

No installation required. This is an Agent Skill — Claude Code reads SKILL.md and follows the procedures using its native tools (Read, Write, Edit, Glob, Bash).

**Prerequisites**:
- Claude Code CLI configured
- Obsidian (optional, for GUI viewing)
- A target directory for the vault

**Usage**: Invoke via the `obsidian-vault-agent` or trigger keywords (vault, inbox, triage, dashboard).

## Testing

See `tests/scenarios.md` for structured test scenarios:

- **Initialize Empty Vault** (Easy) — Verify 5 folders + 2 core files
- **Triage Three Inbox Files** (Medium) — Verify priority classification and routing
- **Full Lifecycle** (Hard) — Init, triage, complete, review in sequence
- **Malformed Inbox File** (Edge-case) — Missing frontmatter handling
- **Bronze Tier Full Lifecycle** (Medium) — End-to-end Bronze compliance verification

## Constitution Compliance

This skill operates under the Bronze Law Constitution (`.specify/memory/constitution.md`):

- **Principle I**: Local-first. All data stays in the vault. No network calls.
- **Principle II**: Human-in-the-loop. Restricted actions halt and await approval.
- **Principle III**: Vault integrity. Dashboard rebuilt from actual state, never cached.
- **Principle IV**: Audit logging. Every operation logged, never skipped.
- **Principle V**: Bronze boundaries. No external APIs, no autonomous loops.
