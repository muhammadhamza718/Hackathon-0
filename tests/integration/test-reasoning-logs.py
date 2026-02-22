"""
Test: Reasoning Logs accuracy (T034)

Tests that reasoning logs are properly formatted with ISO-8601 timestamps,
maintain chronological order, and are preserved across sessions.

Setup: Create plan, execute steps, log entries
Assert: Each step completion generates timestamped log entry
Assert: Timestamps are ISO-8601 format
Assert: Logs preserve chronological order
"""

import logging
import pytest
import re
from pathlib import Path
from datetime import datetime
from agents.skills.managing_obsidian_vault.plan_manager import PlanManager

logger = logging.getLogger(__name__)


@pytest.fixture
def vault_tmp(tmp_path):
    """Create temporary vault directory for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    (vault / "Plans").mkdir()
    (vault / "Done").mkdir()
    (vault / "Done" / "Plans").mkdir()
    return vault


def is_iso8601_timestamp(timestamp_str: str) -> bool:
    """Check if string is valid ISO-8601 UTC timestamp."""
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
    return bool(re.match(pattern, timestamp_str))


def test_reasoning_logs_iso8601_timestamps(vault_tmp):
    """
    Test that all reasoning log entries have valid ISO-8601 timestamps.
    """
    pm = PlanManager(vault_tmp)

    plan_id = "TEST-2026-001"
    objective = "Test plan for logging"
    context = "Context for testing reasoning logs"
    steps = [
        "Step 1: First action",
        "Step 2: Second action",
        "Step 3: Third action"
    ]

    plan_path = pm.create_plan(
        task_id=plan_id,
        objective=objective,
        context=context,
        steps=steps,
        priority="medium"
    )

    plan = pm.load_plan(plan_id)
    initial_log_count = len(plan.reasoning_logs)
    assert initial_log_count >= 1  # Initial creation log

    # Add more reasoning logs through step completion
    pm.update_step(
        plan_id=plan_id,
        step_number=1,
        completed=True,
        log_entry="Completed first action successfully"
    )

    pm.append_reasoning_log(
        plan_id=plan_id,
        action="Verified step 1 output",
        rationale="Output matches expected format"
    )

    pm.update_step(
        plan_id=plan_id,
        step_number=2,
        completed=True,
        log_entry="Completed second action"
    )

    # Reload and check all logs
    updated_plan = pm.load_plan(plan_id)
    assert len(updated_plan.reasoning_logs) >= initial_log_count + 3

    # Validate each log entry has ISO-8601 timestamp
    iso8601_pattern = r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]'
    for log_entry in updated_plan.reasoning_logs:
        match = re.match(iso8601_pattern, log_entry)
        assert match is not None, f"Invalid timestamp format in log: {log_entry}"

        # Extract and validate timestamp
        timestamp_match = re.match(r'^\[(.+?)\]', log_entry)
        timestamp_str = timestamp_match.group(1)
        assert is_iso8601_timestamp(timestamp_str), f"Invalid ISO-8601 timestamp: {timestamp_str}"

    logger.info("✓ All reasoning logs have valid ISO-8601 timestamps")


def test_reasoning_logs_chronological_order(vault_tmp):
    """
    Test that reasoning logs maintain chronological order.
    """
    pm = PlanManager(vault_tmp)

    plan_id = "TEST-2026-002"
    objective = "Test chronological ordering"
    context = "Testing log order preservation"
    steps = ["Step 1", "Step 2", "Step 3", "Step 4"]

    plan_path = pm.create_plan(
        task_id=plan_id,
        objective=objective,
        context=context,
        steps=steps,
        priority="high"
    )

    # Add logs in sequence
    pm.append_reasoning_log(
        plan_id=plan_id,
        action="Initialized complex task",
        rationale="Multiple steps detected"
    )

    pm.update_step(
        plan_id=plan_id,
        step_number=1,
        completed=True,
        log_entry="Completed step 1"
    )

    pm.append_reasoning_log(
        plan_id=plan_id,
        action="Validated step 1 output",
        rationale="Output correct"
    )

    pm.update_step(
        plan_id=plan_id,
        step_number=2,
        completed=True,
        log_entry="Completed step 2"
    )

    # Extract timestamps
    updated_plan = pm.load_plan(plan_id)
    timestamps = []
    iso8601_pattern = r'^\[(.+?)\]'

    for log_entry in updated_plan.reasoning_logs:
        match = re.match(iso8601_pattern, log_entry)
        if match:
            timestamp_str = match.group(1)
            # Parse ISO-8601 to datetime for comparison
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            timestamps.append(dt)

    # Verify chronological order (non-strict, allowing equal timestamps)
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i + 1], \
            f"Logs out of order: {timestamps[i]} > {timestamps[i + 1]}"

    logger.info("✓ Reasoning logs maintain chronological order")


def test_reasoning_logs_preserved_across_load_save(vault_tmp):
    """
    Test that reasoning logs are preserved when plan is loaded and saved.
    """
    pm = PlanManager(vault_tmp)

    plan_id = "TEST-2026-003"
    objective = "Test log persistence"
    context = "Testing that logs survive load/save cycle"
    steps = ["Step 1", "Step 2"]

    plan_path = pm.create_plan(
        task_id=plan_id,
        objective=objective,
        context=context,
        steps=steps,
        priority="medium"
    )

    # Add initial logs
    initial_logs = []
    for i in range(3):
        pm.append_reasoning_log(
            plan_id=plan_id,
            action=f"Test action {i}",
            rationale=f"Test rationale {i}"
        )
        plan = pm.load_plan(plan_id)
        initial_logs.append(plan.reasoning_logs[-1])

    # Reload and verify all logs still present
    reloaded_plan = pm.load_plan(plan_id)
    for i, log in enumerate(initial_logs):
        assert log in reloaded_plan.reasoning_logs, \
            f"Log {i} lost after reload: {log}"

    # Make another change
    pm.update_step(
        plan_id=plan_id,
        step_number=1,
        completed=True,
        log_entry="Marked step 1 complete"
    )

    # Verify all logs (including new one) present
    final_plan = pm.load_plan(plan_id)
    assert len(final_plan.reasoning_logs) >= len(initial_logs) + 1

    for log in initial_logs:
        assert log in final_plan.reasoning_logs, \
            f"Original log lost: {log}"

    logger.info("✓ Reasoning logs preserved across load/save cycles")


def test_reasoning_logs_format_consistency(vault_tmp):
    """
    Test that all reasoning log entries follow consistent format:
    [ISO-TIMESTAMP] Agent: [action] or [ISO-TIMESTAMP] Agent: [action] — [rationale]
    """
    pm = PlanManager(vault_tmp)

    plan_id = "TEST-2026-004"
    objective = "Test format consistency"
    context = "Verify all logs follow standard format"
    steps = ["Step 1", "Step 2"]

    plan_path = pm.create_plan(
        task_id=plan_id,
        objective=objective,
        context=context,
        steps=steps,
        priority="low"
    )

    # Add logs through various operations
    pm.append_reasoning_log(
        plan_id=plan_id,
        action="Started execution",
        rationale="All prerequisites met"
    )

    pm.update_step(
        plan_id=plan_id,
        step_number=1,
        completed=True,
        log_entry="Step completed successfully"
    )

    pm.append_reasoning_log(
        plan_id=plan_id,
        action="Detected block",
        rationale="HITL step requires approval"
    )

    # Verify all logs match format
    updated_plan = pm.load_plan(plan_id)
    # Format: [ISO-TIMESTAMP] Agent: [action] or [ISO-TIMESTAMP] Agent: [action] — [rationale]
    format_pattern = r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]\s+Agent:\s+.+$'

    for log_entry in updated_plan.reasoning_logs:
        assert re.match(format_pattern, log_entry), \
            f"Log entry doesn't match standard format: {log_entry}"

    logger.info("✓ All reasoning logs follow consistent format")


def test_reasoning_logs_content_preservation(vault_tmp):
    """
    Test that log entry content (action and rationale) is preserved exactly.
    """
    pm = PlanManager(vault_tmp)

    plan_id = "TEST-2026-005"
    objective = "Test content preservation"
    context = "Verify log content is not modified"
    steps = ["Step 1"]

    plan_path = pm.create_plan(
        task_id=plan_id,
        objective=objective,
        context=context,
        steps=steps,
        priority="medium"
    )

    # Test with special characters and formatting
    test_action = "Processed invoice: $1,500 @ 15% discount"
    test_rationale = "Client A approved; includes tax (8.5%) and fees"

    pm.append_reasoning_log(
        plan_id=plan_id,
        action=test_action,
        rationale=test_rationale
    )

    updated_plan = pm.load_plan(plan_id)
    last_log = updated_plan.reasoning_logs[-1]

    # Extract action and rationale from log
    match = re.match(
        r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]\s+Agent:\s+(.+?)\s+—\s+(.+)$',
        last_log
    )
    assert match is not None

    extracted_action = match.group(1)
    extracted_rationale = match.group(2)

    assert extracted_action == test_action
    assert extracted_rationale == test_rationale

    logger.info("✓ Log entry content preserved exactly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
