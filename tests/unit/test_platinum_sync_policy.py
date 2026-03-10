from __future__ import annotations

from pathlib import Path

from agents.platinum.sync_policy import classify_owner, is_forbidden_path


def test_classify_owner_policies():
    assert classify_owner(Path("Dashboard.md")) == "local"
    assert classify_owner(Path("Approved/task.md")) == "local"
    assert classify_owner(Path("Updates/sync/cloud.json")) == "cloud"
    assert classify_owner(Path("In_Progress/cloud/task.md")) == "cloud"
    assert classify_owner(Path("Plans/plan.md")) == "shared"


def test_forbidden_paths_detected():
    assert is_forbidden_path(Path(".env"))
    assert is_forbidden_path(Path("secrets/token.key"))
    assert is_forbidden_path(Path("certs/auth.pfx"))
