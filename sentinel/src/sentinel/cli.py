"""Command-line interface for Sentinel."""

import signal
import sys
from logging import getLogger

from sentinel.config import load_from_env
from sentinel.filesystem import FileSystemWatcher
from sentinel.logging_config import configure_logging


logger = getLogger(__name__)


def main() -> None:
    """Main entry point for sentinel CLI."""
    try:
        # Load configuration from .env
        config = load_from_env()

        # Configure logging
        configure_logging(
            level=config.log_level,
            log_file=config.log_file,
        )

        logger.info(f"Sentinel starting (v0.1.0)")
        logger.info(f"Watching: {config.watch_directory}")
        logger.info(f"Inbox: {config.vault_inbox_path}")

        # Create and start watcher
        watcher = FileSystemWatcher(config)

        # Handle graceful shutdown on Ctrl+C
        def signal_handler(
            signum: int,
            frame: object,
        ) -> None:
            logger.info("Shutdown signal received (SIGINT)")
            watcher.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        # Start monitoring
        watcher.start()

    except ValueError as e:
        logger.error(f"Configuration error: {e}", exc_info=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
