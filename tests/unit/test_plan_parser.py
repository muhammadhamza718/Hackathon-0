"""Unit tests for agents.plan_parser module."""

from __future__ import annotations

from agents.plan_parser import next_pending_step, parse_frontmatter, parse_steps

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
