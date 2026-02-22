"""
Integration Tests: Plan Creation Workflow (T025)

Tests end-to-end plan creation workflow including complexity detection,
InitializePlan execution, and schema validation.

Test Cases:
    test_complex_task_plan_creation() - Complex task triggers plan creation
    test_plan_stored_correctly() - Plan stored with correct metadata
    test_all_sections_present() - All sections present in created plan
    test_yaml_frontmatter_valid() - YAML frontmatter is valid and complete
    test_reasoning_log_initialized() - Reasoning logs initialized with timestamp
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Import from agents package
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager
from agents.skills.managing_obsidian_vault.complexity_detector import detect_complexity, extract_steps


class TestPlanCreationWorkflow:
    """Test suite for plan creation workflow."""

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
        """Create PlanManager instance."""
        return PlanManager(temp_vault)

    def test_complex_task_plan_creation(self, plan_manager, temp_vault):
        """Test that complex task triggers plan creation workflow."""
        # Define complex task
        user_input = "Generate invoice for Client A for $1,500 and send via email"

        # Detect complexity
        complexity = detect_complexity(user_input)
        assert complexity.is_complex() is True

        # Extract steps from input
        steps = extract_steps(user_input)

        # Create plan
        plan_path = plan_manager.create_plan(
            task_id="client-a-invoice",
            objective=user_input,
            context="Client requested via WhatsApp. Standard rate.",
            steps=steps if steps else [
                "Generate invoice PDF",
                "✋ Send email with attachment"
            ],
            priority="high",
            source_link="/Inbox/whatsapp_client_a.md"
        )

        # Assert plan created
        assert plan_path.exists()
        assert plan_path.name == "PLAN-client-a-invoice.md"
        assert (temp_vault / "Plans" / "PLAN-client-a-invoice.md").exists()

    def test_plan_stored_correctly(self, plan_manager, temp_vault):
        """Test that plan metadata stored correctly."""
        plan_path = plan_manager.create_plan(
            task_id="workflow-test",
            objective="Test objective",
            context="Test context with dependencies",
            steps=["Step 1", "Step 2"],
            priority="medium",
            source_link="/Inbox/test.md"
        )

        plan = plan_manager.load_plan("workflow-test")

        assert plan.metadata.task_id == "workflow-test"
        assert plan.metadata.priority == "medium"
        assert plan.metadata.status == "Draft"
        assert plan.metadata.source_link == "/Inbox/test.md"
        assert plan.metadata.blocked_reason is None
        assert plan.metadata.created_date  # Should be set

    def test_all_sections_present(self, plan_manager, temp_vault):
        """Test that all mandatory sections present in created plan."""
        plan_path = plan_manager.create_plan(
            task_id="sections-test",
            objective="Objective text",
            context="Context text",
            steps=["Step 1", "Step 2", "Step 3"],
            priority="high"
        )

        plan = plan_manager.load_plan("sections-test")

        # Check all sections present
        assert plan.objective == "Objective text"
        assert plan.context == "Context text"
        assert len(plan.steps) == 3
        assert len(plan.reasoning_logs) > 0

        # Check markdown content
        plan_file = temp_vault / "Plans" / "PLAN-sections-test.md"
        content = plan_file.read_text(encoding='utf-8')

        assert "# Objective" in content
        assert "## Context" in content
        assert "## Roadmap" in content
        assert "## Reasoning Logs" in content
        assert "- [ ] Step 1" in content
        assert "- [ ] Step 2" in content
        assert "- [ ] Step 3" in content

    def test_yaml_frontmatter_valid(self, plan_manager, temp_vault):
        """Test that YAML frontmatter is valid and complete."""
        plan_path = plan_manager.create_plan(
            task_id="yaml-test",
            objective="Test",
            context="Test",
            steps=["Step 1"],
            priority="high",
            source_link="/Inbox/test.md"
        )

        plan_file = temp_vault / "Plans" / "PLAN-yaml-test.md"
        content = plan_file.read_text(encoding='utf-8')

        # Verify YAML structure
        assert content.startswith("---")
        parts = content.split("---")
        assert len(parts) >= 3

        yaml_content = parts[1]
        assert "task_id: yaml-test" in yaml_content
        assert "priority: high" in yaml_content
        assert "status: Draft" in yaml_content
        assert "source_link: /Inbox/test.md" in yaml_content
        assert "blocked_reason: null" in yaml_content
        assert "created_date:" in yaml_content

    def test_reasoning_log_initialized(self, plan_manager, temp_vault):
        """Test that reasoning logs initialized with creation entry."""
        plan_path = plan_manager.create_plan(
            task_id="log-test",
            objective="Test objective",
            context="Test",
            steps=["Step 1"]
        )

        plan = plan_manager.load_plan("log-test")

        # Should have at least one reasoning log entry
        assert len(plan.reasoning_logs) >= 1

        # First entry should be creation log
        first_log = plan.reasoning_logs[0]
        assert "[" in first_log  # ISO timestamp
        assert "]" in first_log
        assert "Agent: Created plan" in first_log
        assert "2026" in first_log  # Year should be in timestamp

    def test_plan_file_readable(self, plan_manager, temp_vault):
        """Test that created plan file is readable and parseable."""
        plan_path = plan_manager.create_plan(
            task_id="readability-test",
            objective="Test readability",
            context="Test context",
            steps=["Step 1", "Step 2", "✋ HITL Step"]
        )

        # Read file directly
        plan_file = temp_vault / "Plans" / "PLAN-readability-test.md"
        content = plan_file.read_text(encoding='utf-8')

        # Should be valid markdown with frontmatter
        assert "---" in content
        assert "# Objective" in content
        assert "## Roadmap" in content
        assert "- [ ]" in content
        assert "✋" in content

        # Should be re-parseable
        reloaded = plan_manager.load_plan("readability-test")
        assert reloaded.metadata.task_id == "readability-test"
        assert len(reloaded.steps) == 3

    def test_multiple_plans_independent(self, plan_manager, temp_vault):
        """Test that multiple plans are stored independently."""
        # Create first plan
        plan1_path = plan_manager.create_plan(
            task_id="plan-1",
            objective="Plan 1 objective",
            context="Context 1",
            steps=["Step 1", "Step 2"]
        )

        # Create second plan
        plan2_path = plan_manager.create_plan(
            task_id="plan-2",
            objective="Plan 2 objective",
            context="Context 2",
            steps=["Step A", "Step B", "Step C"]
        )

        # Verify independence
        plan1 = plan_manager.load_plan("plan-1")
        plan2 = plan_manager.load_plan("plan-2")

        assert plan1.objective == "Plan 1 objective"
        assert plan2.objective == "Plan 2 objective"
        assert len(plan1.steps) == 2
        assert len(plan2.steps) == 3

        # Both files should exist
        assert (temp_vault / "Plans" / "PLAN-plan-1.md").exists()
        assert (temp_vault / "Plans" / "PLAN-plan-2.md").exists()

    def test_plan_with_hitl_markers(self, plan_manager, temp_vault):
        """Test plan creation with HITL markers."""
        plan_path = plan_manager.create_plan(
            task_id="hitl-workflow",
            objective="Workflow with approvals",
            context="Requires human approval",
            steps=[
                "Generate document",
                "✋ Send for approval",
                "Implement changes",
                "✋ Final sign-off"
            ]
        )

        plan = plan_manager.load_plan("hitl-workflow")

        # Verify HITL markers parsed
        assert len(plan.steps) == 4
        assert plan.steps[0].hitl_required is False
        assert plan.steps[1].hitl_required is True
        assert plan.steps[2].hitl_required is False
        assert plan.steps[3].hitl_required is True

        # Verify markdown representation
        plan_file = temp_vault / "Plans" / "PLAN-hitl-workflow.md"
        content = plan_file.read_text(encoding='utf-8')
        assert "✋" in content
        assert content.count("✋") == 2


class TestPlanDuplicateDetection:
    """Test suite for duplicate plan detection."""

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
        """Create PlanManager instance."""
        return PlanManager(temp_vault)

    def test_detect_duplicate_by_task_id(self, plan_manager):
        """Test duplicate detection by task_id."""
        # Create first plan
        plan_manager.create_plan(
            task_id="invoice-001",
            objective="Generate invoice",
            context="Test",
            steps=["Step 1"]
        )

        # Try to detect duplicate
        duplicate = plan_manager.detect_duplicate_plan("invoice-001")
        assert duplicate is not None
        assert duplicate.metadata.task_id == "invoice-001"

    def test_detect_duplicate_by_source_link(self, plan_manager):
        """Test duplicate detection by source_link."""
        # Create first plan
        plan_manager.create_plan(
            task_id="source-test",
            objective="Generate invoice",
            context="Test",
            steps=["Step 1"],
            source_link="/Inbox/whatsapp_client.md"
        )

        # Detect by source_link
        duplicate = plan_manager.detect_duplicate_plan(
            task_id="other-id",
            source_link="/Inbox/whatsapp_client.md"
        )
        assert duplicate is not None
        assert duplicate.metadata.source_link == "/Inbox/whatsapp_client.md"

    def test_no_duplicate_found(self, plan_manager):
        """Test no duplicate when plan doesn't exist."""
        # Create one plan
        plan_manager.create_plan(
            task_id="existing",
            objective="Test",
            context="Test",
            steps=["Step 1"]
        )

        # Check for different task_id
        duplicate = plan_manager.detect_duplicate_plan("non-existing")
        assert duplicate is None

    def test_merge_steps_avoids_duplication(self, plan_manager):
        """Test merging steps into existing plan."""
        # Create initial plan
        plan_path = plan_manager.create_plan(
            task_id="merge-test",
            objective="Test merge",
            context="Test",
            steps=["Step 1", "Step 2"]
        )

        plan = plan_manager.load_plan("merge-test")
        initial_count = len(plan.steps)

        # Merge new steps
        new_steps = ["Step 2", "Step 3", "Step 4"]
        merged = plan_manager.merge_plan_steps(plan, new_steps)

        # Should have 4 steps (Step 2 is duplicate, not added again)
        assert len(merged.steps) == 4
        assert merged.steps[0].description == "Step 1"
        assert merged.steps[1].description == "Step 2"
        assert merged.steps[2].description == "Step 3"
        assert merged.steps[3].description == "Step 4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
