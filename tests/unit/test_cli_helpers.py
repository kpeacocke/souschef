"""Unit tests for CLI helper functions."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from souschef.cli import (
    _display_assessment_text,
    _display_collection_section,
    _display_node_text,
    _display_plan_section,
    _display_recipe_summary,
    _display_resource_summary,
    _display_template_summary,
    _display_upgrade_plan,
    _output_chef_nodes,
    _output_json_format,
    _output_result,
    _output_text_format,
    _resolve_output_path,
    _safe_write_file,
    _validate_user_path,
)


def _capture_echo(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture click.echo output for assertions."""
    messages: list[str] = []

    def fake_echo(message: Any = "", **_kwargs: object) -> None:
        messages.append(str(message))

    monkeypatch.setattr("souschef.cli.click.echo", fake_echo)
    return messages


def test_validate_user_path_defaults_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate user path uses current directory when no input provided."""
    monkeypatch.chdir(tmp_path)

    result = _validate_user_path(None)

    assert result == tmp_path


def test_validate_user_path_rejects_missing_path() -> None:
    """Validate user path raises error for missing paths."""
    with pytest.raises(ValueError, match="Path does not exist"):
        _validate_user_path("/path/does/not/exist")


def test_resolve_output_path_uses_workspace_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolve output path within the configured workspace root."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    default_path = tmp_path / "reports" / "output.txt"

    resolved = _resolve_output_path(None, default_path)

    assert resolved == default_path.resolve()
    assert resolved.parent.exists()


def test_safe_write_file_writes_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Safely write file content to the resolved output path."""
    monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))
    default_path = tmp_path / "out" / "result.txt"

    written_path = _safe_write_file("test-content", None, default_path)

    assert written_path.exists()
    assert written_path.read_text(encoding="utf-8") == "test-content"


def test_output_json_format_handles_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Output JSON format renders parsed JSON when valid."""
    messages = _capture_echo(monkeypatch)

    _output_json_format('{"status": "ok"}')

    assert any('"status"' in message for message in messages)


def test_output_text_format_handles_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Output text format renders dictionaries as key/value pairs."""
    messages = _capture_echo(monkeypatch)

    _output_text_format('{"items": ["one", "two"], "count": 2}')

    assert any(message.startswith("items:") for message in messages)
    assert any("- one" in message for message in messages)
    assert any("count: 2" in message for message in messages)


def test_output_result_respects_json_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """Output result uses JSON formatting when requested."""
    messages = _capture_echo(monkeypatch)

    _output_result('{"ok": true}', "json")

    assert any('"ok"' in message for message in messages)


def test_display_recipe_summary_truncates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Display recipe summary truncates long output."""
    messages = _capture_echo(monkeypatch)
    recipe_file = tmp_path / "recipe.rb"
    recipe_file.write_text("package 'nginx' do\n  action :install\nend")

    recipe_output = "\n".join([f"line {i}" for i in range(15)])
    with patch("souschef.cli.parse_recipe", return_value=recipe_output):
        _display_recipe_summary(recipe_file)

    assert any("more lines" in message for message in messages)


def test_display_resource_summary_handles_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Display resource summary formats JSON content."""
    messages = _capture_echo(monkeypatch)
    resource_file = tmp_path / "resource.rb"
    resource_file.write_text("property :name, String")

    resource_json = """
    {"resource_type": "custom_resource", "properties": [1], "actions": ["create"]}
    """
    with patch("souschef.cli.parse_custom_resource", return_value=resource_json):
        _display_resource_summary(resource_file)

    assert any("Type: custom_resource" in message for message in messages)
    assert any("Properties" in message for message in messages)
    assert any("Actions" in message for message in messages)


