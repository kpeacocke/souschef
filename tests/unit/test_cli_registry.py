"""Tests for cli_registry module."""

from unittest.mock import MagicMock, patch

import pytest

from souschef import cli_registry
from souschef.cli_registry import CLIFeatureRegistry


@pytest.fixture
def registry() -> CLIFeatureRegistry:
    """Provide a fresh registry instance."""
    return CLIFeatureRegistry()


def test_register_and_list_groups(registry: CLIFeatureRegistry) -> None:
    """Registering a group should appear in list_groups."""
    loader = MagicMock()

    registry.register("v2", loader, enabled=True, description="Test group")

    groups = registry.list_groups()
    assert "v2" in groups
    assert groups["v2"]["loader"] == loader
    assert groups["v2"]["enabled"] is True
    assert groups["v2"]["description"] == "Test group"


def test_load_all_only_enabled(registry: CLIFeatureRegistry) -> None:
    """load_all should only call enabled group loaders."""
    loader_enabled = MagicMock()
    loader_disabled = MagicMock()

    registry.register("enabled", loader_enabled, enabled=True)
    registry.register("disabled", loader_disabled, enabled=False)

    cli = MagicMock()
    registry.load_all(cli)

    loader_enabled.assert_called_once_with(cli)
    loader_disabled.assert_not_called()


def test_load_all_raises_runtime_error_on_loader_failure(
    registry: CLIFeatureRegistry,
) -> None:
    """Loader exceptions should be wrapped in RuntimeError."""

    def boom(_cli):
        raise ValueError("Boom")

    registry.register("bad", boom, enabled=True)

    with pytest.raises(RuntimeError, match="Failed to load CLI group 'bad': Boom"):
        registry.load_all(MagicMock())


def test_enable_disable_and_is_enabled(registry: CLIFeatureRegistry) -> None:
    """Enable/disable should toggle group state."""
    loader = MagicMock()
    registry.register("v2", loader, enabled=False)

    assert registry.is_enabled("v2") is False

    registry.enable("v2")
    assert registry.is_enabled("v2") is True

    registry.disable("v2")
    assert registry.is_enabled("v2") is False


def test_enable_unknown_group_raises(registry: CLIFeatureRegistry) -> None:
    """Enabling unknown group should raise KeyError."""
    with pytest.raises(KeyError, match="Unknown CLI group"):
        registry.enable("missing")


def test_disable_unknown_group_raises(registry: CLIFeatureRegistry) -> None:
    """Disabling unknown group should raise KeyError."""
    with pytest.raises(KeyError, match="Unknown CLI group"):
        registry.disable("missing")


def test_is_enabled_unknown_group_false(registry: CLIFeatureRegistry) -> None:
    """Unknown group should report disabled."""
    assert registry.is_enabled("missing") is False


def test_get_registry_returns_global_instance() -> None:
    """get_registry should return the module-global registry."""
    assert cli_registry.get_registry() is cli_registry._registry


def test_register_default_groups_registers_v2() -> None:
    """register_default_groups should register v2 group on global registry."""
    registry = cli_registry._registry
    original_groups = registry._groups.copy()
    try:
        registry._groups.clear()

        with patch("souschef.cli_v2_commands.register_v2_commands") as mock_loader:
            cli_registry.register_default_groups()

        assert "v2" in registry._groups
        assert registry._groups["v2"]["loader"] == mock_loader
        assert registry._groups["v2"]["enabled"] is True
        assert registry._groups["v2"]["description"]
    finally:
        registry._groups = original_groups
