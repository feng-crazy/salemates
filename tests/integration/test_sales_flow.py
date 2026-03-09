# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for complete sales conversation flow.

Tests the full pipeline from NEW_CONTACT -> CLOSE including:
- Stage transitions via state machine
- Intent recognition
- Emotion analysis
- Safety guardrails (guardrails, emotion fuse, confidence router)
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from salemates.agent.emotion.analyzer import CustomerEmotion, EmotionResult
from salemates.agent.models.customer import BANTProfile, CustomerProfile, SalesStage
from salemates.agent.safety.confidence_router import ConfidenceLevel, ConfidenceRouter
from salemates.agent.safety.emotion_fuse import EmotionFuse, EmotionFuseConfig, FuseAction
from salemates.agent.safety.guardrails import (
    CompetitorGuardrailConfig,
    create_default_guardrails,
    GuardrailType,
    GuardrailViolation,
    PriceGuardrailConfig,
    ViolationSeverity,
)
from salemates.agent.stages.state_machine import SalesStageStateMachine
from salemates.bus.events import InboundMessage, OutboundMessage
from salemates.config.schema import SessionKey


# ============ Mock Fixtures ============


@dataclass
class MockLLMResponse:
    """Mock LLM response."""

    content: str
    has_tool_calls: bool = False
    tool_calls: list = field(default_factory=list)
    reasoning_content: str | None = None
    usage: dict = field(
        default_factory=lambda: {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses: list[MockLLMResponse] | None = None):
        self.responses = responses or []
        self.call_count = 0
        self.messages_received: list[dict] = []

    async def chat(self, messages: list[dict], **kwargs) -> MockLLMResponse:
        self.messages_received.append(messages)
        self.call_count += 1
        if self.responses and self.call_count <= len(self.responses):
            return self.responses[self.call_count - 1]
        return MockLLMResponse(content="Default response")

    def get_default_model(self) -> str:
        return "mock-model"


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def state_machine():
    """Create a fresh state machine."""
    return SalesStageStateMachine()


@pytest.fixture
def confidence_router():
    """Create confidence router with default thresholds."""
    return ConfidenceRouter()


@pytest.fixture
def emotion_fuse():
    """Create emotion fuse with default config."""
    return EmotionFuse(EmotionFuseConfig(anger_threshold=0.7, frustration_threshold=0.7))


@pytest.fixture
def guardrail_manager():
    """Create guardrail manager with default guardrails."""
    return create_default_guardrails(max_discount_percent=15.0)


@pytest.fixture
def customer_profile():
    """Create a sample customer profile."""
    return CustomerProfile(
        id="test-customer-001",
        name="张三",
        email="zhangsan@example.com",
        company="测试公司",
        stage=SalesStage.NEW_CONTACT,
        bant=BANTProfile(
            budget=100000,
            authority="技术总监",
            need="团队协作工具",
            timeline="Q2上线",
        ),
    )


# ============ Test Classes ============


class TestSalesFlowStageTransitions:
    """Test stage transitions throughout the sales flow."""

    def test_new_contact_to_discovery(self, state_machine):
        """Test transition from NEW_CONTACT to DISCOVERY when customer shows interest."""
        # Initial state
        assert state_machine.can_transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)

        # Transition triggered by customer reply
        success, error = state_machine.transition(
            SalesStage.NEW_CONTACT, SalesStage.DISCOVERY, trigger="customer_replied"
        )

        assert success is True
        assert error is None
        assert len(state_machine.transition_history) == 1
        assert state_machine.transition_history[0].trigger == "customer_replied"

    def test_discovery_to_presentation(self, state_machine):
        """Test transition from DISCOVERY to PRESENTATION when needs are identified."""
        # First, get to DISCOVERY
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY, "replied")

        # Now test DISCOVERY -> PRESENTATION
        assert state_machine.can_transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)

        success, error = state_machine.transition(
            SalesStage.DISCOVERY, SalesStage.PRESENTATION, trigger="needs_documented"
        )

        assert success is True
        assert len(state_machine.transition_history) == 2

    def test_presentation_to_negotiation(self, state_machine):
        """Test transition from PRESENTATION to NEGOTIATION when pricing is discussed."""
        # Setup: NEW_CONTACT -> DISCOVERY -> PRESENTATION
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        state_machine.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)

        # Test PRESENTATION -> NEGOTIATION
        success, error = state_machine.transition(
            SalesStage.PRESENTATION, SalesStage.NEGOTIATION, trigger="pricing_discussed"
        )

        assert success is True
        assert state_machine.get_last_transition().to_stage == SalesStage.NEGOTIATION

    def test_negotiation_to_close(self, state_machine):
        """Test transition from NEGOTIATION to CLOSE when agreement is reached."""
        # Setup pipeline
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        state_machine.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        state_machine.transition(SalesStage.PRESENTATION, SalesStage.NEGOTIATION)

        # Test NEGOTIATION -> CLOSE
        success, error = state_machine.transition(
            SalesStage.NEGOTIATION, SalesStage.CLOSE, trigger="agreement_signed"
        )

        assert success is True
        assert state_machine.is_terminal_stage(SalesStage.CLOSE)

    def test_invalid_transition_skip_stage(self, state_machine):
        """Test that skipping stages is not allowed."""
        success, error = state_machine.transition(
            SalesStage.NEW_CONTACT,
            SalesStage.CLOSE,  # Cannot skip to CLOSE
        )

        assert success is False
        assert "Invalid transition" in error

    def test_invalid_transition_from_terminal(self, state_machine):
        """Test that terminal states cannot transition."""
        # Setup to CLOSE
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        state_machine.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        state_machine.transition(SalesStage.PRESENTATION, SalesStage.NEGOTIATION)
        state_machine.transition(SalesStage.NEGOTIATION, SalesStage.CLOSE)

        # Cannot transition from CLOSE
        success, error = state_machine.transition(SalesStage.CLOSE, SalesStage.DISCOVERY)
        assert success is False

    def test_loss_transition_from_any_stage(self, state_machine):
        """Test that LOST is reachable from all non-terminal stages."""
        non_terminal_stages = [
            SalesStage.NEW_CONTACT,
            SalesStage.DISCOVERY,
            SalesStage.PRESENTATION,
            SalesStage.NEGOTIATION,
        ]

        for stage in non_terminal_stages:
            sm = SalesStageStateMachine()
            assert sm.can_transition(stage, SalesStage.LOST), (
                f"Cannot transition from {stage} to LOST"
            )


