"""Revenue trend analysis with comparisons.

Provides revenue analytics including trend detection, period comparisons,
and variance analysis for CEO briefings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RevenuePoint:
    """A single revenue data point."""

    date: str
    amount: float
    currency: str = "USD"
    source: str = ""

    @property
    def date_obj(self) -> datetime:
        """Get date as datetime object."""
        return datetime.fromisoformat(self.date.replace("Z", "+00:00"))


@dataclass
class RevenueTrend:
    """Revenue trend analysis results."""

    period_start: str
    period_end: str
    total_revenue: float
    average_daily_revenue: float
    trend_direction: str  # increasing, decreasing, stable
    trend_strength: float  # 0-100
    growth_rate_pct: float
    data_points: int
    projections: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_revenue": self.total_revenue,
            "average_daily_revenue": self.average_daily_revenue,
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength,
            "growth_rate_pct": self.growth_rate_pct,
            "data_points": self.data_points,
            "projections": self.projections,
        }


@dataclass
class PeriodComparison:
    """Comparison between two periods."""

    current_period: str
    previous_period: str
    current_revenue: float
    previous_revenue: float
    absolute_change: float
    pct_change: float
    trend: str  # improved, declined, unchanged

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "current_period": self.current_period,
            "previous_period": self.previous_period,
            "current_revenue": self.current_revenue,
            "previous_revenue": self.previous_revenue,
            "absolute_change": self.absolute_change,
            "pct_change": self.pct_change,
            "trend": self.trend,
        }


class RevenueAnalyzer:
    """Analyzes revenue trends and comparisons.

    Features:
    - Trend detection (increasing, decreasing, stable)
    - Period-over-period comparisons
    - Growth rate calculations
    - Revenue projections
    """

    def __init__(self):
        """Initialize the revenue analyzer."""
        self._data_points: list[RevenuePoint] = []

    def add_data_point(self, point: RevenuePoint) -> None:
        """Add a revenue data point.

        Args:
            point: Revenue data point.
        """
        self._data_points.append(point)
        # Sort by date
        self._data_points.sort(key=lambda x: x.date_obj)

    def add_daily_revenue(
        self, date: str, amount: float, source: str = ""
    ) -> None:
        """Add daily revenue data.

        Args:
            date: Date string (YYYY-MM-DD).
            amount: Revenue amount.
            source: Optional source description.
        """
        self.add_data_point(
            RevenuePoint(date=date, amount=amount, source=source)
        )

    def analyze_trend(
        self, days: int = 30
    ) -> RevenueTrend | None:
        """Analyze revenue trend for the specified period.

        Args:
            days: Number of days to analyze.

        Returns:
            Revenue trend analysis or None if insufficient data.
        """
        if len(self._data_points) < 2:
            return None

        # Filter to specified period
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        filtered = [
            p for p in self._data_points
            if p.date_obj >= start_date
        ]

        if len(filtered) < 2:
            return None

        # Calculate metrics
        total_revenue = sum(p.amount for p in filtered)
        avg_daily = total_revenue / len(filtered)

        # Calculate trend using linear regression (simplified)
        trend_direction, trend_strength, growth_rate = self._calculate_trend(
            filtered
        )

        # Simple projection
        projection_7d = avg_daily * 7
        projection_30d = avg_daily * 30

        return RevenueTrend(
            period_start=filtered[0].date,
            period_end=filtered[-1].date,
            total_revenue=total_revenue,
            average_daily_revenue=avg_daily,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            growth_rate_pct=growth_rate,
            data_points=len(filtered),
            projections={
                "7_day": projection_7d,
                "30_day": projection_30d,
            },
        )

    def _calculate_trend(
        self, data_points: list[RevenuePoint]
    ) -> tuple[str, float, float]:
        """Calculate trend direction, strength, and growth rate.

        Args:
            data_points: List of revenue data points.

        Returns:
            Tuple of (direction, strength, growth_rate).
        """
        if len(data_points) < 2:
            return "stable", 0.0, 0.0

        # Split into first half and second half
        mid = len(data_points) // 2
        first_half_avg = sum(p.amount for p in data_points[:mid]) / mid
        second_half_avg = sum(
            p.amount for p in data_points[mid:]
        ) / (len(data_points) - mid)

        # Calculate growth rate
        if first_half_avg == 0:
            growth_rate = 0.0
        else:
            growth_rate = (
                (second_half_avg - first_half_avg) / first_half_avg
            ) * 100

        # Determine direction and strength
        if growth_rate > 10:
            direction = "increasing"
            strength = min(100, growth_rate * 2)
        elif growth_rate < -10:
            direction = "decreasing"
            strength = min(100, abs(growth_rate) * 2)
        else:
            direction = "stable"
            strength = max(0, 100 - abs(growth_rate) * 5)

        return direction, strength, growth_rate

    def compare_periods(
        self,
        current_days: int = 30,
        previous_days: int = 30,
    ) -> PeriodComparison | None:
        """Compare current period with previous period.

        Args:
            current_days: Number of days in current period.
            previous_days: Number of days in previous period.

        Returns:
            Period comparison or None if insufficient data.
        """
        now = datetime.now(timezone.utc)

        # Current period
        current_end = now
        current_start = current_end - timedelta(days=current_days)

        # Previous period
        previous_end = current_start
        previous_start = previous_end - timedelta(days=previous_days)

        current_revenue = sum(
            p.amount
            for p in self._data_points
            if current_start <= p.date_obj <= current_end
        )

        previous_revenue = sum(
            p.amount
            for p in self._data_points
            if previous_start <= p.date_obj <= previous_end
        )

        absolute_change = current_revenue - previous_revenue

        if previous_revenue == 0:
            pct_change = 0.0
        else:
            pct_change = (absolute_change / previous_revenue) * 100

        if pct_change > 5:
            trend = "improved"
        elif pct_change < -5:
            trend = "declined"
        else:
            trend = "unchanged"

        return PeriodComparison(
            current_period=f"Last {current_days} days",
            previous_period=f"Previous {previous_days} days",
            current_revenue=current_revenue,
            previous_revenue=previous_revenue,
            absolute_change=absolute_change,
            pct_change=pct_change,
            trend=trend,
        )

    def get_mtd_revenue(self) -> float:
        """Get month-to-date revenue.

        Returns:
            MTD revenue total.
        """
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        return sum(
            p.amount
            for p in self._data_points
            if p.date_obj >= month_start
        )

    def get_daily_average(self, days: int = 30) -> float:
        """Get daily average revenue.

        Args:
            days: Number of days to average.

        Returns:
            Daily average revenue.
        """
        if not self._data_points:
            return 0.0

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        filtered = [
            p for p in self._data_points if p.date_obj >= start
        ]

        if not filtered:
            return 0.0

        return sum(p.amount for p in filtered) / len(filtered)

    def get_revenue_by_source(
        self, days: int = 30
    ) -> dict[str, float]:
        """Get revenue breakdown by source.

        Args:
            days: Number of days to analyze.

        Returns:
            Dictionary mapping sources to revenue amounts.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        breakdown: dict[str, float] = {}

        for point in self._data_points:
            if point.date_obj >= start:
                source = point.source or "Unknown"
                breakdown[source] = breakdown.get(source, 0) + point.amount

        return breakdown

    def clear_data(self) -> None:
        """Clear all revenue data."""
        self._data_points.clear()
        logger.info("Revenue data cleared")

    def export_summary(self) -> dict[str, Any]:
        """Export revenue summary.

        Returns:
            Dictionary with revenue summary.
        """
        trend = self.analyze_trend()
        comparison = self.compare_periods()

        return {
            "mtd_revenue": self.get_mtd_revenue(),
            "daily_average": self.get_daily_average(),
            "by_source": self.get_revenue_by_source(),
            "trend": trend.to_dict() if trend else None,
            "comparison": comparison.to_dict() if comparison else None,
        }
