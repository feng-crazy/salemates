# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Customer emotion analyzer for sales conversations.

This module provides emotion detection capabilities using LLM-based analysis.
The analyzer identifies 7 emotion types and provides intensity scores for
safety mechanism integration (EmotionFuse).
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from salemates.agent.emotion.prompts import (
    EMOTION_JSON_SCHEMA,
    get_emotion_analysis_prompt,
)
from salemates.providers.base import LLMProvider


class CustomerEmotion(str, Enum):
    """Customer emotion types detected during sales conversations.

    Each emotion type corresponds to specific signals and triggers
    different response strategies:

    - HESITATION: Uncertainty, need time to consider → SPIN questioning
    - TRUST: Positive recognition, confidence → Advance to next stage
    - ANGER: Strong dissatisfaction, threats → Human handoff (fuse trigger)
    - FRUSTRATION: Impatience, annoyance → Simplify response, quick answers
    - CALCULATING: Rational analysis, comparison → Value proposition
    - INTEREST: Curiosity, wanting more info → Product details
    - NEUTRAL: No strong emotion → Standard response
    """

    HESITATION = "HESITATION"
    TRUST = "TRUST"
    ANGER = "ANGER"
    FRUSTRATION = "FRUSTRATION"
    CALCULATING = "CALCULATING"
    INTEREST = "INTEREST"
    NEUTRAL = "NEUTRAL"

    def __str__(self) -> str:
        """Return the string value of the emotion."""
        return self.value

    @property
    def is_negative(self) -> bool:
        """Check if this is a negative emotion requiring attention.

        Returns:
            True if the emotion is negative (ANGER, FRUSTRATION), False otherwise.
        """
        return self in (CustomerEmotion.ANGER, CustomerEmotion.FRUSTRATION)

    @property
    def is_positive(self) -> bool:
        """Check if this is a positive emotion indicating progress.

        Returns:
            True if the emotion is positive (TRUST, INTEREST), False otherwise.
        """
        return self in (CustomerEmotion.TRUST, CustomerEmotion.INTEREST)


