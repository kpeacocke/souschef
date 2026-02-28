"""Tests for handler routing configuration generation."""

import json
from pathlib import Path
from unittest.mock import patch

from souschef.server import generate_handler_routing_config


def test_generate_handler_routing_config_yaml(tmp_path: Path) -> None:
    """Generate handler routing config in YAML format."""
    cookbook_dir = tmp_path / "cookbook"
    libraries_dir = cookbook_dir / "libraries"
    recipes_dir = cookbook_dir / "recipes"
    libraries_dir.mkdir(parents=True)
    recipes_dir.mkdir(parents=True)

    (libraries_dir / "handler.rb").write_text("handler")
    (recipes_dir / "default.rb").write_text("recipe")

    routing = {
        "event_routes": {"on_fail": {"listener": "handler"}},
        "summary": {"total_patterns": 1},
    }

    with (
        patch(
            "souschef.server._normalise_workspace_path",
            return_value=cookbook_dir,
        ),
        patch(
            "souschef.converters.detect_handler_patterns",
            return_value=[{"pattern": "exception_handler_registration"}],
        ),
        patch(
            "souschef.converters.build_handler_routing_table",
            return_value=routing,
        ),
    ):
        result = generate_handler_routing_config(str(cookbook_dir))

    data = json.loads(result)
    assert data["status"] == "success"
    assert data["handlers_found"] == 2
    assert "handlers:" in data["routing_config"]
    assert "on_fail" in data["routing_config"]


def test_generate_handler_routing_config_json(tmp_path: Path) -> None:
    """Generate handler routing config in JSON format."""
    cookbook_dir = tmp_path / "cookbook"
    cookbook_dir.mkdir()

    routing = {
        "event_routes": {"on_fail": {"listener": "handler"}},
        "summary": {"total_patterns": 2},
    }

    with (
        patch(
            "souschef.server._normalise_workspace_path",
            return_value=cookbook_dir,
        ),
        patch(
            "souschef.converters.detect_handler_patterns",
            return_value=[{"pattern": "exception_handler_registration"}],
        ),
        patch(
            "souschef.converters.build_handler_routing_table",
            return_value=routing,
        ),
    ):
        result = generate_handler_routing_config(
            str(cookbook_dir),
            output_format="json",
        )

    data = json.loads(result)
    assert data["status"] == "success"
    assert "event_routes" in data["routing_config"]


def test_generate_handler_routing_config_invalid_path(tmp_path: Path) -> None:
    """Error when path is not a directory."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("not a directory")

    with patch(
        "souschef.server._normalise_workspace_path",
        return_value=file_path,
    ):
        result = generate_handler_routing_config(str(file_path))

    data = json.loads(result)
    assert data["status"] == "error"
    assert "Cookbook path must be a directory" in data["error"]
