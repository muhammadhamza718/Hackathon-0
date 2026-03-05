"""Unit tests for agents.task_templates module."""

from __future__ import annotations

import pytest

from agents.task_templates import (
    TemplateType,
    hitl_task_template,
    render_template,
    simple_task_template,
)


class TestSimpleTaskTemplate:
    def test_has_title(self):
        md = simple_task_template("Fix Bug", "Fix the login bug")
        assert "# Fix Bug" in md

    def test_has_description(self):
        md = simple_task_template("T", "Some description")
        assert "Some description" in md

    def test_has_frontmatter(self):
        md = simple_task_template("T", "D")
        assert md.startswith("---")

    def test_default_priority(self):
        md = simple_task_template("T", "D")
        assert "priority: medium" in md

    def test_custom_priority(self):
        md = simple_task_template("T", "D", priority="high")
        assert "priority: high" in md

    def test_has_acceptance_criteria(self):
        md = simple_task_template("T", "D")
        assert "Acceptance Criteria" in md


class TestHitlTaskTemplate:
    def test_has_approval_marker(self):
        md = hitl_task_template("Send Email", "Desc", "Send via SMTP")
        assert "✋" in md

    def test_has_action(self):
        md = hitl_task_template("T", "D", "Call payment API")
        assert "Call payment API" in md

    def test_requires_approval_field(self):
        md = hitl_task_template("T", "D", "A")
        assert "requires_approval: true" in md

    def test_default_high_priority(self):
        md = hitl_task_template("T", "D", "A")
        assert "priority: high" in md


class TestTemplateType:
    """Verify TemplateType enum values."""

    def test_simple_value(self):
        assert TemplateType.SIMPLE.value == "simple"

    def test_hitl_value(self):
        assert TemplateType.HITL.value == "hitl"

    def test_members_unique(self):
        values = [t.value for t in TemplateType]
        assert len(values) == len(set(values))


class TestRenderTemplate:
    """Verify render_template dispatcher."""

    def test_simple_dispatch(self):
        md = render_template(TemplateType.SIMPLE, "Task", "Desc")
        assert "Acceptance Criteria" in md
        assert "✋" not in md

    def test_hitl_dispatch(self):
        md = render_template(TemplateType.HITL, "Task", "Desc", action="Send email")
        assert "✋" in md
        assert "Send email" in md

    @pytest.mark.parametrize(
        "ttype,expected_in",
        [
            (TemplateType.SIMPLE, "Acceptance Criteria"),
            (TemplateType.HITL, "Approval Status"),
        ],
    )
    def test_dispatch_sections(self, ttype: TemplateType, expected_in: str):
        md = render_template(ttype, "T", "D", action="A")
        assert expected_in in md
