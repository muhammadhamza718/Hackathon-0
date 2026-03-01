"""Unit tests for agents.vault_init module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.vault_init import REQUIRED_DIRS, init_vault, is_vault_initialized


class TestInitVault:
    def test_creates_all_dirs(self, tmp_path: Path):
        created = init_vault(tmp_path)
        for d in REQUIRED_DIRS:
            assert (tmp_path / d).is_dir()
        assert len(created) >= len(REQUIRED_DIRS)

    def test_creates_dashboard(self, tmp_path: Path):
        init_vault(tmp_path)
        assert (tmp_path / "Dashboard.md").exists()

    def test_idempotent(self, tmp_path: Path):
        init_vault(tmp_path)
        created = init_vault(tmp_path)
        assert len(created) == 0

    def test_returns_only_new(self, tmp_path: Path):
        (tmp_path / "Inbox").mkdir()
        created = init_vault(tmp_path)
        names = [c.name for c in created]
        assert "Inbox" not in names


class TestIsVaultInitialized:
    def test_true_after_init(self, tmp_path: Path):
        init_vault(tmp_path)
        assert is_vault_initialized(tmp_path) is True

    def test_false_empty_dir(self, tmp_path: Path):
        assert is_vault_initialized(tmp_path) is False

    def test_false_partial(self, tmp_path: Path):
        (tmp_path / "Inbox").mkdir()
        assert is_vault_initialized(tmp_path) is False
