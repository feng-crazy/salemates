# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Transition rules and triggers for sales stage state machine.

This module defines:
- Transition rules: Conditions and requirements for stage transitions
- Transition triggers: Events that cause stage changes
- Signal detection: Conversation signals that indicate transitions
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .state_machine import SalesStage


class TransitionType(str, Enum):
    """Types of stage transitions."""

    PROGRESSION = "progression"  # Forward movement in pipeline
    REGRESSION = "regression"  # Backward movement (not typically allowed)
    LOSS = "loss"  # Customer lost/churned
    RECOVERY = "recovery"  # Recovering from lost (not typically allowed)


class SignalCategory(str, Enum):
    """Categories of conversation signals."""

    POSITIVE = "positive"  # Signals indicating progress
    NEGATIVE = "negative"  # Signals indicating problems
    NEUTRAL = "neutral"  # Informational signals


@dataclass
class TransitionRule:
    """Defines a rule for stage transition.

    Attributes:
        from_stage: Source stage.
        to_stage: Target stage.
        transition_type: Type of transition.
        required_signals: Signals that must be present.
        blocking_signals: Signals that prevent transition.
        confidence_threshold: Minimum confidence required (0.0-1.0).
        description: Human-readable description.
    """

    from_stage: SalesStage
    to_stage: SalesStage
    transition_type: TransitionType
    required_signals: list[str] = field(default_factory=list)
    blocking_signals: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.7
    description: str = ""


@dataclass
class ConversationSignal:
    """Represents a detected signal from conversation analysis.

    Attributes:
        name: Signal identifier.
        category: Signal category (positive/negative/neutral).
        confidence: Detection confidence (0.0-1.0).
        evidence: Text evidence from conversation.
        description: Human-readable description of the signal.
        metadata: Additional signal metadata.
    """

    name: str
    category: SignalCategory
    confidence: float
    evidence: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)


# Predefined transition rules
TRANSITION_RULES: dict[tuple[SalesStage, SalesStage], TransitionRule] = {
    # NEW_CONTACT → DISCOVERY
    (
        SalesStage.NEW_CONTACT,
        SalesStage.DISCOVERY,
    ): TransitionRule(
        from_stage=SalesStage.NEW_CONTACT,
        to_stage=SalesStage.DISCOVERY,
        transition_type=TransitionType.PROGRESSION,
        required_signals=[
            "customer_replied",
            "customer_shows_interest",
        ],
        blocking_signals=[
            "customer_declined",
            "wrong_contact",
        ],
        confidence_threshold=0.6,
        description="Customer has shown interest and engaged in conversation",
    ),
    # NEW_CONTACT → LOST
    (
        SalesStage.NEW_CONTACT,
        SalesStage.LOST,
    ): TransitionRule(
        from_stage=SalesStage.NEW_CONTACT,
        to_stage=SalesStage.LOST,
        transition_type=TransitionType.LOSS,
        required_signals=[
            "no_response",
            "customer_declined",
        ],
        blocking_signals=[
            "customer_replied",
        ],
        confidence_threshold=0.8,
        description="Customer did not respond or explicitly declined",
    ),
    # DISCOVERY → PRESENTATION
    (
        SalesStage.DISCOVERY,
        SalesStage.PRESENTATION,
    ): TransitionRule(
        from_stage=SalesStage.DISCOVERY,
        to_stage=SalesStage.PRESENTATION,
        transition_type=TransitionType.PROGRESSION,
        required_signals=[
            "needs_identified",
            "pain_points_discussed",
        ],
        blocking_signals=[
            "no_budget",
            "no_need",
        ],
        confidence_threshold=0.7,
        description="Customer needs have been identified and documented",
    ),
    # DISCOVERY → LOST
    (
        SalesStage.DISCOVERY,
        SalesStage.LOST,
    ): TransitionRule(
        from_stage=SalesStage.DISCOVERY,
        to_stage=SalesStage.LOST,
        transition_type=TransitionType.LOSS,
        required_signals=[
            "no_budget",
            "no_authority",
            "no_need",
            "timeline_mismatch",
        ],
        blocking_signals=[],
        confidence_threshold=0.7,
        description="Customer does not qualify (BANT criteria not met)",
    ),
    # PRESENTATION → NEGOTIATION
    (
        SalesStage.PRESENTATION,
        SalesStage.NEGOTIATION,
    ): TransitionRule(
        from_stage=SalesStage.PRESENTATION,
        to_stage=SalesStage.NEGOTIATION,
        transition_type=TransitionType.PROGRESSION,
        required_signals=[
            "objection_raised",
            "pricing_discussed",
            "competitor_comparison",
        ],
        blocking_signals=[
            "competitor_chosen",
            "project_cancelled",
        ],
        confidence_threshold=0.7,
        description="Customer has questions or objections about the solution",
    ),
    # PRESENTATION → LOST
    (
        SalesStage.PRESENTATION,
        SalesStage.LOST,
    ): TransitionRule(
        from_stage=SalesStage.PRESENTATION,
        to_stage=SalesStage.LOST,
        transition_type=TransitionType.LOSS,
        required_signals=[
            "competitor_chosen",
            "price_too_high",
            "project_cancelled",
        ],
        blocking_signals=[],
        confidence_threshold=0.7,
        description="Customer chose competitor or cancelled project",
    ),
    # NEGOTIATION → CLOSE
    (
        SalesStage.NEGOTIATION,
        SalesStage.CLOSE,
    ): TransitionRule(
        from_stage=SalesStage.NEGOTIATION,
        to_stage=SalesStage.CLOSE,
        transition_type=TransitionType.PROGRESSION,
        required_signals=[
            "agreement_reached",
            "contract_signed",
            "purchase_order_received",
        ],
        blocking_signals=[
            "negotiation_stalled",
        ],
        confidence_threshold=0.9,
        description="Customer has agreed to terms and finalized purchase",
    ),
    # NEGOTIATION → LOST
    (
        SalesStage.NEGOTIATION,
        SalesStage.LOST,
    ): TransitionRule(
        from_stage=SalesStage.NEGOTIATION,
        to_stage=SalesStage.LOST,
        transition_type=TransitionType.LOSS,
        required_signals=[
            "negotiation_failed",
            "competitor_won",
            "budget_cut",
        ],
        blocking_signals=[],
        confidence_threshold=0.8,
        description="Negotiation ended without agreement",
    ),
}


