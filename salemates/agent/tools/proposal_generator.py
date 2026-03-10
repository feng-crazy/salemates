# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Proposal generator tool for creating professional sales proposals.

This tool generates sales proposals with:
- Multi-version support (A/B/C variants)
- ROI calculation and analysis
- Jinja2 template-based formatting
- Tiered solution customization
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional
import uuid

from jinja2 import Environment, BaseLoader
from loguru import logger

from salemates.agent.proposal.models import (
    Proposal,
    ProposalSection,
    ProposalVersion,
    ROICalculator,
)
from salemates.agent.tools.base import Tool, ToolContext


@dataclass
class ProductTierConfig:
    """Configuration for a product tier."""

    name: str
    base_price: float
    features: list[str]
    target_audience: str
    key_benefits: list[str]


DEFAULT_TIER_CONFIGS: dict[str, ProductTierConfig] = {
    "Basic": ProductTierConfig(
        name="Basic",
        base_price=99.0,
        features=[
            "5 users",
            "Basic analytics",
            "Email support",
            "Standard integrations",
        ],
        target_audience="Small teams and startups",
        key_benefits=[
            "Affordable entry point",
            "Quick setup",
            "Essential features",
        ],
    ),
    "Professional": ProductTierConfig(
        name="Professional",
        base_price=299.0,
        features=[
            "25 users",
            "Advanced analytics",
            "Priority support",
            "Custom integrations",
            "API access",
            "Automation workflows",
        ],
        target_audience="Growing businesses",
        key_benefits=[
            "Scalable solution",
            "Advanced capabilities",
            "Priority support",
        ],
    ),
    "Enterprise": ProductTierConfig(
        name="Enterprise",
        base_price=999.0,
        features=[
            "Unlimited users",
            "Enterprise analytics",
            "24/7 dedicated support",
            "Custom development",
            "On-premise option",
            "SSO integration",
            "Advanced security",
            "Dedicated account manager",
        ],
        target_audience="Large organizations",
        key_benefits=[
            "Enterprise-grade security",
            "Unlimited scale",
            "Custom solutions",
            "Dedicated support",
        ],
    ),
}

PROPOSAL_TEMPLATES = {
    ProposalVersion.A: """
# {{ title }}

**Proposal ID:** {{ proposal_id }}
**Customer:** {{ customer_name }}
**Product Tier:** {{ product_tier }}
**Valid Until:** {{ valid_until }}
**Version:** {{ version }}

---

## Executive Summary

{{ executive_summary }}

{% for section in sections %}
{{ section }}
{% endfor %}

{% if roi_section %}
## Return on Investment (ROI)

{{ roi_section }}
{% endif %}

## Investment Summary

**Total Investment:** ¥{{ investment_total | format_currency }}

## Next Steps

{{ next_steps }}

## Terms & Conditions

{{ terms }}
""",
    ProposalVersion.B: """
# {{ title }} - Value-Focused Proposal

**Proposal ID:** {{ proposal_id }}
**Customer:** {{ customer_name }}
**Product Tier:** {{ product_tier }}
**Valid Until:** {{ valid_until }}

---

## 🎯 Value Proposition

{{ executive_summary }}

{% for section in sections %}
{{ section }}
{% endfor %}

{% if roi_section %}
## 💰 Your Return on Investment

{{ roi_section }}

**Why This Investment Makes Sense:**
- Payback in just {{ payback_months }} months
- {{ roi_percentage }}% annual return
- Long-term value beyond the initial investment
{% endif %}

## Investment Required

**Total Investment:** ¥{{ investment_total | format_currency }}

**Flexible Payment Options Available:**
- Monthly subscription
- Annual billing (20% discount)
- Custom enterprise terms

## Ready to Get Started?

{{ next_steps }}
""",
    ProposalVersion.C: """
# {{ title }} - ROI Analysis

**Proposal ID:** {{ proposal_id }}
**Prepared for:** {{ customer_name }}
**Solution:** {{ product_tier }}
**Valid Until:** {{ valid_until }}

---

## 📊 Investment Analysis

{{ executive_summary }}

{% if roi_section %}
## ROI Breakdown

{{ roi_section }}

### Key Financial Metrics

| Metric | Value |
|--------|-------|
| **Annual Benefit** | ¥{{ annual_benefit | format_currency }} |
| **ROI** | {{ roi_percentage }}% |
| **Payback Period** | {{ payback_months }} months |
| **NPV (3-year)** | ¥{{ npv | format_currency }} |

### Why This Investment?

Based on our analysis, this solution delivers exceptional value:

1. **Quick Payback:** Recover your investment in {{ payback_months }} months
2. **Strong ROI:** {{ roi_percentage }}% return on investment
3. **Long-term Value:** Continuous benefits year over year
{% endif %}

{% for section in sections %}
{{ section }}
{% endfor %}

## Investment Summary

| Item | Amount |
|------|--------|
| **Total Investment** | ¥{{ investment_total | format_currency }} |
| **First Year Benefit** | ¥{{ annual_benefit | format_currency }} |
| **Net First Year Value** | ¥{{ net_value | format_currency }} |

## Let's Move Forward

{{ next_steps }}
""",
}


