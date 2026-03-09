"""LLM provider abstraction module."""

from salemates.providers.base import LLMProvider, LLMResponse
from salemates.providers.litellm_provider import LiteLLMProvider

__all__ = ["LLMProvider", "LLMResponse", "LiteLLMProvider"]