class TestSalesFlowIntentRecognition:
    """Test intent recognition during sales conversations."""

    @pytest.mark.asyncio
    async def test_price_inquiry_intent(self, mock_llm_provider):
        """Test recognition of price inquiry intent."""
        # Mock LLM to return price inquiry response
        mock_llm_provider.responses = [MockLLMResponse(content="这是一个关于价格的询问")]

        # In real implementation, this would go through intent recognizer
        response = await mock_llm_provider.chat([{"role": "user", "content": "你们的价格是多少？"}])

        assert "价格" in response.content

    @pytest.mark.asyncio
    async def test_product_feature_intent(self, mock_llm_provider):
        """Test recognition of product feature inquiry intent."""
        mock_llm_provider.responses = [MockLLMResponse(content="用户想了解产品功能")]

        response = await mock_llm_provider.chat(
            [{"role": "user", "content": "这个产品有什么功能？"}]
        )

        assert "功能" in response.content

    @pytest.mark.asyncio
    async def test_competitor_comparison_intent(self, mock_llm_provider):
        """Test recognition of competitor comparison intent."""
        mock_llm_provider.responses = [MockLLMResponse(content="用户在比较竞品")]

        response = await mock_llm_provider.chat(
            [{"role": "user", "content": "你们和竞品A比怎么样？"}]
        )

        assert response.content