# Signal definitions by category
POSITIVE_SIGNALS: dict[str, ConversationSignal] = {
    "customer_replied": ConversationSignal(
        name="customer_replied",
        category=SignalCategory.POSITIVE,
        confidence=0.8,
        description="Customer responded to outreach",
    ),
    "customer_shows_interest": ConversationSignal(
        name="customer_shows_interest",
        category=SignalCategory.POSITIVE,
        confidence=0.7,
        description="Customer expressed interest in product/service",
    ),
    "meeting_scheduled": ConversationSignal(
        name="meeting_scheduled",
        category=SignalCategory.POSITIVE,
        confidence=0.9,
        description="Meeting or demo has been scheduled",
    ),
    "needs_identified": ConversationSignal(
        name="needs_identified",
        category=SignalCategory.POSITIVE,
        confidence=0.8,
        description="Customer needs have been clearly identified",
    ),
    "pain_points_discussed": ConversationSignal(
        name="pain_points_discussed",
        category=SignalCategory.POSITIVE,
        confidence=0.7,
        description="Customer shared pain points and challenges",
    ),
    "budget_confirmed": ConversationSignal(
        name="budget_confirmed",
        category=SignalCategory.POSITIVE,
        confidence=0.8,
        description="Customer confirmed budget availability",
    ),
    "demo_requested": ConversationSignal(
        name="demo_requested",
        category=SignalCategory.POSITIVE,
        confidence=0.85,
        description="Customer requested a product demo",
    ),
    "pricing_discussed": ConversationSignal(
        name="pricing_discussed",
        category=SignalCategory.POSITIVE,
        confidence=0.7,
        description="Customer engaged in pricing discussion",
    ),
    "objection_raised": ConversationSignal(
        name="objection_raised",
        category=SignalCategory.NEUTRAL,
        confidence=0.7,
        description="Customer raised an objection or concern",
    ),
    "competitor_comparison": ConversationSignal(
        name="competitor_comparison",
        category=SignalCategory.NEUTRAL,
        confidence=0.6,
        description="Customer comparing with competitors",
    ),
    "agreement_reached": ConversationSignal(
        name="agreement_reached",
        category=SignalCategory.POSITIVE,
        confidence=0.9,
        description="Customer agreed to terms",
    ),
    "contract_signed": ConversationSignal(
        name="contract_signed",
        category=SignalCategory.POSITIVE,
        confidence=1.0,
        description="Contract has been signed",
    ),
    "purchase_order_received": ConversationSignal(
        name="purchase_order_received",
        category=SignalCategory.POSITIVE,
        confidence=1.0,
        description="Purchase order received",
    ),
}

