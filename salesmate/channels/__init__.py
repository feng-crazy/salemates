"""Chat channels module with plugin architecture."""

from salesmate.channels.base import BaseChannel
from salesmate.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
