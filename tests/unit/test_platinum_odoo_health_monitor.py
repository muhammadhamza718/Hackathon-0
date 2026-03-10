from __future__ import annotations

from types import SimpleNamespace

from agents.platinum.odoo_health_monitor import OdooHealthMonitor


class StubClient:
    def __init__(self, url: str, version: dict | None = None, exc: Exception | None = None):
        self.config = SimpleNamespace(url=url)
        self._version = version or {"server_version": "19.0"}
        self._exc = exc

    def get_version(self) -> dict:
        if self._exc:
            raise self._exc
        return self._version


def test_heartbeat_requires_https():
    monitor = OdooHealthMonitor(client=StubClient("http://odoo.local"))
    heartbeat = monitor.heartbeat()
    assert heartbeat.status == "degraded"
    assert "HTTPS" in (heartbeat.detail or "")


def test_heartbeat_reports_version_when_https():
    monitor = OdooHealthMonitor(client=StubClient("https://odoo.local"))
    heartbeat = monitor.heartbeat()
    assert heartbeat.status == "healthy"
    assert "version=19.0" in (heartbeat.detail or "")
