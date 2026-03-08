"""Unit tests for Gold Tier CEO Briefing Engine."""

import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from agents.constants import COMPANY_HANDBOOK_FILE, NEEDS_ACTION_DIR
from agents.gold.briefing_engine import CEOBriefingEngine
from agents.gold.models import BriefingConfig


class TestShouldGenerate:
    """Test the briefing generation trigger logic."""

    def test_should_generate_correct_day_and_hour(self):
        """Test that should_generate returns True at the configured time."""
        config = BriefingConfig(briefing_day=6, briefing_hour=22)  # Sunday 22:00
        # Mock a Sunday at 22:30
        now = datetime(2026, 3, 8, 22, 30, tzinfo=timezone.utc)  # Sunday

        engine = CEOBriefingEngine(Path("."), config=config)

        # This should be True since it's Sunday after 22:00
        assert engine.should_generate(now)

    def test_should_generate_wrong_day_false(self):
        """Test that should_generate returns False on wrong day."""
        config = BriefingConfig(briefing_day=6, briefing_hour=22)  # Sunday 22:00
        # Mock a Monday at 22:30
        now = datetime(2026, 3, 2, 22, 30, tzinfo=timezone.utc)  # Monday

        engine = CEOBriefingEngine(Path("."), config=config)

        assert not engine.should_generate(now)

    def test_should_generate_before_hour_false(self):
        """Test that should_generate returns False before configured hour."""
        config = BriefingConfig(briefing_day=6, briefing_hour=22)  # Sunday 22:00
        # Mock a Sunday at 21:30
        now = datetime(2026, 3, 8, 21, 30, tzinfo=timezone.utc)  # Sunday before 22:00

        engine = CEOBriefingEngine(Path("."), config=config)

        assert not engine.should_generate(now)

    def test_should_generate_already_generated_this_week(self, tmp_path):
        """Test that should_generate returns False if briefing already exists for the week."""
        config = BriefingConfig(briefing_day=6, briefing_hour=22)  # Sunday 22:00
        now = datetime(2026, 3, 8, 22, 30, tzinfo=timezone.utc)  # Sunday

        # Create a briefing file for this week
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()
        briefing_file = needs_action / "CEO-Briefing-2026-W10.md"
        briefing_file.write_text("# Test Briefing")

        engine = CEOBriefingEngine(tmp_path, config=config)

        assert not engine.should_generate(now)

    def test_initialization_with_injected_odoo_client(self, tmp_path):
        """Test initializing CEOBriefingEngine with injected Odoo client."""
        # Create a mock Odoo client
        mock_odoo = Mock()
        mock_odoo.search_read.return_value = [
            {"id": 1, "amount_total": 1000.0}
        ]

        config = BriefingConfig()
        engine = CEOBriefingEngine(tmp_path, config=config, odoo_client=mock_odoo)

        assert engine._odoo is mock_odoo
        # Verify the mock is used when aggregating revenue
        revenue, unavailable = engine._aggregate_revenue()
        assert mock_odoo.search_read.called
        assert revenue == 1000.0


class TestBottleneckDetection:
    """Test bottleneck detection in /Needs_Action/ directory."""

    def test_detect_bottlenecks_finds_old_tasks(self, tmp_path):
        """Test that old tasks in Needs_Action are detected as bottlenecks."""
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        # Create an old task file (older than threshold)
        old_task = needs_action / "old_task.md"
        old_task.write_text("# Old Task\n\nThis is an old task.")

        # Set file modification time to be 50 hours ago (threshold is 48h by default)
        old_time = (datetime.now() - timedelta(hours=50)).timestamp()
        os.utime(old_task, (old_time, old_time))

        engine = CEOBriefingEngine(tmp_path)
        bottlenecks = engine._detect_bottlenecks()

        assert len(bottlenecks) == 1
        assert bottlenecks[0].filename == "old_task.md"
        assert bottlenecks[0].age_hours > 48  # Should be around 50 hours
        assert bottlenecks[0].summary == "Old Task"

    def test_detect_bottlenecks_ignores_new_tasks(self, tmp_path):
        """Test that recent tasks are not detected as bottlenecks."""
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        # Create a recent task file (younger than threshold)
        recent_task = needs_action / "recent_task.md"
        recent_task.write_text("# Recent Task")

        # Set file modification time to be 20 hours ago (less than 48h threshold)
        recent_time = (datetime.now() - timedelta(hours=20)).timestamp()
        os.utime(recent_task, (recent_time, recent_time))

        engine = CEOBriefingEngine(tmp_path)
        bottlenecks = engine._detect_bottlenecks()

        assert len(bottlenecks) == 0

    def test_detect_bottlenecks_extract_priority(self, tmp_path):
        """Test that priority is extracted from task files."""
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        # Create a task with priority
        task_with_priority = needs_action / "priority_task.md"
        task_with_priority.write_text("""---
priority: P0
---
# Critical Task

This is a critical task.
""")

        # Set file modification time to be 50 hours ago
        old_time = (datetime.now() - timedelta(hours=50)).timestamp()
        os.utime(task_with_priority, (old_time, old_time))

        engine = CEOBriefingEngine(tmp_path)
        bottlenecks = engine._detect_bottlenecks()

        assert len(bottlenecks) == 1
        assert bottlenecks[0].priority == "P0"

    def test_detect_bottlenecks_extract_summary_from_content(self, tmp_path):
        """Test that summary is extracted from file content."""
        needs_action = tmp_path / NEEDS_ACTION_DIR
        needs_action.mkdir()

        # Create a task with content that has a summary
        task = needs_action / "content_task.md"
        task.write_text("""---
priority: HIGH
---
# Task Title

This is the first line of content that should be used as summary.
More content here.
""")

        # Set file modification time to be 50 hours ago
        old_time = (datetime.now() - timedelta(hours=50)).timestamp()
        os.utime(task, (old_time, old_time))

        engine = CEOBriefingEngine(tmp_path)
        bottlenecks = engine._detect_bottlenecks()

        assert len(bottlenecks) == 1
        # The summary should be "Task Title" since it's the first header after frontmatter
        assert bottlenecks[0].summary == "Task Title"