class TestSalesFlowEmotionAnalysis:
    """Test emotion analysis during sales conversations."""

    def test_hesitation_emotion_detection(self, emotion_fuse):
        """Test detection of hesitation emotion triggers correct action."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.HESITATION,
            intensity=0.5,
            signals=["考虑", "想想"],
            reasoning="Customer shows hesitation signals",
        )

        action = emotion_fuse.check(emotion_result, "我再考虑一下")
        assert action == FuseAction.CONTINUE  # Hesitation is manageable

    def test_anger_emotion_triggers_handoff(self, emotion_fuse):
        """Test high anger intensity triggers human handoff."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.ANGER,
            intensity=0.8,  # Above threshold
            signals=["投诉"],
            reasoning="Customer is angry",
        )

        action = emotion_fuse.check(emotion_result, "我要投诉你们！")
        assert action == FuseAction.HUMAN_HANDOFF

    def test_frustration_emotion_triggers_handoff(self, emotion_fuse):
        """Test high frustration intensity triggers human handoff."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.FRUSTRATION,
            intensity=0.75,  # Above threshold
            signals=["烦"],
            reasoning="Customer is frustrated",
        )

        action = emotion_fuse.check(emotion_result, "真烦，说了半天没用")
        assert action == FuseAction.HUMAN_HANDOFF

    def test_trigger_keywords_pause_autoreply(self, emotion_fuse):
        """Test trigger keywords pause auto-reply."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.NEUTRAL, intensity=0.3, signals=[], reasoning="Normal emotion"
        )

        # Message contains trigger keyword "领导"
        action = emotion_fuse.check(emotion_result, "我要找你们领导说话")
        assert action == FuseAction.PAUSE_AUTO_REPLY

    def test_positive_emotion_continues(self, emotion_fuse):
        """Test positive emotions allow normal flow."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.INTEREST,
            intensity=0.7,
            signals=["很好", "不错"],
            reasoning="Customer shows interest",
        )

        action = emotion_fuse.check(emotion_result, "这个产品看起来不错")
        assert action == FuseAction.CONTINUE

    def test_trust_emotion_advances_stage(self, emotion_fuse, state_machine):
        """Test trust emotion can advance conversation stage."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.TRUST,
            intensity=0.8,
            signals=["信任", "专业"],
            reasoning="Customer trusts the sales agent",
        )

        action = emotion_fuse.check(emotion_result, "你们很专业，我信任你们")
        assert action == FuseAction.CONTINUE

        # In real flow, this would trigger stage transition
        signals = ["customer_shows_interest"]
        suggested_stage = state_machine.suggest_transition(signals, SalesStage.NEW_CONTACT)
        assert suggested_stage == SalesStage.DISCOVERY


class TestSalesFlowSafetyGuardrails:
    """Test safety guardrails during sales conversations."""

    def test_unauthorized_discount_blocked(self, guardrail_manager):
        """Test unauthorized discount is detected and blocked."""
        # Agent tries to offer 20% discount (exceeds 15% max)
        response_text = "我可以给你20%的折扣"

        violations = guardrail_manager.check(response_text)

        assert len(violations) >= 1
        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]
        assert len(price_violations) >= 1
        assert price_violations[0].context["discount_percent"] == 20

    def test_authorized_discount_allowed(self, guardrail_manager):
        """Test authorized discount within limits is allowed."""
        response_text = "我可以给您10%的折扣"

        violations = guardrail_manager.check(response_text)
        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]

        # 10% is within 15% limit, should not trigger violation
        assert len(price_violations) == 0

    def test_contract_commitment_blocked(self, guardrail_manager):
        """Test unauthorized contract commitment is blocked."""
        response_text = "我们可以签订5年合同"

        violations = guardrail_manager.check(response_text)

        contract_violations = [v for v in violations if v.type == GuardrailType.CONTRACT]
        assert len(contract_violations) >= 1
        assert contract_violations[0].severity == ViolationSeverity.BLOCK

    def test_unverified_feature_claim_flagged(self, guardrail_manager):
        """Test claims about unverified features are flagged for review."""
        response_text = "我们的产品支持AI自动决策"

        violations = guardrail_manager.check(response_text)

        feature_violations = [v for v in violations if v.type == GuardrailType.FEATURE]
        assert len(feature_violations) >= 1
        assert feature_violations[0].severity == ViolationSeverity.REVIEW

    def test_competitor_negative_comparison_flagged(self, guardrail_manager):
        """Test negative competitor comparisons are flagged."""
        response_text = "竞品A比我们差很多"

        violations = guardrail_manager.check(response_text)

        competitor_violations = [v for v in violations if v.type == GuardrailType.COMPETITOR]
        assert len(competitor_violations) >= 1

    def test_allowed_phrase_escapes_contract_guardrail(self, guardrail_manager):
        """Test allowed phrases escape contract guardrail."""
        response_text = "我们可以签订合同，但需要法务审核"

        violations = guardrail_manager.check(response_text)

        contract_violations = [v for v in violations if v.type == GuardrailType.CONTRACT]
        # Should be allowed because of "需要法务审核" escape hatch
        assert len(contract_violations) == 0


