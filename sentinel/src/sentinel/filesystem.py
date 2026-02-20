"""File system watcher implementation."""

import queue
import threading
import time
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from sentinel.base import BaseWatcher
from sentinel.config import WatcherConfig
from sentinel.sidecar import generate_sidecar


logger = getLogger(__name__)


class EventHandler(FileSystemEventHandler):
    """Watchdog event handler for file detection."""

    def __init__(
        self,
        config: WatcherConfig,
        work_queue: queue.Queue,  # type: ignore
        pending_set: Set[str],
    ) -> None:
        """Initialize event handler.

        Args:
            config: Watcher configuration.
            work_queue: Queue for processing files.
            pending_set: Set of currently pending file paths (dedup).
        """
        self.config = config
        self.work_queue = work_queue
        self.pending_set = pending_set

    def on_created(self, event) -> None:  # type: ignore
        """Handle file creation event."""
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Deduplication: skip if already pending
        if str(path) in self.pending_set:
            logger.debug(f"Skipping duplicate event: {path.name}")
            return

        # Check ignore patterns
        if self._is_ignored(path):
            logger.debug(f"Ignoring file: {path.name}")
            return

        # Check allowed extensions
        if not self._is_allowed(path):
            logger.debug(
                f"Skipping unsupported extension: {path.name}"
            )
            return

        # Add to pending set and queue
        self.pending_set.add(str(path))
        self.work_queue.put(path)
        logger.debug(f"Detected file: {path.name}")

    def _is_ignored(self, path: Path) -> bool:
        """Check if file should be ignored.

        Args:
            path: Path to check.

        Returns:
            True if file should be ignored, False otherwise.
        """
        name = path.name

        # Ignore patterns
        ignore_patterns = [
            ".tmp",
            ".~lock",
            ".crdownload",
            ".part",
        ]

        # Check exact extensions
        for pattern in ignore_patterns:
            if name.endswith(pattern):
                return True

        # Check prefixes
        if name.startswith("."):  # Dot-files
            return True
        if name.startswith("~"):  # Temp files
            return True

        return False

    def _is_allowed(self, path: Path) -> bool:
        """Check if file extension is allowed.

        Args:
            path: Path to check.

        Returns:
            True if extension is allowed, False otherwise.
        """
        allowed = self.config.allowed_extensions.split(",")
        allowed = [ext.strip().lower() for ext in allowed]

        ext = path.suffix.lower()
        return ext in allowed


