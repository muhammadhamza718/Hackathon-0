"""Odoo MCP server wrapper for JSON-RPC integration.

Provides an MCP (Model Context Protocol) server interface for Odoo
operations, enabling AI agents to interact with Odoo through a
standardized protocol.
"""

from __future__ import annotations

import logging
from typing import Any

from .odoo_rpc_client import OdooRPCClient
from .resilient_executor import ResilientExecutor

logger = logging.getLogger(__name__)


class OdooMCPServer:
    """MCP server wrapper for Odoo JSON-RPC operations.

    This class provides a standardized interface for AI agents to
    interact with Odoo through MCP tools and resources.

    Tools provided:
    - odoo_search: Search for records
    - odoo_read: Read record fields
    - odoo_create: Create new records
    - odoo_write: Update existing records
    - odoo_unlink: Delete records
    - odoo_call: Call a method on a record
    - odoo_search_read: Search and read in one call
    """

    def __init__(
        self,
        rpc_client: OdooRPCClient | None = None,
        executor: ResilientExecutor | None = None,
    ):
        """Initialize the Odoo MCP server.

        Args:
            rpc_client: Odoo RPC client instance.
            executor: Resilient executor for fault tolerance.
        """
        self.rpc_client = rpc_client or OdooRPCClient()
        self.executor = executor or ResilientExecutor()

    def connect(self) -> None:
        """Connect to Odoo server."""
        self.rpc_client.authenticate()
        logger.info("Odoo MCP server connected")

    def disconnect(self) -> None:
        """Disconnect from Odoo server."""
        self.rpc_client.disconnect()
        logger.info("Odoo MCP server disconnected")

    def is_connected(self) -> bool:
        """Check if connected to Odoo."""
        return self.rpc_client.is_connected()

    # -----------------------------------------------------------------------
    # MCP Tools
    # -----------------------------------------------------------------------

    def odoo_search(
        self,
        model: str,
        domain: list[Any] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
    ) -> list[int]:
        """Search for record IDs.

        Args:
            model: The model name (e.g., 'account.move').
            domain: Search domain as list of tuples.
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            order: Order by field name.

        Returns:
            List of record IDs.
        """
        return self.executor.execute_or_raise(
            self.rpc_client.search,
            model,
            domain=domain,
            limit=limit,
            offset=offset,
            order=order,
            operation_name=f"odoo_search_{model}",
        )

    def odoo_read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Read records by ID.

        Args:
            model: The model name.
            ids: List of record IDs to read.
            fields: List of field names to return.

        Returns:
            List of records as dictionaries.
        """
        return self.executor.execute_or_raise(
            self.rpc_client.read,
            model,
            ids,
            fields=fields,
            operation_name=f"odoo_read_{model}",
        )

    def odoo_create(
        self, model: str, values: dict[str, Any]
    ) -> int | list[int]:
        """Create new records.

        Args:
            model: The model name.
            values: Field values for the new record(s).

        Returns:
            ID of created record, or list of IDs.
        """
        return self.executor.execute_or_raise(
            self.rpc_client.create,
            model,
            values,
            operation_name=f"odoo_create_{model}",
        )

    def odoo_write(
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
        return self.executor.execute_or_raise(
            self.rpc_client.write,
            model,
            ids,
            values,
            operation_name=f"odoo_write_{model}",
        )

    def odoo_unlink(self, model: str, ids: list[int]) -> bool:
        """Delete records.

        Args:
            model: The model name.
            ids: List of record IDs to delete.

        Returns:
            True if successful.
        """
        return self.executor.execute_or_raise(
            self.rpc_client.unlink,
            model,
            ids,
            operation_name=f"odoo_unlink_{model}",
        )

    def odoo_call(
        self,
        model: str,
        record_id: int,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Call a method on a specific record.

        Args:
            model: The model name.
            record_id: The record ID.
            method: The method name.
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            The method result.
        """
        return self.executor.execute_or_raise(
            self.rpc_client.call_method,
            model,
            record_id,
            method,
            *(args or []),
            **(kwargs or {}),
            operation_name=f"odoo_call_{model}_{method}",
        )

    def odoo_search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        fields: list[str] | None = None,
        limit: int | None = None,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search and read records in one call.

        Args:
            model: The model name.
            domain: Search domain.
            fields: List of fields to return.
            limit: Maximum number of records.
            offset: Number of records to skip.
            order: Order by field.

        Returns:
            List of records as dictionaries.
        """
        return self.executor.execute_or_raise(
            self.rpc_client.search_read,
            model,
            domain=domain,
            fields=fields,
            limit=limit,
            offset=offset,
            order=order,
            operation_name=f"odoo_search_read_{model}",
        )

    # -----------------------------------------------------------------------
    # Accounting-specific helpers
    # -----------------------------------------------------------------------

    def get_invoices(
        self,
        state: str | None = None,
        move_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get invoices with optional filtering.

        Args:
            state: Filter by state (draft, posted, cancel).
            move_type: Filter by type (out_invoice, in_invoice, etc.).
            limit: Maximum number of invoices.

        Returns:
            List of invoice records.
        """
        domain = []
        if state:
            domain.append(("state", "=", state))
        if move_type:
            domain.append(("move_type", "=", move_type))

        return self.odoo_search_read(
            "account.move",
            domain=domain,
            fields=[
                "id",
                "name",
                "state",
                "move_type",
                "partner_id",
                "amount_total",
                "amount_due",
                "invoice_date",
                "invoice_date_due",
            ],
            limit=limit,
        )

    def get_bank_statements(
        self, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get bank statements for reconciliation.

        Args:
            limit: Maximum number of statements.

        Returns:
            List of bank statement records.
        """
        return self.odoo_search_read(
            "account.bank.statement.line",
            domain=[],
            fields=[
                "id",
                "name",
                "date",
                "amount",
                "partner_name",
                "payment_ref",
                "state",
            ],
            limit=limit,
        )

    def reconcile_bank_statement(
        self, statement_line_id: int, move_line_ids: list[int]
    ) -> bool:
        """Reconcile a bank statement line with move lines.

        Args:
            statement_line_id: The bank statement line ID.
            move_line_ids: List of move line IDs to reconcile with.

        Returns:
            True if successful.
        """
        return self.odoo_write(
            "account.bank.statement.line",
            [statement_line_id],
            {
                "reconciled_move_line_ids": [(6, 0, move_line_ids)],
            },
        )

    # -----------------------------------------------------------------------
    # Resource interface
    # -----------------------------------------------------------------------

    def get_resource(
        self, uri: str
    ) -> dict[str, Any] | None:
        """Get a resource by URI.

        Supports URIs like:
        - odoo://account.move/123
        - odoo://res.partner/456

        Args:
            uri: The resource URI.

        Returns:
            Resource data as dictionary, or None if not found.
        """
        if not uri.startswith("odoo://"):
            return None

        # Parse URI: odoo://model/id
        parts = uri.replace("odoo://", "").split("/")
        if len(parts) != 2:
            return None

        model, record_id_str = parts
        try:
            record_id = int(record_id_str)
        except ValueError:
            return None

        records = self.odoo_read(model, [record_id])
        return records[0] if records else None
