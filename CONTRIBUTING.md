# Contributing Guide

Thank you for contributing to the Personal AI Employee project!

## Development Setup

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager

### Install dependencies
```bash
cd sentinel
uv sync
```

### Run tests
```bash
pytest tests/ -v
```

### Run the sentinel watcher
```bash
cd sentinel
uv run python -m sentinel
```

## Code Standards

- Follow PEP 8 style guidelines
- Add docstrings to all public functions and classes
- Write tests for new functionality
- Keep commits small and focused

## Commit Message Format

```
<type>(<scope>): <short description>

Types: feat, fix, docs, test, refactor, chore
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes with tests
4. Submit a PR with a clear description

## Architecture Overview

This project uses a Bronze–Silver tiered architecture:
- **Bronze Tier**: Vault management, inbox triage
- **Silver Tier**: Multi-step reasoning, HITL approval gates
