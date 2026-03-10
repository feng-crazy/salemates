# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Personalization engine for thousand-person-thousand-faces strategy.

This module provides personalized strategy generation based on customer
profiles, including adaptive SPIN/FAB scripts, dynamic tone adjustment,
and context-aware response suggestions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from loguru import logger

from salemates.agent.models.customer import CustomerProfile, SalesStage
from salemates.providers.base import LLMProvider


class CommunicationStyle(str, Enum):
    """Customer communication style preferences."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    TECHNICAL = "technical"
    BUSINESS = "business"
    CASUAL = "casual"
    FORMAL = "formal"


class DecisionStyle(str, Enum):
    """Customer decision-making style."""

    QUICK = "quick"
    COMPARATIVE = "comparative"
    DELIBERATIVE = "deliberative"
    DELEGATING = "delegating"


@dataclass
class PersonalizationContext:
    """Context for personalization decisions."""

    customer_id: str
    profile: CustomerProfile
    communication_style: CommunicationStyle = CommunicationStyle.DIRECT
    decision_style: DecisionStyle = DecisionStyle.COMPARATIVE
    recent_interactions: int = 0
    engagement_level: str = "medium"
    preferred_topics: list[str] = field(default_factory=list)
    avoid_topics: list[str] = field(default_factory=list)
    successful_approaches: list[str] = field(default_factory=list)
    failed_approaches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "communication_style": self.communication_style.value,
            "decision_style": self.decision_style.value,
            "recent_interactions": self.recent_interactions,
            "engagement_level": self.engagement_level,
            "preferred_topics": self.preferred_topics,
            "avoid_topics": self.avoid_topics,
            "successful_approaches": self.successful_approaches,
            "failed_approaches": self.failed_approaches,
        }


@dataclass
class StrategySuggestion:
    """A personalized strategy suggestion."""

    strategy_type: str
    content: str
    reasoning: str
    confidence: float
    alternatives: list[str] = field(default_factory=list)
    stage_transition_hint: Optional[SalesStage] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_type": self.strategy_type,
            "content": self.content,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "stage_transition_hint": (
                self.stage_transition_hint.value if self.stage_transition_hint else None
            ),
        }


class PersonalizationEngine:
    """
    Generates personalized strategies based on customer profiles.

    This engine implements the "thousand-person-thousand-faces" concept by:
    1. Analyzing customer profile and preferences
    2. Adapting sales methodology (SPIN/FAB/BANT) to customer style
    3. Generating context-aware response suggestions
    4. Learning from interaction history

    Example:
        >>> engine = PersonalizationEngine(provider)
        >>> context = PersonalizationContext(
        ...     customer_id="123",
        ...     profile=customer_profile,
        ...     communication_style=CommunicationStyle.TECHNICAL,
        ... )
        >>> suggestion = await engine.generate_strategy(context, "客户询问价格")
        >>> print(suggestion.content)
    """

    STRATEGY_PROMPT = """你是一个专业的销售策略顾问，需要根据客户画像生成个性化的销售策略。

## 客户画像
{customer_profile}

## 客户偏好
- 沟通风格: {communication_style}
- 决策风格: {decision_style}
- 参与度: {engagement_level}
- 感兴趣的话题: {preferred_topics}
- 需要避免的话题: {avoid_topics}
- 成功过的策略: {successful_approaches}

## 当前情况
- 销售阶段: {current_stage}
- 当前情境: {situation}
- 客户最近的情绪: {recent_emotion}

## 任务
基于以上信息，生成一个个性化的销售策略建议。

## 输出格式（严格JSON）
```json
{{
    "strategy_type": "<SPIN/FAB/BANT/CLOSING/FOLLOW_UP>",
    "content": "<策略内容，包含具体话术建议>",
    "reasoning": "<为什么这个策略适合这个客户>",
    "confidence": <0.0-1.0>,
    "alternatives": ["<备选策略1>", "<备选策略2>"],
    "stage_transition_hint": "<建议的下一阶段或null>"
}}
```

## 策略选择原则
1. 技术型客户：侧重技术细节、数据、ROI分析
2. 商务型客户：侧重价值、案例、ROI
3. 直接型客户：简洁明了，快速给结论
4. 委婉型客户：循序渐进，先建立信任
5. 快速决策者：提供明确选项，推动成交
6. 比较型决策者：提供对比分析，竞品差异

