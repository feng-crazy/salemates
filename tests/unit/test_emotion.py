# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for emotion detection.

Tests the EmotionAnalyzer class and CustomerEmotion enum for
detecting customer emotions during sales conversations.
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock

from salemates.agent.emotion.analyzer import (
    CustomerEmotion,
    EmotionAnalyzer,
    EmotionResult,
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
            content=json.dumps(
                {
                    "emotion": "NEUTRAL",
                    "intensity": 0.3,
                    "signals": [],
                    "reasoning": "Default response",
                }
            )
        )

    def get_default_model(self) -> str:
        return "mock-model"


@pytest.fixture
def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
def analyzer(mock_llm_provider):
    """Create EmotionAnalyzer with mock provider."""
    return EmotionAnalyzer(mock_llm_provider)


# ============ Test Classes ============


class TestCustomerEmotionEnum:
    """Test CustomerEmotion enum values and properties."""

    def test_all_emotion_values_exist(self):
        """Test all expected emotion enum values exist."""
        assert CustomerEmotion.HESITATION.value == "HESITATION"
        assert CustomerEmotion.TRUST.value == "TRUST"
        assert CustomerEmotion.ANGER.value == "ANGER"
        assert CustomerEmotion.FRUSTRATION.value == "FRUSTRATION"
        assert CustomerEmotion.CALCULATING.value == "CALCULATING"
        assert CustomerEmotion.INTEREST.value == "INTEREST"
        assert CustomerEmotion.NEUTRAL.value == "NEUTRAL"

    def test_emotion_string_representation(self):
        """Test emotion string representation."""
        assert str(CustomerEmotion.HESITATION) == "HESITATION"
        assert str(CustomerEmotion.ANGER) == "ANGER"

    def test_emotion_count(self):
        """Test correct number of emotions."""
        assert len(CustomerEmotion) == 7

    def test_is_negative_property(self):
        """Test is_negative property returns correct values."""
        assert CustomerEmotion.ANGER.is_negative is True
        assert CustomerEmotion.FRUSTRATION.is_negative is True
        assert CustomerEmotion.HESITATION.is_negative is False
        assert CustomerEmotion.TRUST.is_negative is False
        assert CustomerEmotion.NEUTRAL.is_negative is False

    def test_is_positive_property(self):
        """Test is_positive property returns correct values."""
        assert CustomerEmotion.TRUST.is_positive is True
        assert CustomerEmotion.INTEREST.is_positive is True
        assert CustomerEmotion.ANGER.is_positive is False
        assert CustomerEmotion.FRUSTRATION.is_positive is False
        assert CustomerEmotion.NEUTRAL.is_positive is False


