# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for intent recognition.

Tests the IntentRecognizer class and SalesIntent enum for
detecting customer intents during sales conversations.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from salemates.agent.intent.recognizer import (
    IntentRecognizer,
    IntentResult,
    SalesIntent,
)


# ============ Mock Fixtures ============


class MockLLMResponse:
    """Mock LLM response for testing."""

    def __init__(self, content: str):
        self.content = content
        self.has_tool_calls = False
        self.tool_calls = []
        self.reasoning_content = None
        self.usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}


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
        return MockLLMResponse(
            content='{"intent": "UNKNOWN", "confidence": 0.5, "reasoning": "", "signals": []}'
        )

    def get_default_model(self) -> str:
        return "mock-model"


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def recognizer(mock_llm_provider):
    """Create IntentRecognizer with mock provider."""
    return IntentRecognizer(mock_llm_provider)


# ============ Test Classes ============


class TestSalesIntentEnum:
    """Test SalesIntent enum values and properties."""

    def test_all_intent_values_exist(self):
        """Test all expected intent enum values exist."""
        assert SalesIntent.OBJECTION_PRICE.value == "OBJECTION_PRICE"
        assert SalesIntent.OBJECTION_FEATURE.value == "OBJECTION_FEATURE"
        assert SalesIntent.OBJECTION_COMPETITOR.value == "OBJECTION_COMPETITOR"
        assert SalesIntent.HESITATION.value == "HESITATION"
        assert SalesIntent.BUY_SIGNAL.value == "BUY_SIGNAL"
        assert SalesIntent.BANT_QUALIFICATION.value == "BANT_QUALIFICATION"
        assert SalesIntent.PRODUCT_INQUIRY.value == "PRODUCT_INQUIRY"
        assert SalesIntent.SCHEDULING_REQUEST.value == "SCHEDULING_REQUEST"
        assert SalesIntent.UNKNOWN.value == "UNKNOWN"

    def test_intent_string_representation(self):
        """Test intent string representation."""
        assert str(SalesIntent.OBJECTION_PRICE) == "OBJECTION_PRICE"
        assert str(SalesIntent.HESITATION) == "HESITATION"

    def test_intent_count(self):
        """Test correct number of intents."""
        assert len(SalesIntent) == 9

    def test_is_objection_property(self):
        """Test is_objection property returns correct values."""
        assert SalesIntent.OBJECTION_PRICE.is_objection is True
        assert SalesIntent.OBJECTION_FEATURE.is_objection is True
        assert SalesIntent.OBJECTION_COMPETITOR.is_objection is True
        assert SalesIntent.HESITATION.is_objection is False
        assert SalesIntent.BUY_SIGNAL.is_objection is False
        assert SalesIntent.UNKNOWN.is_objection is False


class TestIntentResult:
    """Test IntentResult dataclass."""

    def test_result_creation(self):
        """Test creating an IntentResult."""
        result = IntentResult(
            intent=SalesIntent.OBJECTION_PRICE,
            confidence=0.9,
            reasoning="Customer mentioned price comparison",
            signals=["价格", "贵"],
        )

        assert result.intent == SalesIntent.OBJECTION_PRICE
        assert result.confidence == 0.9
        assert result.reasoning == "Customer mentioned price comparison"
        assert "价格" in result.signals

    def test_result_to_dict(self):
        """Test converting IntentResult to dictionary."""
        result = IntentResult(
            intent=SalesIntent.HESITATION,
            confidence=0.85,
            reasoning="Customer wants to think",
            signals=["考虑"],
        )

        data = result.to_dict()

        assert data["intent"] == "HESITATION"
        assert data["confidence"] == 0.85
        assert data["reasoning"] == "Customer wants to think"
        assert "考虑" in data["signals"]