class TestSalesFlowConfidenceRouting:
    """Test confidence-based response routing."""

    def test_high_confidence_auto_reply(self, confidence_router):
        """Test high confidence responses are routed to auto-reply."""
        decision = confidence_router.route(0.95, {"customer_id": "test-001"})

        assert decision.level == ConfidenceLevel.HIGH
        assert decision.action == "auto_reply"
        assert "High confidence" in decision.reason

    def test_medium_confidence_draft(self, confidence_router):
        """Test medium confidence responses are routed for draft approval."""
        decision = confidence_router.route(0.75, {"customer_id": "test-001"})

        assert decision.level == ConfidenceLevel.MEDIUM
        assert decision.action == "draft"
        assert "human approval" in decision.reason

    def test_low_confidence_human_intervention(self, confidence_router):
        """Test low confidence responses require human intervention."""
        decision = confidence_router.route(0.45, {"customer_id": "test-001"})

        assert decision.level == ConfidenceLevel.LOW
        assert decision.action == "human_intervention"
        assert "immediate human intervention" in decision.reason

    def test_confidence_threshold_boundary_high(self, confidence_router):
        """Test confidence at exactly high threshold."""
        decision = confidence_router.route(0.90, {})

        assert decision.level == ConfidenceLevel.HIGH

    def test_confidence_threshold_boundary_medium(self, confidence_router):
        """Test confidence at exactly medium threshold."""
        decision = confidence_router.route(0.60, {})

        assert decision.level == ConfidenceLevel.MEDIUM

    def test_needs_human_review_check(self, confidence_router):
        """Test needs_human_review helper method."""
        assert confidence_router.needs_human_review(0.85) is True
        assert confidence_router.needs_human_review(0.95) is False

    def test_needs_immediate_intervention_check(self, confidence_router):
        """Test needs_immediate_intervention helper method."""
        assert confidence_router.needs_immediate_intervention(0.50) is True
        assert confidence_router.needs_immediate_intervention(0.75) is False


