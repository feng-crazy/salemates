"""LLM provider abstraction module."""

from salesmate.providers.base import LLMProvider, LLMResponse
from salesmate.providers.litellm_provider import LiteLLMProvider

__all__ = ["LLMProvider", "LLMResponse", "LiteLLMProvider"]
