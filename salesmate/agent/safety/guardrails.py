# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Safety guardrails for sales agent responses.

Prevents unauthorized commitments and policy violations:
- Price guardrail: Block unauthorized discounts
- Contract guardrail: Block contract commitments without approval
- Feature guardrail: Prevent claims about unverified features
- Competitor guardrail: Prevent false competitor comparisons

Example:
    >>> manager = GuardrailManager()
    >>> manager.add_guardrail(PriceGuardrail(max_discount_percent=15))
    >>> violations = manager.check("我可以给你20%折扣")
    >>> print(violations[0].type)
    GuardrailType.PRICE
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GuardrailType(str, Enum):
    """Type of guardrail violation.

    Each type corresponds to a different category of business risk.
    """

    PRICE = "price"  # Unauthorized pricing/discount commitments
    CONTRACT = "contract"  # Unauthorized contract terms
    FEATURE = "feature"  # Claims about unverified features
    COMPETITOR = "competitor"  # False or risky competitor comparisons

    def __str__(self) -> str:
        """Return the string value of the guardrail type."""
        return self.value


class ViolationSeverity(str, Enum):
    """Severity level for guardrail violations.

    Determines the action taken when a violation is detected.
    """

    WARNING = "warning"  # Soft alert - warn but allow
    BLOCK = "block"  # Hard block - prevent response
    REVIEW = "review"  # Flag for human review

    def __str__(self) -> str:
        """Return the string value of the severity."""
        return self.value


@dataclass
class GuardrailViolation:
    """Represents a detected guardrail violation.

    Attributes:
        type: The type of guardrail that was violated.
        severity: The severity level of the violation.
        message: Human-readable description of the violation.
        context: Additional context about the violation (e.g., detected phrases).
        guardrail_name: Name of the guardrail that detected this violation.
    """

    type: GuardrailType
    severity: ViolationSeverity
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    guardrail_name: str = ""


@dataclass
class GuardrailConfig:
    """Base configuration for guardrails.

    Attributes:
        enabled: Whether this guardrail is active.
    """

    enabled: bool = True


@dataclass
class PriceGuardrailConfig(GuardrailConfig):
    """Configuration for price guardrail.

    Attributes:
        max_discount_percent: Maximum allowed discount percentage (0-100).
        discount_patterns: Regex patterns to detect discount mentions.
        price_patterns: Regex patterns to detect price mentions.
    """

    max_discount_percent: float = 15.0
    discount_patterns: list[str] = field(
        default_factory=lambda: [
            r"(\d+)%\s*折扣",
            r"打折\s*(\d+)%",
            r"优惠\s*(\d+)%",
            r"减免\s*(\d+)%",
            r"(\d+)\s*percent\s*off",
            r"discount.*?(\d+)%",
            r"(\d+)%\s*discount",
        ]
    )


@dataclass
class ContractGuardrailConfig(GuardrailConfig):
    """Configuration for contract guardrail.

    Attributes:
        commitment_patterns: Patterns that indicate contract commitments.
        allowed_phrases: Phrases that are allowed even with commitment keywords.
    """

    commitment_patterns: list[str] = field(
        default_factory=lambda: [
            r"我(们)?可以(为您)?签订",
            r"我(们)?保证",
            r"我(们)?承诺",
            r"合同(条款)?",
            r"签约",
            r"we (can|will) sign",
            r"we guarantee",
            r"we promise",
            r"contract",
        ]
    )
    allowed_phrases: list[str] = field(
        default_factory=lambda: [
            "需要法务审核",
            "需要上级审批",
            "需要确认条款",
            "subject to approval",
            "pending review",
        ]
    )


@dataclass
class FeatureGuardrailConfig(GuardrailConfig):
    """Configuration for feature guardrail.

    Attributes:
        unverified_features: List of features that require verification before claiming.
        verification_required_phrases: Phrases that trigger verification requirement.
    """

    unverified_features: list[str] = field(
        default_factory=lambda: [
            "AI自动决策",
            "智能风险预测",
            "自动合同生成",
            "AI autonomous decision",
            "intelligent risk prediction",
            "automatic contract generation",
        ]
    )
    verification_required_phrases: list[str] = field(
        default_factory=lambda: [
            "我们的产品支持",
            "我们可以提供",
            "系统具有",
            "our product supports",
            "we can provide",
            "the system has",
        ]
    )


