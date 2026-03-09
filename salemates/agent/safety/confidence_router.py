# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Confidence-based response routing for sales agent.

Routes responses based on confidence scores with three tiers:
- HIGH (>90%): Auto-response without human review
- MEDIUM (60-90%): Generate draft for human approval
- LOW (<60%): Immediate human intervention required

Example:
    >>> router = ConfidenceRouter()
    >>> decision = router.route(0.95, {"customer_id": "123"})
    >>> print(decision.level)
    ConfidenceLevel.HIGH
    >>> print(decision.action)
    "auto_reply"
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from salemates.agent.safety.human_handoff import HumanHandoffManager


class ConfidenceLevel(str, Enum):
    """Confidence level for response routing.

    Each level corresponds to a different handling strategy.
    """

    HIGH = "high"  # >90% confidence - auto-response
    MEDIUM = "medium"  # 60-90% confidence - draft for approval
    LOW = "low"  # <60% confidence - human intervention

    def __str__(self) -> str:
        """Return the string value of the confidence level."""
        return self.value


@dataclass
class RoutingDecision:
    """Represents a routing decision based on confidence score.

    Attributes:
        level: The confidence level (HIGH, MEDIUM, LOW).
        action: The action to take (auto_reply, draft, human_intervention).
        reason: Human-readable explanation for the routing decision.
        confidence: The original confidence score (0.0 to 1.0).
        context: Additional context that influenced the decision.
    """

    level: ConfidenceLevel
    action: str
    reason: str
    confidence: float
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate confidence score is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class ConfidenceThresholds:
    """Configurable thresholds for confidence routing.

    Attributes:
        high_threshold: Minimum confidence for HIGH level (default: 0.90).
        medium_threshold: Minimum confidence for MEDIUM level (default: 0.60).
    """

    high_threshold: float = 0.90
    medium_threshold: float = 0.60

    def __post_init__(self) -> None:
        """Validate thresholds are in correct order and range."""
        if not 0.0 <= self.medium_threshold <= self.high_threshold <= 1.0:
            raise ValueError(
                f"Invalid thresholds: medium ({self.medium_threshold}) must be <= "
                f"high ({self.high_threshold}), and both must be in [0.0, 1.0]"
            )


