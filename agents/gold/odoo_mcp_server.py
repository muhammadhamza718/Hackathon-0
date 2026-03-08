"""Odoo MCP Server - JSON-RPC integration via Model Context Protocol.

This module provides an MCP server wrapper around the Odoo RPC client,
enabling external tools to interact with Odoo through standardized MCP
tool calls.

All WRITE operations are drafted to /Pending_Approval/ per Constitution XI.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agents.gold.odoo_rpc_client import OdooConfig, OdooRPCClient, load_odoo_config
from agents.gold.models import OdooSession

logger = logging.getLogger(__name__)


class OdooMCPServer:
    """MCP server for Odoo operations.

    Exposes Odoo CRUD operations as MCP tools with proper HITL gating
    for write operations.
    """

    def __init__(
        self,
        vault_root: Path,
        config: OdooConfig | None = None,
        session: OdooSession | None = None,
    ) -> None:
        """Initialize Odoo MCP server.

        Args:
            vault_root: Root path of the vault for approval workflows.
            config: Optional Odoo configuration. If not provided, loads
                   from environment variables.
            session: Optional injected Odoo session for testing/DI.
        """
        self.vault_root = vault_root
        self._config = config or load_odoo_config()
        self._client = OdooRPCClient(
            config=self._config,
            vault_root=vault_root,
            session=session,
        )
        self._authenticated = False

    # ------------------------------------------------------------------
    # MCP Tool Definitions
    # ------------------------------------------------------------------

    def get_tools(self) -> list[dict[str, Any]]:
        """Return list of MCP tool definitions.

        Returns:
            List of tool definitions compatible with MCP protocol.
        """
        return [
            {
                "name": "odoo_authenticate",
                "description": "Authenticate to Odoo and establish a session",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "odoo_search_read",
                "description": "Search and read records from an Odoo model (autonomous)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Odoo model name (e.g., 'res.partner', 'account.move')",
                        },
                        "domain": {
                            "type": "array",
                            "description": "Search domain as list of tuples",
                            "items": {"type": "array"},
                        },
                        "fields": {
                            "type": "array",
                            "description": "List of field names to retrieve",
                            "items": {"type": "string"},
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of records to return",
                            "default": 100,
                        },
                    },
                    "required": ["model", "domain", "fields"],
                },
            },
            {
                "name": "odoo_read_by_id",
                "description": "Read specific records by ID from an Odoo model",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Odoo model name",
                        },
                        "ids": {
                            "type": "array",
                            "description": "List of record IDs to read",
                            "items": {"type": "integer"},
                        },
                        "fields": {
                            "type": "array",
                            "description": "List of field names to retrieve",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["model", "ids", "fields"],
                },
            },
            {
                "name": "odoo_draft_create",
                "description": "Draft a create operation for approval (requires HITL)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Odoo model name",
                        },
                        "values": {
                            "type": "object",
                            "description": "Field values for the new record",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Business justification for this create operation",
                        },
                    },
                    "required": ["model", "values", "rationale"],
                },
            },
            {
                "name": "odoo_draft_write",
                "description": "Draft a write (update) operation for approval (requires HITL)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Odoo model name",
                        },
                        "ids": {
                            "type": "array",
                            "description": "List of record IDs to update",
                            "items": {"type": "integer"},
                        },
                        "values": {
                            "type": "object",
                            "description": "Field values to update",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Business justification for this update",
                        },
                    },
                    "required": ["model", "ids", "values", "rationale"],
                },
            },
            {
                "name": "odoo_execute_approved",
                "description": "Execute a previously approved Odoo operation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation_id": {
                            "type": "string",
                            "description": "Operation ID from the approved file",
                        },
                        "model": {
                            "type": "string",
                            "description": "Odoo model name",
                        },
                        "method": {
                            "type": "string",
                            "description": "Operation method (create/write)",
                        },
                    },
                    "required": ["operation_id", "model", "method"],
                },
            },
        ]

    # ------------------------------------------------------------------
    # MCP Tool Handlers
    # ------------------------------------------------------------------

    def handle_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle an MCP tool call.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool arguments as a dict.

        Returns:
            Tool execution result with success/error status.
        """
        handlers = {
            "odoo_authenticate": self._tool_authenticate,
            "odoo_search_read": self._tool_search_read,
            "odoo_read_by_id": self._tool_read_by_id,
            "odoo_draft_create": self._tool_draft_create,
            "odoo_draft_write": self._tool_draft_write,
            "odoo_execute_approved": self._tool_execute_approved,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }

        try:
            result = handler(arguments)
            return {"success": True, "result": result}
        except Exception as exc:
            logger.exception("Tool call failed: %s", tool_name)
            return {
                "success": False,
                "error": str(exc),
            }

    def _tool_authenticate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Authenticate to Odoo."""
        session = self._client.authenticate()
        self._authenticated = True
        return {
            "uid": session.uid,
            "database": session.database,
            "authenticated": session.authenticated,
        }

    def _tool_search_read(
        self, args: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Execute search_read on Odoo model."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated. Call odoo_authenticate first.")

        return self._client.search_read(
            model=args["model"],
            domain=args["domain"],
            fields=args["fields"],
            limit=args.get("limit", 100),
        )

    def _tool_read_by_id(
        self, args: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Read records by ID."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated. Call odoo_authenticate first.")

        return self._client.read(
            model=args["model"],
            ids=args["ids"],
            fields=args["fields"],
        )

    def _tool_draft_create(self, args: dict[str, Any]) -> dict[str, Any]:
        """Draft a create operation."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated. Call odoo_authenticate first.")

        operation = self._client.draft_create(
            model=args["model"],
            values=args["values"],
            rationale=args["rationale"],
        )

        return {
            "operation_id": operation.operation_id,
            "status": operation.status,
            "approval_file": operation.operation_id,  # Reference to approval file
        }

    def _tool_draft_write(self, args: dict[str, Any]) -> dict[str, Any]:
        """Draft a write operation."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated. Call odoo_authenticate first.")

        operation = self._client.draft_write(
            model=args["model"],
            ids=args["ids"],
            values=args["values"],
            rationale=args["rationale"],
        )

        return {
            "operation_id": operation.operation_id,
            "status": operation.status,
            "approval_file": operation.operation_id,
        }

    def _tool_execute_approved(
        self, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute an approved operation."""
        if not self._authenticated:
            raise RuntimeError("Not authenticated. Call odoo_authenticate first.")

        from agents.gold.models import OdooOperation

        operation = OdooOperation(
            operation_id=args["operation_id"],
            model=args["model"],
            method=args["method"],
            args=(),  # Will be reconstructed from approval file
        )

        result = self._client.execute_approved(operation)

        return {
            "operation_id": result.operation_id,
            "status": result.status,
            "result": result.result,
        }

    # ------------------------------------------------------------------
    # Server Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the MCP server (blocking).

        In production, this would integrate with an MCP host.
        For now, this is a placeholder for future MCP integration.
        """
        logger.info("Odoo MCP Server initialized")
        logger.info("Available tools: %s", [t["name"] for t in self.get_tools()])
        # Future: integrate with actual MCP protocol handler
        # For now, the server is available for programmatic use


def create_odoo_mcp_server(
    vault_root: Path,
    config: OdooConfig | None = None,
) -> OdooMCPServer:
    """Factory function to create an Odoo MCP server instance.

    Args:
        vault_root: Root path of the vault.
        config: Optional Odoo configuration.

    Returns:
        Configured OdooMCPServer instance.
    """
    return OdooMCPServer(vault_root=vault_root, config=config)