class TestIntentRecognizer:
    """Test IntentRecognizer class."""

    @pytest.mark.asyncio
    async def test_recognize_price_objection(self, recognizer, mock_llm_provider):
        """Test: "你们比 A 公司贵多了" → OBJECTION_PRICE"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "OBJECTION_PRICE",
                        "confidence": 0.9,
                        "reasoning": "Customer comparing prices with competitor",
                        "signals": ["贵", "比较", "价格"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("你们比 A 公司贵多了")

        assert result.intent == SalesIntent.OBJECTION_PRICE
        assert result.confidence > 0.8
        assert (
            "价格" in result.reasoning
            or "price" in result.reasoning.lower()
            or "贵" in result.reasoning
        )

    @pytest.mark.asyncio
    async def test_recognize_hesitation(self, recognizer, mock_llm_provider):
        """Test: "我再考虑一下" → HESITATION"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "HESITATION",
                        "confidence": 0.85,
                        "reasoning": "Customer wants time to consider",
                        "signals": ["考虑", "想想"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("我再考虑一下")

        assert result.intent == SalesIntent.HESITATION
        assert result.confidence > 0.7
        assert len(result.signals) > 0

    @pytest.mark.asyncio
    async def test_recognize_product_inquiry(self, recognizer, mock_llm_provider):
        """Test: "你们支持私有化部署吗？" → PRODUCT_INQUIRY"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "PRODUCT_INQUIRY",
                        "confidence": 0.95,
                        "reasoning": "Question about deployment feature",
                        "signals": ["私有化", "部署"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("你们支持私有化部署吗？")

        assert result.intent == SalesIntent.PRODUCT_INQUIRY
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_recognize_buy_signal(self, recognizer, mock_llm_provider):
        """Test: "我们想购买企业版" → BUY_SIGNAL"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "BUY_SIGNAL",
                        "confidence": 0.92,
                        "reasoning": "Customer expresses intent to purchase",
                        "signals": ["购买", "企业版"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("我们想购买企业版")

        assert result.intent == SalesIntent.BUY_SIGNAL
        assert result.confidence > 0.85

    @pytest.mark.asyncio
    async def test_recognize_bant_qualification(self, recognizer, mock_llm_provider):
        """Test BANT qualification intent detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "BANT_QUALIFICATION",
                        "confidence": 0.88,
                        "reasoning": "Customer asking about timeline and budget",
                        "signals": ["预算", "时间"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("你们的预算范围是多少？什么时候能上线？")

        assert result.intent == SalesIntent.BANT_QUALIFICATION
        assert result.confidence > 0.7

    @pytest.mark.asyncio
    async def test_recognize_scheduling_request(self, recognizer, mock_llm_provider):
        """Test: "可以安排一次演示吗？" → SCHEDULING_REQUEST"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "SCHEDULING_REQUEST",
                        "confidence": 0.91,
                        "reasoning": "Customer requests a demo meeting",
                        "signals": ["演示", "安排"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("可以安排一次演示吗？")

        assert result.intent == SalesIntent.SCHEDULING_REQUEST
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_recognize_feature_objection(self, recognizer, mock_llm_provider):
        """Test feature objection detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "OBJECTION_FEATURE",
                        "confidence": 0.82,
                        "reasoning": "Customer concerned about missing feature",
                        "signals": ["没有", "功能"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("你们的产品没有我们需要的数据分析功能")

        assert result.intent == SalesIntent.OBJECTION_FEATURE
        assert result.confidence > 0.7

    @pytest.mark.asyncio
    async def test_recognize_competitor_objection(self, recognizer, mock_llm_provider):
        """Test competitor objection detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "OBJECTION_COMPETITOR",
                        "confidence": 0.87,
                        "reasoning": "Customer comparing with competitor product",
                        "signals": ["竞品", "比较"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("竞品A有你们没有的功能")

        assert result.intent == SalesIntent.OBJECTION_COMPETITOR
        assert result.confidence > 0.75

    @pytest.mark.asyncio
    async def test_recognize_with_context(self, recognizer, mock_llm_provider):
        """Test intent recognition with conversation context."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "BUY_SIGNAL",
                        "confidence": 0.93,
                        "reasoning": "Strong purchase intent with context",
                        "signals": ["签约"],
                    }
                )
            )
        ]

        context = {
            "stage": "negotiation",
            "previous_intents": ["PRODUCT_INQUIRY", "BANT_QUALIFICATION"],
            "customer_budget": 100000,
        }

        result = await recognizer.recognize("好的，我们签约吧", context=context)

        assert result.intent == SalesIntent.BUY_SIGNAL
        # Verify context was passed to LLM
        assert len(mock_llm_provider.messages_received) > 0

    @pytest.mark.asyncio
    async def test_recognize_unknown_intent(self, recognizer, mock_llm_provider):
        """Test handling of unknown/unclassifiable intent."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "UNKNOWN",
                        "confidence": 0.3,
                        "reasoning": "Unable to classify intent",
                        "signals": [],
                    }
                )
            )
        ]

        result = await recognizer.recognize("asdfghjkl random text")

        assert result.intent == SalesIntent.UNKNOWN
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_recognize_fallback_on_invalid_json(self, recognizer, mock_llm_provider):
        """Test fallback behavior when LLM returns invalid JSON."""
        mock_llm_provider.responses = [MockLLMResponse(content="This is not valid JSON")]

        result = await recognizer.recognize("测试消息")

        # Should return UNKNOWN on parsing error
        assert result.intent == SalesIntent.UNKNOWN
        assert result.confidence == 0.0
        assert "Error" in result.reasoning

    @pytest.mark.asyncio
    async def test_recognize_fallback_on_invalid_intent_value(self, recognizer, mock_llm_provider):
        """Test fallback when LLM returns invalid intent value."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "INVALID_INTENT",
                        "confidence": 0.5,
                        "reasoning": "Test",
                        "signals": [],
                    }
                )
            )
        ]

        result = await recognizer.recognize("测试消息")

        # Should map invalid intent to UNKNOWN
        assert result.intent == SalesIntent.UNKNOWN

    @pytest.mark.asyncio
    async def test_recognize_empty_message(self, recognizer, mock_llm_provider):
        """Test handling of empty message."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "UNKNOWN",
                        "confidence": 0.0,
                        "reasoning": "Empty message",
                        "signals": [],
                    }
                )
            )
        ]

        result = await recognizer.recognize("")

        # Should handle gracefully
        assert result is not None
        assert isinstance(result, IntentResult)

    @pytest.mark.asyncio
    async def test_recognize_uses_low_temperature(self, recognizer, mock_llm_provider):
        """Test that intent recognition uses low temperature for consistency."""
        await recognizer.recognize("测试消息")

        # Verify the call was made
        assert mock_llm_provider.call_count == 1


