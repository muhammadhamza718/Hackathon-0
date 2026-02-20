# Feature Specification: Sentinel File System Watcher

**Feature Branch**: `002-sentinel-watcher`
**Created**: 2026-02-20
**Status**: Draft
**Input**: User description: "Design the first Sentinel (Watcher) script for the Personal AI Employee (Bronze Tier). An external Python script that monitors a Source directory and automatically moves work items into the Obsidian Vault's /Inbox/ folder."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic File Ingestion from Drop Folder (Priority: P1)

As a Digital FTE operator, I want new files placed in my designated "drop folder" on my desktop to be automatically detected and moved into the Obsidian Vault's `/Inbox/` folder, so that I don't have to manually copy files into the vault and can simply drop work items into a convenient location.

**Why this priority**: This is the core value proposition of the sentinel — the fundamental perception layer that feeds work into the vault. Without this, the Digital FTE has no way to receive external inputs automatically.

**Independent Test**: Can be fully tested by starting the watcher, dropping a `.md` file into the source directory, and verifying it appears in the vault's `/Inbox/` within 5 seconds.

**Acceptance Scenarios**:

1. **Given** the sentinel is running and monitoring an empty source directory, **When** a user saves a new `.md` file into the source directory, **Then** the file is moved to the vault's `/Inbox/` folder within 5 seconds and removed from the source directory.
2. **Given** the sentinel is running, **When** a user saves a `.txt` file into the source directory, **Then** the `.txt` file is moved to `/Inbox/` within 5 seconds.
3. **Given** the sentinel is running, **When** multiple files are dropped into the source directory simultaneously, **Then** all files are individually detected and moved to `/Inbox/`.

---

### User Story 2 - Sidecar Generation for Non-Markdown Files (Priority: P2)

As a Digital FTE operator, I want the sentinel to generate a companion `.md` sidecar file for non-markdown files (e.g., `.pdf`, `.jpg`), so that the Claude Code agent can "see" and triage these files by reading their metadata without needing to parse binary formats.

**Why this priority**: The agent operates on markdown. Without sidecar files, PDFs and images would sit in `/Inbox/` invisible to the triage process.

**Independent Test**: Can be tested by dropping a `.pdf` file into the source directory and verifying both the original file and a companion `.md` file appear in `/Inbox/`.

**Acceptance Scenarios**:

1. **Given** the sentinel is running, **When** a user drops a `.pdf` file named `invoice-march.pdf` into the source directory, **Then** both `invoice-march.pdf` and `invoice-march.pdf.md` are moved/created in `/Inbox/`, where the sidecar contains the original filename, source path, file size, and ingestion timestamp.
2. **Given** the sentinel is running, **When** a user drops a `.jpg` image into the source directory, **Then** a sidecar `.md` file is generated alongside the original image in `/Inbox/`.
3. **Given** the sentinel is running, **When** a user drops a `.md` file into the source directory, **Then** no sidecar is generated (markdown files are self-describing).

---

### User Story 3 - Robust Error Handling and Ignored Files (Priority: P3)

As a Digital FTE operator, I want the sentinel to gracefully handle errors (missing directories, permission issues) and ignore temporary/system files, so that the watcher runs reliably without crashing or polluting my inbox with junk.

**Why this priority**: Robustness is essential for a background process that runs unattended. Without it, the sentinel would crash on the first error and stop feeding the vault.

**Independent Test**: Can be tested by starting the watcher with a non-existent source directory and verifying it logs an error and retries, or by dropping a `.tmp` file and verifying it is ignored.

**Acceptance Scenarios**:

1. **Given** the sentinel is started with a source directory that does not exist, **When** the sentinel initializes, **Then** it logs an error message and either creates the directory or exits gracefully with a clear error.
2. **Given** the sentinel is running, **When** a `.tmp` file or `.~lock` file appears in the source directory, **Then** the sentinel ignores it (no move, no sidecar, no error).
3. **Given** the sentinel is running and the vault's `/Inbox/` directory becomes temporarily inaccessible, **When** a new file is detected, **Then** the sentinel logs the error and retries on the next detection cycle rather than crashing.

---

### User Story 4 - Extensible Watcher Base Class (Priority: P4)

As a developer building the Silver Tier, I want a `BaseWatcher` abstract class that defines the common interface for all watchers, so that I can later implement Gmail and WhatsApp watchers that plug into the same ingestion pipeline.

**Why this priority**: While not needed for Bronze Tier functionality, this architectural foundation prevents costly refactoring when adding new input sources in Silver Tier.

**Independent Test**: Can be tested by verifying the `BaseWatcher` class defines the required abstract methods and that the file system watcher correctly inherits from it.

**Acceptance Scenarios**:

1. **Given** the `BaseWatcher` abstract class exists, **When** a developer inspects it, **Then** it defines abstract methods for `start()`, `stop()`, and `on_new_item()` at minimum.
2. **Given** the file system watcher inherits from `BaseWatcher`, **When** the file system watcher is instantiated, **Then** it correctly implements all abstract methods from the base class.

---

### Edge Cases

