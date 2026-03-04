"""Unit tests for agents.plan_parser module."""

from __future__ import annotations

import pytest

from agents.plan_parser import (
    PlanSummary,
    next_pending_step,
    parse_frontmatter,
    parse_steps,
    summarize_plan,
)

SAMPLE_PLAN = """---
task_id: PLAN-2026-001
status: active
priority: high
created_date: 2026-02-27
---
# Objective
Test the parser.

## Roadmap
- [x] Step 1: Initialize
- [ ] Step 2: Execute ✋
- [ ] Step 3: Complete
"""


class TestParseFrontmatter:
    def test_extracts_task_id(self):
        meta = parse_frontmatter(SAMPLE_PLAN)
        assert meta["task_id"] == "PLAN-2026-001"

    def test_extracts_status(self):
        meta = parse_frontmatter(SAMPLE_PLAN)
        assert meta["status"] == "active"

    def test_extracts_priority(self):
        meta = parse_frontmatter(SAMPLE_PLAN)
        assert meta["priority"] == "high"

    def test_empty_content_returns_defaults(self):
        meta = parse_frontmatter("no frontmatter here")
        assert meta["task_id"] == ""
        assert meta["status"] == ""


class TestParseSteps:
    def test_returns_three_steps(self):
        steps = parse_steps(SAMPLE_PLAN)
        assert len(steps) == 3

    def test_first_step_done(self):
        steps = parse_steps(SAMPLE_PLAN)
        assert steps[0]["done"] is True

    def test_second_step_pending(self):
        steps = parse_steps(SAMPLE_PLAN)
        assert steps[1]["done"] is False

    def test_second_step_requires_hitl(self):
        steps = parse_steps(SAMPLE_PLAN)
        assert steps[1]["requires_hitl"] is True

    def test_first_step_no_hitl(self):
        steps = parse_steps(SAMPLE_PLAN)
        assert steps[0]["requires_hitl"] is False

    def test_step_indices_sequential(self):
        steps = parse_steps(SAMPLE_PLAN)
        for i, step in enumerate(steps):
            assert step["index"] == i


class TestNextPendingStep:
    def test_returns_first_incomplete(self):
        steps = parse_steps(SAMPLE_PLAN)
        pending = next_pending_step(steps)
        assert pending is not None
        assert pending["index"] == 1

    def test_returns_none_when_all_done(self):
        steps = [{"index": 0, "description": "done", "done": True, "requires_hitl": False}]
        assert next_pending_step(steps) is None  # type: ignore[arg-type]


COMPLETE_PLAN = """---
task_id: PLAN-2026-099
status: active
priority: low
---
## Roadmap
- [x] Step 1
- [x] Step 2
"""

EMPTY_PLAN = """---
task_id: PLAN-2026-000
status: draft
priority: medium
---
# No roadmap steps
"""


class TestPlanSummary:
    """Verify PlanSummary dataclass and its computed properties."""

    def test_progress_pct_partial(self):
        summary = summarize_plan(SAMPLE_PLAN)
        assert summary.progress_pct == pytest.approx(33.3, abs=0.1)

    def test_progress_pct_complete(self):
        summary = summarize_plan(COMPLETE_PLAN)
        assert summary.progress_pct == 100.0

    def test_progress_pct_empty_plan(self):
        summary = summarize_plan(EMPTY_PLAN)
        assert summary.progress_pct == 0.0

    def test_is_complete_false(self):
        summary = summarize_plan(SAMPLE_PLAN)
        assert summary.is_complete is False

    def test_is_complete_true(self):
        summary = summarize_plan(COMPLETE_PLAN)
        assert summary.is_complete is True

    def test_is_complete_empty(self):
        summary = summarize_plan(EMPTY_PLAN)
        assert summary.is_complete is False

    def test_next_step_returns_pending(self):
        summary = summarize_plan(SAMPLE_PLAN)
        assert summary.next_step is not None
        assert summary.next_step["done"] is False

    def test_next_step_none_when_complete(self):
        summary = summarize_plan(COMPLETE_PLAN)
        assert summary.next_step is None

    def test_meta_preserved(self):
        summary = summarize_plan(SAMPLE_PLAN)
        assert summary.meta["task_id"] == "PLAN-2026-001"
        assert summary.meta["status"] == "active"

    @pytest.mark.parametrize(
        "done_count,total,expected_pct",
        [
            (0, 5, 0.0),
            (1, 4, 25.0),
            (2, 3, 66.7),
            (5, 5, 100.0),
        ],
    )
    def test_progress_pct_values(self, done_count: int, total: int, expected_pct: float):
        steps_text = ""
        for i in range(total):
            mark = "x" if i < done_count else " "
            steps_text += f"- [{mark}] Step {i + 1}\n"
        content = f"---\ntask_id: T\nstatus: active\npriority: low\n---\n## Roadmap\n{steps_text}"
        summary = summarize_plan(content)
        assert summary.progress_pct == pytest.approx(expected_pct, abs=0.1)
