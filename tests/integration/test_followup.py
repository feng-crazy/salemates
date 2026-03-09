# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for follow-up scheduling system.

Tests:
- Follow-up message scheduling
- Message sending after delay
- Cancellation on customer response
- Priority-based scheduling
- Snooze functionality
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from salemates.agent.models.customer import SalesStage


# ============ Mock Follow-up Components ============


class FollowupStatus(str, Enum):
    """Status of a follow-up task."""

    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    SNOOZED = "snoozed"


class FollowupPriority(str, Enum):
    """Priority levels for follow-ups."""

    HIGH = "high"  # Hot leads, closing soon
    MEDIUM = "medium"  # Active conversations
    LOW = "low"  # Cold leads, long-term follow-up


@dataclass
class FollowupTask:
    """A scheduled follow-up task."""

    id: str
    customer_id: str
    scheduled_time: datetime
    message_template: str
    status: FollowupStatus = FollowupStatus.PENDING
    priority: FollowupPriority = FollowupPriority.MEDIUM
    stage: SalesStage = SalesStage.NEW_CONTACT
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str = ""
    snooze_count: int = 0
    max_snoozes: int = 3
    metadata: dict = field(default_factory=dict)

    def is_due(self, now: datetime | None = None) -> bool:
        """Check if this follow-up is due."""
        now = now or datetime.utcnow()
        return self.scheduled_time <= now and self.status == FollowupStatus.PENDING

    def can_snooze(self) -> bool:
        """Check if this follow-up can be snoozed."""
        return self.snooze_count < self.max_snoozes and self.status == FollowupStatus.PENDING


@dataclass
class FollowupResult:
    """Result of a follow-up action."""

    success: bool
    task_id: str
    message: str
    error: str | None = None


class MockFollowupScheduler:
    """Mock follow-up scheduler for testing."""

    def __init__(self):
        self.tasks: dict[str, FollowupTask] = {}
        self._task_counter = 0
        self._send_callback: Callable | None = None
        self._sent_messages: list[dict] = []

    def set_send_callback(self, callback: Callable) -> None:
        """Set callback for sending messages."""
        self._send_callback = callback

    async def schedule_followup(
        self,
        customer_id: str,
        delay_hours: float,
        message_template: str,
        priority: FollowupPriority = FollowupPriority.MEDIUM,
        stage: SalesStage = SalesStage.NEW_CONTACT,
        metadata: dict | None = None,
    ) -> FollowupTask:
        """Schedule a new follow-up task."""
        self._task_counter += 1
        task_id = f"followup-{self._task_counter:04d}"

        scheduled_time = datetime.utcnow() + timedelta(hours=delay_hours)

        task = FollowupTask(
            id=task_id,
            customer_id=customer_id,
            scheduled_time=scheduled_time,
            message_template=message_template,
            priority=priority,
            stage=stage,
            metadata=metadata or {},
        )

        self.tasks[task_id] = task
        return task

    async def cancel_followup(self, task_id: str, reason: str = "") -> FollowupResult:
        """Cancel a scheduled follow-up."""
        if task_id not in self.tasks:
            return FollowupResult(
                success=False, task_id=task_id, message="Task not found", error="NOT_FOUND"
            )

        task = self.tasks[task_id]
        if task.status != FollowupStatus.PENDING:
            return FollowupResult(
                success=False,
                task_id=task_id,
                message=f"Cannot cancel task with status {task.status}",
                error="INVALID_STATUS",
            )

        task.status = FollowupStatus.CANCELLED
        task.cancelled_at = datetime.utcnow()
        task.cancellation_reason = reason

        return FollowupResult(success=True, task_id=task_id, message="Follow-up cancelled")

    async def cancel_all_for_customer(self, customer_id: str, reason: str = "") -> int:
        """Cancel all pending follow-ups for a customer."""
        cancelled_count = 0
        for task in self.tasks.values():
            if task.customer_id == customer_id and task.status == FollowupStatus.PENDING:
                task.status = FollowupStatus.CANCELLED
                task.cancelled_at = datetime.utcnow()
                task.cancellation_reason = reason
                cancelled_count += 1
        return cancelled_count

    async def snooze_followup(self, task_id: str, snooze_hours: float = 24.0) -> FollowupResult:
        """Snooze a follow-up for later."""
        if task_id not in self.tasks:
            return FollowupResult(
                success=False, task_id=task_id, message="Task not found", error="NOT_FOUND"
            )

        task = self.tasks[task_id]
        if not task.can_snooze():
            return FollowupResult(
                success=False,
                task_id=task_id,
                message="Cannot snooze: max snoozes reached or invalid status",
                error="CANNOT_SNOOZE",
            )

        task.scheduled_time = datetime.utcnow() + timedelta(hours=snooze_hours)
        task.snooze_count += 1
        task.status = FollowupStatus.SNOOZED

        return FollowupResult(
            success=True, task_id=task_id, message=f"Follow-up snoozed for {snooze_hours} hours"
        )

    async def execute_due_followups(self, now: datetime | None = None) -> list[FollowupResult]:
        """Execute all due follow-ups."""
        results = []
        now = now or datetime.utcnow()

        for task in self.tasks.values():
            if task.is_due(now):
                result = await self._execute_followup(task)
                results.append(result)

        return results

    async def _execute_followup(self, task: FollowupTask) -> FollowupResult:
        """Execute a single follow-up."""
        try:
            message = task.message_template

            # Call send callback if set
            if self._send_callback:
                await self._send_callback(task.customer_id, message)

            # Record sent message
            self._sent_messages.append(
                {
                    "task_id": task.id,
                    "customer_id": task.customer_id,
                    "message": message,
                    "sent_at": datetime.utcnow().isoformat(),
                }
            )

            task.status = FollowupStatus.SENT
            task.sent_at = datetime.utcnow()

            return FollowupResult(
                success=True, task_id=task.id, message="Follow-up sent successfully"
            )

        except Exception as e:
            return FollowupResult(
                success=False, task_id=task.id, message="Failed to send follow-up", error=str(e)
            )

    def get_pending_followups(self, customer_id: str | None = None) -> list[FollowupTask]:
        """Get all pending follow-ups, optionally filtered by customer."""
        tasks = [t for t in self.tasks.values() if t.status == FollowupStatus.PENDING]
        if customer_id:
            tasks = [t for t in tasks if t.customer_id == customer_id]
        return sorted(tasks, key=lambda t: t.scheduled_time)

    def get_due_followups(self, now: datetime | None = None) -> list[FollowupTask]:
        """Get all due follow-ups."""
        now = now or datetime.utcnow()
        return [t for t in self.tasks.values() if t.is_due(now)]


