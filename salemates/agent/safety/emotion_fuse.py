# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Emotion-triggered safety mechanism for sales agent.

Detects negative emotions and triggers appropriate safety actions:
- High anger/frustration intensity -> HUMAN_HANDOFF
- Trigger keywords detected -> PAUSE_AUTO_REPLY
- Normal operation -> CONTINUE

Example:
    >>> from salemates.agent.emotion import EmotionResult, CustomerEmotion
    >>> config = EmotionFuseConfig(anger_threshold=0.7)
    >>> fuse = EmotionFuse(config)
    >>> result = EmotionResult(emotion=CustomerEmotion.ANGER, intensity=0.8)
    >>> action = fuse.check(result, "我要投诉你们!")
    >>> print(action)
    FuseAction.HUMAN_HANDOFF
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from loguru import logger

from salemates.agent.emotion.analyzer import CustomerEmotion, EmotionResult

if TYPE_CHECKING:
    from salemates.agent.safety.human_handoff import HumanHandoffManager


class FuseAction(str, Enum):
    """Action to take based on emotion analysis.

    Each action represents a different handling strategy:
    - CONTINUE: Normal operation, proceed with AI response
    - PAUSE_AUTO_REPLY: Pause automated responses, flag for review
    - HUMAN_HANDOFF: Immediate human intervention required
    """

    CONTINUE = "CONTINUE"
    PAUSE_AUTO_REPLY = "PAUSE_AUTO_REPLY"
    HUMAN_HANDOFF = "HUMAN_HANDOFF"

    def __str__(self) -> str:
        """Return the string value of the action."""
        return self.value

    @property
    def requires_human(self) -> bool:
        """Check if this action requires human involvement.

        Returns:
            True if human involvement is needed (PAUSE_AUTO_REPLY or HUMAN_HANDOFF).
        """
        return self in (FuseAction.PAUSE_AUTO_REPLY, FuseAction.HUMAN_HANDOFF)


@dataclass
class EmotionFuseConfig:
    """Configuration for emotion fuse safety mechanism.

    Attributes:
        anger_threshold: Intensity threshold for anger to trigger handoff (default: 0.7).
        frustration_threshold: Intensity threshold for frustration to trigger handoff (default: 0.7).
        trigger_keywords: Keywords that trigger PAUSE_AUTO_REPLY (default: complaint words).
        enabled: Whether the emotion fuse is active.
    """

    anger_threshold: float = 0.7
    frustration_threshold: float = 0.7
    trigger_keywords: list[str] = field(default_factory=lambda: ["投诉", "领导", "律师", "退款"])
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate thresholds are in valid range."""
        if not 0.0 <= self.anger_threshold <= 1.0:
            raise ValueError(
                f"anger_threshold must be between 0.0 and 1.0, got {self.anger_threshold}"
            )
        if not 0.0 <= self.frustration_threshold <= 1.0:
            raise ValueError(
                f"frustration_threshold must be between 0.0 and 1.0, got {self.frustration_threshold}"
            )


@dataclass
class FuseCheckResult:
    """Result of emotion fuse check.

    Attributes:
        action: The recommended action to take.
        reason: Human-readable explanation for the action.
        triggered_keywords: Keywords that were detected (if any).
        emotion: The emotion that triggered the action (if applicable).
        intensity: The intensity score that triggered the action (if applicable).
    """

    action: FuseAction
    reason: str
    triggered_keywords: list[str] = field(default_factory=list)
    emotion: CustomerEmotion | None = None
    intensity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the fuse check result.
        """
        return {
            "action": self.action.value,
            "reason": self.reason,
            "triggered_keywords": self.triggered_keywords,
            "emotion": self.emotion.value if self.emotion else None,
            "intensity": self.intensity,
        }


