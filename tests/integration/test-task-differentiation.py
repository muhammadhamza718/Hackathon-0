"""
Integration Tests: Simple vs Complex Task Differentiation (T026-T027)

Tests that agent correctly distinguishes between:
    - Simple tasks: Execute directly without planning
    - Complex tasks: Suggest plan creation before execution

Test Cases (T026):
    test_simple_task_no_plan() - Simple task doesn't create plan
    test_dashboard_query_simple() - "Show dashboard" is simple
    test_list_query_simple() - "List all tasks" is simple
    test_read_operation_simple() - "Read file" is simple

Test Cases (T027):
    test_complex_invoice_task() - Invoice + email is complex
    test_client_payment_complex() - Client payment task is complex
    test_multi_step_project_complex() - Multi-step project is complex
    test_complex_with_approval() - Complex task prevents direct execution
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Import from agents package
from agents.skills.managing_obsidian_vault.complexity_detector import detect_complexity, ComplexityLevel
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager


class TestSimpleTaskDifferentiation:
    """Test suite for simple task differentiation (T026)."""

    def test_simple_task_no_plan(self):
        """Test that simple task is correctly identified."""
        user_input = "Show me the dashboard"
        complexity = detect_complexity(user_input)

        assert complexity.is_complex() is False
        assert complexity.level == ComplexityLevel.SIMPLE
        assert "dashboard" not in complexity.suggestion.lower() or "no plan" in complexity.suggestion.lower()

    def test_dashboard_query_simple(self):
        """Test dashboard query is simple task."""
        inputs = [
            "Display the current dashboard",
            "Show dashboard",
            "What's on the dashboard",
            "Display all tasks from dashboard"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is False, f"Failed for: {user_input}"

    def test_list_query_simple(self):
        """Test list queries are simple tasks."""
        inputs = [
            "List all tasks",
            "Show me all active plans",
            "Display the task list",
            "What tasks are pending"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is False, f"Failed for: {user_input}"

    def test_read_operation_simple(self):
        """Test read operations are simple tasks."""
        inputs = [
            "Read the status file",
            "Show me the config",
            "Display the readme",
            "What does the plan say"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is False, f"Failed for: {user_input}"

    def test_summarize_query_simple(self):
        """Test summarization queries are simple."""
        inputs = [
            "Summarize today's activities",
            "Give me a summary of the plan",
            "How many tasks completed",
            "Tell me the status"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is False, f"Failed for: {user_input}"

    def test_single_action_simple(self):
        """Test single-action tasks are simple."""
        inputs = [
            "Read the inbox",
            "Find the client contact",
            "Search for recent messages",
            "Get the current date"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is False, f"Failed for: {user_input}"


class TestComplexTaskDifferentiation:
    """Test suite for complex task differentiation (T027)."""

    def test_complex_invoice_task(self):
        """Test invoice + email task is complex."""
        user_input = "Generate invoice for Client A and send via email"
        complexity = detect_complexity(user_input)

        assert complexity.is_complex() is True
        assert complexity.level == ComplexityLevel.COMPLEX
        # Should suggest plan creation
        assert "plan" in complexity.suggestion.lower()

    def test_client_payment_complex(self):
        """Test client payment task is complex."""
        inputs = [
            "Create invoice for Client B for $5000 and process payment",
            "Generate payment invoice and email client",
            "invoice client A for services and send receipt"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_multi_step_project_complex(self):
        """Test multi-step project tasks are complex."""
        inputs = [
            "Set up project schedule, assign team, and send notifications",
            "Create campaign plan, review with team, then launch",
            "Plan the audit: schedule, review docs, generate report, email stakeholders"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_high_priority_urgent_complex(self):
        """Test urgent tasks are marked complex."""
        inputs = [
            "URGENT: Send invoice to client ASAP",
            "CRITICAL: Generate report and submit",
            "#high: Process payment immediately"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_external_action_complex(self):
        """Test external actions are marked complex."""
        inputs = [
            "Send email to client with invoice",
            "Email team the campaign update and publish online",
            "Send notification to subscribers",
            "Email manager and submit report to system"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_dependent_steps_complex(self):
        """Test dependent steps marked complex."""
        inputs = [
            "After approval, send invoice. Then log transaction.",
            "Once report is done, email client and archive",
            "Generate invoice, then after payment confirmed, send receipt"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_stakeholder_involvement_complex(self):
        """Test multi-stakeholder tasks marked complex."""
        inputs = [
            "Obtain client approval for invoice and process payment",
            "Coordinate invoice audit with team and manager",
            "Send report for approval and await sign-off"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"


class TestComplexTaskPlanCreation:
    """Test suite for plan creation in response to complex tasks."""

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

    def test_complex_with_approval_prevents_direct_execution(self, plan_manager, temp_vault):
        """Test that complex task with approval gates execution."""
        user_input = "Generate invoice for Client A and send via email"

        # Detect complexity
        complexity = detect_complexity(user_input)
        assert complexity.is_complex() is True

        # If user approves plan creation, create plan
        plan_path = plan_manager.create_plan(
            task_id="client-invoice-test",
            objective=user_input,
            context="Client requested standard invoice",
            steps=[
                "Generate invoice PDF",
                "✋ Send email with invoice (requires approval)"
            ],
            priority="high"
        )

        assert plan_path.exists()

        # Load plan and verify it has HITL step
        plan = plan_manager.load_plan("client-invoice-test")
        assert plan.has_pending_approval() is True

        # Verify external action would not be executed
        # (It's marked with ✋, indicating requires human approval)
        hitl_steps = [s for s in plan.steps if s.hitl_required]
        assert len(hitl_steps) >= 1

    def test_plan_creation_workflow_for_complex_invoice(self, plan_manager, temp_vault):
        """Test full workflow: Detect complex → Create plan → Prevent execution."""
        # Step 1: User provides complex task
        user_input = "Invoice Client X for $2,000 and send email to approve"

        # Step 2: Detect complexity
        complexity = detect_complexity(user_input)
        assert complexity.is_complex() is True
        assert "plan" in complexity.suggestion.lower()

        # Step 3: User approves plan creation
        # (In real system, agent would wait for approval)

        # Step 4: Create plan
        plan_path = plan_manager.create_plan(
            task_id="invoice-client-x",
            objective=user_input,
            context="Standard invoice for services",
            steps=[
                "Retrieve client rate: $2,000",
                "Generate invoice PDF",
                "✋ Send email with invoice (requires human approval)"
            ],
            priority="high",
            source_link="/Inbox/client_x_request.md"
        )

        # Step 5: Verify plan created
        assert plan_path.exists()
        plan = plan_manager.load_plan("invoice-client-x")
        assert len(plan.steps) == 3

        # Step 6: Verify external actions are gated
        send_step = plan.steps[2]
        assert send_step.hitl_required is True
        assert "send" in send_step.description.lower()

        # Step 7: Verify no external action would execute directly
        # (Only after human approval)
        assert plan.has_pending_approval() is True


class TestEdgeCases:
    """Test edge cases in complexity detection."""

    def test_empty_input(self):
        """Test empty input handling."""
        complexity = detect_complexity("")
        assert complexity.is_complex() is False

    def test_whitespace_only(self):
        """Test whitespace-only input."""
        complexity = detect_complexity("   ")
        assert complexity.is_complex() is False

    def test_mixed_case_keywords(self):
        """Test keywords work with mixed case."""
        inputs = [
            "INVOICE client for $1000",
            "Send EMAIL to team",
            "CLIENT approval required"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_keyword_in_sentence(self):
        """Test keywords in middle of sentence."""
        inputs = [
            "I need to send an email to the team",
            "Can you invoice this client please",
            "The project requires approval"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is True, f"Failed for: {user_input}"

    def test_negative_case(self):
        """Test that simple synonyms don't trigger complexity."""
        inputs = [
            "Display the invoice I already created",
            "Show me sent emails",
            "List approved projects"
        ]

        for user_input in inputs:
            complexity = detect_complexity(user_input)
            assert complexity.is_complex() is False, f"Failed for: {user_input}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