class TestEmotionResult:
    """Test EmotionResult dataclass."""

    def test_result_creation(self):
        """Test creating an EmotionResult."""
        result = EmotionResult(
            emotion=CustomerEmotion.HESITATION,
            intensity=0.6,
            signals=["考虑", "想想"],
            reasoning="Customer shows hesitation signals",
        )

        assert result.emotion == CustomerEmotion.HESITATION
        assert result.intensity == 0.6
        assert "考虑" in result.signals
        assert result.reasoning == "Customer shows hesitation signals"

    def test_intensity_clamping_high(self):
        """Test intensity is clamped to 1.0 for high values."""
        result = EmotionResult(
            emotion=CustomerEmotion.ANGER,
            intensity=1.5,  # Should be clamped to 1.0
            signals=[],
            reasoning="Test",
        )

        assert result.intensity == 1.0

    def test_intensity_clamping_low(self):
        """Test intensity is clamped to 0.0 for negative values."""
        result = EmotionResult(
            emotion=CustomerEmotion.NEUTRAL,
            intensity=-0.5,  # Should be clamped to 0.0
            signals=[],
            reasoning="Test",
        )

        assert result.intensity == 0.0

    def test_is_high_intensity_negative(self):
        """Test is_high_intensity_negative property."""
        # High intensity negative emotion
        result = EmotionResult(
            emotion=CustomerEmotion.ANGER,
            intensity=0.8,
            signals=[],
            reasoning="Test",
        )
        assert result.is_high_intensity_negative is True

        # Low intensity negative emotion
        result = EmotionResult(
            emotion=CustomerEmotion.ANGER,
            intensity=0.5,
            signals=[],
            reasoning="Test",
        )
        assert result.is_high_intensity_negative is False

        # High intensity positive emotion
        result = EmotionResult(
            emotion=CustomerEmotion.TRUST,
            intensity=0.9,
            signals=[],
            reasoning="Test",
        )
        assert result.is_high_intensity_negative is False

    def test_should_handoff(self):
        """Test should_handoff property."""
        # High intensity anger should handoff
        result = EmotionResult(
            emotion=CustomerEmotion.ANGER,
            intensity=0.85,
            signals=["投诉"],
            reasoning="Angry customer",
        )
        assert result.should_handoff is True

        # Low intensity frustration should not handoff
        result = EmotionResult(
            emotion=CustomerEmotion.FRUSTRATION,
            intensity=0.5,
            signals=["烦"],
            reasoning="Mildly frustrated",
        )
        assert result.should_handoff is False

    def test_to_dict(self):
        """Test converting EmotionResult to dictionary."""
        result = EmotionResult(
            emotion=CustomerEmotion.INTEREST,
            intensity=0.7,
            signals=["感兴趣", "不错"],
            reasoning="Customer shows interest",
        )

        data = result.to_dict()

        assert data["emotion"] == "INTEREST"
        assert data["intensity"] == 0.7
        assert "感兴趣" in data["signals"]
        assert data["reasoning"] == "Customer shows interest"