@dataclass
class CompetitorGuardrailConfig(GuardrailConfig):
    """Configuration for competitor guardrail.

    Attributes:
        competitor_names: List of competitor names to watch for.
        negative_comparison_patterns: Patterns indicating negative comparisons.
    """

    competitor_names: list[str] = field(
        default_factory=lambda: [
            "竞品A",
            "竞品B",
            "竞争对手",
        ]
    )
    negative_comparison_patterns: list[str] = field(
        default_factory=lambda: [
            r"比.*?差",
            r"不如我们",
            r"没有.*?好",
            r"他们的问题",
            r"他们的缺陷",
            r"worse than",
            r"not as good as",
            r"their problem",
        ]
    )


class Guardrail(ABC):
    """Abstract base class for all guardrails.

    Each guardrail checks responses for a specific type of violation.
    Guardrails are designed to be composable and can be combined
    through the GuardrailManager.

    Attributes:
        name: Human-readable name of the guardrail.
        config: Configuration for the guardrail.
    """

    def __init__(self, name: str, config: GuardrailConfig | None = None) -> None:
        """Initialize the guardrail.

        Args:
            name: Human-readable name for this guardrail.
            config: Optional configuration. Uses defaults if not provided.
        """
        self.name = name
        self.config = config or GuardrailConfig()

    @abstractmethod
    def check(self, text: str, context: dict[str, Any] | None = None) -> list[GuardrailViolation]:
        """Check text for violations.

        Args:
            text: The text to check for violations.
            context: Optional context (e.g., conversation history, customer info).

        Returns:
            List of detected violations. Empty list if no violations found.
        """
        pass

    def is_enabled(self) -> bool:
        """Check if this guardrail is enabled.

        Returns:
            True if the guardrail is enabled and should be checked.
        """
        return self.config.enabled


class PriceGuardrail(Guardrail):
    """Guardrail for detecting unauthorized pricing commitments.

    Detects when the agent offers discounts or pricing beyond
    authorized limits.

    Example:
        >>> guardrail = PriceGuardrail(max_discount_percent=15)
        >>> violations = guardrail.check("我可以给你20%折扣")
        >>> len(violations)
        1
        >>> violations[0].type
        GuardrailType.PRICE
    """

    def __init__(
        self, config: PriceGuardrailConfig | None = None, max_discount_percent: float = 15.0
    ) -> None:
        """Initialize the price guardrail.

        Args:
            config: Optional configuration. If not provided, uses max_discount_percent.
            max_discount_percent: Maximum allowed discount (default: 15%).
        """
        if config is None:
            config = PriceGuardrailConfig(max_discount_percent=max_discount_percent)
        super().__init__("PriceGuardrail", config)
        self._price_config = config

    def check(self, text: str, context: dict[str, Any] | None = None) -> list[GuardrailViolation]:
        """Check text for unauthorized discount mentions.

        Args:
            text: The text to check for price violations.
            context: Optional context (unused for price guardrail).

        Returns:
            List of violations if discounts exceed allowed threshold.
        """
        import re

        if not self.is_enabled():
            return []

        violations: list[GuardrailViolation] = []
        max_discount = self._price_config.max_discount_percent

        for pattern in self._price_config.discount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the discount percentage from the match
                for group in match.groups():
                    if group and group.isdigit():
                        discount_percent = float(group)
                        if discount_percent > max_discount:
                            violations.append(
                                GuardrailViolation(
                                    type=GuardrailType.PRICE,
                                    severity=ViolationSeverity.WARNING,
                                    message=(
                                        f"Unauthorized discount detected: {discount_percent}% "
                                        f"exceeds maximum allowed {max_discount}%"
                                    ),
                                    context={
                                        "discount_percent": discount_percent,
                                        "max_allowed": max_discount,
                                        "matched_text": match.group(),
                                    },
                                    guardrail_name=self.name,
                                )
                            )

        return violations


class ContractGuardrail(Guardrail):
    """Guardrail for detecting unauthorized contract commitments.

    Prevents the agent from making binding commitments without
    proper authorization.

    Example:
        >>> guardrail = ContractGuardrail()
        >>> violations = guardrail.check("我们可以签订5年合同")
        >>> len(violations) > 0
        True
        >>> violations[0].type
        GuardrailType.CONTRACT
    """

    def __init__(self, config: ContractGuardrailConfig | None = None) -> None:
        """Initialize the contract guardrail.

        Args:
            config: Optional configuration for the contract guardrail.
        """
        config = config or ContractGuardrailConfig()
        super().__init__("ContractGuardrail", config)
        self._contract_config = config

    def check(self, text: str, context: dict[str, Any] | None = None) -> list[GuardrailViolation]:
        """Check text for unauthorized contract commitments.

        Args:
            text: The text to check for contract violations.
            context: Optional context (unused for contract guardrail).

        Returns:
            List of violations if contract commitments detected.
        """
        import re

        if not self.is_enabled():
            return []

        violations: list[GuardrailViolation] = []

        # Check if any allowed phrases are present (escape hatch)
        has_allowed_phrase = any(
            phrase.lower() in text.lower() for phrase in self._contract_config.allowed_phrases
        )

        if has_allowed_phrase:
            return violations

        for pattern in self._contract_config.commitment_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    GuardrailViolation(
                        type=GuardrailType.CONTRACT,
                        severity=ViolationSeverity.BLOCK,
                        message=(
                            "Unauthorized contract commitment detected. "
                            "Contract terms require human approval."
                        ),
                        context={
                            "matched_pattern": pattern,
                        },
                        guardrail_name=self.name,
                    )
                )
                break  # Only report one violation per text

        return violations


