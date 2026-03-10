"""Data models for sales coaching mode.

This module defines the core data structures for the coaching feature:
- CoachingMode: Enum for practice vs assist modes
- PracticeScenario: Predefined customer scenarios for training
- CoachingSession: Active coaching session state
- PerformanceScore: Evaluation metrics for salesperson performance
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CoachingMode(str, Enum):
    """Coaching operation modes.

    PRACTICE: AI acts as customer, salesperson practices responses
    ASSIST: AI provides real-time strategy suggestions for live conversations
    """

    PRACTICE = "practice"
    ASSIST = "assist"

    def __str__(self) -> str:
        return self.value


class ScenarioDifficulty(str, Enum):
    """Difficulty levels for practice scenarios."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class PracticeScenario:
    """Predefined customer scenario for sales practice.

    Each scenario represents a common customer type with specific
    characteristics, objections, and behavioral patterns.
    """

    id: str
    name: str
    description: str
    customer_persona: str  # Role/title of the customer
    industry: str
    difficulty: ScenarioDifficulty
    initial_message: str  # Opening message from customer
    personality_traits: list[str] = field(default_factory=list)
    common_objections: list[str] = field(default_factory=list)
    decision_criteria: list[str] = field(default_factory=list)
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    pain_points: list[str] = field(default_factory=list)
    competitors_considering: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize scenario to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "customer_persona": self.customer_persona,
            "industry": self.industry,
            "difficulty": self.difficulty.value,
            "initial_message": self.initial_message,
            "personality_traits": self.personality_traits,
            "common_objections": self.common_objections,
            "decision_criteria": self.decision_criteria,
            "budget_range": self.budget_range,
            "timeline": self.timeline,
            "pain_points": self.pain_points,
            "competitors_considering": self.competitors_considering,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PracticeScenario":
        """Deserialize scenario from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            customer_persona=data["customer_persona"],
            industry=data["industry"],
            difficulty=ScenarioDifficulty(data["difficulty"]),
            initial_message=data["initial_message"],
            personality_traits=data.get("personality_traits", []),
            common_objections=data.get("common_objections", []),
            decision_criteria=data.get("decision_criteria", []),
            budget_range=data.get("budget_range"),
            timeline=data.get("timeline"),
            pain_points=data.get("pain_points", []),
            competitors_considering=data.get("competitors_considering", []),
        )


@dataclass
class DialogueTurn:
    """Single turn in a coaching dialogue."""

    role: str  # "customer" or "salesperson"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)  # e.g., emotion detected, intent


@dataclass
class CoachingSession:
    """Active coaching session state.

    Tracks the full state of a practice or assist session including
    conversation history, scenario details, and performance metrics.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mode: CoachingMode = CoachingMode.PRACTICE
    scenario_id: Optional[str] = None
    scenario: Optional[PracticeScenario] = None
    salesperson_id: str = ""
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    dialogue_history: list[DialogueTurn] = field(default_factory=list)
    customer_context: dict = field(default_factory=dict)  # Evolving customer state
    performance_metrics: dict = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)
    is_active: bool = True

    def add_turn(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        """Add a dialogue turn to the session."""
        self.dialogue_history.append(
            DialogueTurn(
                role=role,
                content=content,
                metadata=metadata or {},
            )
        )

    def get_last_customer_message(self) -> Optional[str]:
        """Get the most recent customer message."""
        for turn in reversed(self.dialogue_history):
            if turn.role == "customer":
                return turn.content
        return None

    def get_last_salesperson_message(self) -> Optional[str]:
        """Get the most recent salesperson message."""
        for turn in reversed(self.dialogue_history):
            if turn.role == "salesperson":
                return turn.content
        return None

    def get_dialogue_summary(self) -> str:
        """Get a formatted summary of the dialogue."""
        lines = []
        for turn in self.dialogue_history:
            role_label = "👤 Customer" if turn.role == "customer" else "💼 Salesperson"
            lines.append(f"{role_label}: {turn.content}")
        return "\n".join(lines)

    def end_session(self) -> None:
        """Mark the session as ended."""
        self.is_active = False
        self.ended_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize session to dictionary."""
        return {
            "id": self.id,
            "mode": self.mode.value,
            "scenario_id": self.scenario_id,
            "salesperson_id": self.salesperson_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "dialogue_history": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp.isoformat(),
                    "metadata": t.metadata,
                }
                for t in self.dialogue_history
            ],
            "customer_context": self.customer_context,
            "performance_metrics": self.performance_metrics,
            "feedback": self.feedback,
            "is_active": self.is_active,
        }


@dataclass
class PerformanceScore:
    """Performance evaluation metrics for a coaching session.

    Provides detailed scoring across multiple dimensions of sales
    effectiveness with actionable feedback.
    """

    overall_score: float  # 0.0 to 1.0
    rapport_building: float = 0.0  # Building connection with customer
    needs_discovery: float = 0.0  # SPIN/questioning effectiveness
    product_knowledge: float = 0.0  # Accurate product information
    objection_handling: float = 0.0  # Handling pushback
    closing_technique: float = 0.0  # Moving towards commitment
    communication_clarity: float = 0.0  # Clear, professional communication
    active_listening: float = 0.0  # Responding to customer cues
    strengths: list[str] = field(default_factory=list)
    areas_for_improvement: list[str] = field(default_factory=list)
    specific_feedback: list[str] = field(default_factory=list)
    recommended_skills: list[str] = field(default_factory=list)
    session_id: Optional[str] = None
    evaluated_at: datetime = field(default_factory=datetime.utcnow)

    def get_grade(self) -> str:
        """Convert score to letter grade."""
        if self.overall_score >= 0.9:
            return "A+"
        elif self.overall_score >= 0.85:
            return "A"
        elif self.overall_score >= 0.8:
            return "A-"
        elif self.overall_score >= 0.75:
            return "B+"
        elif self.overall_score >= 0.7:
            return "B"
        elif self.overall_score >= 0.65:
            return "B-"
        elif self.overall_score >= 0.6:
            return "C+"
        elif self.overall_score >= 0.55:
            return "C"
        elif self.overall_score >= 0.5:
            return "C-"
        elif self.overall_score >= 0.4:
            return "D"
        else:
            return "F"

    def get_summary(self) -> str:
        """Get a formatted summary of the performance."""
        lines = [
            f"📊 Performance Score: {self.overall_score:.0%} (Grade: {self.get_grade()})",
            "",
            "📈 Dimension Scores:",
            f"  Rapport Building:      {self.rapport_building:.0%}",
            f"  Needs Discovery:       {self.needs_discovery:.0%}",
            f"  Product Knowledge:     {self.product_knowledge:.0%}",
            f"  Objection Handling:    {self.objection_handling:.0%}",
            f"  Closing Technique:     {self.closing_technique:.0%}",
            f"  Communication Clarity: {self.communication_clarity:.0%}",
            f"  Active Listening:      {self.active_listening:.0%}",
            "",
        ]

        if self.strengths:
            lines.append("✅ Strengths:")
            for strength in self.strengths:
                lines.append(f"  • {strength}")
            lines.append("")

        if self.areas_for_improvement:
            lines.append("⚠️ Areas for Improvement:")
            for area in self.areas_for_improvement:
                lines.append(f"  • {area}")
            lines.append("")

        if self.specific_feedback:
            lines.append("💡 Specific Feedback:")
            for feedback in self.specific_feedback:
                lines.append(f"  • {feedback}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize score to dictionary."""
        return {
            "overall_score": self.overall_score,
            "rapport_building": self.rapport_building,
            "needs_discovery": self.needs_discovery,
            "product_knowledge": self.product_knowledge,
            "objection_handling": self.objection_handling,
            "closing_technique": self.closing_technique,
            "communication_clarity": self.communication_clarity,
            "active_listening": self.active_listening,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement,
            "specific_feedback": self.specific_feedback,
            "recommended_skills": self.recommended_skills,
            "session_id": self.session_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "grade": self.get_grade(),
        }
