# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Tests for customer profile extraction and personalization."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from salemates.agent.models.customer import BANTProfile, CustomerProfile, SalesStage
from salemates.agent.profile import (
    CommunicationStyle,
    CustomerProfileExtractor,
    CustomerMemoryContext,
    DecisionStyle,
    EnhancedMemoryManager,
    ExtractedFieldType,
    PersonalizationContext,
    PersonalizationEngine,
    ProfileExtractionResult,
    SalesContextBuilder,
    StrategySuggestion,
)
from salemates.agent.profile.extractor import ExtractedField


class TestCustomerProfileExtractor:
    """Tests for CustomerProfileExtractor."""

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.chat = AsyncMock()
        return provider

    @pytest.fixture
    def extractor(self, mock_provider):
        return CustomerProfileExtractor(mock_provider, model="test-model")

    def test_extracted_field_to_dict(self):
        field = ExtractedField(
            field_type=ExtractedFieldType.BUDGET,
            value="500000",
            confidence=0.9,
            source_message="预算50万",
        )
        result = field.to_dict()
        assert result["field_type"] == "budget"
        assert result["value"] == "500000"
        assert result["confidence"] == 0.9

    def test_profile_extraction_result_has_updates(self):
        result = ProfileExtractionResult()
        assert not result.has_updates()

        result.bant_updates = {"budget": 500000}
        assert result.has_updates()

        result.bant_updates = {}
        result.pain_points = ["效率低"]
        assert result.has_updates()

    @pytest.mark.asyncio
    async def test_extract_empty_conversation(self, extractor):
        result = await extractor.extract("")
        assert isinstance(result, ProfileExtractionResult)
        assert not result.has_updates()

    @pytest.mark.asyncio
    async def test_extract_with_bant_data(self, mock_provider, extractor):
        mock_response = MagicMock()
        mock_response.content = """```json
{
    "bant": {
        "budget": 500000,
        "authority": "技术总监",
        "authority_level": "Director",
        "need": "团队协作工具",
        "need_urgency": "High",
        "timeline": "Q2"
    },
    "pain_points": ["现有工具效率低", "团队沟通不畅"],
    "preferences": {
        "communication_style": "技术型"
    },
    "competitors": [],
    "objections": [],
    "buying_signals": ["询问报价"],
    "risk_signals": [],
    "suggested_stage": "discovery",
    "summary": "客户是技术总监，预算50万，急需团队协作工具"
}
```"""
        mock_provider.chat.return_value = mock_response

        result = await extractor.extract("我们预算50万，我是技术总监")

        assert result.bant_updates.get("budget") == 500000
        assert result.bant_updates.get("authority") == "技术总监"
        assert len(result.pain_points) == 2
        assert result.suggested_stage == SalesStage.DISCOVERY

    def test_apply_updates_to_profile(self, extractor):
        profile = CustomerProfile(id="test_user")
        result = ProfileExtractionResult(
            bant_updates={"budget": 500000, "authority": "技术总监"},
            pain_points=["效率低"],
            competitors=["竞品A"],
            summary="测试摘要",
        )

        updated = extractor.apply_updates(profile, result)

        assert updated.bant.budget == 500000
        assert updated.bant.authority == "技术总监"
        assert "效率低" in updated.pain_points
        assert "竞品A" in updated.competitors
        assert "测试摘要" in updated.notes


class TestPersonalizationEngine:
    """Tests for PersonalizationEngine."""

    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.chat = AsyncMock()
        return provider

    @pytest.fixture
    def engine(self, mock_provider):
        return PersonalizationEngine(mock_provider, model="test-model")

    def test_infer_communication_style_c_level(self, engine):
        profile = CustomerProfile(id="test")
        profile.bant.authority_level = "C-level"
        assert engine.infer_communication_style(profile) == CommunicationStyle.BUSINESS

    def test_infer_communication_style_technical(self, engine):
        profile = CustomerProfile(id="test")
        profile.bant.authority_level = "Director"
        profile.bant.need = "需要一个技术架构设计工具"
        assert engine.infer_communication_style(profile) == CommunicationStyle.TECHNICAL

    def test_infer_decision_style_high_budget(self, engine):
        profile = CustomerProfile(id="test")
        profile.bant.budget = 1000000
        assert engine.infer_decision_style(profile) == DecisionStyle.DELIBERATIVE

    def test_infer_decision_style_urgent(self, engine):
        profile = CustomerProfile(id="test")
        profile.bant.need_urgency = "Critical"
        assert engine.infer_decision_style(profile) == DecisionStyle.QUICK

    def test_infer_decision_style_with_competitors(self, engine):
        profile = CustomerProfile(id="test")
        profile.competitors = ["竞品A", "竞品B"]
        assert engine.infer_decision_style(profile) == DecisionStyle.COMPARATIVE

    @pytest.mark.asyncio
    async def test_generate_strategy(self, mock_provider, engine):
        mock_response = MagicMock()
        mock_response.content = """```json
{
    "strategy_type": "SPIN",
    "content": "先了解客户的具体痛点，然后展示我们的解决方案",
    "reasoning": "客户是技术总监，适合技术导向的沟通",
    "confidence": 0.85,
    "alternatives": ["直接报价", "安排演示"],
    "stage_transition_hint": "presentation"
}
```"""
        mock_provider.chat.return_value = mock_response

        profile = CustomerProfile(id="test")
        profile.bant.authority = "技术总监"
        context = PersonalizationContext(
            customer_id="test",
            profile=profile,
            communication_style=CommunicationStyle.TECHNICAL,
            decision_style=DecisionStyle.COMPARATIVE,
        )

        suggestion = await engine.generate_strategy(
            context=context,
            situation="客户询问价格",
        )

        assert suggestion.strategy_type == "SPIN"
        assert suggestion.confidence == 0.85
        assert len(suggestion.alternatives) == 2


