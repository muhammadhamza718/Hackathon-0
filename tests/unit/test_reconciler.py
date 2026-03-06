"""Unit tests for agents.reconciler module."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.reconciler import (
    ReconcileResult,
    ReconcileStrategy,
    count_by_status,
    find_incomplete_plans,
    prioritize_plans,
    reconcile,
)

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

HITL_PLAN = """---
task_id: PLAN-2026-004
status: active
priority: high
created_date: 2026-02-28
---
# Objective
HITL plan.

## Roadmap
- [x] Step 1
- [ ] Step 2: Send report ✋
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


class TestReconcileResult:
    """Verify the ReconcileResult dataclass behaves correctly."""

    def test_has_work_true(self, vault: Path):
        result = reconcile(vault)
        assert result.has_work is True

    def test_has_work_false(self, tmp_path: Path):
        result = reconcile(tmp_path)
        assert result.has_work is False

    def test_is_frozen(self, vault: Path):
        result = reconcile(vault)
        with pytest.raises(AttributeError):
            result.total_incomplete = 99  # type: ignore[misc]

    def test_next_step_requires_hitl_false(self, vault: Path):
        result = reconcile(vault)
        assert result.next_step_requires_hitl is False

    def test_next_step_requires_hitl_true(self, tmp_path: Path):
        plans = tmp_path / "Plans"
        plans.mkdir()
        (plans / "PLAN-2026-004.md").write_text(HITL_PLAN)
        result = reconcile(tmp_path)
        assert result.next_step_requires_hitl is True

    def test_hitl_false_when_no_work(self, tmp_path: Path):
        result = reconcile(tmp_path)
        assert result.next_step_requires_hitl is False


class TestReconcile:
    def test_returns_next_plan(self, vault: Path):
        result = reconcile(vault)
        assert result.total_incomplete == 2
        assert result.next_plan == "PLAN-2026-001.md"

    def test_next_step_is_pending(self, vault: Path):
        result = reconcile(vault)
        assert result.next_step is not None
        assert result.next_step["done"] is False

    def test_empty_vault(self, tmp_path: Path):
        result = reconcile(tmp_path)
        assert result.total_incomplete == 0
        assert result.next_plan is None

    @pytest.mark.parametrize(
        "statuses,expected_count",
        [
            (["active"], 1),
            (["active", "draft"], 2),
            (["complete"], 0),
            (["complete", "complete"], 0),
            (["active", "blocked", "draft"], 3),
        ],
    )
    def test_incomplete_counts(self, tmp_path: Path, statuses: list[str], expected_count: int):
        plans = tmp_path / "Plans"
        plans.mkdir()
        for i, status in enumerate(statuses):
            content = f"---\ntask_id: PLAN-2026-{i:03d}\nstatus: {status}\npriority: medium\n---\n## Roadmap\n- [ ] Step\n"
            (plans / f"PLAN-2026-{i:03d}.md").write_text(content)
        result = reconcile(tmp_path)
        assert result.total_incomplete == expected_count


class TestCountByStatus:
    """Verify plan status aggregation."""

    def test_counts_active_and_draft(self, vault: Path):
        counts = count_by_status(vault)
        assert counts.get("active") == 1
        assert counts.get("draft") == 1

    def test_counts_complete(self, vault: Path):
        counts = count_by_status(vault)
        assert counts.get("complete") == 1

    def test_empty_vault(self, tmp_path: Path):
        assert count_by_status(tmp_path) == {}

    def test_total_matches_plan_count(self, vault: Path):
        counts = count_by_status(vault)
        assert sum(counts.values()) == 3


class TestReconcileStrategy:
    """Verify strategy-based plan selection."""

    def test_default_is_priority_first(self, vault: Path):
        result = reconcile(vault)
        assert result.next_plan == "PLAN-2026-001.md"

    def test_newest_first(self, vault: Path):
        result = reconcile(vault, strategy=ReconcileStrategy.NEWEST_FIRST)
        assert result.next_plan == "PLAN-2026-002.md"

    def test_oldest_first(self, vault: Path):
        result = reconcile(vault, strategy=ReconcileStrategy.OLDEST_FIRST)
        assert result.next_plan == "PLAN-2026-001.md"

    def test_empty_vault_all_strategies(self, tmp_path: Path):
        for strategy in ReconcileStrategy:
            result = reconcile(tmp_path, strategy=strategy)
            assert result.has_work is False