class FeatureGuardrail(Guardrail):
    """Guardrail for detecting claims about unverified features.

    Prevents the agent from claiming features that have not been
    verified or approved.

    Example:
        >>> guardrail = FeatureGuardrail()
        >>> violations = guardrail.check("我们的产品支持AI自动决策")
        >>> len(violations) > 0
        True
        >>> violations[0].type
        GuardrailType.FEATURE
    """

    def __init__(self, config: FeatureGuardrailConfig | None = None) -> None:
        """Initialize the feature guardrail.

        Args:
            config: Optional configuration for the feature guardrail.
        """
        config = config or FeatureGuardrailConfig()
        super().__init__("FeatureGuardrail", config)
        self._feature_config = config

    def check(self, text: str, context: dict[str, Any] | None = None) -> list[GuardrailViolation]:
        """Check text for claims about unverified features.

        Args:
            text: The text to check for feature violations.
            context: Optional context (unused for feature guardrail).

        Returns:
            List of violations if unverified feature claims detected.
        """
        if not self.is_enabled():
            return []

        violations: list[GuardrailViolation] = []
        text_lower = text.lower()

        # Check if making a feature claim
        is_claiming_feature = any(
            phrase.lower() in text_lower
            for phrase in self._feature_config.verification_required_phrases
        )

        if not is_claiming_feature:
            return violations

        # Check if claiming an unverified feature
        for feature in self._feature_config.unverified_features:
            if feature.lower() in text_lower:
                violations.append(
                    GuardrailViolation(
                        type=GuardrailType.FEATURE,
                        severity=ViolationSeverity.REVIEW,
                        message=(
                            f"Claim about unverified feature detected: '{feature}'. "
                            "Feature claims require verification before stating."
                        ),
                        context={
                            "unverified_feature": feature,
                        },
                        guardrail_name=self.name,
                    )
                )
                break  # Only report one violation per text

        return violations


class CompetitorGuardrail(Guardrail):
    """Guardrail for detecting risky competitor comparisons.

    Prevents the agent from making false or potentially problematic
    competitor comparisons.

    Example:
        >>> config = CompetitorGuardrailConfig(competitor_names=["竞品A"])
        >>> guardrail = CompetitorGuardrail(config)
        >>> violations = guardrail.check("竞品A比我们差很多")
        >>> len(violations) > 0
        True
        >>> violations[0].type
        GuardrailType.COMPETITOR
    """

    def __init__(self, config: CompetitorGuardrailConfig | None = None) -> None:
        """Initialize the competitor guardrail.

        Args:
            config: Optional configuration for the competitor guardrail.
        """
        config = config or CompetitorGuardrailConfig()
        super().__init__("CompetitorGuardrail", config)
        self._competitor_config = config

    def check(self, text: str, context: dict[str, Any] | None = None) -> list[GuardrailViolation]:
        """Check text for risky competitor comparisons.

        Args:
            text: The text to check for competitor violations.
            context: Optional context (unused for competitor guardrail).

        Returns:
            List of violations if risky competitor comparisons detected.
        """
        import re

        if not self.is_enabled():
            return []

        violations: list[GuardrailViolation] = []

        # Check if mentioning a competitor
        mentioned_competitors = [
            name
            for name in self._competitor_config.competitor_names
            if name.lower() in text.lower()
        ]

        if not mentioned_competitors:
            return violations

        # Check for negative comparisons
        for pattern in self._competitor_config.negative_comparison_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(
                    GuardrailViolation(
                        type=GuardrailType.COMPETITOR,
                        severity=ViolationSeverity.REVIEW,
                        message=(
                            "Risky competitor comparison detected. "
                            "Competitor comparisons should be factual and verified."
                        ),
                        context={
                            "mentioned_competitors": mentioned_competitors,
                            "negative_pattern": pattern,
                        },
                        guardrail_name=self.name,
                    )
                )
                break  # Only report one violation per text

        return violations


