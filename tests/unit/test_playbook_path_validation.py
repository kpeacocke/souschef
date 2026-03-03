"""Tests for playbook path validation error handling."""

from pathlib import Path
from unittest.mock import patch

from souschef.converters import playbook as playbook_module
from souschef.converters.playbook import (
    generate_playbook_from_recipe,
    generate_playbook_from_recipe_with_ai,
)


def test_generate_playbook_from_recipe_missing_file() -> None:
    """Return error when recipe file does not exist."""
    with (
        patch.object(playbook_module, "parse_recipe", return_value="parsed"),
        patch(
            "souschef.converters.playbook._normalize_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook._get_workspace_root",
            return_value=Path("/tmp"),
        ),
        patch(
            "souschef.converters.playbook._ensure_within_base_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook.safe_exists",
            return_value=False,
        ),
    ):
        result = generate_playbook_from_recipe("/tmp/recipe.rb")

    assert "Recipe file does not exist" in result


def test_generate_playbook_from_recipe_path_traversal() -> None:
    """Return error on path traversal detection."""
    with (
        patch.object(playbook_module, "parse_recipe", return_value="parsed"),
        patch(
            "souschef.converters.playbook._normalize_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook._get_workspace_root",
            return_value=Path("/tmp"),
        ),
        patch(
            "souschef.converters.playbook._ensure_within_base_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook.safe_exists",
            return_value=True,
        ),
        patch(
            "souschef.converters.playbook.safe_read_text",
            side_effect=ValueError("traversal"),
        ),
    ):
        result = generate_playbook_from_recipe("/tmp/recipe.rb")

    assert "Path traversal attempt detected" in result


def test_generate_playbook_from_recipe_with_ai_missing_file() -> None:
    """AI conversion returns missing file error."""
    with (
        patch(
            "souschef.converters.playbook._normalize_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook._get_workspace_root",
            return_value=Path("/tmp"),
        ),
        patch(
            "souschef.converters.playbook._ensure_within_base_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook.safe_exists",
            return_value=False,
        ),
    ):
        result = generate_playbook_from_recipe_with_ai("/tmp/recipe.rb")

    assert "Recipe file does not exist" in result


def test_generate_playbook_from_recipe_with_ai_path_traversal() -> None:
    """AI conversion returns path traversal error."""
    with (
        patch(
            "souschef.converters.playbook._normalize_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook._get_workspace_root",
            return_value=Path("/tmp"),
        ),
        patch(
            "souschef.converters.playbook._ensure_within_base_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook.safe_exists",
            return_value=True,
        ),
        patch(
            "souschef.converters.playbook.safe_read_text",
            side_effect=ValueError("traversal"),
        ),
    ):
        result = generate_playbook_from_recipe_with_ai("/tmp/recipe.rb")

    assert "Path traversal attempt detected" in result


def test_generate_playbook_from_recipe_with_ai_parse_error() -> None:
    """AI conversion returns parse error when parse_recipe fails."""
    with (
        patch(
            "souschef.converters.playbook._normalize_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook._get_workspace_root",
            return_value=Path("/tmp"),
        ),
        patch(
            "souschef.converters.playbook._ensure_within_base_path",
            return_value=Path("/tmp/recipe.rb"),
        ),
        patch(
            "souschef.converters.playbook.safe_exists",
            return_value=True,
        ),
        patch(
            "souschef.converters.playbook.safe_read_text",
            return_value="content",
        ),
        patch(
            "souschef.converters.playbook.parse_recipe",
            return_value="Error: parse failed",
        ),
    ):
        result = generate_playbook_from_recipe_with_ai("/tmp/recipe.rb")

    assert "Error: parse failed" in result
