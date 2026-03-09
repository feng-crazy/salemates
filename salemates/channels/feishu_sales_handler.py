"""Feishu sales-specific message handler extending the base Feishu channel.

This module provides sales-specific functionality for the Feishu channel:
- Customer info extraction from Feishu user profiles
- Sales context enrichment for messages
- Routing messages through SaleMates agent loop
- Handling sales-specific interactive cards
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx
from loguru import logger

from salemates.bus.events import InboundMessage, OutboundMessage
from salemates.bus.queue import MessageBus
from salemates.channels.feishu import FeishuChannel
from salemates.channels.feishu_cards import (
    BANTFormCard,
    MeetingScheduleCard,
    ProductComparisonCard,
    QuoteCard,
)
from salemates.config.schema import FeishuChannelConfig

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        GetUserInfoRequest,
        P2ImMessageReceiveV1,
    )

    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False
    lark = None


@dataclass
class FeishuCustomerInfo:
    """Customer information extracted from Feishu user profile."""

    open_id: str
    name: str = ""
    avatar_url: str = ""
    department_id: str = ""
    department_name: str = ""
    email: str = ""
    mobile: str = ""
    tenant_key: str = ""
    # Sales-specific fields
    company_name: str = ""
    job_title: str = ""
    extracted_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata."""
        return {
            "open_id": self.open_id,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "email": self.email,
            "mobile": self.mobile,
            "tenant_key": self.tenant_key,
            "company_name": self.company_name,
            "job_title": self.job_title,
            "extracted_at": self.extracted_at.isoformat(),
        }


