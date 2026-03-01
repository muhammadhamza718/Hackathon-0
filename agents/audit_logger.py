"""Audit logging for agent actions — append-only log in /Logs/."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agents.constants import LOGS_DIR
from agents.utils import ensure_dir


def _log_path(vault_root: Path) -> Path:
    """Get today's audit log file path."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logs_dir = ensure_dir(vault_root / LOGS_DIR)
    return logs_dir / f"audit-{today}.md"


def append_log(
    vault_root: Path,
    action: str,
    detail: str,
    tier: str = "bronze",
) -> Path:
    """Append an entry to the audit log.

    Args:
        vault_root: Root directory of the vault.
        action: Action type (e.g. "route", "approve", "reject").
        detail: Human-readable description.
        tier: Agent tier that performed the action.

    Returns:
        Path to the audit log file.
    """
    log_file = _log_path(vault_root)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    entry = f"- [{ts}] [{tier}] **{action}**: {detail}\n"

    with log_file.open("a", encoding="utf-8") as f:
        if log_file.stat().st_size == 0:
            f.write(f"# Audit Log — {ts[:10]}\n\n")
        f.write(entry)

    return log_file


def read_log(vault_root: Path, date: str | None = None) -> str:
    """Read an audit log file.

    Args:
        vault_root: Root directory of the vault.
        date: Date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Log contents or empty string if no log exists.
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = vault_root / LOGS_DIR / f"audit-{date}.md"
    if not log_file.exists():
        return ""
    return log_file.read_text(encoding="utf-8")
