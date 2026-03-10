"""Integrations with external services."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from salemates.integrations.esignature import ESignatureClient
    from salemates.integrations.langfuse import LangfuseClient

__all__ = ["ESignatureClient", "LangfuseClient"]


def __getattr__(name: str):
    if name == "ESignatureClient":
        from salemates.integrations.esignature import ESignatureClient

        return ESignatureClient
    if name == "LangfuseClient":
        from salemates.integrations.langfuse import LangfuseClient

        return LangfuseClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
