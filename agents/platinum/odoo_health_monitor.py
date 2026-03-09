"""Cloud Odoo health monitor for Platinum."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

from agents.gold.odoo_rpc_client import OdooRPCClient


@dataclass(frozen=True)
class OdooHeartbeat:
    status: str
    checked_at: datetime
    detail: str | None = None


class OdooHealthMonitor:
    def __init__(self, client: OdooRPCClient | None = None):
        self.client = client or OdooRPCClient()

    def heartbeat(self) -> OdooHeartbeat:
        url = self.client.config.url
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return OdooHeartbeat(
                status="degraded",
                checked_at=datetime.utcnow(),
                detail="HTTPS required for cloud Odoo",
            )
        try:
            version = self.client.get_version()
            return OdooHeartbeat(
                status="healthy",
                checked_at=datetime.utcnow(),
                detail=f"version={version.get('server_version', 'unknown')}",
            )
        except Exception as exc:  # pragma: no cover - network failures vary
            return OdooHeartbeat(
                status="down",
                checked_at=datetime.utcnow(),
                detail=str(exc),
            )
