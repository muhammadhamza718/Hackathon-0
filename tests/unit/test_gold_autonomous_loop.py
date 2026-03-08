"""Unit tests for the Ralph Wiggum autonomous loop."""

import json
import signal
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agents.constants import DONE_DIR, LOGS_DIR, LOOP_STATE_FILE, NEEDS_ACTION_DIR, PLANS_DIR
from agents.exceptions import StateCorruptionError
from agents.gold.autonomous_loop import AutonomousLoop
from agents.gold.models import LoopConfig, LoopState
from agents.plan_parser import PlanStep


class TestAutonomousLoopInitialization:
    """Test AutonomousLoop initialization and configuration."""

    def test_init_with_defaults(self, tmp_path):
        """Test initialization with default configuration."""
        loop = AutonomousLoop(tmp_path)

        assert loop.vault_root == tmp_path
        assert isinstance(loop.config, LoopConfig)
        assert loop.config.max_iterations == 1000

    def test_init_with_custom_config(self, tmp_path):
        """Test initialization with custom configuration."""
        config = LoopConfig(max_iterations=50, checkpoint_interval=5)
        loop = AutonomousLoop(tmp_path, config=config)

        assert loop.config == config

    def test_signal_handlers_registered(self, tmp_path):
        """Test that signal handlers are registered."""
        with patch('signal.signal'), patch('atexit.register'):
            loop = AutonomousLoop(tmp_path)

            # Verify internal state is set up
            assert hasattr(loop, '_running')
            assert loop._running is True


class TestLoopStatePersistence:
    """Test state checkpointing and resumption."""

    def test_checkpoint_creates_file(self, tmp_path):
        """Test that checkpoint creates the state file."""
        loop = AutonomousLoop(tmp_path)
        loop._state = LoopState(session_id="test-session", iteration=5)

        loop.checkpoint()

        state_path = tmp_path / LOGS_DIR / LOOP_STATE_FILE
        assert state_path.exists()

    def test_checkpoint_updates_timestamp(self, tmp_path):
        """Test that checkpoint updates the last_checkpoint field."""
        loop = AutonomousLoop(tmp_path)
        initial_state = LoopState(session_id="test-session", iteration=0)
        loop._state = initial_state

        loop.checkpoint()

        state_path = tmp_path / LOGS_DIR / LOOP_STATE_FILE
        data = json.loads(state_path.read_text())

        assert data["last_checkpoint"] != ""
        assert data["session_id"] == "test-session"
        assert data["iteration"] == 0  # Should preserve original state

    def test_resume_from_existing_state(self, tmp_path):
        """Test resuming from an existing state file."""
        # Create initial state
        logs_dir = tmp_path / LOGS_DIR
        logs_dir.mkdir()
        state_path = logs_dir / LOOP_STATE_FILE

        initial_state = {
            "session_id": "test-session",
            "iteration": 10,
            "active_plan_id": "PLAN-test",
            "active_step_index": 2,
            "blocked_plans": ["PLAN-other"],
            "last_checkpoint": "2026-03-06T10:00:00Z",
            "exit_promise_met": False
        }
        state_path.write_text(json.dumps(initial_state))

        loop = AutonomousLoop(tmp_path)
        restored = loop.resume()

        assert restored is not None
        assert restored.session_id == "test-session"
        assert restored.iteration == 10
        assert restored.active_plan_id == "PLAN-test"
        assert restored.active_step_index == 2
        assert restored.blocked_plans == ("PLAN-other",)

    def test_resume_no_file_creates_fresh_session(self, tmp_path):
        """Test that resume creates a fresh session when no state file exists."""
        loop = AutonomousLoop(tmp_path)
        result = loop.resume()

        # Should create a new session with generated ID
        assert result is not None
        assert result.session_id != ""
        assert result.iteration == 0
        assert result.active_plan_id is None

    def test_resume_corrupted_file_raises_state_corruption_error(self, tmp_path):
        """Test that resume raises StateCorruptionError for corrupted files."""
        logs_dir = tmp_path / LOGS_DIR
        logs_dir.mkdir()
        state_path = logs_dir / LOOP_STATE_FILE
        state_path.write_text("invalid json content")

        loop = AutonomousLoop(tmp_path)
        
        with pytest.raises(StateCorruptionError) as exc_info:
            loop.resume()
        
        assert "invalid_json" in str(exc_info.value.corruption_type)
        assert "loop-state.json" in exc_info.value.state_path


