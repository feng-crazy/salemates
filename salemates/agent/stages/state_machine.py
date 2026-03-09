# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Sales stage state machine with transition validation.

This module implements a state machine for managing sales pipeline stages.
The pipeline follows a 6-stage progression:
- NEW_CONTACT: Initial contact established
- DISCOVERY: Understanding customer needs
- PRESENTATION: Presenting solutions
- NEGOTIATION: Handling objections and pricing
- CLOSE: Finalizing the deal
- LOST: Deal lost or customer churned
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SalesStage(str, Enum):
    """Sales pipeline stages.

    Each stage represents a distinct phase in the sales process.
    """

    NEW_CONTACT = "new_contact"
    DISCOVERY = "discovery"
    PRESENTATION = "presentation"
    NEGOTIATION = "negotiation"
    CLOSE = "close"
    LOST = "lost"

    def __str__(self) -> str:
        """Return the string value of the stage."""
        return self.value


@dataclass
class StageTransition:
    """Represents a valid stage transition.

    Attributes:
        from_stage: The stage transitioning from.
        to_stage: The stage transitioning to.
        trigger: What triggers this transition.
        required_signals: Required conversation signals for this transition.
        timestamp: When the transition occurred.
    """

    from_stage: SalesStage
    to_stage: SalesStage
    trigger: str
    required_signals: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# Signal-to-stage mapping constants
SIGNAL_TO_STAGE: dict[str, SalesStage] = {
    "customer_shows_interest": SalesStage.DISCOVERY,
    "needs_identified": SalesStage.PRESENTATION,
    "objection_raised": SalesStage.NEGOTIATION,
    "agreement_reached": SalesStage.CLOSE,
    "customer_unresponsive": SalesStage.LOST,
    "customer_declined": SalesStage.LOST,
    "budget_not_qualified": SalesStage.LOST,
}

# Stage transition triggers
TRANSITION_TRIGGERS: dict[tuple[SalesStage, SalesStage], list[str]] = {
    (SalesStage.NEW_CONTACT, SalesStage.DISCOVERY): [
        "customer_replied",
        "meeting_scheduled",
        "demo_requested",
    ],
    (SalesStage.NEW_CONTACT, SalesStage.LOST): [
        "no_response",
        "wrong_contact",
        "not_interested",
    ],
    (SalesStage.DISCOVERY, SalesStage.PRESENTATION): [
        "needs_documented",
        "pain_points_identified",
        "budget_confirmed",
    ],
    (SalesStage.DISCOVERY, SalesStage.LOST): [
        "no_budget",
        "no_authority",
        "timeline_mismatch",
    ],
    (SalesStage.PRESENTATION, SalesStage.NEGOTIATION): [
        "pricing_discussed",
        "objection_raised",
        "competitor_comparison",
    ],
    (SalesStage.PRESENTATION, SalesStage.LOST): [
        "price_too_high",
        "competitor_chosen",
        "project_cancelled",
    ],
    (SalesStage.NEGOTIATION, SalesStage.CLOSE): [
        "agreement_signed",
        "purchase_order",
        "verbal_commitment",
    ],
    (SalesStage.NEGOTIATION, SalesStage.LOST): [
        "negotiation_failed",
        "competitor_won",
        "budget_cut",
    ],
}


