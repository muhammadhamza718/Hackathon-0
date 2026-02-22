"""
Unit Tests: Plan.md Schema Validation (T024)

Tests the PlanManager schema validation against valid, invalid, and edge case plans.
Ensures Plan.md files conform to rigid YAML + Markdown structure.

Test Cases:
    test_valid_plan_parsing() - Valid plan with all sections
    test_invalid_yaml_handling() - Malformed YAML frontmatter
    test_missing_sections_handling() - Missing mandatory sections
    test_missing_metadata_fields() - Incomplete YAML metadata
    test_invalid_timestamps() - Non-ISO-8601 timestamps
    test_schema_validation_pass() - Schema validation passes
    test_schema_validation_fail() - Schema validation fails
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Import from agents package
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager, PlanContent, PlanMetadata, PlanStep


class TestPlanSchemaValidation:
    """Test suite for Plan.md schema validation."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        with TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            (vault_path / "Plans").mkdir(parents=True)
            (vault_path / "Done" / "Plans").mkdir(parents=True)
            yield vault_path

    @pytest.fixture
    def plan_manager(self, temp_vault):
        """Create PlanManager instance with temporary vault."""
        return PlanManager(temp_vault)

    def test_valid_plan_parsing(self, plan_manager, temp_vault):
        """Test parsing of valid Plan.md with complete schema."""
        # Create a valid plan file
        plan_file = temp_vault / "Plans" / "PLAN-2026-001.md"
        valid_plan_content = """---
task_id: PLAN-2026-001
source_link: /Inbox/test.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Draft
blocked_reason: null
---

# Objective

Generate and send invoice to Client A for $1,500

## Context

Client requested via WhatsApp. Rate card: $1,500. No blocking dependencies.

## Roadmap

- [ ] Identify client contact information
- [ ] Calculate amount from rate card
- [ ] Generate invoice PDF
- [ ] ✋ Send email with invoice (requires approval)

## Reasoning Logs

- [2026-02-21T10:30:00Z] Agent: Created plan — Task ID: PLAN-2026-001
"""
        plan_file.write_text(valid_plan_content, encoding='utf-8')

        # Load and validate
        plan = plan_manager.load_plan("PLAN-2026-001")
        assert plan.metadata.task_id == "PLAN-2026-001"
        assert plan.objective == "Generate and send invoice to Client A for $1,500"
        assert len(plan.steps) == 4
        assert plan.steps[3].hitl_required is True
        assert len(plan.reasoning_logs) > 0
        plan_manager.validate_schema(plan)

    def test_invalid_yaml_handling(self, plan_manager, temp_vault):
        """Test error handling for malformed YAML frontmatter."""
        plan_file = temp_vault / "Plans" / "PLAN-invalid-yaml.md"
        invalid_yaml = """---
task_id: PLAN-invalid
source_link: /Inbox/test.md
created_date: [INVALID_DATE
priority: high
---

# Objective
Invalid plan
"""
        plan_file.write_text(invalid_yaml, encoding='utf-8')

        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid YAML"):
            plan_manager.load_plan("PLAN-invalid-yaml")

    def test_missing_sections_handling(self, plan_manager, temp_vault):
        """Test error handling for missing mandatory sections."""
        plan_file = temp_vault / "Plans" / "PLAN-missing-sections.md"
        missing_sections = """---
task_id: PLAN-2026-002
source_link: /Inbox/test.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Draft
blocked_reason: null
---

# Some wrong section

Test content

## Roadmap

- [ ] Step 1

## Reasoning Logs

- [2026-02-21T10:30:00Z] Agent: Created plan
"""
        plan_file.write_text(missing_sections, encoding='utf-8')

        plan = plan_manager.load_plan("PLAN-missing-sections")
        # Objective should be empty
        assert plan.objective == ""

        # Validation should fail for missing Objective
        with pytest.raises(ValueError, match="Missing Objective"):
            plan_manager.validate_schema(plan)

    def test_missing_metadata_fields(self, plan_manager, temp_vault):
        """Test error handling for incomplete YAML metadata."""
        plan_file = temp_vault / "Plans" / "PLAN-incomplete-meta.md"
        incomplete_meta = """---
task_id: PLAN-2026-003
source_link: /Inbox/test.md
priority: high
status: Draft
---

# Objective

Test objective

## Context

Test context

## Roadmap

- [ ] Step 1

## Reasoning Logs

- [2026-02-21T10:30:00Z] Agent: Created plan
"""
        plan_file.write_text(incomplete_meta, encoding='utf-8')

        plan = plan_manager.load_plan("PLAN-incomplete-meta")
        # created_date should be missing
        assert plan.metadata.created_date == ""

        # Validation should fail
        with pytest.raises(ValueError, match="Missing created_date"):
            plan_manager.validate_schema(plan)

    def test_invalid_timestamps(self, plan_manager, temp_vault):
        """Test error handling for non-ISO-8601 timestamps."""
        plan_file = temp_vault / "Plans" / "PLAN-bad-timestamps.md"
        bad_timestamps = """---
task_id: PLAN-2026-004
source_link: /Inbox/test.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Draft
blocked_reason: null
---

# Objective

Test objective

## Context

Test context

## Roadmap

- [ ] Step 1

## Reasoning Logs

- [02-21-2026 10:30] Agent: Created plan
- [2026-02-21T10:30:00Z] Agent: Valid entry
"""
        plan_file.write_text(bad_timestamps, encoding='utf-8')

        plan = plan_manager.load_plan("PLAN-bad-timestamps")
        # Should have parsed, but validation should fail
        with pytest.raises(ValueError, match="Invalid timestamp"):
            plan_manager.validate_schema(plan)

    def test_schema_validation_pass(self, plan_manager, temp_vault):
        """Test schema validation passes for correct plan."""
        # Create a plan programmatically
        plan_path = plan_manager.create_plan(
            task_id="test-001",
            objective="Test objective",
            context="Test context",
            steps=["Step 1", "Step 2", "✋ Step 3"],
            priority="high",
            source_link="/Inbox/test.md"
        )

        # Load and validate
        plan = plan_manager.load_plan("test-001")
        result = plan_manager.validate_schema(plan)
        assert result is True

    def test_schema_validation_fail_no_steps(self, plan_manager, temp_vault):
        """Test schema validation fails when no steps defined."""
        plan_file = temp_vault / "Plans" / "PLAN-no-steps.md"
        no_steps = """---
task_id: PLAN-2026-005
source_link: /Inbox/test.md
created_date: 2026-02-21T10:30:00Z
priority: high
status: Draft
blocked_reason: null
---

# Objective

Test objective

## Context

Test context

## Roadmap

## Reasoning Logs

- [2026-02-21T10:30:00Z] Agent: Created plan
"""
        plan_file.write_text(no_steps, encoding='utf-8')

        plan = plan_manager.load_plan("PLAN-no-steps")
        with pytest.raises(ValueError, match="No steps"):
            plan_manager.validate_schema(plan)

    def test_empty_objective(self, plan_manager):
        """Test schema validation fails with empty objective."""
        plan = PlanContent(
            metadata=PlanMetadata(
                task_id="test",
                source_link="/Inbox/test.md",
                created_date="2026-02-21T10:30:00Z",
                priority="high",
                status="Draft"
            ),
            objective="",  # Empty
            context="Test",
            steps=[PlanStep(1, "Step 1")]
        )

        with pytest.raises(ValueError, match="Missing Objective"):
            plan_manager.validate_schema(plan)

    def test_step_parsing_with_hitl_marker(self, plan_manager, temp_vault):
        """Test step parsing correctly identifies HITL markers."""
        plan_path = plan_manager.create_plan(
            task_id="hitl-test",
            objective="Test HITL markers",
            context="Test context",
            steps=["Regular step", "✋ HITL step", "✋ Another HITL"],
            priority="medium"
        )

        plan = plan_manager.load_plan("hitl-test")
        assert len(plan.steps) == 3
        assert plan.steps[0].hitl_required is False
        assert plan.steps[1].hitl_required is True
        assert plan.steps[2].hitl_required is True


class TestComplexityDetection:
    """Test suite for complexity detection integration."""

    def test_complexity_assessment(self):
        """Test complexity assessment for simple vs complex tasks."""
        from agents.skills.managing_obsidian_vault.complexity_detector import detect_complexity

        # Simple task
        simple_result = detect_complexity("Show me the dashboard")
        assert simple_result.is_complex() is False
        assert "show" in simple_result.reasoning.lower()

        # Complex task
        complex_result = detect_complexity("Generate invoice for Client A and send via email")
        assert complex_result.is_complex() is True
        assert "client" in [k.lower() for k in complex_result.matched_keywords]

    def test_complexity_keywords(self):
        """Test keyword matching in complexity detection."""
        from agents.skills.managing_obsidian_vault.complexity_detector import detect_complexity

        # High priority task
        result = detect_complexity("URGENT: Generate and send invoice ASAP")
        assert any(k in result.matched_keywords for k in ['urgent', 'asap'])

        # Multi-step task
        result = detect_complexity("invoice client with payment details")
        assert 'invoice' in result.matched_keywords or 'payment' in result.matched_keywords

        # External action task
        result = detect_complexity("send email to team and post update")
        assert any(k in result.matched_keywords for k in ['send', 'post', 'email'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
