"""Competitor tool for retrieving competitor info and generating value comparisons.

This tool provides:
- Competitor information retrieval from OpenViking knowledge base
- Value comparisons between our products and competitors
- Guardrail enforcement to prevent false claims
"""

from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger

from salemates.agent.safety.guardrails import (
    CompetitorGuardrail,
    CompetitorGuardrailConfig,
    GuardrailManager,
    GuardrailViolation,
    ViolationSeverity,
)
from salemates.agent.tools.base import Tool, ToolContext


@dataclass
class CompetitorInfo:
    """Information about a competitor.

    Attributes:
        name: Competitor name.
        strengths: Known strengths of the competitor.
        weaknesses: Known weaknesses or gaps.
        pricing_tier: Relative pricing (budget, mid-market, premium).
        target_market: Primary target market.
        key_differentiators: Key differentiating factors.
        verified: Whether info is verified from reliable sources.
    """

    name: str
    strengths: list[str]
    weaknesses: list[str]
    pricing_tier: str
    target_market: str
    key_differentiators: list[str]
    verified: bool = True


@dataclass
class ValueComparison:
    """Comparison between our product and a competitor.

    Attributes:
        competitor_name: Name of the competitor.
        our_advantages: Areas where we have an advantage.
        competitor_advantages: Areas where competitor excels.
        value_propositions: Key value propositions to emphasize.
        recommended_positioning: How to position against this competitor.
        factual_claims: Only verified factual claims.
    """

    competitor_name: str
    our_advantages: list[str]
    competitor_advantages: list[str]
    value_propositions: list[str]
    recommended_positioning: str
    factual_claims: list[str]


