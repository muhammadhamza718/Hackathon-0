# Testing Guide

## Running Tests

### All tests
```bash
pytest tests/ -v
```

### Unit tests only
```bash
pytest tests/unit/ -v
```

### Integration tests
```bash
pytest tests/integration/ -v
```

### E2E tests
```bash
pytest tests/e2e/ -v
```

### Single test file
```bash
pytest tests/unit/test_vault_router.py -v
```

## Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── test_utils.py
│   ├── test_constants.py
│   ├── test_validators.py
│   ├── test_vault_router.py
│   ├── test_dashboard_writer.py
│   ├── test_plan_parser.py
│   ├── test_plan_manager.py
│   ├── test_hitl_gate.py
│   ├── test_reconciler.py
│   └── test_logging_config.py
├── integration/             # Multi-component workflows
│   └── test_vault_workflow.py
├── e2e/                     # Full system tests
└── fixtures/                # Shared test fixtures
    └── vault_fixture.py
```

## Writing Tests

### Conventions
- Test classes named `Test<Component>`
- Test methods named `test_<behavior>`
- Use `pytest.fixture` for setup
- Use `tmp_path` for file system tests

### Example
```python
class TestMyFeature:
    def test_happy_path(self, tmp_path):
        # Arrange
        ...
        # Act
        result = my_function(input)
        # Assert
        assert result == expected
```
