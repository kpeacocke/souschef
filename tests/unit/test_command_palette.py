"""Tests for command palette and shortcut registry helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from souschef.ui.command_palette import (
    CommandDefinition,
    build_shortcut_registry,
    dispatch_command,
    fuzzy_find_commands,
    record_recent_command,
    register_shortcut,
    render_command_palette,
)


class SessionState(dict):
    """Session state helper with attribute access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _commands() -> list[CommandDefinition]:
    return [
        CommandDefinition("go_dashboard", "Go: Dashboard", "Dashboard", "g d"),
        CommandDefinition("go_history", "Go: History", "History", "g h"),
        CommandDefinition("go_workspace", "Go: Workspace", "Workspace", "g w"),
    ]


def test_register_shortcut_detects_conflict() -> None:
    """Conflicting shortcut registrations should raise a clear error."""
    registry = {"g d": "go_dashboard"}

    with pytest.raises(ValueError, match="Shortcut conflict"):
        register_shortcut(registry, "g d", "go_history")


def test_build_shortcut_registry_success() -> None:
    """Building registry should include all command shortcuts."""
    registry = build_shortcut_registry(_commands())

    assert registry["g d"] == "go_dashboard"
    assert registry["g h"] == "go_history"


def test_fuzzy_find_commands_query() -> None:
    """Fuzzy matching should find close label matches."""
    matches = fuzzy_find_commands("hist", _commands())
    assert matches
    assert matches[0].command_id == "go_history"


def test_dispatch_and_recent_commands() -> None:
    """Dispatch should resolve actions and recents should maintain order."""
    assert dispatch_command("go_workspace", _commands()) == "Workspace"
    assert dispatch_command("missing", _commands()) is None

    session_state = SessionState()
    record_recent_command("go_history", session_state)
    record_recent_command("go_workspace", session_state)
    record_recent_command("go_history", session_state)

    assert session_state.recent_commands == ["go_history", "go_workspace"]


def test_render_command_palette_runs_selected_command() -> None:
    """Running palette action should return selected target page."""
    sidebar = MagicMock()
    sidebar.text_input.return_value = ""
    sidebar.selectbox.return_value = "Go: History (g h)"
    sidebar.button.return_value = True

    st_module = SimpleNamespace(sidebar=sidebar, session_state=SessionState())

    result = render_command_palette(st_module, _commands())

    assert result == "History"
    assert st_module.session_state.recent_commands == ["go_history"]
