# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Human handoff notification and management for sales agent.

Provides Feishu-based notification system for human intervention:
- Low confidence (< 60%) triggers notification
- Emotion fuse (anger/frustration) triggers notification
- Sends interactive Feishu cards with customer context
- Pauses auto-replies until human responds

Example:
    >>> manager = HumanHandoffManager(feishu_client, redis_client)
    >>> await manager.notify_human(
    ...     customer_id="cust_123",
    ...     conversation_summary="Customer asked about pricing discount...",
    ...     ai_suggested_response="I can offer you a 10% discount...",
    ...     trigger_reason=HandoffTrigger.LOW_CONFIDENCE,
    ...     context={"confidence": 0.45}
    ... )
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from loguru import logger

from salemates.agent.models.customer import CustomerProfile, SalesStage


class HandoffTrigger(str, Enum):
    """Reason for human handoff."""

    LOW_CONFIDENCE = "low_confidence"  # Confidence score < 60%
    EMOTION_FUSE = "emotion_fuse"  # High anger/frustration detected
    GUARDRAIL_VIOLATION = "guardrail_violation"  # Price/contract violation
    MANUAL_REQUEST = "manual_request"  # Customer explicitly asked for human

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        """Human-readable trigger name for display."""
        names = {
            HandoffTrigger.LOW_CONFIDENCE: "低置信度",
            HandoffTrigger.EMOTION_FUSE: "情绪熔断",
            HandoffTrigger.GUARDRAIL_VIOLATION: "围栏触发",
            HandoffTrigger.MANUAL_REQUEST: "客户请求",
        }
        return names.get(self, self.value)


@dataclass
class HandoffConfig:
    """Configuration for human handoff system.

    Attributes:
        feishu_app_id: Feishu app ID for API calls.
        feishu_app_secret: Feishu app secret for API calls.
        handoff_group_id: Feishu group ID to send notifications to.
        pause_duration_hours: Hours to pause auto-replies (default: 24).
        enabled: Whether human handoff is enabled.
    """

    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    handoff_group_id: str = ""
    pause_duration_hours: int = 24
    enabled: bool = True

    def __post_init__(self) -> None:
        """Load from environment if not provided."""
        if not self.feishu_app_id:
            self.feishu_app_id = os.environ.get("FEISHU_APP_ID", "")
        if not self.feishu_app_secret:
            self.feishu_app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        if not self.handoff_group_id:
            self.handoff_group_id = os.environ.get("HUMAN_HANDOFF_GROUP_ID", "")


