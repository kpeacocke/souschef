"""Unit tests for live preview helpers in cookbook_analysis."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_streamlit() -> Generator[MagicMock, None, None]:
    """Mock Streamlit for the live preview helper tests."""
    mock_st = MagicMock()
    mock_st.expander.return_value.__enter__.return_value = mock_st
    mock_st.expander.return_value.__exit__.return_value = False

    with patch("souschef.ui.pages.cookbook_analysis.st", mock_st):
        yield mock_st


from souschef.ui.pages.cookbook_analysis import (  # noqa: E402
    _apply_preview_tweaks,
    _build_live_preview_content,
    _display_inline_validation_feedback,
    _display_playbook_previews,
    _parse_preview_mapping_input,
    _summarise_inline_validation,
)


def test_parse_preview_mapping_input_handles_invalid_values() -> None:
    """Invalid mapping inputs degrade to an empty mapping."""
    assert _parse_preview_mapping_input("") == {}
    assert _parse_preview_mapping_input("[]") == {}
    assert _parse_preview_mapping_input("{") == {}
    assert _parse_preview_mapping_input(MagicMock()) == {}


def test_parse_preview_mapping_input_parses_string_mapping() -> None:
    """Valid JSON objects are coerced to string mappings."""
    result = _parse_preview_mapping_input('{"apt:": "package:", 1: true}')

    assert result == {"apt:": "package:", "1": "True"}


def test_apply_preview_tweaks_replaces_normalises_and_prefixes() -> None:
    """Preview tweaks update module names, states, and task names."""
    content = "- name: install nginx\n  apt:\n    state: installed\n"

    result = _apply_preview_tweaks(
        content,
        {"apt:": "package:"},
        normalise_package_state=True,
        task_name_prefix="Preview: ",
    )

    assert result == (
        "- name: Preview: install nginx\n  package:\n    state: present\n"
    )


def test_summarise_inline_validation_handles_invalid_json() -> None:
    """Invalid validation payloads report a synthetic error."""
    assert _summarise_inline_validation("not json") == {"errors": 1, "warnings": 0}


def test_summarise_inline_validation_reads_summary() -> None:
    """Validation summaries are extracted from JSON payloads."""
    payload = json.dumps({"summary": {"errors": 2, "warnings": 3}})

    assert _summarise_inline_validation(payload) == {"errors": 2, "warnings": 3}


def test_display_inline_validation_feedback_shows_error(
    mock_streamlit: MagicMock,
) -> None:
    """Error summaries surface as Streamlit errors."""
    with patch(
        "souschef.ui.pages.cookbook_analysis.validate_conversion_output",
        return_value=json.dumps({"summary": {"errors": 1, "warnings": 2}}),
    ):
        _display_inline_validation_feedback("- hosts: all")

    mock_streamlit.error.assert_called_once()


def test_display_inline_validation_feedback_shows_warning(
    mock_streamlit: MagicMock,
) -> None:
    """Warning-only summaries surface as Streamlit warnings."""
    with patch(
        "souschef.ui.pages.cookbook_analysis.validate_conversion_output",
        return_value=json.dumps({"summary": {"errors": 0, "warnings": 2}}),
    ):
        _display_inline_validation_feedback("- hosts: all")

    mock_streamlit.warning.assert_called_once()


def test_display_inline_validation_feedback_shows_success(
    mock_streamlit: MagicMock,
) -> None:
    """Clean validation summaries surface as Streamlit success messages."""
    with patch(
        "souschef.ui.pages.cookbook_analysis.validate_conversion_output",
        return_value=json.dumps({"summary": {"errors": 0, "warnings": 0}}),
    ):
        _display_inline_validation_feedback("- hosts: all")

    mock_streamlit.success.assert_called_once_with("Inline validation passed.")


def test_build_live_preview_content_uses_controls(mock_streamlit: MagicMock) -> None:
    """Live preview content is built from the tweak controls."""
    mock_streamlit.text_area.return_value = '{"apt:": "package:"}'
    mock_streamlit.checkbox.return_value = True
    mock_streamlit.text_input.return_value = "Preview: "

    result = _build_live_preview_content(
        {"playbook_content": "- name: install\n  apt:\n    state: installed\n"},
        4,
    )

    assert result == ("- name: Preview: install\n  package:\n    state: present\n")
    mock_streamlit.text_area.assert_called_once()
    mock_streamlit.checkbox.assert_called_once()
    mock_streamlit.text_input.assert_called_once()


def test_display_playbook_previews_uses_live_preview_helpers(
    mock_streamlit: MagicMock,
) -> None:
    """Preview rendering delegates to the live preview helpers per playbook."""
    playbooks = [
        {
            "cookbook_name": "nginx",
            "recipe_file": "default.rb",
            "playbook_content": "- hosts: all\n",
            "conversion_method": "AI-enhanced",
        }
    ]

    with (
        patch(
            "souschef.ui.pages.cookbook_analysis._build_live_preview_content",
            return_value="- hosts: all\n",
        ) as mock_build,
        patch(
            "souschef.ui.pages.cookbook_analysis._display_inline_validation_feedback"
        ) as mock_feedback,
    ):
        _display_playbook_previews(playbooks)

    mock_build.assert_called_once_with(playbooks[0], 0)
    mock_feedback.assert_called_once_with("- hosts: all\n")
    mock_streamlit.code.assert_called_once()
