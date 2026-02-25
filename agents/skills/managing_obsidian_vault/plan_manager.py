"""
PlanManager: Core module for managing Plan.md files in the Obsidian vault.

Provides functions for creating, loading, parsing, and updating plan files
following the rigid Silver Tier schema defined in references/plan-template.md.

Classes:
    PlanMetadata: YAML frontmatter extracted from Plan.md
    PlanContent: Parsed plan (metadata + sections)
    PlanStep: Represents a single step in the Roadmap

Functions:
    create_plan(): Create new Plan.md from template
    load_plan(): Read and parse existing Plan.md
    find_active_plan(): Scan /Plans/ for incomplete plans (Reconciliation-First)
    validate_schema(): Ensure Plan.md integrity
    update_step(): Mark step complete and append reasoning log entry
    append_reasoning_log(): Add ISO-8601 timestamped log entry
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

# Configure logging with ISO-8601 timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


@dataclass
class PlanMetadata:
    """Represents YAML frontmatter from Plan.md."""
    task_id: str
    source_link: str
    created_date: str
    priority: str
    status: str  # Draft, Active, Blocked, Done
    blocked_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanMetadata":
        """Create PlanMetadata from YAML dict."""
        return cls(
            task_id=data.get("task_id", ""),
            source_link=data.get("source_link", ""),
            created_date=data.get("created_date", ""),
            priority=data.get("priority", "medium"),
            status=data.get("status", "Draft"),
            blocked_reason=data.get("blocked_reason")
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for YAML serialization."""
        return {
            "task_id": self.task_id,
            "source_link": self.source_link,
            "created_date": self.created_date,
            "priority": self.priority,
            "status": self.status,
            "blocked_reason": self.blocked_reason
        }


@dataclass
class PlanStep:
    """Represents a single step in the Roadmap."""
    number: int
    description: str
    completed: bool = False
    hitl_required: bool = False  # Requires human-in-the-loop approval

    def to_markdown(self) -> str:
        """Convert to markdown checkbox format."""
        checkbox = "[x]" if self.completed else "[ ]"
        hitl_marker = "✋ " if self.hitl_required else ""
        return f"- {checkbox} {hitl_marker}{self.description}".rstrip()

    @staticmethod
    def from_markdown(line: str) -> Optional["PlanStep"]:
        """Parse markdown checkbox line to PlanStep."""
        # Match format: "- [ ] description" or "- [x] description"
        # Optional ✋ emoji before description
        match = re.match(r'^\s*-\s+\[([ x])\]\s*(✋\s)?(.+)$', line.strip(), re.IGNORECASE)
        if not match:
            return None

        completed = match.group(1).lower() == 'x'
        hitl_required = match.group(2) is not None
        description = match.group(3)

        return PlanStep(
            number=0,  # Will be set by parent
            description=description,
            completed=completed,
            hitl_required=hitl_required
        )


@dataclass
class PlanContent:
    """Represents complete parsed Plan.md content."""
    metadata: PlanMetadata
    objective: str
    context: str
    steps: List[PlanStep] = field(default_factory=list)
    reasoning_logs: List[str] = field(default_factory=list)

    def is_complete(self) -> bool:
        """Check if all non-HITL steps are completed."""
        return all(step.completed or step.hitl_required for step in self.steps)

    def get_next_incomplete_step(self) -> Optional[PlanStep]:
        """Get first incomplete step (excluding HITL steps)."""
        for step in self.steps:
            if not step.completed and not step.hitl_required:
                return step
        return None

    def has_pending_approval(self) -> bool:
        """Check if plan has HITL steps awaiting approval."""
        return any(step.hitl_required and not step.completed for step in self.steps)