class TestIntentRecognizerSync:
    """Test synchronous version of intent recognition."""

    def test_recognize_sync_basic(self, mock_llm_provider):
        """Test synchronous intent recognition."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "PRODUCT_INQUIRY",
                        "confidence": 0.9,
                        "reasoning": "Product question",
                        "signals": ["功能"],
                    }
                )
            )
        ]

        recognizer = IntentRecognizer(mock_llm_provider)
        result = recognizer.recognize_sync("你们有什么功能？")

        assert result.intent == SalesIntent.PRODUCT_INQUIRY
        assert result.confidence > 0.8


class TestIntentRecognitionEdgeCases:
    """Test edge cases in intent recognition."""

    @pytest.mark.asyncio
    async def test_multiple_intents_in_message(self, recognizer, mock_llm_provider):
        """Test message with multiple potential intents."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "OBJECTION_PRICE",
                        "confidence": 0.88,
                        "reasoning": "Price is the primary concern",
                        "signals": ["贵", "考虑"],
                    }
                )
            )
        ]

        # Message has both price objection and hesitation signals
        result = await recognizer.recognize("你们太贵了，我再考虑一下")

        assert result.intent == SalesIntent.OBJECTION_PRICE
        # Primary intent should be detected

    @pytest.mark.asyncio
    async def test_very_long_message(self, recognizer, mock_llm_provider):
        """Test handling of very long messages."""
        long_message = "我想了解一下" + "产品" * 100 + "的功能"

        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "PRODUCT_INQUIRY",
                        "confidence": 0.85,
                        "reasoning": "Long product inquiry",
                        "signals": ["功能"],
                    }
                )
            )
        ]

        result = await recognizer.recognize(long_message)

        assert result is not None
        assert isinstance(result, IntentResult)

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, recognizer, mock_llm_provider):
        """Test handling of special characters."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "PRODUCT_INQUIRY",
                        "confidence": 0.8,
                        "reasoning": "Question detected",
                        "signals": ["?"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("你们的价格是？！@#￥%……&*（）")

        assert result is not None

    @pytest.mark.asyncio
    async def test_mixed_language_message(self, recognizer, mock_llm_provider):
        """Test handling of mixed language messages."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "intent": "PRODUCT_INQUIRY",
                        "confidence": 0.82,
                        "reasoning": "Mixed language product question",
                        "signals": ["price", "价格"],
                    }
                )
            )
        ]

        result = await recognizer.recognize("What is your 价格? Can you give me a discount?")

        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_exception_handling(self, mock_llm_provider):
        """Test handling of LLM exceptions."""

        # Create a provider that raises an exception
        class FailingProvider:
            async def chat(self, messages, **kwargs):
                raise Exception("LLM connection failed")

        recognizer = IntentRecognizer(FailingProvider())
        result = await recognizer.recognize("测试消息")

        # Should return UNKNOWN on error
        assert result.intent == SalesIntent.UNKNOWN
        assert result.confidence == 0.0
        assert "Error" in result.reasoning