class TestSubscriptionAudit:
    """Test subscription audit functionality."""

    def test_audit_subscriptions_finds_subscription_data(self, tmp_path):
        """Test that subscription audit parses subscription data from Company_Handbook."""
        handbook = tmp_path / COMPANY_HANDBOOK_FILE
        handbook.write_text("""
# Company Handbook

## Subscriptions

| Service | Cost | Utilization |
|---------|------|-------------|
| AWS | $500 | 15% |
| Azure | $300 | 5% |
| Google Cloud | $200 | 80% |

## Other Section

Not in subscriptions section.
""")

        engine = CEOBriefingEngine(tmp_path)
        findings = engine._audit_subscriptions()

        # Should find the underutilized services (AWS and Azure)
        assert len(findings) == 2

        # Check that AWS and Azure are flagged as underutilized
        service_names = {f.service_name for f in findings}
        assert "AWS" in service_names
        assert "Azure" in service_names

    def test_audit_subscriptions_ignores_well_utilized(self, tmp_path):
        """Test that well-utilized subscriptions are not flagged."""
        handbook = tmp_path / COMPANY_HANDBOOK_FILE
        handbook.write_text("""
# Company Handbook

## Subscriptions

| Service | Cost | Utilization |
|---------|------|-------------|
| Google Cloud | $200 | 80% |
| Office 365 | $100 | 95% |

## Other Section
""")

        engine = CEOBriefingEngine(tmp_path)
        findings = engine._audit_subscriptions()

        # Should not flag well-utilized services
        assert len(findings) == 0

    def test_audit_subscriptions_handles_invalid_data_gracefully(self, tmp_path):
        """Test that invalid subscription data doesn't crash the audit."""
        handbook = tmp_path / COMPANY_HANDBOOK_FILE
        handbook.write_text("""
# Company Handbook

## Subscriptions

| Service | Cost | Utilization |
|---------|------|-------------|
| Valid Service | $100 | 10% |
| Invalid Row | Not A Number | Not A Percentage |
| Another Valid | $200 | 5% |

## Other Section
""")

        engine = CEOBriefingEngine(tmp_path)
        findings = engine._audit_subscriptions()

        # Should handle invalid rows gracefully and still process valid ones
        assert len(findings) >= 1  # At least the valid services should be processed


class TestBriefingGeneration:
    """Test full briefing generation."""

    def test_generate_briefing_with_mock_odoo_client(self, tmp_path):
        """Test generating a briefing with a mock Odoo client."""
        # Mock an Odoo client
        mock_odoo = Mock()
        mock_odoo.search_read.return_value = [
            {"amount_total": 8000.0},
            {"amount_total": 2000.0}
        ]

        engine = CEOBriefingEngine(tmp_path, odoo_client=mock_odoo)
        briefing = engine.generate_briefing()

        # Check that revenue was calculated
        assert briefing.revenue_mtd == 10000.0  # 8000 + 2000
        assert briefing.revenue_delta_pct is not None  # Should calculate percentage against goal

    def test_generate_briefing_without_odoo_client(self, tmp_path):
        """Test generating a briefing without Odoo client (should handle gracefully)."""
        engine = CEOBriefingEngine(tmp_path, odoo_client=None)
        briefing = engine.generate_briefing()

        # Should have None for revenue data but still generate
        assert briefing.revenue_mtd is None
        assert "Revenue" in briefing.data_unavailable[0] if briefing.data_unavailable else True

    def test_write_briefing_creates_file(self, tmp_path):
        """Test that write_briefing creates a file in Needs_Action."""
        engine = CEOBriefingEngine(tmp_path)

        # Create a mock briefing
        from agents.gold.models import CEOBriefing, BottleneckTask, SubscriptionFinding
        briefing = CEOBriefing(
            briefing_id="BRIEFING-2026-W10",
            generated_at="2026-03-08T22:00:00Z",
            period_start="2026-03-02",
            period_end="2026-03-08",
            revenue_mtd=9500.0,
            revenue_goal=10000.0,
            revenue_delta_pct=-5.0,
            bottleneck_tasks=(),
            subscription_findings=(),
            data_unavailable=()
        )

        output_path = engine.write_briefing(briefing)

        # Check that file was created
        assert output_path.exists()
        assert "Monday Morning CEO Briefing" in output_path.read_text(encoding="utf-8")
        assert "CEO-Briefing-2026-W10.md" in str(output_path)


class TestBriefingConfig:
    """Test BriefingConfig functionality."""

    def test_default_config_values(self):
        """Test that BriefingConfig has expected default values."""
        config = BriefingConfig()

        assert config.briefing_day == 6  # Sunday
        assert config.briefing_hour == 22  # 22:00
        assert config.revenue_goal == 10000.0
        assert config.bottleneck_threshold_hours == 48.0
        assert config.utilization_threshold_pct == 30.0
        assert config.overpriced_threshold_pct == 20.0