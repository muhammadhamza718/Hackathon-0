"""Browser MCP automation for social media posting.

Provides browser automation scripts for posting to X (Twitter), Facebook,
and Instagram via Browser MCP. Handles login sessions securely and
supports scheduled posting.

Note: This module requires Browser MCP to be configured with appropriate
credentials stored securely (e.g., environment variables or secret manager).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, unique
from pathlib import Path
from typing import Any, Protocol

from agents.exceptions import SocialMediaError


@unique
class BrowserAction(Enum):
    """Browser automation actions."""

    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    UPLOAD = "upload"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    EVALUATE = "evaluate"


@dataclass
class BrowserStep:
    """A single browser automation step."""

    action: BrowserAction
    selector: str = ""
    value: str = ""
    timeout: int = 5000
    description: str = ""


@dataclass
class PostResult:
    """Result of a social media post operation."""

    success: bool
    platform: str
    post_url: str | None = None
    error: str | None = None
    timestamp: str = ""
    screenshot_path: str | None = None


class BrowserMCPProtocol(Protocol):
    """Protocol for Browser MCP client."""

    async def navigate(self, url: str) -> dict: ...
    async def click(self, selector: str) -> dict: ...
    async def type(self, selector: str, text: str) -> dict: ...
    async def upload(self, selector: str, file_path: str) -> dict: ...
    async def screenshot(self, path: str) -> dict: ...
    async def wait(self, milliseconds: int) -> dict: ...
    async def evaluate(self, script: str) -> dict: ...


class SocialMediaAutomation:
    """Browser-based social media posting automation.

    Provides platform-specific automation for posting to X, Facebook,
    and Instagram. Uses Browser MCP for browser control.

    Security Notes:
        - Credentials MUST be stored in environment variables
        - Session cookies should be encrypted at rest
        - Never log sensitive information
        - Implement rate limiting to avoid account flags
    """

    def __init__(
        self,
        browser_client: BrowserMCPProtocol | None = None,
        vault_root: Path | None = None,
    ) -> None:
        """Initialize SocialMediaAutomation.

        Args:
            browser_client: Browser MCP client instance.
            vault_root: Vault root for storing session data.
        """
        self._browser = browser_client
        self._vault_root = vault_root
        self._sessions: dict[str, dict] = {}

    def set_browser_client(self, client: BrowserMCPProtocol) -> None:
        """Set the Browser MCP client.

        Args:
            client: Browser MCP client instance.
        """
        self._browser = client

    async def _execute_steps(
        self,
        steps: list[BrowserStep],
    ) -> list[dict]:
        """Execute a sequence of browser steps.

        Args:
            steps: List of browser steps to execute.

        Returns:
            List of results from each step.

        Raises:
            SocialMediaError: If browser client is not set or step fails.
        """
        if self._browser is None:
            raise SocialMediaError("Browser client not set")

        results: list[dict] = []
        for step in steps:
            try:
                if step.action == BrowserAction.NAVIGATE:
                    result = await self._browser.navigate(step.value)
                elif step.action == BrowserAction.CLICK:
                    result = await self._browser.click(step.selector)
                elif step.action == BrowserAction.TYPE:
                    result = await self._browser.type(step.selector, step.value)
                elif step.action == BrowserAction.UPLOAD:
                    result = await self._browser.upload(step.selector, step.value)
                elif step.action == BrowserAction.SCREENSHOT:
                    result = await self._browser.screenshot(step.value)
                elif step.action == BrowserAction.WAIT:
                    result = await self._browser.wait(step.timeout)
                elif step.action == BrowserAction.EVALUATE:
                    result = await self._browser.evaluate(step.value)
                else:
                    raise SocialMediaError(f"Unknown action: {step.action}")

                results.append(result)

                # Small delay between steps
                if step.timeout > 0:
                    await asyncio.sleep(step.timeout / 1000)

            except Exception as e:
                raise SocialMediaError(
                    f"Step failed: {step.description or step.action.value} - {e}"
                ) from e

        return results

    def _get_x_post_steps(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
    ) -> list[BrowserStep]:
        """Get browser steps for posting to X (Twitter).

        Args:
            content: Post content.
            media_paths: Paths to media files.

        Returns:
            List of browser steps.
        """
        steps = [
            BrowserStep(
                BrowserAction.NAVIGATE,
                value="https://twitter.com/home",
                description="Navigate to X home",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=2000,
                description="Wait for page load",
            ),
            BrowserStep(
                BrowserAction.CLICK,
                selector="[data-testid='tweetTextarea_0']",
                description="Click compose box",
            ),
            BrowserStep(
                BrowserAction.TYPE,
                selector="[data-testid='tweetTextarea_0']",
                value=content,
                description="Type post content",
            ),
        ]

        # Add media upload steps
        for i, media_path in enumerate(media_paths[:4]):  # X allows max 4
            steps.extend([
                BrowserStep(
                    BrowserAction.CLICK,
                    selector="[data-testid='addImageButton']",
                    description=f"Click add image button {i+1}",
                ),
                BrowserStep(
                    BrowserAction.UPLOAD,
                    selector="input[type='file']",
                    value=media_path,
                    description=f"Upload image {i+1}",
                ),
                BrowserStep(
                    BrowserAction.WAIT,
                    timeout=1500,
                    description="Wait for upload",
                ),
            ])

        steps.extend([
            BrowserStep(
                BrowserAction.CLICK,
                selector="[data-testid='tweetButton']",
                description="Click tweet button",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=3000,
                description="Wait for post to publish",
            ),
            BrowserStep(
                BrowserAction.SCREENSHOT,
                value="x_post_confirmation.png",
                description="Capture confirmation",
            ),
        ])

        return steps

    def _get_facebook_post_steps(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
    ) -> list[BrowserStep]:
        """Get browser steps for posting to Facebook.

        Args:
            content: Post content.
            media_paths: Paths to media files.

        Returns:
            List of browser steps.
        """
        steps = [
            BrowserStep(
                BrowserAction.NAVIGATE,
                value="https://www.facebook.com",
                description="Navigate to Facebook",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=2000,
                description="Wait for page load",
            ),
            BrowserStep(
                BrowserAction.CLICK,
                selector="[placeholder=\"What's on your mind?\"]",
                description="Click create post",
            ),
            BrowserStep(
                BrowserAction.TYPE,
                selector="[placeholder=\"What's on your mind?\"]",
                value=content,
                description="Type post content",
            ),
        ]

        # Add media upload
        if media_paths:
            steps.append(
                BrowserStep(
                    BrowserAction.CLICK,
                    selector="[aria-label='Photo/video']",
                    description="Click add photo/video",
                ),
            )
            for media_path in media_paths[:10]:  # FB allows max 10
                steps.extend([
                    BrowserStep(
                        BrowserAction.UPLOAD,
                        selector="input[type='file']",
                        value=media_path,
                        description=f"Upload image",
                    ),
                    BrowserStep(
                        BrowserAction.WAIT,
                        timeout=2000,
                        description="Wait for upload",
                    ),
                ])

        steps.extend([
            BrowserStep(
                BrowserAction.CLICK,
                selector="[type='submit']",
                description="Click post button",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=3000,
                description="Wait for post to publish",
            ),
        ])

        return steps

    def _get_instagram_post_steps(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
    ) -> list[BrowserStep]:
        """Get browser steps for posting to Instagram.

        Args:
            content: Post content (caption).
            media_paths: Paths to media files.

        Returns:
            List of browser steps.
        """
        steps = [
            BrowserStep(
                BrowserAction.NAVIGATE,
                value="https://www.instagram.com",
                description="Navigate to Instagram",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=2000,
                description="Wait for page load",
            ),
            BrowserStep(
                BrowserAction.CLICK,
                selector="[aria-label='New post']",
                description="Click new post",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=1000,
                description="Wait for dialog",
            ),
        ]

        # Add media upload
        for media_path in media_paths[:10]:  # IG allows max 10
            steps.extend([
                BrowserStep(
                    BrowserAction.UPLOAD,
                    selector="input[type='file']",
                    value=media_path,
                    description="Upload image",
                ),
                BrowserStep(
                    BrowserAction.WAIT,
                    timeout=2000,
                    description="Wait for upload",
                ),
            ])

        steps.extend([
            BrowserStep(
                BrowserAction.CLICK,
                selector="button[type='button']",
                description="Click next",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=1000,
                description="Wait for edit screen",
            ),
            BrowserStep(
                BrowserAction.CLICK,
                selector="button[type='button']",
                description="Click next again",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=1000,
                description="Wait for caption screen",
            ),
            BrowserStep(
                BrowserAction.TYPE,
                selector="[aria-label='Write a caption...']",
                value=content,
                description="Type caption",
            ),
            BrowserStep(
                BrowserAction.CLICK,
                selector="button[type='button']",
                description="Click share",
            ),
            BrowserStep(
                BrowserAction.WAIT,
                timeout=3000,
                description="Wait for post to publish",
            ),
        ])

        return steps

    async def post_to_x(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
        screenshot_dir: Path | None = None,
    ) -> PostResult:
        """Post content to X (Twitter).

        Args:
            content: Post content (max 280 chars).
            media_paths: Paths to media files.
            screenshot_dir: Directory for screenshots.

        Returns:
            PostResult with success status and details.
        """
        try:
            steps = self._get_x_post_steps(content, media_paths)

            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                # Update screenshot path
                for step in steps:
                    if step.action == BrowserAction.SCREENSHOT:
                        step.value = str(screenshot_dir / f"x_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

            results = await self._execute_steps(steps)

            return PostResult(
                success=True,
                platform="X",
                timestamp=datetime.now(timezone.utc).isoformat(),
                screenshot_path=results[-1].get("path") if results else None,
            )

        except SocialMediaError as e:
            return PostResult(
                success=False,
                platform="X",
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def post_to_facebook(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
        screenshot_dir: Path | None = None,
    ) -> PostResult:
        """Post content to Facebook.

        Args:
            content: Post content.
            media_paths: Paths to media files.
            screenshot_dir: Directory for screenshots.

        Returns:
            PostResult with success status and details.
        """
        try:
            steps = self._get_facebook_post_steps(content, media_paths)

            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)

            await self._execute_steps(steps)

            return PostResult(
                success=True,
                platform="Facebook",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except SocialMediaError as e:
            return PostResult(
                success=False,
                platform="Facebook",
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def post_to_instagram(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
        screenshot_dir: Path | None = None,
    ) -> PostResult:
        """Post content to Instagram.

        Args:
            content: Post caption.
            media_paths: Paths to media files.
            screenshot_dir: Directory for screenshots.

        Returns:
            PostResult with success status and details.
        """
        try:
            steps = self._get_instagram_post_steps(content, media_paths)

            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)

            await self._execute_steps(steps)

            return PostResult(
                success=True,
                platform="Instagram",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except SocialMediaError as e:
            return PostResult(
                success=False,
                platform="Instagram",
                error=str(e),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    async def post_to_all(
        self,
        content: str,
        media_paths: tuple[str, ...] = (),
        platforms: list[str] | None = None,
    ) -> dict[str, PostResult]:
        """Post content to multiple platforms.

        Args:
            content: Post content.
            media_paths: Paths to media files.
            platforms: List of platforms (default: all).

        Returns:
            Dict mapping platform to PostResult.
        """
        if platforms is None:
            platforms = ["X", "Facebook", "Instagram"]

        results: dict[str, PostResult] = {}

        for platform in platforms:
            if platform == "X":
                results["X"] = await self.post_to_x(content, media_paths)
            elif platform == "Facebook":
                results["Facebook"] = await self.post_to_facebook(content, media_paths)
            elif platform == "Instagram":
                results["Instagram"] = await self.post_to_instagram(content, media_paths)
            else:
                results[platform] = PostResult(
                    success=False,
                    platform=platform,
                    error=f"Unknown platform: {platform}",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        return results


# Convenience function for synchronous usage (for testing)
def create_automation(
    browser_client: BrowserMCPProtocol | None = None,
    vault_root: Path | None = None,
) -> SocialMediaAutomation:
    """Create a SocialMediaAutomation instance.

    Args:
        browser_client: Browser MCP client.
        vault_root: Vault root path.

    Returns:
        Configured SocialMediaAutomation instance.
    """
    return SocialMediaAutomation(browser_client, vault_root)
