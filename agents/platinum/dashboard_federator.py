"""Federate distributed status into a local dashboard summary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.constants import IN_PROGRESS_DIR, UPDATES_HEARTBEATS_DIR, UPDATES_SYNC_DIR
from agents.platinum.models import ClaimState, NodeStatus, TaskClaim


@dataclass(frozen=True)
class FederatedStatus:
    heartbeats: dict[str, dict[str, Any]]
    sync_states: dict[str, dict[str, Any]]
    active_claims: list[TaskClaim]
    alerts: list[str]
    node_health: dict[str, dict[str, Any]]


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", ""))


def _load_heartbeats(vault_root: Path) -> dict[str, dict[str, Any]]:
    heartbeats: dict[str, dict[str, Any]] = {}
    updates = vault_root / UPDATES_HEARTBEATS_DIR
    if not updates.exists():
        return heartbeats
    for path in updates.glob("*.json"):
        data = _load_json(path)
        if data:
            heartbeats[path.stem] = data
    return heartbeats


def _load_sync_states(vault_root: Path) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    updates = vault_root / UPDATES_SYNC_DIR
    if not updates.exists():
        return states
    for path in updates.glob("*.json"):
        data = _load_json(path)
        if data:
            states[path.stem] = data
    return states


def _parse_claim(data: dict[str, Any]) -> TaskClaim:
    return TaskClaim(
        task_id=data["task_id"],
        owner_node=data["owner_node"],
        claim_nonce=data["claim_nonce"],
        claimed_at=_parse_timestamp(data["claimed_at"]) or datetime.utcnow(),
        lease_expires_at=_parse_timestamp(data["lease_expires_at"]) or datetime.utcnow(),
        state=ClaimState(data["state"]),
        source_path=data["source_path"],
        current_path=data["current_path"],
        last_heartbeat_at=_parse_timestamp(data.get("last_heartbeat_at")),
    )


def _load_active_claims(vault_root: Path) -> list[TaskClaim]:
    claims: list[TaskClaim] = []
    in_progress = vault_root / IN_PROGRESS_DIR
    if not in_progress.exists():
        return claims
    for sidecar in in_progress.glob("**/*.claim.json"):
        data = _load_json(sidecar)
        if not data:
            continue
        claims.append(_parse_claim(data))
    return claims


def _compute_node_health(
    heartbeats: dict[str, dict[str, Any]], warn_seconds: int, stale_seconds: int
) -> dict[str, dict[str, Any]]:
    now = datetime.utcnow()
    health: dict[str, dict[str, Any]] = {}
    for node_id, data in heartbeats.items():
        last_seen = _parse_timestamp(data.get("last_seen_at"))
        if not last_seen:
            health[node_id] = {"status": NodeStatus.OFFLINE.value, "age": None}
            continue
        age = (now - last_seen).total_seconds()
        if age > stale_seconds:
            status = NodeStatus.OFFLINE.value
        elif age > warn_seconds:
            status = NodeStatus.DEGRADED.value
        else:
            status = NodeStatus.HEALTHY.value
        health[node_id] = {"status": status, "age": age}
    return health


def federate_status(
    vault_root: Path,
    warn_seconds: int = 300,
    stale_seconds: int = 900,
    sync_warn_seconds: int = 300,
) -> FederatedStatus:
    heartbeats = _load_heartbeats(vault_root)
    sync_states = _load_sync_states(vault_root)
    claims = _load_active_claims(vault_root)
    alerts: list[str] = []

    node_health = _compute_node_health(heartbeats, warn_seconds, stale_seconds)
    for node_id, info in node_health.items():
        if info["status"] != NodeStatus.HEALTHY.value:
            alerts.append(f"{node_id} heartbeat {info['status']}")

    for node_id, state in sync_states.items():
        latency = state.get("latency_seconds")
        if latency is None:
            finished = _parse_timestamp(state.get("sync_finished_at"))
            if finished:
                latency = (datetime.utcnow() - finished).total_seconds()
        if latency is not None and latency > sync_warn_seconds:
            alerts.append(f"{node_id} sync lag {int(latency)}s")

    return FederatedStatus(
        heartbeats=heartbeats,
        sync_states=sync_states,
        active_claims=claims,
        alerts=alerts,
        node_health=node_health,
    )
