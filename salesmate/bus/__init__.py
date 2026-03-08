"""Message bus module for decoupled channel-agent communication."""

from salesmate.bus.events import InboundMessage, OutboundMessage
from salesmate.bus.queue import MessageBus

__all__ = ["MessageBus", "InboundMessage", "OutboundMessage"]
