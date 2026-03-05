"""Unit tests for agents.vault_init module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.vault_init import InitResult, REQUIRED_DIRS, init_vault, is_vault_initialized


class TestInitResult:
    """Verify frozen InitResult dataclass."""

    def test_total_created(self):
        result = InitResult(
            created_dirs=(Path("a"), Path("b")),
            created_files=(Path("c"),),
            vault_root=Path("/tmp"),
        )
        assert result.total_created == 3

    def test_was_fresh_true(self):
        result = InitResult(
            created_dirs=(Path("a"),),
            created_files=(),
            vault_root=Path("/tmp"),
        )
        assert result.was_fresh is True

    def test_was_fresh_false(self):
        result = InitResult(
            created_dirs=(),
            created_files=(),
            vault_root=Path("/tmp"),
        )
        assert result.was_fresh is False

    def test_frozen(self):
        result = InitResult(
            created_dirs=(),
            created_files=(),
            vault_root=Path("/tmp"),
        )
        with pytest.raises(AttributeError):
            result.vault_root = Path("/other")  # type: ignore[misc]


class TestInitVault:
    def test_creates_all_dirs(self, tmp_path: Path):
        result = init_vault(tmp_path)
        for d in REQUIRED_DIRS:
            assert (tmp_path / d).is_dir()
        assert len(result.created_dirs) >= len(REQUIRED_DIRS)

    def test_creates_dashboard(self, tmp_path: Path):
        result = init_vault(tmp_path)
        assert (tmp_path / "Dashboard.md").exists()
        assert any(f.name == "Dashboard.md" for f in result.created_files)

    def test_idempotent(self, tmp_path: Path):
        init_vault(tmp_path)
        result = init_vault(tmp_path)
        assert result.total_created == 0
        assert result.was_fresh is False

    def test_returns_only_new(self, tmp_path: Path):
        (tmp_path / "Inbox").mkdir()
        result = init_vault(tmp_path)
        dir_names = [c.name for c in result.created_dirs]
        assert "Inbox" not in dir_names

    def test_vault_root_preserved(self, tmp_path: Path):
        result = init_vault(tmp_path)
        assert result.vault_root == tmp_path

    def test_was_fresh_on_new_vault(self, tmp_path: Path):
        result = init_vault(tmp_path)
        assert result.was_fresh is True


class TestIsVaultInitialized:
    def test_true_after_init(self, tmp_path: Path):
        init_vault(tmp_path)
        assert is_vault_initialized(tmp_path) is True

    def test_false_empty_dir(self, tmp_path: Path):
        assert is_vault_initialized(tmp_path) is False

    def test_false_partial(self, tmp_path: Path):
        (tmp_path / "Inbox").mkdir()
        assert is_vault_initialized(tmp_path) is False
