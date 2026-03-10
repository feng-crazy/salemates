# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Customer profile extractor for automatic BANT and preference extraction.

This module provides intelligent extraction of customer information from
conversation text, including BANT qualification data, pain points,
preferences, and behavioral signals.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from loguru import logger

from salemates.agent.models.customer import BANTProfile, CustomerProfile, SalesStage
from salemates.providers.base import LLMProvider


class ExtractedFieldType(str, Enum):
    """Types of fields that can be extracted from conversation."""

    BUDGET = "budget"
    AUTHORITY = "authority"
    NEED = "need"
    TIMELINE = "timeline"
    PAIN_POINT = "pain_point"
    PREFERENCE = "preference"
    COMPETITOR = "competitor"
    OBJECTION = "objection"
    BUYING_SIGNAL = "buying_signal"
    RISK_SIGNAL = "risk_signal"


@dataclass
class ExtractedField:
    """A field extracted from conversation with confidence score."""

    field_type: ExtractedFieldType
    value: str
    confidence: float
    source_message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field_type": self.field_type.value,
            "value": self.value,
            "confidence": self.confidence,
            "source_message": self.source_message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProfileExtractionResult:
    """Result of profile extraction from a conversation."""

    fields: list[ExtractedField] = field(default_factory=list)
    bant_updates: dict[str, Any] = field(default_factory=dict)
    pain_points: list[str] = field(default_factory=list)
    preferences: dict[str, str] = field(default_factory=dict)
    competitors: list[str] = field(default_factory=list)
    objections: list[str] = field(default_factory=list)
    buying_signals: list[str] = field(default_factory=list)
    risk_signals: list[str] = field(default_factory=list)
    suggested_stage: Optional[SalesStage] = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "fields": [f.to_dict() for f in self.fields],
            "bant_updates": self.bant_updates,
            "pain_points": self.pain_points,
            "preferences": self.preferences,
            "competitors": self.competitors,
            "objections": self.objections,
            "buying_signals": self.buying_signals,
            "risk_signals": self.risk_signals,
            "suggested_stage": self.suggested_stage.value if self.suggested_stage else None,
            "summary": self.summary,
        }

    def has_updates(self) -> bool:
        """Check if there are any meaningful updates."""
        return bool(
            self.bant_updates
            or self.pain_points
            or self.preferences
            or self.competitors
            or self.objections
            or self.buying_signals
            or self.risk_signals
        )


