"""Unit tests for Gold Tier Odoo RPC client."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agents.constants import APPROVED_DIR, DONE_DIR, PENDING_APPROVAL_DIR
from agents.exceptions import ApprovalNotFoundError, ConfigurationError, OdooAuthError
from agents.gold.models import OdooSession
from agents.gold.odoo_rpc_client import OdooConfig, OdooRPCClient, load_odoo_config


class TestOdooConfigLoading:
    """Test loading Odoo configuration from environment."""

    def test_load_config_from_env(self, monkeypatch):
        """Test loading config from environment variables."""
        monkeypatch.setenv("ODOO_URL", "https://test-odoo.com")
        monkeypatch.setenv("ODOO_DB", "test_db")
        monkeypatch.setenv("ODOO_USERNAME", "admin")
        monkeypatch.setenv("ODOO_API_KEY", "test-key")

        config = load_odoo_config()

        assert config.url == "https://test-odoo.com"
        assert config.database == "test_db"
        assert config.username == "admin"
        assert config.api_key == "test-key"

    def test_load_config_missing_variables_raises(self, monkeypatch):
        """Test that missing required variables raise ConfigurationError."""
        # Clear all env vars
        monkeypatch.delenv("ODOO_URL", raising=False)
        monkeypatch.delenv("ODOO_DB", raising=False)
        monkeypatch.delenv("ODOO_USERNAME", raising=False)
        monkeypatch.delenv("ODOO_API_KEY", raising=False)

        with pytest.raises(ConfigurationError, match="Missing Odoo environment variables"):
            load_odoo_config()

    def test_config_trailing_slash_removed(self, monkeypatch):
        """Test that trailing slash is removed from URL."""
        monkeypatch.setenv("ODOO_URL", "https://test-odoo.com/")
        monkeypatch.setenv("ODOO_DB", "test_db")
        monkeypatch.setenv("ODOO_USERNAME", "admin")
        monkeypatch.setenv("ODOO_API_KEY", "test-key")

        config = load_odoo_config()

        assert config.url == "https://test-odoo.com"  # No trailing slash


class TestOdooRPCClientInitialization:
    """Test Odoo RPC client initialization."""

    def test_client_initialization(self, tmp_path):
        """Test initializing the client with config and vault root."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )

        client = OdooRPCClient(config, tmp_path)

        assert client.config == config
        assert client.vault_root == tmp_path
        assert client._session.url == "https://test-odoo.com"
        assert client._session.database == "test_db"

    def test_client_initialization_with_injected_session(self, tmp_path):
        """Test initializing the client with an injected session."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        
        # Create a pre-authenticated session to inject
        injected_session = OdooSession(
            url="https://custom-odoo.com",
            database="custom_db",
            uid=99,
            authenticated=True
        )

        client = OdooRPCClient(config, tmp_path, session=injected_session)

        assert client._session.uid == 99
        assert client._session.authenticated
        assert client._session.url == "https://custom-odoo.com"


class TestAuthentication:
    """Test Odoo authentication."""

    @patch('agents.gold.odoo_rpc_client.requests')
    def test_authenticate_success(self, mock_requests, tmp_path):
        """Test successful authentication."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 5}
        mock_requests.post.return_value = mock_response

        session = client.authenticate()

        assert session.authenticated
        assert session.uid == 5
        mock_requests.post.assert_called_once()

    @patch('agents.gold.odoo_rpc_client.requests')
    def test_authenticate_failure_raises(self, mock_requests, tmp_path):
        """Test that authentication failure raises OdooAuthError."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)

        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 0}  # Invalid UID
        mock_requests.post.return_value = mock_response

        with pytest.raises(OdooAuthError, match="Invalid Odoo credentials"):
            client.authenticate()


class TestReadOnlyOperations:
    """Test read-only operations (search_read, read)."""

    @patch('agents.gold.odoo_rpc_client.requests')
    def test_search_read_success(self, mock_requests, tmp_path):
        """Test successful search_read operation."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)

        # Set up session
        client._session.uid = 5
        client._session.authenticated = True

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [{"id": 1, "name": "Test"}]}
        mock_requests.post.return_value = mock_response

        result = client.search_read("res.partner", [("name", "=", "Test")], ["name"])

        assert result == [{"id": 1, "name": "Test"}]
        mock_requests.post.assert_called_once()

    @patch('agents.gold.odoo_rpc_client.requests')
    def test_read_success(self, mock_requests, tmp_path):
        """Test successful read operation."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)

        # Set up session
        client._session.uid = 5
        client._session.authenticated = True

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": [{"id": 1, "name": "Test"}]}
        mock_requests.post.return_value = mock_response

        result = client.read("res.partner", [1], ["name"])

        assert result == [{"id": 1, "name": "Test"}]


class TestWriteOperations:
    """Test write operations (draft_create, draft_write)."""

    def test_draft_create_creates_approval_file(self, tmp_path):
        """Test that draft_create creates an approval file in Pending_Approval."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)
        client._session.uid = 5
        client._session.authenticated = True

        values = {"name": "Test Partner", "email": "test@example.com"}
        operation = client.draft_create("res.partner", values, "Creating test partner")

        # Check that approval file was created
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        approval_files = list(pending_dir.glob("odoo-create-res.partner-*.md"))
        assert len(approval_files) == 1

        # Check file content
        content = approval_files[0].read_text()
        assert "type: odoo_write_draft" in content
        assert "model: res.partner" in content
        assert "method: create" in content
        assert '"name": "Test Partner"' in content
        assert "Creating test partner" in content

    def test_draft_write_creates_approval_file(self, tmp_path):
        """Test that draft_write creates an approval file in Pending_Approval."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)
        client._session.uid = 5
        client._session.authenticated = True

        values = {"name": "Updated Partner"}
        operation = client.draft_write("res.partner", [1], values, "Updating partner")

        # Check that approval file was created
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        approval_files = list(pending_dir.glob("odoo-write-res.partner-*.md"))
        assert len(approval_files) == 1

        # Check file content
        content = approval_files[0].read_text()
        assert "type: odoo_write_draft" in content
        assert "model: res.partner" in content
        assert "method: write" in content
        assert '"name": "Updated Partner"' in content


class TestExecuteApproved:
    """Test executing approved operations."""

    @patch('agents.gold.odoo_rpc_client.requests')
    def test_execute_approved_moves_file_to_done(self, mock_requests, tmp_path):
        """Test that execute_approved moves approved file to Done after execution."""
        # Setup vault structure
        approved_dir = tmp_path / APPROVED_DIR
        approved_dir.mkdir()
        done_dir = tmp_path / DONE_DIR
        done_dir.mkdir()

        # Create an approved file (simulate approval)
        approved_file = approved_dir / "odoo-create-res.partner-test123.md"
        approved_file.write_text("""---