@dataclass
class HandoffState:
    """State of a paused conversation awaiting human intervention.

    Attributes:
        customer_id: ID of the customer conversation.
        chat_id: Feishu chat ID.
        trigger: Reason for handoff.
        paused_at: When auto-replies were paused.
        expires_at: When pause expires and auto-replies resume.
        notified: Whether human has been notified.
        human_responded: Whether human has taken over.
        notification_message_id: Feishu message ID of the notification card.
    """

    customer_id: str
    chat_id: str
    trigger: HandoffTrigger
    paused_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(hours=24))
    notified: bool = False
    human_responded: bool = False
    notification_message_id: str = ""

    def is_expired(self) -> bool:
        """Check if the pause has expired."""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for storage."""
        return {
            "customer_id": self.customer_id,
            "chat_id": self.chat_id,
            "trigger": self.trigger.value,
            "paused_at": self.paused_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "notified": self.notified,
            "human_responded": self.human_responded,
            "notification_message_id": self.notification_message_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffState":
        """Deserialize from dictionary."""
        return cls(
            customer_id=data["customer_id"],
            chat_id=data["chat_id"],
            trigger=HandoffTrigger(data["trigger"]),
            paused_at=datetime.fromisoformat(data["paused_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            notified=data.get("notified", False),
            human_responded=data.get("human_responded", False),
            notification_message_id=data.get("notification_message_id", ""),
        )


class HumanHandoffManager:
    """Manages human handoff notifications and auto-reply pauses.

    This class provides:
    1. Feishu notification with interactive cards
    2. Auto-reply pause state management
    3. Integration with ConfidenceRouter and EmotionFuse

    Attributes:
        config: Handoff configuration.
        feishu_client: Feishu API client (lark.Client).
        redis_client: Optional Redis client for state persistence.

    Example:
        >>> from lark_oapi import Client
        >>> import redis.asyncio as redis
        >>> client = Client.builder().app_id("...").app_secret("...").build()
        >>> redis_client = redis.Redis()
        >>> manager = HumanHandoffManager(config, client, redis_client)
        >>> await manager.notify_human(...)
    """

    # Redis key prefixes
    PAUSE_KEY_PREFIX = "salemates:handoff:pause:"
    STATE_KEY_PREFIX = "salemates:handoff:state:"

    def __init__(
        self,
        config: HandoffConfig | None = None,
        feishu_client: Any = None,
        redis_client: Any = None,
    ) -> None:
        """Initialize the human handoff manager.

        Args:
            config: Optional configuration. Uses env vars if not provided.
            feishu_client: Feishu API client (lark.Client instance).
            redis_client: Optional Redis async client for state persistence.
        """
        self.config = config or HandoffConfig()
        self.feishu_client = feishu_client
        self.redis_client = redis_client

    async def notify_human(
        self,
        customer_id: str,
        chat_id: str,
        conversation_summary: str,
        ai_suggested_response: str,
        trigger_reason: HandoffTrigger,
        context: dict[str, Any] | None = None,
        customer_profile: CustomerProfile | None = None,
    ) -> bool:
        """Send human handoff notification via Feishu.

        Sends an interactive card to the configured handoff group with:
        - Customer info and current stage
        - Conversation summary
        - AI's suggested response
        - "Take Over" button for human to accept

        Also pauses auto-replies for the conversation.

        Args:
            customer_id: ID of the customer.
            chat_id: Feishu chat ID where conversation is happening.
            conversation_summary: Summary of the conversation so far.
            ai_suggested_response: AI's proposed response that triggered handoff.
            trigger_reason: Why the handoff was triggered.
            context: Additional context (confidence score, emotion, etc.).
            customer_profile: Optional customer profile for display.

        Returns:
            True if notification was sent successfully, False otherwise.

        Example:
            >>> await manager.notify_human(
            ...     customer_id="cust_123",
            ...     chat_id="oc_xxxx",
            ...     conversation_summary="Customer is asking about 50% discount...",
            ...     ai_suggested_response="I understand you're looking for a discount...",
            ...     trigger_reason=HandoffTrigger.GUARDRAIL_VIOLATION,
            ...     context={"violation_type": "price", "discount_requested": 50}
            ... )
        """
        if not self.config.enabled:
            logger.warning(f"Human handoff is disabled, skipping notification for {customer_id}")
            return False

        if not self.feishu_client:
            logger.error("Feishu client not configured, cannot send notification")
            return False

        if not self.config.handoff_group_id:
            logger.error("HUMAN_HANDOFF_GROUP_ID not configured, cannot send notification")
            return False

        try:
            # Build the interactive card
            card_content = self._build_handoff_card(
                customer_id=customer_id,
                chat_id=chat_id,
                conversation_summary=conversation_summary,
                ai_suggested_response=ai_suggested_response,
                trigger_reason=trigger_reason,
                context=context,
                customer_profile=customer_profile,
            )

            # Send to handoff group
            message_id = await self._send_feishu_card(card_content)

            if message_id:
                # Pause auto-replies for this conversation
                await self._pause_auto_reply(
                    customer_id=customer_id,
                    chat_id=chat_id,
                    trigger=trigger_reason,
                    message_id=message_id,
                )

                logger.info(
                    f"Human handoff notification sent for customer {customer_id}, "
                    f"trigger: {trigger_reason}, message_id: {message_id}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to send human handoff notification: {e}")
            return False

    def _build_handoff_card(
        self,
        customer_id: str,
        chat_id: str,
        conversation_summary: str,
        ai_suggested_response: str,
        trigger_reason: HandoffTrigger,
        context: dict[str, Any] | None,
        customer_profile: CustomerProfile | None,
    ) -> dict[str, Any]:
        """Build Feishu interactive card JSON for handoff notification.

        Args:
            customer_id: Customer ID.
            chat_id: Feishu chat ID.
            conversation_summary: Summary of conversation.
            ai_suggested_response: AI's suggested response.
            trigger_reason: Why handoff was triggered.
            context: Additional context.
            customer_profile: Optional customer profile.

        Returns:
            Card JSON structure for Feishu API.
        """
        # Build customer info section
        customer_info = "未知客户"
        stage_display = "新建联系"
        if customer_profile:
            customer_info = f"{customer_profile.name or customer_id}"
            if customer_profile.company:
                customer_info += f" ({customer_profile.company})"
            stage_display = self._get_stage_display(customer_profile.stage)

        # Build context info
        context_lines = []
        if context:
            if "confidence" in context:
                context_lines.append(f"置信度: {context['confidence']:.1%}")
            if "emotion" in context:
                context_lines.append(f"情绪: {context['emotion']}")
            if "intensity" in context:
                context_lines.append(f"强度: {context['intensity']:.2f}")
            if "violation_type" in context:
                context_lines.append(f"违规类型: {context['violation_type']}")

        # Truncate long texts
        summary_display = conversation_summary[:500] + (
            "..." if len(conversation_summary) > 500 else ""
        )
        response_display = ai_suggested_response[:800] + (
            "..." if len(ai_suggested_response) > 800 else ""
        )

        # Build card elements
        elements = [
            # Header with trigger reason
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🚨 人工接管请求**\n触发原因: {trigger_reason.display_name}",
                },
            },
            # Divider
            {"tag": "hr"},
            # Customer info
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**客户信息**\n{customer_info}"},
                    },
                    {
                        "is_short": True,
                        "text": {"tag": "lark_md", "content": f"**销售阶段**\n{stage_display}"},
                    },
                ],
            },
        ]

        # Add context info if available
        if context_lines:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**上下文信息**\n{' | '.join(context_lines)}",
                    },
                }
            )

        # Add conversation summary
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**对话摘要**\n{summary_display}",
                    },
                },
            ]
        )

        # Add AI suggested response (if not empty)
        if response_display.strip():
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**AI 建议回复**\n```\n{response_display}\n```",
                    },
                }
            )

        # Add action buttons
        elements.extend(
            [
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "接管对话"},
                            "type": "primary",
                            "value": {
                                "action": "takeover",
                                "customer_id": customer_id,
                                "chat_id": chat_id,
                            },
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看详情"},
                            "type": "default",
                            "value": {
                                "action": "view_details",
                                "customer_id": customer_id,
                                "chat_id": chat_id,
                            },
                        },
                    ],
                },
                # Note section
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"自动回复已暂停 {self.config.pause_duration_hours} 小时 | 客户ID: {customer_id}",
                        }
                    ],
                },
            ]
        )

        # Build complete card
        card = {
            "type": "template",
            "data": {
                "template_id": "AAqk3R8J",  # Default template or custom
                "template_variable": {
                    "elements": elements,
                },
            },
        }

        # Alternative: direct card JSON (no template)
        direct_card = {
            "config": {"wide_screen_mode": True},
            "elements": elements,
        }

        return direct_card

    async def _send_feishu_card(self, card_content: dict[str, Any]) -> str | None:
        """Send interactive card to Feishu group.

        Args:
            card_content: Card JSON structure.

        Returns:
            Message ID if successful, None otherwise.
        """
        if not self.feishu_client:
            return None

        try:
            # Import here to handle optional dependency
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            content = json.dumps(card_content, ensure_ascii=False)

            request = (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(self.config.handoff_group_id)
                    .msg_type("interactive")
                    .content(content)
                    .build()
                )
                .build()
            )

            response = self.feishu_client.im.v1.message.create(request)

            if response.success():
                return response.data.message_id
            else:
                logger.error(
                    f"Failed to send Feishu card: code={response.code}, msg={response.msg}"
                )
                return None

        except ImportError:
            logger.warning("lark-oapi not installed, cannot send Feishu card")
            return None
        except Exception as e:
            logger.error(f"Error sending Feishu card: {e}")
            return None

    async def _pause_auto_reply(
        self,
        customer_id: str,
        chat_id: str,
        trigger: HandoffTrigger,
        message_id: str,
    ) -> None:
        """Pause auto-replies for a conversation.

        Stores the pause state in Redis with expiration.

        Args:
            customer_id: Customer ID.
            chat_id: Feishu chat ID.
            trigger: Handoff trigger reason.
            message_id: Notification message ID.
        """
        state = HandoffState(
            customer_id=customer_id,
            chat_id=chat_id,
            trigger=trigger,
            notified=True,
            notification_message_id=message_id,
        )
        state.expires_at = datetime.utcnow() + timedelta(hours=self.config.pause_duration_hours)

        if self.redis_client:
            try:
                # Store pause state with expiration
                pause_key = f"{self.PAUSE_KEY_PREFIX}{chat_id}"
                state_key = f"{self.STATE_KEY_PREFIX}{customer_id}"

                await self.redis_client.setex(
                    pause_key,
                    self.config.pause_duration_hours * 3600,
                    json.dumps(state.to_dict()),
                )
                await self.redis_client.setex(
                    state_key,
                    self.config.pause_duration_hours * 3600,
                    json.dumps(state.to_dict()),
                )

                logger.info(
                    f"Auto-reply paused for {customer_id} until {state.expires_at.isoformat()}"
                )
            except Exception as e:
                logger.error(f"Failed to store pause state in Redis: {e}")
        else:
            logger.warning("No Redis client, pause state will not persist")

    async def is_auto_reply_paused(self, chat_id: str) -> bool:
        """Check if auto-replies are paused for a chat.

        Args:
            chat_id: Feishu chat ID to check.

        Returns:
            True if auto-replies are paused, False otherwise.
        """
        if not self.redis_client:
            return False

        try:
            pause_key = f"{self.PAUSE_KEY_PREFIX}{chat_id}"
            result = await self.redis_client.get(pause_key)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check pause state: {e}")
            return False

    async def get_handoff_state(self, customer_id: str) -> HandoffState | None:
        """Get the current handoff state for a customer.

        Args:
            customer_id: Customer ID to look up.

        Returns:
            HandoffState if exists and not expired, None otherwise.
        """
        if not self.redis_client:
            return None

        try:
            state_key = f"{self.STATE_KEY_PREFIX}{customer_id}"
            data = await self.redis_client.get(state_key)

            if data:
                state = HandoffState.from_dict(json.loads(data))
                if not state.is_expired():
                    return state

            return None
        except Exception as e:
            logger.error(f"Failed to get handoff state: {e}")
            return None

    async def resume_auto_reply(self, chat_id: str, customer_id: str) -> bool:
        """Resume auto-replies for a conversation.

        Called when human takes over or pause expires.

        Args:
            chat_id: Feishu chat ID.
            customer_id: Customer ID.

        Returns:
            True if successfully resumed, False otherwise.
        """
        if not self.redis_client:
            return False

        try:
            pause_key = f"{self.PAUSE_KEY_PREFIX}{chat_id}"
            state_key = f"{self.STATE_KEY_PREFIX}{customer_id}"

            await self.redis_client.delete(pause_key)
            await self.redis_client.delete(state_key)

            logger.info(f"Auto-reply resumed for {customer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume auto-reply: {e}")
            return False

    async def mark_human_responded(self, customer_id: str) -> bool:
        """Mark that a human has responded to the handoff.

        Args:
            customer_id: Customer ID.

        Returns:
            True if successfully updated, False otherwise.
        """
        state = await self.get_handoff_state(customer_id)
        if not state:
            return False

        state.human_responded = True

        if self.redis_client:
            try:
                state_key = f"{self.STATE_KEY_PREFIX}{customer_id}"
                await self.redis_client.set(
                    state_key,
                    json.dumps(state.to_dict()),
                    ex=self.config.pause_duration_hours * 3600,
                )
                return True
            except Exception as e:
                logger.error(f"Failed to update handoff state: {e}")
                return False

        return False

    def _get_stage_display(self, stage: SalesStage) -> str:
        """Get display name for sales stage.

        Args:
            stage: SalesStage enum value.

        Returns:
            Chinese display name for the stage.
        """
        stage_names = {
            SalesStage.NEW_CONTACT: "新建联系",
            SalesStage.DISCOVERY: "需求挖掘",
            SalesStage.PRESENTATION: "方案展示",
            SalesStage.NEGOTIATION: "谈判协商",
            SalesStage.CLOSE: "已成交",
            SalesStage.LOST: "已流失",
        }
        return stage_names.get(stage, stage.value)


def create_handoff_manager(
    feishu_app_id: str | None = None,
    feishu_app_secret: str | None = None,
    handoff_group_id: str | None = None,
    feishu_client: Any = None,
    redis_client: Any = None,
    pause_duration_hours: int = 24,
) -> HumanHandoffManager:
    """Create a HumanHandoffManager with configuration.

    Convenience function to quickly set up a handoff manager.

    Args:
        feishu_app_id: Optional Feishu app ID (defaults to env var).
        feishu_app_secret: Optional Feishu app secret (defaults to env var).
        handoff_group_id: Optional group ID (defaults to env var).
        feishu_client: Feishu API client instance.
        redis_client: Redis async client for state persistence.
        pause_duration_hours: Hours to pause auto-replies.

    Returns:
        Configured HumanHandoffManager instance.

    Example:
        >>> from lark_oapi import Client
        >>> client = Client.builder().app_id("...").app_secret("...").build()
        >>> manager = create_handoff_manager(
        ...     handoff_group_id="oc_xxxx",
        ...     feishu_client=client
        ... )
    """
    config = HandoffConfig(
        feishu_app_id=feishu_app_id or "",
        feishu_app_secret=feishu_app_secret or "",
        handoff_group_id=handoff_group_id or "",
        pause_duration_hours=pause_duration_hours,
    )
    return HumanHandoffManager(
        config=config, feishu_client=feishu_client, redis_client=redis_client
    )
