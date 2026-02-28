"""Unit tests for agents.validators module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.validators import (
    has_frontmatter,
    is_safe_filename,
    is_valid_plan_id,
    is_valid_priority,
    is_valid_status,
    validate_vault_structure,
)


class TestIsValidPlanId:
    def test_valid(self):
        assert is_valid_plan_id("PLAN-2026-001") is True

    def test_invalid_no_prefix(self):
        assert is_valid_plan_id("2026-001") is False

    def test_invalid_short_num(self):
        assert is_valid_plan_id("PLAN-2026-01") is False

    def test_invalid_format(self):
        assert is_valid_plan_id("PLAN-XX-001") is False


class TestIsValidPriority:
    def test_valid_values(self):
        for p in ("high", "medium", "low"):
            assert is_valid_priority(p) is True

    def test_invalid(self):
        assert is_valid_priority("urgent") is False


class TestIsValidStatus:
    def test_valid_values(self):
        for s in ("draft", "active", "blocked", "complete", "approved", "rejected"):
            assert is_valid_status(s) is True

    def test_invalid(self):
        assert is_valid_status("unknown") is False


class TestHasFrontmatter:
    def test_with_frontmatter(self):
        assert has_frontmatter("---\ntitle: X\n---\n# Body") is True

    def test_without(self):
        assert has_frontmatter("# Just a heading") is False


class TestIsSafeFilename:
    def test_valid(self):
        assert is_safe_filename("task-001.md") is True

    def test_path_traversal(self):
        assert is_safe_filename("../etc/passwd") is False

    def test_dotfile(self):
        assert is_safe_filename(".hidden") is False

    def test_empty(self):
        assert is_safe_filename("") is False

    def test_backslash(self):
        assert is_safe_filename("a\\b") is False


class TestValidateVaultStructure:
    def test_valid_vault(self, tmp_path: Path):
        for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval",
                   "Approved", "Rejected"):
            (tmp_path / d).mkdir()
        assert validate_vault_structure(tmp_path) == []

    def test_missing_dirs(self, tmp_path: Path):
        errors = validate_vault_structure(tmp_path)
        assert len(errors) >= 1
        assert "Missing required directory" in errors[0]