type: odoo_write_draft
model: res.partner
method: create
operation_id: test123
---
# Odoo Create: res.partner

```json
{"name": "Test Partner"}
```
""")

        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)
        client._session.uid = 5
        client._session.authenticated = True

        # Mock successful execution response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 42}
        mock_requests.post.return_value = mock_response

        from agents.gold.models import OdooOperation
        operation = OdooOperation(
            operation_id="test123",
            model="res.partner",
            method="create",
            args=({"name": "Test Partner"},),
        )

        result = client.execute_approved(operation)

        # Check that file was moved to Done
        assert not approved_file.exists()
        done_files = list(done_dir.glob("odoo-create-res.partner-test123.md"))
        assert len(done_files) == 1

        # Check operation status was updated
        assert result.status == "executed"
        assert result.result == 42

    def test_execute_approved_missing_approval_raises(self, tmp_path):
        """Test that execute_approved raises if no approved file exists."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)

        from agents.gold.models import OdooOperation
        operation = OdooOperation(
            operation_id="nonexistent",
            model="res.partner",
            method="create",
            args=({"name": "Test Partner"},),
        )

        with pytest.raises(ApprovalNotFoundError):
            client.execute_approved(operation)


class TestCredentialRedaction:
    """Test that credentials are redacted in logs and payloads."""

    def test_draft_operations_redact_credentials(self, tmp_path):
        """Test that draft operations redact credentials in JSON-RPC payloads."""
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )
        client = OdooRPCClient(config, tmp_path)
        client._session.uid = 5
        client._session.authenticated = True

        values = {"name": "Test Partner"}
        operation = client.draft_create("res.partner", values)

        # Check that the operation payload has redacted API key
        payload = operation.json_rpc_payload
        params = payload["params"]["args"]
        # The API key should be redacted as "***"
        assert params[2] == "***"  # Third argument is the API key