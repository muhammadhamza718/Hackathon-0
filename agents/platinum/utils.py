"""Utility helpers for Platinum distributed agents."""

from __future__ import annotations

import os


def resolve_node_id() -> str:
    """Resolve node identity as cloud or local.

    Defaults to local if not explicitly set.
    """
    node_id = os.getenv("PLATINUM_NODE_ID") or os.getenv("NODE_ROLE")
    if not node_id:
        return "local"
    node_id = node_id.strip().lower()
    if node_id not in {"cloud", "local"}:
        return "local"
    return node_id
