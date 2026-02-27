# Specs Directory

This directory contains the Spec-Driven Development (SDD) artifacts for each feature.

## Structure

```
specs/
├── 001-vault-manager/     # Bronze Tier vault management
│   ├── spec.md            # Feature requirements
│   ├── plan.md            # Architecture decisions
│   └── tasks.md           # Testable implementation tasks
├── 002-sentinel-watcher/  # File system watcher
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
└── 003-silver-reasoning/  # Silver Tier reasoning loop
    ├── spec.md
    ├── plan.md
    └── tasks.md
```

## SDD Workflow

1. **`/sp.specify`** — Create or update the feature spec from natural language
2. **`/sp.plan`** — Generate architecture and design plan
3. **`/sp.tasks`** — Break the plan into testable implementation tasks
4. **`/sp.implement`** — Execute the tasks
5. **`/sp.phr`** — Record the session as a Prompt History Record

## Artifact Descriptions

| File | Purpose |
|------|---------|
| `spec.md` | User stories, acceptance criteria, constraints |
| `plan.md` | Tech stack, architecture decisions, file structure |
| `tasks.md` | TDD task list with test cases |
