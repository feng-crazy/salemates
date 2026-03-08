# Copyright (c) 2026 SalesMate Team
# SPDX-License-Identifier: Apache-2.0

"""SalesMate Intent Recognition Module."""

from salesmate.agent.intent.recognizer import (
    IntentRecognizer,
    IntentResult,
    SalesIntent,
)
from salesmate.agent.intent.prompts import INTENT_CLASSIFICATION_PROMPT

__all__ = [
    "IntentRecognizer",
    "IntentResult",
    "SalesIntent",
    "INTENT_CLASSIFICATION_PROMPT",
]
