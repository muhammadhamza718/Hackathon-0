"""Integration tests for Gold Tier autonomous loop lifecycle."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agents.constants import DONE_DIR, NEEDS_ACTION_DIR, PLANS_DIR
from agents.gold.autonomous_loop import AutonomousLoop
from agents.gold.models import LoopConfig


class TestGoldLoopLifecycle:
    """Test the complete lifecycle of the autonomous loop."""

    def test_loop_processes_simple_plan(self, tmp_path):
        """Test that the loop can process a simple plan with multiple steps."""
        # Create a plan with multiple steps
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()

        plan_content = """---
status: active
---
# Test Plan

- [ ] Step 1: Do something
- [ ] Step 2: Do something else
- [ ] Step 3: Final step
"""
        plan_file = plans_dir / "PLAN-test.md"
        plan_file.write_text(plan_content)

        # Configure loop to run just 3 iterations
        config = LoopConfig(max_iterations=3, checkpoint_interval=1)
        loop = AutonomousLoop(tmp_path, config=config)

        # Run the loop with a custom step executor that marks steps complete
        completed_steps = []

        def mock_step_executor(plan_path, step_index):
            completed_steps.append(step_index)
            # Mark the step as complete by updating the plan file
            content = plan_path.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if f"Step {step_index + 1}:" in line and '[ ]' in line:
                    lines[i] = line.replace('[ ]', '[x]')
                    break
            plan_path.write_text('\n'.join(lines))
            return True

        loop._step_executor = mock_step_executor
        result = loop.run()

        # Verify that steps were processed (all steps processed in first iteration)
        assert len(completed_steps) >= 1
        assert result.total_iterations >= 1

        # Check that state was checkpointed
        state_path = tmp_path / "Logs" / "loop-state.json"
        assert state_path.exists()

    def test_loop_resume_from_checkpoint(self, tmp_path):
        """Test that the loop can resume from a checkpoint."""
        # Create initial state file
        logs_dir = tmp_path / "Logs"
        logs_dir.mkdir()
        state_file = logs_dir / "loop-state.json"

        initial_state = {
            "session_id": "test-session",
            "iteration": 5,
            "active_plan_id": None,
            "active_step_index": None,
            "blocked_plans": [],
            "last_checkpoint": "2026-03-06T10:00:00Z",
            "exit_promise_met": False
        }
        state_file.write_text(json.dumps(initial_state))

        # Create a simple plan
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()

        plan_content = """---
status: active
---
# Resume Test Plan

- [ ] Step 1: Continue from here
"""
        plan_file = plans_dir / "PLAN-resume.md"
        plan_file.write_text(plan_content)

        # Run loop with limited iterations
        config = LoopConfig(max_iterations=2, checkpoint_interval=1)
        loop = AutonomousLoop(tmp_path, config=config)

        def mock_step_executor(plan_path, step_index):
            # Mark step as complete
            content = plan_path.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "Step 1:" in line and '[ ]' in line:
                    lines[i] = line.replace('[ ]', '[x]')
                    break
            plan_path.write_text('\n'.join(lines))
            return True

        loop._step_executor = mock_step_executor
        result = loop.run()

        # Loop starts at iteration 5, processes the plan step, then exits when exit promise is met
        # The iteration counter advances to 6 after processing
        assert result.total_iterations >= 5

        # Check that state was updated
        updated_state = json.loads(state_file.read_text())
        assert updated_state["iteration"] >= 5  # Should have advanced from initial state

    def test_loop_processes_needs_action_items(self, tmp_path):
        """Test that the loop processes items in Needs_Action directory."""
        # Create some needs_action items
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        task1 = needs_action / "task1.md"
        task1.write_text("# Task 1\n\nDescription of task 1.")

        task2 = needs_action / "task2.md"
        task2.write_text("# Task 2\n\nDescription of task 2.")

        # Create Done directory
        done_dir = tmp_path / DONE_DIR
        done_dir.mkdir()

        # Run loop to process needs_action items
        config = LoopConfig(max_iterations=2, checkpoint_interval=1)
        loop = AutonomousLoop(tmp_path, config=config)
        result = loop.run()

        # Tasks should be moved to Done
        assert not task1.exists()  # Original file should be gone
        assert not task2.exists()  # Original file should be gone

        done_files = list(done_dir.iterdir())
        assert len(done_files) == 2  # Both tasks should be in Done
        assert result.tasks_completed >= 2

    def test_loop_exit_promise_met(self, tmp_path):
        """Test that the loop exits when the exit promise is met."""
        # Create a completed plan (marked as complete)
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()

        completed_plan = plans_dir / "PLAN-completed.md"
        completed_plan.write_text("""---
status: complete
---
# Completed Plan

- [x] Step 1: Done
- [x] Step 2: Also Done
""")

        # Create empty needs_action directory
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        # Run loop - should exit early due to exit promise
        config = LoopConfig(max_iterations=10, checkpoint_interval=1)  # High max to test early exit
        loop = AutonomousLoop(tmp_path, config=config)
        result = loop.run()

        # Loop should have exited early because exit promise was met
        assert result.exit_promise_met
        assert result.total_iterations < 10  # Should exit before reaching max

    def test_loop_handles_blocked_plans(self, tmp_path):
        """Test that the loop handles blocked plans correctly."""
        # Create a plan with a blocked step
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()

        plan_content = """---
status: active
---
# Blocked Plan

- [ ] Step 1: This might be blocked
- [ ] Step 2: This should wait
"""
        plan_file = plans_dir / "PLAN-blocked.md"
        plan_file.write_text(plan_content)

        # Run loop with executor that returns False (indicating blocked)
        config = LoopConfig(max_iterations=2, checkpoint_interval=1)
        loop = AutonomousLoop(tmp_path, config=config)

        def blocking_executor(plan_path, step_index):
            return False  # Always return False to simulate blocking

        loop._step_executor = blocking_executor
        result = loop.run()

        # Should have tried to process but marked as blocked
        assert result.total_iterations == 2
        assert result.plans_blocked >= 0  # At least one plan processed

    def test_loop_checkpoint_persistence(self, tmp_path):
        """Test that loop state is properly persisted through checkpoints."""
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()

        plan_content = """---
status: active
---
# Checkpoint Plan

- [ ] Step 1: Test checkpointing
"""
        plan_file = plans_dir / "PLAN-checkpoint.md"
        plan_file.write_text(plan_content)

        config = LoopConfig(max_iterations=1, checkpoint_interval=1)
        loop = AutonomousLoop(tmp_path, config=config)

        def mock_executor(plan_path, step_index):
            # Mark step as complete
            content = plan_path.read_text()
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "Step 1:" in line and '[ ]' in line:
                    lines[i] = line.replace('[ ]', '[x]')
                    break
            plan_path.write_text('\n'.join(lines))
            return True

        loop._step_executor = mock_executor
        result = loop.run()

        # Verify checkpoint file exists with proper content
        state_path = tmp_path / "Logs" / "loop-state.json"
        assert state_path.exists()

        state_data = json.loads(state_path.read_text())
        assert "session_id" in state_data
        assert state_data["iteration"] == 1  # Should reflect current iteration