class FileSystemWatcher(BaseWatcher):
    """File system watcher for vault ingestion."""

    def __init__(self, config: WatcherConfig) -> None:
        """Initialize file system watcher.

        Args:
            config: Watcher configuration.
        """
        self.config = config
        self._running = False
        self._pending_set: Set[str] = set()
        self._work_queue: queue.Queue = queue.Queue()
        self._observer: Optional[Observer] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def start(self) -> None:
        """Start monitoring for new files."""
        logger.info(f"Starting {self.name}")

        try:
            # Validate directories
            self._validate_directories()

            # Start observer
            self._observer = Observer()
            handler = EventHandler(
                self.config,
                self._work_queue,
                self._pending_set,
            )
            self._observer.schedule(
                handler,
                str(self.config.watch_directory),
                recursive=False,
            )
            self._observer.start()
            logger.info(
                f"Observing: {self.config.watch_directory}"
            )

            # Start worker thread
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._process_queue,
                daemon=False,
            )
            self._worker_thread.start()

            self._running = True
            logger.info(f"{self.name} ready")

            # Keep main thread alive
            while self._running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"Start failed: {e}", exc_info=True)
            self.stop()
            raise

    def stop(self) -> None:
        """Stop monitoring."""
        logger.info(f"Stopping {self.name}")

        self._running = False
        self._stop_event.set()

        # Stop observer
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            logger.debug("Observer stopped")

        # Drain queue
        timeout = 5
        start = time.time()
        while not self._work_queue.empty():
            if time.time() - start > timeout:
                logger.warning(
                    f"Queue not emptied within {timeout}s"
                )
                break
            time.sleep(0.1)

        # Wait for worker thread
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            logger.debug("Worker thread stopped")

        logger.info("Shutdown complete")

    def _validate_directories(self) -> None:
        """Validate source and inbox directories."""
        # Check watch directory
        if not self.config.watch_directory.exists():
            try:
                self.config.watch_directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                logger.warning(
                    f"Created watch directory: "
                    f"{self.config.watch_directory}"
                )
            except Exception as e:
                raise ValueError(
                    f"Cannot create watch directory: {e}"
                )

        if not self.config.watch_directory.is_dir():
            raise ValueError(
                f"Not a directory: {self.config.watch_directory}"
            )

        # Check inbox directory (fail-fast)
        if not self.config.vault_inbox_path.exists():
            raise ValueError(
                f"Inbox not found: {self.config.vault_inbox_path}"
            )

        if not self.config.vault_inbox_path.is_dir():
            raise ValueError(
                f"Not a directory: {self.config.vault_inbox_path}"
            )

    def _process_queue(self) -> None:
        """Worker thread: process queued files."""
        logger.debug("Worker thread started")

        while not self._stop_event.is_set():
            try:
                # Wait for file with timeout
                try:
                    path = self._work_queue.get(timeout=1)
                except queue.Empty:
                    continue

                try:
                    # Wait for stability
                    if not self._wait_for_stability(path):
                        logger.warning(
                            f"Stability check failed (timeout): "
                            f"{path.name}"
                        )
                        continue

                    # Move to inbox
                    dest = self._move_to_inbox(path)
                    logger.info(f"Moved: {path.name} → {dest.name}")

                except Exception as e:
                    logger.error(
                        f"Error processing {path.name}: {e}",
                        exc_info=True,
                    )

                finally:
                    # Remove from pending
                    self._pending_set.discard(str(path))

            except Exception as e:
                logger.error(
                    f"Queue processing error: {e}",
                    exc_info=True,
                )

        logger.debug("Worker thread stopping")

    def _wait_for_stability(
        self,
        path: Path,
        timeout: float = 10.0,
    ) -> bool:
        """Wait for file to be fully written.

        Args:
            path: Path to file.
            timeout: Maximum wait time in seconds.

        Returns:
            True if file is stable, False if timeout.
        """
        interval = 1.0
        stable_threshold = int(self.config.stability_seconds)
        stable_count = 0
        last_size = -1
        start = time.time()

        while time.time() - start < timeout:
            try:
                current_size = path.stat().st_size

                if current_size == last_size and last_size >= 0:
                    stable_count += 1
                    if stable_count >= stable_threshold:
                        logger.debug(
                            f"File stable: {path.name} "
                            f"({current_size} bytes)"
                        )
                        return True
                else:
                    stable_count = 0

                last_size = current_size
                time.sleep(interval)

            except FileNotFoundError:
                # File was deleted
                logger.warning(f"File not found: {path.name}")
                return False
            except Exception as e:
                logger.error(
                    f"Stability check error: {e}",
                    exc_info=True,
                )
                return False

        return False

    def _move_to_inbox(self, source: Path) -> Path:
        """Move file to inbox with collision handling and sidecar.

        Args:
            source: Source file path.

        Returns:
            Destination file path.
        """
        dest = self.config.vault_inbox_path / source.name

        # Resolve collision
        dest = self._resolve_collision(dest)

        try:
            source.rename(dest)
            logger.debug(f"File moved: {source} → {dest}")

            # Generate sidecar for non-markdown files
            if dest.suffix.lower() != ".md":
                generate_sidecar(source, dest, self.config)

            return dest
        except Exception as e:
            raise RuntimeError(f"Move failed: {e}")

    def _resolve_collision(self, dest: Path) -> Path:
        """Resolve filename collision by appending timestamp.

        Args:
            dest: Destination path.

        Returns:
            Non-colliding destination path.
        """
        if not dest.exists():
            return dest

        # Collision: append timestamp before extension
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        stem = dest.stem
        suffix = dest.suffix

        new_name = f"{stem}_{timestamp}{suffix}"
        new_dest = dest.parent / new_name

        logger.debug(
            f"Collision resolved: {dest.name} → {new_dest.name}"
        )
        return new_dest

    def on_new_item(self, path: Path) -> None:
        """Handle new item (BaseWatcher interface).

        Args:
            path: Path to new item.
        """
        # Queue is used instead for decoupling
        pass