class TestExitPromise:
    """Test exit promise logic."""

    def test_exit_promise_empty_needs_action_and_complete_plans(self, tmp_path):
        """Test exit promise when all plans are complete and needs_action is empty."""
        # Create empty needs_action directory
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        # Create plans directory with no incomplete plans
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()
        # Create a complete plan
        complete_plan = plans_dir / "PLAN-complete.md"
        complete_plan.write_text("""---
status: complete
---
# Complete Plan

- [x] Step 1
- [x] Step 2
""")

        loop = AutonomousLoop(tmp_path)
        assert loop.is_exit_promise_met()


    def test_exit_promise_incomplete_plan_blocks_exit(self, tmp_path):
        """Test that incomplete plans prevent exit promise."""
        plans_dir = tmp_path / PLANS_DIR
        plans_dir.mkdir()
        # Create an incomplete plan (has active status and at least one pending step)
        incomplete_plan = plans_dir / "PLAN-incomplete.md"
        incomplete_plan.write_text("""---
status: active
---
# Incomplete Plan

- [ ] Step 1
- [x] Step 2
""")

        loop = AutonomousLoop(tmp_path)
        assert not loop.is_exit_promise_met()

        loop = AutonomousLoop(tmp_path)
        assert not loop.is_exit_promise_met()

    def test_exit_promise_needs_action_items_block_exit(self, tmp_path):
        """Test that items in needs_action prevent exit promise."""
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()
        # Create an item in needs_action
        item = needs_action / "task.md"
        item.write_text("# Task")

        loop = AutonomousLoop(tmp_path)
        assert not loop.is_exit_promise_met()


class TestMainLoop:
    """Test the main loop execution."""

    def test_run_initializes_new_session(self, tmp_path):
        """Test that run initializes a new session when no state exists."""
        # Create a needs_action item so the loop has work to do
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()
        item = needs_action / "task.md"
        item.write_text("# Task")

        loop = AutonomousLoop(tmp_path, config=LoopConfig(max_iterations=1))

        result = loop.run()

        assert result.total_iterations == 1
        # Exit promise is met after processing the task
        assert result.exit_promise_met

    def test_run_resumes_existing_session(self, tmp_path):
        """Test that run resumes from existing state."""
        # Create initial state
        logs_dir = tmp_path / LOGS_DIR
        logs_dir.mkdir()
        state_path = logs_dir / LOOP_STATE_FILE
        initial_state = {
            "session_id": "test-session",
            "iteration": 5,
            "active_plan_id": None,
            "active_step_index": None,
            "blocked_plans": [],
            "last_checkpoint": "2026-03-06T10:00:00Z",
            "exit_promise_met": False
        }
        state_path.write_text(json.dumps(initial_state))

        # Create many needs_action items so the loop runs for multiple iterations
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()
        for i in range(20):
            item = needs_action / f"task{i}.md"
            item.write_text(f"# Task {i}")

        # max_iterations must be > starting iteration for loop to run
        loop = AutonomousLoop(tmp_path, config=LoopConfig(max_iterations=8))

        result = loop.run()

        # Loop starts at iteration 5, processes all tasks in iteration 5,
        # then checks exit promise at start of iteration 6 and exits
        assert result.total_iterations == 6
        assert result.exit_promise_met
        assert result.tasks_completed == 20

    def test_run_processes_needs_action_items(self, tmp_path):
        """Test that run processes items in needs_action directory."""
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()
        item = needs_action / "task1.md"
        item.write_text("# Task 1")

        done_dir = tmp_path / DONE_DIR
        done_dir.mkdir(exist_ok=True)

        loop = AutonomousLoop(tmp_path, config=LoopConfig(max_iterations=1))

        result = loop.run()

        # Item should be moved to Done
        assert not item.exists()
        assert (done_dir / "task1.md").exists()
        assert result.tasks_completed >= 1

    def test_run_checkpoint_interval(self, tmp_path):
        """Test that checkpoints happen at specified intervals."""
        # Create needs_action items
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()
        for i in range(5):
            item = needs_action / f"task{i}.md"
            item.write_text(f"# Task {i}")

        loop = AutonomousLoop(tmp_path, config=LoopConfig(max_iterations=5, checkpoint_interval=2))

        result = loop.run()

        # Loop processes all tasks in first iteration, then continues until max_iterations or exit promise
        # Since tasks are done, exit promise is met after iteration 1
        assert result.total_iterations >= 1

        # Check that state was saved
        state_path = tmp_path / LOGS_DIR / LOOP_STATE_FILE
        assert state_path.exists()
        # Verify checkpoint was written
        import json
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        assert state_data["iteration"] == result.total_iterations


class TestSignalHandling:
    """Test signal handler functionality."""

    def test_signal_handler_stops_loop(self, tmp_path):
        """Test that signal handler stops the loop."""
        # Initialize state so checkpoint has something to save
        loop = AutonomousLoop(tmp_path, config=LoopConfig(max_iterations=100))
        loop._state = LoopState(session_id="test", iteration=1)

        # Simulate signal
        loop._signal_handler(signal.SIGINT, None)

        assert not loop._running
        # State should be checkpointed
        state_path = tmp_path / LOGS_DIR / LOOP_STATE_FILE
        assert state_path.exists()

    def test_atexit_handler_checkpoints_state(self, tmp_path):
        """Test that atexit handler checkpoints state."""
        loop = AutonomousLoop(tmp_path)
        loop._state = LoopState(session_id="test", iteration=1)

        loop._on_exit()

        state_path = tmp_path / LOGS_DIR / LOOP_STATE_FILE
        assert state_path.exists()