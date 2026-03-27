"""Dark/light mode theme support with OS detection for Streamlit UI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

import streamlit as st

LOGGER = logging.getLogger(__name__)

ThemeMode = Literal["light", "dark", "auto"]
VALID_THEMES = {"light", "dark", "auto"}
THEME_CONFIG_FILE = Path.home() / ".souschef" / "theme.json"


def _get_os_prefers_dark() -> bool:
    """
    Detect if the operating system prefers dark mode.

    Uses CSS media query simulation. Returns True if OS is in dark mode.
    Note: This is a best-effort approach; Streamlit client detection is limited.

    Returns:
        True if OS prefers dark mode, False otherwise.

    """
    # Streamlit doesn't provide direct OS theme detection at runtime
    # We use client-side CSS media query via JS injection
    # For now, default to system default (we'll detect via JS in sidebar)
    return False


def _load_theme_preference() -> ThemeMode:
    """
    Load theme preference from local config file.

    Returns:
        Saved theme preference or 'auto' if not set.

    """
    try:
        if THEME_CONFIG_FILE.exists():
            with THEME_CONFIG_FILE.open() as f:
                config = json.load(f)
                theme = config.get("theme", "auto")
                if theme in VALID_THEMES and isinstance(theme, str):
                    return theme  # type: ignore[return-value]
    except (OSError, json.JSONDecodeError) as e:
        LOGGER.debug(f"Could not load theme config: {e}")
    return "auto"


def _save_theme_preference(theme: ThemeMode) -> None:
    """
    Save theme preference to local config file.

    Args:
        theme: Theme mode to save ('light', 'dark', or 'auto').

    """
    try:
        THEME_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with THEME_CONFIG_FILE.open("w") as f:
            json.dump({"theme": theme}, f)
    except OSError as e:
        LOGGER.warning(f"Could not save theme config: {e}")


def get_active_theme() -> ThemeMode:
    """
    Get the currently active theme mode.

    Checks session state first, then loads from file if not in session.

    Returns:
        Current theme mode ('light', 'dark', or 'auto').

    """
    if "souschef_theme" not in st.session_state:
        st.session_state.souschef_theme = _load_theme_preference()
    theme = st.session_state.souschef_theme
    if isinstance(theme, str) and theme in VALID_THEMES:
        return theme  # type: ignore[return-value]
    return "auto"


def set_theme(theme: ThemeMode) -> None:
    """
    Set the active theme mode.

    Args:
        theme: Theme mode to set ('light', 'dark', or 'auto').

    """
    if theme not in VALID_THEMES:
        raise ValueError(f"Invalid theme: {theme}. Must be one of {VALID_THEMES}")
    st.session_state.souschef_theme = theme
    _save_theme_preference(theme)


def apply_theme_config(st_config: dict[str, str]) -> dict[str, str | None]:
    """
    Apply the current theme to Streamlit configuration.

    Args:
        st_config: Current Streamlit config dict (from st.set_page_config theme param).

    Returns:
        Updated configuration dict with theme applied.

    """
    theme_mode = get_active_theme()

    if theme_mode == "light":
        return {**st_config, "theme": "light"}
    elif theme_mode == "dark":
        return {**st_config, "theme": "dark"}
    else:  # auto
        # Let Streamlit use browser/OS preference
        return {**st_config, "theme": None}


def show_theme_selector() -> None:
    """
    Display theme selector in the UI (typically in sidebar).

    Allows user to switch between light, dark, and auto modes.
    Persists selection across sessions.

    """
    st.sidebar.divider()
    st.sidebar.subheader("Theme")

    current_theme = get_active_theme()
    options = ["Light", "Dark", "Auto (OS default)"]
    option_values = ["light", "dark", "auto"]
    current_index = option_values.index(current_theme)

    selected = st.sidebar.selectbox(
        "Appearance",
        options,
        index=current_index,
        key="theme_selector",
        help="Choose your preferred color mode. 'Auto' follows your OS setting.",
    )

    selected_value: ThemeMode = option_values[options.index(selected)]  # type: ignore[assignment]
    if selected_value != current_theme:
        set_theme(selected_value)
        st.rerun()
