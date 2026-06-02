"""
regops.importers — plugin registry for compliance-source importers.

Concrete importers register themselves at import time via the
@register decorator and are then discoverable by name:

    from regops.importers import register, get_importer
    @register
    class MyImporter(ImporterBase):
        name = "myimporter"
        ...

    cls = get_importer("myimporter")
"""

from typing import Type

from regops.importers.base import ImporterBase, ImportPayload

_REGISTRY: dict[str, Type[ImporterBase]] = {}


def register(cls: Type[ImporterBase]) -> Type[ImporterBase]:
    """Decorator: add an importer class to the registry under its `name`."""
    if not getattr(cls, "name", ""):
        raise ValueError(
            f"{cls.__name__} cannot be registered: missing or empty `name` attribute"
        )
    if cls.name in _REGISTRY and _REGISTRY[cls.name] is not cls:
        raise ValueError(
            f"Importer name {cls.name!r} already registered "
            f"by {_REGISTRY[cls.name].__name__}"
        )
    _REGISTRY[cls.name] = cls
    return cls


def get_importer(name: str) -> Type[ImporterBase]:
    """Return the importer class registered under `name`. Raises KeyError if absent."""
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise KeyError(
            f"Unknown importer {name!r}. Available: {available}"
        )
    return _REGISTRY[name]


def list_importers() -> list[str]:
    """Sorted list of registered importer names."""
    return sorted(_REGISTRY)


__all__ = [
    "ImporterBase",
    "ImportPayload",
    "register",
    "get_importer",
    "list_importers",
]
