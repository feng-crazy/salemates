# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Proactive follow-up engine for sales automation.

Triggers personalized follow-ups based on:
- Time since last contact (default: 24h)
- Sales stage (e.g., PRESENTATION stage priority)
- Customer engagement signals
- Scheduled reminders

Usage:
    >>> from salemates.agent.followup import FollowUpEngine, FollowUpConfig, FollowUpTask
    >>>
    >>> # Create engine with config
    >>> config = FollowUpConfig(delay_hours=24, max_followups=3)
    >>> engine = FollowUpEngine(config)
    >>>
    >>> # Schedule follow-up
    >>> task = engine.schedule_followup(
    ...     customer_id="abc123",
    ...     delay_hours=24,
    ...     context={"stage": "presentation", "last_topic": "pricing"}
    ... )
    >>>
    >>> # Cancel on customer response
    >>> engine.cancel_followup("abc123")
    >>>
    >>> # Get due follow-ups
    >>> due_tasks = engine.get_due_followups()
"""

from salemates.agent.followup.engine import (
    FollowUpConfig,
    FollowUpTask,
    FollowUpEngine,
)

__all__ = [
    # Engine
    "FollowUpEngine",
    "FollowUpConfig",
    "FollowUpTask",
]
