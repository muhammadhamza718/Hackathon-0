"""Odoo Connection Pool - Session management and connection pooling.

Provides efficient session reuse, health checks, and auto-reconnect
functionality for Odoo RPC connections.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Queue, Empty
from threading import Lock
from typing import TYPE_CHECKING

from agents.gold.models import OdooConfig, OdooSession
from agents.utils import utcnow_iso

if TYPE_CHECKING:
    from agents.gold.odoo_rpc_client import OdooRPCClient

logger = logging.getLogger(__name__)


@dataclass
class PooledSession:
    """A session wrapper with pool metadata."""

    session: OdooSession
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    is_healthy: bool = True

    def mark_used(self) -> None:
        """Mark this session as recently used."""
        self.last_used = time.time()
        self.use_count += 1

    @property
    def age_seconds(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """Get time since last use in seconds."""
        return time.time() - self.last_used


class OdooConnectionPool:
    """Connection pool for Odoo RPC sessions.

    Manages a pool of reusable Odoo sessions with:
    - Session reuse to avoid repeated authentication
    - Health checks to detect stale connections
    - Auto-reconnect on failure
    - Configurable pool size and timeouts
    """

    def __init__(
        self,
        config: OdooConfig,
        vault_root,
        max_size: int = 5,
        min_size: int = 1,
        max_idle_seconds: float = 300.0,
        max_age_seconds: float = 3600.0,
        health_check_interval: float = 60.0,
    ) -> None:
        """Initialize Odoo connection pool.

        Args:
            config: Odoo configuration.
            vault_root: Vault root path for audit logging.
            max_size: Maximum number of sessions in the pool.
            min_size: Minimum number of sessions to maintain.
            max_idle_seconds: Maximum idle time before session is closed.
            max_age_seconds: Maximum session lifetime.
            health_check_interval: Seconds between health checks.
        """
        self.config = config
        self.vault_root = vault_root
        self.max_size = max_size
        self.min_size = min_size
        self.max_idle_seconds = max_idle_seconds
        self.max_age_seconds = max_age_seconds
        self.health_check_interval = health_check_interval

        self._pool: Queue[PooledSession] = Queue(maxsize=max_size)
        self._lock = Lock()
        self._total_created = 0
        self._total_acquired = 0
        self._total_released = 0
        self._total_reconnected = 0

    def _create_session(self, client: OdooRPCClient) -> PooledSession:
        """Create a new authenticated session.

        Args:
            client: Odoo RPC client for authentication.

        Returns:
            New pooled session wrapper.
        """
        session = client.authenticate()
        pooled = PooledSession(session=session)
        self._total_created += 1
        logger.debug(
            "Created new Odoo session (uid=%d, total_created=%d)",
            session.uid,
            self._total_created,
        )
        return pooled

    def acquire(self, client: OdooRPCClient, timeout: float = 30.0) -> OdooSession:
        """Acquire a session from the pool.

        Args:
            client: Odoo RPC client for creating new sessions if needed.
            timeout: Maximum time to wait for a session.

        Returns:
            Authenticated OdooSession ready for use.

        Raises:
            RuntimeError: If unable to acquire a session within timeout.
        """
        start_time = time.time()

        while True:
            try:
                # Try to get an existing session
                pooled = self._pool.get_nowait()
            except Empty:
                # No sessions available, create new one if under limit
                with self._lock:
                    if self._total_created < self.max_size:
                        pooled = self._create_session(client)
                    else:
                        # Pool exhausted, wait for a session
                        elapsed = time.time() - start_time
                        remaining = timeout - elapsed
                        if remaining <= 0:
                            raise RuntimeError(
                                f"Timeout waiting for Odoo session after {timeout}s"
                            )
                        try:
                            pooled = self._pool.get(timeout=remaining)
                        except Empty:
                            raise RuntimeError(
                                f"Timeout waiting for Odoo session after {timeout}s"
                            )

            # Check if session is still healthy
            if self._is_session_healthy(pooled):
                pooled.mark_used()
                self._total_acquired += 1
                logger.debug(
                    "Acquired healthy session (uid=%d, use_count=%d)",
                    pooled.session.uid,
                    pooled.use_count,
                )
                return pooled.session
            else:
                # Session is stale, reconnect
                logger.debug(
                    "Session unhealthy (age=%.0fs, idle=%.0fs), reconnecting",
                    pooled.age_seconds,
                    pooled.idle_seconds,
                )
                try:
                    new_session = client.authenticate()
                    pooled.session = new_session
                    pooled.is_healthy = True
                    pooled.created_at = time.time()
                    pooled.use_count = 0
                    self._total_reconnected += 1
                    pooled.mark_used()
                    self._total_acquired += 1
                    return pooled.session
                except Exception as exc:
                    logger.warning("Reconnection failed: %s", exc)
                    # Discard this pooled session and try again
                    continue

    def release(self, session: OdooSession) -> None:
        """Release a session back to the pool.

        Args:
            session: The session to release.
        """
        # Find the pooled session wrapper
        found = None
        temp_sessions = []
        
        # Drain the queue to find our session
        while True:
            try:
                pooled = self._pool.get_nowait()
                if pooled.session is session:
                    found = pooled
                    break
                temp_sessions.append(pooled)
            except Empty:
                break

        if found is not None:
            # Check if session should be discarded
            if (
                found.age_seconds > self.max_age_seconds
                or found.idle_seconds > self.max_idle_seconds
            ):
                logger.debug(
                    "Discarding old session (age=%.0fs, idle=%.0fs)",
                    found.age_seconds,
                    found.idle_seconds,
                )
            else:
                found.is_healthy = True
                try:
                    self._pool.put_nowait(found)
                    self._total_released += 1
                    logger.debug("Released session back to pool")
                except:
                    pass  # Pool full, let it be garbage collected

        # Put back the temp sessions
        for temp in temp_sessions:
            try:
                self._pool.put_nowait(temp)
            except:
                pass  # Pool full, let it be garbage discarded

    def _is_session_healthy(self, pooled: PooledSession) -> bool:
        """Check if a session is healthy.

        Args:
            pooled: Pooled session to check.

        Returns:
            True if session is healthy and can be used.
        """
        # Check age
        if pooled.age_seconds > self.max_age_seconds:
            logger.debug("Session too old: %.0fs > %.0fs", pooled.age_seconds, self.max_age_seconds)
            return False

        # Check idle time
        if pooled.idle_seconds > self.max_idle_seconds:
            logger.debug("Session idle too long: %.0fs > %.0fs", pooled.idle_seconds, self.max_idle_seconds)
            return False

        # Check explicit health flag
        if not pooled.is_healthy:
            return False

        # Check session authenticated status
        if not pooled.session.authenticated:
            return False

        return True

    def health_check(self, client: OdooRPCClient) -> int:
        """Perform health check on all pooled sessions.

        Args:
            client: Odoo RPC client for re-authentication if needed.

        Returns:
            Number of sessions reconnected.
        """
        reconnected = 0
        temp_sessions = []

        while True:
            try:
                pooled = self._pool.get_nowait()
            except Empty:
                break

            if not self._is_session_healthy(pooled):
                # Try to reconnect
                try:
                    new_session = client.authenticate()
                    pooled.session = new_session
                    pooled.is_healthy = True
                    pooled.created_at = time.time()
                    pooled.use_count = 0
                    reconnected += 1
                    logger.debug("Health check reconnected session")
                except Exception as exc:
                    logger.warning("Health check reconnection failed: %s", exc)
                    pooled.is_healthy = False
                    # Don't put unhealthy session back

            temp_sessions.append(pooled)

        # Put sessions back
        for pooled in temp_sessions:
            if pooled.is_healthy:
                try:
                    self._pool.put_nowait(pooled)
                except:
                    pass  # Pool full

        return reconnected

    def get_stats(self) -> dict:
        """Get pool statistics.

        Returns:
            Dict with pool statistics.
        """
        with self._lock:
            current_size = self._pool.qsize()
            return {
                "current_size": current_size,
                "max_size": self.max_size,
                "min_size": self.min_size,
                "total_created": self._total_created,
                "total_acquired": self._total_acquired,
                "total_released": self._total_released,
                "total_reconnected": self._total_reconnected,
                "utilization": (
                    (self._total_acquired - self._total_released) / max(1, self._total_acquired) * 100
                ),
            }

    def close_all(self) -> None:
        """Close all sessions in the pool."""
        with self._lock:
            count = 0
            while True:
                try:
                    self._pool.get_nowait()
                    count += 1
                except Empty:
                    break
            logger.debug("Closed %d sessions", count)


class SessionManager:
    """High-level session manager using connection pool.

    Provides context manager interface for session acquisition.
    """

    def __init__(
        self,
        pool: OdooConnectionPool,
        client: OdooRPCClient,
    ) -> None:
        """Initialize session manager.

        Args:
            pool: Connection pool to use.
            client: Odoo RPC client for authentication.
        """
        self.pool = pool
        self.client = client
        self._session: OdooSession | None = None

    def __enter__(self) -> OdooSession:
        """Acquire session on context entry."""
        self._session = self.pool.acquire(self.client)
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release session on context exit."""
        if self._session is not None:
            self.pool.release(self._session)
            self._session = None

    def get_session(self) -> OdooSession:
        """Get current session.

        Returns:
            Current session, or raises RuntimeError if not in context.
        """
        if self._session is None:
            raise RuntimeError("Session not acquired. Use context manager.")
        return self._session