- What happens when a file with the same name already exists in `/Inbox/`? The system appends a timestamp suffix to avoid overwriting (e.g., `report.md` becomes `report_20260220T120000.md`).
- What happens when a very large file (>100 MB) is being written and the watcher detects it mid-write? The system uses a stability check (file size unchanged for 2 seconds) before moving, ensuring atomic transfer of fully-written files only.
- What happens when the source directory contains subdirectories? Subdirectories are ignored; only top-level files are monitored.
- What happens when a file has an unsupported extension (e.g., `.exe`, `.dll`)? The system only processes allowed extensions (`.md`, `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.png`). All other extensions are ignored and logged as skipped.
- What happens if the sentinel process is interrupted mid-move? On next startup, the sentinel checks both source and inbox for partial transfers and completes or cleans up as needed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST continuously monitor a single configured local directory (the "source" or "drop folder") for new files.
- **FR-002**: System MUST detect new files with the following extensions: `.md`, `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.png`.
- **FR-003**: System MUST perform a stability check before processing — a file is considered ready only after its size remains unchanged for at least 2 seconds.
- **FR-004**: System MUST move ready files from the source directory to the Obsidian Vault's `/Inbox/` folder.
- **FR-005**: System MUST generate a sidecar `.md` file for every non-markdown file moved to `/Inbox/`. The sidecar MUST contain: original filename, source path, file size in bytes, and ingestion timestamp (ISO-8601).
- **FR-006**: System MUST NOT generate a sidecar for `.md` files (they are self-describing).
- **FR-007**: System MUST ignore temporary and system files: `.tmp`, `.~lock`, files starting with `.` (dot-files), and files starting with `~`.
- **FR-008**: System MUST handle filename collisions in `/Inbox/` by appending a timestamp suffix to the filename (before the extension).
- **FR-009**: System MUST log all file operations (detected, moved, skipped, error) to the console with timestamps.
- **FR-010**: System MUST NOT call any external APIs, cloud services, or network endpoints (Bronze Law Principle I: Local-First Privacy).
- **FR-011**: System MUST NOT perform any triage, classification, or prioritization of files — it is a "dumb feeder" only.
- **FR-012**: System MUST be configurable via a local configuration file or command-line arguments for: source directory path, vault inbox path, and allowed file extensions.
- **FR-013**: System MUST define a `BaseWatcher` abstract class with at minimum `start()`, `stop()`, and `on_new_item()` abstract methods.
- **FR-014**: The file system watcher MUST inherit from `BaseWatcher` and implement all abstract methods.
- **FR-015**: System MUST only monitor top-level files in the source directory (no recursive subdirectory monitoring).
- **FR-016**: System MUST gracefully handle missing source or inbox directories at startup by logging clear error messages.
- **FR-017**: System MUST handle I/O errors during file move without crashing — log the error and continue monitoring.

### Key Entities

- **SourceDirectory**: The local file system directory being monitored for new files. Configured by the user (e.g., `C:/Users/User/Desktop/AI_Employee_Drop/`).
- **InboxDirectory**: The Obsidian Vault's `/Inbox/` folder where files are delivered. Target destination for all ingested items.
- **WatchedFile**: A file detected in the source directory. Key attributes: name, extension, size, last-modified time, stability status (ready/not-ready).
- **SidecarFile**: A companion `.md` file generated for non-markdown files. Contains metadata: original filename, source path, file size, ingestion timestamp.
- **BaseWatcher**: Abstract base defining the watcher interface. All concrete watchers (FileSystem, Gmail, WhatsApp) inherit from it.
- **FileSystemWatcher**: Concrete watcher implementation for local directory monitoring. The only watcher implemented at Bronze Tier.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Files dropped into the source directory appear in the vault's `/Inbox/` within 5 seconds of being fully written.
- **SC-002**: 100% of non-markdown files have a corresponding sidecar `.md` file generated in `/Inbox/`.
- **SC-003**: Zero temporary files (`.tmp`, `.~lock`, dot-files) are ever moved to `/Inbox/`.
- **SC-004**: The sentinel runs continuously for 1 hour without crashing, even when encountering permission errors or missing directories.
- **SC-005**: Zero external network calls are made during sentinel operation (verifiable via network traffic audit or code grep).
- **SC-006**: A developer can create a new watcher type (e.g., `GmailWatcher`) by inheriting from `BaseWatcher` and implementing 3 methods without modifying existing code.
- **SC-007**: All file operations are logged to the console with ISO-8601 timestamps and clear action descriptions.
- **SC-008**: Files mid-write (actively being copied) are not moved until fully written (stability check passes).

## Assumptions

- The user has Python 3.10+ installed on their system.
- The `watchdog` library is an acceptable third-party dependency (well-established, local-only, no network calls).
- The source directory and vault inbox directory are on the same local file system (no network drives at Bronze Tier).
- The sentinel runs as a foreground console process (no daemon/service mode required at Bronze Tier).
- Only one instance of the sentinel runs at a time (no multi-instance coordination needed).
- The Obsidian Vault already exists and has been initialized with the `/Inbox/` folder before the sentinel starts.
