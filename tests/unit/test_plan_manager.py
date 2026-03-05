"""Unit tests for agents.plan_manager module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.plan_manager import PlanStatus, create_plan, next_plan_id, update_plan_status


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


class TestPlanStatusEnum:
    """Verify PlanStatus enum values and properties."""

    @pytest.mark.parametrize(
        "status,expected_terminal",
        [
            (PlanStatus.DRAFT, False),
            (PlanStatus.ACTIVE, False),
            (PlanStatus.COMPLETE, True),
            (PlanStatus.CANCELLED, True),
        ],
    )
    def test_is_terminal(self, status: PlanStatus, expected_terminal: bool):
        assert status.is_terminal is expected_terminal

    def test_values_are_unique(self):
        values = [s.value for s in PlanStatus]
        assert len(values) == len(set(values))


class TestUpdatePlanStatus:
    def test_updates_status_string(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"])
        update_plan_status(path, "active")
        assert "status: active" in path.read_text()

    def test_updates_status_enum(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"])
        update_plan_status(path, PlanStatus.ACTIVE)
        assert "status: active" in path.read_text()

    def test_updates_to_complete(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"])
        update_plan_status(path, PlanStatus.COMPLETE)
        assert "status: complete" in path.read_text()

    def test_preserves_other_fields(self, vault: Path):
        path = create_plan(vault, "Obj", ["S1"], priority="high")
        update_plan_status(path, PlanStatus.ACTIVE)
        content = path.read_text()
        assert "priority: high" in content
        assert "status: active" in content
