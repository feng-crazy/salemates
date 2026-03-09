"""Customer profile models with BANT data for SaleMates."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class SalesStage(str, Enum):
    """Sales pipeline stages for customer progression."""

    NEW_CONTACT = "new_contact"
    DISCOVERY = "discovery"
    PRESENTATION = "presentation"
    NEGOTIATION = "negotiation"
    CLOSE = "close"
    LOST = "lost"

    def __str__(self) -> str:
        return self.value


# Valid stage transitions for sales pipeline
VALID_TRANSITIONS: dict[SalesStage, set[SalesStage]] = {
    SalesStage.NEW_CONTACT: {SalesStage.DISCOVERY, SalesStage.LOST},
    SalesStage.DISCOVERY: {SalesStage.PRESENTATION, SalesStage.LOST},
    SalesStage.PRESENTATION: {SalesStage.NEGOTIATION, SalesStage.LOST},
    SalesStage.NEGOTIATION: {SalesStage.CLOSE, SalesStage.LOST},
    SalesStage.CLOSE: set(),  # Terminal state
    SalesStage.LOST: set(),  # Terminal state
}


@dataclass
class BANTProfile:
    """
    BANT qualification data for sales opportunities.

    BANT stands for:
    - Budget: Does the prospect have budget allocated?
    - Authority: Is the contact a decision-maker?
    - Need: Does the prospect have a genuine need?
    - Timeline: What is their buying timeline?
    """

    budget: Optional[float] = None  # Allocated budget in USD
    budget_confirmed: bool = False  # Whether budget is verified
    authority: Optional[str] = None  # Decision maker name/role
    authority_level: Optional[str] = None  # e.g., "C-level", "Manager", "Individual Contributor"
    need: Optional[str] = None  # Primary business need
    need_urgency: Optional[str] = None  # e.g., "Critical", "High", "Medium", "Low"
    timeline: Optional[str] = None  # Expected purchase timeline
    timeline_confirmed: bool = False

    def is_qualified(self) -> bool:
        """Check if BANT criteria are sufficiently met for progression."""
        return all(
            [
                self.budget is not None and self.budget > 0,
                self.authority is not None,
                self.need is not None,
                self.timeline is not None,
            ]
        )

    def qualification_score(self) -> float:
        """
        Calculate BANT qualification score (0.0 to 1.0).
        Higher score indicates better qualified lead.
        """
        score = 0.0
        max_score = 4.0

        if self.budget is not None and self.budget > 0:
            score += 1.0
            if self.budget_confirmed:
                score += 0.25

        if self.authority is not None:
            score += 1.0
            if self.authority_level in ("C-level", "VP", "Director"):
                score += 0.25

        if self.need is not None:
            score += 1.0
            if self.need_urgency in ("Critical", "High"):
                score += 0.25

        if self.timeline is not None:
            score += 1.0
            if self.timeline_confirmed:
                score += 0.25

        return min(score / max_score, 1.0)


@dataclass
class CustomerProfile:
    """
    Complete customer profile for sales tracking.

    Includes BANT qualification data, sales stage, pain points,
    competitors, and metadata.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    email: str = ""
    company: str = ""
    stage: SalesStage = SalesStage.NEW_CONTACT
    bant: BANTProfile = field(default_factory=BANTProfile)
    pain_points: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_transition_to(self, new_stage: SalesStage) -> bool:
        """Check if transition to new stage is valid."""
        return new_stage in VALID_TRANSITIONS.get(self.stage, set())

    def transition_to(self, new_stage: SalesStage) -> bool:
        """
        Attempt to transition to a new sales stage.

        Returns True if transition was successful, False otherwise.
        """
        if not self.can_transition_to(new_stage):
            return False

        self.stage = new_stage
        self.updated_at = datetime.utcnow()
        return True

    def validate_stage_transition(self, new_stage: SalesStage) -> tuple[bool, str]:
        """
        Validate a potential stage transition with detailed error message.

        Returns (is_valid, error_message).
        """
        if new_stage == self.stage:
            return True, "Already in this stage"

        if not self.can_transition_to(new_stage):
            valid_stages = ", ".join(s.value for s in VALID_TRANSITIONS.get(self.stage, set()))
            if not valid_stages:
                return False, f"Cannot transition from {self.stage.value} (terminal stage)"
            return (
                False,
                f"Cannot transition from {self.stage.value} to {new_stage.value}. Valid transitions: {valid_stages}",
            )

        return True, "Transition valid"

    def update_bant(
        self,
        budget: Optional[float] = None,
        budget_confirmed: Optional[bool] = None,
        authority: Optional[str] = None,
        authority_level: Optional[str] = None,
        need: Optional[str] = None,
        need_urgency: Optional[str] = None,
        timeline: Optional[str] = None,
        timeline_confirmed: Optional[bool] = None,
    ) -> None:
        """Update BANT profile fields."""
        if budget is not None:
            self.bant.budget = budget
        if budget_confirmed is not None:
            self.bant.budget_confirmed = budget_confirmed
        if authority is not None:
            self.bant.authority = authority
        if authority_level is not None:
            self.bant.authority_level = authority_level
        if need is not None:
            self.bant.need = need
        if need_urgency is not None:
            self.bant.need_urgency = need_urgency
        if timeline is not None:
            self.bant.timeline = timeline
        if timeline_confirmed is not None:
            self.bant.timeline_confirmed = timeline_confirmed

        self.updated_at = datetime.utcnow()

    def add_pain_point(self, pain_point: str) -> None:
        """Add a pain point to the customer profile."""
        if pain_point and pain_point not in self.pain_points:
            self.pain_points.append(pain_point)
            self.updated_at = datetime.utcnow()

    def add_competitor(self, competitor: str) -> None:
        """Add a competitor to the customer profile."""
        if competitor and competitor not in self.competitors:
            self.competitors.append(competitor)
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serialize customer profile to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "company": self.company,
            "stage": self.stage.value,
            "bant": {
                "budget": self.bant.budget,
                "budget_confirmed": self.bant.budget_confirmed,
                "authority": self.bant.authority,
                "authority_level": self.bant.authority_level,
                "need": self.bant.need,
                "need_urgency": self.bant.need_urgency,
                "timeline": self.bant.timeline,
                "timeline_confirmed": self.bant.timeline_confirmed,
            },
            "pain_points": self.pain_points,
            "competitors": self.competitors,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CustomerProfile":
        """Deserialize customer profile from dictionary."""
        bant_data = data.get("bant", {})
        bant = BANTProfile(
            budget=bant_data.get("budget"),
            budget_confirmed=bant_data.get("budget_confirmed", False),
            authority=bant_data.get("authority"),
            authority_level=bant_data.get("authority_level"),
            need=bant_data.get("need"),
            need_urgency=bant_data.get("need_urgency"),
            timeline=bant_data.get("timeline"),
            timeline_confirmed=bant_data.get("timeline_confirmed", False),
        )

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            email=data.get("email", ""),
            company=data.get("company", ""),
            stage=SalesStage(data.get("stage", "new_contact")),
            bant=bant,
            pain_points=data.get("pain_points", []),
            competitors=data.get("competitors", []),
            notes=data.get("notes", ""),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.utcnow(),
        )
