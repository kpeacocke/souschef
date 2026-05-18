"""Keyboard shortcut registry and command palette helpers."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any


@dataclass(frozen=True)
class CommandDefinition:
    """A palette command with display metadata and target action."""

    command_id: str
    label: str
    action: str
    shortcut: str


def register_shortcut(
    registry: dict[str, str],
    shortcut: str,
    command_id: str,
) -> dict[str, str]:
    """Register a shortcut and enforce conflict safety."""
    normalised = shortcut.strip().lower()
    if not normalised:
        raise ValueError("shortcut must not be empty")

    existing = registry.get(normalised)
    if existing and existing != command_id:
        raise ValueError(
            f"Shortcut conflict for '{normalised}': '{existing}' vs '{command_id}'"
        )

    registry[normalised] = command_id
    return registry


def build_shortcut_registry(
    commands: list[CommandDefinition],
) -> dict[str, str]:
    """Build a global shortcut registry with conflict validation."""
    registry: dict[str, str] = {}
    for command in commands:
        register_shortcut(registry, command.shortcut, command.command_id)
    return registry


def fuzzy_find_commands(
    query: str,
    commands: list[CommandDefinition],
    limit: int = 6,
) -> list[CommandDefinition]:
    """Find commands by fuzzy label and shortcut matching."""
    if not query.strip():
        return commands[:limit]

    lowered_query = query.strip().lower()
    by_contains = [
        command
        for command in commands
        if lowered_query in command.label.lower()
        or lowered_query in command.shortcut.lower()
    ]
    if by_contains:
        return by_contains[:limit]

    labels = [command.label for command in commands]
    fuzzy_labels = set(get_close_matches(query, labels, n=limit, cutoff=0.35))
    return [command for command in commands if command.label in fuzzy_labels][:limit]


def dispatch_command(
    command_id: str,
    commands: list[CommandDefinition],
) -> str | None:
    """Resolve command ID into a target page action."""
    for command in commands:
        if command.command_id == command_id:
            return command.action
    return None


def record_recent_command(
    command_id: str,
    session_state: Any,
    max_items: int = 5,
) -> list[str]:
    """Record recently executed commands in most-recent-first order."""
    recent = list(session_state.get("recent_commands", []))
    recent = [value for value in recent if value != command_id]
    recent.insert(0, command_id)
    updated: list[str] = recent[:max_items]
    session_state.recent_commands = updated
    return updated


def render_command_palette(
    streamlit_module: Any,
    commands: list[CommandDefinition],
) -> str | None:
    """Render command palette controls and return selected action if executed."""
    if not commands:
        return None

    sidebar = streamlit_module.sidebar
    sidebar.divider()
    sidebar.subheader("Command Palette")

    raw_query = sidebar.text_input(
        "Find command",
        value="",
        key="command_palette_query",
        help="Search commands by name or shortcut.",
    )
    query = str(raw_query)

    matches = fuzzy_find_commands(query, commands)
    command_labels = [f"{item.label} ({item.shortcut})" for item in matches]

    if not command_labels:
        sidebar.info("No commands match your query.")
        return None

    selected_label = sidebar.selectbox(
        "Commands",
        options=command_labels,
        key="command_palette_select",
    )

    if selected_label not in command_labels:
        return None

    selected_command = next(
        item for item in matches if f"{item.label} ({item.shortcut})" == selected_label
    )

    recent_commands = streamlit_module.session_state.get("recent_commands", [])
    if recent_commands:
        sidebar.caption("Recent: " + ", ".join(recent_commands))

    sidebar.caption(
        "Shortcut hints: "
        + " | ".join(f"{item.shortcut}={item.label}" for item in commands[:4])
    )

    if sidebar.button("Run Command", key="command_palette_run", width="stretch"):
        record_recent_command(
            selected_command.command_id,
            streamlit_module.session_state,
        )
        return selected_command.action

    return None
