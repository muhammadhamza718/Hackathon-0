"""Configuration management for Sentinel watcher."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv


@dataclass
class WatcherConfig:
    """Configuration for file system watcher.

    Attributes:
        watch_directory: Path to monitor for new files.
        vault_inbox_path: Obsidian Vault Inbox path.
        stability_seconds: Seconds a file must be stable before processing.
        allowed_extensions: Comma-separated allowed file extensions.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to log file (outside vault).
    """

    watch_directory: Path
    vault_inbox_path: Path
    stability_seconds: float = 2.0
    allowed_extensions: str = ".md,.txt,.pdf,.jpg,.jpeg,.png"
    log_level: str = "INFO"
    log_file: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate and normalize configuration."""
        # Convert to Path if strings
        if isinstance(self.watch_directory, str):
            self.watch_directory = Path(self.watch_directory)
        if isinstance(self.vault_inbox_path, str):
            self.vault_inbox_path = Path(self.vault_inbox_path)

        # Validate required paths
        if not self.watch_directory or str(self.watch_directory) == ".":
            raise ValueError("WATCH_DIRECTORY is required")
        if not self.vault_inbox_path or str(self.vault_inbox_path) == ".":
            raise ValueError("VAULT_INBOX_PATH is required")

        # Validate stability seconds
        if self.stability_seconds < 0.5:
            raise ValueError("STABILITY_SECONDS must be >= 0.5")

        # Normalize log level
        self.log_level = self.log_level.upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")


def load_from_env() -> WatcherConfig:
    """Load configuration from .env file.

    Returns:
        WatcherConfig instance populated from environment variables.

    Raises:
        ValueError: If required variables are missing or invalid.
    """
    load_dotenv()

    watch_dir = os.getenv("WATCH_DIRECTORY")
    vault_inbox = os.getenv("VAULT_INBOX_PATH")

    if not watch_dir:
        raise ValueError("WATCH_DIRECTORY environment variable is required")
    if not vault_inbox:
        raise ValueError("VAULT_INBOX_PATH environment variable is required")

    return WatcherConfig(
        watch_directory=Path(watch_dir),
        vault_inbox_path=Path(vault_inbox),
        stability_seconds=float(os.getenv("STABILITY_SECONDS", "2.0")),
        allowed_extensions=os.getenv(
            "ALLOWED_EXTENSIONS",
            ".md,.txt,.pdf,.jpg,.jpeg,.png"
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE"),
    )
