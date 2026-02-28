"""Unit tests for agents.plan_manager module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.plan_manager import create_plan, next_plan_id, update_plan_status


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Plans").mkdir()
    return tmp_path


class TestNextPlanId:
    def test_first_plan(self, vault: Path):
        pid = next_plan_id(vault)
        assert pid.startswith("PLAN-")
        assert pid.endswith("-001")

    def test_increments(self, vault: Path):
        (vault / "Plans" / "PLAN-2026-001.md").write_text("x")
        pid = next_plan_id(vault)
        assert pid.endswith("-002")


class TestCreatePlan:
    def test_creates_file(self, vault: Path):
        path = create_plan(vault, "Test objective", ["Step 1", "Step 2"])
        assert path.exists()
        assert path.suffix == ".md"

    def test_contains_objective(self, vault: Path):
        path = create_plan(vault, "Build the widget", ["Do it"])
        content = path.read_text()
        assert "Build the widget" in content

    def test_contains_steps(self, vault: Path):
        path = create_plan(vault, "Obj", ["Alpha", "Beta"])
        content = path.read_text()
        assert "- [ ] Alpha" in content
        assert "- [ ] Beta" in content

    def test_has_frontmatter(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"])
        content = path.read_text()
        assert content.startswith("---")
        assert "status: draft" in content

    def test_priority_default(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"])
        assert "priority: medium" in path.read_text()

    def test_priority_custom(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"], priority="high")
        assert "priority: high" in path.read_text()


class TestUpdatePlanStatus:
    def test_updates_status(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"])
        update_plan_status(path, "active")
        assert "status: active" in path.read_text()
