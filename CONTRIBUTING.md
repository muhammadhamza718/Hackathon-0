# Contributing Guide

Thank you for contributing to the Personal AI Employee project!

## Development Setup

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Git for version control

### Install dependencies
```bash
cd sentinel
uv sync
```

### Run tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/unit/test_gold_social_bridge.py -v

# Run with coverage
pytest tests/ --cov=agents --cov-report=html
```

### Run the sentinel watcher
```bash
cd sentinel
uv run python -m sentinel
```

## Code Standards

### Style Guidelines
- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Add docstrings to all public functions and classes (Google style)
- Keep functions under 50 lines when possible
- Keep modules under 500 lines when possible

### Testing Requirements
- Write tests for all new functionality
- Achieve 80%+ code coverage for new modules
- Use pytest fixtures for common test data
- Mock external dependencies (Odoo, Browser MCP)

### Code Review Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Coverage meets threshold
- [ ] Docstrings are complete
- [ ] Type hints are accurate
- [ ] No hardcoded secrets or tokens

## Commit Message Format

```
<type>(<scope>): <short description>

Types: feat, fix, docs, test, refactor, chore
Scope: social, briefing, loop, odoo, vault, etc.

Examples:
feat(social): add hashtag suggestion engine
fix(briefing): correct revenue calculation
docs(loop): add state diagram documentation
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes with tests
4. Run full test suite: `pytest tests/ -v`
5. Submit a PR with a clear description

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Coverage maintained

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

## Architecture Overview

### Tier Structure
- **Bronze**: Vault management, inbox triage
- **Silver**: Reasoning loop, plan persistence
- **Gold**: Full autonomy (Odoo, social media, briefings)

### Key Modules
- `agents/gold/`: Gold Tier autonomous features
- `agents/silver/`: Silver Tier reasoning
- `sentinel/`: Vault watchers and triggers
- `tests/`: Unit and integration tests

## Gold Tier Development

### Adding New Features
1. Create module in `agents/gold/`
2. Add tests in `tests/unit/test_gold_*.py`
3. Update `agents/gold/__init__.py` exports
4. Document in README.md Gold Tier section

### Safety Gates
All Gold Tier external actions must:
- Route through `/Pending_Approval/` for HITL
- Include rationale and risk assessment
- Provide rollback path
- Log to `/Logs/YYYY-MM-DD.json`

## Questions?
Open an issue for clarification on any topic.

This project uses a Bronze–Silver tiered architecture:
- **Bronze Tier**: Vault management, inbox triage
- **Silver Tier**: Multi-step reasoning, HITL approval gates
