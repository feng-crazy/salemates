# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Data models for sales proposal generation.

This module defines the core data structures for creating professional
sales proposals including ROI calculations and multi-version support.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ProposalVersion(str, Enum):
    """Proposal version variants for A/B testing."""

    A = "A"  # Standard proposal
    B = "B"  # Value-focused proposal
    C = "C"  # ROI-focused proposal


@dataclass
class ROICalculator:
    """ROI calculator for proposal value quantification.

    Calculates return on investment metrics based on investment cost
    and expected savings/benefits.

    Attributes:
        investment_amount: Total investment required (CNY).
        annual_savings: Expected annual savings (CNY).
        time_saved_hours: Hours saved per month.
        hourly_rate: Hourly labor rate for time value calculation.
        additional_benefits: Other quantified benefits (CNY).
    """

    investment_amount: float
    annual_savings: float = 0.0
    time_saved_hours: float = 0.0
    hourly_rate: float = 200.0  # Default hourly rate in CNY
    additional_benefits: float = 0.0

    def calculate_roi_percentage(self) -> float:
        """Calculate ROI as a percentage.

        Returns:
            ROI percentage (e.g., 150.0 means 150% ROI).
        """
        if self.investment_amount <= 0:
            return 0.0

        total_annual_benefit = self._calculate_total_annual_benefit()
        roi = ((total_annual_benefit - self.investment_amount) / self.investment_amount) * 100
        return round(roi, 1)

    def calculate_payback_months(self) -> float:
        """Calculate payback period in months.

        Returns:
            Number of months to recover the investment.
        """
        total_annual_benefit = self._calculate_total_annual_benefit()
        if total_annual_benefit <= 0:
            return float("inf")

        monthly_benefit = total_annual_benefit / 12
        if monthly_benefit <= 0:
            return float("inf")

        payback_months = self.investment_amount / monthly_benefit
        return round(payback_months, 1)

    def _calculate_total_annual_benefit(self) -> float:
        """Calculate total annual benefit including all factors.

        Returns:
            Total annual benefit in CNY.
        """
        time_value = self.time_saved_hours * 12 * self.hourly_rate
        return self.annual_savings + time_value + self.additional_benefits

    def get_summary(self) -> dict:
        """Get a summary of ROI metrics.

        Returns:
            Dictionary with ROI metrics.
        """
        return {
            "investment": self.investment_amount,
            "annual_benefit": self._calculate_total_annual_benefit(),
            "roi_percentage": self.calculate_roi_percentage(),
            "payback_months": self.calculate_payback_months(),
        }


@dataclass
class ProposalSection:
    """A section within a sales proposal.

    Attributes:
        title: Section title.
        content: Section content (markdown supported).
        order: Display order (lower = earlier).
        is_highlighted: Whether this section should be emphasized.
    """

    title: str
    content: str
    order: int = 0
    is_highlighted: bool = False

    def to_markdown(self) -> str:
        """Convert section to markdown format.

        Returns:
            Markdown formatted section string.
        """
        prefix = "### " if not self.is_highlighted else "## ⭐ "
        return f"{prefix}{self.title}\n\n{self.content}\n"


@dataclass
class Proposal:
    """Complete sales proposal with sections and ROI analysis.

    Attributes:
        proposal_id: Unique identifier for the proposal.
        customer_name: Customer name.
        product_tier: Product tier (Basic, Professional, Enterprise).
        version: Proposal version (A, B, or C).
        title: Proposal title.
        executive_summary: Brief overview of the proposal.
        sections: List of proposal sections.
        investment_total: Total investment amount.
        roi_calculator: Optional ROI calculator for value quantification.
        valid_until: Proposal expiration date.
        created_at: Creation timestamp.
        terms: Terms and conditions.
        next_steps: Recommended next steps.
    """

    customer_name: str
    product_tier: str
    proposal_id: str = ""
    version: ProposalVersion = ProposalVersion.A
    title: str = ""
    executive_summary: str = ""
    sections: list[ProposalSection] = field(default_factory=list)
    investment_total: float = 0.0
    roi_calculator: Optional[ROICalculator] = None
    valid_until: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    terms: str = ""
    next_steps: str = ""

    def __post_init__(self):
        """Set default values after initialization."""
        if not self.proposal_id:
            import uuid

            self.proposal_id = f"PROP-{uuid.uuid4().hex[:8].upper()}"

        if not self.title:
            self.title = f"{self.product_tier} Solution Proposal for {self.customer_name}"

        if not self.valid_until:
            from datetime import timedelta

            self.valid_until = datetime.utcnow() + timedelta(days=30)

    def add_section(self, section: ProposalSection) -> None:
        """Add a section to the proposal.

        Args:
            section: Section to add.
        """
        self.sections.append(section)
        self.sections.sort(key=lambda s: s.order)

    def to_markdown(self) -> str:
        """Convert proposal to markdown format.

        Returns:
            Markdown formatted proposal string.
        """
        lines = [
            f"# {self.title}",
            "",
            f"**Proposal ID:** {self.proposal_id}",
            f"**Customer:** {self.customer_name}",
            f"**Product Tier:** {self.product_tier}",
            f"**Valid Until:** {self.valid_until.strftime('%Y-%m-%d') if self.valid_until else 'N/A'}",
            f"**Version:** {self.version.value}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            self.executive_summary,
            "",
        ]

        # Add sections
        for section in self.sections:
            lines.append(section.to_markdown())

        # Add ROI section if available
        if self.roi_calculator:
            lines.extend(
                [
                    "## Return on Investment (ROI)",
                    "",
                    self._format_roi_section(),
                    "",
                ]
            )

        # Add investment summary
        lines.extend(
            [
                "## Investment Summary",
                "",
                f"**Total Investment:** ¥{self.investment_total:,.2f}",
                "",
            ]
        )

        # Add next steps
        if self.next_steps:
            lines.extend(
                [
                    "## Next Steps",
                    "",
                    self.next_steps,
                    "",
                ]
            )

        # Add terms
        if self.terms:
            lines.extend(
                [
                    "## Terms & Conditions",
                    "",
                    self.terms,
                    "",
                ]
            )

        return "\n".join(lines)

    def _format_roi_section(self) -> str:
        """Format ROI section as markdown.

        Returns:
            Markdown formatted ROI section.
        """
        if not self.roi_calculator:
            return ""

        roi = self.roi_calculator.calculate_roi_percentage()
        payback = self.roi_calculator.calculate_payback_months()
        annual_benefit = self.roi_calculator._calculate_total_annual_benefit()

        return (
            f"| Metric | Value |\n"
            f"|--------|-------|\n"
            f"| **Annual Benefit** | ¥{annual_benefit:,.2f} |\n"
            f"| **ROI** | {roi}% |\n"
            f"| **Payback Period** | {payback} months |\n"
        )
