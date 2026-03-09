"""Configuration for Platinum distributed agents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class PlatinumConfig:
    node_id: str
    vault_root: Path
    repo_root: Path
    heartbeat_interval_seconds: int = 60
    sync_interval_seconds: int = 120
    claim_lease_seconds: int = 600
    sync_remote: str = "origin"
    sync_branch: str = "main"

    @staticmethod
    def from_env() -> "PlatinumConfig":
        node_id = os.getenv("PLATINUM_NODE_ID", "local").strip() or "local"
        vault_root = Path(os.getenv("PLATINUM_VAULT_ROOT", "."))
        repo_root = Path(os.getenv("PLATINUM_REPO_ROOT", "."))
        heartbeat = int(os.getenv("PLATINUM_HEARTBEAT_SECONDS", "60"))
        sync_interval = int(os.getenv("PLATINUM_SYNC_SECONDS", "120"))
        lease = int(os.getenv("PLATINUM_CLAIM_LEASE_SECONDS", "600"))
        remote = os.getenv("PLATINUM_SYNC_REMOTE", "origin")
        branch = os.getenv("PLATINUM_SYNC_BRANCH", "main")
        return PlatinumConfig(
            node_id=node_id,
            vault_root=vault_root,
            repo_root=repo_root,
            heartbeat_interval_seconds=heartbeat,
            sync_interval_seconds=sync_interval,
            claim_lease_seconds=lease,
            sync_remote=remote,
            sync_branch=branch,
        )
