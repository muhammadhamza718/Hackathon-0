"""Social media analytics aggregation and summary.

Provides unified analytics collection and reporting across multiple
social media platforms.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PlatformMetrics:
    """Metrics for a single platform."""

    platform: str
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    impressions: int = 0
    engagements: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    profile_views: int = 0
    collected_at: str = ""

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate."""
        if self.impressions == 0:
            return 0.0
        return (self.engagements / self.impressions) * 100

    @property
    def click_through_rate(self) -> float:
        """Calculate click-through rate."""
        if self.impressions == 0:
            return 0.0
        return (self.clicks / self.impressions) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "platform": self.platform,
            "followers": self.followers,
            "following": self.following,
            "posts_count": self.posts_count,
            "impressions": self.impressions,
            "engagements": self.engagements,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "clicks": self.clicks,
            "profile_views": self.profile_views,
            "engagement_rate": round(self.engagement_rate, 2),
            "click_through_rate": round(self.click_through_rate, 2),
            "collected_at": self.collected_at,
        }


@dataclass
class PostMetrics:
    """Metrics for a single post."""

    post_id: str
    platform: str
    content: str = ""
    posted_at: str = ""
    impressions: int = 0
    engagements: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    saves: int = 0

    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate."""
        if self.impressions == 0:
            return 0.0
        return (self.engagements / self.impressions) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "post_id": self.post_id,
            "platform": self.platform,
            "content": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "posted_at": self.posted_at,
            "impressions": self.impressions,
            "engagements": self.engagements,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "clicks": self.clicks,
            "saves": self.saves,
            "engagement_rate": round(self.engagement_rate, 2),
        }


@dataclass
class AnalyticsSummary:
    """Aggregated analytics summary across platforms."""

    period_start: str
    period_end: str
    platform_metrics: dict[str, PlatformMetrics] = field(default_factory=dict)
    post_metrics: list[PostMetrics] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    @property
    def total_followers(self) -> int:
        """Get total followers across all platforms."""
        return sum(m.followers for m in self.platform_metrics.values())

    @property
    def total_impressions(self) -> int:
        """Get total impressions across all platforms."""
        return sum(m.impressions for m in self.platform_metrics.values())

    @property
    def total_engagements(self) -> int:
        """Get total engagements across all platforms."""
        return sum(m.engagements for m in self.platform_metrics.values())

    @property
    def average_engagement_rate(self) -> float:
        """Get average engagement rate across platforms."""
        if not self.platform_metrics:
            return 0.0
        rates = [m.engagement_rate for m in self.platform_metrics.values()]
        return sum(rates) / len(rates)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": self.generated_at,
            "total_followers": self.total_followers,
            "total_impressions": self.total_impressions,
            "total_engagements": self.total_engagements,
            "average_engagement_rate": round(self.average_engagement_rate, 2),
            "platforms": {
                name: metrics.to_dict()
                for name, metrics in self.platform_metrics.items()
            },
            "top_posts": [
                p.to_dict() for p in sorted(
                    self.post_metrics,
                    key=lambda x: x.engagements,
                    reverse=True,
                )[:5]
            ],
        }


class AnalyticsAggregator:
    """Aggregates analytics from multiple social media platforms.

    Features:
    - Unified metrics collection
    - Cross-platform comparison
    - Trend analysis
    - Summary generation
    """

    def __init__(self):
        """Initialize the analytics aggregator."""
        self._metrics_cache: dict[str, PlatformMetrics] = {}
        self._post_metrics: list[PostMetrics] = []

    def add_platform_metrics(self, metrics: PlatformMetrics) -> None:
        """Add metrics for a platform.

        Args:
            metrics: Platform metrics to add.
        """
        self._metrics_cache[metrics.platform] = metrics
        logger.debug(f"Added metrics for {metrics.platform}")

    def add_post_metrics(self, metrics: PostMetrics) -> None:
        """Add metrics for a post.

        Args:
            metrics: Post metrics to add.
        """
        self._post_metrics.append(metrics)
        logger.debug(f"Added metrics for post {metrics.post_id}")

    def get_platform_metrics(
        self, platform: str
    ) -> PlatformMetrics | None:
        """Get metrics for a specific platform.

        Args:
            platform: Platform name.

        Returns:
            Platform metrics or None if not found.
        """
        return self._metrics_cache.get(platform)

    def get_all_platform_metrics(self) -> dict[str, PlatformMetrics]:
        """Get metrics for all platforms.

        Returns:
            Dictionary mapping platform names to metrics.
        """
        return dict(self._metrics_cache)

    def generate_summary(
        self,
        days: int = 7,
        include_posts: bool = True,
    ) -> AnalyticsSummary:
        """Generate an analytics summary.

        Args:
            days: Number of days for the summary period.
            include_posts: Whether to include post metrics.

        Returns:
            Analytics summary.
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        summary = AnalyticsSummary(
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
            platform_metrics=self._metrics_cache,
            post_metrics=self._post_metrics if include_posts else [],
        )

        logger.info(
            f"Generated analytics summary for {days} days: "
            f"{summary.total_followers} total followers, "
            f"{summary.total_impressions} impressions"
        )

        return summary

    def compare_platforms(
        self, platforms: list[str] | None = None
    ) -> dict[str, Any]:
        """Compare metrics across platforms.

        Args:
            platforms: List of platforms to compare (default: all).

        Returns:
            Comparison results.
        """
        if platforms is None:
            platforms = list(self._metrics_cache.keys())

        comparison = {
            "platforms": platforms,
            "metrics": {},
            "rankings": {},
        }

        # Compare key metrics
        for metric in [
            "followers",
            "impressions",
            "engagements",
            "engagement_rate",
        ]:
            values = []
            for platform in platforms:
                metrics = self._metrics_cache.get(platform)
                if metrics:
                    if metric == "engagement_rate":
                        values.append(
                            (platform, metrics.engagement_rate)
                        )
                    else:
                        values.append(
                            (platform, getattr(metrics, metric, 0))
                        )

            # Sort by value
            sorted_values = sorted(
                values, key=lambda x: x[1], reverse=True
            )
            comparison["rankings"][metric] = [
                {"platform": p, "value": v} for p, v in sorted_values
            ]

        return comparison

    def get_trends(
        self, metric: str = "engagements", days: int = 7
    ) -> dict[str, Any]:
        """Get trends for a specific metric.

        Args:
            metric: Metric to track.
            days: Number of days.

        Returns:
            Trend data.
        """
        # This is a simplified implementation
        # A full implementation would track historical data
        return {
            "metric": metric,
            "days": days,
            "note": "Historical tracking not implemented",
            "current_value": sum(
                getattr(m, metric, 0)
                for m in self._metrics_cache.values()
            ),
        }

    def clear_cache(self) -> None:
        """Clear the metrics cache."""
        self._metrics_cache.clear()
        self._post_metrics.clear()
        logger.info("Analytics cache cleared")

    def export_to_json(self) -> dict[str, Any]:
        """Export all analytics to JSON-compatible dict.

        Returns:
            Dictionary with all analytics data.
        """
        return {
            "platform_metrics": {
                name: m.to_dict()
                for name, m in self._metrics_cache.items()
            },
            "post_metrics": [
                m.to_dict() for m in self._post_metrics
            ],
            "summary": self.generate_summary().to_dict(),
        }
