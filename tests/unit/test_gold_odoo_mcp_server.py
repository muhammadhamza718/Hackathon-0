"""Unit tests for Odoo MCP Server."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agents.gold.models import OdooOperation, OdooSession
from agents.gold.odoo_mcp_server import OdooMCPServer, create_odoo_mcp_server
from agents.gold.odoo_rpc_client import OdooConfig


class TestOdooMCPServerInitialization:
    """Test Odoo MCP server initialization."""

    def test_server_initialization(self, tmp_path):
        """Test initializing the MCP server."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )

        server = OdooMCPServer(tmp_path, config=config)

        assert server.vault_root == tmp_path
        assert server._config == config
        assert not server._authenticated

    def test_server_initialization_with_injected_session(self, tmp_path):
        """Test initializing MCP server with injected session."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )

        injected_session = OdooSession(
            url="https://custom-odoo.com",
            database="custom_db",
            uid=99,
            authenticated=True,
        )

        server = OdooMCPServer(tmp_path, config=config, session=injected_session)

        assert server._client._session.uid == 99
        assert server._client._session.authenticated

    def test_factory_function(self, tmp_path):
        """Test the factory function creates server correctly."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )

        server = create_odoo_mcp_server(tmp_path, config=config)

        assert isinstance(server, OdooMCPServer)
        assert server.vault_root == tmp_path


class TestToolDefinitions:
    """Test MCP tool definitions."""

    def test_get_tools_returns_list(self, tmp_path):
        """Test that get_tools returns a list of tool definitions."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        tools = server.get_tools()

        assert isinstance(tools, list)
        assert len(tools) == 6  # 6 tools defined

    def test_tool_definitions_have_required_fields(self, tmp_path):
        """Test that each tool definition has required MCP fields."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        tools = server.get_tools()

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert isinstance(tool["inputSchema"], dict)

    def test_tool_names_are_correct(self, tmp_path):
        """Test that tool names match expected values."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        tools = server.get_tools()
        tool_names = [t["name"] for t in tools]

        expected_names = [
            "odoo_authenticate",
            "odoo_search_read",
            "odoo_read_by_id",
            "odoo_draft_create",
            "odoo_draft_write",
            "odoo_execute_approved",
        ]

        assert tool_names == expected_names


class TestToolCallHandling:
    """Test MCP tool call handling."""

    def test_handle_unknown_tool_returns_error(self, tmp_path):
        """Test that unknown tool names return an error."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        result = server.handle_tool_call("unknown_tool", {})

        assert not result["success"]
        assert "Unknown tool" in result["error"]

    @patch.object(OdooMCPServer, "_tool_authenticate")
    def test_handle_tool_call_catches_exceptions(
        self, mock_auth, tmp_path
    ):
        """Test that exceptions in tool handlers are caught."""
        mock_auth.side_effect = RuntimeError("Test error")

        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        result = server.handle_tool_call("odoo_authenticate", {})

        assert not result["success"]
        assert "Test error" in result["error"]


class TestAuthenticateTool:
    """Test odoo_authenticate tool."""

    @patch("agents.gold.odoo_rpc_client.requests")
    def test_authenticate_tool_success(self, mock_requests, tmp_path):
        """Test successful authentication via tool."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 5}
        mock_requests.post.return_value = mock_response

        result = server.handle_tool_call("odoo_authenticate", {})

        assert result["success"]
        assert result["result"]["uid"] == 5
        assert result["result"]["authenticated"]
        assert server._authenticated

    def test_authenticate_tool_requires_no_args(self, tmp_path):
        """Test that authenticate tool works with empty args."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # Should not raise with empty args
        result = server.handle_tool_call("odoo_authenticate", {})

        # Result depends on mock, but should not error on args


