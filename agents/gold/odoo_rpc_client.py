"""Odoo 19+ JSON-RPC integration client.

All READ operations are autonomous.  All WRITE operations are drafted
to ``/Pending_Approval/`` and only executed after human approval
(Constitution XI).  Credentials are loaded from ``.env`` and never
persisted to the vault.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agents.constants import (
    APPROVED_DIR,
    DONE_DIR,
    PENDING_APPROVAL_DIR,
    TIER_GOLD,
)
from agents.exceptions import (
    ApprovalNotFoundError,
    ConfigurationError,
    OdooAuthError,
    OdooError,
    LogicAPIError,
    TransientAPIError,
)
from agents.gold.audit_gold import append_gold_log
from agents.gold.models import OdooConfig, OdooOperation, OdooSession
from agents.utils import ensure_dir, utcnow_iso

# Optional: import requests at call-time to keep module importable
# even when `requests` is not installed (for testing / type-checking).
try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


def load_odoo_config() -> OdooConfig:
    """Load Odoo connection settings from environment variables.

    Raises:
        ConfigurationError: If required variables are missing.
    """
    url = os.getenv("ODOO_URL", "")
    database = os.getenv("ODOO_DB", "")
    username = os.getenv("ODOO_USERNAME", "")
    api_key = os.getenv("ODOO_API_KEY", "")

    missing = [
        name
        for name, val in [
            ("ODOO_URL", url),
            ("ODOO_DB", database),
            ("ODOO_USERNAME", username),
            ("ODOO_API_KEY", api_key),
        ]
        if not val
    ]
    if missing:
        raise ConfigurationError(
            f"Missing Odoo environment variables: {', '.join(missing)}"
        )

    return OdooConfig(
        url=url.rstrip("/"),
        database=database,
        username=username,
        api_key=api_key,
    )


def _jsonrpc_payload(
    service: str, method: str, args: list
) -> dict:
    """Build a JSON-RPC 2.0 request payload."""
    return {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": service,
            "method": method,
            "args": args,
        },
    }


class OdooRPCClient:
    """JSON-RPC client for Odoo 19+ Community Edition."""

    def __init__(
        self,
        config: OdooConfig,
        vault_root: Path,
        executor: object | None = None,
    ) -> None:
        self.config = config
        self.vault_root = vault_root
        self._session = OdooSession(
            url=config.url, database=config.database
        )
        self._executor = executor  # ResilientExecutor, if wired

    # ------------------------------------------------------------------
    # Low-level RPC
    # ------------------------------------------------------------------

    def _call(self, service: str, method: str, args: list) -> object:
        """Make a JSON-RPC call to Odoo.

        Raises:
            OdooError: On any RPC failure.
            TransientAPIError: On 5xx / timeout.
            LogicAPIError: On 4xx.
        """
        if requests is None:
            raise OdooError("The 'requests' package is required for Odoo integration")

        payload = _jsonrpc_payload(service, method, args)
        url = f"{self.config.url}/jsonrpc"

        try:
            resp = requests.post(url, json=payload, timeout=30)
        except requests.ConnectionError as exc:
            raise TransientAPIError(f"Connection to Odoo failed: {exc}") from exc
        except requests.Timeout as exc:
            raise TransientAPIError("Odoo request timed out") from exc

        if resp.status_code >= 500:
            raise TransientAPIError(
                f"Odoo server error: HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        if resp.status_code in {400, 401, 403, 422}:
            raise LogicAPIError(
                f"Odoo client error: HTTP {resp.status_code}",
                status_code=resp.status_code,
            )

        data = resp.json()
        if "error" in data:
            msg = data["error"].get("message", str(data["error"]))
            raise OdooError(f"Odoo RPC error: {msg}")

        return data.get("result")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> OdooSession:
        """Authenticate to Odoo and return an ``OdooSession``.

        Raises:
            OdooAuthError: If authentication fails.
        """
        result = self._call(
            "common",
            "authenticate",
            [
                self.config.database,
                self.config.username,
                self.config.api_key,
                {},
            ],
        )

        if not result or (isinstance(result, (int, float)) and result <= 0):
            raise OdooAuthError("Invalid Odoo credentials")

        uid = int(result)  # type: ignore[arg-type]
        self._session = OdooSession(
            url=self.config.url,
            database=self.config.database,
            uid=uid,
            authenticated=True,
            last_call=utcnow_iso(),
        )

        append_gold_log(
            self.vault_root,
            action="odoo_read",
            details=f"Authenticated as uid={uid}",
            rationale="Odoo session initialization",
        )

        return self._session

    # ------------------------------------------------------------------
    # Autonomous READ operations
    # ------------------------------------------------------------------

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list,
        limit: int = 100,
    ) -> list[dict]:
        """Execute ``search_read`` on an Odoo model (autonomous).

        Returns:
            List of record dicts.
        """
        result = self._call(
            "object",
            "execute_kw",
            [
                self.config.database,
                self._session.uid,
                self.config.api_key,
                model,
                "search_read",
                [domain],
                {"fields": fields, "limit": limit},
            ],
        )
        self._session.last_call = utcnow_iso()
        return result if isinstance(result, list) else []

    def read(
        self,
        model: str,
        ids: list[int],
        fields: list,
    ) -> list[dict]:
        """Read specific records by ID (autonomous)."""
        result = self._call(
            "object",
            "execute_kw",
            [
                self.config.database,
                self._session.uid,
                self.config.api_key,
                model,
                "read",
                [ids],
                {"fields": fields},
            ],
        )
        self._session.last_call = utcnow_iso()
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # WRITE operations — draft to /Pending_Approval/
    # ------------------------------------------------------------------

    def draft_create(
        self,
        model: str,
        values: dict,
        rationale: str = "",
    ) -> OdooOperation:
        """Draft a ``create`` operation to ``/Pending_Approval/``.

        The operation is NOT executed against Odoo until approved.
        """
        op_id = str(uuid.uuid4())[:8]
        payload = _jsonrpc_payload(
            "object",
            "execute_kw",
            [
                self.config.database,
                self._session.uid,
                "***",  # redacted
                model,
                "create",
                [values],
                {},
            ],
        )

        op = OdooOperation(
            operation_id=op_id,
            model=model,
            method="create",
            args=(values,),
            is_write=True,
            requires_approval=True,
            status="pending",
            json_rpc_payload=payload,
        )

        # Write approval file
        pending_dir = ensure_dir(self.vault_root / PENDING_APPROVAL_DIR)
        filename = f"odoo-create-{model}-{op_id}.md"
        content = (
            "---\n"
            f"type: odoo_write_draft\n"
            f"model: {model}\n"
            f"method: create\n"
            f"operation_id: {op_id}\n"
            f"rationale: {rationale}\n"
            f"risk_level: Medium\n"
            "---\n\n"
            f"# Odoo Create: {model}\n\n"
            f"```json\n{json.dumps(values, indent=2)}\n```\n"
        )
        (pending_dir / filename).write_text(content, encoding="utf-8")

        append_gold_log(
            self.vault_root,
            action="odoo_write_draft",
            source_file=f"Pending_Approval/{filename}",
            details=f"Draft create {model}",
            rationale=rationale or f"Draft Odoo create: {model}",
        )

        return op

    def draft_write(
        self,
        model: str,
        ids: list[int],
        values: dict,
        rationale: str = "",
    ) -> OdooOperation:
        """Draft a ``write`` (update) operation to ``/Pending_Approval/``."""
        op_id = str(uuid.uuid4())[:8]
        payload = _jsonrpc_payload(
            "object",
            "execute_kw",
            [
                self.config.database,
                self._session.uid,
                "***",
                model,
                "write",
                [ids, values],
                {},
            ],
        )

        op = OdooOperation(
            operation_id=op_id,
            model=model,
            method="write",
            args=(ids, values),
            is_write=True,
            requires_approval=True,
            status="pending",
            json_rpc_payload=payload,
        )

        pending_dir = ensure_dir(self.vault_root / PENDING_APPROVAL_DIR)
        filename = f"odoo-write-{model}-{op_id}.md"
        content = (
            "---\n"
            f"type: odoo_write_draft\n"
            f"model: {model}\n"
            f"method: write\n"
            f"operation_id: {op_id}\n"
            f"rationale: {rationale}\n"
            "---\n\n"
            f"# Odoo Write: {model} (IDs: {ids})\n\n"
            f"```json\n{json.dumps(values, indent=2)}\n```\n"
        )
        (pending_dir / filename).write_text(content, encoding="utf-8")

        append_gold_log(
            self.vault_root,
            action="odoo_write_draft",
            source_file=f"Pending_Approval/{filename}",
            details=f"Draft write {model} ids={ids}",
            rationale=rationale or f"Draft Odoo write: {model}",
        )

        return op

    def execute_approved(
        self,
        operation: OdooOperation,
    ) -> OdooOperation:
        """Execute a previously approved Odoo write operation.

        The corresponding file MUST exist in ``/Approved/``.

        Raises:
            ApprovalNotFoundError: If the file is not in ``/Approved/``.
        """
        approved_dir = self.vault_root / APPROVED_DIR
        pattern = f"odoo-*-{operation.model}-{operation.operation_id}.md"
        matches = list(approved_dir.glob(pattern))

        if not matches:
            raise ApprovalNotFoundError(
                f"No approved file found for operation {operation.operation_id}"
            )

        # Execute the actual RPC call
        result = self._call(
            "object",
            "execute_kw",
            [
                self.config.database,
                self._session.uid,
                self.config.api_key,
                operation.model,
                operation.method,
                list(operation.args),
                operation.kwargs,
            ],
        )

        # Move approval file to Done
        done_dir = ensure_dir(self.vault_root / DONE_DIR)
        for match in matches:
            match.rename(done_dir / match.name)

        append_gold_log(
            self.vault_root,
            action="odoo_read",  # executed write
            source_file=f"Done/{matches[0].name}",
            details=f"Executed approved {operation.method} on {operation.model}",
            rationale=f"Approved operation {operation.operation_id}",
        )

        return OdooOperation(
            operation_id=operation.operation_id,
            model=operation.model,
            method=operation.method,
            args=operation.args,
            kwargs=operation.kwargs,
            is_write=operation.is_write,
            requires_approval=False,
            status="executed",
            result=result,
            json_rpc_payload=operation.json_rpc_payload,
        )
