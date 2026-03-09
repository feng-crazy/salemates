# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""Follow-up message templates for sales automation.

Templates are personalized based on:
- Sales stage (NEW_CONTACT, DISCOVERY, PRESENTATION, NEGOTIATION)
- Customer profile (name, company, pain points, needs)
- Last conversation context
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from salemates.agent.models.customer import CustomerProfile, SalesStage


@dataclass
class FollowUpContext:
    """Context for generating personalized follow-up messages."""

    customer: CustomerProfile
    last_contact_at: Optional[datetime] = None
    last_topic: Optional[str] = None
    last_pain_point_discussed: Optional[str] = None
    days_since_contact: int = 0
    previous_followup_count: int = 0
    custom_notes: str = ""


@dataclass
class FollowUpTemplate:
    """A follow-up message template with personalization placeholders."""

    stage: SalesStage
    priority: int  # Higher = more important
    template: str
    value_offering: str  # What we offer (case study, article, demo, etc.)
    tone: str = "professional"  # professional, friendly, urgent

    def render(self, context: FollowUpContext) -> str:
        """Render the template with customer context."""
        customer = context.customer

        # Build personalization context
        name = customer.name or "there"
        company = customer.company or "your company"
        pain_points = customer.pain_points
        need = customer.bant.need or "your needs"
        timeline = customer.bant.timeline or "your timeline"

        # Get last topic if available
        last_topic = context.last_topic or "our previous conversation"
        last_pain = context.last_pain_point_discussed
        if not last_pain and pain_points:
            last_pain = pain_points[0]

        # Replace placeholders
        message = self.template
        message = message.replace("{name}", name)
        message = message.replace("{company}", company)
        message = message.replace("{need}", need)
        message = message.replace("{timeline}", timeline)
        message = message.replace("{last_topic}", last_topic)
        message = message.replace("{last_pain}", last_pain or "your challenges")

        # Add value offering
        message = message.replace("{value_offering}", self.value_offering)

        return message


# Default follow-up templates by stage
DEFAULT_TEMPLATES: dict[SalesStage, list[FollowUpTemplate]] = {
    SalesStage.NEW_CONTACT: [
        FollowUpTemplate(
            stage=SalesStage.NEW_CONTACT,
            priority=5,
            template=(
                "Hi {name}, just wanted to follow up on our initial conversation. "
                "Have you had a chance to think about {last_topic}? "
                "I'd love to learn more about your situation at {company}."
            ),
            value_offering="a quick discovery call",
            tone="friendly",
        ),
        FollowUpTemplate(
            stage=SalesStage.NEW_CONTACT,
            priority=3,
            template=(
                "Hi {name}, I haven't heard from you in a while. "
                "I wanted to share {value_offering} that might be relevant to {need}. "
                "Let me know if you'd like to discuss."
            ),
            value_offering="an industry insights report",
            tone="professional",
        ),
    ],
    SalesStage.DISCOVERY: [
        FollowUpTemplate(
            stage=SalesStage.DISCOVERY,
            priority=7,
            template=(
                "Hi {name}, following up on our discussion about {last_pain}. "
                "I've been thinking about how we might help address this at {company}. "
                "Would you be open to {value_offering}?"
            ),
            value_offering="a brief product demo tailored to your needs",
            tone="professional",
        ),
        FollowUpTemplate(
            stage=SalesStage.DISCOVERY,
            priority=5,
            template=(
                "Hi {name}, I wanted to circle back on {last_topic}. "
                "Based on what you shared about {need}, "
                "I think {value_offering} could be really valuable for {company}."
            ),
            value_offering="our solution",
            tone="friendly",
        ),
    ],
    SalesStage.PRESENTATION: [
        FollowUpTemplate(
            stage=SalesStage.PRESENTATION,
            priority=9,
            template=(
                "Hi {name}, I wanted to follow up on the presentation we shared. "
                "Have you had a chance to review how we can help with {last_pain}? "
                "I'd be happy to {value_offering} if you have any questions."
            ),
            value_offering="schedule a Q&A session",
            tone="professional",
        ),
        FollowUpTemplate(
            stage=SalesStage.PRESENTATION,
            priority=8,
            template=(
                "Hi {name}, just checking in on the proposal for {company}. "
                "I understand {last_topic} might require some internal discussion. "
                "Would {value_offering} be helpful?"
            ),
            value_offering="a case study from a similar company",
            tone="professional",
        ),
        FollowUpTemplate(
            stage=SalesStage.PRESENTATION,
            priority=7,
            template=(
                "Hi {name}, I thought you might find this article interesting - "
                "it relates to {last_pain} we discussed. "
                "{value_offering}. Let me know your thoughts!"
            ),
            value_offering="Here's the link: [relevant article URL]",
            tone="friendly",
        ),
    ],
    SalesStage.NEGOTIATION: [
        FollowUpTemplate(
            stage=SalesStage.NEGOTIATION,
            priority=10,
            template=(
                "Hi {name}, I wanted to follow up on our pricing discussion. "
                "I understand {last_topic} is an important consideration for {company}. "
                "I've been exploring some options and might have {value_offering}."
            ),
            value_offering="flexible payment terms",
            tone="professional",
        ),
        FollowUpTemplate(
            stage=SalesStage.NEGOTIATION,
            priority=9,
            template=(
                "Hi {name}, checking in on the decision process. "
                "I know {last_pain} is a priority for you. "
                "Is there anything else I can provide to help move things forward? "
                "I can offer {value_offering}."
            ),
            value_offering="a pilot program with reduced commitment",
            tone="professional",
        ),
    ],
    SalesStage.CLOSE: [
        # Terminal state - typically no follow-ups needed
    ],
    SalesStage.LOST: [
        # Terminal state - re-engagement campaigns handled separately
    ],
}


