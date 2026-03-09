# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Sales stage state machine.

6-stage sales pipeline:
- NEW_CONTACT: Initial contact established
- DISCOVERY: Understanding customer needs
- PRESENTATION: Presenting solutions
- NEGOTIATION: Handling objections and pricing
- CLOSE: Finalizing the deal
- LOST: Deal lost or customer churned
"""

from .state_machine import (
    SalesStage,
    SalesStageStateMachine,
    StageTransition,
    SIGNAL_TO_STAGE,
    TRANSITION_TRIGGERS,
)
from .transitions import (
    ConversationSignal,
    SignalCategory,
    TransitionRule,
    TransitionType,
    evaluate_transition,
    get_all_signals,
    get_signal_definition,
    get_signals_by_category,
    get_transition_rule,
    NEGATIVE_SIGNALS,
    POSITIVE_SIGNALS,
    TRANSITION_RULES,
)

__all__ = [
    # State machine
    "SalesStage",
    "SalesStageStateMachine",
    "StageTransition",
    "SIGNAL_TO_STAGE",
    "TRANSITION_TRIGGERS",
    # Transitions
    "ConversationSignal",
    "SignalCategory",
    "TransitionRule",
    "TransitionType",
    "evaluate_transition",
    "get_all_signals",
    "get_signal_definition",
    "get_signals_by_category",
    "get_transition_rule",
    "NEGATIVE_SIGNALS",
    "POSITIVE_SIGNALS",
    "TRANSITION_RULES",
]