class PlanManager:
    """Manages Plan.md files in the Obsidian vault."""

    def __init__(self, vault_root: Path):
        """
        Initialize PlanManager with vault root directory.

        Args:
            vault_root: Root directory of the Obsidian vault
        """
        self.vault_root = vault_root
        self.plans_dir = vault_root / "Plans"
        self.done_dir = vault_root / "Done" / "Plans"

        logger.info(f"PlanManager initialized with vault_root={vault_root}")

    def create_plan(
        self,
        task_id: str,
        objective: str,
        context: str,
        steps: List[str],
        priority: str = "medium",
        source_link: Optional[str] = None
    ) -> Path:
        """
        Create new Plan.md from template with valid schema.

        Args:
            task_id: Unique plan identifier (e.g., PLAN-2026-001)
            objective: Single-sentence mission statement
            context: Problem statement, dependencies, constraints
            steps: List of step descriptions (can include ✋ prefix for HITL steps)
            priority: high, medium, low
            source_link: Reference to source document (optional)

        Returns:
            Path to created Plan.md file

        Raises:
            ValueError: If task_id or objective invalid
            IOError: If file creation fails
        """
        if not task_id or not objective:
            raise ValueError("task_id and objective are required")

        plan_path = self.plans_dir / f"PLAN-{task_id}.md"

        # Create metadata
        metadata = PlanMetadata(
            task_id=task_id,
            source_link=source_link or "null",
            created_date=self._iso_timestamp(),
            priority=priority,
            status="Draft",
            blocked_reason=None
        )

        # Create steps
        plan_steps: List[PlanStep] = []
        for idx, step_desc in enumerate(steps, 1):
            hitl = step_desc.startswith("✋")
            clean_desc = step_desc.replace("✋", "").strip()
            plan_steps.append(PlanStep(
                number=idx,
                description=clean_desc,
                completed=False,
                hitl_required=hitl
            ))

        # Create content
        plan_content = PlanContent(
            metadata=metadata,
            objective=objective,
            context=context,
            steps=plan_steps,
            reasoning_logs=[
                f"[{self._iso_timestamp()}] Agent: Created plan — Task ID: {task_id}. Objective: {objective}"
            ]
        )

        # Write to file
        self._write_plan_file(plan_path, plan_content)

        logger.info(f"Plan created: {plan_path}")
        return plan_path

    def load_plan(self, plan_id: str) -> PlanContent:
        """
        Read and parse existing Plan.md.

        Args:
            plan_id: Plan identifier (with or without PLAN- prefix)

        Returns:
            Parsed PlanContent object

        Raises:
            FileNotFoundError: If plan file not found
            ValueError: If YAML or markdown structure invalid
        """
        if not plan_id.startswith("PLAN-"):
            plan_id = f"PLAN-{plan_id}"

        plan_path = self.plans_dir / f"{plan_id}.md"

        if not plan_path.exists():
            raise FileNotFoundError(f"Plan not found: {plan_path}")

        content = plan_path.read_text(encoding='utf-8')
        parsed = self._parse_plan_content(content)

        logger.info(f"Plan loaded: {plan_path}")
        return parsed

    def find_active_plan(self) -> Optional[PlanContent]:
        """
        Scan /Plans/ for incomplete plans (Reconciliation-First startup).

        Prioritizes by:
        1. Status: Active > Blocked > Draft
        2. Created date (most recent first)

        Returns:
            Most relevant incomplete PlanContent, or None if no plans found
        """
        if not self.plans_dir.exists():
            logger.info("No plans directory found")
            return None

        incomplete_plans: List[tuple[str, PlanContent]] = []

        for plan_file in self.plans_dir.glob("PLAN-*.md"):
            try:
                plan = self.load_plan(plan_file.stem)
                # Only consider non-Done plans
                if plan.metadata.status != "Done":
                    incomplete_plans.append((plan_file.stem, plan))
            except (ValueError, FileNotFoundError) as e:
                logger.warning(f"Skipping invalid plan {plan_file.stem}: {e}")

        if not incomplete_plans:
            logger.info("No active plans found")
            return None

        # Sort by status priority, then by created_date descending
        status_priority = {"Active": 0, "Blocked": 1, "Draft": 2}
        incomplete_plans.sort(
            key=lambda x: (
                status_priority.get(x[1].metadata.status, 99),
                -self._parse_timestamp(x[1].metadata.created_date).timestamp()
            )
        )

        selected = incomplete_plans[0][1]
        logger.info(f"Active plan found: {selected.metadata.task_id} (status: {selected.metadata.status})")
        return selected

    def validate_schema(self, plan_content: PlanContent) -> bool:
        """
        Ensure Plan.md integrity by validating schema.

        Checks:
        - YAML frontmatter completeness
        - Mandatory sections present
        - Reasoning logs are ISO-8601 timestamped

        Args:
            plan_content: PlanContent to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        # Check metadata completeness
        if not plan_content.metadata.task_id:
            raise ValueError("Missing task_id in frontmatter")
        if not plan_content.metadata.created_date:
            raise ValueError("Missing created_date in frontmatter")

        # Check mandatory sections
        if not plan_content.objective:
            raise ValueError("Missing Objective section")
        if not plan_content.context:
            raise ValueError("Missing Context section")
        if not plan_content.steps:
            raise ValueError("No steps in Roadmap")

        # Validate reasoning logs have ISO-8601 timestamps
        for log_entry in plan_content.reasoning_logs:
            if not re.match(r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]', log_entry):
                raise ValueError(f"Invalid timestamp in reasoning log: {log_entry}")

        logger.info(f"Schema validated for plan {plan_content.metadata.task_id}")
        return True

    def update_step(
        self,
        plan_id: str,
        step_number: int,
        completed: bool = True,
        log_entry: Optional[str] = None
    ) -> Path:
        """
        Mark step complete/incomplete and append reasoning log entry.

        Args:
            plan_id: Plan identifier
            step_number: Step number in Roadmap (1-indexed)
            completed: True to mark complete, False to mark incomplete
            log_entry: Optional reasoning log message (without timestamp)

        Returns:
            Path to updated plan file

        Raises:
            FileNotFoundError: If plan not found
            ValueError: If step number invalid
        """
        plan = self.load_plan(plan_id)

        if step_number < 1 or step_number > len(plan.steps):
            raise ValueError(f"Invalid step number: {step_number}")

        plan.steps[step_number - 1].completed = completed

        if log_entry:
            formatted_log = f"[{self._iso_timestamp()}] Agent: {log_entry}"
            plan.reasoning_logs.append(formatted_log)

        plan_path = self.plans_dir / f"PLAN-{plan.metadata.task_id}.md"
        self._write_plan_file(plan_path, plan)

        logger.info(f"Step {step_number} updated in plan {plan_id}, completed={completed}")
        return plan_path

    def append_reasoning_log(self, plan_id: str, action: str, rationale: str) -> Path:
        """
        Add ISO-8601 timestamped log entry to plan reasoning log.

        Args:
            plan_id: Plan identifier
            action: What was done (past tense)
            rationale: Why it was done

        Returns:
            Path to updated plan file
        """
        plan = self.load_plan(plan_id)

        log_entry = f"[{self._iso_timestamp()}] Agent: {action} — {rationale}"
        plan.reasoning_logs.append(log_entry)

        plan_path = self.plans_dir / f"PLAN-{plan.metadata.task_id}.md"
        self._write_plan_file(plan_path, plan)

        logger.info(f"Reasoning log appended to plan {plan_id}")
        return plan_path

    def archive_plan(self, plan_id: str, status: str = "Done") -> Path:
        """
        Move completed plan to /Done/Plans/ and update status.

        Args:
            plan_id: Plan identifier
            status: Final status (typically "Done")

        Returns:
            Path to archived plan file
        """
        plan = self.load_plan(plan_id)
        plan.metadata.status = status

        source_path = self.plans_dir / f"PLAN-{plan.metadata.task_id}.md"
        dest_path = self.done_dir / f"PLAN-{plan.metadata.task_id}.md"

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_plan_file(dest_path, plan)
        source_path.unlink(missing_ok=True)

        logger.info(f"Plan archived: {plan_id} -> {dest_path}")
        return dest_path

    # ------------------------------------------------------------------
    # T060 — handle_corrupted_plan
    # ------------------------------------------------------------------

    def handle_corrupted_plan(self, plan_path: Path) -> Optional[Path]:
        """
        Handle a corrupted Plan.md file that cannot be parsed.

        Process:
        1. Detect invalid YAML, missing sections, or incomplete file.
        2. Log error to dashboard / logger — DO NOT crash.
        3. Move corrupted file to /Archive/Corrupted/ for human review.
        4. Return path to the quarantined file, or None if move fails.

        Args:
            plan_path: Path to the plan file that failed to parse.

        Returns:
            Path to quarantined file, or None if quarantine also fails.
        """
        corrupted_dir = self.vault_root / "Archive" / "Corrupted"
        corrupted_dir.mkdir(parents=True, exist_ok=True)

        dest_path = corrupted_dir / plan_path.name
        try:
            # Read raw content for diagnostic log
            raw = plan_path.read_text(encoding="utf-8", errors="replace")
            logger.error(
                "Corrupted plan detected: %s — first 200 chars: %r",
                plan_path.name,
                raw[:200],
            )

            # Atomic copy to quarantine, then remove source
            dest_path.write_text(raw, encoding="utf-8")
            plan_path.unlink(missing_ok=True)

            logger.warning(
                "Corrupted plan quarantined: %s -> %s. "
                "Human review required — do NOT auto-delete.",
                plan_path.name,
                dest_path,
            )
            return dest_path

        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to quarantine corrupted plan %s: %s",
                plan_path.name,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # T062 — consolidate_duplicate_plans (enhances detect_duplicate_plan)
    # ------------------------------------------------------------------

    def consolidate_duplicate_plans(
        self,
        primary_plan_id: str,
        duplicate_plan_id: str,
    ) -> Path:
        """
        Merge steps from a duplicate plan into the primary plan and archive
        the duplicate.

        Process:
        1. Load both plans.
        2. Merge unique steps from duplicate into primary via merge_plan_steps().
        3. Append a reasoning log entry recording the consolidation.
        4. Save primary plan.
        5. Move duplicate to /Archive/ with a consolidation note.

        Args:
            primary_plan_id: Plan to keep and merge into.
            duplicate_plan_id: Plan to merge from and then archive.

        Returns:
            Path to the updated primary plan file.

        Raises:
            FileNotFoundError: If either plan cannot be found.
        """
        primary = self.load_plan(primary_plan_id)
        duplicate = self.load_plan(duplicate_plan_id)

        # Collect raw step descriptions from duplicate
        dup_steps = [
            ("✋ " if s.hitl_required else "") + s.description
            for s in duplicate.steps
        ]

        # Merge unique steps into primary
        primary = self.merge_plan_steps(primary, dup_steps)

        # Log the consolidation
        primary.reasoning_logs.append(
            f"[{self._iso_timestamp()}] Agent: Consolidated duplicate plan "
            f"{duplicate.metadata.task_id} into {primary.metadata.task_id} — "
            f"merged {len(dup_steps)} steps; duplicate archived."
        )

        # Save primary
        primary_path = self.plans_dir / f"PLAN-{primary.metadata.task_id}.md"
        self._write_plan_file(primary_path, primary)

        # Archive duplicate to /Archive/
        archive_dir = self.vault_root / "Archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        dup_source = self.plans_dir / f"PLAN-{duplicate.metadata.task_id}.md"
        dup_dest = archive_dir / f"PLAN-{duplicate.metadata.task_id}.md"

        if dup_source.exists():
            dup_raw = dup_source.read_text(encoding="utf-8")
            dup_dest.write_text(dup_raw, encoding="utf-8")
            dup_source.unlink(missing_ok=True)

        logger.info(
            "Duplicate plan %s consolidated into %s; duplicate moved to %s",
            duplicate_plan_id,
            primary_plan_id,
            dup_dest,
        )
        return primary_path

    def detect_duplicate_plan(self, task_id: str, source_link: Optional[str] = None) -> Optional[PlanContent]:
        """
        Detect if a plan already exists for the same task or source.

        Args:
            task_id: Task identifier to check
            source_link: Optional source link to check for duplicates

        Returns:
            Existing PlanContent if duplicate found, None otherwise
        """
        if not self.plans_dir.exists():
            return None

        for plan_file in self.plans_dir.glob("PLAN-*.md"):
            try:
                plan = self.load_plan(plan_file.stem)

                # Check for same task_id
                if plan.metadata.task_id == task_id:
                    logger.warning(f"Duplicate plan detected: task_id {task_id} already exists")
                    return plan

                # Check for same source_link
                if source_link and source_link != "null":
                    if plan.metadata.source_link == source_link:
                        logger.warning(f"Duplicate plan detected: source_link {source_link} already exists")
                        return plan

            except (ValueError, FileNotFoundError) as e:
                logger.debug(f"Skipping invalid plan during duplicate check {plan_file.stem}: {e}")

        return None

    def merge_plan_steps(self, existing_plan: PlanContent, new_steps: List[str]) -> PlanContent:
        """
        Merge new steps into existing plan to avoid duplication.

        Args:
            existing_plan: Existing PlanContent to merge into
            new_steps: List of new steps to add

        Returns:
            Updated PlanContent with merged steps
        """
        # Add new steps that don't already exist
        for step_desc in new_steps:
            clean_desc = step_desc.replace("✋", "").strip()

            # Check if step already exists
            if not any(s.description.lower() == clean_desc.lower() for s in existing_plan.steps):
                hitl = step_desc.startswith("✋")
                new_step = PlanStep(
                    number=len(existing_plan.steps) + 1,
                    description=clean_desc,
                    completed=False,
                    hitl_required=hitl
                )
                existing_plan.steps.append(new_step)

        logger.info(f"Merged {len(new_steps)} steps into plan {existing_plan.metadata.task_id}")
        return existing_plan

    def validate_hitl_completion(
        self,
        plan_id: str,
        step_number: int,
        approval_manager: Optional[object] = None,
    ) -> bool:
        """
        Enforce T044: prevent marking a ✋ step complete without approval proof.

        A step that requires human-in-the-loop (hitl_required=True) MUST have a
        corresponding executed approval file before it can be marked [x].

        Args:
            plan_id: Plan identifier
            step_number: Step number (1-indexed)
            approval_manager: ApprovalManager instance for checking approval files.
                              If None, raises PermissionError unconditionally for
                              HITL steps (safe-fail default).

        Returns:
            True if step may be marked complete

        Raises:
            ValueError: If step_number is out of range
            PermissionError: If step is HITL-required and no approval proof found
        """
        plan = self.load_plan(plan_id)

        if step_number < 1 or step_number > len(plan.steps):
            raise ValueError(f"Invalid step number: {step_number} (plan has {len(plan.steps)} steps)")

        step = plan.steps[step_number - 1]

        if not step.hitl_required:
            # Non-HITL step: no approval check required
            return True

        # HITL step: verify approval exists
        if approval_manager is None:
            raise PermissionError(
                f"Cannot mark HITL step {step_number} complete in plan {plan_id}: "
                f"no ApprovalManager provided. "
                f"Pass an ApprovalManager instance to validate approval proof."
            )

        # Delegate to ApprovalManager.validate_hitl_step_has_approval()
        # This raises PermissionError if no executed approval file is found
        approval_manager.validate_hitl_step_has_approval(
            plan_id=plan.metadata.task_id,
            step_id=step_number,
        )

        logger.info(
            "HITL completion validated for plan %s step %d",
            plan.metadata.task_id, step_number,
        )
        return True

    # Private helper methods

    def _atomic_write(self, path: Path, content: str) -> None:
        """
        Write content to file atomically using temp-file-and-rename pattern.

        Ensures Plan.md files never end up in a corrupted/half-written state.

        Args:
            path: Target file path
            content: Content to write

        Raises:
            IOError: If write or rename fails
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first
        temp_path = path.parent / f".{path.name}.tmp"

        try:
            temp_path.write_text(content, encoding='utf-8')
            # Atomic rename
            temp_path.replace(path)
            logger.debug(f"Atomic write completed: {path}")
        except IOError as e:
            # Clean up temp file if rename failed
            temp_path.unlink(missing_ok=True)
            logger.error(f"Atomic write failed for {path}: {e}")
            raise IOError(f"Failed to write plan file {path}: {e}")

    def _write_plan_file(self, path: Path, plan: PlanContent) -> None:
        """Write PlanContent to markdown file with YAML frontmatter."""
        # Build YAML frontmatter
        yaml_dict = plan.metadata.to_dict()
        yaml_str = yaml.dump(yaml_dict, default_flow_style=False, sort_keys=False)

        # Build markdown content
        lines = [
            "---",
            yaml_str.rstrip(),
            "---",
            "",
            "# Objective",
            "",
            plan.objective,
            "",
            "## Context",
            "",
            plan.context,
            "",
            "## Roadmap",
            ""
        ]

        for step in plan.steps:
            lines.append(step.to_markdown())

        lines.extend([
            "",
            "## Reasoning Logs",
            ""
        ])

        for log_entry in plan.reasoning_logs:
            lines.append(f"- {log_entry}")

        content = "\n".join(lines)
        self._atomic_write(path, content)

    def _parse_plan_content(self, content: str) -> PlanContent:
        """Parse markdown content with YAML frontmatter into PlanContent."""
        # Extract YAML frontmatter
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if not match:
            raise ValueError("Missing YAML frontmatter")

        yaml_content = match.group(1)
        remaining = content[match.end():]

        try:
            yaml_dict = yaml.safe_load(yaml_content)
            metadata = PlanMetadata.from_dict(yaml_dict)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}")

        # Extract sections (use non-greedy for middle content, greedy for logs since it's the final section)
        objective_match = re.search(r'^# Objective\s*\n\n(.*?)\n## Context', remaining, re.MULTILINE | re.DOTALL)
        context_match = re.search(r'^## Context\s*\n\n(.*?)\n## Roadmap', remaining, re.MULTILINE | re.DOTALL)
        roadmap_match = re.search(r'^## Roadmap\s*\n(.*?)\n## Reasoning Logs', remaining, re.MULTILINE | re.DOTALL)
        logs_match = re.search(r'^## Reasoning Logs\s*\n(.*)', remaining, re.MULTILINE | re.DOTALL)

        objective = objective_match.group(1).strip() if objective_match else ""
        context = context_match.group(1).strip() if context_match else ""

        # Parse steps from roadmap
        steps: List[PlanStep] = []
        if roadmap_match:
            roadmap_text = roadmap_match.group(1)
            for idx, line in enumerate(roadmap_text.split('\n'), 1):
                step = PlanStep.from_markdown(line)
                if step:
                    step.number = len(steps) + 1
                    steps.append(step)

        # Parse reasoning logs
        reasoning_logs: List[str] = []
        if logs_match:
            logs_text = logs_match.group(1)
            for line in logs_text.split('\n'):
                if line.startswith('- ['):
                    reasoning_logs.append(line[2:].strip())

        return PlanContent(
            metadata=metadata,
            objective=objective,
            context=context,
            steps=steps,
            reasoning_logs=reasoning_logs
        )

    @staticmethod
    def _iso_timestamp() -> str:
        """Get current time as ISO-8601 UTC string."""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def _parse_timestamp(iso_str: str) -> datetime:
        """Parse ISO-8601 UTC timestamp string."""
        return datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
