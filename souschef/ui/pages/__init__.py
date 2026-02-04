"""SousChef UI pages package."""

# Import submodules to ensure they're accessible as souschef.ui.pages.migration_config
from . import (  # noqa: F401
    ai_settings,
    chef_server_settings,
    cookbook_analysis,
    history,
    migration_config,
    validation_reports,
)

__all__ = [
    "ai_settings",
    "chef_server_settings",
    "cookbook_analysis",
    "history",
    "migration_config",
    "validation_reports",
]