NEGATIVE_SIGNALS: dict[str, ConversationSignal] = {
    "no_response": ConversationSignal(
        name="no_response",
        category=SignalCategory.NEGATIVE,
        confidence=0.5,
        description="No response from customer",
    ),
    "customer_declined": ConversationSignal(
        name="customer_declined",
        category=SignalCategory.NEGATIVE,
        confidence=0.9,
        description="Customer explicitly declined",
    ),
    "wrong_contact": ConversationSignal(
        name="wrong_contact",
        category=SignalCategory.NEGATIVE,
        confidence=0.9,
        description="Wrong person contacted",
    ),
    "no_budget": ConversationSignal(
        name="no_budget",
        category=SignalCategory.NEGATIVE,
        confidence=0.8,
        description="Customer has no budget",
    ),
    "no_authority": ConversationSignal(
        name="no_authority",
        category=SignalCategory.NEGATIVE,
        confidence=0.8,
        description="Contact has no decision authority",
    ),
    "no_need": ConversationSignal(
        name="no_need",
        category=SignalCategory.NEGATIVE,
        confidence=0.8,
        description="Customer has no need for product",
    ),
    "timeline_mismatch": ConversationSignal(
        name="timeline_mismatch",
        category=SignalCategory.NEGATIVE,
        confidence=0.7,
        description="Timeline doesn't match customer needs",
    ),
    "competitor_chosen": ConversationSignal(
        name="competitor_chosen",
        category=SignalCategory.NEGATIVE,
        confidence=0.9,
        description="Customer chose a competitor",
    ),
    "price_too_high": ConversationSignal(
        name="price_too_high",
        category=SignalCategory.NEGATIVE,
        confidence=0.8,
        description="Customer found price too high",
    ),
    "project_cancelled": ConversationSignal(
        name="project_cancelled",
        category=SignalCategory.NEGATIVE,
        confidence=0.9,
        description="Customer's project was cancelled",
    ),
    "negotiation_failed": ConversationSignal(
        name="negotiation_failed",
        category=SignalCategory.NEGATIVE,
        confidence=0.85,
        description="Negotiation ended without agreement",
    ),
    "competitor_won": ConversationSignal(
        name="competitor_won",
        category=SignalCategory.NEGATIVE,
        confidence=0.9,
        description="Competitor won the deal",
    ),
    "budget_cut": ConversationSignal(
        name="budget_cut",
        category=SignalCategory.NEGATIVE,
        confidence=0.85,
        description="Customer's budget was cut",
    ),
    "customer_unresponsive": ConversationSignal(
        name="customer_unresponsive",
        category=SignalCategory.NEGATIVE,
        confidence=0.6,
        description="Customer became unresponsive",
    ),
}


def get_transition_rule(
    from_stage: SalesStage,
    to_stage: SalesStage,
) -> Optional[TransitionRule]:
    """Get the transition rule for a specific stage transition.

    Args:
        from_stage: Source stage.
        to_stage: Target stage.

    Returns:
        The transition rule, or None if no rule exists.
    """
    return TRANSITION_RULES.get((from_stage, to_stage))


def get_signal_definition(signal_name: str) -> Optional[ConversationSignal]:
    """Get the definition of a conversation signal.

    Args:
        signal_name: Name of the signal.

    Returns:
        The signal definition, or None if not found.
    """
    if signal_name in POSITIVE_SIGNALS:
        return POSITIVE_SIGNALS[signal_name]
    if signal_name in NEGATIVE_SIGNALS:
        return NEGATIVE_SIGNALS[signal_name]
    return None


def evaluate_transition(
    from_stage: SalesStage,
    to_stage: SalesStage,
    detected_signals: list[str],
    signal_confidences: Optional[dict[str, float]] = None,
) -> tuple[bool, str]:
    """Evaluate whether a transition should occur based on signals.

    Args:
        from_stage: Source stage.
        to_stage: Target stage.
        detected_signals: List of signals detected in conversation.
        signal_confidences: Optional mapping of signal to confidence scores.

    Returns:
        Tuple of (should_transition, reason).
    """
    rule = get_transition_rule(from_stage, to_stage)
    if rule is None:
        return False, f"No transition rule for {from_stage.value} → {to_stage.value}"

    # Check for blocking signals
    for blocking_signal in rule.blocking_signals:
        if blocking_signal in detected_signals:
            return False, f"Blocked by signal: {blocking_signal}"

    # Check for required signals
    has_required = False
    for required_signal in rule.required_signals:
        if required_signal in detected_signals:
            # Check confidence if provided
            if signal_confidences:
                confidence = signal_confidences.get(required_signal, 0.0)
                if confidence < rule.confidence_threshold:
                    continue
            has_required = True
            break

    if not has_required:
        required_str = ", ".join(rule.required_signals)
        return False, f"Missing required signals. Need one of: {required_str}"

    return True, rule.description


def get_all_signals() -> dict[str, ConversationSignal]:
    """Get all defined signals.

    Returns:
        Dictionary of all signal definitions.
    """
    all_signals = {}
    all_signals.update(POSITIVE_SIGNALS)
    all_signals.update(NEGATIVE_SIGNALS)
    return all_signals


def get_signals_by_category(category: SignalCategory) -> dict[str, ConversationSignal]:
    """Get signals filtered by category.

    Args:
        category: The signal category to filter by.

    Returns:
        Dictionary of signals in the specified category.
    """
    all_signals = get_all_signals()
    return {name: signal for name, signal in all_signals.items() if signal.category == category}