class SalesStageStateMachine:
    """Manages sales stage transitions with validation.

    This state machine enforces valid transitions between sales stages,
    ensuring that deals progress through the pipeline in a logical order.

    Valid transitions:
        NEW_CONTACT → DISCOVERY (customer shows interest)
        NEW_CONTACT → LOST (customer churns immediately)
        DISCOVERY → PRESENTATION (needs identified)
        DISCOVERY → LOST (customer churns)
        PRESENTATION → NEGOTIATION (objections raised)
        PRESENTATION → LOST (customer churns)
        NEGOTIATION → CLOSE (agreement reached)
        NEGOTIATION → LOST (customer churns)
        CLOSE → (terminal state)
        LOST → (terminal state)

    Example:
        >>> sm = SalesStageStateMachine()
        >>> sm.can_transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        True
        >>> sm.can_transition(SalesStage.CLOSE, SalesStage.DISCOVERY)
        False
        >>> success, error = sm.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        >>> print(success)
        True
    """

    VALID_TRANSITIONS: dict[SalesStage, list[SalesStage]] = {
        SalesStage.NEW_CONTACT: [SalesStage.DISCOVERY, SalesStage.LOST],
        SalesStage.DISCOVERY: [SalesStage.PRESENTATION, SalesStage.LOST],
        SalesStage.PRESENTATION: [SalesStage.NEGOTIATION, SalesStage.LOST],
        SalesStage.NEGOTIATION: [SalesStage.CLOSE, SalesStage.LOST],
        SalesStage.CLOSE: [],  # Terminal state
        SalesStage.LOST: [],  # Terminal state
    }

    def __init__(self) -> None:
        """Initialize the state machine with empty transition history."""
        self.transition_history: list[StageTransition] = []

    def can_transition(self, from_stage: SalesStage, to_stage: SalesStage) -> bool:
        """Check if a transition between stages is valid.

        Args:
            from_stage: The current stage.
            to_stage: The target stage.

        Returns:
            True if the transition is valid, False otherwise.
        """
        valid_targets = self.VALID_TRANSITIONS.get(from_stage, [])
        return to_stage in valid_targets

    def transition(
        self,
        from_stage: SalesStage,
        to_stage: SalesStage,
        trigger: str = "",
    ) -> tuple[bool, Optional[str]]:
        """Attempt a stage transition.

        Args:
            from_stage: The current stage.
            to_stage: The target stage.
            trigger: Optional description of what triggered this transition.

        Returns:
            A tuple of (success, error_message).
            If successful, error_message will be None.
        """
        if not self.can_transition(from_stage, to_stage):
            valid_targets = self.VALID_TRANSITIONS.get(from_stage, [])
            valid_str = ", ".join(s.value for s in valid_targets) or "none (terminal)"
            return False, (
                f"Invalid transition: {from_stage.value} → {to_stage.value}. "
                f"Valid transitions from {from_stage.value}: {valid_str}"
            )

        # Record the transition
        transition_record = StageTransition(
            from_stage=from_stage,
            to_stage=to_stage,
            trigger=trigger,
            required_signals=[],
        )
        self.transition_history.append(transition_record)

        return True, None

    def get_next_possible_stages(self, current_stage: SalesStage) -> list[SalesStage]:
        """Get the list of valid next stages from the current stage.

        Args:
            current_stage: The current stage in the pipeline.

        Returns:
            List of stages that can be transitioned to from current_stage.
        """
        return self.VALID_TRANSITIONS.get(current_stage, []).copy()

    def suggest_transition(
        self,
        conversation_signals: list[str],
        current_stage: Optional[SalesStage] = None,
    ) -> Optional[SalesStage]:
        """Suggest the next stage based on conversation signals.

        Analyzes conversation signals to suggest an appropriate stage transition.
        Priority is given to positive progression signals, then to loss signals.

        Signals and their target stages:
            - "customer_shows_interest" → DISCOVERY
            - "needs_identified" → PRESENTATION
            - "objection_raised" → NEGOTIATION
            - "agreement_reached" → CLOSE
            - "customer_unresponsive" → LOST
            - "customer_declined" → LOST
            - "budget_not_qualified" → LOST

        Args:
            conversation_signals: List of detected signals from the conversation.
            current_stage: Optional current stage to validate transition validity.
                If provided, only valid transitions from this stage will be suggested.

        Returns:
            The suggested stage, or None if no matching signals found or
            transition would be invalid.
        """
        # Priority order: positive progression first, then loss signals
        signal_priority = [
            "agreement_reached",
            "objection_raised",
            "needs_identified",
            "customer_shows_interest",
            "customer_declined",
            "customer_unresponsive",
            "budget_not_qualified",
        ]

        for signal in signal_priority:
            if signal in conversation_signals:
                target_stage = SIGNAL_TO_STAGE.get(signal)
                if target_stage:
                    # If current_stage is provided, validate the transition
                    if current_stage is not None:
                        if self.can_transition(current_stage, target_stage):
                            return target_stage
                    else:
                        return target_stage

        return None

    def get_valid_triggers(
        self,
        from_stage: SalesStage,
        to_stage: SalesStage,
    ) -> list[str]:
        """Get valid triggers for a specific transition.

        Args:
            from_stage: The source stage.
            to_stage: The target stage.

        Returns:
            List of valid trigger descriptions for this transition.
        """
        key = (from_stage, to_stage)
        return TRANSITION_TRIGGERS.get(key, [])

    def get_transition_count(self, to_stage: Optional[SalesStage] = None) -> int:
        """Get the count of transitions, optionally filtered by target stage.

        Args:
            to_stage: Optional stage to filter by.

        Returns:
            Number of transitions matching the filter.
        """
        if to_stage is None:
            return len(self.transition_history)

        return sum(1 for t in self.transition_history if t.to_stage == to_stage)

    def get_last_transition(self) -> Optional[StageTransition]:
        """Get the most recent transition.

        Returns:
            The last transition, or None if no transitions have occurred.
        """
        if not self.transition_history:
            return None
        return self.transition_history[-1]

    def clear_history(self) -> None:
        """Clear all transition history."""
        self.transition_history.clear()

    def is_terminal_stage(self, stage: SalesStage) -> bool:
        """Check if a stage is terminal (no further transitions possible).

        Args:
            stage: The stage to check.

        Returns:
            True if the stage is terminal, False otherwise.
        """
        return len(self.VALID_TRANSITIONS.get(stage, [])) == 0