@dataclass
class EmotionResult:
    """Result of emotion analysis for a customer message.

    Attributes:
        emotion: The detected primary emotion type.
        intensity: Emotion intensity score (0.0-1.0).
            - 0.0-0.3: Low intensity
            - 0.4-0.6: Medium intensity
            - 0.7-1.0: High intensity (triggers safety mechanisms for negative emotions)
        signals: List of detected signal words or expressions.
        reasoning: Brief explanation of the analysis.
    """

    emotion: CustomerEmotion
    intensity: float
    signals: list[str] = field(default_factory=list)
    reasoning: str = ""

    def __post_init__(self) -> None:
        """Validate intensity is within bounds."""
        self.intensity = max(0.0, min(1.0, self.intensity))

    @property
    def is_high_intensity_negative(self) -> bool:
        """Check if this is a high-intensity negative emotion.

        High-intensity negative emotions (>0.7) should trigger
        the EmotionFuse safety mechanism for human handoff.

        Returns:
            True if negative emotion with intensity > 0.7.
        """
        return self.emotion.is_negative and self.intensity > 0.7

    @property
    def should_handoff(self) -> bool:
        """Check if this emotion requires human handoff.

        Returns:
            True if human handoff is recommended.
        """
        return self.is_high_intensity_negative

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the emotion result.
        """
        return {
            "emotion": self.emotion.value,
            "intensity": self.intensity,
            "signals": self.signals,
            "reasoning": self.reasoning,
        }


class EmotionAnalyzer:
    """Analyzes customer emotions in sales conversations using LLM.

    This analyzer uses a structured LLM prompt to detect emotions
    and provide intensity scores. It integrates with the EmotionFuse
    safety mechanism for negative emotion handling.

    Example:
        >>> analyzer = EmotionAnalyzer(llm_provider)
        >>> result = await analyzer.analyze("我再考虑一下")
        >>> print(result.emotion)
        CustomerEmotion.HESITATION
        >>> print(result.intensity)
        0.6
    """

    # Default model for emotion analysis (can be smaller/faster)
    DEFAULT_MODEL = "anthropic/claude-sonnet-4-5"

    def __init__(
        self,
        llm_provider: LLMProvider,
        model: str | None = None,
    ) -> None:
        """Initialize the emotion analyzer.

        Args:
            llm_provider: The LLM provider for making completion requests.
            model: Optional model override (defaults to claude-sonnet-4-5).
        """
        self.llm_provider = llm_provider
        self.model = model or self.DEFAULT_MODEL

    async def analyze(self, message: str) -> EmotionResult:
        """Analyze the emotion in a customer message.

        Uses LLM with structured output to detect emotion type, intensity,
        and signals. Falls back to NEUTRAL on parsing errors.

        Args:
            message: The customer message to analyze.

        Returns:
            EmotionResult with detected emotion, intensity, and signals.
        """
        if not message or not message.strip():
            return EmotionResult(
                emotion=CustomerEmotion.NEUTRAL,
                intensity=0.0,
                signals=[],
                reasoning="Empty message",
            )

        prompt = get_emotion_analysis_prompt(message)

        try:
            response = await self.llm_provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                max_tokens=500,
                temperature=0.3,  # Lower temperature for consistent analysis
            )

            if not response.content:
                logger.warning("Empty LLM response for emotion analysis")
                return self._create_fallback_result(message)

            # Parse the JSON response
            return self._parse_response(response.content, message)

        except Exception as e:
            logger.error(f"Error analyzing emotion: {e}")
            return self._create_fallback_result(message)

    def _parse_response(self, content: str, original_message: str) -> EmotionResult:
        """Parse LLM response into EmotionResult.

        Args:
            content: The raw LLM response content.
            original_message: The original message being analyzed (for fallback).

        Returns:
            Parsed EmotionResult or fallback result on error.
        """
        try:
            # Try to extract JSON from the response
            # LLM might wrap in markdown code blocks
            json_content = self._extract_json(content)
            data = json.loads(json_content)

            # Validate against schema
            self._validate_response(data)

            # Parse emotion
            emotion_str = data.get("emotion", "NEUTRAL")
            try:
                emotion = CustomerEmotion(emotion_str)
            except ValueError:
                logger.warning(f"Unknown emotion type: {emotion_str}, defaulting to NEUTRAL")
                emotion = CustomerEmotion.NEUTRAL

            return EmotionResult(
                emotion=emotion,
                intensity=float(data.get("intensity", 0.5)),
                signals=data.get("signals", []),
                reasoning=data.get("reasoning", ""),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse emotion JSON: {e}")
            return self._create_fallback_result(original_message)
        except Exception as e:
            logger.error(f"Error parsing emotion response: {e}")
            return self._create_fallback_result(original_message)

    def _extract_json(self, content: str) -> str:
        """Extract JSON from potentially markdown-wrapped content.

        Args:
            content: Raw LLM response content.

        Returns:
            Extracted JSON string.
        """
        content = content.strip()

        # Check for markdown code block
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```) and last line (```)
            if len(lines) > 2:
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        return content.strip()

    def _validate_response(self, data: dict[str, Any]) -> None:
        """Validate response data against the schema.

        Args:
            data: Parsed JSON data.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        required_fields = ["emotion", "intensity", "signals"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        # Validate emotion is in the enum
        if data["emotion"] not in [e.value for e in CustomerEmotion]:
            raise ValueError(f"Invalid emotion value: {data['emotion']}")

        # Validate intensity range
        intensity = data.get("intensity", 0.5)
        if not isinstance(intensity, (int, float)) or not (0 <= intensity <= 1):
            raise ValueError(f"Invalid intensity value: {intensity}")

    def _create_fallback_result(self, message: str) -> EmotionResult:
        """Create a fallback result when analysis fails.

        Attempts simple keyword matching for basic emotion detection.

        Args:
            message: The original message being analyzed.

        Returns:
            Fallback EmotionResult based on keyword matching or NEUTRAL.
        """
        message_lower = message.lower()

        # Simple keyword matching for critical emotions
        anger_keywords = ["投诉", "骗子", "垃圾", "退款", "举报", "领导", "律师"]
        frustration_keywords = ["烦", "无语", "够了", "算了", "麻烦"]
        hesitation_keywords = ["考虑", "想想", "看看", "比较", "不确定"]

        for keyword in anger_keywords:
            if keyword in message_lower:
                return EmotionResult(
                    emotion=CustomerEmotion.ANGER,
                    intensity=0.7,
                    signals=[keyword],
                    reasoning=f"Fallback: detected '{keyword}' keyword",
                )

        for keyword in frustration_keywords:
            if keyword in message_lower:
                return EmotionResult(
                    emotion=CustomerEmotion.FRUSTRATION,
                    intensity=0.5,
                    signals=[keyword],
                    reasoning=f"Fallback: detected '{keyword}' keyword",
                )

        for keyword in hesitation_keywords:
            if keyword in message_lower:
                return EmotionResult(
                    emotion=CustomerEmotion.HESITATION,
                    intensity=0.5,
                    signals=[keyword],
                    reasoning=f"Fallback: detected '{keyword}' keyword",
                )

        return EmotionResult(
            emotion=CustomerEmotion.NEUTRAL,
            intensity=0.0,
            signals=[],
            reasoning="Fallback: no specific emotion signals detected",
        )