class ProposalGeneratorTool(Tool):
    """Tool for generating professional sales proposals.

    Generates proposals with:
    - Multiple version variants (A/B/C for testing)
    - ROI calculation and analysis
    - Tiered solution customization
    - Jinja2 template formatting
    """

    def __init__(
        self,
        tier_configs: Optional[dict[str, ProductTierConfig]] = None,
        proposal_validity_days: int = 30,
    ):
        """Initialize the proposal generator.

        Args:
            tier_configs: Custom tier configurations.
            proposal_validity_days: Days until proposal expires.
        """
        self._tier_configs = tier_configs or DEFAULT_TIER_CONFIGS
        self._proposal_validity_days = proposal_validity_days
        self._jinja_env = Environment(loader=BaseLoader())

    @property
    def name(self) -> str:
        return "generate_proposal"

    @property
    def description(self) -> str:
        return (
            "Generate professional sales proposals with ROI analysis. "
            "Supports multiple versions (A/B/C) for A/B testing. "
            "Returns formatted markdown proposal."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer name for the proposal",
                },
                "product_tier": {
                    "type": "string",
                    "description": "Product tier (Basic, Professional, Enterprise)",
                    "enum": ["Basic", "Professional", "Enterprise"],
                },
                "include_roi": {
                    "type": "boolean",
                    "description": "Include ROI analysis section",
                    "default": True,
                },
                "version": {
                    "type": "string",
                    "description": "Proposal version variant",
                    "enum": ["A", "B", "C"],
                    "default": "A",
                },
                "investment_amount": {
                    "type": "number",
                    "description": "Total investment amount (CNY)",
                    "minimum": 0,
                },
                "annual_savings": {
                    "type": "number",
                    "description": "Expected annual savings (CNY)",
                    "minimum": 0,
                },
                "time_saved_hours": {
                    "type": "number",
                    "description": "Hours saved per month",
                    "minimum": 0,
                },
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Customer pain points to address",
                },
                "custom_sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                    "description": "Custom sections to include",
                },
            },
            "required": ["customer_name", "product_tier"],
        }

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        """Execute the proposal generator tool.

        Args:
            tool_context: Runtime context with session info.
            **kwargs: Tool parameters.

        Returns:
            Formatted proposal markdown string.
        """
        customer_name = kwargs.get("customer_name")
        product_tier = kwargs.get("product_tier")
        include_roi = kwargs.get("include_roi", True)
        version = ProposalVersion(kwargs.get("version", "A"))
        investment_amount = kwargs.get("investment_amount", 0.0)
        annual_savings = kwargs.get("annual_savings", 0.0)
        time_saved_hours = kwargs.get("time_saved_hours", 0.0)
        pain_points = kwargs.get("pain_points", [])
        custom_sections = kwargs.get("custom_sections", [])

        try:
            tier_config = self._tier_configs.get(product_tier)
            if not tier_config:
                return f"Error: Unknown product tier '{product_tier}'"

            investment = investment_amount or tier_config.base_price * 12

            roi_calculator = None
            if include_roi:
                roi_calculator = ROICalculator(
                    investment_amount=investment,
                    annual_savings=annual_savings,
                    time_saved_hours=time_saved_hours,
                )

            proposal = self._create_proposal(
                customer_name=customer_name,
                tier_config=tier_config,
                version=version,
                investment=investment,
                roi_calculator=roi_calculator,
                pain_points=pain_points,
                custom_sections=custom_sections,
            )

            return self._render_proposal(proposal, version)

        except Exception as e:
            logger.exception(f"Proposal generator error: {e}")
            return f"Error generating proposal: {str(e)}"

    def _create_proposal(
        self,
        customer_name: str,
        tier_config: ProductTierConfig,
        version: ProposalVersion,
        investment: float,
        roi_calculator: Optional[ROICalculator],
        pain_points: list[str],
        custom_sections: list[dict],
    ) -> Proposal:
        """Create a proposal object.

        Args:
            customer_name: Customer name.
            tier_config: Product tier configuration.
            version: Proposal version.
            investment: Total investment amount.
            roi_calculator: ROI calculator instance.
            pain_points: Customer pain points.
            custom_sections: Custom sections to add.

        Returns:
            Proposal object.
        """
        proposal = Proposal(
            proposal_id=f"PROP-{uuid.uuid4().hex[:8].upper()}",
            customer_name=customer_name,
            product_tier=tier_config.name,
            version=version,
            investment_total=investment,
            roi_calculator=roi_calculator,
            valid_until=datetime.utcnow() + timedelta(days=self._proposal_validity_days),
        )

        executive_summaries = {
            ProposalVersion.A: self._generate_standard_summary(tier_config, customer_name),
            ProposalVersion.B: self._generate_value_summary(tier_config, customer_name),
            ProposalVersion.C: self._generate_roi_summary(tier_config, customer_name, investment),
        }
        proposal.executive_summary = executive_summaries[version]

        proposal.sections = self._generate_sections(
            tier_config, pain_points, custom_sections, version
        )

        proposal.next_steps = self._generate_next_steps(tier_config)
        proposal.terms = self._generate_terms()

        return proposal

    def _generate_standard_summary(self, tier_config: ProductTierConfig, customer_name: str) -> str:
        """Generate standard executive summary."""
        benefits = "\n".join(f"- {b}" for b in tier_config.key_benefits)
        return (
            f"We are pleased to present this proposal for {customer_name}'s consideration. "
            f"Our **{tier_config.name}** solution is designed specifically for "
            f"{tier_config.target_audience}.\n\n"
            f"**Key Benefits:**\n{benefits}"
        )

    def _generate_value_summary(self, tier_config: ProductTierConfig, customer_name: str) -> str:
        """Generate value-focused executive summary."""
        return (
            f"Dear {customer_name},\n\n"
            f"We understand that every investment must deliver tangible value. "
            f"Our **{tier_config.name}** solution is crafted to maximize your return "
            f"while addressing your core business needs.\n\n"
            f"This proposal outlines how we can help you achieve your goals with "
            f"measurable, lasting impact."
        )

    def _generate_roi_summary(
        self, tier_config: ProductTierConfig, customer_name: str, investment: float
    ) -> str:
        """Generate ROI-focused executive summary."""
        return (
            f"This proposal presents a comprehensive investment analysis for {customer_name}. "
            f"The **{tier_config.name}** solution at ¥{investment:,.2f} is designed to deliver "
            f"measurable returns and long-term value for {tier_config.target_audience}."
        )

    def _generate_sections(
        self,
        tier_config: ProductTierConfig,
        pain_points: list[str],
        custom_sections: list[dict],
        version: ProposalVersion,
    ) -> list[ProposalSection]:
        """Generate proposal sections."""
        sections = []

        features_content = "\n".join(f"- ✅ {f}" for f in tier_config.features)
        sections.append(
            ProposalSection(
                title="Solution Features",
                content=features_content,
                order=10,
            )
        )

        if pain_points:
            pain_content = "\n".join(f"- **{p}** - Addressed by this solution" for p in pain_points)
            sections.append(
                ProposalSection(
                    title="Addressing Your Challenges",
                    content=pain_content,
                    order=20,
                    is_highlighted=True,
                )
            )

        for i, cs in enumerate(custom_sections):
            sections.append(
                ProposalSection(
                    title=cs.get("title", f"Section {i + 1}"),
                    content=cs.get("content", ""),
                    order=30 + i,
                )
            )

        return sections

    def _generate_next_steps(self, tier_config: ProductTierConfig) -> str:
        """Generate next steps section."""
        return (
            "1. Review this proposal and discuss with your team\n"
            "2. Schedule a demo to see the solution in action\n"
            "3. Finalize terms and begin implementation\n\n"
            "**Contact us to schedule your demo today!**"
        )

    def _generate_terms(self) -> str:
        """Generate terms and conditions."""
        return (
            "- This proposal is valid for 30 days from the date of issue\n"
            "- Pricing subject to final agreement\n"
            "- Implementation timeline to be confirmed upon acceptance\n"
            "- All terms subject to final contract negotiation"
        )

    def _render_proposal(self, proposal: Proposal, version: ProposalVersion) -> str:
        """Render proposal using Jinja2 template.

        Args:
            proposal: Proposal to render.
            version: Template version to use.

        Returns:
            Rendered markdown string.
        """
        template = self._jinja_env.from_string(PROPOSAL_TEMPLATES[version])

        roi_section = ""
        roi_percentage = 0
        payback_months = 0
        annual_benefit = 0
        net_value = 0
        npv = 0

        if proposal.roi_calculator:
            roi_section = proposal._format_roi_section()
            roi_percentage = proposal.roi_calculator.calculate_roi_percentage()
            payback_months = proposal.roi_calculator.calculate_payback_months()
            annual_benefit = proposal.roi_calculator._calculate_total_annual_benefit()
            net_value = annual_benefit - proposal.investment_total
            npv = annual_benefit * 2.5 - proposal.investment_total

        def format_currency(value):
            return f"{value:,.2f}"

        sections_md = [s.to_markdown() for s in proposal.sections]

        return template.render(
            title=proposal.title,
            proposal_id=proposal.proposal_id,
            customer_name=proposal.customer_name,
            product_tier=proposal.product_tier,
            valid_until=proposal.valid_until.strftime("%Y-%m-%d")
            if proposal.valid_until
            else "N/A",
            version=proposal.version.value,
            executive_summary=proposal.executive_summary,
            sections=sections_md,
            roi_section=roi_section,
            investment_total=proposal.investment_total,
            next_steps=proposal.next_steps,
            terms=proposal.terms,
            roi_percentage=roi_percentage,
            payback_months=payback_months,
            annual_benefit=annual_benefit,
            net_value=net_value,
            npv=npv,
            format_currency=format_currency,
        )
