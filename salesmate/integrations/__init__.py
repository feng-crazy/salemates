"""Integrations with external services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from salesmate.integrations.langfuse import LangfuseClient

__all__ = ["LangfuseClient"]


def __getattr__(name: str):
    if name == "LangfuseClient":
        from salesmate.integrations.langfuse import LangfuseClient

        return LangfuseClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