def test_display_resource_summary_handles_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Display resource summary falls back to raw output on invalid JSON."""
    messages = _capture_echo(monkeypatch)
    resource_file = tmp_path / "resource.rb"
    resource_file.write_text("property :name, String")

    with patch("souschef.cli.parse_custom_resource", return_value="not-json"):
        _display_resource_summary(resource_file)

    assert any("not-json" in message for message in messages)


def test_display_template_summary_handles_variable_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Display template summary shows variable counts and samples."""
    messages = _capture_echo(monkeypatch)
    template_file = tmp_path / "template.erb"
    template_file.write_text("<%= @name %>")

    template_json = '{"variables": ["a", "b", "c", "d", "e", "f"]}'
    with patch("souschef.cli.parse_template", return_value=template_json):
        _display_template_summary(template_file)

    assert any("Variables: 6" in message for message in messages)
    assert any("and 1 more" in message for message in messages)


def test_display_assessment_text_outputs_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Display assessment output prints the expected fields."""
    messages = _capture_echo(monkeypatch)
    analysis = {
        "complexity": "Low",
        "recipe_count": 1,
        "resource_count": 2,
        "estimated_hours": 3.0,
        "recommendations": "All good",
    }

    _display_assessment_text("example", analysis)

    assert any("Complexity: Low" in message for message in messages)
    assert any("Recipe Count" in message for message in messages)
    assert any("Resource Count" in message for message in messages)


def test_display_node_text_outputs_optional_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Display node text includes optional fields when present."""
    messages = _capture_echo(monkeypatch)
    node = {
        "name": "node-1",
        "environment": "prod",
        "platform": "ubuntu",
        "ipaddress": "10.0.0.1",  # NOSONAR - test fixture
        "fqdn": "node.example.com",
        "roles": ["web"],
    }

    _display_node_text(node)

    assert any("Environment" in message for message in messages)
    assert any("IP" in message for message in messages)
    assert any("Roles" in message for message in messages)


def test_output_chef_nodes_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Output chef nodes returns JSON when requested."""
    messages = _capture_echo(monkeypatch)

    _output_chef_nodes([{"name": "node-1"}], output_json=True)

    assert any("node-1" in message for message in messages)


def test_output_chef_nodes_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Output chef nodes uses text display when requested."""
    messages = _capture_echo(monkeypatch)

    with patch("souschef.cli._display_node_text") as mock_display:
        _output_chef_nodes([{"name": "node-1"}], output_json=False)

    mock_display.assert_called_once()
    assert not messages


def test_display_plan_section_limits_items(monkeypatch: pytest.MonkeyPatch) -> None:
    """Display plan section truncates long item lists."""
    messages = _capture_echo(monkeypatch)

    _display_plan_section("Breaking Changes", [str(i) for i in range(8)], "-")

    assert any("Breaking Changes" in message for message in messages)
    assert any("and 3 more" in message for message in messages)


def test_display_upgrade_plan_outputs_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    """Display upgrade plan renders details from upgrade path data."""
    messages = _capture_echo(monkeypatch)
    plan = {
        "upgrade_path": {
            "from_version": "2.9",
            "to_version": "2.15",
            "intermediate_versions": ["2.10"],
            "breaking_changes": ["Change 1"],
            "collection_updates_needed": {"example.collection": "1.0.0"},
            "estimated_effort_days": 5,
        }
    }

    _display_upgrade_plan(plan)

    assert any("Upgrade Path" in message for message in messages)
    assert any("Intermediate Versions" in message for message in messages)
    assert any("Estimated Effort" in message for message in messages)


def test_display_collection_section_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Display collection section truncates output when long."""
    messages = _capture_echo(monkeypatch)

    _display_collection_section("Compatible Collections", [str(i) for i in range(7)])

    assert any("Compatible Collections" in message for message in messages)
    assert any("and 2 more" in message for message in messages)


def test_display_collection_section_ignores_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Display collection section skips empty lists."""
    messages = _capture_echo(monkeypatch)

    _display_collection_section("Compatible Collections", [])

    assert messages == []
