"""Context manager for scoped vault operations with automatic audit logging."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from agents.audit_logger import append_log
from agents.exceptions import VaultStructureError
from agents.validators import validate_vault_structure


@contextmanager
def vault_session(
    vault_root: Path,
    tier: str = "bronze",
) -> Generator[Path, None, None]:
    """Context manager that validates vault structure on entry and logs on exit.

    Usage::

        with vault_session(vault_root, tier="silver") as vault:
            route_file(task, vault)

    Args:
        vault_root: Root directory of the vault.
        tier: Agent tier for audit logging.

    Yields:
        The validated vault root path.

    Raises:
        VaultStructureError: If required directories are missing.
    """
    result = validate_vault_structure(vault_root)
    if not result.valid:
        raise VaultStructureError(
            f"Vault at {vault_root} is invalid: {'; '.join(result.errors)}"
        )

    append_log(vault_root, "session_start", f"Opened {tier} session", tier=tier)
    try:
        yield vault_root
    except Exception as exc:
        append_log(
            vault_root,
            "session_error",
            f"{type(exc).__name__}: {exc}",
            tier=tier,
        )
        raise
    finally:
        append_log(vault_root, "session_end", f"Closed {tier} session", tier=tier)
