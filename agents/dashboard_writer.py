"""Dashboard.md generator from current vault state."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agents.constants import (
    APPROVED_DIR,
    DASHBOARD_FILE,
    DONE_DIR,
    INBOX_DIR,
    NEEDS_ACTION_DIR,
    PENDING_APPROVAL_DIR,
    PLANS_DIR,
    REJECTED_DIR,
)


def count_files(directory: Path) -> int:
    """Count markdown files in a directory.

    Args:
        directory: Path to the directory.

    Returns:
        Number of .md files, 0 if directory doesn't exist.
    """
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.md")))


def generate_dashboard(vault_root: Path) -> str:
    """Generate Dashboard.md content from vault state.

    Args:
        vault_root: Root directory of the Obsidian vault.

    Returns:
        Markdown string for Dashboard.md.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    folders = {
        "Inbox": count_files(vault_root / INBOX_DIR),
        "Needs Action": count_files(vault_root / NEEDS_ACTION_DIR),
        "Pending Approval": count_files(vault_root / PENDING_APPROVAL_DIR),
        "Approved": count_files(vault_root / APPROVED_DIR),
        "Rejected": count_files(vault_root / REJECTED_DIR),
        "Done": count_files(vault_root / DONE_DIR),
        "Plans": count_files(vault_root / PLANS_DIR),
    }

    total = sum(folders.values())

    lines = [
        "# Dashboard",
        "",
        f"*Last updated: {now}*",
        "",
        "## Vault Status",
        "",
        "| Folder | Count |",
        "|--------|-------|",
    ]

    for name, count in folders.items():
        lines.append(f"| {name} | {count} |")

    lines.extend([
        "",
        f"**Total files:** {total}",
        "",
    ])

    return "\n".join(lines)


def write_dashboard(vault_root: Path) -> Path:
    """Write Dashboard.md to the vault root.

    Args:
        vault_root: Root directory of the Obsidian vault.

    Returns:
        Path to the written Dashboard.md file.
    """
    content = generate_dashboard(vault_root)
    path = vault_root / DASHBOARD_FILE
    path.write_text(content, encoding="utf-8")
    return path
