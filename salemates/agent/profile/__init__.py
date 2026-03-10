# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Profile extraction and personalization for intelligent customer understanding."""

from salemates.agent.profile.extractor import (
    CustomerProfileExtractor,
    ExtractedField,
    ExtractedFieldType,
    ProfileExtractionResult,
)
from salemates.agent.profile.personalization import (
    CommunicationStyle,
    DecisionStyle,
    PersonalizationContext,
    PersonalizationEngine,
    StrategySuggestion,
)
from salemates.agent.profile.memory_manager import (
    CustomerMemoryContext,
    EnhancedMemoryManager,
)
from salemates.agent.profile.context_builder import SalesContextBuilder

__all__ = [
    "CustomerProfileExtractor",
    "ExtractedField",
    "ExtractedFieldType",
    "ProfileExtractionResult",
    "CommunicationStyle",
    "DecisionStyle",
    "PersonalizationContext",
    "PersonalizationEngine",
    "StrategySuggestion",
    "CustomerMemoryContext",
    "EnhancedMemoryManager",
    "SalesContextBuilder",
]
