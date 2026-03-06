"""Gold-tier audit logger — JSON format with mandatory rationale field.

Extends the existing Bronze/Silver markdown logger with Gold-specific
JSON log entries per Constitution XVI.  Each day's log lives at
``/Logs/YYYY-MM-DD.json`` as a JSON array of entry objects.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from agents.constants import LOGS_DIR
from agents.gold.models import GoldAuditEntry
from agents.utils import ensure_dir


def _log_path(vault_root: Path, date: str | None = None) -> Path:
    """Return the JSON log path for *date* (default: today UTC)."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logs_dir = ensure_dir(vault_root / LOGS_DIR)
    return logs_dir / f"{date}.json"


def _read_entries(path: Path) -> list[dict]:
    """Read existing entries from a JSON log, returning ``[]`` if absent."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def append_gold_log(
    vault_root: Path,
    *,
    action: str,
    source_file: str = "",
    details: str = "",
    result: str = "success",
    rationale: str,
    iteration: int = 0,
    duration_ms: int = 0,
) -> GoldAuditEntry:
    """Append a Gold-tier audit entry to today's JSON log.

    Args:
        vault_root: Vault root directory.
        action: Action type (must be a valid Gold action).
        source_file: Vault-relative path of the file acted upon.
        details: Human-readable description.
        result: Outcome — ``success``, ``failure``, ``warning``, ``skipped``.
        rationale: **Mandatory** — Plan step reference or explanation.
        iteration: Ralph Wiggum loop cycle count.
        duration_ms: Execution time in milliseconds.

    Returns:
        The created ``GoldAuditEntry``.

    Raises:
        ValueError: If *rationale* is empty.
    """
    if not rationale:
        raise ValueError("Gold audit entries require a non-empty 'rationale'")

    entry = GoldAuditEntry.now(
        action=action,
        source_file=source_file,
        details=details,
        result=result,
        rationale=rationale,
        iteration=iteration,
        duration_ms=duration_ms,
    )

    log_file = _log_path(vault_root)
    entries = _read_entries(log_file)
    entries.append(entry.to_dict())
    log_file.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")

    return entry


def read_gold_log(
    vault_root: Path, date: str | None = None
) -> list[dict]:
    """Read Gold-tier audit entries for a given date.

    Args:
        vault_root: Vault root directory.
        date: Date string ``YYYY-MM-DD``.  Defaults to today UTC.

    Returns:
        List of entry dicts (may be empty).
    """
    return _read_entries(_log_path(vault_root, date))