只输出JSON，不要其他内容。"""

    def __init__(
        self,
        provider: LLMProvider,
        model: str | None = None,
    ):
        self.provider = provider
        self.model = model
        self.logger = logger.bind(component="PersonalizationEngine")

    async def generate_strategy(
        self,
        context: PersonalizationContext,
        situation: str,
        recent_emotion: str = "neutral",
    ) -> StrategySuggestion:
        """
        Generate a personalized strategy suggestion.

        Args:
            context: Personalization context with customer profile and preferences.
            situation: The current situation or customer question.
            recent_emotion: Recent detected emotion from customer.

        Returns:
            StrategySuggestion with personalized content.
        """
        prompt = self.STRATEGY_PROMPT.format(
            customer_profile=self._format_profile(context.profile),
            communication_style=context.communication_style.value,
            decision_style=context.decision_style.value,
            engagement_level=context.engagement_level,
            preferred_topics=", ".join(context.preferred_topics) or "无",
            avoid_topics=", ".join(context.avoid_topics) or "无",
            successful_approaches=", ".join(context.successful_approaches) or "无",
            current_stage=context.profile.stage.value,
            situation=situation,
            recent_emotion=recent_emotion,
        )

        try:
            response = await self.provider.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的销售策略顾问。只输出JSON。"},
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )

            return self._parse_strategy_response(response.content or "")

        except Exception as e:
            self.logger.warning(f"Strategy generation failed: {e}")
            return StrategySuggestion(
                strategy_type="FALLBACK",
                content="基于客户画像，建议继续了解客户需求，建立信任关系。",
                reasoning="策略生成失败，使用默认策略",
                confidence=0.5,
            )

    def _format_profile(self, profile: CustomerProfile) -> str:
        """Format customer profile for prompt."""
        lines = [
            f"姓名: {profile.name or '未知'}",
            f"公司: {profile.company or '未知'}",
            f"阶段: {profile.stage.value}",
            f"BANT评分: {profile.bant.qualification_score():.0%}",
        ]

        if profile.bant.budget:
            lines.append(f"预算: ¥{profile.bant.budget:,.0f}")
        if profile.bant.authority:
            lines.append(
                f"决策者: {profile.bant.authority} ({profile.bant.authority_level or '未知级别'})"
            )
        if profile.bant.need:
            lines.append(f"需求: {profile.bant.need}")
            if profile.bant.need_urgency:
                lines.append(f"需求紧迫度: {profile.bant.need_urgency}")
        if profile.bant.timeline:
            lines.append(f"时间线: {profile.bant.timeline}")
        if profile.pain_points:
            lines.append(f"痛点: {', '.join(profile.pain_points)}")
        if profile.competitors:
            lines.append(f"关注竞品: {', '.join(profile.competitors)}")

        return "\n".join(lines)

    def _parse_strategy_response(self, content: str) -> StrategySuggestion:
        """Parse LLM response into StrategySuggestion."""
        import re

        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

        data = json.loads(json_str)

        stage_hint = None
        if stage_str := data.get("stage_transition_hint"):
            try:
                stage_hint = SalesStage(stage_str)
            except ValueError:
                pass

        return StrategySuggestion(
            strategy_type=data.get("strategy_type", "SPIN"),
            content=data.get("content", ""),
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 0.7)),
            alternatives=data.get("alternatives", []),
            stage_transition_hint=stage_hint,
        )

    def infer_communication_style(self, profile: CustomerProfile) -> CommunicationStyle:
        """Infer communication style from profile."""
        if profile.bant.authority_level in ("C-level", "VP"):
            return CommunicationStyle.BUSINESS
        if profile.bant.authority_level in ("Director", "Manager"):
            if profile.bant.need and any(
                kw in profile.bant.need.lower() for kw in ["技术", "开发", "架构", "api", "集成"]
            ):
                return CommunicationStyle.TECHNICAL
            return CommunicationStyle.BUSINESS
        return CommunicationStyle.DIRECT

    def infer_decision_style(self, profile: CustomerProfile) -> DecisionStyle:
        """Infer decision style from profile."""
        if profile.bant.budget and profile.bant.budget > 500000:
            return DecisionStyle.DELIBERATIVE
        if profile.bant.need_urgency in ("Critical", "High"):
            return DecisionStyle.QUICK
        if profile.competitors:
            return DecisionStyle.COMPARATIVE
        return DecisionStyle.DELIBERATIVE