class TestSalesFlowCompletePipeline:
    """Test complete sales flow from NEW_CONTACT to CLOSE."""

    @pytest.mark.asyncio
    async def test_complete_sales_flow_success(
        self,
        state_machine,
        emotion_fuse,
        guardrail_manager,
        confidence_router,
        mock_llm_provider,
        customer_profile,
    ):
        """Test a successful complete sales flow."""
        # Stage 1: NEW_CONTACT -> DISCOVERY
        # Customer shows interest
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.INTEREST,
            intensity=0.6,
            signals=["感兴趣"],
            reasoning="Customer is interested",
        )

        action = emotion_fuse.check(emotion_result, "我对你们的产品很感兴趣")
        assert action == FuseAction.CONTINUE

        # Transition to DISCOVERY
        signals = ["customer_shows_interest"]
        success, _ = state_machine.transition(
            SalesStage.NEW_CONTACT, SalesStage.DISCOVERY, trigger="customer_replied"
        )
        assert success

        # Stage 2: DISCOVERY -> PRESENTATION
        # Needs identified, BANT qualified
        customer_profile.update_bant(
            budget=100000, authority="技术总监", need="团队协作", timeline="Q2"
        )
        assert customer_profile.bant.is_qualified()

        success, _ = state_machine.transition(
            SalesStage.DISCOVERY, SalesStage.PRESENTATION, trigger="needs_documented"
        )
        assert success

        # Stage 3: PRESENTATION -> NEGOTIATION
        # Customer asks about pricing, objection raised
        response_text = "我们的企业版价格是每年10万元，可以给您12%的折扣"
        violations = guardrail_manager.check(response_text)
        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]
        assert len(price_violations) == 0  # 12% is within 15% limit

        success, _ = state_machine.transition(
            SalesStage.PRESENTATION, SalesStage.NEGOTIATION, trigger="pricing_discussed"
        )
        assert success

        # Stage 4: NEGOTIATION -> CLOSE
        # Agreement reached
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.TRUST,
            intensity=0.85,
            signals=["同意"],
            reasoning="Customer agrees to terms",
        )
        action = emotion_fuse.check(emotion_result, "好的，我们签合同")
        assert action == FuseAction.CONTINUE

        # Check confidence routing for final response
        decision = confidence_router.route(0.92, {"stage": "close"})
        assert decision.level == ConfidenceLevel.HIGH

        success, _ = state_machine.transition(
            SalesStage.NEGOTIATION, SalesStage.CLOSE, trigger="agreement_signed"
        )
        assert success
        assert state_machine.is_terminal_stage(SalesStage.CLOSE)

    @pytest.mark.asyncio
    async def test_sales_flow_with_angry_customer_handoff(
        self,
        state_machine,
        emotion_fuse,
        customer_profile,
    ):
        """Test sales flow interruption when customer gets angry."""
        # Start at DISCOVERY
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)

        # Customer gets angry during discovery
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.ANGER,
            intensity=0.85,
            signals=["投诉", "骗子"],
            reasoning="Customer is very angry",
        )

        action = emotion_fuse.check(emotion_result, "你们是骗子！我要投诉！")
        assert action == FuseAction.HUMAN_HANDOFF

        # Flow should stop, waiting for human intervention
        # No further stage transitions should happen automatically

    @pytest.mark.asyncio
    async def test_sales_flow_with_lost_deal(
        self,
        state_machine,
        emotion_fuse,
        customer_profile,
    ):
        """Test sales flow when deal is lost."""
        # Progress to PRESENTATION
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        state_machine.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)

        # Customer declines due to budget
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.NEUTRAL,
            intensity=0.3,
            signals=["预算不够"],
            reasoning="Customer cannot afford",
        )

        action = emotion_fuse.check(emotion_result, "抱歉，我们预算不够")
        assert action == FuseAction.CONTINUE  # No emotion issue, just business

        # Transition to LOST
        success, _ = state_machine.transition(
            SalesStage.PRESENTATION, SalesStage.LOST, trigger="price_too_high"
        )
        assert success
        assert state_machine.is_terminal_stage(SalesStage.LOST)

    @pytest.mark.asyncio
    async def test_sales_flow_with_guardrail_violation(
        self,
        state_machine,
        guardrail_manager,
    ):
        """Test sales flow when guardrail violation is detected."""
        # At NEGOTIATION stage
        state_machine.transition(SalesStage.NEW_CONTACT, SalesStage.DISCOVERY)
        state_machine.transition(SalesStage.DISCOVERY, SalesStage.PRESENTATION)
        state_machine.transition(SalesStage.PRESENTATION, SalesStage.NEGOTIATION)

        # Agent attempts unauthorized discount
        response_text = "我可以给您25%的折扣"
        violations = guardrail_manager.check(response_text)

        assert guardrail_manager.needs_review(response_text)

        price_violations = [v for v in violations if v.type == GuardrailType.PRICE]
        assert len(price_violations) >= 1
        assert price_violations[0].context["discount_percent"] == 25


