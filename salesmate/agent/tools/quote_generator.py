"""Quote generator tool for creating price quotes with guardrail enforcement.

This tool generates price quotes while enforcing:
- Maximum discount limits (PriceGuardrail)
- Tiered pricing based on customer segment
- Volume discounts within authorized limits
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from loguru import logger

from salesmate.agent.safety.guardrails import (
    GuardrailManager,
    GuardrailViolation,
    PriceGuardrail,
    ViolationSeverity,
)
from salesmate.agent.tools.base import Tool, ToolContext


@dataclass
class PricingTier:
    """Pricing tier configuration.

    Attributes:
        name: Tier name (e.g., "Basic", "Professional", "Enterprise").
        base_price: Base price per unit/month.
        features: List of features included.
        min_units: Minimum units for this tier.
    """

    name: str
    base_price: float
    features: list[str]
    min_units: int = 1


@dataclass
class QuoteItem:
    """Individual quote line item.

    Attributes:
        name: Item name.
        quantity: Number of units.
        unit_price: Price per unit.
        discount_percent: Applied discount percentage.
        subtotal: Line total after discount.
    """

    name: str
    quantity: int
    unit_price: float
    discount_percent: float
    subtotal: float


@dataclass
class Quote:
    """Complete price quote.

    Attributes:
        quote_id: Unique quote identifier.
        customer_name: Customer name.
        items: List of quote items.
        subtotal: Total before discount.
        discount_total: Total discount amount.
        final_total: Final amount after discount.
        valid_until: Quote expiration date.
        notes: Additional notes.
        violations: Any guardrail violations detected.
    """

    quote_id: str
    customer_name: str
    items: list[QuoteItem]
    subtotal: float
    discount_total: float
    final_total: float
    valid_until: datetime
    notes: str
    violations: list[GuardrailViolation]


class QuoteGeneratorTool(Tool):
    """Tool for generating price quotes with guardrail enforcement.

    Generates professional quotes while enforcing pricing policies:
    - Maximum discount limits via PriceGuardrail
    - Tiered pricing based on customer segment
    - Volume discounts within authorized limits
    - Automatic approval workflow for quotes within limits

    Attributes:
        _max_discount_percent: Maximum allowed discount percentage.
        _guardrail_manager: GuardrailManager for price validation.
        _pricing_tiers: Available pricing tiers.
    """

    # Default pricing tiers
    DEFAULT_TIERS: list[PricingTier] = [
        PricingTier(
            name="Basic",
            base_price=99.0,
            features=[
                "5 users",
                "Basic analytics",
                "Email support",
                "Standard integrations",
            ],
            min_units=1,
        ),
        PricingTier(
            name="Professional",
            base_price=299.0,
            features=[
                "25 users",
                "Advanced analytics",
                "Priority support",
                "Custom integrations",
                "API access",
            ],
            min_units=5,
        ),
        PricingTier(
            name="Enterprise",
            base_price=999.0,
            features=[
                "Unlimited users",
                "Enterprise analytics",
                "24/7 dedicated support",
                "Custom development",
                "On-premise option",
                "SSO integration",
            ],
            min_units=10,
        ),
    ]

    def __init__(
        self,
        max_discount_percent: float = 15.0,
        pricing_tiers: Optional[list[PricingTier]] = None,
        quote_validity_days: int = 30,
    ):
        """Initialize the quote generator tool.

        Args:
            max_discount_percent: Maximum allowed discount percentage (default: 15%).
            pricing_tiers: Custom pricing tiers (uses defaults if not provided).
            quote_validity_days: Number of days quotes are valid (default: 30).
        """
        self._max_discount_percent = max_discount_percent
        self._pricing_tiers = pricing_tiers or self.DEFAULT_TIERS
        self._quote_validity_days = quote_validity_days

        # Initialize guardrail manager with price guardrail
        self._guardrail_manager = GuardrailManager()
        self._guardrail_manager.add_guardrail(
            PriceGuardrail(max_discount_percent=max_discount_percent)
        )

    @property
    def name(self) -> str:
        return "generate_quote"

    @property
    def description(self) -> str:
        return (
            "Generate price quotes for customers. Enforces maximum discount limits "
            "and provides tiered pricing options. Returns formatted quote card."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer name for the quote",
                },
                "product_tier": {
                    "type": "string",
                    "description": "Product tier (Basic, Professional, Enterprise)",
                    "enum": ["Basic", "Professional", "Enterprise"],
                },
                "units": {
                    "type": "integer",
                    "description": "Number of units/seats",
                    "minimum": 1,
                },
                "requested_discount": {
                    "type": "number",
                    "description": "Requested discount percentage (0-100)",
                    "minimum": 0,
                    "maximum": 100,
                },
                "billing_cycle": {
                    "type": "string",
                    "description": "Billing cycle",
                    "enum": ["monthly", "annual"],
                    "default": "monthly",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes for the quote",
                },
            },
            "required": ["customer_name", "product_tier", "units"],
        }

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        """Execute the quote generator tool.

        Args:
            tool_context: Runtime context with session info.
            **kwargs: Tool parameters including customer and product details.

        Returns:
            Formatted quote card string.
        """
        customer_name = kwargs.get("customer_name")
        product_tier = kwargs.get("product_tier")
        units = kwargs.get("units", 1)
        requested_discount = kwargs.get("requested_discount", 0)
        billing_cycle = kwargs.get("billing_cycle", "monthly")
        notes = kwargs.get("notes", "")

        try:
            # Find the pricing tier
            tier = self._get_tier(product_tier)
            if not tier:
                return f"Error: Unknown product tier '{product_tier}'"

            # Calculate discount with guardrail enforcement
            actual_discount, violations = self._calculate_discount(requested_discount)

            # Calculate pricing
            quote = self._create_quote(
                customer_name=customer_name,
                tier=tier,
                units=units,
                discount=actual_discount,
                billing_cycle=billing_cycle,
                notes=notes,
                violations=violations,
            )

            return self._format_quote(quote)
        except Exception as e:
            logger.exception(f"Quote generator error: {e}")
            return f"Error generating quote: {str(e)}"

    def _get_tier(self, tier_name: str) -> Optional[PricingTier]:
        """Get pricing tier by name.

        Args:
            tier_name: Name of the tier to find.

        Returns:
            PricingTier if found, None otherwise.
        """
        for tier in self._pricing_tiers:
            if tier.name.lower() == tier_name.lower():
                return tier
        return None

    def _calculate_discount(
        self, requested_discount: float
    ) -> tuple[float, list[GuardrailViolation]]:
        """Calculate actual discount with guardrail enforcement.

        Args:
            requested_discount: Requested discount percentage.

        Returns:
            Tuple of (actual_discount, violations).
        """
        violations: list[GuardrailViolation] = []

        # Check discount against guardrail
        test_text = f"申请 {requested_discount}% 折扣"
        violations = self._guardrail_manager.check(test_text)

        # Determine actual discount
        if any(v.severity == ViolationSeverity.BLOCK for v in violations):
            # Hard block - use max discount
            actual_discount = self._max_discount_percent
            logger.warning(
                f"Discount {requested_discount}% blocked, using max {self._max_discount_percent}%"
            )
        elif any(v.severity == ViolationSeverity.WARNING for v in violations):
            # Warning - cap at max
            actual_discount = min(requested_discount, self._max_discount_percent)
        else:
            actual_discount = requested_discount

        return actual_discount, violations

    def _create_quote(
        self,
        customer_name: str,
        tier: PricingTier,
        units: int,
        discount: float,
        billing_cycle: str,
        notes: str,
        violations: list[GuardrailViolation],
    ) -> Quote:
        """Create a quote object.

        Args:
            customer_name: Customer name.
            tier: Pricing tier.
            units: Number of units.
            discount: Applied discount percentage.
            billing_cycle: Billing cycle (monthly/annual).
            notes: Additional notes.
            violations: Guardrail violations detected.

        Returns:
            Quote object.
        """
        import uuid

        # Calculate pricing
        unit_price = tier.base_price
        if billing_cycle == "annual":
            # 20% discount for annual billing
            unit_price = unit_price * 12 * 0.8

        subtotal = unit_price * units
        discount_amount = subtotal * (discount / 100)
        final_total = subtotal - discount_amount

        # Create quote item
        item = QuoteItem(
            name=f"{tier.name} Plan ({billing_cycle})",
            quantity=units,
            unit_price=unit_price,
            discount_percent=discount,
            subtotal=final_total,
        )

        # Calculate validity date
        from datetime import timedelta

        valid_until = datetime.utcnow() + timedelta(days=self._quote_validity_days)

        return Quote(
            quote_id=f"QT-{uuid.uuid4().hex[:8].upper()}",
            customer_name=customer_name,
            items=[item],
            subtotal=subtotal,
            discount_total=discount_amount,
            final_total=final_total,
            valid_until=valid_until,
            notes=notes,
            violations=violations,
        )

    def _format_quote(self, quote: Quote) -> str:
        """Format quote for display.

        Args:
            quote: Quote to format.

        Returns:
            Formatted quote card string.
        """
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            "║                    💰 PRICE QUOTE                        ║",
            "╠══════════════════════════════════════════════════════════╣",
            f"║  Quote ID: {quote.quote_id:<43}║",
            f"║  Customer: {quote.customer_name:<43}║",
            f"║  Valid Until: {quote.valid_until.strftime('%Y-%m-%d'):<40}║",
            "╠══════════════════════════════════════════════════════════╣",
            "║  LINE ITEMS                                              ║",
            "╟──────────────────────────────────────────────────────────╢",
        ]

        for item in quote.items:
            lines.extend(
                [
                    f"║  {item.name:<54}║",
                    f"║    Qty: {item.quantity:<5}  Unit Price: ¥{item.unit_price:,.2f}{'':>20}║",
                    f"║    Discount: {item.discount_percent}%{'':>42}║",
                    f"║    Subtotal: ¥{item.subtotal:,.2f}{'':>36}║",
                ]
            )

        lines.extend(
            [
                "╟──────────────────────────────────────────────────────────╢",
                f"║  Subtotal:          ¥{quote.subtotal:,.2f}{'':>26}║",
                f"║  Discount Applied:  ¥{quote.discount_total:,.2f}{'':>26}║",
                "╟──────────────────────────────────────────────────────────╢",
                f"║  💵 FINAL TOTAL:    ¥{quote.final_total:,.2f}{'':>26}║",
                "╚══════════════════════════════════════════════════════════╝",
            ]
        )

        # Add violation warnings if any
        if quote.violations:
            lines.append("")
            lines.append("⚠️  PRICING POLICY NOTICES:")
            for v in quote.violations:
                lines.append(f"  • {v.message}")

        # Add tier features
        if quote.items:
            tier = self._get_tier_from_item(quote.items[0])
            if tier:
                lines.append("")
                lines.append("📦 INCLUDED FEATURES:")
                for feature in tier.features:
                    lines.append(f"  ✓ {feature}")

        # Add notes if any
        if quote.notes:
            lines.append("")
            lines.append(f"📝 Notes: {quote.notes}")

        return "\n".join(lines)

    def _get_tier_from_item(self, item: QuoteItem) -> Optional[PricingTier]:
        """Get pricing tier from quote item name.

        Args:
            item: Quote item.

        Returns:
            PricingTier if found, None otherwise.
        """
        for tier in self._pricing_tiers:
            if tier.name.lower() in item.name.lower():
                return tier
        return None

    def get_available_tiers(self) -> list[dict[str, Any]]:
        """Get available pricing tiers.

        Returns:
            List of tier information dictionaries.
        """
        return [
            {
                "name": tier.name,
                "base_price": tier.base_price,
                "features": tier.features,
                "min_units": tier.min_units,
            }
            for tier in self._pricing_tiers
        ]

    def get_max_discount(self) -> float:
        """Get the maximum allowed discount percentage.

        Returns:
            Maximum discount percentage.
        """
        return self._max_discount_percent
