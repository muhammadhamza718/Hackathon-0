"""Unit tests for agents.vault_router module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.vault_router import classify_task, mark_done, route_file


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    for d in ("Inbox", "Needs_Action", "Done", "Pending_Approval"):
        (tmp_path / d).mkdir()
    return tmp_path


class TestClassifyTask:
    def test_simple_task(self):
        assert classify_task("# Fix typo\n\nCorrect the spelling.") == "simple"

    def test_complex_with_email(self):
        assert classify_task("Send an email to the client.") == "complex"

    def test_complex_with_api(self):
        assert classify_task("Call the payment API.") == "complex"

    def test_complex_with_hitl_marker(self):
        assert classify_task("Step 2: Execute ✋") == "complex"

    def test_complex_multi_step(self):
        assert classify_task("This is a multi-step process.") == "complex"


class TestRouteFile:
    def test_simple_routed_to_needs_action(self, vault: Path):
        f = vault / "Inbox" / "task.md"
        f.write_text("# Simple task\n\nDo something.")
        dest = route_file(f, vault)
        assert dest.parent.name == "Needs_Action"
        assert not f.exists()

    def test_complex_routed_to_pending(self, vault: Path):
        f = vault / "Inbox" / "task.md"
        f.write_text("# Send email to client\n\nEmail the report.")
        dest = route_file(f, vault)
        assert dest.parent.name == "Pending_Approval"

    def test_missing_file_raises(self, vault: Path):
        with pytest.raises(FileNotFoundError):
            route_file(vault / "Inbox" / "nope.md", vault)


class TestMarkDone:
    def test_moves_to_done(self, vault: Path):
        f = vault / "Needs_Action" / "task.md"
        f.write_text("done")
        dest = mark_done(f, vault)
        assert dest.parent.name == "Done"
        assert not f.exists()
