# Copyright (c) 2026 SaleMates Team
# SPDX-License-Identifier: Apache-2.0

"""SaleMates Intent Recognition Module."""

from salemates.agent.intent.recognizer import (
    IntentRecognizer,
    IntentResult,
    SalesIntent,
)
from salemates.agent.intent.prompts import INTENT_CLASSIFICATION_PROMPT

__all__ = [
    "IntentRecognizer",
    "IntentResult",
    "SalesIntent",
    "INTENT_CLASSIFICATION_PROMPT",
]
