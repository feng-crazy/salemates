# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Sales intent recognition system.

Detects customer intents during sales conversations to enable
appropriate response strategies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
import json

from loguru import logger

from salesmate.providers.base import LLMProvider
from salesmate.agent.intent.prompts import INTENT_CLASSIFICATION_PROMPT


class SalesIntent(str, Enum):
    """Sales-specific customer intents.

    Each intent type triggers specific response strategies:
    - OBJECTION_PRICE: Price concerns → Value justification
    - OBJECTION_FEATURE: Feature gaps → Alternative solutions
    - OBJECTION_COMPETITOR: Competitor mentions → Competitive positioning
    - HESITATION: Buying uncertainty → SPIN questioning
    - BUY_SIGNAL: Purchase readiness → Close techniques
    - BANT_QUALIFICATION: Qualification questions → Profile building
    - PRODUCT_INQUIRY: Product questions → Information provision
    - SCHEDULING_REQUEST: Meeting request → Calendar booking
    """

    OBJECTION_PRICE = "OBJECTION_PRICE"
    OBJECTION_FEATURE = "OBJECTION_FEATURE"
    OBJECTION_COMPETITOR = "OBJECTION_COMPETITOR"
    HESITATION = "HESITATION"
    BUY_SIGNAL = "BUY_SIGNAL"
    BANT_QUALIFICATION = "BANT_QUALIFICATION"
    PRODUCT_INQUIRY = "PRODUCT_INQUIRY"
    SCHEDULING_REQUEST = "SCHEDULING_REQUEST"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value

    @property
    def is_objection(self) -> bool:
        """Check if this is an objection intent."""
        return self in (
            SalesIntent.OBJECTION_PRICE,
            SalesIntent.OBJECTION_FEATURE,
            SalesIntent.OBJECTION_COMPETITOR,
        )


@dataclass
class IntentResult:
    """Result of intent classification.

    Attributes:
        intent: The detected primary intent.
        confidence: Classification confidence (0.0-1.0).
        reasoning: Explanation of why this intent was detected.
        signals: List of signals detected in the message.
    """

    intent: SalesIntent
    confidence: float
    reasoning: str
    signals: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "signals": self.signals,
        }


class IntentRecognizer:
    """Recognizes customer intents from messages using LLM.

    This class provides sales-specific intent detection to enable
    appropriate response strategies for different customer needs.
    """

    def __init__(self, llm_provider: LLMProvider):
        """Initialize the intent recognizer.

        Args:
            llm_provider: LLM provider for classification.
        """
        self.llm_provider = llm_provider
        self.logger = logger.bind(component="IntentRecognizer")

    async def recognize(
        self, message: str, context: Optional[dict[str, Any]] = None
    ) -> IntentResult:
        """Classify the intent of a customer message.

        Args:
            message: Customer message to classify.
            context: Optional conversation context.

        Returns:
            IntentResult with intent, confidence, and reasoning.
        """
        try:
            # Build prompt with context
            user_content = f"{INTENT_CLASSIFICATION_PROMPT}\n\nMessage: {message}"
            if context:
                user_content += f"\n\nContext: {json.dumps(context, ensure_ascii=False)}"

            # Call LLM using chat interface
            messages = [{"role": "user", "content": user_content}]
            response = await self.llm_provider.chat(
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent classification
            )

            # Parse JSON response
            result_data = json.loads(response.content or "{}")

            # Map to enum
            intent_str = result_data.get("intent", "UNKNOWN")
            try:
                intent = SalesIntent(intent_str)
            except ValueError:
                intent = SalesIntent.UNKNOWN

            return IntentResult(
                intent=intent,
                confidence=result_data.get("confidence", 0.5),
                reasoning=result_data.get("reasoning", ""),
                signals=result_data.get("signals", []),
            )

        except Exception as e:
            self.logger.error(f"Intent recognition failed: {e}")
            return IntentResult(
                intent=SalesIntent.UNKNOWN,
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                signals=[],
            )

    def recognize_sync(
        self, message: str, context: Optional[dict[str, Any]] = None
    ) -> IntentResult:
        """Synchronous version of recognize.

        Args:
            message: Customer message to classify.
            context: Optional conversation context.

        Returns:
            IntentResult with intent, confidence, and reasoning.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.recognize(message, context))
                    return future.result()
            else:
                return loop.run_until_complete(self.recognize(message, context))
        except RuntimeError:
            return asyncio.run(self.recognize(message, context))
