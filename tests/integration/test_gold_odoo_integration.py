"""Integration tests for Gold Tier Odoo integration."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agents.constants import APPROVED_DIR, DONE_DIR, PENDING_APPROVAL_DIR
from agents.exceptions import ApprovalNotFoundError
from agents.gold.odoo_rpc_client import OdooConfig, OdooRPCClient


class TestGoldOdooIntegration:
    """Test the full lifecycle of Odoo integration."""

    def test_full_odoo_lifecycle_with_mock_server(self, tmp_path):
        """Test full lifecycle: authenticate → search_read → draft_create → approve → execute_approved."""
        # Setup vault directories
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        pending_dir.mkdir()
        approved_dir = tmp_path / APPROVED_DIR
        approved_dir.mkdir()
        done_dir = tmp_path / DONE_DIR
        done_dir.mkdir()

        # Create config
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )

        # Create client
        client = OdooRPCClient(config, tmp_path)

        # Mock all Odoo API calls
        with patch('agents.gold.odoo_rpc_client.requests') as mock_requests:
            # Mock authentication
            auth_response = Mock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"result": 5}  # UID = 5
            mock_requests.post.return_value = auth_response

            # Authenticate
            session = client.authenticate()
            assert session.authenticated
            assert session.uid == 5

            # Mock search_read response
            search_response = Mock()
            search_response.status_code = 200
            search_response.json.return_value = {"result": [{"id": 1, "name": "Existing Partner"}]}
            mock_requests.post.return_value = search_response

            # Perform search_read
            partners = client.search_read("res.partner", [], ["name"])
            assert len(partners) == 1
            assert partners[0]["name"] == "Existing Partner"

            # Mock draft_create response for JSON-RPC payload
            create_response = Mock()
            create_response.status_code = 200
            create_response.json.return_value = {"result": 42}
            mock_requests.post.return_value = create_response

            # Draft a create operation
            values = {"name": "New Partner", "email": "new@example.com"}
            operation = client.draft_create("res.partner", values, "Creating new partner")

            # Verify approval file was created
            approval_files = list(pending_dir.glob("odoo-create-res.partner-*.md"))
            assert len(approval_files) == 1

            # Simulate human approval by moving file to Approved
            approval_file = approval_files[0]
            approved_file = approved_dir / approval_file.name
            approval_file.rename(approved_file)

            # Now execute the approved operation
            result = client.execute_approved(operation)

            # Verify execution
            assert result.status == "executed"
            assert result.result == 42

            # Verify file was moved to Done
            done_files = list(done_dir.glob("odoo-create-res.partner-*.md"))
            assert len(done_files) == 1

    def test_odoo_write_operation_lifecycle(self, tmp_path):
        """Test the full lifecycle for a write operation."""
        # Setup vault directories
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        pending_dir.mkdir()
        approved_dir = tmp_path / APPROVED_DIR
        approved_dir.mkdir()
        done_dir = tmp_path / DONE_DIR
        done_dir.mkdir()

        # Create config
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )

        client = OdooRPCClient(config, tmp_path)

        # Mock authentication
        with patch('agents.gold.odoo_rpc_client.requests') as mock_requests:
            auth_response = Mock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"result": 5}
            mock_requests.post.return_value = auth_response

            client.authenticate()  # Set up session

            # Mock write response
            write_response = Mock()
            write_response.status_code = 200
            write_response.json.return_value = {"result": True}
            mock_requests.post.return_value = write_response

            # Draft a write operation
            values = {"name": "Updated Name"}
            operation = client.draft_write("res.partner", [1], values, "Updating partner name")

            # Verify approval file was created
            approval_files = list(pending_dir.glob("odoo-write-res.partner-*.md"))
            assert len(approval_files) == 1

            # Simulate approval
            approval_file = approval_files[0]
            approved_file = approved_dir / approval_file.name
            approval_file.rename(approved_file)

            # Execute approved operation
            result = client.execute_approved(operation)

            # Verify execution
            assert result.status == "executed"
            assert result.result is True

    def test_approve_nonexistent_operation_raises(self, tmp_path):
        """Test that attempting to execute a non-existent approved operation raises an error."""
        # Setup vault directories
        approved_dir = tmp_path / APPROVED_DIR
        approved_dir.mkdir()

        # Create config and client
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )

        client = OdooRPCClient(config, tmp_path)

        # Create an operation that doesn't have a corresponding approved file
        from agents.gold.models import OdooOperation
        operation = OdooOperation(
            operation_id="nonexistent",
            model="res.partner",
            method="create",
            args=({"name": "Test Partner"},),
        )

        # Should raise ApprovalNotFoundError
        with pytest.raises(ApprovalNotFoundError):
            client.execute_approved(operation)

    def test_odoo_read_operations_dont_require_approval(self, tmp_path):
        """Test that read operations can be performed without approval."""
        # Create config and client
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="test-key"
        )

        client = OdooRPCClient(config, tmp_path)

        # Mock authentication and read response
        with patch('agents.gold.odoo_rpc_client.requests') as mock_requests:
            auth_response = Mock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"result": 5}
            mock_requests.post.return_value = auth_response

            client.authenticate()  # Set up session

            # Mock read response
            read_response = Mock()
            read_response.status_code = 200
            read_response.json.return_value = {"result": [{"id": 1, "name": "Partner"}]}
            mock_requests.post.return_value = read_response

            # Perform read operation (should NOT create approval file)
            result = client.read("res.partner", [1], ["name"])

            assert len(result) == 1
            assert result[0]["name"] == "Partner"

            # Verify no approval file was created
            pending_dir = tmp_path / PENDING_APPROVAL_DIR
            approval_files = list(pending_dir.glob("*.md")) if pending_dir.exists() else []
            assert len(approval_files) == 0

    def test_credential_redaction_in_draft_operations(self, tmp_path):
        """Test that API credentials are properly redacted in draft operation payloads."""
        # Setup vault directories
        pending_dir = tmp_path / PENDING_APPROVAL_DIR
        pending_dir.mkdir()

        # Create config and client
        config = OdooConfig(
            url="https://test-odoo.com",
            database="test_db",
            username="admin",
            api_key="super-secret-api-key"
        )

        client = OdooRPCClient(config, tmp_path)
        client._session.uid = 5
        client._session.authenticated = True

        # Draft an operation
        values = {"name": "Test Partner"}
        operation = client.draft_create("res.partner", values, "Creating test partner")

        # Check that the operation's JSON-RPC payload has redacted credentials
        payload = operation.json_rpc_payload
        params_args = payload["params"]["args"]

        # The API key (3rd parameter) should be redacted
        assert params_args[2] == "***"

        # Verify the approval file also doesn't contain the real API key
        approval_files = list(pending_dir.glob("odoo-create-res.partner-*.md"))
        assert len(approval_files) == 1

        file_content = approval_files[0].read_text()
        # The real API key should not appear in the file content
        assert "super-secret-api-key" not in file_content