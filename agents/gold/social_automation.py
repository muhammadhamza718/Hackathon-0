"""Browser MCP automation for social media publishing.

Provides browser automation capabilities for social media platforms
that don't have public APIs, using Playwright for reliable automation.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
    """Browser configuration for automation."""

    headless: bool = True
    timeout_ms: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str | None = None
    proxy: str | None = None


@dataclass
class PublishTask:
    """A social media publishing task."""

    platform: str
    content: str
    media_paths: list[str] | None = None
    scheduled_time: str | None = None
    status: str = "pending"
    result_url: str | None = None
    error: str | None = None


class SocialMediaAutomation:
    """Browser automation for social media publishing.

    Supports:
    - X (Twitter) posting
    - Facebook posting
    - LinkedIn posting
    - Instagram posting (via web)

    Note: This is a framework - actual implementation requires
    proper authentication and may violate platform ToS.
    Use official APIs when available.
    """

    def __init__(self, config: BrowserConfig | None = None):
        """Initialize the automation engine.

        Args:
            config: Browser configuration.
        """
        self.config = config or BrowserConfig()
        self._browser = None
        self._context = None
        self._page = None

    async def start(self) -> None:
        """Start the browser."""
        try:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=self.config.headless
            )
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                user_agent=self.config.user_agent,
            )
            self._page = await self._context.new_page()
            logger.info("Browser automation started")

        except ImportError:
            logger.warning(
                "Playwright not installed. Install with: pip install playwright"
            )
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    async def stop(self) -> None:
        """Stop the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._context = None
            self._page = None
            logger.info("Browser automation stopped")

    async def login(
        self, platform: str, username: str, password: str
    ) -> bool:
        """Login to a social media platform.

        Args:
            platform: Platform name.
            username: Username or email.
            password: Password.

        Returns:
            True if login successful.
        """
        if not self._page:
            await self.start()

        try:
            if platform.lower() == "x" or platform.lower() == "twitter":
                return await self._login_x(username, password)
            elif platform.lower() == "facebook":
                return await self._login_facebook(username, password)
            elif platform.lower() == "linkedin":
                return await self._login_linkedin(username, password)
            else:
                logger.error(f"Unsupported platform: {platform}")
                return False

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def _login_x(
        self, username: str, password: str
    ) -> bool:
        """Login to X (Twitter)."""
        if not self._page:
            return False

        await self._page.goto("https://twitter.com/login")
        await self._page.wait_for_load_state("networkidle")

        # Fill login form (selectors may change)
        await self._page.fill(
            'input[autocomplete="username"]', username
        )
        await self._page.click('div[role="button"]:has-text("Next")')
        await self._page.wait_for_timeout(1000)

        await self._page.fill(
            'input[type="password"]', password
        )
        await self._page.click('div[role="button"]:has-text("Log in")')
        await self._page.wait_for_load_state("networkidle")

        # Check if login successful
        url = self._page.url
        return "home" in url or "timeline" in url

    async def _login_facebook(
        self, username: str, password: str
    ) -> bool:
        """Login to Facebook."""
        if not self._page:
            return False

        await self._page.goto("https://facebook.com")
        await self._page.wait_for_load_state("networkidle")

        # Fill login form
        await self._page.fill("#email", username)
        await self._page.fill("#pass", password)
        await self._page.click('button[name="login"]')
        await self._page.wait_for_load_state("networkidle")

        # Check if login successful
        url = self._page.url
        return "facebook.com" in url and "login" not in url

    async def _login_linkedin(
        self, username: str, password: str
    ) -> bool:
        """Login to LinkedIn."""
        if not self._page:
            return False

        await self._page.goto("https://linkedin.com/login")
        await self._page.wait_for_load_state("networkidle")

        # Fill login form
        await self._page.fill("#username", username)
        await self._page.fill("#password", password)
        await self._page.click('button[type="submit"]')
        await self._page.wait_for_load_state("networkidle")

        # Check if login successful
        url = self._page.url
        return "linkedin.com/feed" in url

    async def publish(
        self, platform: str, content: str, media_paths: list[str] | None = None
    ) -> PublishTask:
        """Publish content to a platform.

        Args:
            platform: Platform name.
            content: Content to publish.
            media_paths: Optional media file paths.

        Returns:
            PublishTask with result.
        """
        task = PublishTask(
            platform=platform,
            content=content,
            media_paths=media_paths,
        )

        if not self._page:
            task.status = "error"
            task.error = "Browser not started"
            return task

        try:
            if platform.lower() == "x" or platform.lower() == "twitter":
                await self._publish_x(content, media_paths)
            elif platform.lower() == "facebook":
                await self._publish_facebook(content, media_paths)
            elif platform.lower() == "linkedin":
                await self._publish_linkedin(content, media_paths)
            else:
                task.status = "error"
                task.error = f"Unsupported platform: {platform}"
                return task

            task.status = "published"
            task.result_url = self._page.url if self._page else None
            logger.info(f"Published to {platform}")

        except Exception as e:
            task.status = "error"
            task.error = str(e)
            logger.error(f"Publish failed: {e}")

        return task

    async def _publish_x(
        self, content: str, media_paths: list[str] | None
    ) -> None:
        """Publish to X (Twitter)."""
        if not self._page:
            return

        await self._page.goto("https://twitter.com/home")
        await self._page.wait_for_load_state("networkidle")

        # Find and fill tweet box
        tweet_box = self._page.locator(
            'div[contenteditable="true"][data-testid="tweetTextarea_0"]'
        )
        await tweet_box.fill(content)

        # Upload media if provided
        if media_paths:
            for media_path in media_paths[:4]:  # X allows up to 4 images
                await self._page.locator(
                    'input[type="file"][accept="image/*,video/*"]'
                ).set_input_files(media_path)
                await self._page.wait_for_timeout(1000)

        # Click tweet button
        await self._page.click(
            'div[role="button"][data-testid="tweetButton"]'
        )
        await self._page.wait_for_load_state("networkidle")

    async def _publish_facebook(
        self, content: str, media_paths: list[str] | None
    ) -> None:
        """Publish to Facebook."""
        if not self._page:
            return

        await self._page.goto("https://facebook.com")
        await self._page.wait_for_load_state("networkidle")

        # Click on "What's on your mind?" box
        await self._page.click(
            'div[role="button"][aria-label="What\'s on your mind?"]'
        )
        await self._page.wait_for_timeout(1000)

        # Fill content
        await self._page.fill(
            'div[contenteditable="true"][data-testid="post-creation-textarea"]',
            content,
        )

        # Upload media if provided
        if media_paths:
            await self._page.click(
                'div[role="button"][aria-label="Photo/video"]'
            )
            for media_path in media_paths[:10]:  # Facebook allows up to 10
                await self._page.locator(
                    'input[type="file"][accept="image/*,video/*"]'
                ).set_input_files(media_path)

        # Click post button
        await self._page.click(
            'div[role="button"][aria-label="Post"]'
        )
        await self._page.wait_for_load_state("networkidle")

    async def _publish_linkedin(
        self, content: str, media_paths: list[str] | None
    ) -> None:
        """Publish to LinkedIn."""
        if not self._page:
            return

        await self._page.goto("https://linkedin.com/feed")
        await self._page.wait_for_load_state("networkidle")

        # Click on "Start a post"
        await self._page.click(
            'div[role="button"][aria-label="Start a post"]'
        )
        await self._page.wait_for_timeout(1000)

        # Fill content
        await self._page.fill(
            'div[contenteditable="true"][aria-label="What do you want to talk about?"]',
            content,
        )

        # Upload media if provided
        if media_paths:
            await self._page.click(
                'div[role="button"][aria-label="Add media"]'
            )
            for media_path in media_paths[:9]:  # LinkedIn allows up to 9
                await self._page.locator(
                    'input[type="file"]'
                ).set_input_files(media_path)

        # Click post button
        await self._page.click(
            'div[role="button"][aria-label="Post"]'
        )
        await self._page.wait_for_load_state("networkidle")

    async def take_screenshot(
        self, output_path: str | Path
    ) -> str:
        """Take a screenshot of the current page.

        Args:
            output_path: Path to save screenshot.

        Returns:
            Path to saved screenshot.
        """
        if not self._page:
            raise RuntimeError("Browser not started")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        await self._page.screenshot(path=str(output_path))
        logger.info(f"Screenshot saved to {output_path}")
        return str(output_path)

    async def get_current_url(self) -> str:
        """Get the current page URL.

        Returns:
            Current URL.
        """
        if not self._page:
            return ""
        return self._page.url