class TestSearchReadTool:
    """Test odoo_search_read tool."""

    @patch("agents.gold.odoo_rpc_client.requests")
    def test_search_read_requires_authentication(self, mock_requests, tmp_path):
        """Test that search_read requires prior authentication."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # Mock to avoid actual call
        mock_requests.post.return_value = Mock(
            status_code=200, json=Mock(return_value={"result": []})
        )

        result = server.handle_tool_call(
            "odoo_search_read",
            {
                "model": "res.partner",
                "domain": [("name", "=", "Test")],
                "fields": ["name"],
            },
        )

        assert not result["success"]
        assert "Not authenticated" in result["error"]

    @patch("agents.gold.odoo_rpc_client.requests")
    def test_search_read_success(self, mock_requests, tmp_path):
        """Test successful search_read via tool."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # First authenticate
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 5}
        mock_requests.post.return_value = mock_response

        server.handle_tool_call("odoo_authenticate", {})

        # Then search_read
        mock_response.json.return_value = {
            "result": [{"id": 1, "name": "Test Partner"}]
        }

        result = server.handle_tool_call(
            "odoo_search_read",
            {
                "model": "res.partner",
                "domain": [("name", "=", "Test")],
                "fields": ["name"],
                "limit": 10,
            },
        )

        assert result["success"]
        assert result["result"] == [{"id": 1, "name": "Test Partner"}]


class TestDraftCreateTool:
    """Test odoo_draft_create tool."""

    def test_draft_create_requires_authentication(self, tmp_path):
        """Test that draft_create requires prior authentication."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        result = server.handle_tool_call(
            "odoo_draft_create",
            {
                "model": "res.partner",
                "values": {"name": "Test Partner"},
                "rationale": "Testing",
            },
        )

        assert not result["success"]
        assert "Not authenticated" in result["error"]

    @patch("agents.gold.odoo_rpc_client.requests")
    def test_draft_create_success(self, mock_requests, tmp_path):
        """Test successful draft_create via tool."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # Authenticate first
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 5}
        mock_requests.post.return_value = mock_response

        server.handle_tool_call("odoo_authenticate", {})

        # Draft create
        result = server.handle_tool_call(
            "odoo_draft_create",
            {
                "model": "res.partner",
                "values": {"name": "Test Partner", "email": "test@example.com"},
                "rationale": "Creating test partner",
            },
        )

        assert result["success"]
        assert "operation_id" in result["result"]
        assert result["result"]["status"] == "pending"


class TestDraftWriteTool:
    """Test odoo_draft_write tool."""

    @patch("agents.gold.odoo_rpc_client.requests")
    def test_draft_write_success(self, mock_requests, tmp_path):
        """Test successful draft_write via tool."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # Authenticate
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 5}
        mock_requests.post.return_value = mock_response

        server.handle_tool_call("odoo_authenticate", {})

        # Draft write
        result = server.handle_tool_call(
            "odoo_draft_write",
            {
                "model": "res.partner",
                "ids": [1, 2],
                "values": {"name": "Updated Partner"},
                "rationale": "Updating test partners",
            },
        )

        assert result["success"]
        assert "operation_id" in result["result"]
        assert result["result"]["status"] == "pending"


class TestExecuteApprovedTool:
    """Test odoo_execute_approved tool."""

    @patch("agents.gold.odoo_rpc_client.requests")
    def test_execute_approved_success(self, mock_requests, tmp_path):
        """Test successful execute_approved via tool."""
        # Setup vault structure
        approved_dir = tmp_path / "Approved"
        approved_dir.mkdir()
        approved_file = approved_dir / "odoo-create-res.partner-test123.md"
        approved_file.write_text("""---
type: odoo_write_draft
model: res.partner
method: create
operation_id: test123
---
# Odoo Create

```json
{"name": "Test Partner"}
```
""")

        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key",
        )
        server = OdooMCPServer(tmp_path, config=config)

        # Authenticate
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 5}
        mock_requests.post.return_value = mock_response

        server.handle_tool_call("odoo_authenticate", {})

        # Mock execution response
        mock_response.json.return_value = {"result": 42}

        result = server.handle_tool_call(
            "odoo_execute_approved",
            {
                "operation_id": "test123",
                "model": "res.partner",
                "method": "create",
            },
        )

        assert result["success"]
        assert result["result"]["status"] == "executed"
        assert result["result"]["result"] == 42