class ConfidenceRouter:
    """Routes responses based on confidence scores.

    Determines how AI-generated responses should be handled based on
    the model's confidence in the response quality.

    Routing Logic:
        - confidence >= high_threshold → HIGH (auto-reply)
        - medium_threshold <= confidence < high_threshold → MEDIUM (draft)
        - confidence < medium_threshold → LOW (human intervention)

    Attributes:
        thresholds: Configurable threshold values.

    Example:
        >>> router = ConfidenceRouter()
        >>> decision = router.route(0.95, {})
        >>> decision.level
        ConfidenceLevel.HIGH
        >>> decision.action
        'auto_reply'

        >>> router = ConfidenceRouter(ConfidenceThresholds(high_threshold=0.85))
        >>> decision = router.route(0.87, {})
        >>> decision.level
        ConfidenceLevel.HIGH
    """

    def __init__(self, thresholds: ConfidenceThresholds | None = None) -> None:
        """Initialize the confidence router.

        Args:
            thresholds: Optional custom thresholds. Uses defaults if not provided.
        """
        self.thresholds = thresholds or ConfidenceThresholds()

    def route(self, confidence: float, context: dict[str, Any]) -> RoutingDecision:
        """Route a response based on its confidence score.

        Args:
            confidence: Confidence score from 0.0 to 1.0.
            context: Additional context for the routing decision (e.g.,
                customer_id, conversation_history, intent).

        Returns:
            RoutingDecision with level, action, and reason.

        Raises:
            ValueError: If confidence is not between 0.0 and 1.0.

        Example:
            >>> router = ConfidenceRouter()
            >>> decision = router.route(0.95, {"customer_id": "123"})
            >>> decision.level
            ConfidenceLevel.HIGH
            >>> decision.action
            'auto_reply'
        """
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

        if confidence >= self.thresholds.high_threshold:
            return RoutingDecision(
                level=ConfidenceLevel.HIGH,
                action="auto_reply",
                reason=f"High confidence ({confidence:.1%}) - safe for auto-response",
                confidence=confidence,
                context=context,
            )
        elif confidence >= self.thresholds.medium_threshold:
            return RoutingDecision(
                level=ConfidenceLevel.MEDIUM,
                action="draft",
                reason=(
                    f"Medium confidence ({confidence:.1%}) - generate draft for human approval"
                ),
                confidence=confidence,
                context=context,
            )
        else:
            return RoutingDecision(
                level=ConfidenceLevel.LOW,
                action="human_intervention",
                reason=(
                    f"Low confidence ({confidence:.1%}) - immediate human intervention required"
                ),
                confidence=confidence,
                context=context,
            )

    def get_level(self, confidence: float) -> ConfidenceLevel:
        """Get the confidence level for a given confidence score.

        This is a convenience method when you only need the level,
        not the full routing decision.

        Args:
            confidence: Confidence score from 0.0 to 1.0.

        Returns:
            The corresponding ConfidenceLevel.

        Example:
            >>> router = ConfidenceRouter()
            >>> router.get_level(0.95)
            ConfidenceLevel.HIGH
            >>> router.get_level(0.75)
            ConfidenceLevel.MEDIUM
            >>> router.get_level(0.55)
            ConfidenceLevel.LOW
        """
        decision = self.route(confidence, {})
        return decision.level

    def should_auto_reply(self, confidence: float) -> bool:
        """Check if confidence is high enough for auto-reply.

        Args:
            confidence: Confidence score from 0.0 to 1.0.

        Returns:
            True if confidence is at or above high threshold.

        Example:
            >>> router = ConfidenceRouter()
            >>> router.should_auto_reply(0.95)
            True
            >>> router.should_auto_reply(0.85)
            False
        """
        return confidence >= self.thresholds.high_threshold

    def needs_human_review(self, confidence: float) -> bool:
        """Check if human review is needed (MEDIUM or LOW confidence).

        Args:
            confidence: Confidence score from 0.0 to 1.0.

        Returns:
            True if confidence is below high threshold.

        Example:
            >>> router = ConfidenceRouter()
            >>> router.needs_human_review(0.75)
            True
            >>> router.needs_human_review(0.95)
            False
        """
        return confidence < self.thresholds.high_threshold

    def needs_immediate_intervention(self, confidence: float) -> bool:
        """Check if immediate human intervention is needed (LOW confidence).

        Args:
            confidence: Confidence score from 0.0 to 1.0.

        Returns:
            True if confidence is below medium threshold.

        Example:
            >>> router = ConfidenceRouter()
            >>> router.needs_immediate_intervention(0.55)
            True
            >>> router.needs_immediate_intervention(0.75)
            False
        """
        return confidence < self.thresholds.medium_threshold

    async def route_with_handoff(
        self,
        confidence: float,
        context: dict[str, Any],
        handoff_manager: "HumanHandoffManager | None" = None,
        conversation_summary: str = "",
        ai_suggested_response: str = "",
        customer_profile: Any = None,
    ) -> RoutingDecision:
        """Route response and trigger human handoff if needed.

        This method extends route() to automatically trigger human handoff
        notifications when confidence is LOW. The handoff_manager must be
        provided for handoff to occur.

        Args:
            confidence: Confidence score from 0.0 to 1.0.
            context: Context including customer_id and chat_id for handoff.
            handoff_manager: Optional HumanHandoffManager for sending notifications.
            conversation_summary: Summary of the conversation for handoff notification.
            ai_suggested_response: AI's proposed response for handoff context.
            customer_profile: Optional customer profile for display.

        Returns:
            RoutingDecision with level, action, and reason.

        Example:
            >>> from salemates.agent.safety.human_handoff import HumanHandoffManager
            >>> router = ConfidenceRouter()
            >>> handoff_manager = HumanHandoffManager(...)
            >>> decision = await router.route_with_handoff(
            ...     confidence=0.45,
            ...     context={"customer_id": "cust_123", "chat_id": "oc_xxx"},
            ...     handoff_manager=handoff_manager,
            ...     conversation_summary="Customer asked about pricing...",
            ...     ai_suggested_response="Based on our policy..."
            ... )
        """
        decision = self.route(confidence, context)

        # Trigger handoff for LOW confidence
        if decision.level == ConfidenceLevel.LOW and handoff_manager:
            from salemates.agent.safety.human_handoff import HandoffTrigger

            customer_id = context.get("customer_id", "unknown")
            chat_id = context.get("chat_id", "")

            if chat_id:
                await handoff_manager.notify_human(
                    customer_id=customer_id,
                    chat_id=chat_id,
                    conversation_summary=conversation_summary,
                    ai_suggested_response=ai_suggested_response,
                    trigger_reason=HandoffTrigger.LOW_CONFIDENCE,
                    context={"confidence": confidence},
                    customer_profile=customer_profile,
                )

        return decision
