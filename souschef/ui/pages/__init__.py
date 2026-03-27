"""SousChef UI pages package."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

__all__ = [
    "ai_settings",
    "chef_server_settings",
    "cookbook_analysis",
    "history",
    "migration_config",
    "validation_reports",
]


class _PagesModule(types.ModuleType):
    """Resolve page submodules dynamically to keep cache state consistent."""

    def __getattribute__(self, name: str) -> Any:
        exported = super().__getattribute__("__dict__").get("__all__", [])
        if name in exported:
            full_name = f"{super().__getattribute__('__name__')}.{name}"
            module = sys.modules.get(full_name)
            if module is None:
                module = importlib.import_module(full_name)
            return module
        return super().__getattribute__(name)


sys.modules[__name__].__class__ = _PagesModule