class TestCustomerMemoryContext:
    """Tests for CustomerMemoryContext."""

    def test_to_prompt_context(self):
        profile = CustomerProfile(
            id="test",
            name="张三",
            company="测试公司",
        )
        profile.bant.budget = 500000
        profile.bant.authority = "技术总监"
        profile.pain_points = ["效率低"]

        context = CustomerMemoryContext(
            customer_profile=profile,
            long_term_memory="历史记忆",
            user_profile="用户画像",
            recent_memories=[{"abstract": "上次聊了预算"}],
            personalization_hints={"推荐沟通风格": "技术型"},
        )

        result = context.to_prompt_context()

        assert "客户画像" in result
        assert "张三" in result
        assert "测试公司" in result
        assert "¥500,000" in result
        assert "技术总监" in result
        assert "效率低" in result
        assert "个性化建议" in result


class TestSalesContextBuilder:
    """Tests for SalesContextBuilder."""

    @pytest.fixture
    def mock_provider(self):
        return MagicMock()

    @pytest.fixture
    def mock_sandbox_manager(self):
        manager = MagicMock()
        manager.to_workspace_id = MagicMock(return_value="workspace_001")
        manager.get_sandbox_cwd = AsyncMock(return_value="/sandbox")
        return manager

    @pytest.fixture
    def builder(self, mock_provider, mock_sandbox_manager, tmp_path):
        return SalesContextBuilder(
            workspace=tmp_path,
            provider=mock_provider,
            sandbox_manager=mock_sandbox_manager,
            sender_id="user_123",
        )

    def test_lazy_loading_enhanced_memory(self, builder, mock_provider):
        assert builder._enhanced_memory is None
        memory = builder.enhanced_memory
        assert memory is not None
        assert isinstance(memory, EnhancedMemoryManager)

    def test_lazy_loading_personalization_engine(self, builder, mock_provider):
        assert builder._personalization_engine is None
        engine = builder.personalization_engine
        assert engine is not None
        assert isinstance(engine, PersonalizationEngine)

    def test_format_personalization_section(self, builder):
        profile = CustomerProfile(id="test")
        profile.bant.budget = 500000
        profile.bant.authority = "技术总监"
        profile.bant.need = "团队协作"

        context = CustomerMemoryContext(
            customer_profile=profile,
            long_term_memory="",
            user_profile="",
            personalization_hints={
                "推荐沟通风格": "technical",
                "推荐决策策略": "comparative",
                "紧迫性": "高，建议快速响应",
            },
        )

        result = builder._format_personalization_section(context)

        assert "个性化沟通建议" in result
        assert "技术导向" in result
        assert "比较型决策者" in result
        assert "高，建议快速响应" in result


class TestBANTProfile:
    """Tests for BANTProfile."""

    def test_is_qualified(self):
        bant = BANTProfile(
            budget=500000,
            authority="技术总监",
            need="团队协作工具",
            timeline="Q2",
        )
        assert bant.is_qualified()

    def test_is_not_qualified(self):
        bant = BANTProfile(budget=500000)
        assert not bant.is_qualified()

    def test_qualification_score(self):
        bant = BANTProfile(
            budget=500000,
            budget_confirmed=True,
            authority="技术总监",
            authority_level="Director",
            need="团队协作工具",
            need_urgency="High",
            timeline="Q2",
            timeline_confirmed=True,
        )
        score = bant.qualification_score()
        assert score > 0.8


class TestCustomerProfile:
    """Tests for CustomerProfile."""

    def test_can_transition_to(self):
        profile = CustomerProfile(id="test")
        assert profile.can_transition_to(SalesStage.DISCOVERY)
        assert not profile.can_transition_to(SalesStage.CLOSE)

    def test_transition_to(self):
        profile = CustomerProfile(id="test")
        assert profile.transition_to(SalesStage.DISCOVERY)
        assert profile.stage == SalesStage.DISCOVERY
        assert not profile.transition_to(SalesStage.CLOSE)

    def test_add_pain_point(self):
        profile = CustomerProfile(id="test")
        profile.add_pain_point("效率低")
        profile.add_pain_point("沟通难")
        profile.add_pain_point("效率低")
        assert len(profile.pain_points) == 2

    def test_update_bant(self):
        profile = CustomerProfile(id="test")
        profile.update_bant(
            budget=500000,
            authority="技术总监",
            need="团队协作工具",
        )
        assert profile.bant.budget == 500000
        assert profile.bant.authority == "技术总监"
