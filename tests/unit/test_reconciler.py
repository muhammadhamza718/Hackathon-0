"""Unit tests for agents.reconciler module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.reconciler import find_incomplete_plans, prioritize_plans, reconcile

ACTIVE_PLAN = """---
task_id: PLAN-2026-001
status: active
priority: high
created_date: 2026-02-27
---
# Objective
Active plan.

## Roadmap
- [x] Step 1
- [ ] Step 2
"""

DRAFT_PLAN = """---
task_id: PLAN-2026-002
status: draft
priority: medium
created_date: 2026-02-27
---
# Objective
Draft plan.

## Roadmap
- [ ] Step 1
"""

COMPLETE_PLAN = """---
task_id: PLAN-2026-003
status: complete
priority: low
created_date: 2026-02-27
---
# Objective
Done plan.

## Roadmap
- [x] Step 1
"""


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    plans = tmp_path / "Plans"
    plans.mkdir()
    (plans / "PLAN-2026-001.md").write_text(ACTIVE_PLAN)
    (plans / "PLAN-2026-002.md").write_text(DRAFT_PLAN)
    (plans / "PLAN-2026-003.md").write_text(COMPLETE_PLAN)
    return tmp_path


class TestFindIncompletePlans:
    def test_finds_active_and_draft(self, vault: Path):
        plans = find_incomplete_plans(vault)
        names = [p.name for p in plans]
        assert "PLAN-2026-001.md" in names
        assert "PLAN-2026-002.md" in names

    def test_excludes_complete(self, vault: Path):
        plans = find_incomplete_plans(vault)
        names = [p.name for p in plans]
        assert "PLAN-2026-003.md" not in names

    def test_empty_vault(self, tmp_path: Path):
        assert find_incomplete_plans(tmp_path) == []


class TestPrioritizePlans:
    def test_active_before_draft(self, vault: Path):
        plans = find_incomplete_plans(vault)
        ordered = prioritize_plans(plans)
        names = [p.name for p in ordered]
        assert names.index("PLAN-2026-001.md") < names.index("PLAN-2026-002.md")


class TestReconcile:
    def test_returns_next_plan(self, vault: Path):
        result = reconcile(vault)
        assert result["total_incomplete"] == 2
        assert result["next_plan"] == "PLAN-2026-001.md"

    def test_next_step_is_pending(self, vault: Path):
        result = reconcile(vault)
        assert result["next_step"] is not None
        assert result["next_step"]["done"] is False

    def test_empty_vault(self, tmp_path: Path):
        result = reconcile(tmp_path)
        assert result["total_incomplete"] == 0
        assert result["next_plan"] is None
