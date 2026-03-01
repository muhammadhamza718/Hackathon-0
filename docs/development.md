# Development Guide

## Project Structure

```
Hackathon-0/
├── agents/                  # Agent modules (Bronze + Silver tier logic)
│   ├── __init__.py
│   ├── audit_logger.py      # Append-only audit logging
│   ├── complexity_detector.py # Task complexity scoring
│   ├── constants.py          # Shared constants
│   ├── dashboard_writer.py   # Dashboard.md generation
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── frontmatter.py        # YAML frontmatter parser/builder
│   ├── hitl_gate.py          # Human approval gate
│   ├── inbox_scanner.py      # Inbox file discovery
│   ├── logging_config.py     # Centralized logging
│   ├── plan_manager.py       # Plan file CRUD
│   ├── plan_parser.py        # Plan file parsing
│   ├── reconciler.py         # Session reconciliation
│   ├── task_templates.py     # Task markdown generators
│   ├── utils.py              # Shared utilities
│   ├── validators.py         # Input validation
│   ├── vault_init.py         # Vault initialization
│   └── vault_router.py       # File routing logic
├── sentinel/                # File system watcher (standalone package)
│   └── src/sentinel/
│       ├── base.py           # BaseWatcher ABC
│       ├── cli.py            # CLI entry point
│       ├── config.py         # WatcherConfig dataclass
│       ├── events.py         # Event types
│       ├── filesystem.py     # Watchdog integration
│       ├── health.py         # Health checking
│       └── sidecar.py        # Sidecar file generation
├── tests/                   # Test suite
│   ├── unit/                # Fast isolated tests
│   ├── integration/         # Multi-component tests
│   ├── e2e/                 # Full system tests
│   └── fixtures/            # Shared fixtures
├── docs/                    # Documentation
├── history/                 # PHRs and ADRs
└── specs/                   # SDD feature specs
```

## Adding a New Agent Module

1. Create `agents/my_module.py`
2. Add tests in `tests/unit/test_my_module.py`
3. Import shared constants from `agents.constants`
4. Use `agents.exceptions` for error handling
5. Run tests: `pytest tests/unit/test_my_module.py -v`

## Code Conventions

- Type hints on all public functions
- Docstrings in Google style
- Use `pathlib.Path` instead of string paths
- Use constants from `agents.constants` instead of magic strings
- Raise exceptions from `agents.exceptions`

## Testing Conventions

- Use `tmp_path` fixture for filesystem tests
- Create vault fixtures in `tests/conftest.py` for reuse
- Name test classes `Test<Component>` and methods `test_<behavior>`
