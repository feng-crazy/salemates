"""Agent tools module."""

from salemates.agent.tools.base import Tool
from salemates.agent.tools.competitor_tool import CompetitorTool
from salemates.agent.tools.customer_profile_tool import CustomerProfileTool
from salemates.agent.tools.factory import register_default_tools, register_subagent_tools
from salemates.agent.tools.quote_generator import QuoteGeneratorTool
from salemates.agent.tools.registry import ToolRegistry

__all__ = [
    "Tool",
    "ToolRegistry",
    "register_default_tools",
    "register_subagent_tools",
    "CustomerProfileTool",
    "QuoteGeneratorTool",
    "CompetitorTool",
]
