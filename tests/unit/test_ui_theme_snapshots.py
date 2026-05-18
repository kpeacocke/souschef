"""Snapshot-style tests for UI theme CSS output."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class SessionState(dict):
    """Session state helper with attribute access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def test_build_theme_css_snapshot_light_contains_focus_and_tokens() -> None:
    """Light mode CSS should include deterministic token and focus styles."""
    from souschef.ui.theme import build_theme_css

    css = build_theme_css("light")

    assert "--sc-bg: #ffffff;" in css
    assert "--sc-text: #182230;" in css
    assert "*:focus" in css
    assert "outline: 3px solid var(--sc-focus-ring)" in css
    assert ".skip-link" in css
    assert '[role="main"]' in css


def test_build_theme_css_snapshot_high_contrast_critical_tokens() -> None:
    """High-contrast CSS should preserve strict contrast token palette."""
    from souschef.ui.theme import build_theme_css

    css = build_theme_css("high_contrast")

    assert "--sc-bg: #000000;" in css
    assert "--sc-text: #ffffff;" in css
    assert "--sc-focus-ring: #ffdd00;" in css


def test_apply_theme_styles_writes_css_to_sidebar() -> None:
    """Applying theme styles should inject CSS through sidebar markdown."""
    from souschef.ui import theme

    mock_st = SimpleNamespace(
        session_state=SessionState({"souschef_theme": "dark"}),
        sidebar=MagicMock(),
    )

    with patch("souschef.ui.theme.st", mock_st):
        theme.apply_theme_styles()

    mock_st.sidebar.markdown.assert_called_once()


def test_render_accessibility_landmarks_writes_semantic_html() -> None:
    """Landmark renderer should inject skip-link and semantic role markup."""
    from souschef.ui import theme

    mock_st = SimpleNamespace(
        session_state=SessionState({"souschef_theme": "dark"}),
        sidebar=MagicMock(),
        markdown=MagicMock(),
    )

    with patch("souschef.ui.theme.st", mock_st):
        theme.render_accessibility_landmarks()

    mock_st.markdown.assert_called_once()
    rendered_html = mock_st.markdown.call_args.args[0]
    assert "Skip to main content" in rendered_html
    assert 'role="navigation"' in rendered_html
    assert 'role="main"' in rendered_html
