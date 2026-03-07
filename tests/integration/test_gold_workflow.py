"""Integration tests for Gold Tier autonomous agent.

End-to-end tests for Gold Tier workflows including:
- Loop lifecycle
- Odoo integration
- Social media workflow
- Briefing generation
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from agents.gold.models import (
    GoldAuditEntry,
    LoopState,
    SocialDraft,
)
from agents.gold.audit_gold import GoldAuditLogger
from agents.gold.safety_gate import GoldSafetyGate
from agents.gold.resilient_executor import ResilientExecutor
from agents.gold.social_bridge import SocialBridge
from agents.gold.briefing_engine import CEOBriefingEngine, RevenueData
from agents.gold.revenue_analysis import RevenueAnalyzer, RevenuePoint
from agents.gold.subscription_tracker import (
    SubscriptionTracker,
    Subscription,
    SubscriptionUsage,
)


# ---------------------------------------------------------------------------
# Audit Workflow Integration Tests
# ---------------------------------------------------------------------------

class TestAuditWorkflowIntegration:
    """Integration tests for audit logging workflow."""

    def test_full_audit_roundtrip(self, tmp_path):
        """Test complete audit entry lifecycle."""
        logger = GoldAuditLogger(logs_dir=str(tmp_path))

        # Log multiple entries
        entry1 = logger.log_action(
            action="triage",
            rationale="Processing inbox",
            source_file="Inbox/task_001.md",
        )
        entry2 = logger.log_action(
            action="complete",
            rationale="Task completed",
            source_file="Needs_Action/task_001.md",
            result="success",
        )

        # Verify entries were logged
        counts = logger.count_by_action()
        assert counts.get("triage", 0) == 1
        assert counts.get("complete", 0) == 1

        # Verify result counts
        result_counts = logger.count_by_result()
        assert result_counts.get("success", 0) == 2


# ---------------------------------------------------------------------------
# Safety Gate Integration Tests
# ---------------------------------------------------------------------------

class TestSafetyGateIntegration:
    """Integration tests for HITL safety gate."""

    def test_approval_workflow(self, tmp_path):
        """Test complete approval workflow."""
        gate = GoldSafetyGate(approval_dir=str(tmp_path))

        # Create approval request
        request = gate.request_approval(
            action="odoo_write",
            rationale="Creating invoice",
            payload={
                "model": "account.move",
                "values": {"move_type": "out_invoice"},
            },
        )

        # Verify request is pending
        pending = gate.get_pending_requests()
        assert len(pending) == 1
        assert pending[0].request_id == request.request_id

        # Approve the request
        gate.approve(request.request_id)

        # Verify approval
        assert gate.is_approved(request.request_id)
        assert len(gate.get_pending_requests()) == 0


# ---------------------------------------------------------------------------
# Social Media Integration Tests
# ---------------------------------------------------------------------------

class TestSocialBridgeIntegration:
    """Integration tests for social media bridge."""

    def test_multi_platform_draft_creation(self):
        """Test creating drafts for multiple platforms."""
        bridge = SocialBridge()

        drafts = bridge.create_draft(
            content="Exciting product launch! 🚀",
            platforms=["X", "Facebook", "Instagram"],
            hashtags=["ProductLaunch", "Innovation"],
            rationale="Marketing campaign",
        )

        assert len(drafts) == 3
        assert "X" in drafts
        assert "Facebook" in drafts
        assert "Instagram" in drafts

        # Verify content adaptation
        x_content = drafts["X"].content
        instagram_content = drafts["Instagram"].content

        # Instagram should have hashtags at end
        assert "#ProductLaunch" in instagram_content

    def test_platform_limits(self):
        """Test getting platform limits."""
        bridge = SocialBridge()
        limits = bridge.get_platform_limits()

        assert "X" in limits
        assert limits["X"]["char_limit"] == 280
        assert limits["Instagram"]["char_limit"] == 2200


# ---------------------------------------------------------------------------
# Briefing Engine Integration Tests
# ---------------------------------------------------------------------------

class TestBriefingEngineIntegration:
    """Integration tests for CEO briefing engine."""

    def test_full_briefing_generation(self, tmp_path):
        """Test complete briefing generation workflow."""
        engine = CEOBriefingEngine(briefings_dir=str(tmp_path))

        revenue_data = RevenueData(
            mtd_revenue=8500.0,
            goal=10000.0,
            previous_month_same_period=7500.0,
        )

        briefing = engine.generate_briefing(
            revenue_data=revenue_data,
        )

        # Verify briefing content
        assert briefing.revenue_mtd == 8500.0
        assert briefing.revenue_goal == 10000.0
        assert briefing.revenue_delta_pct is not None
        assert briefing.revenue_delta_pct < 0  # Below goal

        # Save and verify
        output_path = engine.save_briefing(briefing)
        assert Path(output_path).exists()

        # Verify markdown rendering
        markdown = engine.render_markdown(briefing)
        assert "# CEO Weekly Briefing" in markdown
        assert "Revenue Analysis" in markdown

    def test_briefing_with_bottlenecks(self, tmp_path):
        """Test briefing with bottleneck tasks."""
        from agents.gold.models import BottleneckTask

        engine = CEOBriefingEngine(briefings_dir=str(tmp_path))

        bottlenecks = [
            BottleneckTask(
                filename="task_urgent.md",
                age_hours=72.5,
                priority="CRITICAL",
                summary="Urgent client request",
            ),
        ]

        briefing = engine.generate_briefing(
            revenue_data=RevenueData(mtd_revenue=10000.0),
            bottleneck_tasks=bottlenecks,
        )

        assert len(briefing.bottleneck_tasks) == 1
        assert briefing.bottleneck_tasks[0].priority == "CRITICAL"


# ---------------------------------------------------------------------------
# Revenue Analysis Integration Tests
# ---------------------------------------------------------------------------

class TestRevenueAnalysisIntegration:
    """Integration tests for revenue analysis."""

    def test_trend_analysis(self):
        """Test revenue trend analysis."""
        analyzer = RevenueAnalyzer()

        # Add sample data
        for i in range(10):
            date = (datetime.now(timezone.utc).replace(day=i+1)).strftime("%Y-%m-%d")
            analyzer.add_daily_revenue(date, 1000 + i * 100)

        trend = analyzer.analyze_trend(days=10)
        assert trend is not None
        assert trend.data_points == 10
        assert trend.trend_direction == "increasing"

    def test_period_comparison(self):
        """Test period-over-period comparison."""
        analyzer = RevenueAnalyzer()

        # Add data for two periods
        now = datetime.now(timezone.utc)
        for i in range(30):
            # Current period
            date = (now.replace(day=now.day - i)).strftime("%Y-%m-%d")
            analyzer.add_daily_revenue(date, 1000)

            # Previous period
            prev_date = (now.replace(day=now.day - 30 - i)).strftime("%Y-%m-%d")
            analyzer.add_daily_revenue(prev_date, 800)

        comparison = analyzer.compare_periods(current_days=30, previous_days=30)
        assert comparison is not None
        assert comparison.trend == "improved"
        assert comparison.pct_change > 0

    def test_mtd_calculation(self):
        """Test MTD revenue calculation."""
        analyzer = RevenueAnalyzer()

        # Add data for current month
        now = datetime.now(timezone.utc)
        for i in range(1, now.day + 1):
            date = now.replace(day=i).strftime("%Y-%m-%d")
            analyzer.add_daily_revenue(date, 500)

        mtd = analyzer.get_mtd_revenue()
        assert mtd == 500 * now.day


# ---------------------------------------------------------------------------
# Subscription Tracker Integration Tests
# ---------------------------------------------------------------------------

class TestSubscriptionTrackerIntegration:
    """Integration tests for subscription tracking."""

    def test_optimization_analysis(self, tmp_path):
        """Test subscription optimization analysis."""
        tracker = SubscriptionTracker(data_file=tmp_path / "subs.json")

        # Add subscriptions
        tracker.add_subscription(
            Subscription(
                name="TestService",
                monthly_cost=100.0,
                category="Software",
                status="active",
            )
        )

        # Add usage data (underused)
        tracker.update_usage(
            SubscriptionUsage(
                subscription_name="TestService",
                active_users=1,
                total_seats=10,
                usage_count_30d=2,
            )
        )

        # Get optimization findings
        findings = tracker.analyze_optimization()
        assert len(findings) >= 1
        assert any(f.finding_type == "underused" for f in findings)

    def test_cost_calculation(self, tmp_path):
        """Test total cost calculations."""
        tracker = SubscriptionTracker(data_file=tmp_path / "subs.json")

        tracker.add_subscription(
            Subscription(name="Service1", monthly_cost=50.0)
        )
        tracker.add_subscription(
            Subscription(name="Service2", monthly_cost=75.0)
        )

        assert tracker.get_total_monthly_cost() == 125.0
        assert tracker.get_total_annual_cost() == 1500.0


# ---------------------------------------------------------------------------
# Resilient Executor Integration Tests
# ---------------------------------------------------------------------------

class TestResilientExecutorIntegration:
    """Integration tests for resilient executor."""

    def test_retry_with_backoff(self):
        """Test retry with exponential backoff."""
        executor = ResilientExecutor()

        call_times = []

        def track_calls():
            call_times.append(datetime.now(timezone.utc))
            if len(call_times) < 2:
                raise ValueError("Temporary failure")
            return "success"

        result = executor.execute(
            track_calls,
            operation_name="test_backoff",
        )

        assert result.success
        assert len(call_times) == 2
        # Verify there was a delay between calls
        if len(call_times) >= 2:
            delay = (call_times[1] - call_times[0]).total_seconds()
            assert delay >= 0.9  # At least 0.9 seconds (base delay)


# ---------------------------------------------------------------------------
# Loop State Integration Tests
# ---------------------------------------------------------------------------

class TestLoopStateIntegration:
    """Integration tests for loop state management."""

    def test_state_serialization_roundtrip(self):
        """Test state serialization and deserialization."""
        original = LoopState(
            session_id="test_session",
            iteration=42,
            active_plan_id="plan_123",
            active_step_index=5,
            blocked_plans=("plan_456", "plan_789"),
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = LoopState.from_dict(data)

        assert restored.session_id == original.session_id
        assert restored.iteration == original.iteration
        assert restored.active_plan_id == original.active_plan_id
        assert restored.blocked_plans == original.blocked_plans


# ---------------------------------------------------------------------------
# End-to-End Workflow Tests
# ---------------------------------------------------------------------------

class TestEndToEndWorkflow:
    """End-to-end workflow tests."""

    def test_social_post_workflow(self, tmp_path):
        """Test complete social post workflow."""
        # Create draft
        bridge = SocialBridge()
        drafts = bridge.create_draft(
            content="New feature release! 🎉",
            platforms=["X"],
            hashtags=["Release", "Feature"],
            rationale="Product announcement",
        )

        # Create approval request
        gate = GoldSafetyGate(approval_dir=str(tmp_path))
        draft = drafts["X"]

        request = gate.request_approval(
            action="social_post",
            rationale=draft.rationale,
            payload={
                "platform": draft.platform,
                "content": draft.content,
            },
        )

        # Approve
        gate.approve(request.request_id)

        # Verify workflow completed
        assert gate.is_approved(request.request_id)

    def test_briefing_with_all_data(self, tmp_path):
        """Test briefing generation with all data sources."""
        from agents.gold.models import BottleneckTask, SubscriptionFinding

        engine = CEOBriefingEngine(briefings_dir=str(tmp_path))

        briefing = engine.generate_briefing(
            revenue_data=RevenueData(
                mtd_revenue=9500.0,
                goal=10000.0,
            ),
            bottleneck_tasks=[
                BottleneckTask(
                    filename="urgent.md",
                    age_hours=48.0,
                    priority="P0",
                    summary="Urgent task",
                ),
            ],
            subscription_findings=[
                SubscriptionFinding(
                    service_name="UnusedService",
                    monthly_cost=50.0,
                    finding_type="unused",
                    recommendation="Cancel subscription",
                    potential_savings=50.0,
                ),
            ],
        )

        # Save in both formats
        md_path = engine.save_briefing(briefing)
        json_path = engine.save_json(briefing)

        assert Path(md_path).exists()
        assert Path(json_path).exists()

        # Verify content
        markdown = engine.render_markdown(briefing)
        assert "Revenue Analysis" in markdown
        assert "Task Bottlenecks" in markdown
        assert "Subscription Optimization" in markdown
