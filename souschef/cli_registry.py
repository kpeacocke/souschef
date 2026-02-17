"""
CLI feature registry for pluggable command groups.

Provides a mechanism to register and conditionally load CLI command groups,
enabling extensibility without modifying the main CLI module.
"""

from collections.abc import Callable
from typing import Any


class CLIFeatureRegistry:
    """
    Registry for pluggable CLI command groups.

    Allows teams to add new CLI command groups without modifying core CLI code.
    Supports conditional loading and feature management.
    """

    def __init__(self) -> None:
        """Initialise the CLI feature registry."""
        self._groups: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        loader: Callable[[Any], None],
        enabled: bool = True,
        description: str = "",
    ) -> None:
        """
        Register a CLI command group.

        Args:
            name: Group name (e.g., 'v2').
            loader: Callable that registers the group.
                   Receives the main CLI object as argument.
            enabled: Whether the group is enabled (default: True).
            description: Description of the command group.

        """
        self._groups[name] = {
            "loader": loader,
            "enabled": enabled,
            "description": description,
        }

    def load_all(self, cli: Any) -> None:
        """
        Load all enabled command groups into the main CLI.

        Args:
            cli: The main Click CLI group.

        """
        for name, config in self._groups.items():
            if config["enabled"]:
                try:
                    config["loader"](cli)
                except Exception as e:
                    raise RuntimeError(f"Failed to load CLI group '{name}': {e}") from e

    def enable(self, name: str) -> None:
        """
        Enable a command group.

        Args:
            name: Group name to enable.

        Raises:
            KeyError: If group does not exist.

        """
        if name not in self._groups:
            raise KeyError(f"Unknown CLI group: {name}")
        self._groups[name]["enabled"] = True

    def disable(self, name: str) -> None:
        """
        Disable a command group.

        Args:
            name: Group name to disable.

        Raises:
            KeyError: If group does not exist.

        """
        if name not in self._groups:
            raise KeyError(f"Unknown CLI group: {name}")
        self._groups[name]["enabled"] = False

    def is_enabled(self, name: str) -> bool:
        """
        Check if a command group is enabled.

        Args:
            name: Group name to check.

        Returns:
            True if group is registered and enabled.

        """
        return bool(self._groups.get(name, {}).get("enabled", False))

    def list_groups(self) -> dict[str, dict[str, Any]]:
        """
        List all registered command groups.

        Returns:
            Dictionary of group names to their configuration.

        """
        return self._groups.copy()


# Global registry instance
_registry = CLIFeatureRegistry()


def get_registry() -> CLIFeatureRegistry:
    """
    Get the global CLI feature registry.

    Returns:
        The global CLIFeatureRegistry instance.

    """
    return _registry


def register_default_groups() -> None:
    """
    Register the default SousChef command groups.

    This function registers the v2 migration command group and any other
    built-in command groups that should be available by default.
    """
    from souschef.cli_v2_commands import register_v2_commands

    _registry.register(
        name="v2",
        loader=register_v2_commands,
        enabled=True,
        description="V2 migration orchestrator commands",
    )
