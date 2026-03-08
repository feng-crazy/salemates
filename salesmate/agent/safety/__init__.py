"""Safety and control systems for sales agent.

Components:
- Confidence Router: Routes responses based on confidence scores
- Emotion Fuse: Detects negative emotions and triggers human handoff
- Guardrails: Prevents unauthorized commitments (price, contract, feature, competitor)
- Human Handoff: Feishu notifications for human intervention
"""

# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

from .confidence_router import (
    ConfidenceLevel,
    ConfidenceRouter,
    ConfidenceThresholds,
    RoutingDecision,
)
from .emotion_fuse import (
    EmotionFuse,
    EmotionFuseConfig,
    FuseAction,
    FuseCheckResult,
    create_default_emotion_fuse,
)
from .guardrails import (
    CompetitorGuardrail,
    CompetitorGuardrailConfig,
    ContractGuardrail,
    ContractGuardrailConfig,
    FeatureGuardrail,
    FeatureGuardrailConfig,
    Guardrail,
    GuardrailConfig,
    GuardrailManager,
    GuardrailType,
    GuardrailViolation,
    PriceGuardrail,
    PriceGuardrailConfig,
    ViolationSeverity,
    create_default_guardrails,
)
from .human_handoff import (
    HandoffConfig,
    HandoffState,
    HandoffTrigger,
    HumanHandoffManager,
    create_handoff_manager,
)

__all__ = [
    # Confidence Router
    "ConfidenceLevel",
    "ConfidenceRouter",
    "ConfidenceThresholds",
    "RoutingDecision",
    # Emotion Fuse
    "EmotionFuse",
    "EmotionFuseConfig",
    "FuseAction",
    "FuseCheckResult",
    "create_default_emotion_fuse",
    # Guardrails
    "CompetitorGuardrail",
    "CompetitorGuardrailConfig",
    "ContractGuardrail",
    "ContractGuardrailConfig",
    "FeatureGuardrail",
    "FeatureGuardrailConfig",
    "Guardrail",
    "GuardrailConfig",
    "GuardrailManager",
    "GuardrailType",
    "GuardrailViolation",
    "PriceGuardrail",
    "PriceGuardrailConfig",
    "ViolationSeverity",
    "create_default_guardrails",
    # Human Handoff
    "HandoffConfig",
    "HandoffState",
    "HandoffTrigger",
    "HumanHandoffManager",
    "create_handoff_manager",
]
