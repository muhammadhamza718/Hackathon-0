"""Integration tests for Gold Tier CEO Briefing workflow."""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from agents.constants import COMPANY_HANDBOOK_FILE, NEEDS_ACTION_DIR
from agents.gold.briefing_engine import CEOBriefingEngine
from agents.gold.models import BriefingConfig


class TestGoldBriefingWorkflow:
    """Test the complete CEO briefing workflow."""

    def test_full_briefing_generation_with_mock_data(self, tmp_path):
        """Test generating a full briefing with mock data sources."""
        # Setup vault directories
        needs_action_dir = tmp_path / NEEDS_ACTION_DIR
        needs_action_dir.mkdir()

        # Create some old tasks to trigger bottleneck detection
        old_task = needs_action_dir / "old_task.md"
        old_task.write_text("""---
priority: P0
---
# Critical Old Task

This task is very important and has been pending for a long time.
""")

        # Set file modification time to be 50 hours ago (threshold is 48h)
        old_time = (datetime.now() - timedelta(hours=50)).timestamp()
        os.utime(old_task, (old_time, old_time))

        # Create a Company Handbook with subscription data
        handbook = tmp_path / COMPANY_HANDBOOK_FILE
        handbook.write_text("""
# Company Handbook

## Subscriptions

| Service | Cost | Utilization |
|---------|------|-------------|
| AWS | $500 | 10% |
| Azure | $300 | 5% |
| Google Cloud | $200 | 80% |
| Office 365 | $100 | 95% |

## Other Section

Not relevant to subscriptions.
""")

        # Mock an Odoo client that returns some revenue data
        mock_odoo = Mock()
        mock_odoo.search_read.return_value = [
            {"amount_total": 8000.0, "name": "Invoice 1"},
            {"amount_total": 2000.0, "name": "Invoice 2"},
            {"amount_total": 1500.0, "name": "Invoice 3"}
        ]

        # Create briefing engine with custom config
        config = BriefingConfig(
            briefing_day=6,  # Sunday
            briefing_hour=22,  # 22:00
            revenue_goal=10000.0,
            bottleneck_threshold_hours=48.0,
            utilization_threshold_pct=30.0
        )

        engine = CEOBriefingEngine(tmp_path, config=config, odoo_client=mock_odoo)

        # Generate briefing
        briefing = engine.generate_briefing()

        # Verify briefing content
        assert briefing.briefing_id.startswith("BRIEFING-")
        assert briefing.revenue_mtd == 11500.0  # 8000 + 2000 + 1500
        assert briefing.revenue_goal == 10000.0
        assert briefing.revenue_delta_pct is not None  # Should be calculated
        assert len(briefing.bottleneck_tasks) >= 1  # Should find the old task
        assert len(briefing.subscription_findings) >= 1  # Should find underutilized services

        # Write the briefing to vault
        output_path = engine.write_briefing(briefing)

        # Verify file was created in Needs_Action
        assert output_path.exists()
        assert "Monday Morning CEO Briefing" in output_path.read_text()
        assert NEEDS_ACTION_DIR in str(output_path)

    def test_briefing_generation_with_no_odoo_data(self, tmp_path):
        """Test briefing generation when Odoo is unavailable."""
        # Create engine without Odoo client
        engine = CEOBriefingEngine(tmp_path, odoo_client=None)

        # Generate briefing
        briefing = engine.generate_briefing()

        # Should handle missing revenue data gracefully
        assert briefing.revenue_mtd is None
        assert any("Odoo" in note for note in briefing.data_unavailable) if briefing.data_unavailable else True

    def test_briefing_generation_with_no_handbook(self, tmp_path):
        """Test briefing generation when Company Handbook doesn't exist."""
        # Don't create Company Handbook file

        # Create engine
        engine = CEOBriefingEngine(tmp_path)

        # Generate briefing
        briefing = engine.generate_briefing()

        # Should handle missing subscription data gracefully
        assert len(briefing.subscription_findings) == 0

    def test_briefing_generation_with_empty_needs_action(self, tmp_path):
        """Test briefing generation when Needs_Action is empty."""
        # Create empty Needs_Action directory
        needs_action_dir = tmp_path / NEEDS_ACTION_DIR
        needs_action_dir.mkdir()

        # Create engine
        engine = CEOBriefingEngine(tmp_path)

        # Generate briefing
        briefing = engine.generate_briefing()

        # Should have no bottlenecks
        assert len(briefing.bottleneck_tasks) == 0

    def test_should_generate_logic(self, tmp_path):
        """Test the should_generate logic."""
        # Create engine with Sunday 22:00 configuration
        config = BriefingConfig(briefing_day=6, briefing_hour=22)  # Sunday 22:00
        engine = CEOBriefingEngine(tmp_path, config=config)

        # Test with a Sunday at 22:30
        sunday_evening = datetime(2026, 3, 8, 22, 30, tzinfo=timezone.utc)  # Sunday

        # Should generate if no briefing exists for the week
        assert engine.should_generate(sunday_evening)

        # Create a briefing file for this week
        needs_action_dir = tmp_path / NEEDS_ACTION_DIR
        needs_action_dir.mkdir(exist_ok=True)
        briefing_file = needs_action_dir / "CEO-Briefing-2026-W10.md"
        briefing_file.write_text("# Test Briefing")

        # Should not generate since briefing already exists for the week
        assert not engine.should_generate(sunday_evening)

    def test_briefing_generation_with_realistic_scenario(self, tmp_path):
        """Test briefing generation with a realistic scenario."""
        # Setup vault directories
        needs_action_dir = tmp_path / NEEDS_ACTION_DIR
        needs_action_dir.mkdir()

        # Create multiple old tasks with different priorities
        high_priority_task = needs_action_dir / "high_priority_task.md"
        high_priority_task.write_text("""---
priority: P0
---
# Critical Issue

This is a critical issue that needs immediate attention.
""")

        medium_priority_task = needs_action_dir / "medium_priority_task.md"
        medium_priority_task.write_text("""---
priority: P1
---
# Medium Priority Task

This task is moderately important.
""")

        # Set modification times
        old_time = (datetime.now() - timedelta(hours=60)).timestamp()  # 60 hours ago
        os.utime(high_priority_task, (old_time, old_time))
        os.utime(medium_priority_task, (old_time, old_time))

        # Create Company Handbook with various subscription scenarios
        handbook = tmp_path / COMPANY_HANDBOOK_FILE
        handbook.write_text("""
# Company Handbook

## Subscriptions

| Service | Cost | Utilization |
|---------|------|-------------|
| AWS | $1000 | 10% |  # Underutilized
| Azure | $500 | 90% |   # Well utilized
| Google Cloud | $300 | 5% |  # Underutilized
| Office 365 | $200 | 100% | # Well utilized
| Slack | $150 | 20% |   # Underutilized

## Other Section
""")

        # Mock Odoo client with realistic revenue data
        mock_odoo = Mock()
        mock_odoo.search_read.return_value = [
            {"amount_total": 9500.0, "name": "Invoice 1"},
        ]

        config = BriefingConfig(
            briefing_day=6,  # Sunday
            briefing_hour=22,  # 22:00
            revenue_goal=10000.0,
            bottleneck_threshold_hours=48.0,
            utilization_threshold_pct=30.0
        )

        engine = CEOBriefingEngine(tmp_path, config=config, odoo_client=mock_odoo)
        briefing = engine.generate_briefing()

        # Verify all sections have appropriate data
        assert briefing.revenue_mtd == 9500.0
        assert len(briefing.bottleneck_tasks) == 2  # Both old tasks should be detected
        assert len(briefing.subscription_findings) == 3  # AWS, Google Cloud, Slack should be flagged

        # The high priority task should come first
        assert briefing.bottleneck_tasks[0].priority == "P0"
        assert "Critical Issue" in briefing.bottleneck_tasks[0].summary

        # Write and verify file content
        output_path = engine.write_briefing(briefing)
        content = output_path.read_text(encoding="utf-8")

        # Should contain all the key sections
        assert "Monday Morning CEO Briefing" in content
        assert "Revenue (MTD vs Goal)" in content
        assert "Task Bottlenecks" in content
        assert "Subscription Optimizations" in content
        assert "Critical Issue" in content
        assert "AWS" in content

    def test_briefing_config_customization(self, tmp_path):
        """Test briefing generation with custom configuration."""
        # Create custom config with different thresholds
        config = BriefingConfig(
            briefing_day=0,  # Monday
            briefing_hour=10,  # 10:00 AM
            revenue_goal=5000.0,
            bottleneck_threshold_hours=24.0,  # Shorter threshold
            utilization_threshold_pct=20.0   # Different utilization threshold
        )

        # Mock Odoo client
        mock_odoo = Mock()
        mock_odoo.search_read.return_value = [{"amount_total": 4500.0}]

        engine = CEOBriefingEngine(tmp_path, config=config, odoo_client=mock_odoo)

        # Generate briefing
        briefing = engine.generate_briefing()

        # Verify custom config values are reflected
        assert briefing.revenue_goal == 5000.0
        assert briefing.revenue_mtd == 4500.0

        # Verify the should_generate logic respects custom config
        monday_morning = datetime(2026, 3, 2, 10, 30, tzinfo=timezone.utc)  # Monday 10:30
        assert engine.should_generate(monday_morning)