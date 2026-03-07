"""Gold Tier Autonomous Agent Package.

This package provides the Gold Tier autonomous agent capabilities including:
- Odoo accounting integration (JSON-RPC)
- Cross-platform social media management
- CEO briefing generation
- Ralph Wiggum autonomous loop
"""

__version__ = "0.1.0"
__author__ = "muhammadhamza718"

from .models import (
    GoldAuditEntry,
    LoopConfig,
    LoopState,
    OdooOperation,
    OdooSession,
)

__all__ = [
    "GoldAuditEntry",
    "LoopConfig",
    "LoopState",
    "OdooOperation",
    "OdooSession",
    "__version__",
    "__author__",
]
