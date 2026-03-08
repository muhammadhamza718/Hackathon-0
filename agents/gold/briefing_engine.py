"""CEO Briefing Engine — weekly audit and intelligence report.

Generates a Monday Morning CEO Briefing every Sunday at 22:00 with
revenue analysis, operational bottlenecks, and subscription optimizations.
Constitution XIII governs this module.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from agents.constants import (
    COMPANY_HANDBOOK_FILE,
    NEEDS_ACTION_DIR,
    BRIEFING_PREFIX,
)
from agents.gold.audit_gold import append_gold_log
from agents.gold.models import (
    BriefingConfig,
    BottleneckTask,
    CEOBriefing,
    SubscriptionFinding,
)
from agents.utils import ensure_dir, safe_read, utcnow_iso


class CEOBriefingEngine:
    """Weekly CEO briefing generator.

    Supports dependency injection for Odoo client and data providers,
    enabling easier testing and custom data sources.
    """

    def __init__(
        self,
        vault_root: Path,
        config: BriefingConfig | None = None,
        odoo_client: object | None = None,
    ) -> None:
        """Initialize CEO Briefing Engine.

        Args:
            vault_root: Root path of the vault.
            config: Optional briefing configuration.
            odoo_client: Optional injected Odoo RPC client for revenue data.
                        If not provided, revenue aggregation will report
                        data as unavailable.
        """
        self.vault_root = vault_root
        self.config = config or BriefingConfig()
        self._odoo = odoo_client

    # ------------------------------------------------------------------
    # Trigger logic
    # ------------------------------------------------------------------

    def should_generate(self, now: datetime | None = None) -> bool:
        """Return True if it's time to generate the briefing.

        Checks: weekday matches, hour >= configured hour, and no
        briefing already exists for the current ISO week.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        if now.weekday() != self.config.briefing_day:
            return False
        if now.hour < self.config.briefing_hour:
            return False

        # Check if briefing for this week already exists
        iso_year, iso_week, _ = now.isocalendar()
        briefing_id = f"{BRIEFING_PREFIX}{iso_year}-W{iso_week:02d}.md"
        needs_action = self.vault_root / NEEDS_ACTION_DIR
        done = self.vault_root / "Done"
        for d in (needs_action, done):
            if d.exists() and (d / briefing_id).exists():
                return False

        return True

    # ------------------------------------------------------------------
    # Revenue aggregation with trend analysis
    # ------------------------------------------------------------------

    def _aggregate_revenue(self) -> tuple[float | None, list[str]]:
        """Fetch MTD revenue from Odoo.

        Returns:
            (revenue_mtd, data_unavailable_list)
        """
        unavailable: list[str] = []

        if self._odoo is None:
            unavailable.append("Revenue — Odoo client not configured")
            return None, unavailable

        try:
            now = datetime.now(timezone.utc)
            first_of_month = now.replace(day=1).strftime("%Y-%m-%d")
            today = now.strftime("%Y-%m-%d")

            invoices = self._odoo.search_read(  # type: ignore[union-attr]
                "account.move",
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("date", ">=", first_of_month),
                    ("date", "<=", today),
                ],
                ["amount_total"],
                limit=500,
            )
            total = sum(inv.get("amount_total", 0.0) for inv in invoices)
            return total, unavailable
        except Exception as exc:
            unavailable.append(f"Revenue — Odoo unreachable: {exc}")
            return None, unavailable

    def _get_revenue_trend(
        self,
        current_revenue: float | None,
        previous_revenue: float | None,
    ) -> dict:
        """Calculate revenue trend between two periods.

        Args:
            current_revenue: Current period revenue.
            previous_revenue: Previous period revenue.

        Returns:
            Dict with trend analysis (delta, percentage, direction).
        """
        if current_revenue is None or previous_revenue is None:
            return {
                "current": current_revenue,
                "previous": previous_revenue,
                "delta": None,
                "delta_pct": None,
                "trend": "unknown",
                "indicator": "⚪",
            }

        delta = current_revenue - previous_revenue
        delta_pct = (delta / previous_revenue * 100) if previous_revenue > 0 else 0

        if delta_pct > 5:
            trend = "up_strong"
            indicator = "🟢"
        elif delta_pct > 0:
            trend = "up"
            indicator = "🟡"
        elif delta_pct > -5:
            trend = "flat"
            indicator = "⚪"
        elif delta_pct > -20:
            trend = "down"
            indicator = "🟠"
        else:
            trend = "down_strong"
            indicator = "🔴"

        return {
            "current": current_revenue,
            "previous": previous_revenue,
            "delta": round(delta, 2),
            "delta_pct": round(delta_pct, 1),
            "trend": trend,
            "indicator": indicator,
        }

    def _fetch_historical_revenue(
        self,
        days_back: int,
        end_date: datetime | None = None,
    ) -> tuple[float | None, str]:
        """Fetch revenue for a historical period.

        Args:
            days_back: Number of days to look back.
            end_date: End date for period (default: now).

        Returns:
            Tuple of (revenue, period_label).
        """
        if self._odoo is None:
            return None, "N/A"

        if end_date is None:
            end_date = datetime.now(timezone.utc)

        start_date = end_date - timedelta(days=days_back)

        try:
            invoices = self._odoo.search_read(  # type: ignore[union-attr]
                "account.move",
                [
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                    ("date", ">=", start_date.strftime("%Y-%m-%d")),
                    ("date", "<=", end_date.strftime("%Y-%m-%d")),
                ],
                ["amount_total"],
                limit=500,
            )
            total = sum(inv.get("amount_total", 0.0) for inv in invoices)
            return total, f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        except Exception:
            return None, "Error fetching data"

    def _analyze_revenue_trends(self) -> dict:
        """Analyze revenue trends with comparisons.

        Returns:
            Dict with WoW, MoM comparisons and trend indicators.
        """
        now = datetime.now(timezone.utc)

        # Current MTD
        current_mtd, _ = self._aggregate_revenue()

        # Previous MTD (same days last month)
        last_month_same_day = now - timedelta(days=28)  # Approximate
        prev_mtd, _ = self._fetch_historical_revenue(28, last_month_same_day)

        # Previous week (7 days before today)
        last_week = now - timedelta(days=7)
        prev_week, _ = self._fetch_historical_revenue(7, last_week)

        # Current week (last 7 days)
        current_week, _ = self._fetch_historical_revenue(7, now)

        # Calculate trends
        mom_trend = self._get_revenue_trend(current_mtd, prev_mtd)
        wow_trend = self._get_revenue_trend(current_week, prev_week)

        return {
            "current_mtd": current_mtd,
            "mom_comparison": mom_trend,
            "current_week": current_week,
            "wow_comparison": wow_trend,
            "summary": self._generate_revenue_summary(mom_trend, wow_trend),
        }

    def _generate_revenue_summary(
        self,
        mom_trend: dict,
        wow_trend: dict,
    ) -> str:
        """Generate human-readable revenue summary.

        Args:
            mom_trend: Month-over-month trend dict.
            wow_trend: Week-over-week trend dict.

        Returns:
            Human-readable summary string.
        """
        parts = []

        # MoM summary
        if mom_trend["trend"] == "unknown":
            parts.append("MoM: data unavailable")
        else:
            indicator = mom_trend["indicator"]
            pct = mom_trend["delta_pct"]
            if pct is not None:
                parts.append(f"MoM: {indicator} {pct:+.1f}%")

        # WoW summary
        if wow_trend["trend"] == "unknown":
            parts.append("WoW: data unavailable")
        else:
            indicator = wow_trend["indicator"]
            pct = wow_trend["delta_pct"]
            if pct is not None:
                parts.append(f"WoW: {indicator} {pct:+.1f}%")

        return " | ".join(parts) if parts else "Revenue trends unavailable"

    # ------------------------------------------------------------------
    # Bottleneck detection with escalation
    # ------------------------------------------------------------------

    def _detect_bottlenecks(self) -> list[BottleneckTask]:
        """Scan /Needs_Action/ for tasks older than threshold hours."""
        threshold = self.config.bottleneck_threshold_hours
        needs_action = self.vault_root / NEEDS_ACTION_DIR
        if not needs_action.exists():
            return []

        bottlenecks: list[BottleneckTask] = []
        now = time.time()

        for item in sorted(needs_action.iterdir()):
            if not item.is_file():
                continue
            age_seconds = now - item.stat().st_mtime
            age_hours = age_seconds / 3600.0
            if age_hours < threshold:
                continue

            # Extract summary (first non-empty, non-frontmatter line)
            content = safe_read(item) or ""
            summary = ""
            in_frontmatter = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter:
                    continue
                if stripped and not stripped.startswith("#"):
                    summary = stripped[:100]
                    break
                if stripped.startswith("#"):
                    summary = stripped.lstrip("# ")[:100]
                    break

            # Extract priority
            priority = "MEDIUM"
            if "priority:" in content.lower():
                for line in content.splitlines():
                    if line.lower().strip().startswith("priority:"):
                        priority = line.split(":", 1)[1].strip().upper()
                        break

            # Apply age-based escalation
            escalated_priority = self._escalate_priority(priority, age_hours)

            bottlenecks.append(
                BottleneckTask(
                    filename=item.name,
                    age_hours=round(age_hours, 1),
                    priority=escalated_priority,
                    summary=summary or item.stem,
                )
            )

        # Sort by priority then age
        priority_order = {"P0": 0, "CRITICAL": 0, "HIGH": 1, "P1": 1, "MEDIUM": 2, "P2": 2, "LOW": 3, "P3": 3}
        bottlenecks.sort(
            key=lambda b: (priority_order.get(b.priority, 9), -b.age_hours)
        )
        return bottlenecks

    def _escalate_priority(self, original_priority: str, age_hours: float) -> str:
        """Escalate priority based on task age.

        Args:
            original_priority: Original task priority.
            age_hours: Task age in hours.

        Returns:
            Escalated priority string.
        """
        # Escalation rules:
        # - 48h+ old: escalate one level
        # - 72h+ old: escalate two levels
        # - 96h+ old: mark as CRITICAL

        priority_order = ["P3", "LOW", "P2", "MEDIUM", "P1", "HIGH", "P0", "CRITICAL"]

        try:
            current_idx = priority_order.index(original_priority.upper())
        except ValueError:
            current_idx = 3  # Default to MEDIUM

        # Apply escalation
        if age_hours >= 96:
            return "CRITICAL"
        elif age_hours >= 72:
            new_idx = max(0, current_idx - 2)
            return priority_order[new_idx]
        elif age_hours >= 48:
            new_idx = max(0, current_idx - 1)
            return priority_order[new_idx]

        return original_priority

    def _get_escalation_notifications(
        self,
        bottlenecks: list[BottleneckTask],
    ) -> list[dict]:
        """Generate escalation notifications for critical bottlenecks.

        Args:
            bottlenecks: List of bottleneck tasks.

        Returns:
            List of notification dicts with escalation details.
        """
        notifications: list[dict] = []

        for task in bottlenecks:
            if task.priority in ("CRITICAL", "P0"):
                notifications.append({
                    "type": "critical_escalation",
                    "task": task.filename,
                    "priority": task.priority,
                    "age_hours": task.age_hours,
                    "message": f"CRITICAL: {task.filename} is {task.age_hours:.1f}h old",
                    "action_required": "Immediate attention required",
                })
            elif task.age_hours >= 72:
                notifications.append({
                    "type": "age_escalation",
                    "task": task.filename,
                    "priority": task.priority,
                    "age_hours": task.age_hours,
                    "message": f"Task {task.filename} escalated due to age ({task.age_hours:.1f}h)",
                    "action_required": "Review and prioritize",
                })

        return notifications

    # ------------------------------------------------------------------
    # Subscription audit with usage tracking
    # ------------------------------------------------------------------

    def _audit_subscriptions(self) -> list[SubscriptionFinding]:
        """Parse Company_Handbook.md for subscription data."""
        handbook_path = self.vault_root / COMPANY_HANDBOOK_FILE
        content = safe_read(handbook_path)
        if not content:
            return []

        # Look for a subscriptions section
        findings: list[SubscriptionFinding] = []
        in_subs = False
        for line in content.splitlines():
            lower = line.lower().strip()
            if "subscription" in lower and lower.startswith("#"):
                in_subs = True
                continue
            if in_subs and lower.startswith("#"):
                break  # exited subscription section
            if in_subs and "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3 and parts[0] != "---":
                    try:
                        name = parts[0]
                        cost = float(parts[1].replace("$", "").replace(",", ""))
                        util_str = parts[2].replace("%", "").strip() if len(parts) > 2 else ""
                        util = float(util_str) if util_str else None

                        finding_type = "ok"
                        recommendation = ""
                        savings = 0.0

                        if util is not None and util < self.config.utilization_threshold_pct:
                            finding_type = "underused"
                            recommendation = f"Consider downgrading or cancelling (utilization: {util}%)"
                            savings = cost

                        if finding_type != "ok":
                            findings.append(
                                SubscriptionFinding(
                                    service_name=name,
                                    monthly_cost=cost,
                                    utilization_pct=util,
                                    finding_type=finding_type,
                                    recommendation=recommendation,
                                    potential_savings=savings,
                                )
                            )
                    except (ValueError, IndexError):
                        continue

        return findings

    def _track_subscription_usage(self) -> list[SubscriptionFinding]:
        """Track subscription usage via browser automation.

        Checks login dates and usage patterns for each subscription.
        Returns findings for unused or underutilized subscriptions.

        Note: In production, this would use Browser MCP to check
        actual service login dates and usage metrics.
        """
        findings: list[SubscriptionFinding] = []

        # Simulated subscription usage data — Browser MCP integration point
        simulated_usage = {
            "Slack": {"last_login_days_ago": 2, "monthly_cost": 8.75, "utilization": 85},
            "Zoom": {"last_login_days_ago": 1, "monthly_cost": 15.99, "utilization": 90},
            "Adobe Creative Cloud": {"last_login_days_ago": 45, "monthly_cost": 54.99, "utilization": 10},
            "Figma": {"last_login_days_ago": 3, "monthly_cost": 15.00, "utilization": 75},
            "Notion": {"last_login_days_ago": 0, "monthly_cost": 10.00, "utilization": 95},
            "Salesforce": {"last_login_days_ago": 60, "monthly_cost": 75.00, "utilization": 5},
        }

        for service, data in simulated_usage.items():
            finding_type = "ok"
            recommendation = ""

            # Flag unused (no login in 30+ days)
            if data["last_login_days_ago"] > 30:
                finding_type = "unused"
                recommendation = f"No login in {data['last_login_days_ago']} days — consider cancelling"
            # Flag underused (< 30% utilization)
            elif data["utilization"] < 30:
                finding_type = "underused"
                recommendation = f"Low utilization ({data['utilization']}%) — consider downgrading"

            if finding_type != "ok":
                findings.append(
                    SubscriptionFinding(
                        service_name=service,
                        monthly_cost=data["monthly_cost"],
                        utilization_pct=data["utilization"],
                        finding_type=finding_type,
                        recommendation=recommendation,
                        potential_savings=data["monthly_cost"] if finding_type == "unused" else data["monthly_cost"] * 0.5,
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Generate briefing
    # ------------------------------------------------------------------

    def generate_briefing(self) -> CEOBriefing:
        """Aggregate all data sources and produce a CEO briefing."""
        now = datetime.now(timezone.utc)
        iso_year, iso_week, _ = now.isocalendar()

        # Period: Monday to Sunday of current week
        monday = now - timedelta(days=now.weekday())
        sunday = monday + timedelta(days=6)

        revenue_mtd, unavailable = self._aggregate_revenue()
        revenue_trends = self._analyze_revenue_trends()
        bottlenecks = self._detect_bottlenecks()
        subscriptions = self._audit_subscriptions()

        revenue_goal = self.config.revenue_goal
        delta_pct = None
        if revenue_mtd is not None and revenue_goal > 0:
            delta_pct = round(((revenue_mtd - revenue_goal) / revenue_goal) * 100, 1)

        # Add trend summary to unavailable if data missing
        if revenue_trends["summary"].startswith("MoM: data unavailable"):
            unavailable.append("Revenue trends — insufficient historical data")

        briefing = CEOBriefing(
            briefing_id=f"BRIEFING-{iso_year}-W{iso_week:02d}",
            generated_at=utcnow_iso(),
            period_start=monday.strftime("%Y-%m-%d"),
            period_end=sunday.strftime("%Y-%m-%d"),
            revenue_mtd=revenue_mtd,
            revenue_goal=revenue_goal,
            revenue_delta_pct=delta_pct,
            bottleneck_tasks=tuple(bottlenecks),
            subscription_findings=tuple(subscriptions),
            data_unavailable=tuple(unavailable),
        )

        append_gold_log(
            self.vault_root,
            action="ceo_briefing",
            details=f"Generated briefing {briefing.briefing_id} with trend analysis",
            rationale="Scheduled weekly CEO briefing (Constitution XIII)",
        )

        return briefing

    def generate_briefing_with_trends(self) -> str:
        """Generate full briefing markdown with revenue trend analysis.

        Returns:
            Markdown-formatted briefing with trend indicators.
        """
        briefing = self.generate_briefing()
        trends = self._analyze_revenue_trends()

        lines = [
            f"# {briefing.briefing_id} — CEO Weekly Briefing",
            "",
            f"**Generated**: {briefing.generated_at}",
            f"**Period**: {briefing.period_start} to {briefing.period_end}",
            "",
            "## Executive Summary",
            "",
            "### Revenue",
            "",
        ]

        # Revenue section with trends
        if briefing.revenue_mtd is not None:
            lines.append(f"- **MTD Revenue**: ${briefing.revenue_mtd:,.2f}")
            if briefing.revenue_delta_pct is not None:
                sign = "+" if briefing.revenue_delta_pct >= 0 else ""
                lines.append(f"- **vs Goal**: {sign}{briefing.revenue_delta_pct}% (${briefing.revenue_goal:,.2f})")
        else:
            lines.append("- **Revenue**: Data unavailable")

        lines.append("")
        lines.append("### Revenue Trends")
        lines.append("")
        lines.append(f"- **Month-over-Month**: {trends['mom_comparison']['indicator']} {trends['mom_comparison'].get('delta_pct', 'N/A')!s}%")
        lines.append(f"- **Week-over-Week**: {trends['wow_comparison']['indicator']} {trends['wow_comparison'].get('delta_pct', 'N/A')!s}%")
        lines.append(f"- **Summary**: {trends['summary']}")
        lines.append("")

        # Bottlenecks
        lines.append("### Task Bottlenecks")
        lines.append("")
        if briefing.bottleneck_tasks:
            for task in briefing.bottleneck_tasks[:5]:
                lines.append(f"- **[{task.priority}]** {task.filename} ({task.age_hours:.1f}h old): {task.summary}")
        else:
            lines.append("No bottlenecks detected.")
        lines.append("")

        # Subscription findings
        lines.append("### Subscription Optimizations")
        lines.append("")
        if briefing.subscription_findings:
            total_savings = sum(f.potential_savings for f in briefing.subscription_findings)
            lines.append(f"**Potential Monthly Savings**: ${total_savings:,.2f}")
            lines.append("")
            for finding in briefing.subscription_findings:
                lines.append(f"- **{finding.service_name}** (${finding.monthly_cost}/mo): {finding.recommendation}")
        else:
            lines.append("No optimization opportunities found.")
        lines.append("")

        # Data availability
        if briefing.data_unavailable:
            lines.append("### Data Unavailable")
            lines.append("")
            for item in briefing.data_unavailable:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Write to vault
    # ------------------------------------------------------------------

    def write_briefing(self, briefing: CEOBriefing) -> Path:
        """Render briefing as Markdown and write to /Needs_Action/.

        Returns:
            Path to the generated file.
        """
        lines = [
            "# Monday Morning CEO Briefing",
            f"**Period**: {briefing.period_start} to {briefing.period_end}",
            f"**Generated**: {briefing.generated_at}",
            "",
        ]

        # Revenue section
        lines.append("## Revenue (MTD vs Goal)\n")
        if briefing.revenue_mtd is not None:
            delta = (briefing.revenue_mtd - briefing.revenue_goal)
            status = "On Track" if delta >= 0 else "At Risk"
            emoji = "✅" if delta >= 0 else "⚠️"
            lines += [
                "| Metric | Value |",
                "|--------|-------|",
                f"| MTD Revenue | ${briefing.revenue_mtd:,.2f} |",
                f"| Monthly Goal | ${briefing.revenue_goal:,.2f} |",
                f"| Delta | ${delta:+,.2f} ({briefing.revenue_delta_pct:+.1f}%) |",
                f"| Status | {emoji} {status} |",
                "",
            ]
        else:
            lines.append("[DATA UNAVAILABLE — Odoo unreachable]\n")

        # Bottleneck section
        lines.append("## Task Bottlenecks\n")
        if briefing.bottleneck_tasks:
            lines += [
                "| Task | Age | Priority | Summary |",
                "|------|-----|----------|---------|",
            ]
            for bt in briefing.bottleneck_tasks:
                lines.append(
                    f"| {bt.filename} | {bt.age_hours:.0f}h | {bt.priority} | {bt.summary} |"
                )
            lines.append("")
        else:
            lines.append("No stale tasks found.\n")

        # Subscription section
        lines.append("## Subscription Optimizations\n")
        if briefing.subscription_findings:
            lines += [
                "| Service | Monthly Cost | Utilization | Finding | Potential Savings |",
                "|---------|-------------|-------------|---------|-------------------|",
            ]
            total_savings = 0.0
            for sf in briefing.subscription_findings:
                util = f"{sf.utilization_pct:.0f}%" if sf.utilization_pct is not None else "N/A"
                lines.append(
                    f"| {sf.service_name} | ${sf.monthly_cost:.2f} | {util} | "
                    f"{sf.finding_type} | ${sf.potential_savings:.2f}/mo |"
                )
                total_savings += sf.potential_savings
            lines.append(f"\n**Total Potential Savings**: ${total_savings:.2f}/month\n")
        else:
            lines.append("No optimization opportunities found.\n")

        # Data unavailable
        if briefing.data_unavailable:
            lines.append("## Data Availability Warnings\n")
            for note in briefing.data_unavailable:
                lines.append(f"- {note}")
            lines.append("")

        lines.append("---")
        lines.append("*Generated by Gold Tier CEO Briefing Engine*\n")

        # Write file
        needs_action = ensure_dir(self.vault_root / NEEDS_ACTION_DIR)
        iso_year, iso_week, _ = datetime.now(timezone.utc).isocalendar()
        filename = f"{BRIEFING_PREFIX}{iso_year}-W{iso_week:02d}.md"
        output_path = needs_action / filename
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path
