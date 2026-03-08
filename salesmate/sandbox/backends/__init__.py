"""Sandbox backend registry."""

from typing import TYPE_CHECKING, Type, Callable, Dict
from salesmate.sandbox.base import SandboxBackend

_BACKENDS: Dict[str, Type[SandboxBackend]] = {}


def register_backend(name: str) -> Callable[[Type[SandboxBackend]], Type[SandboxBackend]]:
    """Decorator to register a sandbox backend."""

    def decorator(cls: Type[SandboxBackend]) -> Type[SandboxBackend]:
        _BACKENDS[name] = cls
        return cls

    return decorator


def get_backend(name: str) -> Type[SandboxBackend] | None:
    """Get backend class by name."""
    return _BACKENDS.get(name)


def list_backends() -> list[str]:
    """List all registered backends."""
    return list(_BACKENDS.keys())


# Import backends to register them (avoid circular import)

from salesmate.sandbox.backends import srt
from salesmate.sandbox.backends import opensandbox
from salesmate.sandbox.backends import direct
from salesmate.sandbox.backends import aiosandbox
