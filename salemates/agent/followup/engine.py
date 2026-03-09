# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Proactive follow-up engine for sales automation.

Schedules and sends personalized follow-up messages based on
customer engagement signals and sales stage.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


@dataclass
class FollowUpConfig:
    """Configuration for follow-up rules.

    Attributes:
        delay_hours: Hours before sending follow-up (default: 24)
        max_followups: Maximum follow-ups per customer (default: 3)
        stages_priority: Stages that should have follow-ups
    """

    delay_hours: int = 24
    max_followups: int = 3
    stages_priority: list[str] = field(default_factory=lambda: ["presentation", "negotiation"])

    def __post_init__(self):
        if self.stages_priority is None:
            self.stages_priority = ["presentation", "negotiation"]


@dataclass
class FollowUpTask:
    """Represents a scheduled follow-up.

    Attributes:
        customer_id: Customer to follow up with
        scheduled_at: When to send the follow-up
        message_template: Template to use
        context: Conversation context for personalization
    """

    customer_id: str
    scheduled_at: datetime
    message_template: str
    context: dict

    def is_due(self) -> bool:
        """Check if follow-up is due."""
        return datetime.utcnow() >= self.scheduled_at


class FollowUpEngine:
    """Manages proactive follow-up scheduling and execution.

    This engine uses the existing VikingBot cron system to schedule
    personalized follow-up messages when customers become unresponsive.

    Rules:
    - If last_contact_at > delay_hours AND stage in priority stages
    - Generate personalized message referencing last conversation
    - Cancel follow-up if customer responds before scheduled time
    """

    def __init__(self, config: Optional[FollowUpConfig] = None):
        """Initialize follow-up engine.

        Args:
            config: Follow-up configuration.
        """
        self.config = config or FollowUpConfig()
        self.scheduled_tasks: dict[str, FollowUpTask] = {}
        self.logger = logger.bind(component="FollowUpEngine")

    def should_follow_up(
        self,
        customer_id: str,
        last_contact_at: datetime,
        stage: str,
        followup_count: int = 0,
    ) -> bool:
        """Determine if a customer should receive a follow-up.

        Args:
            customer_id: Customer ID.
            last_contact_at: Last contact timestamp.
            stage: Current sales stage.
            followup_count: Number of follow-ups already sent.

        Returns:
            True if follow-up should be scheduled.
        """
        # Check if max follow-ups reached
        if followup_count >= self.config.max_followups:
            self.logger.debug(
                f"Max follow-ups reached for {customer_id}",
                followup_count=followup_count,
            )
            return False

        # Check if enough time has passed
        hours_since_contact = (datetime.utcnow() - last_contact_at).total_seconds() / 3600

        if hours_since_contact < self.config.delay_hours:
            self.logger.debug(
                f"Not enough time passed for {customer_id}",
                hours=hours_since_contact,
                required=self.config.delay_hours,
            )
            return False

        # Check if stage is priority
        if stage not in self.config.stages_priority:
            self.logger.debug(
                f"Stage {stage} not in priority stages",
                priority_stages=self.config.stages_priority,
            )
            return False

        return True

    def schedule_followup(
        self,
        customer_id: str,
        delay_hours: Optional[int] = None,
        context: Optional[dict] = None,
    ) -> FollowUpTask:
        """Schedule a follow-up for a customer.

        Args:
            customer_id: Customer to follow up with.
            delay_hours: Hours until follow-up (uses config default if None).
            context: Conversation context for personalization.

        Returns:
            Scheduled FollowUpTask.
        """
        delay = delay_hours or self.config.delay_hours
        scheduled_at = datetime.utcnow() + timedelta(hours=delay)

        # Generate message template based on context
        message_template = self._generate_template(context)

        task = FollowUpTask(
            customer_id=customer_id,
            scheduled_at=scheduled_at,
            message_template=message_template,
            context=context or {},
        )

        self.scheduled_tasks[customer_id] = task
        self.logger.info(
            f"Scheduled follow-up for {customer_id}",
            scheduled_at=scheduled_at.isoformat(),
        )

        return task

    def cancel_followup(self, customer_id: str) -> bool:
        """Cancel a scheduled follow-up.

        Called when customer responds before follow-up is sent.

        Args:
            customer_id: Customer ID.

        Returns:
            True if follow-up was cancelled, False if not found.
        """
        if customer_id in self.scheduled_tasks:
            del self.scheduled_tasks[customer_id]
            self.logger.info(f"Cancelled follow-up for {customer_id}")
            return True
        return False

    def get_due_followups(self) -> list[FollowUpTask]:
        """Get all follow-ups that are due to be sent.

        Returns:
            List of due FollowUpTasks.
        """
        return [task for task in self.scheduled_tasks.values() if task.is_due()]

    def generate_message(
        self,
        task: FollowUpTask,
        customer_name: Optional[str] = None,
    ) -> str:
        """Generate personalized follow-up message.

        Args:
            task: Follow-up task with template and context.
            customer_name: Customer's name for personalization.

        Returns:
            Personalized message.
        """
        template = task.message_template
        context = task.context

        # Personalize with customer name
        if customer_name:
            template = template.replace("{customer_name}", customer_name)

        # Add context references
        last_topic = context.get("last_topic", "")
        if last_topic:
            template = template.replace("{last_topic}", last_topic)

        return template

    def _generate_template(self, context: Optional[dict]) -> str:
        """Generate message template based on context.

        Args:
            context: Conversation context.

        Returns:
            Message template with placeholders.
        """
        if not context:
            return (
                "{customer_name}您好，"
                "上次我们聊到{last_topic}，"
                "我这边刚好整理了一些相关资料，"
                "需要我发给您参考一下吗？"
            )

        stage = context.get("stage", "")

        if stage == "presentation":
            return (
                "{customer_name}您好，"
                "关于上次讨论的方案，"
                "我准备了一个和您行业类似的案例，"
                "发给您看看？"
            )

        if stage == "negotiation":
            return (
                "{customer_name}您好，"
                "上次我们聊到的{last_topic}，"
                "我这边有了一些新的想法，"
                "不知道您现在方便聊几句吗？"
            )

        return "{customer_name}您好，最近怎么样？关于{last_topic}的事情，您这边有什么新的进展吗？"
