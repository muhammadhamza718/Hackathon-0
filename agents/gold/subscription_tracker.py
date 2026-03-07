"""Subscription usage tracking and optimization.

Provides subscription management including usage tracking, cost analysis,
and optimization recommendations for CEO briefings.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import SubscriptionFinding

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """A subscription service."""

    name: str
    monthly_cost: float
    annual_cost: float = 0.0
    category: str = "Software"
    vendor: str = ""
    start_date: str = ""
    renewal_date: str = ""
    status: str = "active"  # active, cancelled, pending_cancel
    notes: str = ""

    def __post_init__(self):
        if self.annual_cost == 0.0:
            self.annual_cost = self.monthly_cost * 12

    @property
    def annual_savings(self) -> float:
        """Calculate savings from annual vs monthly billing."""
        if self.annual_cost == 0:
            return 0.0
        monthly_total = self.monthly_cost * 12
        return monthly_total - self.annual_cost


@dataclass
class SubscriptionUsage:
    """Usage metrics for a subscription."""

    subscription_name: str
    tracked_at: str = ""
    last_used: str = ""
    usage_count_30d: int = 0
    usage_count_7d: int = 0
    active_users: int = 0
    total_seats: int = 1
    utilization_pct: float = 0.0
    features_used: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.tracked_at:
            self.tracked_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        if self.total_seats > 0:
            self.utilization_pct = (self.active_users / self.total_seats) * 100

    @property
    def is_underused(self) -> bool:
        """Check if subscription is underused."""
        return self.utilization_pct < 30 or self.usage_count_30d < 5

    @property
    def is_unused(self) -> bool:
        """Check if subscription is unused."""
        return self.usage_count_30d == 0


@dataclass
class MarketComparison:
    """Market rate comparison for a subscription."""

    subscription_name: str
    current_price: float
    market_average: float
    market_low: float
    market_high: float
    compared_at: str = ""

    def __post_init__(self):
        if not self.compared_at:
            self.compared_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

    @property
    def pct_above_market(self) -> float:
        """Calculate percentage above market average."""
        if self.market_average == 0:
            return 0.0
        return ((self.current_price - self.market_average) / self.market_average) * 100

    @property
    def is_overpriced(self) -> bool:
        """Check if subscription is overpriced."""
        return self.pct_above_market > 20


class SubscriptionTracker:
    """Tracks and analyzes subscription usage.

    Features:
    - Subscription inventory management
    - Usage tracking
    - Cost analysis
    - Optimization recommendations
    """

    def __init__(self, data_file: str | Path | None = None):
        """Initialize the subscription tracker.

        Args:
            data_file: Optional path to persist subscription data.
        """
        self.data_file = Path(data_file) if data_file else None
        self._subscriptions: dict[str, Subscription] = {}
        self._usage: dict[str, SubscriptionUsage] = {}
        self._market_comparisons: dict[str, MarketComparison] = {}

        if self.data_file and self.data_file.exists():
            self._load_data()

    def add_subscription(self, subscription: Subscription) -> None:
        """Add a subscription.

        Args:
            subscription: Subscription to add.
        """
        self._subscriptions[subscription.name] = subscription
        logger.info(f"Added subscription: {subscription.name}")
        self._save_data()

    def remove_subscription(self, name: str) -> None:
        """Remove a subscription.

        Args:
            name: Subscription name.
        """
        if name in self._subscriptions:
            del self._subscriptions[name]
            logger.info(f"Removed subscription: {name}")
            self._save_data()

    def update_usage(self, usage: SubscriptionUsage) -> None:
        """Update usage metrics for a subscription.

        Args:
            usage: Usage metrics.
        """
        self._usage[usage.subscription_name] = usage
        logger.debug(f"Updated usage for: {usage.subscription_name}")
        self._save_data()

    def add_market_comparison(
        self, comparison: MarketComparison
    ) -> None:
        """Add market comparison for a subscription.

        Args:
            comparison: Market comparison data.
        """
        self._market_comparisons[comparison.subscription_name] = comparison
        self._save_data()

    def get_subscription(
        self, name: str
    ) -> Subscription | None:
        """Get a subscription by name.

        Args:
            name: Subscription name.

        Returns:
            Subscription or None if not found.
        """
        return self._subscriptions.get(name)

    def get_all_subscriptions(self) -> list[Subscription]:
        """Get all subscriptions.

        Returns:
            List of subscriptions.
        """
        return list(self._subscriptions.values())

    def get_total_monthly_cost(self) -> float:
        """Get total monthly subscription cost.

        Returns:
            Total monthly cost.
        """
        return sum(
            s.monthly_cost
            for s in self._subscriptions.values()
            if s.status == "active"
        )

    def get_total_annual_cost(self) -> float:
        """Get total annual subscription cost.

        Returns:
            Total annual cost.
        """
        return sum(
            s.annual_cost if s.annual_cost > 0 else s.monthly_cost * 12
            for s in self._subscriptions.values()
            if s.status == "active"
        )

    def analyze_optimization(
        self,
        underused_threshold: float = 30.0,
        overpriced_threshold: float = 20.0,
    ) -> list[SubscriptionFinding]:
        """Analyze subscriptions for optimization opportunities.

        Args:
            underused_threshold: Utilization % below which to flag.
            overpriced_threshold: % above market to flag.

        Returns:
            List of optimization findings.
        """
        findings: list[SubscriptionFinding] = []

        for sub in self._subscriptions.values():
            if sub.status != "active":
                continue

            usage = self._usage.get(sub.name)
            market = self._market_comparisons.get(sub.name)

            # Check for unused subscriptions
            if usage and usage.is_unused:
                findings.append(
                    SubscriptionFinding(
                        service_name=sub.name,
                        monthly_cost=sub.monthly_cost,
                        finding_type="unused",
                        recommendation="Cancel subscription - no usage detected",
                        potential_savings=sub.monthly_cost,
                    )
                )
                continue

            # Check for underused subscriptions
            if usage and usage.utilization_pct < underused_threshold:
                savings = sub.monthly_cost * (
                    1 - usage.utilization_pct / 100
                )
                findings.append(
                    SubscriptionFinding(
                        service_name=sub.name,
                        monthly_cost=sub.monthly_cost,
                        utilization_pct=usage.utilization_pct,
                        finding_type="underused",
                        recommendation=f"Reduce seats or downgrade plan (current utilization: {usage.utilization_pct:.1f}%)",
                        potential_savings=savings,
                    )
                )

            # Check for overpriced subscriptions
            if market and market.is_overpriced:
                savings = (
                    market.current_price - market.market_average
                )
                findings.append(
                    SubscriptionFinding(
                        service_name=sub.name,
                        monthly_cost=sub.monthly_cost,
                        market_rate=market.market_average,
                        finding_type="overpriced",
                        recommendation=f"Negotiate or switch provider (paying {market.pct_above_market:.1f}% above market)",
                        potential_savings=savings,
                    )
                )

        logger.info(f"Found {len(findings)} optimization opportunities")
        return findings

    def get_upcoming_renewals(
        self, days_ahead: int = 30
    ) -> list[Subscription]:
        """Get subscriptions with upcoming renewals.

        Args:
            days_ahead: Number of days to look ahead.

        Returns:
            List of subscriptions renewing soon.
        """
        if not days_ahead:
            return []

        now = datetime.now(timezone.utc)
        cutoff = now.replace(day=now.day + days_ahead)

        renewals = []
        for sub in self._subscriptions.values():
            if sub.renewal_date:
                try:
                    renewal = datetime.fromisoformat(
                        sub.renewal_date.replace("Z", "+00:00")
                    )
                    if now <= renewal <= cutoff:
                        renewals.append(sub)
                except ValueError:
                    pass

        return sorted(
            renewals, key=lambda s: s.renewal_date or ""
        )

    def get_category_breakdown(self) -> dict[str, float]:
        """Get cost breakdown by category.

        Returns:
            Dictionary mapping categories to monthly costs.
        """
        breakdown: dict[str, float] = {}

        for sub in self._subscriptions.values():
            if sub.status == "active":
                category = sub.category or "Other"
                breakdown[category] = breakdown.get(category, 0) + sub.monthly_cost

        return breakdown

    def export_summary(self) -> dict[str, Any]:
        """Export subscription summary.

        Returns:
            Dictionary with subscription summary.
        """
        findings = self.analyze_optimization()

        return {
            "total_monthly_cost": self.get_total_monthly_cost(),
            "total_annual_cost": self.get_total_annual_cost(),
            "subscription_count": len(
                [s for s in self._subscriptions.values() if s.status == "active"]
            ),
            "category_breakdown": self.get_category_breakdown(),
            "upcoming_renewals": [
                {"name": s.name, "renewal_date": s.renewal_date}
                for s in self.get_upcoming_renewals()
            ],
            "optimization_findings": [
                {
                    "service_name": f.service_name,
                    "finding_type": f.finding_type,
                    "potential_savings": f.potential_savings,
                    "recommendation": f.recommendation,
                }
                for f in findings
            ],
            "total_potential_savings": sum(
                f.potential_savings for f in findings
            ),
        }

    def _save_data(self) -> None:
        """Save data to file."""
        if not self.data_file:
            return

        data = {
            "subscriptions": {
                name: {
                    "name": s.name,
                    "monthly_cost": s.monthly_cost,
                    "annual_cost": s.annual_cost,
                    "category": s.category,
                    "vendor": s.vendor,
                    "start_date": s.start_date,
                    "renewal_date": s.renewal_date,
                    "status": s.status,
                    "notes": s.notes,
                }
                for name, s in self._subscriptions.items()
            },
            "usage": {
                name: {
                    "subscription_name": u.subscription_name,
                    "tracked_at": u.tracked_at,
                    "last_used": u.last_used,
                    "usage_count_30d": u.usage_count_30d,
                    "usage_count_7d": u.usage_count_7d,
                    "active_users": u.active_users,
                    "total_seats": u.total_seats,
                    "features_used": u.features_used,
                }
                for name, u in self._usage.items()
            },
        }

        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_data(self) -> None:
        """Load data from file."""
        if not self.data_file or not self.data_file.exists():
            return

        with open(self.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for name, s_data in data.get("subscriptions", {}).items():
            self._subscriptions[name] = Subscription(**s_data)

        for name, u_data in data.get("usage", {}).items():
            self._usage[name] = SubscriptionUsage(**u_data)

        logger.info(f"Loaded subscription data from {self.data_file}")
