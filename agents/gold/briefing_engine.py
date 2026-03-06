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
    """Weekly CEO briefing generator."""

    def __init__(
        self,
        vault_root: Path,
        config: BriefingConfig | None = None,
        odoo_client: object | None = None,
    ) -> None:
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
    # Revenue aggregation
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

    # ------------------------------------------------------------------
    # Bottleneck detection
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

            bottlenecks.append(
                BottleneckTask(
                    filename=item.name,
                    age_hours=round(age_hours, 1),
                    priority=priority,
                    summary=summary or item.stem,
                )
            )

        # Sort by priority then age
        priority_order = {"P0": 0, "CRITICAL": 0, "HIGH": 1, "P1": 1, "MEDIUM": 2, "P2": 2, "LOW": 3, "P3": 3}
        bottlenecks.sort(
            key=lambda b: (priority_order.get(b.priority, 9), -b.age_hours)
        )
        return bottlenecks

    # ------------------------------------------------------------------
    # Subscription audit
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
        bottlenecks = self._detect_bottlenecks()
        subscriptions = self._audit_subscriptions()

        revenue_goal = self.config.revenue_goal
        delta_pct = None
        if revenue_mtd is not None and revenue_goal > 0:
            delta_pct = round(((revenue_mtd - revenue_goal) / revenue_goal) * 100, 1)

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
            details=f"Generated briefing {briefing.briefing_id}",
            rationale="Scheduled weekly CEO briefing (Constitution XIII)",
        )

        return briefing

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