class CompetitorTool(Tool):
    """Tool for competitor information and value comparisons.

    Retrieves competitor information from OpenViking knowledge base and
    generates factual comparisons while enforcing the CompetitorGuardrail
    to prevent false or unverified claims.

    Attributes:
        _guardrail_manager: GuardrailManager for competitor content validation.
        _competitor_names: List of known competitor names.
    """

    # Default competitor database (would be loaded from OpenViking in production)
    DEFAULT_COMPETITORS: dict[str, CompetitorInfo] = {
        "CompetitorA": CompetitorInfo(
            name="CompetitorA",
            strengths=[
                "Strong brand recognition",
                "Large enterprise customer base",
                "Comprehensive feature set",
            ],
            weaknesses=[
                "Higher pricing",
                "Complex implementation",
                "Longer time to value",
            ],
            pricing_tier="premium",
            target_market="Large enterprises",
            key_differentiators=[
                "Enterprise focus",
                "On-premise deployment",
                "Custom development",
            ],
            verified=True,
        ),
        "CompetitorB": CompetitorInfo(
            name="CompetitorB",
            strengths=[
                "Lower price point",
                "Quick setup",
                "Simple interface",
            ],
            weaknesses=[
                "Limited features",
                "No enterprise support",
                "Basic analytics only",
            ],
            pricing_tier="budget",
            target_market="SMBs and startups",
            key_differentiators=[
                "Self-service model",
                "Template-based workflows",
                "Community support",
            ],
            verified=True,
        ),
        "CompetitorC": CompetitorInfo(
            name="CompetitorC",
            strengths=[
                "Industry-specific solutions",
                "Strong integration ecosystem",
                "Good customer support",
            ],
            weaknesses=[
                "Niche market focus",
                "Limited scalability",
                "Higher total cost of ownership",
            ],
            pricing_tier="mid-market",
            target_market="Industry verticals",
            key_differentiators=[
                "Industry templates",
                "Compliance features",
                "Partner network",
            ],
            verified=True,
        ),
    }

    def __init__(
        self,
        competitor_names: Optional[list[str]] = None,
        use_openviking: bool = True,
    ):
        """Initialize the competitor tool.

        Args:
            competitor_names: Custom list of competitor names to track.
            use_openviking: Whether to use OpenViking for competitor info.
        """
        self._use_openviking = use_openviking
        self._competitor_names = competitor_names or list(self.DEFAULT_COMPETITORS.keys())

        # Initialize guardrail manager with competitor guardrail
        config = CompetitorGuardrailConfig(competitor_names=self._competitor_names)
        self._guardrail_manager = GuardrailManager()
        self._guardrail_manager.add_guardrail(CompetitorGuardrail(config=config))

    @property
    def name(self) -> str:
        return "competitor_info"

    @property
    def description(self) -> str:
        return (
            "Retrieve competitor information and generate value comparisons. "
            "Actions: get_info, compare, list_competitors. Enforces factual "
            "accuracy and prevents false claims."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["get_info", "compare", "list_competitors"],
                },
                "competitor_name": {
                    "type": "string",
                    "description": "Name of the competitor",
                },
                "focus_area": {
                    "type": "string",
                    "description": "Specific area to focus comparison on",
                },
            },
            "required": ["action"],
        }

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        """Execute the competitor tool.

        Args:
            tool_context: Runtime context with session info.
            **kwargs: Tool parameters including action and competitor details.

        Returns:
            Formatted competitor information or comparison.
        """
        action = kwargs.get("action")
        competitor_name = kwargs.get("competitor_name")
        focus_area = kwargs.get("focus_area")

        try:
            if action == "get_info":
                return await self._get_competitor_info(competitor_name)
            elif action == "compare":
                return await self._compare_with_competitor(competitor_name, focus_area)
            elif action == "list_competitors":
                return self._list_competitors()
            else:
                return f"Error: Unknown action: {action}"
        except Exception as e:
            logger.exception(f"Competitor tool error: {e}")
            return f"Error executing {action}: {str(e)}"

    async def _get_competitor_info(self, competitor_name: Optional[str]) -> str:
        """Retrieve information about a competitor.

        Args:
            competitor_name: Name of the competitor.

        Returns:
            Formatted competitor information.
        """
        if not competitor_name:
            return "Error: competitor_name is required"

        # Get competitor info (from OpenViking or default database)
        info = await self._fetch_competitor_info(competitor_name)

        if not info:
            return f"No information found for competitor: {competitor_name}"

        # Format the information
        lines = [
            f"📊 Competitor Profile: {info.name}",
            "",
            f"  💰 Pricing Tier: {info.pricing_tier}",
            f"  🎯 Target Market: {info.target_market}",
            "",
            "  ✅ Strengths:",
        ]

        for strength in info.strengths:
            lines.append(f"    • {strength}")

        lines.append("")
        lines.append("  ⚠️ Weaknesses:")

        for weakness in info.weaknesses:
            lines.append(f"    • {weakness}")

        lines.append("")
        lines.append("  🔑 Key Differentiators:")

        for diff in info.key_differentiators:
            lines.append(f"    • {diff}")

        if not info.verified:
            lines.append("")
            lines.append("  ⚠️ Note: This information has not been verified from primary sources.")

        return "\n".join(lines)

    async def _compare_with_competitor(
        self, competitor_name: Optional[str], focus_area: Optional[str]
    ) -> str:
        """Generate a value comparison against a competitor.

        Args:
            competitor_name: Name of the competitor.
            focus_area: Optional specific area to focus on.

        Returns:
            Formatted comparison with recommended positioning.
        """
        if not competitor_name:
            return "Error: competitor_name is required"

        # Get competitor info
        info = await self._fetch_competitor_info(competitor_name)

        if not info:
            return f"No information found for competitor: {competitor_name}"

        # Generate comparison
        comparison = self._create_comparison(info, focus_area)

        # Validate with guardrails
        validated_response = self._validate_comparison(comparison)

        # Format the comparison
        lines = [
            f"⚖️ Value Comparison: Us vs {competitor_name}",
            "",
            "  🏆 Our Advantages:",
        ]

        for adv in validated_response.our_advantages:
            lines.append(f"    ✓ {adv}")

        lines.append("")
        lines.append(f"  📈 {competitor_name} Advantages:")

        for adv in validated_response.competitor_advantages:
            lines.append(f"    • {adv}")

        lines.append("")
        lines.append("  💡 Value Propositions to Emphasize:")

        for vp in validated_response.value_propositions:
            lines.append(f"    → {vp}")

        lines.append("")
        lines.append("  🎯 Recommended Positioning:")
        lines.append(f"    {validated_response.recommended_positioning}")

        if validated_response.factual_claims:
            lines.append("")
            lines.append("  ✅ Verified Factual Claims:")
            for claim in validated_response.factual_claims:
                lines.append(f"    • {claim}")

        return "\n".join(lines)

    def _list_competitors(self) -> str:
        """List all tracked competitors.

        Returns:
            Formatted list of competitors.
        """
        lines = [
            "📋 Tracked Competitors:",
            "",
        ]

        for name, info in self.DEFAULT_COMPETITORS.items():
            verification = "✓" if info.verified else "?"
            lines.append(
                f"  {verification} {name} - {info.pricing_tier} tier, {info.target_market}"
            )

        lines.append("")
        lines.append("Use 'get_info' action to see details for a specific competitor.")
        lines.append("Use 'compare' action to generate value comparisons.")

        return "\n".join(lines)

    async def _fetch_competitor_info(self, competitor_name: str) -> Optional[CompetitorInfo]:
        """Fetch competitor information from OpenViking or default database.

        Args:
            competitor_name: Name of the competitor.

        Returns:
            CompetitorInfo if found, None otherwise.
        """
        # Try default database first
        if competitor_name in self.DEFAULT_COMPETITORS:
            return self.DEFAULT_COMPETITORS[competitor_name]

        # Check for case-insensitive match
        for name, info in self.DEFAULT_COMPETITORS.items():
            if name.lower() == competitor_name.lower():
                return info

        # TODO: Query OpenViking for competitor info when available
        # if self._use_openviking:
        #     # Query OpenViking knowledge base
        #     pass

        return None

    def _create_comparison(
        self, competitor: CompetitorInfo, focus_area: Optional[str]
    ) -> ValueComparison:
        """Create a value comparison against a competitor.

        Args:
            competitor: Competitor information.
            focus_area: Optional focus area for comparison.

        Returns:
            ValueComparison object.
        """
        # Generate advantages based on competitor weaknesses
        our_advantages = []
        for weakness in competitor.weaknesses:
            if "pricing" in weakness.lower() or "price" in weakness.lower():
                our_advantages.append("Competitive pricing with transparent plans")
            elif "implementation" in weakness.lower():
                our_advantages.append("Quick implementation with minimal setup time")
            elif "support" in weakness.lower():
                our_advantages.append("Responsive support with dedicated account managers")
            elif "feature" in weakness.lower():
                our_advantages.append("Rich feature set that scales with your needs")
            elif "scalability" in weakness.lower():
                our_advantages.append("Built to scale from startup to enterprise")

        # Default advantages if none matched
        if not our_advantages:
            our_advantages = [
                "Flexible deployment options (cloud and on-premise)",
                "Intuitive user interface with minimal learning curve",
                "Strong ROI with quick time to value",
            ]

        # Value propositions based on competitor positioning
        value_props = []
        if competitor.pricing_tier == "premium":
            value_props.extend(
                [
                    "Get enterprise-grade features at a fraction of the cost",
                    "Lower total cost of ownership over time",
                    "Flexible pricing that grows with your business",
                ]
            )
        elif competitor.pricing_tier == "budget":
            value_props.extend(
                [
                    "More features and capabilities for serious businesses",
                    "Enterprise-grade security and compliance",
                    "Dedicated support when you need it",
                ]
            )
        else:
            value_props.extend(
                [
                    "Best-in-class balance of features and value",
                    "Industry-leading customer satisfaction",
                    "Proven track record with similar customers",
                ]
            )

        # Positioning recommendation
        positioning = self._get_positioning(competitor)

        # Only include verified factual claims
        factual_claims = []
        if competitor.verified:
            factual_claims = [
                f"{competitor.name} is positioned as a {competitor.pricing_tier} solution",
                f"Their primary focus is {competitor.target_market}",
            ]

        return ValueComparison(
            competitor_name=competitor.name,
            our_advantages=our_advantages,
            competitor_advantages=competitor.strengths,
            value_propositions=value_props,
            recommended_positioning=positioning,
            factual_claims=factual_claims,
        )

    def _get_positioning(self, competitor: CompetitorInfo) -> str:
        """Get recommended positioning against a competitor.

        Args:
            competitor: Competitor information.

        Returns:
            Recommended positioning statement.
        """
        if competitor.pricing_tier == "premium":
            return (
                f"Position on value and ROI. Emphasize that {competitor.name} may have "
                "more features but at a significantly higher cost. Focus on our "
                "superior value proposition and faster time to value."
            )
        elif competitor.pricing_tier == "budget":
            return (
                f"Position on capability and support. {competitor.name} may be cheaper "
                "but lacks enterprise features and support. Focus on our ability to "
                "scale with their business and provide dedicated support."
            )
        else:
            return (
                f"Position on differentiation. {competitor.name} targets similar customers. "
                "Focus on our unique strengths and specific success stories from "
                "customers who switched from them."
            )

    def _validate_comparison(self, comparison: ValueComparison) -> ValueComparison:
        """Validate comparison with guardrails.

        Args:
            comparison: Value comparison to validate.

        Returns:
            Validated comparison with only approved content.
        """
        # Check each value proposition for guardrail violations
        validated_props = []
        for prop in comparison.value_propositions:
            violations = self._guardrail_manager.check(prop)
            if not any(v.severity == ViolationSeverity.BLOCK for v in violations):
                validated_props.append(prop)
            else:
                logger.warning(f"Value proposition blocked by guardrail: {prop}")

        # If all props were blocked, add a generic one
        if not validated_props:
            validated_props = ["We offer excellent value for your specific needs"]

        # Update comparison with validated content
        comparison.value_propositions = validated_props

        return comparison

    def get_tracked_competitors(self) -> list[str]:
        """Get list of tracked competitor names.

        Returns:
            List of competitor names.
        """
        return self._competitor_names.copy()

    def add_competitor(self, name: str, info: Optional[CompetitorInfo] = None) -> None:
        """Add a new competitor to track.

        Args:
            name: Competitor name.
            info: Optional competitor information.
        """
        if name not in self._competitor_names:
            self._competitor_names.append(name)

        if info:
            self.DEFAULT_COMPETITORS[name] = info
