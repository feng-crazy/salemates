"""Chat channels module with plugin architecture."""

from salemates.channels.base import BaseChannel
from salemates.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