class CustomerProfileExtractor:
    """
    Extracts customer profile information from conversation text.

    Uses LLM to intelligently extract BANT qualification data, pain points,
    preferences, and behavioral signals from natural conversation.

    Example:
        >>> extractor = CustomerProfileExtractor(provider)
        >>> result = await extractor.extract(
        ...     "我们的预算大概在50万左右，我是技术总监，想要一个协作工具",
        ...     current_profile
        ... )
        >>> print(result.bant_updates)
        {'budget': 500000, 'authority': '技术总监'}
    """

    EXTRACTION_PROMPT = """你是一个专业的销售客户画像分析专家。从以下对话内容中提取客户信息。

## 输出格式
请严格按以下JSON格式输出，不要添加任何其他内容：

```json
{
    "bant": {
        "budget": <数字或null>,
        "budget_confirmed": <true/false>,
        "authority": "<决策者角色或null>",
        "authority_level": "<C-level/VP/Director/Manager/Individual Contributor/null>",
        "need": "<核心需求描述或null>",
        "need_urgency": "<Critical/High/Medium/Low/null>",
        "timeline": "<购买时间线或null>",
        "timeline_confirmed": <true/false>
    },
    "pain_points": ["<痛点1>", "<痛点2>"],
    "preferences": {
        "<偏好类型>": "<偏好内容>",
        "communication_style": "<直接/委婉/技术型/商务型>",
        "decision_style": "<快速决策/需要比较/需要汇报>"
    },
    "competitors": ["<竞品1>", "<竞品2>"],
    "objections": ["<异议1>", "<异议2>"],
    "buying_signals": ["<购买信号1>"],
    "risk_signals": ["<风险信号1>"],
    "suggested_stage": "<new_contact/discovery/presentation/negotiation/close/lost>",
    "summary": "<本次对话关键信息总结>"
}
```

## 当前客户画像
{current_profile}

## 对话内容
{conversation}

## 提取规则
1. 只提取明确提及的信息，不要推测
2. 金额转换为人民币数字（去掉单位）
3. 权限级别根据角色判断
4. 购买信号：提及预算、询问报价、要求演示、对比竞品、询问实施
5. 风险信号：提及竞品优势、预算削减、项目暂停、人事变动
6. 痛点：客户表达的困难、不满、低效之处
7. 偏好：沟通风格、决策风格、技术偏好等

请输出JSON："""

    def __init__(
        self,
        provider: LLMProvider,
        model: str | None = None,
        min_confidence: float = 0.7,
    ):
        """
        Initialize the profile extractor.

        Args:
            provider: LLM provider for text analysis.
            model: Model to use for extraction.
            min_confidence: Minimum confidence threshold for extraction.
        """
        self.provider = provider
        self.model = model
        self.min_confidence = min_confidence
        self.logger = logger.bind(component="ProfileExtractor")

    async def extract(
        self,
        conversation: str,
        current_profile: CustomerProfile | None = None,
        context: dict[str, Any] | None = None,
    ) -> ProfileExtractionResult:
        """
        Extract customer profile information from conversation text.

        Args:
            conversation: The conversation text to analyze.
            current_profile: Existing customer profile for context.
            context: Additional context (channel, timestamp, etc.).

        Returns:
            ProfileExtractionResult with extracted fields and updates.
        """
        if not conversation or not conversation.strip():
            return ProfileExtractionResult()

        # Format current profile for context
        profile_context = self._format_profile_context(current_profile)

        # Build prompt
        prompt = self.EXTRACTION_PROMPT.format(
            current_profile=profile_context,
            conversation=conversation[:3000],  # Limit length
        )

        try:
            # Call LLM
            response = await self.provider.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的客户画像分析专家。只输出JSON，不要有其他内容。",
                    },
                    {"role": "user", "content": prompt},
                ],
                model=self.model,
            )

            # Parse response
            content = response.content or ""
            result = self._parse_extraction_result(content)

            self.logger.info(
                f"Extracted {len(result.fields)} fields from conversation",
                has_updates=result.has_updates(),
            )

            return result

        except Exception as e:
            self.logger.warning(f"Profile extraction failed: {e}")
            return ProfileExtractionResult()

    def _format_profile_context(self, profile: CustomerProfile | None) -> str:
        """Format current profile for prompt context."""
        if not profile:
            return "无现有画像信息"

        lines = [
            f"客户姓名: {profile.name or '未知'}",
            f"公司: {profile.company or '未知'}",
            f"当前阶段: {profile.stage.value}",
            f"BANT评分: {profile.bant.qualification_score():.0%}",
        ]

        if profile.bant.budget:
            lines.append(f"预算: ¥{profile.bant.budget:,.0f}")
        if profile.bant.authority:
            lines.append(f"决策者: {profile.bant.authority}")
        if profile.bant.need:
            lines.append(f"需求: {profile.bant.need}")
        if profile.bant.timeline:
            lines.append(f"时间线: {profile.bant.timeline}")
        if profile.pain_points:
            lines.append(f"已知痛点: {', '.join(profile.pain_points)}")
        if profile.competitors:
            lines.append(f"关注竞品: {', '.join(profile.competitors)}")

        return "\n".join(lines)

    def _parse_extraction_result(self, content: str) -> ProfileExtractionResult:
        """Parse LLM response into ProfileExtractionResult."""
        result = ProfileExtractionResult()

        # Extract JSON from response
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
            else:
                self.logger.warning("No JSON found in extraction response")
                return result

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON: {e}")
            return result

        # Parse BANT updates
        if bant_data := data.get("bant"):
            if bant_data.get("budget") is not None:
                result.bant_updates["budget"] = float(bant_data["budget"])
            if bant_data.get("budget_confirmed") is not None:
                result.bant_updates["budget_confirmed"] = bant_data["budget_confirmed"]
            if bant_data.get("authority"):
                result.bant_updates["authority"] = bant_data["authority"]
            if bant_data.get("authority_level"):
                result.bant_updates["authority_level"] = bant_data["authority_level"]
            if bant_data.get("need"):
                result.bant_updates["need"] = bant_data["need"]
            if bant_data.get("need_urgency"):
                result.bant_updates["need_urgency"] = bant_data["need_urgency"]
            if bant_data.get("timeline"):
                result.bant_updates["timeline"] = bant_data["timeline"]
            if bant_data.get("timeline_confirmed") is not None:
                result.bant_updates["timeline_confirmed"] = bant_data["timeline_confirmed"]

        # Parse lists
        result.pain_points = data.get("pain_points", [])
        result.preferences = data.get("preferences", {})
        result.competitors = data.get("competitors", [])
        result.objections = data.get("objections", [])
        result.buying_signals = data.get("buying_signals", [])
        result.risk_signals = data.get("risk_signals", [])
        result.summary = data.get("summary", "")

        # Parse suggested stage
        if stage_str := data.get("suggested_stage"):
            try:
                result.suggested_stage = SalesStage(stage_str)
            except ValueError:
                pass

        # Build extracted fields list
        for key, value in result.bant_updates.items():
            field_type_map = {
                "budget": ExtractedFieldType.BUDGET,
                "authority": ExtractedFieldType.AUTHORITY,
                "need": ExtractedFieldType.NEED,
                "timeline": ExtractedFieldType.TIMELINE,
            }
            if key in field_type_map:
                result.fields.append(
                    ExtractedField(
                        field_type=field_type_map[key],
                        value=str(value),
                        confidence=0.85,  # Default confidence
                        source_message=result.summary,
                    )
                )

        for pp in result.pain_points:
            result.fields.append(
                ExtractedField(
                    field_type=ExtractedFieldType.PAIN_POINT,
                    value=pp,
                    confidence=0.8,
                    source_message=result.summary,
                )
            )

        return result

    async def apply_updates(
        self,
        profile: CustomerProfile,
        extraction_result: ProfileExtractionResult,
    ) -> CustomerProfile:
        """
        Apply extraction results to a customer profile.

        Args:
            profile: The profile to update.
            extraction_result: The extraction result to apply.

        Returns:
            Updated customer profile.
        """
        # Apply BANT updates
        if extraction_result.bant_updates:
            profile.update_bant(**extraction_result.bant_updates)

        # Add pain points
        for pain_point in extraction_result.pain_points:
            profile.add_pain_point(pain_point)

        # Add competitors
        for competitor in extraction_result.competitors:
            profile.add_competitor(competitor)

        # Update notes with summary
        if extraction_result.summary:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            if profile.notes:
                profile.notes += f"\n[{timestamp}] {extraction_result.summary}"
            else:
                profile.notes = f"[{timestamp}] {extraction_result.summary}"

        # Update stage if suggested and valid
        if extraction_result.suggested_stage:
            if profile.can_transition_to(extraction_result.suggested_stage):
                profile.transition_to(extraction_result.suggested_stage)
                self.logger.info(
                    f"Stage transition: {profile.stage.value} -> {extraction_result.suggested_stage.value}"
                )

        return profile
