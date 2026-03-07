"""Odoo connection pooling and session management.

Provides efficient connection pooling for Odoo JSON-RPC connections
with automatic session management and health checking.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from .config import OdooConfig as OdooConfigData
from .odoo_rpc_client import OdooRPCClient
from .models import OdooSession

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """A pooled Odoo connection."""

    client: OdooRPCClient
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    use_count: int = 0
    is_healthy: bool = True

    def touch(self) -> None:
        """Update last used timestamp and increment use count."""
        self.last_used_at = datetime.now(timezone.utc)
        self.use_count += 1

    def age_seconds(self) -> float:
        """Get connection age in seconds."""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now(timezone.utc) - self.last_used_at).total_seconds()


class OdooConnectionPool:
    """Connection pool for Odoo RPC clients.

    Features:
    - Configurable pool size
    - Automatic connection health checking
    - Session reuse
    - Connection aging and cleanup
    """

    def __init__(
        self,
        config: OdooConfigData | None = None,
        pool_size: int = 5,
        max_idle_seconds: float = 300.0,
        max_age_seconds: float = 3600.0,
        health_check_interval: float = 60.0,
    ):
        """Initialize the connection pool.

        Args:
            config: Odoo configuration.
            pool_size: Maximum number of connections in the pool.
            max_idle_seconds: Maximum idle time before connection is closed.
            max_age_seconds: Maximum connection age before refresh.
            health_check_interval: Interval between health checks.
        """
        self.config = config or OdooConfigData.from_env()
        self.pool_size = pool_size
        self.max_idle_seconds = max_idle_seconds
        self.max_age_seconds = max_age_seconds
        self.health_check_interval = health_check_interval

        self._pool: deque[PooledConnection] = deque()
        self._in_use: set[PooledConnection] = set()
        self._lock = threading.Lock()
        self._initialized = False

    def _create_connection(self) -> PooledConnection:
        """Create a new pooled connection."""
        client = OdooRPCClient(self.config)
        client.authenticate()

        return PooledConnection(client=client)

    def _is_healthy(self, conn: PooledConnection) -> bool:
        """Check if a connection is healthy."""
        if not conn.is_healthy:
            return False
        if conn.age_seconds() > self.max_age_seconds:
            return False
        if conn.idle_seconds() > self.max_idle_seconds:
            return False
        try:
            # Quick health check
            conn.client.get_version()
            return True
        except Exception:
            return False

    def initialize(self) -> None:
        """Initialize the connection pool with pre-created connections."""
        if self._initialized:
            return

        with self._lock:
            for _ in range(min(2, self.pool_size)):
                try:
                    conn = self._create_connection()
                    self._pool.append(conn)
                    logger.debug(f"Created initial connection {id(conn)}")
                except Exception as e:
                    logger.warning(f"Failed to create initial connection: {e}")

            self._initialized = True
            logger.info(f"Connection pool initialized with {len(self._pool)} connections")

    def acquire(self, timeout: float = 30.0) -> OdooRPCClient:
        """Acquire a connection from the pool.

        Args:
            timeout: Maximum time to wait for a connection.

        Returns:
            An OdooRPCClient instance.

        Raises:
            TimeoutError: If no connection available within timeout.
        """
        if not self._initialized:
            self.initialize()

        start_time = datetime.now(timezone.utc)

        while True:
            with self._lock:
                # Try to get a healthy connection from the pool
                while self._pool:
                    conn = self._pool.popleft()
                    if self._is_healthy(conn):
                        conn.touch()
                        self._in_use.add(conn)
                        logger.debug(f"Acquired connection {id(conn)}")
                        return conn.client
                    else:
                        # Close unhealthy connection
                        try:
                            conn.client.disconnect()
                        except Exception:
                            pass
                        logger.debug(f"Discarded unhealthy connection {id(conn)}")

                # No available connections, try to create a new one
                if len(self._in_use) < self.pool_size:
                    try:
                        conn = self._create_connection()
                        conn.touch()
                        self._in_use.add(conn)
                        logger.debug(f"Created new connection {id(conn)}")
                        return conn.client
                    except Exception as e:
                        logger.warning(f"Failed to create new connection: {e}")

            # Check timeout
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                raise TimeoutError(
                    f"Could not acquire connection within {timeout}s"
                )

            # Wait a bit before retrying
            import time
            time.sleep(0.1)

    def release(self, client: OdooRPCClient) -> None:
        """Release a connection back to the pool.

        Args:
            client: The OdooRPCClient to release.
        """
        with self._lock:
            # Find the connection for this client
            for conn in self._in_use:
                if conn.client is client:
                    self._in_use.remove(conn)

                    if self._is_healthy(conn):
                        self._pool.append(conn)
                        logger.debug(f"Released connection {id(conn)}")
                    else:
                        # Close unhealthy connection
                        try:
                            conn.client.disconnect()
                        except Exception:
                            pass
                        logger.debug(f"Discarded unhealthy connection {id(conn)}")
                    return

        logger.warning(f"Attempted to release unknown client {id(client)}")

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary with pool statistics.
        """
        with self._lock:
            return {
                "pool_size": self.pool_size,
                "available": len(self._pool),
                "in_use": len(self._in_use),
                "total_connections": len(self._pool) + len(self._in_use),
            }

    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            # Close pooled connections
            while self._pool:
                conn = self._pool.popleft()
                try:
                    conn.client.disconnect()
                except Exception:
                    pass
                logger.debug(f"Closed connection {id(conn)}")

            # Close in-use connections
            for conn in self._in_use:
                try:
                    conn.client.disconnect()
                except Exception:
                    pass
                logger.debug(f"Closed in-use connection {id(conn)}")

            self._in_use.clear()
            self._initialized = False

        logger.info("Connection pool closed")

    def __enter__(self) -> "OdooConnectionPool":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close_all()


class SessionManager:
    """Manages Odoo sessions with automatic renewal.

    Provides a higher-level interface for session management with
    automatic session renewal and connection pooling integration.
    """

    def __init__(self, pool: OdooConnectionPool | None = None):
        """Initialize the session manager.

        Args:
            pool: Connection pool to use.
        """
        self.pool = pool or OdooConnectionPool()
        self._sessions: dict[str, OdooSession] = {}
        self._lock = threading.Lock()

    def get_session(self, session_id: str = "default") -> OdooSession:
        """Get or create a session.

        Args:
            session_id: Session identifier.

        Returns:
            The Odoo session.
        """
        with self._lock:
            if session_id not in self._sessions:
                client = self.pool.acquire()
                self._sessions[session_id] = client.session or OdooSession(
                    url=client.config.url,
                    database=client.config.database,
                    authenticated=True,
                )
            return self._sessions[session_id]

    def release_session(self, session_id: str = "default") -> None:
        """Release a session back to the pool.

        Args:
            session_id: Session identifier.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

    def refresh_session(self, session_id: str = "default") -> OdooSession:
        """Refresh a session by re-authenticating.

        Args:
            session_id: Session identifier.

        Returns:
            The refreshed Odoo session.
        """
        client = self.pool.acquire()
        try:
            session = client.authenticate()
            with self._lock:
                self._sessions[session_id] = session
            return session
        finally:
            self.pool.release(client)

    def get_all_sessions(self) -> dict[str, OdooSession]:
        """Get all active sessions.

        Returns:
            Dictionary mapping session IDs to sessions.
        """
        with self._lock:
            return dict(self._sessions)

    def close_all(self) -> None:
        """Close all sessions and the connection pool."""
        with self._lock:
            self._sessions.clear()
        self.pool.close_all()
