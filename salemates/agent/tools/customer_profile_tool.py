"""Customer profile tool for managing customer data and BANT profiles.

This tool provides methods for:
- Retrieving customer profiles
- Updating BANT qualification data
- Advancing sales stages
- Adding pain points and competitors
"""

from typing import Any, Optional

from loguru import logger

from salemates.agent.models.customer import BANTProfile, CustomerProfile, SalesStage
from salemates.agent.repositories.customer_repo import CustomerRepository
from salemates.agent.tools.base import Tool, ToolContext


class CustomerProfileTool(Tool):
    """Tool for managing customer profiles in the sales process.

    Provides CRUD operations for customer profiles including:
    - get_customer: Retrieve customer by ID or email
    - update_bant: Update BANT qualification data
    - advance_stage: Move customer to next sales stage
    - add_pain_point: Record customer pain points
    - add_competitor: Track competitors mentioned by customer

    Attributes:
        _repository: CustomerRepository instance for data persistence.
    """

    def __init__(self, repository: Optional[CustomerRepository] = None):
        """Initialize the customer profile tool.

        Args:
            repository: Optional CustomerRepository instance. If not provided,
                operations will return an error message.
        """
        self._repository = repository

    def set_repository(self, repository: CustomerRepository) -> None:
        """Set the customer repository.

        Args:
            repository: CustomerRepository instance for data persistence.
        """
        self._repository = repository

    @property
    def name(self) -> str:
        return "customer_profile"

    @property
    def description(self) -> str:
        return (
            "Manage customer profiles including BANT data, sales stage, "
            "pain points, and competitor information. Actions: get_customer, "
            "update_bant, advance_stage, add_pain_point, add_competitor."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": [
                        "get_customer",
                        "update_bant",
                        "advance_stage",
                        "add_pain_point",
                        "add_competitor",
                    ],
                },
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID (UUID format)",
                },
                "email": {
                    "type": "string",
                    "description": "Customer email address (alternative to customer_id)",
                },
                "bant_data": {
                    "type": "object",
                    "description": "BANT qualification data to update",
                    "properties": {
                        "budget": {"type": "number", "description": "Budget amount"},
                        "budget_confirmed": {"type": "boolean"},
                        "authority": {"type": "string", "description": "Decision maker"},
                        "authority_level": {
                            "type": "string",
                            "enum": [
                                "C-level",
                                "VP",
                                "Director",
                                "Manager",
                                "Individual Contributor",
                            ],
                        },
                        "need": {"type": "string", "description": "Primary business need"},
                        "need_urgency": {
                            "type": "string",
                            "enum": ["Critical", "High", "Medium", "Low"],
                        },
                        "timeline": {"type": "string", "description": "Purchase timeline"},
                        "timeline_confirmed": {"type": "boolean"},
                    },
                },
                "target_stage": {
                    "type": "string",
                    "description": "Target sales stage for advance_stage action",
                    "enum": [s.value for s in SalesStage],
                },
                "pain_point": {
                    "type": "string",
                    "description": "Pain point to add",
                },
                "competitor": {
                    "type": "string",
                    "description": "Competitor name to add",
                },
            },
            "required": ["action"],
        }

    async def execute(self, tool_context: ToolContext, **kwargs: Any) -> str:
        """Execute the customer profile tool.

        Args:
            tool_context: Runtime context with session info.
            **kwargs: Tool parameters including action and related data.

        Returns:
            String result of the operation.
        """
        if not self._repository:
            return "Error: Customer repository not configured"

        action = kwargs.get("action")
        customer_id = kwargs.get("customer_id")
        email = kwargs.get("email")

        try:
            if action == "get_customer":
                return await self._get_customer(customer_id, email)
            elif action == "update_bant":
                bant_data = kwargs.get("bant_data", {})
                return await self._update_bant(customer_id, email, bant_data)
            elif action == "advance_stage":
                target_stage = kwargs.get("target_stage")
                return await self._advance_stage(customer_id, email, target_stage)
            elif action == "add_pain_point":
                pain_point = kwargs.get("pain_point")
                return await self._add_pain_point(customer_id, email, pain_point)
            elif action == "add_competitor":
                competitor = kwargs.get("competitor")
                return await self._add_competitor(customer_id, email, competitor)
            else:
                return f"Error: Unknown action: {action}"
        except Exception as e:
            logger.exception(f"Customer profile tool error: {e}")
            return f"Error executing {action}: {str(e)}"

    async def _get_customer(self, customer_id: Optional[str], email: Optional[str]) -> str:
        """Retrieve a customer profile.

        Args:
            customer_id: Customer UUID.
            email: Customer email (alternative lookup).

        Returns:
            Formatted customer profile string.
        """
        customer = None

        if customer_id:
            customer = await self._repository.get(customer_id)
        elif email:
            customer = await self._repository.search_by_email(email)
        else:
            return "Error: Either customer_id or email is required"

        if not customer:
            return "Customer not found"

        return self._format_customer(customer)

    async def _update_bant(
        self,
        customer_id: Optional[str],
        email: Optional[str],
        bant_data: dict[str, Any],
    ) -> str:
        """Update BANT qualification data for a customer.

        Args:
            customer_id: Customer UUID.
            email: Customer email (alternative lookup).
            bant_data: BANT fields to update.

        Returns:
            Result message with updated qualification score.
        """
        customer = await self._find_customer(customer_id, email)
        if not customer:
            return "Customer not found"

        # Update BANT fields
        customer.update_bant(
            budget=bant_data.get("budget"),
            budget_confirmed=bant_data.get("budget_confirmed"),
            authority=bant_data.get("authority"),
            authority_level=bant_data.get("authority_level"),
            need=bant_data.get("need"),
            need_urgency=bant_data.get("need_urgency"),
            timeline=bant_data.get("timeline"),
            timeline_confirmed=bant_data.get("timeline_confirmed"),
        )

        await self._repository.update(customer)

        score = customer.bant.qualification_score()
        qualified = "✅ Qualified" if customer.bant.is_qualified() else "⚠️ Not yet qualified"

        return (
            f"BANT updated for {customer.name}:\n"
            f"  Budget: {customer.bant.budget or 'Unknown'}\n"
            f"  Authority: {customer.bant.authority or 'Unknown'} ({customer.bant.authority_level or 'Unknown level'})\n"
            f"  Need: {customer.bant.need or 'Unknown'} (Urgency: {customer.bant.need_urgency or 'Unknown'})\n"
            f"  Timeline: {customer.bant.timeline or 'Unknown'}\n"
            f"  Qualification Score: {score:.0%}\n"
            f"  Status: {qualified}"
        )

    async def _advance_stage(
        self,
        customer_id: Optional[str],
        email: Optional[str],
        target_stage: Optional[str],
    ) -> str:
        """Advance customer to a new sales stage.

        Args:
            customer_id: Customer UUID.
            email: Customer email (alternative lookup).
            target_stage: Target sales stage.

        Returns:
            Result message with stage transition info.
        """
        if not target_stage:
            return "Error: target_stage is required"

        customer = await self._find_customer(customer_id, email)
        if not customer:
            return "Customer not found"

        try:
            new_stage = SalesStage(target_stage)
        except ValueError:
            return f"Error: Invalid stage '{target_stage}'"

        is_valid, error_msg = customer.validate_stage_transition(new_stage)

        if not is_valid:
            return f"Cannot advance stage: {error_msg}"

        old_stage = customer.stage
        customer.transition_to(new_stage)
        await self._repository.update(customer)

        return (
            f"Stage advanced for {customer.name}:\n"
            f"  {old_stage.value} → {new_stage.value}\n"
            f"  Next possible stages: {', '.join(s.value for s in self._get_valid_transitions(new_stage)) or 'Terminal stage'}"
        )

    async def _add_pain_point(
        self,
        customer_id: Optional[str],
        email: Optional[str],
        pain_point: Optional[str],
    ) -> str:
        """Add a pain point to customer profile.

        Args:
            customer_id: Customer UUID.
            email: Customer email (alternative lookup).
            pain_point: Pain point description.

        Returns:
            Result message with updated pain points list.
        """
        if not pain_point:
            return "Error: pain_point is required"

        customer = await self._find_customer(customer_id, email)
        if not customer:
            return "Customer not found"

        customer.add_pain_point(pain_point)
        await self._repository.update(customer)

        return (
            f"Pain point added for {customer.name}:\n"
            f'  "{pain_point}"\n'
            f"  Total pain points: {len(customer.pain_points)}"
        )

    async def _add_competitor(
        self,
        customer_id: Optional[str],
        email: Optional[str],
        competitor: Optional[str],
    ) -> str:
        """Add a competitor to customer profile.

        Args:
            customer_id: Customer UUID.
            email: Customer email (alternative lookup).
            competitor: Competitor name.

        Returns:
            Result message with updated competitors list.
        """
        if not competitor:
            return "Error: competitor is required"

        customer = await self._find_customer(customer_id, email)
        if not customer:
            return "Customer not found"

        customer.add_competitor(competitor)
        await self._repository.update(customer)

        return (
            f"Competitor tracked for {customer.name}:\n"
            f'  "{competitor}"\n'
            f"  Total competitors: {len(customer.competitors)}"
        )

    async def _find_customer(
        self, customer_id: Optional[str], email: Optional[str]
    ) -> Optional[CustomerProfile]:
        """Find a customer by ID or email.

        Args:
            customer_id: Customer UUID.
            email: Customer email.

        Returns:
            CustomerProfile if found, None otherwise.
        """
        if customer_id:
            return await self._repository.get(customer_id)
        elif email:
            return await self._repository.search_by_email(email)
        return None

    def _format_customer(self, customer: CustomerProfile) -> str:
        """Format customer profile for display.

        Args:
            customer: Customer profile to format.

        Returns:
            Formatted string representation.
        """
        lines = [
            f"📋 Customer Profile: {customer.name}",
            f"  ID: {customer.id}",
            f"  Email: {customer.email}",
            f"  Company: {customer.company or 'Unknown'}",
            f"  Stage: {customer.stage.value}",
            "",
            "  BANT Qualification:",
            f"    Budget: {customer.bant.budget or 'Unknown'} {'(confirmed)' if customer.bant.budget_confirmed else ''}",
            f"    Authority: {customer.bant.authority or 'Unknown'} ({customer.bant.authority_level or 'Unknown level'})",
            f"    Need: {customer.bant.need or 'Unknown'} (Urgency: {customer.bant.need_urgency or 'Unknown'})",
            f"    Timeline: {customer.bant.timeline or 'Unknown'} {'(confirmed)' if customer.bant.timeline_confirmed else ''}",
            f"    Score: {customer.bant.qualification_score():.0%}",
            "",
            f"  Pain Points: {len(customer.pain_points)}",
        ]

        for pp in customer.pain_points[:3]:
            lines.append(f"    • {pp}")
        if len(customer.pain_points) > 3:
            lines.append(f"    ... and {len(customer.pain_points) - 3} more")

        lines.append(f"  Competitors: {', '.join(customer.competitors) or 'None tracked'}")

        return "\n".join(lines)

    def _get_valid_transitions(self, stage: SalesStage) -> list[SalesStage]:
        """Get valid transitions from a stage.

        Args:
            stage: Current sales stage.

        Returns:
            List of valid next stages.
        """
        VALID_TRANSITIONS: dict[SalesStage, list[SalesStage]] = {
            SalesStage.NEW_CONTACT: [SalesStage.DISCOVERY, SalesStage.LOST],
            SalesStage.DISCOVERY: [SalesStage.PRESENTATION, SalesStage.LOST],
            SalesStage.PRESENTATION: [SalesStage.NEGOTIATION, SalesStage.LOST],
            SalesStage.NEGOTIATION: [SalesStage.CLOSE, SalesStage.LOST],
            SalesStage.CLOSE: [],
            SalesStage.LOST: [],
        }
        return VALID_TRANSITIONS.get(stage, [])
