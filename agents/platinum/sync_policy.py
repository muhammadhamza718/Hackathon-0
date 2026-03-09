"""Sync ownership and exclusion policy for Platinum Git sync."""

from __future__ import annotations

from pathlib import Path

from agents.constants import (
    APPROVED_DIR,
    DASHBOARD_FILE,
    DONE_DIR,
    IN_PROGRESS_DIR,
    PLANS_DIR,
    REJECTED_DIR,
    UPDATES_DIR,
)

FORBIDDEN_PREFIXES = (
    ".env",
    ".runtime",
    "runtime",
    "secrets",
    "sessions",
    "cookies",
    "private",
)

FORBIDDEN_EXTENSIONS = (
    ".token",
    ".cookie",
    ".key",
    ".pem",
    ".pfx",
    ".p12",
    ".kdbx",
)


def _as_posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def is_forbidden_path(path: Path) -> bool:
    """Return True when a path is forbidden from sync."""
    posix = _as_posix(path).lstrip("./")
    for prefix in FORBIDDEN_PREFIXES:
        if posix == prefix or posix.startswith(prefix + "/"):
            return True
    for ext in FORBIDDEN_EXTENSIONS:
        if posix.endswith(ext):
            return True
    return False


def is_local_owned(path: Path) -> bool:
    """Paths only Local may author."""
    posix = _as_posix(path)
    if posix.endswith(DASHBOARD_FILE):
        return True
    if posix.startswith(APPROVED_DIR + "/"):
        return True
    if posix.startswith(REJECTED_DIR + "/"):
        return True
    if posix.startswith(DONE_DIR + "/"):
        return True
    return False


def is_cloud_owned(path: Path) -> bool:
    """Paths Cloud may author without Local confirmation."""
    posix = _as_posix(path)
    if posix.startswith(UPDATES_DIR + "/"):
        return True
    if posix.startswith(IN_PROGRESS_DIR + "/cloud/"):
        return True
    return False


def is_shared_state(path: Path) -> bool:
    """Shared state that both nodes may read and propose updates for."""
    posix = _as_posix(path)
    if posix.startswith(PLANS_DIR + "/"):
        return True
    if posix.startswith(IN_PROGRESS_DIR + "/"):
        return True
    return True


def classify_owner(path: Path) -> str:
    """Return owner: local, cloud, or shared."""
    if is_forbidden_path(path):
        return "forbidden"
    if is_local_owned(path):
        return "local"
    if is_cloud_owned(path):
        return "cloud"
    return "shared"