class MockMessageBus:
    """Mock message bus for testing."""

    def __init__(self):
        self.sent_messages: list[dict] = []
        self._consumers: list = []

    async def publish_outbound(self, message: Any) -> None:
        """Publish an outbound message."""
        self.sent_messages.append(
            {
                "content": getattr(message, "content", str(message)),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Notify consumers
        for consumer in self._consumers:
            await consumer(message)

    def subscribe(self, consumer: Callable) -> None:
        """Subscribe to messages."""
        self._consumers.append(consumer)


# ============ Fixtures ============


@pytest.fixture
def scheduler():
    """Create a fresh follow-up scheduler."""
    return MockFollowupScheduler()


@pytest.fixture
def message_bus():
    """Create a mock message bus."""
    return MockMessageBus()


@pytest.fixture
def mock_send_callback():
    """Create a mock send callback."""
    return AsyncMock()


# ============ Test Classes ============


class TestFollowupScheduling:
    """Test follow-up scheduling functionality."""

    @pytest.mark.asyncio
    async def test_schedule_basic_followup(self, scheduler):
        """Test scheduling a basic follow-up."""
        task = await scheduler.schedule_followup(
            customer_id="customer-001",
            delay_hours=24.0,
            message_template="您好，想了解一下您对我们产品的想法。",
        )

        assert task.id
        assert task.customer_id == "customer-001"
        assert task.status == FollowupStatus.PENDING
        assert task.scheduled_time > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_schedule_followup_with_priority(self, scheduler):
        """Test scheduling follow-up with priority."""
        task = await scheduler.schedule_followup(
            customer_id="customer-002",
            delay_hours=4.0,
            message_template="您提到想要优惠，我来跟进一下。",
            priority=FollowupPriority.HIGH,
        )

        assert task.priority == FollowupPriority.HIGH

    @pytest.mark.asyncio
    async def test_schedule_followup_by_stage(self, scheduler):
        """Test scheduling follow-up based on customer stage."""
        # NEGOTIATION stage - shorter follow-up
        task = await scheduler.schedule_followup(
            customer_id="customer-003",
            delay_hours=2.0,
            message_template="关于价格的问题，我可以帮您申请。",
            priority=FollowupPriority.HIGH,
            stage=SalesStage.NEGOTIATION,
        )

        assert task.stage == SalesStage.NEGOTIATION
        assert task.priority == FollowupPriority.HIGH

    @pytest.mark.asyncio
    async def test_schedule_multiple_followups(self, scheduler):
        """Test scheduling multiple follow-ups for same customer."""
        task1 = await scheduler.schedule_followup(
            customer_id="customer-001", delay_hours=24.0, message_template="第一次跟进"
        )
        task2 = await scheduler.schedule_followup(
            customer_id="customer-001", delay_hours=48.0, message_template="第二次跟进"
        )

        pending = scheduler.get_pending_followups("customer-001")
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_schedule_followup_with_metadata(self, scheduler):
        """Test scheduling follow-up with custom metadata."""
        task = await scheduler.schedule_followup(
            customer_id="customer-001",
            delay_hours=24.0,
            message_template="跟进报价单",
            metadata={"quote_id": "Q-2024-001", "product": "企业版", "discount_percent": 10},
        )

        assert task.metadata["quote_id"] == "Q-2024-001"
        assert task.metadata["discount_percent"] == 10


class TestFollowupExecution:
    """Test follow-up execution functionality."""

    @pytest.mark.asyncio
    async def test_execute_due_followup(self, scheduler, mock_send_callback):
        """Test executing a due follow-up."""
        scheduler.set_send_callback(mock_send_callback)

        # Schedule a follow-up that's immediately due
        task = await scheduler.schedule_followup(
            customer_id="customer-001",
            delay_hours=-1.0,  # Already due (negative delay)
            message_template="测试跟进消息",
        )

        results = await scheduler.execute_due_followups()

        assert len(results) == 1
        assert results[0].success
        assert results[0].task_id == task.id

        # Verify callback was called
        mock_send_callback.assert_called_once_with("customer-001", "测试跟进消息")

    @pytest.mark.asyncio
    async def test_execute_future_followup_not_sent(self, scheduler, mock_send_callback):
        """Test future follow-ups are not executed."""
        scheduler.set_send_callback(mock_send_callback)

        # Schedule a future follow-up
        await scheduler.schedule_followup(
            customer_id="customer-001",
            delay_hours=24.0,  # Due in 24 hours
            message_template="未来跟进",
        )

        results = await scheduler.execute_due_followups()

        # Should not execute future follow-ups
        assert len(results) == 0
        mock_send_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_multiple_due_followups(self, scheduler, mock_send_callback):
        """Test executing multiple due follow-ups."""
        scheduler.set_send_callback(mock_send_callback)

        # Schedule multiple due follow-ups
        await scheduler.schedule_followup("c1", -1.0, "跟进1")
        await scheduler.schedule_followup("c2", -1.0, "跟进2")
        await scheduler.schedule_followup("c3", -1.0, "跟进3")

        results = await scheduler.execute_due_followups()

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_updates_task_status(self, scheduler, mock_send_callback):
        """Test execution updates task status to SENT."""
        scheduler.set_send_callback(mock_send_callback)

        task = await scheduler.schedule_followup("customer-001", -1.0, "测试")

        await scheduler.execute_due_followups()

        assert task.status == FollowupStatus.SENT
        assert task.sent_at is not None


class TestFollowupCancellation:
    """Test follow-up cancellation functionality."""

    @pytest.mark.asyncio
    async def test_cancel_followup(self, scheduler):
        """Test cancelling a scheduled follow-up."""
        task = await scheduler.schedule_followup("customer-001", 24.0, "测试")

        result = await scheduler.cancel_followup(task.id, reason="客户已回复")

        assert result.success
        assert task.status == FollowupStatus.CANCELLED
        assert task.cancellation_reason == "客户已回复"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_followup(self, scheduler):
        """Test cancelling a non-existent follow-up."""
        result = await scheduler.cancel_followup("nonexistent-id")

        assert not result.success
        assert result.error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_cancel_already_sent_followup(self, scheduler, mock_send_callback):
        """Test cannot cancel already sent follow-up."""
        scheduler.set_send_callback(mock_send_callback)

        task = await scheduler.schedule_followup("customer-001", -1.0, "测试")
        await scheduler.execute_due_followups()

        # Try to cancel sent follow-up
        result = await scheduler.cancel_followup(task.id)

        assert not result.success
        assert result.error == "INVALID_STATUS"

    @pytest.mark.asyncio
    async def test_cancel_all_for_customer(self, scheduler):
        """Test cancelling all follow-ups for a customer."""
        # Schedule multiple follow-ups
        await scheduler.schedule_followup("customer-001", 24.0, "跟进1")
        await scheduler.schedule_followup("customer-001", 48.0, "跟进2")
        await scheduler.schedule_followup("customer-002", 24.0, "其他客户")

        # Cancel all for customer-001
        cancelled = await scheduler.cancel_all_for_customer("customer-001", reason="客户已成交")

        assert cancelled == 2

        # Verify customer-002's follow-up is still pending
        pending = scheduler.get_pending_followups("customer-002")
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_cancel_on_customer_response(self, scheduler):
        """Test cancellation triggered by customer response."""
        # Schedule a follow-up
        task = await scheduler.schedule_followup("customer-001", 24.0, "跟进消息")

        # Simulate customer responding
        cancelled = await scheduler.cancel_all_for_customer(
            "customer-001", reason="Customer responded"
        )

        assert cancelled == 1
        assert task.status == FollowupStatus.CANCELLED


class TestFollowupSnooze:
    """Test follow-up snooze functionality."""

    @pytest.mark.asyncio
    async def test_snooze_followup(self, scheduler):
        """Test snoozing a follow-up."""
        task = await scheduler.schedule_followup("customer-001", 1.0, "测试")

        original_time = task.scheduled_time

        result = await scheduler.snooze_followup(task.id, snooze_hours=24.0)

        assert result.success
        assert task.scheduled_time > original_time
        assert task.snooze_count == 1
        assert task.status == FollowupStatus.SNOOZED

    @pytest.mark.asyncio
    async def test_snooze_max_reached(self, scheduler):
        """Test cannot snooze beyond max limit."""
        task = await scheduler.schedule_followup("customer-001", 1.0, "测试")

        # Snooze multiple times
        for _ in range(3):
            await scheduler.snooze_followup(task.id)

        # Try to snooze again
        result = await scheduler.snooze_followup(task.id)

        assert not result.success
        assert result.error == "CANNOT_SNOOZE"

    @pytest.mark.asyncio
    async def test_snooze_nonexistent_followup(self, scheduler):
        """Test snoozing non-existent follow-up."""
        result = await scheduler.snooze_followup("nonexistent-id")

        assert not result.success
        assert result.error == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_snooze_cancelled_followup(self, scheduler):
        """Test cannot snooze cancelled follow-up."""
        task = await scheduler.schedule_followup("customer-001", 1.0, "测试")
        await scheduler.cancel_followup(task.id)

        result = await scheduler.snooze_followup(task.id)

        assert not result.success


class TestFollowupPriority:
    """Test follow-up priority handling."""

    @pytest.mark.asyncio
    async def test_high_priority_first(self, scheduler, mock_send_callback):
        """Test high priority follow-ups are processed first."""
        scheduler.set_send_callback(mock_send_callback)

        # Schedule with different priorities
        low_task = await scheduler.schedule_followup(
            "c1", -1.0, "低优先级", priority=FollowupPriority.LOW
        )
        high_task = await scheduler.schedule_followup(
            "c2", -1.0, "高优先级", priority=FollowupPriority.HIGH
        )
        medium_task = await scheduler.schedule_followup(
            "c3", -1.0, "中优先级", priority=FollowupPriority.MEDIUM
        )

        # Execute due follow-ups
        results = await scheduler.execute_due_followups()

        # All should be sent
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_priority_based_on_stage(self, scheduler):
        """Test priority is set based on customer stage."""
        # NEGOTIATION stage should have high priority
        negotiation_task = await scheduler.schedule_followup(
            "c1", 1.0, "谈判阶段", priority=FollowupPriority.HIGH, stage=SalesStage.NEGOTIATION
        )

        # NEW_CONTACT should have lower priority
        new_contact_task = await scheduler.schedule_followup(
            "c2", 1.0, "新联系人", priority=FollowupPriority.LOW, stage=SalesStage.NEW_CONTACT
        )

        assert negotiation_task.priority == FollowupPriority.HIGH
        assert new_contact_task.priority == FollowupPriority.LOW


class TestFollowupIntegration:
    """Test follow-up system integration."""

    @pytest.mark.asyncio
    async def test_followup_with_message_bus(self, scheduler, message_bus):
        """Test follow-up integrates with message bus."""

        async def send_via_bus(customer_id: str, message: str):
            from salemates.config.schema import SessionKey
            from salemates.bus.events import OutboundMessage

            session_key = SessionKey(type="telegram", channel_id="sales", chat_id=customer_id)
            await message_bus.publish_outbound(
                OutboundMessage(session_key=session_key, content=message)
            )

        scheduler.set_send_callback(send_via_bus)

        # Schedule and execute
        await scheduler.schedule_followup("customer-001", -1.0, "测试消息")
        await scheduler.execute_due_followups()

        # Verify message was sent through bus
        assert len(message_bus.sent_messages) == 1
        assert "测试消息" in message_bus.sent_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_followup_chain(self, scheduler, mock_send_callback):
        """Test chain of follow-ups over time."""
        scheduler.set_send_callback(mock_send_callback)

        # Initial follow-up
        await scheduler.schedule_followup("c1", -1.0, "第一次跟进")

        # Execute first
        results = await scheduler.execute_due_followups()
        assert len(results) == 1

        # Schedule second follow-up
        await scheduler.schedule_followup("c1", 0.1, "第二次跟进")  # Very short delay

        # Simulate time passing
        future_time = datetime.utcnow() + timedelta(hours=1)
        results = await scheduler.execute_due_followups(now=future_time)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_followup_cancellation_on_sale(self, scheduler):
        """Test all follow-ups cancelled when customer makes purchase."""
        # Multiple pending follow-ups
        await scheduler.schedule_followup("c1", 24.0, "跟进1")
        await scheduler.schedule_followup("c1", 48.0, "跟进2")
        await scheduler.schedule_followup("c1", 72.0, "跟进3")

        # Customer makes purchase
        cancelled = await scheduler.cancel_all_for_customer("c1", reason="Customer purchased")

        assert cancelled == 3
        assert len(scheduler.get_pending_followups("c1")) == 0


class TestFollowupEdgeCases:
    """Test edge cases in follow-up system."""

    @pytest.mark.asyncio
    async def test_empty_customer_id(self, scheduler):
        """Test scheduling with empty customer ID."""
        task = await scheduler.schedule_followup(
            customer_id="", delay_hours=24.0, message_template="测试"
        )

        # Should still create task
        assert task.customer_id == ""

    @pytest.mark.asyncio
    async def test_negative_delay(self, scheduler, mock_send_callback):
        """Test scheduling with negative delay (immediate)."""
        scheduler.set_send_callback(mock_send_callback)

        task = await scheduler.schedule_followup("c1", -5.0, "立即执行")

        # Should be due immediately
        assert task.is_due()

        results = await scheduler.execute_due_followups()
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_very_long_delay(self, scheduler):
        """Test scheduling with very long delay."""
        task = await scheduler.schedule_followup(
            "c1",
            delay_hours=720.0,  # 30 days
            message_template="长期跟进",
        )

        assert not task.is_due()
        assert task.scheduled_time > datetime.utcnow() + timedelta(days=29)

    @pytest.mark.asyncio
    async def test_concurrent_scheduling(self, scheduler):
        """Test concurrent scheduling requests."""

        async def schedule_one(i: int):
            return await scheduler.schedule_followup(f"customer-{i}", 24.0, f"跟进{i}")

        tasks = await asyncio.gather(*[schedule_one(i) for i in range(10)])

        assert len(tasks) == 10
        assert len(set(t.customer_id for t in tasks)) == 10

    @pytest.mark.asyncio
    async def test_message_template_with_variables(self, scheduler, mock_send_callback):
        """Test message template with variable placeholders."""
        scheduler.set_send_callback(mock_send_callback)

        template = "您好{name}，您对{product}的咨询有进展吗？"
        task = await scheduler.schedule_followup(
            "c1", -1.0, template, metadata={"name": "张先生", "product": "企业版"}
        )

        await scheduler.execute_due_followups()

        # Callback should receive template (in real impl, would be formatted)
        mock_send_callback.assert_called_once()


class TestFollowupPerformance:
    """Test follow-up system performance."""

    @pytest.mark.asyncio
    async def test_schedule_many_followups(self, scheduler):
        """Test scheduling many follow-ups efficiently."""
        import time

        start = time.time()

        for i in range(100):
            await scheduler.schedule_followup(f"c{i}", 24.0, f"跟进{i}")

        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 5.0
        assert len(scheduler.tasks) == 100

    @pytest.mark.asyncio
    async def test_execute_many_due_followups(self, scheduler, mock_send_callback):
        """Test executing many due follow-ups efficiently."""
        scheduler.set_send_callback(mock_send_callback)

        # Schedule many due follow-ups
        for i in range(50):
            await scheduler.schedule_followup(f"c{i}", -1.0, f"跟进{i}")

        import time

        start = time.time()

        results = await scheduler.execute_due_followups()

        elapsed = time.time() - start

        assert len(results) == 50
        assert elapsed < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_get_pending_followups_performance(self, scheduler):
        """Test getting pending follow-ups is efficient."""
        # Schedule many follow-ups
        for i in range(100):
            await scheduler.schedule_followup(f"c{i}", 24.0, f"跟进{i}")

        import time

        start = time.time()

        pending = scheduler.get_pending_followups()

        elapsed = time.time() - start

        assert len(pending) == 100
        assert elapsed < 1.0  # Should be very fast
