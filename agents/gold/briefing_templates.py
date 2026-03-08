"""Briefing templates for different business types.

Provides customizable CEO briefing templates for service-based,
product-based, and freelance business models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import Protocol


@unique
class TemplateType(Enum):
    """Briefing template types."""

    SERVICE = "service"
    PRODUCT = "product"
    FREELANCE = "freelance"
    SAAS = "saas"
    ECOMMERCE = "ecommerce"


class BriefingTemplate(Protocol):
    """Protocol for briefing templates."""

    def render(self, data: dict) -> str: ...
    def get_metrics(self) -> list[str]: ...


@dataclass
class ServiceBusinessTemplate:
    """Template for service-based businesses (agencies, consultants)."""

    name: str = "Service Business"

    def render(self, data: dict) -> str:
        """Render briefing for service business.

        Args:
            data: Briefing data dict.

        Returns:
            Markdown-formatted briefing.
        """
        lines = [
            f"# CEO Briefing — {data.get('briefing_id', 'Weekly')}",
            "",
            f"**Period**: {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}",
            "",
            "## Key Service Metrics",
            "",
            f"- **Billable Hours**: {data.get('billable_hours', 'N/A')}",
            f"- **Utilization Rate**: {data.get('utilization_rate', 'N/A')}%",
            f"- **Active Clients**: {data.get('active_clients', 'N/A')}",
            f"- **Pipeline Value**: ${data.get('pipeline_value', 'N/A'):,.2f}",
            "",
            "## Revenue",
            "",
            f"- **MTD Revenue**: ${data.get('revenue_mtd', 'N/A'):,.2f}",
            f"- **vs Goal**: {data.get('revenue_delta_pct', 'N/A')}%",
            "",
            "## Resource Allocation",
            "",
        ]

        if data.get('team_utilization'):
            for member, util in data['team_utilization'].items():
                status = "🟢" if util >= 80 else ("🟡" if util >= 60 else "🔴")
                lines.append(f"- {status} {member}: {util}%")
        else:
            lines.append("- Team utilization data unavailable")

        return "\n".join(lines)

    def get_metrics(self) -> list[str]:
        """Get list of metrics for this template."""
        return [
            "billable_hours",
            "utilization_rate",
            "active_clients",
            "pipeline_value",
            "revenue_mtd",
            "revenue_delta_pct",
            "team_utilization",
        ]


@dataclass
class ProductBusinessTemplate:
    """Template for product-based businesses (SaaS, physical products)."""

    name: str = "Product Business"

    def render(self, data: dict) -> str:
        """Render briefing for product business.

        Args:
            data: Briefing data dict.

        Returns:
            Markdown-formatted briefing.
        """
        lines = [
            f"# CEO Briefing — {data.get('briefing_id', 'Weekly')}",
            "",
            f"**Period**: {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}",
            "",
            "## Key Product Metrics",
            "",
            f"- **MRR**: ${data.get('mrr', 'N/A'):,.2f}",
            f"- **ARR**: ${data.get('arr', 'N/A'):,.2f}",
            f"- **Active Users**: {data.get('active_users', 'N/A'):,}",
            f"- **Churn Rate**: {data.get('churn_rate', 'N/A')}%",
            f"- **CAC**: ${data.get('cac', 'N/A'):,.2f}",
            f"- **LTV**: ${data.get('ltv', 'N/A'):,.2f}",
            "",
            "## Revenue",
            "",
            f"- **MTD Revenue**: ${data.get('revenue_mtd', 'N/A'):,.2f}",
            f"- **vs Goal**: {data.get('revenue_delta_pct', 'N/A')}%",
            "",
            "## Growth Indicators",
            "",
        ]

        # Growth indicators
        mrr_growth = data.get('mrr_growth_pct')
        if mrr_growth is not None:
            indicator = "🟢" if mrr_growth > 5 else ("🟡" if mrr_growth > 0 else "🔴")
            lines.append(f"- {indicator} MRR Growth: {mrr_growth:+.1f}%")

        user_growth = data.get('user_growth_pct')
        if user_growth is not None:
            indicator = "🟢" if user_growth > 10 else ("🟡" if user_growth > 0 else "🔴")
            lines.append(f"- {indicator} User Growth: {user_growth:+.1f}%")

        return "\n".join(lines)

    def get_metrics(self) -> list[str]:
        """Get list of metrics for this template."""
        return [
            "mrr",
            "arr",
            "active_users",
            "churn_rate",
            "cac",
            "ltv",
            "revenue_mtd",
            "revenue_delta_pct",
            "mrr_growth_pct",
            "user_growth_pct",
        ]


@dataclass
class FreelanceTemplate:
    """Template for freelance/sole proprietor businesses."""

    name: str = "Freelance"

    def render(self, data: dict) -> str:
        """Render briefing for freelance business.

        Args:
            data: Briefing data dict.

        Returns:
            Markdown-formatted briefing.
        """
        lines = [
            f"# Weekly Briefing — {data.get('briefing_id', 'Freelancer')}",
            "",
            f"**Period**: {data.get('period_start', 'N/A')} to {data.get('period_end', 'N/A')}",
            "",
            "## This Week's Focus",
            "",
            f"- **Income**: ${data.get('weekly_income', 'N/A'):,.2f}",
            f"- **Hours Worked**: {data.get('hours_worked', 'N/A')}",
            f"- **Effective Rate**: ${data.get('effective_rate', 'N/A'):,.2f}/hr",
            "",
            "## Pipeline",
            "",
            f"- **Active Projects**: {data.get('active_projects', 'N/A')}",
            f"- **Proposals Sent**: {data.get('proposals_sent', 'N/A')}",
            f"- **Pipeline Value**: ${data.get('pipeline_value', 'N/A'):,.2f}",
            "",
            "## Revenue",
            "",
            f"- **MTD Revenue**: ${data.get('revenue_mtd', 'N/A'):,.2f}",
            f"- **Monthly Goal**: ${data.get('revenue_goal', 'N/A'):,.2f}",
            f"- **vs Goal**: {data.get('revenue_delta_pct', 'N/A')}%",
            "",
            "## Action Items",
            "",
        ]

        # Add action items based on data
        if data.get('follow_ups'):
            lines.append("**Follow-ups Needed:**")
            for followup in data['follow_ups']:
                lines.append(f"- {followup}")

        if data.get('invoices_pending'):
            lines.append(f"\n**Invoices Pending**: {data['invoices_pending']}")

        return "\n".join(lines)

    def get_metrics(self) -> list[str]:
        """Get list of metrics for this template."""
        return [
            "weekly_income",
            "hours_worked",
            "effective_rate",
            "active_projects",
            "proposals_sent",
            "pipeline_value",
            "revenue_mtd",
            "revenue_goal",
            "revenue_delta_pct",
            "follow_ups",
            "invoices_pending",
        ]


class BriefingTemplateFactory:
    """Factory for creating briefing templates."""

    _templates: dict[TemplateType, BriefingTemplate] = {
        TemplateType.SERVICE: ServiceBusinessTemplate(),
        TemplateType.PRODUCT: ProductBusinessTemplate(),
        TemplateType.FREELANCE: FreelanceTemplate(),
    }

    @classmethod
    def get_template(cls, template_type: TemplateType) -> BriefingTemplate:
        """Get template by type.

        Args:
            template_type: Type of template needed.

        Returns:
            BriefingTemplate instance.

        Raises:
            ValueError: If template type not found.
        """
        template = cls._templates.get(template_type)
        if template is None:
            raise ValueError(f"Unknown template type: {template_type}")
        return template

    @classmethod
    def register_template(
        cls,
        template_type: TemplateType,
        template: BriefingTemplate,
    ) -> None:
        """Register a custom template.

        Args:
            template_type: Type identifier.
            template: Template instance.
        """
        cls._templates[template_type] = template

    @classmethod
    def list_templates(cls) -> list[str]:
        """List available template types.

        Returns:
            List of template type names.
        """
        return [t.value for t in cls._templates.keys()]


def create_briefing_with_template(
    template_type: TemplateType,
    data: dict,
) -> str:
    """Create a briefing using the specified template.

    Args:
        template_type: Type of template to use.
        data: Briefing data.

    Returns:
        Rendered briefing markdown.
    """
    template = BriefingTemplateFactory.get_template(template_type)
    return template.render(data)
