"""Resilient executor with exponential backoff and circuit breaker.

Provides fault-tolerant execution for Gold Tier operations with automatic
retry logic, exponential backoff, and circuit breaker pattern.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

from .config import ResilienceConfig
from .exceptions import (
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
    ResilienceError,
)

T = TypeVar("T")


@dataclass
class ExecutionResult:
    """Result of a resilient execution."""

    success: bool
    value: Any = None
    error: str | None = None
    retries_attempted: int = 0
    duration_ms: int = 0


@dataclass
class CircuitBreaker:
    """Circuit breaker for a specific API or operation."""

    name: str
    failure_count: int = 0
    last_failure_time: datetime | None = None
    is_open: bool = False
    opened_at: datetime | None = None
    failure_threshold: int = 3
    reset_timeout_seconds: float = 30.0

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            self.opened_at = self.last_failure_time

    def record_success(self) -> None:
        """Record a success and reset the circuit breaker."""
        self.failure_count = 0
        self.is_open = False
        self.opened_at = None

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if not self.is_open:
            return True

        # Check if reset timeout has elapsed
        if self.opened_at is None:
            return False

        elapsed = (
            datetime.now(timezone.utc) - self.opened_at
        ).total_seconds()
        if elapsed >= self.reset_timeout_seconds:
            # Half-open: allow one test execution
            return True

        return False

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self.is_open = False
        self.opened_at = None
        self.last_failure_time = None


class ResilientExecutor:
    """Executes operations with resilience patterns.

    Features:
    - Exponential backoff retry logic
    - Circuit breaker pattern
    - Configurable retry limits
    - Execution result tracking
    """

    def __init__(self, config: ResilienceConfig | None = None):
        """Initialize the resilient executor.

        Args:
            config: Resilience configuration.
        """
        self.config = config or ResilienceConfig.from_env()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    def _get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker for the given name."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=self.config.circuit_breaker_threshold,
                reset_timeout_seconds=self.config.circuit_breaker_reset_seconds,
            )
        return self._circuit_breakers[name]

    def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        operation_name: str = "operation",
        **kwargs: Any,
    ) -> ExecutionResult:
        """Execute a function with resilience patterns.

        Args:
            func: The function to execute.
            *args: Positional arguments for the function.
            operation_name: Name of the operation (for circuit breaker).
            **kwargs: Keyword arguments for the function.

        Returns:
            ExecutionResult with success status and value or error.
        """
        circuit_breaker = self._get_circuit_breaker(operation_name)
        start_time = datetime.now(timezone.utc)

        # Check circuit breaker
        if not circuit_breaker.can_execute():
            return ExecutionResult(
                success=False,
                error=f"Circuit breaker open for {operation_name}",
                retries_attempted=0,
            )

        last_error: Exception | None = None
        retries_attempted = 0

        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()

                duration_ms = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds()
                    * 1000
                )

                return ExecutionResult(
                    success=True,
                    value=result,
                    retries_attempted=retries_attempted,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                last_error = e
                retries_attempted = attempt
                circuit_breaker.record_failure()

                # Check if we should retry
                if attempt < self.config.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.config.exponential_base**attempt
                        * self.config.base_delay_seconds,
                        self.config.max_delay_seconds,
                    )
                    time.sleep(delay)
                else:
                    # Max retries exceeded
                    break

        duration_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        return ExecutionResult(
            success=False,
            error=str(last_error) if last_error else "Unknown error",
            retries_attempted=retries_attempted,
            duration_ms=duration_ms,
        )

    def execute_or_raise(
        self,
        func: Callable[..., T],
        *args: Any,
        operation_name: str = "operation",
        **kwargs: Any,
    ) -> T:
        """Execute a function and raise on failure.

        Args:
            func: The function to execute.
            *args: Positional arguments for the function.
            operation_name: Name of the operation (for circuit breaker).
            **kwargs: Keyword arguments for the function.

        Returns:
            The function result.

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open.
            MaxRetriesExceededError: If max retries exceeded.
            ResilienceError: For other execution errors.
        """
        result = self.execute(
            func, *args, operation_name=operation_name, **kwargs
        )

        if not result.success:
            if "Circuit breaker open" in (result.error or ""):
                raise CircuitBreakerOpenError(operation_name, result.error)
            if result.retries_attempted >= self.config.max_retries:
                raise MaxRetriesExceededError(
                    f"Max retries ({self.config.max_retries}) exceeded for {operation_name}: {result.error}"
                )
            raise ResilienceError(result.error or "Execution failed")

        return result.value  # type: ignore

    def get_circuit_breaker_status(
        self, name: str
    ) -> dict[str, Any] | None:
        """Get the status of a circuit breaker.

        Args:
            name: The circuit breaker name.

        Returns:
            Dictionary with circuit breaker status, or None if not found.
        """
        if name not in self._circuit_breakers:
            return None

        cb = self._circuit_breakers[name]
        return {
            "name": cb.name,
            "failure_count": cb.failure_count,
            "is_open": cb.is_open,
            "failure_threshold": cb.failure_threshold,
            "reset_timeout_seconds": cb.reset_timeout_seconds,
            "last_failure_time": (
                cb.last_failure_time.isoformat()
                if cb.last_failure_time
                else None
            ),
            "opened_at": (
                cb.opened_at.isoformat() if cb.opened_at else None
            ),
        }

    def reset_circuit_breaker(self, name: str) -> None:
        """Manually reset a circuit breaker.

        Args:
            name: The circuit breaker name.
        """
        if name in self._circuit_breakers:
            self._circuit_breakers[name].reset()

    def reset_all_circuit_breakers(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._circuit_breakers.values():
            cb.reset()