@dataclass
class SalesContext:
    """Sales context for message processing."""

    customer_info: FeishuCustomerInfo | None = None
    conversation_stage: str = "discovery"  # discovery, qualification, proposal, negotiation, close
    bant_data: dict[str, Any] = field(default_factory=dict)
    quote_data: dict[str, Any] = field(default_factory=dict)
    meeting_data: dict[str, Any] = field(default_factory=dict)
    interested_products: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    competitors_mentioned: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata."""
        return {
            "customer_info": self.customer_info.to_dict() if self.customer_info else None,
            "conversation_stage": self.conversation_stage,
            "bant_data": self.bant_data,
            "quote_data": self.quote_data,
            "meeting_data": self.meeting_data,
            "interested_products": self.interested_products,
            "pain_points": self.pain_points,
            "competitors_mentioned": self.competitors_mentioned,
        }


class FeishuSalesHandler(FeishuChannel):
    """
    Extended Feishu channel with sales-specific message handling.

    This class extends the base FeishuChannel to add:
    - Customer profile extraction from Feishu
    - Sales context tracking per conversation
    - Sales-specific card generation and handling
    - Integration with SaleMates agent loop
    """

    name = "feishu_sales"

    def __init__(self, config: FeishuChannelConfig, bus: MessageBus, **kwargs):
        super().__init__(config, bus, **kwargs)
        self.config: FeishuChannelConfig = config
        # Per-conversation sales context cache
        self._sales_contexts: dict[str, SalesContext] = {}
        # Customer info cache by open_id
        self._customer_cache: dict[str, FeishuCustomerInfo] = {}
        # Pending card callbacks (card_id -> callback)
        self._pending_cards: dict[str, dict[str, Any]] = {}

    async def _get_user_info(self, open_id: str) -> FeishuCustomerInfo | None:
        """
        Fetch user information from Feishu API.

        Args:
            open_id: The user's Feishu open_id

        Returns:
            FeishuCustomerInfo or None if failed
        """
        # Check cache first
        if open_id in self._customer_cache:
            return self._customer_cache[open_id]

        if not self._client:
            return None

        try:
            request = GetUserInfoRequest.builder().user_id(open_id).user_id_type("open_id").build()

            # Run sync call in executor
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: self._client.contact.v3.user.get(request)
            )

            if not response.success():
                logger.warning(f"Failed to get user info: code={response.code}, msg={response.msg}")
                return None

            user = response.data.user

            customer_info = FeishuCustomerInfo(
                open_id=open_id,
                name=getattr(user, "name", "") or "",
                avatar_url=getattr(user, "avatar_url", "") or "",
                department_id=getattr(user, "department_id", "") or "",
                email=getattr(user, "email", "") or "",
                mobile=getattr(user, "mobile", "") or "",
                tenant_key=getattr(user, "tenant_key", "") or "",
                job_title=getattr(user, "job_title", "") or "",
            )

            # Cache the result
            self._customer_cache[open_id] = customer_info
            return customer_info

        except Exception as e:
            logger.exception(f"Error fetching user info for {open_id}: {e}")
            return None

    async def _get_department_name(self, department_id: str) -> str:
        """Get department name by ID."""
        if not self._client or not department_id:
            return ""

        try:
            from lark_oapi.api.contact.v3 import GetDepartmentRequest

            request = (
                GetDepartmentRequest.builder()
                .department_id(department_id)
                .department_id_type("open_department_id")
                .build()
            )

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: self._client.contact.v3.department.get(request)
            )

            if response.success():
                return getattr(response.data.department, "name", "") or ""
        except Exception as e:
            logger.debug(f"Failed to get department name: {e}")

        return ""

    async def _extract_customer_info(
        self, open_id: str, message_data: "P2ImMessageReceiveV1"
    ) -> FeishuCustomerInfo | None:
        """
        Extract customer information from Feishu message context.

        Combines user profile data with message context to build
        a complete customer profile.
        """
        # Get base user info
        customer_info = await self._get_user_info(open_id)

        if customer_info and customer_info.department_id:
            # Fetch department name
            dept_name = await self._get_department_name(customer_info.department_id)
            customer_info.department_name = dept_name

            # Try to infer company name from department hierarchy
            # (top-level department often represents company)
            if not customer_info.company_name and dept_name:
                # Simple heuristic: if department name looks like a company
                company_indicators = ["公司", "集团", "corp", "inc", "ltd", "co.", "company"]
                dept_lower = dept_name.lower()
                if any(ind in dept_lower for ind in company_indicators):
                    customer_info.company_name = dept_name

        return customer_info

    def _get_or_create_sales_context(self, chat_id: str) -> SalesContext:
        """Get or create sales context for a conversation."""
        if chat_id not in self._sales_contexts:
            self._sales_contexts[chat_id] = SalesContext()
        return self._sales_contexts[chat_id]

    async def _on_message(self, data: "P2ImMessageReceiveV1") -> None:
        """
        Handle incoming message with sales-specific processing.

        Extends the base _on_message to:
        1. Extract customer info from Feishu profile
        2. Enrich message with sales context
        3. Route through sales agent loop
        """
        try:
            event = data.event
            message = event.message
            sender = event.sender

            # Check for card action (interactive card callback)
            msg_type = message.message_type
            if msg_type == "interactive":
                await self._handle_card_callback(data)
                return

            # Deduplication check (from parent class)
            message_id = message.message_id
            if message_id in self._processed_message_ids:
                return
            self._processed_message_ids[message_id] = None

            # Trim cache
            while len(self._processed_message_ids) > 1000:
                self._processed_message_ids.popitem(last=False)

            # Skip bot messages
            sender_type = sender.sender_type
            if sender_type == "bot":
                return

            sender_id = sender.sender_id.open_id if sender.sender_id else "unknown"
            chat_id = message.chat_id
            chat_type = message.chat_type

            # Extract customer info
            customer_info = await self._extract_customer_info(sender_id, data)

            # Get or create sales context
            sales_context = self._get_or_create_sales_context(chat_id)
            if customer_info:
                sales_context.customer_info = customer_info

            # Add reaction
            await self._add_reaction(message_id, "MeMeMe")

            # Parse message content
            content = ""
            media = []

            if msg_type == "text":
                try:
                    content = json.loads(message.content).get("text", "")
                except json.JSONDecodeError:
                    content = message.content or ""
            elif msg_type in ("image", "post"):
                # Delegate to parent class for image/post handling
                # We'll call parent's _on_message but capture the result
                # For now, use simplified content extraction
                content = f"[{msg_type}]"
                if msg_type == "post":
                    try:
                        msg_content = json.loads(message.content)
                        text_parts = []
                        for block in msg_content.get("content", []):
                            for element in block:
                                if element.get("tag") == "text":
                                    text_parts.append(element.get("text", ""))
                        content = " ".join(text_parts).strip() or "[post]"
                    except (json.JSONDecodeError, KeyError):
                        pass
            else:
                content = f"[{msg_type}]"

            if not content:
                return

            # Build sales-enriched metadata
            metadata = {
                "message_id": message_id,
                "chat_type": chat_type,
                "reply_to": chat_id if chat_type == "group" else sender_id,
                "msg_type": msg_type,
                "root_id": message.root_id,
                "sender_id": sender_id,
                # Sales-specific metadata
                "sales_context": sales_context.to_dict(),
                "customer_info": customer_info.to_dict() if customer_info else None,
            }

            # Forward to message bus with sales context
            logger.info(f"Feishu sales message from {sender_id}: {content[:100]}")
            await self._handle_message(
                sender_id=sender_id,
                chat_id=chat_id,
                content=content,
                media=media if media else None,
                metadata=metadata,
            )

        except Exception as e:
            logger.exception(f"Error processing Feishu sales message: {e}")

    async def _handle_card_callback(self, data: "P2ImMessageReceiveV1") -> None:
        """
        Handle interactive card callback from Feishu.

        Processes user interactions with sales cards:
        - Quote card actions
        - BANT form submissions
        - Meeting scheduling
        - Product comparisons
        """
        try:
            event = data.event
            message = event.message
            sender = event.sender

            sender_id = sender.sender_id.open_id if sender.sender_id else "unknown"
            chat_id = message.chat_id

            # Parse card action
            try:
                content = json.loads(message.content)
                action = content.get("action", {})
                action_type = action.get("tag", "")
                action_value = action.get("value", {})
            except (json.JSONDecodeError, KeyError):
                logger.warning("Failed to parse card action")
                return

            logger.info(f"Card action: {action_type} from {sender_id}")

            # Get sales context
            sales_context = self._get_or_create_sales_context(chat_id)

            # Handle different card actions
            if action_type == "button":
                action_name = action_value.get("action", "")

                if action_name == "accept_quote":
                    await self._handle_quote_accept(chat_id, action_value, sales_context)
                elif action_name == "request_revision":
                    await self._handle_quote_revision(chat_id, action_value, sales_context)
                elif action_name == "schedule_meeting":
                    await self._handle_meeting_request(chat_id, action_value, sales_context)
                elif action_name == "select_product":
                    await self._handle_product_selection(chat_id, action_value, sales_context)
                elif action_name.startswith("bant_"):
                    await self._handle_bant_action(
                        chat_id, action_name, action_value, sales_context
                    )

            elif action_type == "input":
                # Handle form input (e.g., BANT form)
                field_name = action_value.get("field", "")
                field_value = action_value.get("value", "")
                await self._handle_form_input(chat_id, field_name, field_value, sales_context)

            elif action_type == "select_static":
                # Handle dropdown selection
                selected = action_value.get("selected_option", {})
                await self._handle_select_option(chat_id, selected, sales_context)

        except Exception as e:
            logger.exception(f"Error handling card callback: {e}")

    async def _handle_quote_accept(
        self, chat_id: str, action_value: dict, context: SalesContext
    ) -> None:
        """Handle quote acceptance."""
        quote_id = action_value.get("quote_id", "")
        logger.info(f"Quote {quote_id} accepted in chat {chat_id}")

        # Update sales context
        if "accepted_quotes" not in context.quote_data:
            context.quote_data["accepted_quotes"] = []
        context.quote_data["accepted_quotes"].append(quote_id)
        context.conversation_stage = "negotiation"

        # Send confirmation
        await self._send_text_message(
            chat_id, f"感谢确认报价！我们的销售代表将尽快与您联系以推进下一步流程。"
        )

    async def _handle_quote_revision(
        self, chat_id: str, action_value: dict, context: SalesContext
    ) -> None:
        """Handle quote revision request."""
        quote_id = action_value.get("quote_id", "")
        revision_notes = action_value.get("notes", "")

        logger.info(f"Quote {quote_id} revision requested: {revision_notes}")

        # Store revision request
        context.quote_data["revision_requested"] = True
        context.quote_data["revision_notes"] = revision_notes

        await self._send_text_message(
            chat_id, "已收到您的修改请求，我们将重新评估并提供更新后的报价。"
        )

    async def _handle_meeting_request(
        self, chat_id: str, action_value: dict, context: SalesContext
    ) -> None:
        """Handle meeting scheduling request."""
        preferred_time = action_value.get("preferred_time", "")

        context.meeting_data["requested"] = True
        context.meeting_data["preferred_time"] = preferred_time

        logger.info(f"Meeting requested for chat {chat_id}: {preferred_time}")

        # Send meeting card for user to pick time slots
        card = MeetingScheduleCard(
            title="选择会议时间",
            description="请选择您方便的时间段，我们的销售代表将与您确认。",
        )
        await self._send_card_message(chat_id, card)

    async def _handle_product_selection(
        self, chat_id: str, action_value: dict, context: SalesContext
    ) -> None:
        """Handle product selection."""
        product_id = action_value.get("product_id", "")
        product_name = action_value.get("product_name", "")

        if product_name not in context.interested_products:
            context.interested_products.append(product_name)

        logger.info(f"Product selected: {product_name} ({product_id})")

        await self._send_text_message(
            chat_id, f"您选择了「{product_name}」，请问您希望了解更多详情还是获取报价？"
        )

    async def _handle_bant_action(
        self, chat_id: str, action_name: str, action_value: dict, context: SalesContext
    ) -> None:
        """Handle BANT qualification actions."""
        # Extract BANT component from action name (e.g., "bant_budget" -> "budget")
        component = action_name.replace("bant_", "")
        value = action_value.get("value", "")

        context.bant_data[component] = value

        logger.info(f"BANT update: {component} = {value}")

        # Check if BANT is complete
        required = ["budget", "authority", "need", "timeline"]
        if all(k in context.bant_data for k in required):
            context.conversation_stage = "qualification"
            await self._send_text_message(
                chat_id, "感谢您提供的信息！基于您的需求，我为您推荐以下方案..."
            )

    async def _handle_form_input(
        self, chat_id: str, field_name: str, field_value: str, context: SalesContext
    ) -> None:
        """Handle form input from interactive cards."""
        if field_name.startswith("bant_"):
            component = field_name.replace("bant_", "")
            context.bant_data[component] = field_value
        elif field_name.startswith("quote_"):
            context.quote_data[field_name] = field_value
        elif field_name.startswith("meeting_"):
            context.meeting_data[field_name] = field_value

        logger.debug(f"Form input: {field_name} = {field_value}")

    async def _handle_select_option(
        self, chat_id: str, selected: dict, context: SalesContext
    ) -> None:
        """Handle dropdown selection."""
        option_value = selected.get("value", "")
        logger.info(f"Option selected: {option_value}")

    async def _send_text_message(self, chat_id: str, text: str) -> None:
        """Send a simple text message."""
        if not self._client:
            return

        try:
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            content = json.dumps({"text": text}, ensure_ascii=False)

            request = (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(content)
                    .build()
                )
                .build()
            )

            response = self._client.im.v1.message.create(request)
            if not response.success():
                logger.warning(f"Failed to send message: {response.msg}")

        except Exception as e:
            logger.exception(f"Error sending text message: {e}")

    async def _send_card_message(self, chat_id: str, card) -> None:
        """Send an interactive card message."""
        if not self._client:
            return

        try:
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

            card_content = card.to_json()

            request = (
                CreateMessageRequest.builder()
                .receive_id_type("chat_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("interactive")
                    .content(json.dumps(card_content, ensure_ascii=False))
                    .build()
                )
                .build()
            )

            response = self._client.im.v1.message.create(request)
            if not response.success():
                logger.warning(f"Failed to send card: {response.msg}")

        except Exception as e:
            logger.exception(f"Error sending card message: {e}")

    # ============== Sales Card Generation Methods ==============

    async def send_quote_card(
        self,
        chat_id: str,
        quote_id: str,
        products: list[dict],
        total_price: float,
        discount: float = 0,
        valid_until: str | None = None,
        terms: str | None = None,
    ) -> None:
        """
        Send a quote presentation card.

        Args:
            chat_id: Target chat ID
            quote_id: Unique quote identifier
            products: List of product dicts with name, quantity, unit_price
            total_price: Total price before discount
            discount: Discount percentage (0-100)
            valid_until: Quote validity date string
            terms: Additional terms and conditions
        """
        card = QuoteCard(
            quote_id=quote_id,
            products=products,
            total_price=total_price,
            discount=discount,
            valid_until=valid_until,
            terms=terms,
        )
        await self._send_card_message(chat_id, card)

    async def send_bant_form(self, chat_id: str) -> None:
        """
        Send a BANT qualification form card.

        BANT: Budget, Authority, Need, Timeline
        """
        card = BANTFormCard()
        await self._send_card_message(chat_id, card)

    async def send_meeting_card(
        self, chat_id: str, title: str = "预约会议", description: str = ""
    ) -> None:
        """
        Send a meeting scheduling card.
        """
        card = MeetingScheduleCard(title=title, description=description)
        await self._send_card_message(chat_id, card)

    async def send_product_comparison(
        self,
        chat_id: str,
        products: list[dict],
        features: list[str],
        title: str = "产品对比",
    ) -> None:
        """
        Send a product comparison card.

        Args:
            chat_id: Target chat ID
            products: List of product dicts with name, and feature values
            features: List of feature names to compare
            title: Card title
        """
        card = ProductComparisonCard(
            title=title,
            products=products,
            features=features,
        )
        await self._send_card_message(chat_id, card)

    # ============== Sales Agent Integration ==============

    def get_sales_context(self, chat_id: str) -> SalesContext | None:
        """Get sales context for a conversation (for agent use)."""
        return self._sales_contexts.get(chat_id)

    def update_conversation_stage(self, chat_id: str, stage: str) -> None:
        """Update the conversation stage for a chat."""
        context = self._get_or_create_sales_context(chat_id)
        context.conversation_stage = stage
        logger.info(f"Conversation stage updated: {chat_id} -> {stage}")

    def add_interested_product(self, chat_id: str, product: str) -> None:
        """Add an interested product to the sales context."""
        context = self._get_or_create_sales_context(chat_id)
        if product not in context.interested_products:
            context.interested_products.append(product)

    def add_pain_point(self, chat_id: str, pain_point: str) -> None:
        """Add a pain point to the sales context."""
        context = self._get_or_create_sales_context(chat_id)
        if pain_point not in context.pain_points:
            context.pain_points.append(pain_point)

    def add_competitor(self, chat_id: str, competitor: str) -> None:
        """Add a mentioned competitor to the sales context."""
        context = self._get_or_create_sales_context(chat_id)
        if competitor not in context.competitors_mentioned:
            context.competitors_mentioned.append(competitor)