class FollowUpTemplateManager:
    """Manages follow-up templates and selects the best one for a given context."""

    def __init__(
        self,
        templates: dict[SalesStage, list[FollowUpTemplate]] | None = None,
        max_followup_count: int = 3,
    ):
        """Initialize template manager.

        Args:
            templates: Custom templates by stage. Defaults to DEFAULT_TEMPLATES.
            max_followup_count: Maximum follow-ups before escalating.
        """
        self.templates = templates or DEFAULT_TEMPLATES
        self.max_followup_count = max_followup_count

    def get_template(
        self,
        context: FollowUpContext,
        prefer_high_priority: bool = True,
    ) -> Optional[FollowUpTemplate]:
        """Select the best template for the given context.

        Args:
            context: Follow-up context with customer info.
            prefer_high_priority: If True, prefer higher priority templates.

        Returns:
            Best matching template, or None if no templates available.
        """
        stage = context.customer.stage
        stage_templates = self.templates.get(stage, [])

        if not stage_templates:
            return None

        # Check if we've exceeded max follow-ups
        if context.previous_followup_count >= self.max_followup_count:
            return None

        # Sort by priority
        sorted_templates = sorted(
            stage_templates,
            key=lambda t: t.priority,
            reverse=prefer_high_priority,
        )

        # Select based on follow-up count (rotate through templates)
        index = min(context.previous_followup_count, len(sorted_templates) - 1)
        return sorted_templates[index]

    def render_message(self, context: FollowUpContext) -> Optional[str]:
        """Render a personalized follow-up message.

        Args:
            context: Follow-up context with customer info.

        Returns:
            Personalized message, or None if no template available.
        """
        template = self.get_template(context)
        if template:
            return template.render(context)
        return None

    def get_value_offering(self, stage: SalesStage) -> list[str]:
        """Get list of value offerings for a stage.

        Args:
            stage: Sales stage.

        Returns:
            List of possible value offerings.
        """
        stage_templates = self.templates.get(stage, [])
        return list({t.value_offering for t in stage_templates})

    def add_template(self, template: FollowUpTemplate) -> None:
        """Add a new template for a stage.

        Args:
            template: Template to add.
        """
        if template.stage not in self.templates:
            self.templates[template.stage] = []
        self.templates[template.stage].append(template)


def create_followup_message(
    customer: CustomerProfile,
    last_contact_at: Optional[datetime] = None,
    last_topic: Optional[str] = None,
    last_pain_point: Optional[str] = None,
    days_since_contact: int = 0,
    previous_followup_count: int = 0,
) -> Optional[str]:
    """Convenience function to create a follow-up message.

    Args:
        customer: Customer profile.
        last_contact_at: When we last contacted the customer.
        last_topic: Topic of last conversation.
        last_pain_point: Last pain point discussed.
        days_since_contact: Days since last contact.
        previous_followup_count: Number of previous follow-ups.

    Returns:
        Personalized follow-up message, or None if no template available.
    """
    context = FollowUpContext(
        customer=customer,
        last_contact_at=last_contact_at,
        last_topic=last_topic,
        last_pain_point_discussed=last_pain_point,
        days_since_contact=days_since_contact,
        previous_followup_count=previous_followup_count,
    )

    manager = FollowUpTemplateManager()
    return manager.render_message(context)
