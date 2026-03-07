"""Odoo JSON-RPC client for Odoo 19+ integration.

Provides a type-safe client for interacting with Odoo's JSON-RPC API
for accounting operations, invoice management, and bank reconciliation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from .config import OdooConfig as OdooConfigData
from .exceptions import (
    OdooAuthenticationError,
    OdooConnectionError,
    OdooOperationError,
)
from .models import OdooOperation, OdooSession

logger = logging.getLogger(__name__)


class OdooRPCClient:
    """Client for Odoo JSON-RPC API.

    Supports:
    - Authentication and session management
    - Model operations (search, read, create, write, unlink)
    - Method calls on models
    - Batch operations
    """

    def __init__(self, config: OdooConfigData | None = None):
        """Initialize the Odoo RPC client.

        Args:
            config: Odoo configuration. If None, loads from environment.
        """
        self.config = config or OdooConfigData.from_env()
        self.session: OdooSession | None = None
        self._session_id: str | None = None

    def _get_endpoint(self, path: str) -> str:
        """Get the full endpoint URL."""
        return f"{self.config.url}{path}"

    def _make_request(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a JSON-RPC request to Odoo.

        Args:
            method: The RPC method to call.
            params: Method parameters.

        Returns:
            The JSON-RPC response.

        Raises:
            OdooConnectionError: If connection fails.
            OdooOperationError: If the operation fails.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": 1,
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                self._get_endpoint("/jsonrpc"),
                data=json.dumps(payload),
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error = result["error"]
                raise OdooOperationError(
                    operation=method,
                    message=error.get("message", "Unknown error"),
                )

            return result.get("result", {})

        except requests.exceptions.RequestException as e:
            raise OdooConnectionError(f"Connection failed: {e}") from e

    def authenticate(self) -> OdooSession:
        """Authenticate with Odoo and create a session.

        Returns:
            The authenticated session.

        Raises:
            OdooAuthenticationError: If authentication fails.
        """
        try:
            result = self._make_request(
                "authenticate",
                {
                    "db": self.config.database,
                    "login": self.config.username,
                    "password": self.config.api_key,
                },
            )

            uid = result.get("uid")
            if not uid:
                raise OdooAuthenticationError("Authentication failed: no UID")

            self.session = OdooSession(
                url=self.config.url,
                database=self.config.database,
                uid=uid,
                authenticated=True,
            )
            self._session_id = result.get("session_id")

            logger.info(f"Authenticated to Odoo as user {uid}")
            return self.session

        except OdooOperationError as e:
            raise OdooAuthenticationError(str(e)) from e

    def execute(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a method on an Odoo model.

        Args:
            model: The model name (e.g., 'account.move').
            method: The method name (e.g., 'search_read').
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            The method result.

        Raises:
            OdooOperationError: If the operation fails.
        """
        if self.session is None or not self.session.authenticated:
            self.authenticate()

        params = {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        }

        # Log operation
        operation = OdooOperation(
            operation_id=f"op_{model}_{method}",
            model=model,
            method=method,
            args=tuple(args or []),
            kwargs=kwargs or {},
            is_write=method in ("create", "write", "unlink"),
        )

        logger.debug(f"Executing {model}.{method}")
        result = self._make_request("execute", params)
        operation.status = "executed"
        operation.result = result

        return result

    def search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search and read records from a model.

        Args:
            model: The model name.
            domain: Search domain (list of tuples).
            fields: List of fields to return.
            limit: Maximum number of records.
            offset: Number of records to skip.
            order: Order by field.

        Returns:
            List of records as dictionaries.
        """
        kwargs = {
            "domain": domain or [],
            "fields": fields or [],
            "offset": offset,
        }

        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order

        return self.execute(model, "search_read", kwargs=kwargs)

    def search(
        self,
        model: str,
        domain: list[Any] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
    ) -> list[int]:
        """Search for record IDs.

        Args:
            model: The model name.
            domain: Search domain.
            limit: Maximum number of records.
            offset: Number of records to skip.
            order: Order by field.

        Returns:
            List of record IDs.
        """
        kwargs = {
            "domain": domain or [],
            "offset": offset,
        }

        if limit is not None:
            kwargs["limit"] = limit
        if order is not None:
            kwargs["order"] = order

        return self.execute(model, "search", kwargs=kwargs)

    def read(
        self, model: str, ids: list[int], fields: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Read records by ID.

        Args:
            model: The model name.
            ids: List of record IDs.
            fields: List of fields to return.

        Returns:
            List of records as dictionaries.
        """
        return self.execute(
            model, "read", args=[ids], kwargs={"fields": fields or []}
        )

    def create(
        self, model: str, values: dict[str, Any]
    ) -> int | list[int]:
        """Create new records.

        Args:
            model: The model name.
            values: Field values for the new record(s).

        Returns:
            ID of the created record, or list of IDs for multiple records.
        """
        return self.execute(model, "create", args=[values])

    def write(
        self, model: str, ids: list[int], values: dict[str, Any]
    ) -> bool:
        """Update existing records.

        Args:
            model: The model name.
            ids: List of record IDs to update.
            values: Field values to update.

        Returns:
            True if successful.
        """
        return self.execute(model, "write", args=[ids, values])

    def unlink(self, model: str, ids: list[int]) -> bool:
        """Delete records.

        Args:
            model: The model name.
            ids: List of record IDs to delete.

        Returns:
            True if successful.
        """
        return self.execute(model, "unlink", args=[ids])

    def call_method(
        self, model: str, record_id: int, method: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Call a method on a specific record.

        Args:
            model: The model name.
            record_id: The record ID.
            method: The method name.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            The method result.
        """
        return self.execute(
            model, method, args=[record_id, *args], kwargs=kwargs
        )

    def get_version(self) -> dict[str, Any]:
        """Get Odoo server version information.

        Returns:
            Dictionary with version information.
        """
        return self._make_request(
            "call",
            {"service": "common", "method": "version"},
        )

    def is_connected(self) -> bool:
        """Check if connected to Odoo."""
        return self.session is not None and self.session.authenticated

    def disconnect(self) -> None:
        """Disconnect from Odoo."""
        self.session = None
        self._session_id = None
        logger.info("Disconnected from Odoo")
