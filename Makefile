.PHONY: test test-unit test-integration test-e2e test-cov lint format typecheck install clean help

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Run ruff linter"
	@echo "  make format         - Run ruff formatter"
	@echo "  make typecheck      - Run mypy type checker"
	@echo "  make check          - Run lint + typecheck + tests"
	@echo "  make clean          - Remove cache files"

install:
	cd sentinel && uv sync

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-e2e:
	pytest tests/e2e/ -v

test-cov:
	pytest tests/ -v --cov=agents --cov=sentinel --cov-report=term-missing

lint:
	cd sentinel && uv run ruff check .

format:
	cd sentinel && uv run ruff format .

typecheck:
	mypy agents/ sentinel/src/sentinel/

check: lint typecheck test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
