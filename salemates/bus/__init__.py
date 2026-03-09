"""Message bus module for decoupled channel-agent communication."""

from salemates.bus.events import InboundMessage, OutboundMessage
from salemates.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
