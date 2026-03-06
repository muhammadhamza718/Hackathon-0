"""Resilient executor — exponential backoff, quarantine, circuit breaker.

Implements the three-layer resilience architecture per Constitution XIV:
  Layer 1: Exponential backoff for transient errors (429, 5xx, timeouts).
  Layer 2: Quarantine-first for logic errors (400, 401, 403, 422).
  Layer 3: Circuit breaker — open after 3 consecutive failures.
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar

from agents.constants import (
    BACKOFF_BASE_SECONDS,
    BACKOFF_MAX_SECONDS,
    CIRCUIT_BREAKER_THRESHOLD,
    MAX_RETRIES,
    NEEDS_ACTION_DIR,
    QUARANTINE_PREFIX,
)
from agents.exceptions import (
    CircuitOpenError,
    LogicAPIError,
    QuarantineError,
    TransientAPIError,
)
from agents.gold.models import CircuitBreakerState, ErrorType, QuarantinedItem
from agents.utils import ensure_dir, utcnow_iso

T = TypeVar("T")


def classify_error(exc: Exception) -> ErrorType:
    """Classify an exception as transient or logic.

    Transient: ``TransientAPIError``, ``ConnectionError``, ``TimeoutError``.
    Logic: ``LogicAPIError``, ``ValueError``, ``TypeError``.
    """
    if isinstance(exc, TransientAPIError | ConnectionError | TimeoutError):
        return ErrorType.TRANSIENT
    if isinstance(exc, LogicAPIError | ValueError | TypeError):
        return ErrorType.LOGIC
    # Default: treat unknown as transient to allow retry
    return ErrorType.TRANSIENT


def _backoff_delay(attempt: int) -> float:
    """Calculate exponential backoff delay with jitter.

    Sequence: 1s, 2s, 4s, 8s, 16s  (capped at 60s).
    Jitter: uniform [0, delay/2].
    """
    delay = min(BACKOFF_BASE_SECONDS * (2 ** attempt), BACKOFF_MAX_SECONDS)
    jitter = random.uniform(0, delay / 2)  # noqa: S311
    return delay + jitter


class ResilientExecutor:
    """Execute operations with backoff, quarantine, and circuit breaker."""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root
        self._breakers: dict[str, CircuitBreakerState] = {}

    # ------------------------------------------------------------------
    # Circuit breaker helpers
    # ------------------------------------------------------------------

    def get_circuit_state(self, api_name: str) -> CircuitBreakerState:
        """Return (or create) the circuit breaker for *api_name*."""
        if api_name not in self._breakers:
            self._breakers[api_name] = CircuitBreakerState(api_name=api_name)
        return self._breakers[api_name]

    # ------------------------------------------------------------------
    # Core execute
    # ------------------------------------------------------------------

    def execute(
        self,
        operation: Callable[..., T],
        api_name: str,
        *args: object,
        max_retries: int = MAX_RETRIES,
        **kwargs: object,
    ) -> T:
        """Run *operation* with full resilience stack.

        1. Check circuit breaker → raise ``CircuitOpenError`` if open.
        2. On success → reset breaker, return result.
        3. On transient error → exponential backoff, retry up to *max_retries*.
        4. On logic error → quarantine immediately, no retry.
        5. After all retries exhausted → record failure, maybe open breaker.

        Returns:
            The operation result on success.

        Raises:
            CircuitOpenError: If the circuit breaker for *api_name* is open.
            LogicAPIError: If a non-retryable error occurs.
            TransientAPIError: If all retries are exhausted.
        """
        breaker = self.get_circuit_state(api_name)

        if breaker.is_open:
            raise CircuitOpenError(api_name)

        last_exc: Exception | None = None

        for attempt in range(max_retries):
            try:
                result = operation(*args, **kwargs)
                breaker.record_success()
                return result  # type: ignore[return-value]
            except Exception as exc:
                error_type = classify_error(exc)

                if error_type is ErrorType.LOGIC:
                    breaker.record_failure(
                        str(exc), threshold=CIRCUIT_BREAKER_THRESHOLD
                    )
                    raise

                # Transient — backoff and retry
                last_exc = exc
                breaker.record_failure(
                    str(exc), threshold=CIRCUIT_BREAKER_THRESHOLD
                )

                if breaker.is_open:
                    raise CircuitOpenError(api_name) from exc

                if attempt < max_retries - 1:
                    time.sleep(_backoff_delay(attempt))

        # All retries exhausted
        raise TransientAPIError(
            f"All {max_retries} retries exhausted for '{api_name}': {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Quarantine
    # ------------------------------------------------------------------

    def quarantine(
        self,
        filename: str,
        error: Exception,
        payload: dict | None = None,
    ) -> QuarantinedItem:
        """Quarantine a failed operation and create a P0 alert.

        Renames the source file with the ``[QUARANTINED]_`` prefix and
        writes a high-priority alert into ``/Needs_Action/``.

        Returns:
            A ``QuarantinedItem`` describing the quarantined operation.
        """
        ts = utcnow_iso()
        q_filename = f"{QUARANTINE_PREFIX}{filename}"
        error_type = (
            "logic_error"
            if isinstance(error, LogicAPIError | ValueError | TypeError)
            else "system_error"
        )
        status_code = getattr(error, "status_code", None)

        item = QuarantinedItem(
            original_filename=filename,
            quarantined_filename=q_filename,
            error_type=error_type,
            http_status=status_code,
            error_message=str(error),
            original_payload=payload or {},
            quarantined_at=ts,
            alert_created=True,
        )

        # Write P0 alert
        needs_action = ensure_dir(self.vault_root / NEEDS_ACTION_DIR)
        alert_path = needs_action / q_filename
        alert_content = (
            "---\n"
            "priority: P0\n"
            "type: system-failure\n"
            f"quarantined_at: {ts}\n"
            f"original_file: {filename}\n"
            "---\n\n"
            "# System Failure Alert\n\n"
            f"**Error Type**: {error_type} (HTTP {status_code or 'N/A'})\n"
            f"**Message**: {error}\n"
        )
        alert_path.write_text(alert_content, encoding="utf-8")

        return item
