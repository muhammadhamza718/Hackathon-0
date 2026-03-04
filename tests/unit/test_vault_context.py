"""Unit tests for agents.vault_context module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.audit_logger import read_log
from agents.exceptions import VaultStructureError
from agents.vault_context import vault_session
from agents.vault_init import init_vault


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    init_vault(tmp_path)
    return tmp_path


class TestVaultSession:
    def test_yields_vault_root(self, vault: Path):
        with vault_session(vault) as v:
            assert v == vault

    def test_logs_session_start(self, vault: Path):
        with vault_session(vault):
            pass
        log = read_log(vault)
        assert "session_start" in log

    def test_logs_session_end(self, vault: Path):
        with vault_session(vault):
            pass
        log = read_log(vault)
        assert "session_end" in log

    def test_logs_error_on_exception(self, vault: Path):
        with pytest.raises(RuntimeError):
            with vault_session(vault):
                raise RuntimeError("boom")
        log = read_log(vault)
        assert "session_error" in log
        assert "boom" in log

    def test_reraises_exception(self, vault: Path):
        with pytest.raises(ValueError, match="test"):
            with vault_session(vault):
                raise ValueError("test")

    def test_rejects_invalid_vault(self, tmp_path: Path):
        with pytest.raises(VaultStructureError):
            with vault_session(tmp_path):
                pass  # pragma: no cover

    def test_custom_tier_in_log(self, vault: Path):
        with vault_session(vault, tier="silver"):
            pass
        log = read_log(vault)
        assert "[silver]" in log

    @pytest.mark.parametrize("tier", ["bronze", "silver", "gold"])
    def test_all_tiers_accepted(self, vault: Path, tier: str):
        with vault_session(vault, tier=tier) as v:
            assert v.exists()