class GuardrailManager:
    """Manages and runs all guardrails on responses.

    Coordinates multiple guardrails and aggregates their violations.

    Example:
        >>> manager = GuardrailManager()
        >>> manager.add_guardrail(PriceGuardrail(max_discount_percent=15))
        >>> manager.add_guardrail(ContractGuardrail())
        >>> manager.add_guardrail(FeatureGuardrail())
        >>> manager.add_guardrail(CompetitorGuardrail())
        >>> violations = manager.check("我可以给你20%折扣")
        >>> len(violations)
        1
        >>> violations[0].type
        GuardrailType.PRICE
    """

    def __init__(self) -> None:
        """Initialize the guardrail manager."""
        self._guardrails: list[Guardrail] = []

    def add_guardrail(self, guardrail: Guardrail) -> None:
        """Add a guardrail to the manager.

        Args:
            guardrail: The guardrail to add.
        """
        self._guardrails.append(guardrail)

    def remove_guardrail(self, name: str) -> bool:
        """Remove a guardrail by name.

        Args:
            name: The name of the guardrail to remove.

        Returns:
            True if the guardrail was found and removed, False otherwise.
        """
        for i, guardrail in enumerate(self._guardrails):
            if guardrail.name == name:
                self._guardrails.pop(i)
                return True
        return False

    def get_guardrails(self) -> list[Guardrail]:
        """Get all registered guardrails.

        Returns:
            List of all guardrails.
        """
        return self._guardrails.copy()

    def check(self, text: str, context: dict[str, Any] | None = None) -> list[GuardrailViolation]:
        """Run all guardrails on the given text.

        Args:
            text: The text to check for violations.
            context: Optional context passed to each guardrail.

        Returns:
            Aggregated list of all violations from all guardrails.
        """
        all_violations: list[GuardrailViolation] = []
        context = context or {}

        for guardrail in self._guardrails:
            if guardrail.is_enabled():
                violations = guardrail.check(text, context)
                all_violations.extend(violations)

        return all_violations

    def has_violations(self, text: str, context: dict[str, Any] | None = None) -> bool:
        """Check if text has any violations without returning details.

        Args:
            text: The text to check for violations.
            context: Optional context passed to each guardrail.

        Returns:
            True if any violations were detected, False otherwise.
        """
        return len(self.check(text, context)) > 0

    def get_blocking_violations(
        self, text: str, context: dict[str, Any] | None = None
    ) -> list[GuardrailViolation]:
        """Get only the violations that block the response.

        Args:
            text: The text to check for violations.
            context: Optional context passed to each guardrail.

        Returns:
            List of violations with BLOCK severity.
        """
        return [v for v in self.check(text, context) if v.severity == ViolationSeverity.BLOCK]

    def needs_review(self, text: str, context: dict[str, Any] | None = None) -> bool:
        """Check if the text needs human review.

        Args:
            text: The text to check.
            context: Optional context.

        Returns:
            True if there are REVIEW or BLOCK severity violations.
        """
        violations = self.check(text, context)
        return any(
            v.severity in (ViolationSeverity.REVIEW, ViolationSeverity.BLOCK) for v in violations
        )


def create_default_guardrails(
    max_discount_percent: float = 15.0,
    competitor_names: list[str] | None = None,
) -> GuardrailManager:
    """Create a GuardrailManager with default guardrails.

    This is a convenience function to quickly set up a standard
    set of guardrails for a sales agent.

    Args:
        max_discount_percent: Maximum allowed discount percentage.
        competitor_names: Optional list of competitor names to monitor.

    Returns:
        Configured GuardrailManager with all default guardrails.

    Example:
        >>> manager = create_default_guardrails(max_discount_percent=15)
        >>> violations = manager.check("我可以给你20%折扣")
        >>> violations[0].type
        GuardrailType.PRICE
    """
    manager = GuardrailManager()

    # Add price guardrail
    manager.add_guardrail(
        PriceGuardrail(config=PriceGuardrailConfig(max_discount_percent=max_discount_percent))
    )

    # Add contract guardrail
    manager.add_guardrail(ContractGuardrail())

    # Add feature guardrail
    manager.add_guardrail(FeatureGuardrail())

    # Add competitor guardrail with optional custom names
    competitor_config = CompetitorGuardrailConfig()
    if competitor_names:
        competitor_config.competitor_names = competitor_names
    manager.add_guardrail(CompetitorGuardrail(config=competitor_config))

    return manager
