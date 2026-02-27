# Architecture Overview

## System Design

The Personal AI Employee is built on a Bronze–Silver tiered architecture using an Obsidian Vault as the single source of truth.

```
┌─────────────────────────────────────────────┐
│              Silver Tier                     │
│  Reasoning Loop + Plan Persistence + HITL    │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │           Bronze Tier                │   │
│  │  Vault Manager + Inbox Triage        │   │
│  │  Sentinel Watcher + Dashboard        │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## Components

### Bronze Tier

| Component | Responsibility |
|-----------|----------------|
| Vault Manager | Inbox triage, file routing, dashboard updates |
| Sentinel Watcher | File system monitoring via watchdog |
| Audit Logger | Append-only log in `/Logs/` |

### Silver Tier

| Component | Responsibility |
|-----------|----------------|
| Reasoning Agent | Multi-step planning and execution |
| Plan Manager | YAML-fronted Plan files in `/Plans/` |
| HITL Gate | Blocks external actions pending human approval |
| Session Reconciler | Resumes incomplete plans on startup |

## Data Flow

```
Inbox → Sentinel detects → Vault Manager triages
     → Simple task → Needs_Action
     → Complex task → Silver Tier creates Plan
                   → HITL step → Pending_Approval
                   → Approved → Execute → Done
                   → Rejected → Rejected dir
```

## Vault Directory Structure

```
vault/
├── Inbox/              # New incoming tasks
├── Needs_Action/       # Triaged tasks awaiting execution
├── Done/               # Completed tasks
├── Pending_Approval/   # HITL gate queue
├── Approved/           # Human-approved actions
├── Rejected/           # Human-rejected actions
├── Plans/              # Silver Tier plan files
├── Logs/               # Audit logs
└── Dashboard.md        # Live status overview
```