class BrowserMCPTools:
    """MCP tools for browser automation.

    Provides a tool-based interface for AI agents to control
    browser automation.
    """

    def __init__(self, automation: SocialMediaAutomation | None = None):
        """Initialize browser MCP tools.

        Args:
            automation: Social media automation instance.
        """
        self.automation = automation or SocialMediaAutomation()

    def get_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools.

        Returns:
            List of tool definitions.
        """
        return [
            {
                "name": "browser_start",
                "description": "Start the browser automation",
                "parameters": {"headless": {"type": "boolean", "default": True}},
            },
            {
                "name": "browser_stop",
                "description": "Stop the browser automation",
            },
            {
                "name": "browser_login",
                "description": "Login to a social media platform",
                "parameters": {
                    "platform": {"type": "string"},
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                },
            },
            {
                "name": "browser_publish",
                "description": "Publish content to a platform",
                "parameters": {
                    "platform": {"type": "string"},
                    "content": {"type": "string"},
                    "media_paths": {"type": "array", "items": {"type": "string"}},
                },
            },
            {
                "name": "browser_screenshot",
                "description": "Take a screenshot of the current page",
                "parameters": {
                    "output_path": {"type": "string"},
                },
            },
        ]

    async def execute_tool(
        self, tool_name: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Execute a browser tool.

        Args:
            tool_name: Name of the tool to execute.
            **kwargs: Tool parameters.

        Returns:
            Tool execution result.
        """
        if tool_name == "browser_start":
            await self.automation.start()
            return {"success": True, "message": "Browser started"}

        elif tool_name == "browser_stop":
            await self.automation.stop()
            return {"success": True, "message": "Browser stopped"}

        elif tool_name == "browser_login":
            success = await self.automation.login(
                kwargs.get("platform", ""),
                kwargs.get("username", ""),
                kwargs.get("password", ""),
            )
            return {
                "success": success,
                "message": "Login successful" if success else "Login failed",
            }

        elif tool_name == "browser_publish":
            task = await self.automation.publish(
                kwargs.get("platform", ""),
                kwargs.get("content", ""),
                kwargs.get("media_paths"),
            )
            return task.__dict__

        elif tool_name == "browser_screenshot":
            path = await self.automation.take_screenshot(
                kwargs.get("output_path", "screenshot.png")
            )
            return {"success": True, "path": path}

        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
            }
