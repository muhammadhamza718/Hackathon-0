"""CEO Briefing Engine for weekly executive summaries.

Generates comprehensive Monday morning briefings including:
- Revenue MTD vs Goal with variance analysis
- Task bottlenecks and aging analysis
- Subscription optimization recommendations
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .config import BriefingConfig
from .models import (
    BottleneckTask,
    CEOBriefing,
    SubscriptionFinding,
)

logger = logging.getLogger(__name__)


@dataclass
class RevenueData:
    """Revenue data for briefing."""

    mtd_revenue: float = 0.0
    goal: float = 10000.0
    previous_month_same_period: float = 0.0
    currency: str = "USD"

    @property
    def variance(self) -> float:
        """Calculate variance from goal."""
        return self.mtd_revenue - self.goal

    @property
    def variance_pct(self) -> float:
        """Calculate variance percentage."""
        if self.goal == 0:
            return 0.0
        return (self.variance / self.goal) * 100

    @property
    def achievement_pct(self) -> float:
        """Calculate achievement percentage."""
        if self.goal == 0:
            return 0.0
        return (self.mtd_revenue / self.goal) * 100

    @property
    def yoy_growth_pct(self) -> float:
        """Calculate year-over-year growth."""
        if self.previous_month_same_period == 0:
            return 0.0
        return (
            (self.mtd_revenue - self.previous_month_same_period)
            / self.previous_month_same_period
        ) * 100


@dataclass
class BriefingSection:
    """A section of the CEO briefing."""

    title: str
    content: str
    priority: str = "normal"  # normal, high, critical
    data: dict[str, Any] = field(default_factory=dict)


class CEOBriefingEngine:
    """Engine for generating CEO briefings.

    Features:
    - Revenue analysis with variance
    - Task bottleneck detection
    - Subscription optimization
    - Automated markdown generation
    """

    def __init__(
        self,
        config: BriefingConfig | None = None,
        briefings_dir: str = "Briefings",
    ):
        """Initialize the briefing engine.

        Args:
            config: Briefing configuration.
            briefings_dir: Directory for storing briefings.
        """
        self.config = config or BriefingConfig.from_env()
        self.briefings_dir = Path(briefings_dir)
        self.briefings_dir.mkdir(parents=True, exist_ok=True)

    def generate_briefing(
        self,
        revenue_data: RevenueData | None = None,
        bottleneck_tasks: list[BottleneckTask] | None = None,
        subscription_findings: list[SubscriptionFinding] | None = None,
        data_unavailable: list[str] | None = None,
    ) -> CEOBriefing:
        """Generate a CEO briefing.

        Args:
            revenue_data: Revenue data for the period.
            bottleneck_tasks: List of bottleneck tasks.
            subscription_findings: List of subscription findings.
            data_unavailable: List of unavailable data sources.

        Returns:
            Generated CEO briefing.
        """
        now = datetime.now(timezone.utc)
        briefing_id = f"briefing_{now.strftime('%Y%m%d')}"

        # Calculate period (current month to date)
        period_start = now.replace(day=1).strftime("%Y-%m-%d")
        period_end = now.strftime("%Y-%m-%d")

        briefing = CEOBriefing(
            briefing_id=briefing_id,
            generated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            period_start=period_start,
            period_end=period_end,
            revenue_mtd=revenue_data.mtd_revenue if revenue_data else None,
            revenue_goal=self.config.revenue_goal,
            revenue_delta_pct=(
                revenue_data.variance_pct if revenue_data else None
            ),
            bottleneck_tasks=tuple(bottleneck_tasks or []),
            subscription_findings=tuple(subscription_findings or []),
            data_unavailable=tuple(data_unavailable or []),
        )

        logger.info(f"Generated briefing {briefing_id}")
        return briefing

    def render_markdown(
        self, briefing: CEOBriefing
    ) -> str:
        """Render briefing as markdown.

        Args:
            briefing: The briefing to render.

        Returns:
            Markdown string.
        """
        lines = [
            "# CEO Weekly Briefing",
            "",
            f"**Generated:** {briefing.generated_at}",
            f"**Period:** {briefing.period_start} to {briefing.period_end}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
        ]

        # Revenue Section
        lines.extend(self._render_revenue_section(briefing))

        # Bottleneck Tasks Section
        lines.extend(self._render_bottleneck_section(briefing))

        # Subscription Findings Section
        lines.extend(self._render_subscription_section(briefing))

        # Data Unavailable Section
        if briefing.data_unavailable:
            lines.extend(self._render_unavailable_section(briefing))

        lines.extend([
            "",
            "---",
            "",
            "*This briefing was automatically generated by the Gold Tier Autonomous Agent.*",
        ])

        return "\n".join(lines)

    def _render_revenue_section(
        self, briefing: CEOBriefing
    ) -> list[str]:
        """Render revenue section."""
        lines = ["## Revenue Analysis", ""]

        if briefing.revenue_mtd is not None:
            goal = briefing.revenue_goal
            mtd = briefing.revenue_mtd
            delta = briefing.revenue_delta_pct or 0

            status = "✅" if delta >= 0 else "⚠️"

            lines.extend([
                f"{status} **Month-to-Date Revenue:** ${mtd:,.2f}",
                f"**Goal:** ${goal:,.2f}",
                f"**Variance:** ${mtd - goal:,.2f} ({delta:+.1f}%)",
                "",
            ])

            if delta < -20:
                lines.append(
                    "🚨 **CRITICAL:** Revenue is more than 20% below goal. Immediate action required."
                )
                lines.append("")
            elif delta < -10:
                lines.append(
                    "⚠️ **WARNING:** Revenue is more than 10% below goal. Review pipeline."
                )
                lines.append("")
        else:
            lines.append("*Revenue data unavailable*")
            lines.append("")

        return lines

    def _render_bottleneck_section(
        self, briefing: CEOBriefing
    ) -> list[str]:
        """Render bottleneck tasks section."""
        lines = ["## Task Bottlenecks", ""]

        if briefing.bottleneck_tasks:
            lines.append(
                f"**{len(briefing.bottleneck_tasks)} tasks** require attention:"
            )
            lines.append("")

            for i, task in enumerate(briefing.bottleneck_tasks, 1):
                priority_marker = (
                    "🔴"
                    if task.priority in ("CRITICAL", "P0")
                    else "🟡"
                )
                lines.extend([
                    f"{i}. {priority_marker} **{task.filename}**",
                    f"   - Priority: {task.priority}",
                    f"   - Age: {task.age_hours:.1f} hours",
                    f"   - Summary: {task.summary}",
                    "",
                ])
        else:
            lines.append("✅ No bottleneck tasks detected.")
            lines.append("")

        return lines

    def _render_subscription_section(
        self, briefing: CEOBriefing
    ) -> list[str]:
        """Render subscription findings section."""
        lines = ["## Subscription Optimization", ""]

        if briefing.subscription_findings:
            total_savings = sum(
                f.potential_savings for f in briefing.subscription_findings
            )

            lines.append(
                f"**{len(briefing.subscription_findings)} optimization opportunities** identified:"
            )
            lines.append("")
            lines.append(
                f"**Potential Monthly Savings:** ${total_savings:,.2f}"
            )
            lines.append("")

            for i, finding in enumerate(
                briefing.subscription_findings, 1
            ):
                lines.extend([
                    f"{i}. **{finding.service_name}**",
                    f"   - Type: {finding.finding_type}",
                    f"   - Current Cost: ${finding.monthly_cost:,.2f}/month",
                    f"   - Potential Savings: ${finding.potential_savings:,.2f}/month",
                    f"   - Recommendation: {finding.recommendation}",
                    "",
                ])
        else:
            lines.append("✅ No subscription optimization opportunities found.")
            lines.append("")

        return lines

    def _render_unavailable_section(
        self, briefing: CEOBriefing
    ) -> list[str]:
        """Render unavailable data section."""
        lines = ["## Data Availability", ""]
        lines.append("The following data sources were unavailable:")
        lines.append("")

        for source in briefing.data_unavailable:
            lines.append(f"- {source}")

        lines.append("")
        return lines

    def save_briefing(
        self, briefing: CEOBriefing, output_path: str | Path | None = None
    ) -> str:
        """Save briefing to file.

        Args:
            briefing: The briefing to save.
            output_path: Optional output path.

        Returns:
            Path to saved file.
        """
        if output_path is None:
            output_path = self.briefings_dir / f"{briefing.briefing_id}.md"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        markdown = self.render_markdown(briefing)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        briefing.output_path = str(output_path)
        logger.info(f"Saved briefing to {output_path}")

        return str(output_path)

    def save_json(
        self, briefing: CEOBriefing, output_path: str | Path | None = None
    ) -> str:
        """Save briefing as JSON.

        Args:
            briefing: The briefing to save.
            output_path: Optional output path.

        Returns:
            Path to saved file.
        """
        if output_path is None:
            output_path = self.briefings_dir / f"{briefing.briefing_id}.json"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        briefing_dict = {
            "briefing_id": briefing.briefing_id,
            "generated_at": briefing.generated_at,
            "period_start": briefing.period_start,
            "period_end": briefing.period_end,
            "revenue_mtd": briefing.revenue_mtd,
            "revenue_goal": briefing.revenue_goal,
            "revenue_delta_pct": briefing.revenue_delta_pct,
            "bottleneck_tasks": [
                {
                    "filename": t.filename,
                    "age_hours": t.age_hours,
                    "priority": t.priority,
                    "summary": t.summary,
                }
                for t in briefing.bottleneck_tasks
            ],
            "subscription_findings": [
                {
                    "service_name": f.service_name,
                    "monthly_cost": f.monthly_cost,
                    "utilization_pct": f.utilization_pct,
                    "finding_type": f.finding_type,
                    "recommendation": f.recommendation,
                    "potential_savings": f.potential_savings,
                }
                for f in briefing.subscription_findings
            ],
            "data_unavailable": list(briefing.data_unavailable),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(briefing_dict, f, indent=2)

        logger.info(f"Saved briefing JSON to {output_path}")
        return str(output_path)

    def get_briefing_history(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get list of recent briefings.

        Args:
            limit: Maximum number of briefings to return.

        Returns:
            List of briefing metadata.
        """
        briefings = []

        for path in sorted(
            self.briefings_dir.glob("briefing_*.md"), reverse=True
        )[:limit]:
            briefings.append({
                "briefing_id": path.stem,
                "path": str(path),
                "created_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })

        return briefings
