"""Unit tests for agents.validators module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.validators import (
    ValidationResult,
    has_frontmatter,
    is_safe_filename,
    is_valid_plan_id,
    is_valid_priority,
    is_valid_status,
    is_valid_tier,
    validate_vault_structure,
)


class TestValidationResult:
    """Verify frozen ValidationResult dataclass and factories."""

    def test_ok_factory(self):
        result = ValidationResult.ok()
        assert result.valid is True
        assert result.errors == ()
        assert result.error_count == 0

    def test_fail_factory(self):
        result = ValidationResult.fail(["error 1", "error 2"])
        assert result.valid is False
        assert result.error_count == 2

    def test_frozen(self):
        result = ValidationResult.ok()
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]

    def test_errors_are_tuple(self):
        result = ValidationResult.fail(["a"])
        assert isinstance(result.errors, tuple)


class TestIsValidPlanId:
    @pytest.mark.parametrize(
        "plan_id,expected",
        [
            ("PLAN-2026-001", True),
            ("PLAN-2026-999", True),
            ("2026-001", False),
            ("PLAN-2026-01", False),
            ("PLAN-XX-001", False),
            ("", False),
        ],
    )
    def test_plan_id(self, plan_id: str, expected: bool):
        assert is_valid_plan_id(plan_id) is expected


class TestIsValidPriority:
    @pytest.mark.parametrize(
        "priority,expected",
        [
            ("critical", True),
            ("high", True),
            ("medium", True),
            ("low", True),
            ("urgent", False),
            ("", False),
        ],
    )
    def test_priority(self, priority: str, expected: bool):
        assert is_valid_priority(priority) is expected


class TestIsValidStatus:
    @pytest.mark.parametrize(
        "status,expected",
        [
            ("draft", True),
            ("active", True),
            ("complete", True),
            ("cancelled", True),
            ("unknown", False),
        ],
    )
    def test_status(self, status: str, expected: bool):
        assert is_valid_status(status) is expected


class TestIsValidTier:
    @pytest.mark.parametrize(
        "tier,expected",
        [
            ("bronze", True),
            ("silver", True),
            ("gold", True),
            ("platinum", False),
        ],
    )
    def test_tier(self, tier: str, expected: bool):
        assert is_valid_tier(tier) is expected


class TestHasFrontmatter:
    def test_with_frontmatter(self):
        assert has_frontmatter("---\ntitle: X\n---\n# Body") is True

    def test_without(self):
        assert has_frontmatter("# Just a heading") is False


class TestIsSafeFilename:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("task-001.md", True),
            ("my file.md", True),
            ("../etc/passwd", False),
            (".hidden", False),
            ("", False),
            ("a\\b", False),
            ("a/b", False),
        ],
    )
    def test_safety(self, name: str, expected: bool):
        assert is_safe_filename(name) is expected


class TestValidateVaultStructure:
    def test_valid_vault(self, tmp_path: Path):
        for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval",
                   "Approved", "Rejected", "Plans", "Logs"):
            (tmp_path / d).mkdir()
        result = validate_vault_structure(tmp_path)
        assert result.valid is True
        assert result.error_count == 0

    def test_missing_dirs(self, tmp_path: Path):
        result = validate_vault_structure(tmp_path)
        assert result.valid is False
        assert result.error_count >= 1
        assert "Missing required directory" in result.errors[0]

    def test_partial_vault(self, tmp_path: Path):
        (tmp_path / "Inbox").mkdir()
        result = validate_vault_structure(tmp_path)
        assert result.valid is False
        assert result.error_count > 0
