# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Sales emotion analysis module.

Detects customer emotions during sales conversations:
- HESITATION: Uncertainty about buying
- TRUST: Trust and confidence building
- ANGER: Frustration or anger signals
- FRUSTRATION: Difficulty or impatience
- CALCULATING: Evaluating options carefully
- INTEREST: Genuine interest signals
- NEUTRAL: No strong emotion detected

Integration with EmotionFuse safety mechanism:
- High-intensity negative emotions (>0.7 ANGER/FRUSTRATION) trigger human handoff
- EmotionAnalyzer provides structured output for safety checks
"""

from salesmate.agent.emotion.analyzer import (
    CustomerEmotion,
    EmotionAnalyzer,
    EmotionResult,
)

__all__ = [
    "CustomerEmotion",
    "EmotionResult",
    "EmotionAnalyzer",
]
