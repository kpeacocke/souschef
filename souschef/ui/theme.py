"""Theme system for light, dark, and high-contrast Streamlit UI modes."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal, cast

import streamlit as st

LOGGER = logging.getLogger(__name__)

ThemeMode = Literal["light", "dark", "high_contrast", "auto"]
ResolvedThemeMode = Literal["light", "dark", "high_contrast"]
VALID_THEMES = {"light", "dark", "high_contrast", "auto"}
THEME_CONFIG_FILE = Path.home() / ".souschef" / "theme.json"

THEME_TOKENS: dict[ResolvedThemeMode, dict[str, str]] = {
    "light": {
        "bg": "#ffffff",
        "surface": "#f5f7fb",
        "text": "#182230",
        "muted": "#475467",
        "border": "#d0d5dd",
        "focus_ring": "#1570ef",
        "accent": "#0b4a8b",
    },
    "dark": {
        "bg": "#101828",
        "surface": "#1d2939",
        "text": "#f2f4f7",
        "muted": "#cbd5e1",
        "border": "#344054",
        "focus_ring": "#84caff",
        "accent": "#b2ddff",
    },
    "high_contrast": {
        "bg": "#000000",
        "surface": "#111111",
        "text": "#ffffff",
        "muted": "#ffffff",
        "border": "#ffffff",
        "focus_ring": "#ffdd00",
        "accent": "#00ffff",
    },
}


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
                    return cast(ThemeMode, theme)
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
        return cast(ThemeMode, theme)
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


def resolve_theme_mode(theme_mode: ThemeMode | None = None) -> ResolvedThemeMode:
    """Resolve auto mode into an explicit render mode."""
    mode = theme_mode or get_active_theme()
    if mode == "auto":
        return "dark" if _get_os_prefers_dark() else "light"
    if mode in {"light", "dark", "high_contrast"}:
        return mode
    return "light"


def get_theme_tokens(theme_mode: ThemeMode | None = None) -> dict[str, str]:
    """Return centralised theme tokens for the active or requested mode."""
    resolved = resolve_theme_mode(theme_mode)
    return THEME_TOKENS[resolved]


def build_theme_css(theme_mode: ThemeMode | None = None) -> str:
    """Build CSS variables and focus styles for current theme mode."""
    tokens = get_theme_tokens(theme_mode)
    return f"""
<style>
    :root {{
        --sc-bg: {tokens["bg"]};
        --sc-surface: {tokens["surface"]};
        --sc-text: {tokens["text"]};
        --sc-muted: {tokens["muted"]};
        --sc-border: {tokens["border"]};
        --sc-focus-ring: {tokens["focus_ring"]};
        --sc-accent: {tokens["accent"]};
    }}

    .stApp {{
        background-color: var(--sc-bg);
        color: var(--sc-text);
    }}

    .stDataFrame,
    .stMetric,
    .stTextInput,
    .stSelectbox,
    .stMultiSelect,
    .stTextArea {{
        color: var(--sc-text);
    }}

    .stButton > button,
    .stDownloadButton > button {{
        border: 1px solid var(--sc-border);
        color: var(--sc-text);
        background: var(--sc-surface);
    }}

    .stButton > button:hover,
    .stDownloadButton > button:hover {{
        border-color: var(--sc-accent);
    }}

    .skip-link {{
        position: absolute;
        left: -9999px;
        top: 0;
        background: var(--sc-surface);
        border: 2px solid var(--sc-focus-ring);
        color: var(--sc-text);
        padding: 0.5rem 0.75rem;
        z-index: 9999;
    }}

    .skip-link:focus,
    .skip-link:focus-visible {{
        left: 1rem;
        top: 1rem;
    }}

    [role="main"] {{
        scroll-margin-top: 1rem;
    }}

    *:focus,
    *:focus-visible {{
        outline: 3px solid var(--sc-focus-ring) !important;
        outline-offset: 2px;
    }}
</style>
"""


def apply_theme_styles(
    theme_mode: ThemeMode | None = None,
    streamlit_module: Any | None = None,
) -> None:
    """Inject theme CSS so visual tokens and focus styles are applied."""
    active_st = streamlit_module or st
    active_st.sidebar.markdown(build_theme_css(theme_mode), unsafe_allow_html=True)


def build_accessibility_landmarks_html() -> str:
    """Return semantic landmark and skip-link markup for keyboard users."""
    return """
<a class="skip-link" href="#main-content">Skip to main content</a>
<div role="navigation" aria-label="Primary navigation"></div>
<div id="main-content" role="main" aria-label="SousChef main content"></div>
"""


def render_accessibility_landmarks(streamlit_module: Any | None = None) -> None:
    """Render top-level semantic landmarks used across core UI workflows."""
    active_st = streamlit_module or st
    active_st.markdown(build_accessibility_landmarks_html(), unsafe_allow_html=True)


def show_theme_selector(streamlit_module: Any | None = None) -> None:
    """
    Display theme selector in the UI (typically in sidebar).

    Allows user to switch between light, dark, and auto modes.
    Persists selection across sessions.

    """
    active_st = streamlit_module or st

    active_st.sidebar.divider()
    active_st.sidebar.subheader("Theme")

    current_theme = get_active_theme()
    options = ["Light", "Dark", "High Contrast", "Auto (OS default)"]
    option_values = ["light", "dark", "high_contrast", "auto"]
    current_index = option_values.index(current_theme)

    selected = active_st.sidebar.selectbox(
        "Appearance",
        options,
        index=current_index,
        key="theme_selector",
        help="Choose your preferred color mode. 'Auto' follows your OS setting.",
    )

    if selected not in options:
        return

    selected_value = cast(ThemeMode, option_values[options.index(selected)])
    if selected_value != current_theme:
        set_theme(selected_value)
        active_st.rerun()
