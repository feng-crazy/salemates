"""Sales coaching module for practice and assist modes.

This module provides tools for sales training:
- CoachingMode: Practice vs Assist modes
- PracticeScenario: Customer scenarios for training
- CoachingSession: Active session tracking
- PerformanceEvaluator: Performance assessment
"""

from salemates.agent.coaching.evaluator import DEFAULT_SCENARIOS, PerformanceEvaluator
from salemates.agent.coaching.models import (
    CoachingMode,
    CoachingSession,
    DialogueTurn,
    PerformanceScore,
    PracticeScenario,
    ScenarioDifficulty,
)

__all__ = [
    "CoachingMode",
    "CoachingSession",
    "DialogueTurn",
    "PerformanceScore",
    "PracticeScenario",
    "ScenarioDifficulty",
    "PerformanceEvaluator",
    "DEFAULT_SCENARIOS",
]
