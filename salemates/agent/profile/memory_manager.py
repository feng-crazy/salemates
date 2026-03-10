# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Enhanced memory store with customer profile integration.

This module provides an enhanced memory system that integrates CustomerProfile
with OpenViking user memory, enabling semantic search and personalization.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from salemates.agent.memory import MemoryStore
from salemates.agent.models.customer import CustomerProfile
from salemates.agent.profile.extractor import CustomerProfileExtractor, ProfileExtractionResult
from salemates.agent.profile.personalization import (
    CommunicationStyle,
    DecisionStyle,
    PersonalizationContext,
    PersonalizationEngine,
)
from salemates.openviking_mount.ov_server import VikingClient
from salemates.providers.base import LLMProvider


@dataclass
class CustomerMemoryContext:
    """Combined context from memory and customer profile."""

    customer_profile: CustomerProfile
    long_term_memory: str
    user_profile: str
    recent_memories: list[dict[str, Any]] = field(default_factory=list)
    personalization_hints: dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Format as context string for LLM prompt."""
        parts = []

        parts.append("## 客户画像")
        parts.append(self._format_profile(self.customer_profile))

        if self.user_profile:
            parts.append("\n## 客户长期画像")
            parts.append(self.user_profile[:500])

        if self.long_term_memory:
            parts.append("\n## 会话记忆")
            parts.append(self.long_term_memory[:500])

        if self.recent_memories:
            parts.append("\n## 相关历史记忆")
            for mem in self.recent_memories[:3]:
                if abstract := mem.get("abstract"):
                    parts.append(f"- {abstract}")

        if self.personalization_hints:
            parts.append("\n## 个性化建议")
            for key, value in self.personalization_hints.items():
                parts.append(f"- {key}: {value}")

        return "\n".join(parts)

    def _format_profile(self, profile: CustomerProfile) -> str:
        lines = [
            f"- 姓名: {profile.name or '未知'}",
            f"- 公司: {profile.company or '未知'}",
            f"- 阶段: {profile.stage.value}",
            f"- BANT评分: {profile.bant.qualification_score():.0%}",
        ]
        if profile.bant.budget:
            lines.append(f"- 预算: ¥{profile.bant.budget:,.0f}")
        if profile.bant.authority:
            lines.append(f"- 决策者: {profile.bant.authority}")
        if profile.bant.need:
            lines.append(f"- 需求: {profile.bant.need}")
        if profile.bant.timeline:
            lines.append(f"- 时间线: {profile.bant.timeline}")
        if profile.pain_points:
            lines.append(f"- 痛点: {', '.join(profile.pain_points[:3])}")
        return "\n".join(lines)


class EnhancedMemoryManager:
    """
    Manages enhanced memory with customer profile integration.

    This class provides:
    1. Unified access to CustomerProfile and OpenViking memory
    2. Automatic profile extraction from conversations
    3. Semantic memory search for sales context
    4. Personalization context generation

    Example:
        >>> manager = EnhancedMemoryManager(provider, workspace)
        >>> context = await manager.get_context("user_123", "我想了解你们的产品")
        >>> print(context.to_prompt_context())
    """

    def __init__(
        self,
        provider: LLMProvider,
        workspace: Path,
        model: str | None = None,
        enable_extraction: bool = True,
    ):
        self.provider = provider
        self.workspace = workspace
        self.model = model
        self.enable_extraction = enable_extraction

        self.memory_store = MemoryStore(workspace)
        self.profile_extractor = (
            CustomerProfileExtractor(provider, model) if enable_extraction else None
        )
        self.personalization_engine = PersonalizationEngine(provider, model)

        self._profile_cache: dict[str, CustomerProfile] = {}
        self._viking_client: Optional[VikingClient] = None

        self.logger = logger.bind(component="EnhancedMemoryManager")

    async def _get_viking_client(self, workspace_id: str) -> VikingClient:
        """Get or create VikingClient."""
        if self._viking_client is None:
            self._viking_client = await VikingClient.create(agent_id=workspace_id)
        return self._viking_client

    async def get_context(
        self,
        user_id: str,
        current_message: str,
        workspace_id: str,
        session_history: list[dict[str, Any]] | None = None,
    ) -> CustomerMemoryContext:
        """
        Get comprehensive context for a customer.

        Args:
            user_id: Customer user ID.
            current_message: Current message from customer.
            workspace_id: Workspace ID for Viking client.
            session_history: Recent session messages for extraction.

        Returns:
            CustomerMemoryContext with all relevant information.
        """
        profile = await self._get_or_create_profile(user_id, workspace_id)
        long_term_memory = self.memory_store.read_long_term()
        user_profile = await self._get_viking_user_profile(workspace_id, user_id)
        recent_memories = await self._search_relevant_memories(
            workspace_id, user_id, current_message
        )
        personalization_hints = self._build_personalization_hints(profile)

        if session_history and self.profile_extractor:
            await self._maybe_update_profile(user_id, profile, session_history, workspace_id)

        return CustomerMemoryContext(
            customer_profile=profile,
            long_term_memory=long_term_memory,
            user_profile=user_profile,
            recent_memories=recent_memories,
            personalization_hints=personalization_hints,
        )

    async def _get_or_create_profile(self, user_id: str, workspace_id: str) -> CustomerProfile:
        """Get cached profile or create new one."""
        if user_id in self._profile_cache:
            return self._profile_cache[user_id]

        profile = CustomerProfile(id=user_id)
        self._profile_cache[user_id] = profile
        return profile

    async def _get_viking_user_profile(self, workspace_id: str, user_id: str) -> str:
        """Get user profile from OpenViking."""
        try:
            client = await self._get_viking_client(workspace_id)
            return await client.read_user_profile(user_id)
        except Exception as e:
            self.logger.warning(f"Failed to get Viking user profile: {e}")
            return ""

    async def _search_relevant_memories(
        self,
        workspace_id: str,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for relevant memories in OpenViking."""
        try:
            client = await self._get_viking_client(workspace_id)
            result = await client.search_memory(query, user_id, limit=limit)
            return result.get("user_memory", []) + result.get("agent_memory", [])
        except Exception as e:
            self.logger.warning(f"Memory search failed: {e}")
            return []

    def _build_personalization_hints(self, profile: CustomerProfile) -> dict[str, Any]:
        """Build personalization hints from profile."""
        hints = {}

        comm_style = self.personalization_engine.infer_communication_style(profile)
        hints["推荐沟通风格"] = comm_style.value

        decision_style = self.personalization_engine.infer_decision_style(profile)
        hints["推荐决策策略"] = decision_style.value

        if profile.bant.need_urgency in ("Critical", "High"):
            hints["紧迫性"] = "高，建议快速响应"

        if profile.pain_points:
            hints["关注痛点"] = profile.pain_points[0]

        if profile.bant.qualification_score() > 0.75:
            hints["线索质量"] = "高，可推进到下一阶段"

        return hints

    async def _maybe_update_profile(
        self,
        user_id: str,
        profile: CustomerProfile,
        session_history: list[dict[str, Any]],
        workspace_id: str,
        min_messages: int = 3,
    ) -> None:
        """Extract and update profile if enough new messages."""
        if len(session_history) < min_messages:
            return

        recent_messages = session_history[-min_messages:]
        conversation = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent_messages
        )

        try:
            result = await self.profile_extractor.extract(conversation, profile)

            if result.has_updates():
                await self.profile_extractor.apply_updates(profile, result)

                await self._sync_profile_to_viking(workspace_id, user_id, profile, result)

                self.logger.info(
                    f"Updated profile for {user_id}",
                    bant_updates=list(result.bant_updates.keys()),
                    pain_points=len(result.pain_points),
                )

        except Exception as e:
            self.logger.warning(f"Profile extraction failed: {e}")

    async def _sync_profile_to_viking(
        self,
        workspace_id: str,
        user_id: str,
        profile: CustomerProfile,
        extraction_result: ProfileExtractionResult,
    ) -> None:
        """Sync profile updates to OpenViking user memory."""
        try:
            client = await self._get_viking_client(workspace_id)

            profile_content = self._format_profile_for_viking(profile, extraction_result)

            self.logger.debug(
                f"Would sync profile to Viking for {user_id}: {len(profile_content)} chars"
            )

        except Exception as e:
            self.logger.warning(f"Failed to sync profile to Viking: {e}")

    def _format_profile_for_viking(
        self,
        profile: CustomerProfile,
        extraction_result: ProfileExtractionResult,
    ) -> str:
        """Format profile for OpenViking storage."""
        lines = [
            f"# 客户画像 - {profile.name or profile.id}",
            f"\n更新时间: {datetime.utcnow().isoformat()}",
            f"\n## 基本信息",
            f"- 公司: {profile.company or '未知'}",
            f"- 销售阶段: {profile.stage.value}",
            f"- BANT评分: {profile.bant.qualification_score():.0%}",
        ]

        if extraction_result.bant_updates:
            lines.append("\n## 最近更新的BANT信息")
            for key, value in extraction_result.bant_updates.items():
                lines.append(f"- {key}: {value}")

        if extraction_result.pain_points:
            lines.append("\n## 痛点")
            for pp in extraction_result.pain_points:
                lines.append(f"- {pp}")

        if extraction_result.preferences:
            lines.append("\n## 偏好")
            for key, value in extraction_result.preferences.items():
                lines.append(f"- {key}: {value}")

        if extraction_result.summary:
            lines.append(f"\n## 最近互动总结")
            lines.append(extraction_result.summary)

        return "\n".join(lines)

    def update_profile_cache(self, user_id: str, profile: CustomerProfile) -> None:
        """Update the in-memory profile cache."""
        self._profile_cache[user_id] = profile

    def get_cached_profile(self, user_id: str) -> Optional[CustomerProfile]:
        """Get profile from cache if available."""
        return self._profile_cache.get(user_id)

    def clear_cache(self) -> None:
        """Clear the profile cache."""
        self._profile_cache.clear()
