"""Gold Safety Gate with Human-In-The-Loop (HITL) approval.

Implements Constitution XII (Safety Gate) requiring HITL approval for
high-risk operations before execution.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SafetyConfig
from .exceptions import HITLTimeoutError


class ApprovalRequest:
    """Represents a pending approval request."""

    def __init__(
        self,
        request_id: str,
        action: str,
        rationale: str,
        payload: dict[str, Any],
        created_at: str | None = None,
    ):
        self.request_id = request_id
        self.action = action
        self.rationale = rationale
        self.payload = payload
        self.created_at = created_at or datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        self.status = "pending"
        self.decision: str | None = None
        self.decided_at: str | None = None
        self.decider: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "request_id": self.request_id,
            "action": self.action,
            "rationale": self.rationale,
            "payload": self.payload,
            "created_at": self.created_at,
            "status": self.status,
            "decision": self.decision,
            "decided_at": self.decided_at,
            "decider": self.decider,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRequest":
        """Deserialize from dictionary."""
        request = cls(
            request_id=data["request_id"],
            action=data["action"],
            rationale=data["rationale"],
            payload=data["payload"],
            created_at=data.get("created_at"),
        )
        request.status = data.get("status", "pending")
        request.decision = data.get("decision")
        request.decided_at = data.get("decided_at")
        request.decider = data.get("decider")
        return request


class GoldSafetyGate:
    """HITL safety gate for Gold Tier operations.

    All high-risk operations must be approved through this gate before
    execution. Approval requests are stored in the Pending_Approval/
    directory and must be manually approved or rejected.
    """

    def __init__(
        self,
        approval_dir: str = "Pending_Approval",
        config: SafetyConfig | None = None,
    ):
        """Initialize the safety gate.

        Args:
            approval_dir: Directory for storing approval requests.
            config: Safety configuration.
        """
        self.approval_dir = Path(approval_dir)
        self.approval_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or SafetyConfig.from_env()

    def _get_request_path(self, request_id: str) -> Path:
        """Get the file path for an approval request."""
        return self.approval_dir / f"{request_id}.json"

    def request_approval(
        self,
        action: str,
        rationale: str,
        payload: dict[str, Any],
        request_id: str | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request.

        Args:
            action: The action requiring approval.
            rationale: Explanation for why this action is needed.
            payload: The action payload to be executed upon approval.
            request_id: Optional custom request ID.

        Returns:
            The created approval request.
        """
        if request_id is None:
            request_id = f"req_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

        request = ApprovalRequest(
            request_id=request_id,
            action=action,
            rationale=rationale,
            payload=payload,
        )

        # Write approval request to file
        request_path = self._get_request_path(request_id)
        with open(request_path, "w", encoding="utf-8") as f:
            json.dump(request.to_dict(), f, indent=2)

        return request

    def get_pending_requests(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        requests = []
        for path in self.approval_dir.glob("req_*.json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("status") == "pending":
                    requests.append(ApprovalRequest.from_dict(data))
        return requests

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        """Get a specific approval request by ID."""
        request_path = self._get_request_path(request_id)
        if not request_path.exists():
            return None

        with open(request_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ApprovalRequest.from_dict(data)

    def approve(
        self, request_id: str, decider: str = "human"
    ) -> ApprovalRequest:
        """Approve a pending request.

        Args:
            request_id: The request ID to approve.
            decider: Identifier of who approved (default: "human").

        Returns:
            The updated approval request.

        Raises:
            KeyError: If request not found.
        """
        request = self.get_request(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")

        request.status = "approved"
        request.decision = "approved"
        request.decided_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        request.decider = decider

        # Update file
        request_path = self._get_request_path(request_id)
        with open(request_path, "w", encoding="utf-8") as f:
            json.dump(request.to_dict(), f, indent=2)

        return request

    def reject(
        self, request_id: str, decider: str = "human", reason: str = ""
    ) -> ApprovalRequest:
        """Reject a pending request.

        Args:
            request_id: The request ID to reject.
            decider: Identifier of who rejected (default: "human").
            reason: Optional rejection reason.

        Returns:
            The updated approval request.

        Raises:
            KeyError: If request not found.
        """
        request = self.get_request(request_id)
        if request is None:
            raise KeyError(f"Request {request_id} not found")

        request.status = "rejected"
        request.decision = "rejected"
        request.decided_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        request.decider = decider
        if reason:
            request.payload["rejection_reason"] = reason

        # Update file
        request_path = self._get_request_path(request_id)
        with open(request_path, "w", encoding="utf-8") as f:
            json.dump(request.to_dict(), f, indent=2)

        return request

    def is_approved(self, request_id: str) -> bool:
        """Check if a request has been approved."""
        request = self.get_request(request_id)
        return request is not None and request.status == "approved"

    def wait_for_approval(
        self, request_id: str, timeout_seconds: float | None = None
    ) -> ApprovalRequest:
        """Wait for a request to be approved.

        Args:
            request_id: The request ID to wait for.
            timeout_seconds: Optional timeout (uses config default if None).

        Returns:
            The approved approval request.

        Raises:
            HITLTimeoutError: If timeout exceeded.
            KeyError: If request not found.
        """
        timeout = timeout_seconds or self.config.hitl_timeout_seconds
        start_time = datetime.now(timezone.utc)

        while True:
            request = self.get_request(request_id)
            if request is None:
                raise KeyError(f"Request {request_id} not found")

            if request.status == "approved":
                return request
            if request.status == "rejected":
                raise PermissionError(
                    f"Request {request_id} was rejected"
                )

            elapsed = (
                datetime.now(timezone.utc) - start_time
            ).total_seconds()
            if elapsed > timeout:
                raise HITLTimeoutError(
                    f"Approval timeout for request {request_id} after {timeout}s"
                )

            # Sleep before checking again (simplified - would use async in production)
            import time

            time.sleep(1)

    def requires_approval(self, action: str) -> bool:
        """Check if an action requires HITL approval."""
        return action in self.config.approval_required_actions

    def count_pending(self) -> int:
        """Count pending approval requests."""
        return len(self.get_pending_requests())