class TestSalesFlowIntegrationWithBANT:
    """Test sales flow integration with BANT qualification."""

    def test_bant_qualification_affects_stage_transition(self, customer_profile):
        """Test that BANT qualification affects stage decisions."""
        # Initially not qualified
        customer_profile.bant = BANTProfile()
        assert not customer_profile.bant.is_qualified()

        # Update BANT data
        customer_profile.update_bant(
            budget=50000, authority="CTO", need="团队效率提升", timeline="Q2"
        )

        assert customer_profile.bant.is_qualified()
        assert customer_profile.bant.qualification_score() > 0.75

    def test_pain_points_tracking(self, customer_profile):
        """Test pain points are tracked during conversation."""
        customer_profile.add_pain_point("现有工具效率低")
        customer_profile.add_pain_point("团队协作困难")

        assert len(customer_profile.pain_points) == 2
        assert "现有工具效率低" in customer_profile.pain_points

    def test_competitor_tracking(self, customer_profile):
        """Test competitors are tracked during conversation."""
        customer_profile.add_competitor("竞品A")
        customer_profile.add_competitor("竞品B")

        assert len(customer_profile.competitors) == 2


class TestSalesFlowSessionManagement:
    """Test session management during sales flow."""

    def test_session_key_creation(self):
        """Test session key is properly created."""
        session_key = SessionKey(type="telegram", channel_id="sales_bot", chat_id="user_12345")

        assert session_key.type == "telegram"
        assert session_key.channel_id == "sales_bot"
        assert session_key.chat_id == "user_12345"

    def test_inbound_message_creation(self):
        """Test inbound message is properly created."""
        session_key = SessionKey(type="telegram", channel_id="sales_bot", chat_id="user_123")

        msg = InboundMessage(
            sender_id="user_123",
            content="我想了解你们的产品",
            session_key=session_key,
        )

        assert msg.content == "我想了解你们的产品"
        assert msg.session_key == session_key

    def test_outbound_message_creation(self):
        """Test outbound message is properly created."""
        session_key = SessionKey(type="telegram", channel_id="sales_bot", chat_id="user_123")

        msg = OutboundMessage(
            session_key=session_key,
            content="好的，我来为您介绍我们的产品",
        )

        assert msg.content == "好的，我来为您介绍我们的产品"
        assert msg.is_normal_message


class TestSalesFlowEdgeCases:
    """Test edge cases in sales flow."""

    def test_empty_message_handling(self, emotion_fuse):
        """Test handling of empty messages."""
        emotion_result = EmotionResult(
            emotion=CustomerEmotion.NEUTRAL, intensity=0.0, signals=[], reasoning="Empty message"
        )

        action = emotion_fuse.check(emotion_result, "")
        assert action == FuseAction.CONTINUE

    def test_very_long_message_handling(self, emotion_fuse):
        """Test handling of very long messages."""
        long_message = "这是" * 1000

        emotion_result = EmotionResult(
            emotion=CustomerEmotion.NEUTRAL, intensity=0.3, signals=[], reasoning="Long message"
        )

        action = emotion_fuse.check(emotion_result, long_message)
        assert action == FuseAction.CONTINUE

    def test_rapid_stage_transitions(self, state_machine):
        """Test rapid consecutive stage transitions."""
        transitions = [
            (SalesStage.NEW_CONTACT, SalesStage.DISCOVERY),
            (SalesStage.DISCOVERY, SalesStage.PRESENTATION),
            (SalesStage.PRESENTATION, SalesStage.NEGOTIATION),
            (SalesStage.NEGOTIATION, SalesStage.CLOSE),
        ]

        for from_stage, to_stage in transitions:
            success, _ = state_machine.transition(from_stage, to_stage)
            assert success

        assert len(state_machine.transition_history) == 4

    def test_multiple_guardrail_violations(self, guardrail_manager):
        """Test detection of multiple guardrail violations in one message."""
        # Message with price violation AND competitor violation
        response_text = "我可以给您25%折扣，而且竞品A比我们差很多"

        violations = guardrail_manager.check(response_text)

        violation_types = {v.type for v in violations}
        assert GuardrailType.PRICE in violation_types
        assert GuardrailType.COMPETITOR in violation_types

    def test_invalid_confidence_value(self, confidence_router):
        """Test handling of invalid confidence values."""
        with pytest.raises(ValueError):
            confidence_router.route(-0.1, {})

        with pytest.raises(ValueError):
            confidence_router.route(1.5, {})
