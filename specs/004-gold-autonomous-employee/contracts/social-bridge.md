# Contract: Multi-Channel Social Bridge

**Skill**: `social-media-management`
**Module**: `agents/gold/social_bridge.py`

## Interface

### `SocialBridge`

#### `__init__(browser_mcp_config: BrowserMCPConfig, vault_root: Path)`
- **Precondition**: Browser MCP server accessible at configured host:port.
- **Postcondition**: Bridge initialized with platform adapters registered.

#### `draft_post(platform: str, content: str, media_paths: list[str] = [], scheduled: str = "immediate", rationale: str = "") -> SocialDraft`
- **Behavior**: Creates a `SocialDraft` and writes it to `/Pending_Approval/`.
- **HITL**: ALL posts go to `/Pending_Approval/` — no exceptions (Constitution XII).
- **Validation**: Content length checked against platform limits. Media paths verified.
- **Returns**: `SocialDraft` with `approval_status=pending`.
- **Side effects**: Logs `social_draft` audit entry.
- **Errors**: `ContentValidationError` if content exceeds platform limits.

#### `draft_multi_post(content: str, platforms: list[str], media_paths: list[str] = [], scheduled: str = "immediate", rationale: str = "") -> list[SocialDraft]`
- **Behavior**: Adapts content for each platform and creates one draft per platform.
- **Adaptation rules**:
  - Twitter/X: Truncate to 280 chars, prioritize key message.
  - Facebook: Full content, add call-to-action if applicable.
  - Instagram: Optimize for hashtags, ensure no embedded links in body.
- **Returns**: List of `SocialDraft` objects, one per platform.

#### `publish_approved(draft: SocialDraft) -> PublishResult`
- **Precondition**: Draft file MUST exist in `/Approved/`.
- **Behavior**: Use Browser MCP to navigate to platform, compose post, upload media, submit.
- **Postcondition**: Post published, file moved to `/Done/`.
- **Side effects**: Logs `social_post` audit entry.
- **Errors**: `ApprovalNotFoundError` if file not in `/Approved/`. `PublishError` on platform failure.
- **Resilience**: Wrapped in `ResilientExecutor`.

#### `get_engagement_summary(platform: str, period_days: int = 7) -> EngagementSummary`
- **Behavior**: Use Browser MCP to navigate to analytics page and extract metrics.
- **Returns**: `EngagementSummary` with impressions, likes, comments, shares.
- **Autonomous**: This is a READ operation — no approval required.

### Platform Adapters

Each platform has a dedicated adapter implementing:

```python
class PlatformAdapter(Protocol):
    platform_name: str
    max_text_length: int
    max_images: int

    def adapt_content(self, content: str) -> str: ...
    def compose_post(self, draft: SocialDraft) -> BrowserMCPActions: ...
    def extract_engagement(self) -> EngagementMetrics: ...
```

### `PublishResult`

```python
@dataclass(frozen=True)
class PublishResult:
    success: bool
    platform: str
    published_at: str  # ISO-8601
    post_url: str | None
    error: str | None
```

### `EngagementSummary`

```python
@dataclass(frozen=True)
class EngagementSummary:
    platform: str
    period_start: str
    period_end: str
    total_posts: int
    total_impressions: int
    total_likes: int
    total_comments: int
    total_shares: int
    top_post: str | None
```

## Approval File Format (in /Pending_Approval/)

Filename: `<ISO-timestamp>_social-post_<platform>-<slug>.md`

```markdown
---
type: social-post
platform: X
scheduled: 2026-03-10T15:00:00Z
rationale: Plan-2026-005#Step-4 — Weekly product update
risk_level: Low
---

# Social Media Post Draft

**Platform**: X (Twitter)
**Scheduled**: 2026-03-10T15:00:00Z

## Content
Here's what we accomplished this week! [thread continues...]

## Media
- /vault/media/week10-update-1.jpg
- /vault/media/week10-update-2.jpg

## Rationale
Weekly product update per marketing plan (Plan-2026-005#Step-4).
```

## Success Metrics
- **SC-SOCIAL-1**: ALL posts go to `/Pending_Approval/` — zero direct publications.
- **SC-SOCIAL-2**: Content adapted correctly per platform limits (no truncation errors).
- **SC-SOCIAL-3**: Multi-image posts upload successfully across all platforms.
- **SC-SOCIAL-4**: Engagement summaries return accurate metrics.
- **SC-SOCIAL-5**: Brand consistency maintained per `Company_Handbook.md` persona.