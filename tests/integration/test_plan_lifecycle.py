"""Integration test: full plan lifecycle from creation to reconciliation."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.plan_manager import create_plan, update_plan_status
from agents.plan_parser import next_pending_step, parse_frontmatter, parse_steps
from agents.reconciler import reconcile


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    (tmp_path / "Plans").mkdir()
    return tmp_path


class TestPlanLifecycle:
    """Test plan from creation → active → complete."""

    def test_create_and_parse(self, vault: Path):
        path = create_plan(vault, "Deploy new feature", ["Build", "Test", "Deploy"])
        content = path.read_text()

        meta = parse_frontmatter(content)
        assert meta["status"] == "draft"

        steps = parse_steps(content)
        assert len(steps) == 3
        assert all(not s["done"] for s in steps)

    def test_activate_and_reconcile(self, vault: Path):
        path = create_plan(vault, "Setup CI", ["Configure", "Run"])
        update_plan_status(path, "active")

        result = reconcile(vault)
        assert result["total_incomplete"] == 1
        assert result["next_step"]["index"] == 0

    def test_multiple_plans_prioritized(self, vault: Path):
        p1 = create_plan(vault, "Draft plan", ["Step 1"])
        p2 = create_plan(vault, "Active plan", ["Step 1"])
        update_plan_status(p2, "active")

        result = reconcile(vault)
        assert result["next_plan"] == p2.name


class TestPlanCompletion:
    def test_complete_plan_excluded_from_reconcile(self, vault: Path):
        path = create_plan(vault, "Done plan", ["Step 1"])
        update_plan_status(path, "complete")

        result = reconcile(vault)
        assert result["total_incomplete"] == 0
