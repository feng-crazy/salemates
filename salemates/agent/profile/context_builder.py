# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Sales context builder with customer personalization.

Extends ContextBuilder with customer profile integration,
personalized prompts, and sales-specific context assembly.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from salemates.agent.context import ContextBuilder
from salemates.agent.profile import (
    CommunicationStyle,
    CustomerMemoryContext,
    DecisionStyle,
    EnhancedMemoryManager,
    PersonalizationContext,
    PersonalizationEngine,
)
from salemates.agent.profile.extractor import ProfileExtractionResult
from salemates.config.schema import SessionKey
from salemates.providers.base import LLMProvider
from salemates.sandbox import SandboxManager


class SalesContextBuilder(ContextBuilder):
    """
    Enhanced context builder for sales scenarios.

    Adds customer personalization, profile-aware prompts,
    and sales-specific context to the base ContextBuilder.

    Example:
        >>> builder = SalesContextBuilder(
        ...     workspace=workspace,
        ...     provider=llm_provider,
        ...     sandbox_manager=sandbox_manager,
        ...     sender_id="user_123"
        ... )
        >>> messages = await builder.build_messages(
        ...     history=session.get_history(),
        ...     current_message="我想了解报价",
        ...     session_key=session_key
        ... )
    """

    SALES_BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "TOOLS.md", "IDENTITY.md", "SALES_GUIDE.md"]

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider | None = None,
        model: str | None = None,
        sandbox_manager: SandboxManager | None = None,
        sender_id: str | None = None,
        is_group_chat: bool = False,
        eval: bool = False,
        enable_personalization: bool = True,
        enable_profile_extraction: bool = True,
    ):
        super().__init__(
            workspace=workspace,
            sandbox_manager=sandbox_manager,
            sender_id=sender_id,
            is_group_chat=is_group_chat,
            eval=eval,
        )

        self.provider = provider
        self.model = model
        self.enable_personalization = enable_personalization
        self.enable_profile_extraction = enable_profile_extraction

        self._enhanced_memory: EnhancedMemoryManager | None = None
        self._personalization_engine: PersonalizationEngine | None = None
        self._last_extraction_result: ProfileExtractionResult | None = None

        self.logger = logger.bind(component="SalesContextBuilder")

    @property
    def enhanced_memory(self) -> EnhancedMemoryManager | None:
        """Lazy-load EnhancedMemoryManager."""
        if self._enhanced_memory is None and self.provider:
            self._enhanced_memory = EnhancedMemoryManager(
                provider=self.provider,
                workspace=self.workspace,
                model=self.model,
                enable_extraction=self.enable_profile_extraction,
            )
        return self._enhanced_memory

    @property
    def personalization_engine(self) -> PersonalizationEngine | None:
        """Lazy-load PersonalizationEngine."""
        if self._personalization_engine is None and self.provider:
            self._personalization_engine = PersonalizationEngine(
                provider=self.provider,
                model=self.model,
            )
        return self._personalization_engine

    async def build_system_prompt(
        self,
        session_key: SessionKey,
        current_message: str,
        history: list[dict[str, Any]],
    ) -> str:
        """
        Build enhanced system prompt with customer personalization.

        Extends base ContextBuilder with:
        1. Customer profile context
        2. Personalization hints
        3. Sales-specific instructions
        """
        parts = []

        base_prompt = await super().build_system_prompt(session_key, current_message, history)
        parts.append(base_prompt)

        if self._sender_id and self.enhanced_memory and self.sandbox_manager:
            workspace_id = self.sandbox_manager.to_workspace_id(session_key)

            try:
                customer_context = await self.enhanced_memory.get_context(
                    user_id=self._sender_id,
                    current_message=current_message,
                    workspace_id=workspace_id,
                    session_history=history,
                )

                if customer_context.personalization_hints:
                    personalization_section = self._format_personalization_section(customer_context)
                    parts.append(personalization_section)

                self._last_extraction_result = None

            except Exception as e:
                self.logger.warning(f"Failed to get customer context: {e}")

        return "\n\n---\n\n".join(parts)

    def _format_personalization_section(self, context: CustomerMemoryContext) -> str:
        """Format personalization hints for LLM prompt."""
        hints = context.personalization_hints
        profile = context.customer_profile

        lines = ["## 个性化沟通建议"]

        if "推荐沟通风格" in hints:
            style_map = {
                "technical": "技术导向：侧重技术细节、数据、架构设计",
                "business": "商务导向：侧重价值、ROI、案例、竞品对比",
                "direct": "直接高效：简洁明了，快速给结论",
                "indirect": "循序渐进：先建立信任，再推进话题",
            }
            style = hints["推荐沟通风格"]
            lines.append(f"- 沟通风格: {style_map.get(style, style)}")

        if "推荐决策策略" in hints:
            strategy_map = {
                "quick": "快速决策者：提供明确选项，推动成交",
                "comparative": "比较型决策者：提供对比分析，突出优势",
                "deliberative": "深思熟虑型：提供详细资料，给予考虑时间",
                "delegating": "授权型：准备汇报材料，帮助向上汇报",
            }
            strategy = hints["推荐决策策略"]
            lines.append(f"- 决策策略: {strategy_map.get(strategy, strategy)}")

        if "紧迫性" in hints:
            lines.append(f"- 紧迫性: {hints['紧迫性']}")

        if "关注痛点" in hints:
            lines.append(f"- 核心痛点: {hints['关注痛点']}")

        if profile.bant.qualification_score() > 0.6:
            lines.append(f"- 线索评分: {profile.bant.qualification_score():.0%} (优质线索)")

        return "\n".join(lines)

    async def get_personalized_strategy(
        self,
        situation: str,
        recent_emotion: str = "neutral",
    ) -> dict[str, Any] | None:
        """
        Get a personalized strategy suggestion for the current context.

        Args:
            situation: The current situation or customer question.
            recent_emotion: Recent detected emotion.

        Returns:
            Strategy suggestion dict or None if not available.
        """
        if not self._personalization_engine or not self._sender_id:
            return None

        memory = self.enhanced_memory
        if not memory:
            return None

        profile = memory.get_cached_profile(self._sender_id)
        if not profile:
            return None

        comm_style = self._personalization_engine.infer_communication_style(profile)
        decision_style = self._personalization_engine.infer_decision_style(profile)

        context = PersonalizationContext(
            customer_id=self._sender_id,
            profile=profile,
            communication_style=comm_style,
            decision_style=decision_style,
        )

        try:
            suggestion = await self._personalization_engine.generate_strategy(
                context=context,
                situation=situation,
                recent_emotion=recent_emotion,
            )
            return suggestion.to_dict()
        except Exception as e:
            self.logger.warning(f"Failed to generate strategy: {e}")
            return None

    def get_last_extraction_result(self) -> ProfileExtractionResult | None:
        """Get the last profile extraction result."""
        return self._last_extraction_result

    def update_customer_profile(self, profile_updates: dict[str, Any]) -> bool:
        """
        Manually update the customer profile.

        Args:
            profile_updates: Dictionary of profile field updates.

        Returns:
            True if update was successful.
        """
        if not self._sender_id or not self._enhanced_memory:
            return False

        profile = self._enhanced_memory.get_cached_profile(self._sender_id)
        if not profile:
            return False

        try:
            if "pain_points" in profile_updates:
                for pp in profile_updates["pain_points"]:
                    profile.add_pain_point(pp)

            if "competitors" in profile_updates:
                for comp in profile_updates["competitors"]:
                    profile.add_competitor(comp)

            if bant_updates := profile_updates.get("bant"):
                profile.update_bant(**bant_updates)

            self._enhanced_memory.update_profile_cache(self._sender_id, profile)
            return True

        except Exception as e:
            self.logger.warning(f"Failed to update profile: {e}")
            return False