class EmotionFuse:
    """Emotion-triggered safety mechanism for human handoff.

    Analyzes emotion results and triggers appropriate safety actions
    based on intensity thresholds and trigger keywords.

    Trigger Logic:
        1. ANGER intensity >= anger_threshold -> HUMAN_HANDOFF
        2. FRUSTRATION intensity >= frustration_threshold -> HUMAN_HANDOFF
        3. Trigger keyword in message -> PAUSE_AUTO_REPLY
        4. Otherwise -> CONTINUE

    Attributes:
        config: Configuration for thresholds and keywords.

    Example:
        >>> from salemates.agent.emotion import EmotionResult, CustomerEmotion
        >>> fuse = EmotionFuse()
        >>> result = EmotionResult(emotion=CustomerEmotion.ANGER, intensity=0.8)
        >>> action = fuse.check(result, "我要投诉")
        >>> print(action)
        FuseAction.HUMAN_HANDOFF

        >>> result = EmotionResult(emotion=CustomerEmotion.NEUTRAL, intensity=0.2)
        >>> action = fuse.check(result, "这个产品怎么样")
        >>> print(action)
        FuseAction.CONTINUE
    """

    def __init__(self, config: EmotionFuseConfig | None = None) -> None:
        """Initialize the emotion fuse.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or EmotionFuseConfig()

    def check(self, emotion_result: EmotionResult, message: str) -> FuseAction:
        """Check emotion result and determine appropriate action.

        Args:
            emotion_result: The emotion analysis result from EmotionAnalyzer.
            message: The original customer message for keyword detection.

        Returns:
            FuseAction indicating how to proceed.

        Example:
            >>> from salemates.agent.emotion import EmotionResult, CustomerEmotion
            >>> fuse = EmotionFuse()
            >>> result = EmotionResult(emotion=CustomerEmotion.ANGER, intensity=0.8)
            >>> fuse.check(result, "我要投诉")
            FuseAction.HUMAN_HANDOFF
        """
        result = self.check_with_details(emotion_result, message)
        return result.action

    def check_with_details(self, emotion_result: EmotionResult, message: str) -> FuseCheckResult:
        """Check emotion result with detailed information.

        Provides full details about why a particular action was triggered,
        useful for logging and debugging.

        Args:
            emotion_result: The emotion analysis result from EmotionAnalyzer.
            message: The original customer message for keyword detection.

        Returns:
            FuseCheckResult with action, reason, and trigger details.

        Example:
            >>> from salemates.agent.emotion import EmotionResult, CustomerEmotion
            >>> fuse = EmotionFuse()
            >>> result = EmotionResult(emotion=CustomerEmotion.ANGER, intensity=0.8)
            >>> detail = fuse.check_with_details(result, "我要投诉")
            >>> print(detail.action)
            FuseAction.HUMAN_HANDOFF
            >>> print(detail.reason)
            'High anger intensity (0.80) exceeds threshold (0.70)'
        """
        if not self.config.enabled:
            return FuseCheckResult(
                action=FuseAction.CONTINUE,
                reason="Emotion fuse is disabled",
            )

        emotion = emotion_result.emotion
        intensity = emotion_result.intensity

        # Check for high-intensity anger
        if emotion == CustomerEmotion.ANGER and intensity >= self.config.anger_threshold:
            reason = (
                f"High anger intensity ({intensity:.2f}) exceeds "
                f"threshold ({self.config.anger_threshold:.2f})"
            )
            logger.warning(
                f"EmotionFuse triggered HUMAN_HANDOFF: {reason} | message preview: {message[:50]}"
            )
            return FuseCheckResult(
                action=FuseAction.HUMAN_HANDOFF,
                reason=reason,
                emotion=emotion,
                intensity=intensity,
            )

        # Check for high-intensity frustration
        if (
            emotion == CustomerEmotion.FRUSTRATION
            and intensity >= self.config.frustration_threshold
        ):
            reason = (
                f"High frustration intensity ({intensity:.2f}) exceeds "
                f"threshold ({self.config.frustration_threshold:.2f})"
            )
            logger.warning(
                f"EmotionFuse triggered HUMAN_HANDOFF: {reason} | message preview: {message[:50]}"
            )
            return FuseCheckResult(
                action=FuseAction.HUMAN_HANDOFF,
                reason=reason,
                emotion=emotion,
                intensity=intensity,
            )

        # Check for trigger keywords in message
        message_lower = message.lower()
        triggered_keywords = [
            keyword for keyword in self.config.trigger_keywords if keyword.lower() in message_lower
        ]

        if triggered_keywords:
            reason = f"Trigger keywords detected: {', '.join(triggered_keywords)}"
            logger.warning(
                f"EmotionFuse triggered PAUSE_AUTO_REPLY: {reason} | "
                f"emotion: {emotion.value} | intensity: {intensity:.2f}"
            )
            return FuseCheckResult(
                action=FuseAction.PAUSE_AUTO_REPLY,
                reason=reason,
                triggered_keywords=triggered_keywords,
                emotion=emotion,
                intensity=intensity,
            )

        # Normal operation - continue
        logger.debug(
            f"EmotionFuse: CONTINUE | emotion: {emotion.value} | intensity: {intensity:.2f}"
        )
        return FuseCheckResult(
            action=FuseAction.CONTINUE,
            reason=f"Normal operation - emotion: {emotion.value}, intensity: {intensity:.2f}",
            emotion=emotion,
            intensity=intensity,
        )

    def should_handoff(self, emotion_result: EmotionResult, message: str) -> bool:
        """Quick check if human handoff is needed.

        Args:
            emotion_result: The emotion analysis result.
            message: The customer message.

        Returns:
            True if HUMAN_HANDOFF action is recommended.

        Example:
            >>> from salemates.agent.emotion import EmotionResult, CustomerEmotion
            >>> fuse = EmotionFuse()
            >>> result = EmotionResult(emotion=CustomerEmotion.ANGER, intensity=0.8)
            >>> fuse.should_handoff(result, "我要投诉")
            True
        """
        action = self.check(emotion_result, message)
        return action == FuseAction.HUMAN_HANDOFF

    def should_pause(self, emotion_result: EmotionResult, message: str) -> bool:
        """Check if auto-reply should be paused.

        Args:
            emotion_result: The emotion analysis result.
            message: The customer message.

        Returns:
            True if PAUSE_AUTO_REPLY or HUMAN_HANDOFF is recommended.

        Example:
            >>> from salemates.agent.emotion import EmotionResult, CustomerEmotion
            >>> fuse = EmotionFuse()
            >>> result = EmotionResult(emotion=CustomerEmotion.NEUTRAL, intensity=0.2)
            >>> fuse.should_pause(result, "我要找你们领导")
            True
        """
        action = self.check(emotion_result, message)
        return action.requires_human

    def is_enabled(self) -> bool:
        """Check if the emotion fuse is enabled.

        Returns:
            True if the emotion fuse is active.
        """
        return self.config.enabled

    def enable(self) -> None:
        """Enable the emotion fuse."""
        self.config.enabled = True
        logger.info("EmotionFuse enabled")

    def disable(self) -> None:
        """Disable the emotion fuse."""
        self.config.enabled = False
        logger.warning("EmotionFuse disabled")

    async def check_with_handoff(
        self,
        emotion_result: EmotionResult,
        message: str,
        handoff_manager: "HumanHandoffManager | None" = None,
        context: dict[str, Any] | None = None,
        conversation_summary: str = "",
        ai_suggested_response: str = "",
        customer_profile: Any = None,
    ) -> FuseCheckResult:
        """Check emotion and trigger human handoff if needed.

        Extends check_with_details() to automatically trigger human handoff
        notifications when HUMAN_HANDOFF or PAUSE_AUTO_REPLY action is triggered.

        Args:
            emotion_result: The emotion analysis result from EmotionAnalyzer.
            message: The original customer message for keyword detection.
            handoff_manager: Optional HumanHandoffManager for sending notifications.
            context: Context including customer_id and chat_id for handoff.
            conversation_summary: Summary of the conversation for handoff notification.
            ai_suggested_response: AI's proposed response for handoff context.
            customer_profile: Optional customer profile for display.

        Returns:
            FuseCheckResult with action, reason, and trigger details.

        Example:
            >>> from salemates.agent.safety.human_handoff import HumanHandoffManager
            >>> fuse = EmotionFuse()
            >>> handoff_manager = HumanHandoffManager(...)
            >>> result = EmotionResult(emotion=CustomerEmotion.ANGER, intensity=0.8)
            >>> check_result = await fuse.check_with_handoff(
            ...     result,
            ...     "我要投诉你们!",
            ...     handoff_manager=handoff_manager,
            ...     context={"customer_id": "cust_123", "chat_id": "oc_xxx"}
            ... )
        """
        result = self.check_with_details(emotion_result, message)

        if result.action.requires_human and handoff_manager:
            from salemates.agent.safety.human_handoff import HandoffTrigger

            ctx = context or {}
            customer_id = ctx.get("customer_id", "unknown")
            chat_id = ctx.get("chat_id", "")

            if chat_id:
                trigger = (
                    HandoffTrigger.EMOTION_FUSE
                    if result.action == FuseAction.HUMAN_HANDOFF
                    else HandoffTrigger.EMOTION_FUSE
                )

                await handoff_manager.notify_human(
                    customer_id=customer_id,
                    chat_id=chat_id,
                    conversation_summary=conversation_summary or message,
                    ai_suggested_response=ai_suggested_response,
                    trigger_reason=trigger,
                    context={
                        "emotion": result.emotion.value if result.emotion else None,
                        "intensity": result.intensity,
                        "triggered_keywords": result.triggered_keywords,
                    },
                    customer_profile=customer_profile,
                )

        return result


def create_default_emotion_fuse(
    anger_threshold: float = 0.7,
    frustration_threshold: float = 0.7,
    trigger_keywords: list[str] | None = None,
) -> EmotionFuse:
    """Create an EmotionFuse with default or custom settings.

    Convenience function to quickly create a configured EmotionFuse.

    Args:
        anger_threshold: Intensity threshold for anger (default: 0.7).
        frustration_threshold: Intensity threshold for frustration (default: 0.7).
        trigger_keywords: Optional custom trigger keywords.

    Returns:
        Configured EmotionFuse instance.

    Example:
        >>> fuse = create_default_emotion_fuse(anger_threshold=0.6)
        >>> fuse.config.anger_threshold
        0.6
    """
    config = EmotionFuseConfig(
        anger_threshold=anger_threshold,
        frustration_threshold=frustration_threshold,
        trigger_keywords=trigger_keywords or ["投诉", "领导", "律师", "退款"],
    )
    return EmotionFuse(config)