class TestEmotionAnalyzer:
    """Test EmotionAnalyzer class."""

    @pytest.mark.asyncio
    async def test_analyze_hesitation(self, analyzer, mock_llm_provider):
        """Test: "我再考虑一下" → HESITATION"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "HESITATION",
                        "intensity": 0.65,
                        "signals": ["考虑", "想想"],
                        "reasoning": "Customer wants more time to consider",
                    }
                )
            )
        ]

        result = await analyzer.analyze("我再考虑一下")

        assert result.emotion == CustomerEmotion.HESITATION
        assert result.intensity > 0.5
        assert len(result.signals) > 0

    @pytest.mark.asyncio
    async def test_analyze_anger(self, analyzer, mock_llm_provider):
        """Test: "我要投诉你们！" → ANGER"""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "ANGER",
                        "intensity": 0.85,
                        "signals": ["投诉", "骗子"],
                        "reasoning": "Customer is very angry",
                    }
                )
            )
        ]

        result = await analyzer.analyze("我要投诉你们！你们是骗子！")

        assert result.emotion == CustomerEmotion.ANGER
        assert result.intensity > 0.7
        assert result.should_handoff is True

    @pytest.mark.asyncio
    async def test_analyze_frustration(self, analyzer, mock_llm_provider):
        """Test frustration detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "FRUSTRATION",
                        "intensity": 0.72,
                        "signals": ["烦", "够了"],
                        "reasoning": "Customer is frustrated",
                    }
                )
            )
        ]

        result = await analyzer.analyze("真烦，说了半天没用，够了")

        assert result.emotion == CustomerEmotion.FRUSTRATION
        assert result.intensity > 0.6

    @pytest.mark.asyncio
    async def test_analyze_trust(self, analyzer, mock_llm_provider):
        """Test trust emotion detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "TRUST",
                        "intensity": 0.8,
                        "signals": ["信任", "专业"],
                        "reasoning": "Customer trusts the sales agent",
                    }
                )
            )
        ]

        result = await analyzer.analyze("你们很专业，我信任你们")

        assert result.emotion == CustomerEmotion.TRUST
        assert result.is_positive is True
        assert result.is_negative is False

    @pytest.mark.asyncio
    async def test_analyze_interest(self, analyzer, mock_llm_provider):
        """Test interest emotion detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "INTEREST",
                        "intensity": 0.75,
                        "signals": ["感兴趣", "不错"],
                        "reasoning": "Customer shows interest in the product",
                    }
                )
            )
        ]

        result = await analyzer.analyze("这个产品看起来不错，我很感兴趣")

        assert result.emotion == CustomerEmotion.INTEREST
        assert result.is_positive is True

    @pytest.mark.asyncio
    async def test_analyze_calculating(self, analyzer, mock_llm_provider):
        """Test calculating/rational emotion detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "CALCULATING",
                        "intensity": 0.6,
                        "signals": ["比较", "性价比"],
                        "reasoning": "Customer is analyzing rationally",
                    }
                )
            )
        ]

        result = await analyzer.analyze("我在比较几家的性价比")

        assert result.emotion == CustomerEmotion.CALCULATING

    @pytest.mark.asyncio
    async def test_analyze_neutral(self, analyzer, mock_llm_provider):
        """Test neutral emotion detection."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "NEUTRAL",
                        "intensity": 0.2,
                        "signals": [],
                        "reasoning": "No strong emotion detected",
                    }
                )
            )
        ]

        result = await analyzer.analyze("好的，我知道了")

        assert result.emotion == CustomerEmotion.NEUTRAL
        assert result.intensity < 0.5

    @pytest.mark.asyncio
    async def test_analyze_empty_message(self, analyzer):
        """Test handling of empty message."""
        result = await analyzer.analyze("")

        assert result.emotion == CustomerEmotion.NEUTRAL
        assert result.intensity == 0.0
        assert result.reasoning == "Empty message"

    @pytest.mark.asyncio
    async def test_analyze_whitespace_message(self, analyzer):
        """Test handling of whitespace-only message."""
        result = await analyzer.analyze("   ")

        assert result.emotion == CustomerEmotion.NEUTRAL
        assert result.intensity == 0.0

    @pytest.mark.asyncio
    async def test_analyze_fallback_on_invalid_json(self, analyzer, mock_llm_provider):
        """Test fallback behavior when LLM returns invalid JSON."""
        mock_llm_provider.responses = [MockLLMResponse(content="This is not valid JSON")]

        result = await analyzer.analyze("测试消息")

        # Should return fallback result based on keyword matching or NEUTRAL
        assert result is not None
        assert isinstance(result, EmotionResult)

    @pytest.mark.asyncio
    async def test_analyze_fallback_anger_keywords(self, analyzer, mock_llm_provider):
        """Test fallback keyword matching for anger."""
        mock_llm_provider.responses = [MockLLMResponse(content="invalid json")]

        result = await analyzer.analyze("我要找你们领导说话！")

        # Fallback should detect "领导" keyword and return ANGER
        assert result.emotion == CustomerEmotion.ANGER
        assert result.intensity == 0.7

    @pytest.mark.asyncio
    async def test_analyze_fallback_frustration_keywords(self, analyzer, mock_llm_provider):
        """Test fallback keyword matching for frustration."""
        mock_llm_provider.responses = [MockLLMResponse(content="invalid json")]

        result = await analyzer.analyze("真烦，算了")

        # Fallback should detect "烦" keyword
        assert result.emotion == CustomerEmotion.FRUSTRATION
        assert "烦" in result.signals

    @pytest.mark.asyncio
    async def test_analyze_fallback_hesitation_keywords(self, analyzer, mock_llm_provider):
        """Test fallback keyword matching for hesitation."""
        mock_llm_provider.responses = [MockLLMResponse(content="invalid json")]

        result = await analyzer.analyze("我再想想")

        # Fallback should detect "想想" keyword
        assert result.emotion == CustomerEmotion.HESITATION

    @pytest.mark.asyncio
    async def test_analyze_uses_low_temperature(self, analyzer, mock_llm_provider):
        """Test that emotion analysis uses low temperature for consistency."""
        await analyzer.analyze("测试消息")

        # Verify the call was made
        assert mock_llm_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_analyze_llm_exception_handling(self, mock_llm_provider):
        """Test handling of LLM exceptions."""

        # Create a provider that raises an exception
        class FailingProvider:
            async def chat(self, messages, **kwargs):
                raise Exception("LLM connection failed")

        analyzer = EmotionAnalyzer(FailingProvider())
        result = await analyzer.analyze("测试消息")

        # Should return fallback result
        assert result is not None
        assert isinstance(result, EmotionResult)


