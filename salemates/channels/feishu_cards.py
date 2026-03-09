"""Feishu interactive card generators for sales-specific features.

This module provides card generators for:
- Quote presentation cards
- BANT qualification forms
- Meeting scheduling cards
- Product comparison cards

Feishu card JSON schema reference:
https://open.feishu.cn/document/ukTMukTMukTM/ucTM5YjL3ETO24yNxkjN
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass
class CardAction:
    """Represents a card action button."""

    text: str
    action: str
    value: dict[str, Any] = field(default_factory=dict)
    style: str = "primary"  # primary, default, danger

    def to_dict(self) -> dict:
        """Convert to Feishu card action format."""
        return {
            "tag": "button",
            "text": {"tag": "plain_text", "content": self.text},
            "type": self.style,
            "value": {"action": self.action, **self.value},
        }


class BaseCard(ABC):
    """Base class for Feishu interactive cards."""

    @abstractmethod
    def to_json(self) -> dict:
        """Generate Feishu card JSON structure."""
        pass

    def _generate_id(self) -> str:
        """Generate a unique ID for card elements."""
        return str(uuid4())[:8]


class QuoteCard(BaseCard):
    """
    Quote presentation card for sales proposals.

    Displays product details, pricing, and action buttons
    for the customer to accept or request revision.
    """

    def __init__(
        self,
        quote_id: str,
        products: list[dict],
        total_price: float,
        discount: float = 0,
        valid_until: str | None = None,
        terms: str | None = None,
        currency: str = "¥",
    ):
        """
        Initialize quote card.

        Args:
            quote_id: Unique quote identifier
            products: List of products with name, quantity, unit_price, subtotal
            total_price: Total price before discount
            discount: Discount percentage (0-100)
            valid_until: Quote validity date string
            terms: Additional terms and conditions
            currency: Currency symbol
        """
        self.quote_id = quote_id
        self.products = products
        self.total_price = total_price
        self.discount = discount
        self.valid_until = valid_until
        self.terms = terms
        self.currency = currency

    def to_json(self) -> dict:
        """Generate Feishu card JSON."""
        # Calculate final price
        final_price = self.total_price * (1 - self.discount / 100)

        # Build product list elements
        product_elements = []
        for product in self.products:
            product_elements.append(
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**{product.get('name', '产品')}**",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"x{product.get('quantity', 1)}",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"单价: {self.currency}{product.get('unit_price', 0):,.2f}",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"小计: {self.currency}{product.get('subtotal', 0):,.2f}",
                            },
                        },
                    ],
                }
            )

        # Build main content
        elements = [
            # Header
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**报价单 #{self.quote_id}**",
                },
            },
            {"tag": "hr"},
            # Product list
            *product_elements,
            {"tag": "hr"},
            # Summary
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**小计:** {self.currency}{self.total_price:,.2f}",
                        },
                    },
                ],
            },
        ]

        # Add discount if applicable
        if self.discount > 0:
            elements.append(
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**折扣:** -{self.discount}%",
                            },
                        },
                    ],
                }
            )

        # Add final price
        elements.append(
            {
                "tag": "div",
                "fields": [
                    {
                        "is_short": True,
                        "text": {
                            "tag": "lark_md",
                            "content": f"**总计:** {self.currency}{final_price:,.2f}",
                        },
                    },
                ],
            }
        )

        # Add validity date
        if self.valid_until:
            elements.append(
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"有效期至: {self.valid_until}",
                        }
                    ],
                }
            )

        # Add terms if provided
        if self.terms:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**条款与条件:**\n{self.terms}",
                    },
                }
            )

        # Add action buttons
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✓ 接受报价"},
                        "type": "primary",
                        "value": {
                            "action": "accept_quote",
                            "quote_id": self.quote_id,
                        },
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✎ 申请修改"},
                        "type": "default",
                        "value": {
                            "action": "request_revision",
                            "quote_id": self.quote_id,
                        },
                    },
                ],
            }
        )

        return {
            "type": "template",
            "data": {
                "template_id": "AAqkWI8RAA",  # Default template
                "template_variable": {
                    "title": "报价单",
                    "elements": elements,
                },
            },
        }


class BANTFormCard(BaseCard):
    """
    BANT qualification form card.

    BANT = Budget, Authority, Need, Timeline

    Interactive form to gather customer qualification information.
    """

    def __init__(
        self,
        title: str = "需求调研",
        description: str = "请填写以下信息，以便我们为您提供更好的服务",
        pre_filled: dict[str, Any] | None = None,
    ):
        """
        Initialize BANT form card.

        Args:
            title: Form title
            description: Form description
            pre_filled: Pre-filled values for fields
        """
        self.title = title
        self.description = description
        self.pre_filled = pre_filled or {}

    def to_json(self) -> dict:
        """Generate Feishu card JSON."""
        elements = [
            # Header
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{self.title}**\n{self.description}",
                },
            },
            {"tag": "hr"},
            # Budget section
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**💰 预算范围**",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "选择预算范围"},
                        "options": [
                            {
                                "text": {"tag": "plain_text", "content": "5万以下"},
                                "value": "budget_5w",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "5-10万"},
                                "value": "budget_5_10w",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "10-50万"},
                                "value": "budget_10_50w",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "50-100万"},
                                "value": "budget_50_100w",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "100万以上"},
                                "value": "budget_100w_plus",
                            },
                        ],
                        "value": {"action": "bant_budget"},
                    }
                ],
            },
            {"tag": "hr"},
            # Authority section
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**👤 决策角色**",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "您的角色是"},
                        "options": [
                            {
                                "text": {"tag": "plain_text", "content": "决策者"},
                                "value": "authority_decision_maker",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "影响者"},
                                "value": "authority_influencer",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "评估者"},
                                "value": "authority_evaluator",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "执行者"},
                                "value": "authority_executor",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "其他"},
                                "value": "authority_other",
                            },
                        ],
                        "value": {"action": "bant_authority"},
                    }
                ],
            },
            {"tag": "hr"},
            # Need section
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**📋 主要需求**",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "您的主要需求"},
                        "options": [
                            {
                                "text": {"tag": "plain_text", "content": "提升效率"},
                                "value": "need_efficiency",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "降低成本"},
                                "value": "need_cost_reduction",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "合规管理"},
                                "value": "need_compliance",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "数据分析"},
                                "value": "need_analytics",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "团队协作"},
                                "value": "need_collaboration",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "客户管理"},
                                "value": "need_crm",
                            },
                        ],
                        "value": {"action": "bant_need"},
                    }
                ],
            },
            {"tag": "hr"},
            # Timeline section
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**⏰ 期望时间线**",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "期望上线时间"},
                        "options": [
                            {
                                "text": {"tag": "plain_text", "content": "1个月内"},
                                "value": "timeline_1m",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "1-3个月"},
                                "value": "timeline_1_3m",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "3-6个月"},
                                "value": "timeline_3_6m",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "6个月以上"},
                                "value": "timeline_6m_plus",
                            },
                            {
                                "text": {"tag": "plain_text", "content": "暂无计划"},
                                "value": "timeline_none",
                            },
                        ],
                        "value": {"action": "bant_timeline"},
                    }
                ],
            },
            # Submit button
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "提交后，我们将为您生成个性化方案",
                    }
                ],
            },
        ]

        return {
            "type": "template",
            "data": {
                "template_id": "AAqkWI8RAA",
                "template_variable": {
                    "title": self.title,
                    "elements": elements,
                },
            },
        }


class MeetingScheduleCard(BaseCard):
    """
    Meeting scheduling card with time slot selection.

    Allows customers to select preferred meeting times.
    """

    def __init__(
        self,
        title: str = "预约会议",
        description: str = "请选择您方便的时间段",
        available_slots: list[dict] | None = None,
        duration_minutes: int = 30,
    ):
        """
        Initialize meeting schedule card.

        Args:
            title: Card title
            description: Card description
            available_slots: List of available time slots with date, time, timezone
            duration_minutes: Meeting duration in minutes
        """
        self.title = title
        self.description = description
        self.available_slots = available_slots or self._generate_default_slots()
        self.duration_minutes = duration_minutes

    def _generate_default_slots(self) -> list[dict]:
        """Generate default time slots for the next 5 business days."""
        slots = []
        # Generate 3 slots per day for next 5 days
        times = ["09:00", "14:00", "16:00"]
        for i in range(5):
            from datetime import timedelta

            date = datetime.now() + timedelta(days=i + 1)
            date_str = date.strftime("%Y-%m-%d")
            day_name = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date.weekday()]
            for time in times:
                slots.append(
                    {
                        "date": date_str,
                        "day": day_name,
                        "time": time,
                        "label": f"{date_str} ({day_name}) {time}",
                    }
                )
        return slots[:9]  # Limit to 9 slots

    def to_json(self) -> dict:
        """Generate Feishu card JSON."""
        # Build time slot options
        slot_options = [
            {
                "text": {
                    "tag": "plain_text",
                    "content": slot["label"],
                },
                "value": {
                    "date": slot["date"],
                    "time": slot["time"],
                },
            }
            for slot in self.available_slots
        ]

        elements = [
            # Header
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{self.title}**\n{self.description}",
                },
            },
            {"tag": "hr"},
            # Duration info
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📅 会议时长: **{self.duration_minutes}分钟**",
                },
            },
            {"tag": "hr"},
            # Time slot selection
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**选择时间段:**",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "select_static",
                        "placeholder": {"tag": "plain_text", "content": "点击选择时间"},
                        "options": slot_options,
                        "value": {"action": "schedule_meeting"},
                    }
                ],
            },
            # Alternative: request custom time
            {"tag": "hr"},
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": "如以上时间均不合适，请直接回复您期望的时间",
                    }
                ],
            },
        ]

        return {
            "type": "template",
            "data": {
                "template_id": "AAqkWI8RAA",
                "template_variable": {
                    "title": self.title,
                    "elements": elements,
                },
            },
        }


class ProductComparisonCard(BaseCard):
    """
    Product comparison card for showing feature differences.

    Displays a comparison table of multiple products across
    specified features.
    """

    def __init__(
        self,
        title: str = "产品对比",
        products: list[dict] | None = None,
        features: list[str] | None = None,
        highlight_product: str | None = None,
    ):
        """
        Initialize product comparison card.

        Args:
            title: Card title
            products: List of products with name, and feature values
            features: List of feature names to compare
            highlight_product: Product name to highlight (our product)
        """
        self.title = title
        self.products = products or []
        self.features = features or []
        self.highlight_product = highlight_product

    def to_json(self) -> dict:
        """Generate Feishu card JSON."""
        if not self.products:
            return {
                "type": "template",
                "data": {
                    "template_id": "AAqkWI8RAA",
                    "template_variable": {
                        "title": self.title,
                        "elements": [
                            {
                                "tag": "div",
                                "text": {
                                    "tag": "lark_md",
                                    "content": "暂无产品数据",
                                },
                            }
                        ],
                    },
                },
            }

        elements = [
            # Header
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{self.title}**",
                },
            },
            {"tag": "hr"},
        ]

        # Build comparison table as markdown
        if len(self.products) <= 3:
            # Use table format for 3 or fewer products
            header = "| 特性 |" + "|".join([f" {p.get('name', '产品')} |" for p in self.products])
            separator = "|" + "|".join(["---|"] * (len(self.products) + 1))
            rows = [header, separator]

            for feature in self.features:
                row = f"| {feature} |"
                for product in self.products:
                    value = product.get("features", {}).get(feature, "-")
                    # Highlight our product's advantages
                    if product.get("name") == self.highlight_product and value != "-":
                        value = f"✓ {value}"
                    row += f" {value} |"
                rows.append(row)

            elements.append(
                {
                    "tag": "markdown",
                    "content": "\n".join(rows),
                }
            )
        else:
            # Use list format for more products
            for product in self.products:
                product_name = product.get("name", "产品")
                is_highlighted = product_name == self.highlight_product

                content = f"**{product_name}**" + (" ⭐" if is_highlighted else "") + "\n"
                for feature in self.features:
                    value = product.get("features", {}).get(feature, "-")
                    content += f"- {feature}: {value}\n"

                elements.append(
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content,
                        },
                    }
                )
                elements.append({"tag": "hr"})

        # Add recommendation if we have a highlighted product
        if self.highlight_product:
            elements.append(
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"推荐: {self.highlight_product} 最适合您的需求",
                        }
                    ],
                }
            )

        # Add action buttons
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "获取报价"},
                        "type": "primary",
                        "value": {"action": "get_quote"},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "预约演示"},
                        "type": "default",
                        "value": {"action": "request_demo"},
                    },
                ],
            }
        )

        return {
            "type": "template",
            "data": {
                "template_id": "AAqkWI8RAA",
                "template_variable": {
                    "title": self.title,
                    "elements": elements,
                },
            },
        }


class QuickReplyCard(BaseCard):
    """
    Quick reply card with preset response options.

    Useful for guiding customers through common scenarios.
    """

    def __init__(
        self,
        message: str,
        options: list[dict],
        title: str | None = None,
    ):
        """
        Initialize quick reply card.

        Args:
            message: The message to display
            options: List of options with text and value
            title: Optional card title
        """
        self.message = message
        self.options = options
        self.title = title

    def to_json(self) -> dict:
        """Generate Feishu card JSON."""
        elements = []

        if self.title:
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{self.title}**",
                    },
                }
            )
            elements.append({"tag": "hr"})

        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": self.message,
                },
            }
        )

        # Build quick reply buttons
        buttons = []
        for option in self.options:
            buttons.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": option.get("text", "")},
                    "type": "default",
                    "value": option.get("value", {}),
                }
            )

        if buttons:
            elements.append(
                {
                    "tag": "action",
                    "actions": buttons,
                }
            )

        return {
            "type": "template",
            "data": {
                "template_id": "AAqkWI8RAA",
                "template_variable": {
                    "title": self.title or "快速回复",
                    "elements": elements,
                },
            },
        }


class LeadCaptureCard(BaseCard):
    """
    Lead capture form card for collecting contact information.

    Used when starting a new sales conversation.
    """

    def __init__(
        self,
        title: str = "欢迎咨询",
        description: str = "请留下您的联系方式，我们将尽快与您取得联系",
        fields: list[str] | None = None,
    ):
        """
        Initialize lead capture card.

        Args:
            title: Form title
            description: Form description
            fields: List of fields to collect (name, company, phone, email, requirements)
        """
        self.title = title
        self.description = description
        self.fields = fields or ["name", "company", "phone", "requirements"]

    def to_json(self) -> dict:
        """Generate Feishu card JSON."""
        field_labels = {
            "name": "姓名",
            "company": "公司名称",
            "phone": "联系电话",
            "email": "电子邮箱",
            "requirements": "需求描述",
        }

        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{self.title}**\n{self.description}",
                },
            },
            {"tag": "hr"},
        ]

        # Add input fields (using buttons for now, as Feishu cards have limited input support)
        for field in self.fields:
            label = field_labels.get(field, field)
            elements.append(
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{label}**",
                    },
                }
            )
            elements.append(
                {
                    "tag": "input",
                    "placeholder": {"tag": "plain_text", "content": f"请输入{label}"},
                    "element_id": f"lead_{field}",
                }
            )

        # Submit button
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "提交"},
                        "type": "primary",
                        "value": {"action": "submit_lead"},
                    }
                ],
            }
        )

        return {
            "type": "template",
            "data": {
                "template_id": "AAqkWI8RAA",
                "template_variable": {
                    "title": self.title,
                    "elements": elements,
                },
            },
        }


# Utility function for creating cards from templates
def create_card_from_template(template_id: str, variables: dict[str, Any]) -> dict:
    """
    Create a Feishu card from a template ID and variables.

    Args:
        template_id: Feishu card template ID
        variables: Template variable values

    Returns:
        Card JSON structure
    """
    return {
        "type": "template",
        "data": {
            "template_id": template_id,
            "template_variable": variables,
        },
    }
