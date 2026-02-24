"""
DashboardReconciler: Live dashboard reconciliation for Silver Tier.

Scans the vault state (Plans, Pending_Approval) and rebuilds Dashboard.md
atomically with real-time data:

  ⚡ Current Missions  — Active plan objective, current step, HITL blocks
  📊 Plan Statistics   — Active / Blocked / Done counts + completion %
  🚨 Alerts           — Plans blocked > 24 hours
  🕐 Recent Activity  — Last 10 timestamped events from Reasoning Logs

All writes are atomic (temp-file-and-rename) to prevent partial dashboard state.

Classes:
    MissionStatus: Computed status for a single plan (for display)
    DashboardReconciler: Core reconciler

Usage:
    reconciler = DashboardReconciler(vault_root=Path("/vault"))
    reconciler.reconcile()
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from agents.skills.managing_obsidian_vault.plan_manager import PlanContent, PlanManager

logger = logging.getLogger(__name__)

# Plans blocked longer than this trigger a 🚨 alert
BLOCK_ALERT_THRESHOLD_HOURS = 24


@dataclass
class MissionStatus:
    """Computed display data for one plan in the Current Missions section."""

    plan_id: str
    objective: str
    status: str                      # Active | Blocked | Draft
    priority: str
    created_date: str
    total_steps: int
    completed_steps: int
    current_step_desc: str           # Description of next incomplete step
    pending_approval_count: int = 0  # # of files in /Pending_Approval/ for this plan
    blocked_reason: Optional[str] = None

    @property
    def progress_pct(self) -> int:
        if self.total_steps == 0:
            return 0
        return int(self.completed_steps / self.total_steps * 100)

    @property
    def progress_bar(self) -> str:
        filled = self.progress_pct // 10
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}] {self.progress_pct}%"

    @property
    def status_badge(self) -> str:
        badges = {
            "Active": "🟢 Active",
            "Blocked": "🔴 Blocked: Awaiting Human Approval",
            "Draft":  "⚪ Draft",
        }
        return badges.get(self.status, f"❓ {self.status}")


class DashboardReconciler:
    """
    Reconciles Dashboard.md with live vault state.

    Reads from:
      <vault_root>/Plans/       — active plans
      <vault_root>/Pending_Approval/ — pending HITL requests

    Writes to:
      <vault_root>/Dashboard.md — atomically
    """

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self.plans_dir = vault_root / "Plans"
        self.done_plans_dir = vault_root / "Done" / "Plans"
        self.pending_dir = vault_root / "Pending_Approval"
        self.dashboard_path = vault_root / "Dashboard.md"
        self._plan_manager = PlanManager(vault_root=vault_root)
        logger.info("DashboardReconciler initialised with vault_root=%s", vault_root)

    # ------------------------------------------------------------------
    # T047 — ReconcileDashboard
    # ------------------------------------------------------------------

    def reconcile(self) -> Path:
        """
        Rebuild Dashboard.md from current vault state.

        Process (7 steps per spec):
          1. Scan /Plans/ for all incomplete plans
          2. Scan /Pending_Approval/ for approval files (count by plan_id)
          3. Identify active plan (Active > Blocked > Draft, most recent first)
          4. Rebuild ⚡ Current Missions section
          5. Update 📊 Plan Statistics
          6. Update 🚨 Alerts (blocks > 24 h)
          7. Update 🕐 Recent Activity (last 10 log entries across all plans)
          8. Write Dashboard.md atomically

        Returns:
            Path to updated Dashboard.md
        """
        missions = self._collect_missions()
        pending_counts = self._count_pending_by_plan()

        # Annotate missions with pending approval counts.
        # Approval files store plan_id as "PLAN-<id>"; mission plan_id may be "<id>" or "PLAN-<id>".
        for m in missions:
            raw_id = m.plan_id  # e.g. "2026-003"
            prefixed_id = f"PLAN-{raw_id}" if not raw_id.startswith("PLAN-") else raw_id
            m.pending_approval_count = (
                pending_counts.get(raw_id, 0) + pending_counts.get(prefixed_id, 0)
            )

        done_count = self._count_done_plans()
        recent_activity = self._collect_recent_activity(missions, limit=10)

        content = self._render_dashboard(missions, done_count, recent_activity)
        self._atomic_write(self.dashboard_path, content)

        logger.info(
            "Dashboard reconciled: %d active/blocked missions, %d done plans",
            len(missions), done_count,
        )
        return self.dashboard_path

    # ------------------------------------------------------------------
    # Private: data collection
    # ------------------------------------------------------------------

    def _collect_missions(self) -> list[MissionStatus]:
        """Scan /Plans/ and build MissionStatus list, sorted by priority."""
        if not self.plans_dir.exists():
            return []

        missions: list[MissionStatus] = []
        for plan_file in self.plans_dir.glob("PLAN-*.md"):
            try:
                plan = self._plan_manager.load_plan(plan_file.stem)
                if plan.metadata.status == "Done":
                    continue
                missions.append(self._plan_to_mission(plan))
            except (ValueError, FileNotFoundError) as exc:
                logger.warning("Skipping plan %s: %s", plan_file.name, exc)

        # Sort: Active > Blocked > Draft, then most recent first
        status_order = {"Active": 0, "Blocked": 1, "Draft": 2}
        missions.sort(
            key=lambda m: (
                status_order.get(m.status, 9),
                -self._parse_ts(m.created_date),
            )
        )
        return missions

    def _plan_to_mission(self, plan: PlanContent) -> MissionStatus:
        completed = sum(1 for s in plan.steps if s.completed)
        next_step = plan.get_next_incomplete_step()
        current_desc = next_step.description if next_step else "All steps complete"

        return MissionStatus(
            plan_id=plan.metadata.task_id,
            objective=plan.objective,
            status=plan.metadata.status,
            priority=plan.metadata.priority,
            created_date=plan.metadata.created_date,
            total_steps=len(plan.steps),
            completed_steps=completed,
            current_step_desc=current_desc,
            blocked_reason=plan.metadata.blocked_reason,
        )

    def _count_pending_by_plan(self) -> dict[str, int]:
        """Count pending approval files grouped by plan_id."""
        counts: dict[str, int] = {}
        if not self.pending_dir.exists():
            return counts
        for f in self.pending_dir.glob("*.md"):
            try:
                raw = f.read_text(encoding="utf-8")
                match = re.search(r"^plan_id:\s*(.+)$", raw, re.MULTILINE)
                if match:
                    pid = match.group(1).strip().strip("'\"")
                    counts[pid] = counts.get(pid, 0) + 1
            except OSError:
                pass
        return counts

    def _count_done_plans(self) -> int:
        if not self.done_plans_dir.exists():
            return 0
        return sum(1 for _ in self.done_plans_dir.glob("PLAN-*.md"))

    def _collect_recent_activity(
        self, missions: list[MissionStatus], limit: int = 10
    ) -> list[str]:
        """
        Gather the most recent reasoning log entries across all active plans.
        Returns up to `limit` entries, newest first.
        """
        entries: list[tuple[str, str]] = []  # (iso_timestamp, log_line)

        for mission in missions:
            try:
                plan = self._plan_manager.load_plan(mission.plan_id)
                for log_line in plan.reasoning_logs:
                    ts_match = re.match(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\]", log_line)
                    if ts_match:
                        entries.append((ts_match.group(1), log_line.strip()))
            except (ValueError, FileNotFoundError):
                pass

        # Sort newest first, take limit
        entries.sort(key=lambda x: x[0], reverse=True)
        return [line for _, line in entries[:limit]]

    # ------------------------------------------------------------------
    # Private: rendering
    # ------------------------------------------------------------------

    def _render_dashboard(
        self,
        missions: list[MissionStatus],
        done_count: int,
        recent_activity: list[str],
    ) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        active_count = sum(1 for m in missions if m.status == "Active")
        blocked_count = sum(1 for m in missions if m.status == "Blocked")
        draft_count = sum(1 for m in missions if m.status == "Draft")
        total_non_done = len(missions)

        total_steps = sum(m.total_steps for m in missions)
        done_steps = sum(m.completed_steps for m in missions)
        completion_pct = int(done_steps / total_steps * 100) if total_steps > 0 else 0

        # Stale blocks (>24 h)
        alerts = self._build_alerts(missions)

        sections: list[str] = []

        # Header
        sections.append(
            f"# 🧠 Silver Tier Agent Dashboard\n\n"
            f"**Last Updated**: `{now}`  \n"
            f"**Vault**: Silver Tier Reasoning System  \n"
            f"**Agent**: obsidian-vault-agent\n"
        )

        # ⚡ Current Missions
        sections.append(self._render_missions_section(missions))

        # 📊 Plan Statistics
        sections.append(
            f"## 📊 Plan Statistics\n\n"
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| 🟢 Active Plans | {active_count} |\n"
            f"| 🔴 Blocked Plans | {blocked_count} |\n"
            f"| ⚪ Draft Plans | {draft_count} |\n"
            f"| ✅ Completed Plans | {done_count} |\n"
            f"| 📈 Step Completion | {done_steps}/{total_steps} ({completion_pct}%) |\n"
        )

        # 🚨 Alerts
        if alerts:
            alert_lines = "\n".join(f"- {a}" for a in alerts)
            sections.append(f"## 🚨 Alerts\n\n{alert_lines}\n")
        else:
            sections.append("## 🚨 Alerts\n\n_No active alerts._\n")

        # 🕐 Recent Activity
        if recent_activity:
            activity_lines = "\n".join(f"- {entry}" for entry in recent_activity)
            sections.append(f"## 🕐 Recent Activity\n\n{activity_lines}\n")
        else:
            sections.append("## 🕐 Recent Activity\n\n_No activity recorded yet._\n")

        return "\n---\n\n".join(sections)

    def _render_missions_section(self, missions: list[MissionStatus]) -> str:
        if not missions:
            return "## ⚡ Current Missions\n\n_No active missions. Vault is idle._\n"

        lines = ["## ⚡ Current Missions\n"]
        for m in missions:
            lines.append(f"### {m.plan_id} — {m.objective}\n")
            lines.append(f"| Field | Value |")
            lines.append(f"|-------|-------|")
            lines.append(f"| **Status** | {m.status_badge} |")
            lines.append(f"| **Priority** | {m.priority.title()} |")
            lines.append(f"| **Progress** | {m.progress_bar} |")
            lines.append(f"| **Current Step** | {m.current_step_desc} |")
            if m.pending_approval_count:
                lines.append(
                    f"| **Pending Approvals** | ⏸ {m.pending_approval_count} action(s) awaiting review in `/Pending_Approval/` |"
                )
            if m.blocked_reason:
                lines.append(f"| **Block Reason** | {m.blocked_reason} |")
            lines.append("")  # blank line between missions

        return "\n".join(lines)

    def _build_alerts(self, missions: list[MissionStatus]) -> list[str]:
        alerts: list[str] = []
        threshold = timedelta(hours=BLOCK_ALERT_THRESHOLD_HOURS)
        now = datetime.now(timezone.utc)

        for m in missions:
            if m.status != "Blocked":
                continue
            try:
                created = datetime.fromisoformat(m.created_date.replace("Z", "+00:00"))
                age = now - created
                if age > threshold:
                    hours = int(age.total_seconds() / 3600)
                    alerts.append(
                        f"🔴 **{m.plan_id}** blocked for {hours}h — "
                        f"'{m.objective[:60]}...' requires human action."
                    )
            except (ValueError, TypeError):
                pass

        return alerts

    # ------------------------------------------------------------------
    # Private: atomic write + timestamp helpers
    # ------------------------------------------------------------------

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically using temp-file-and-rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.parent / f".{path.name}.tmp"
        try:
            temp_path.write_text(content, encoding="utf-8")
            temp_path.replace(path)
            logger.debug("Atomic dashboard write complete: %s", path)
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            raise IOError(f"Atomic write failed for {path}: {exc}") from exc

    @staticmethod
    def _parse_ts(ts_str: str) -> float:
        """Parse ISO-8601 timestamp to float seconds (for sorting). Returns 0 on error."""
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            return 0.0