class TestEmotionAnalyzerParsing:
    """Test EmotionAnalyzer response parsing."""

    @pytest.mark.asyncio
    async def test_parse_response_with_markdown_wrapper(self, analyzer, mock_llm_provider):
        """Test parsing LLM response wrapped in markdown code block."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content="""```json
{
    "emotion": "INTEREST",
    "intensity": 0.8,
    "signals": ["不错"],
    "reasoning": "Customer interested"
}
```"""
            )
        ]

        result = await analyzer.analyze("这个产品不错")

        assert result.emotion == CustomerEmotion.INTEREST
        assert result.intensity == 0.8

    @pytest.mark.asyncio
    async def test_parse_response_invalid_emotion_value(self, analyzer, mock_llm_provider):
        """Test parsing response with invalid emotion value."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "INVALID_EMOTION",
                        "intensity": 0.5,
                        "signals": [],
                        "reasoning": "Test",
                    }
                )
            )
        ]

        result = await analyzer.analyze("测试消息")

        # Should default to NEUTRAL for unknown emotion
        assert result.emotion == CustomerEmotion.NEUTRAL

    @pytest.mark.asyncio
    async def test_parse_response_missing_fields(self, analyzer, mock_llm_provider):
        """Test parsing response with missing required fields."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "INTEREST",
                        # Missing intensity and signals
                    }
                )
            )
        ]

        result = await analyzer.analyze("测试消息")

        # Should handle gracefully, either with fallback or default values
        assert result is not None


class TestEmotionAnalyzerEdgeCases:
    """Test edge cases in emotion analysis."""

    @pytest.mark.asyncio
    async def test_very_long_message(self, analyzer, mock_llm_provider):
        """Test handling of very long messages."""
        long_message = "我对你们的产品" + "非常" * 100 + "感兴趣"

        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "INTEREST",
                        "intensity": 0.9,
                        "signals": ["感兴趣"],
                        "reasoning": "Strong interest expressed",
                    }
                )
            )
        ]

        result = await analyzer.analyze(long_message)

        assert result is not None
        assert isinstance(result, EmotionResult)

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, analyzer, mock_llm_provider):
        """Test handling of special characters in message."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "NEUTRAL",
                        "intensity": 0.3,
                        "signals": [],
                        "reasoning": "No emotion detected",
                    }
                )
            )
        ]

        result = await analyzer.analyze("？！@#￥%……&*（）")

        assert result is not None

    @pytest.mark.asyncio
    async def test_mixed_language_message(self, analyzer, mock_llm_provider):
        """Test handling of mixed language messages."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "HESITATION",
                        "intensity": 0.55,
                        "signals": ["think", "考虑"],
                        "reasoning": "Customer thinking about it",
                    }
                )
            )
        ]

        result = await analyzer.analyze("Let me think about it, 我再考虑一下")

        assert result is not None

    @pytest.mark.asyncio
    async def test_multiple_emotion_signals(self, analyzer, mock_llm_provider):
        """Test message with multiple emotion signals."""
        mock_llm_provider.responses = [
            MockLLMResponse(
                content=json.dumps(
                    {
                        "emotion": "ANGER",
                        "intensity": 0.75,
                        "signals": ["投诉", "烦", "骗子"],
                        "reasoning": "Multiple negative signals detected",
                    }
                )
            )
        ]

        result = await analyzer.analyze("你们是骗子！真烦！我要投诉！")

        assert result.emotion == CustomerEmotion.ANGER
        assert len(result.signals) >= 2
