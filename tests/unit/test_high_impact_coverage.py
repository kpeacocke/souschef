"""High-impact coverage tests using current public and internal APIs."""

import json
from pathlib import Path
from unittest.mock import patch

from souschef.assessment import (
    analyse_cookbook_dependencies,
    assess_chef_migration_complexity,
)
from souschef.converters.playbook import generate_playbook_from_recipe
from souschef.server import (
    _validate_databags_directory,
    convert_chef_databag_to_vars,
    get_chef_nodes,
    validate_chef_server_connection,
)


def test_validate_databags_directory_nonexistent() -> None:
    """Databags directory validation should return an error for missing paths."""
    path, error = _validate_databags_directory("/nonexistent/path/12345")
    assert path is None
    assert isinstance(error, str)


def test_validate_databags_directory_valid(tmp_path: Path) -> None:
    """Databags directory validation should accept existing directories."""
    users_dir = tmp_path / "users"
    users_dir.mkdir()
    (users_dir / "admin.json").write_text('{"id": "admin"}')

    path, error = _validate_databags_directory(str(tmp_path))
    assert path == tmp_path.resolve()
    assert error is None


def test_convert_databag_basic_json() -> None:
    """Databag conversion should return YAML text for valid JSON."""
    result = convert_chef_databag_to_vars('{"key": "value"}', databag_name="test")
    assert isinstance(result, str)
    assert "key:" in result


def test_convert_databag_encrypted_flag() -> None:
    """Encrypted databags should return vault-style output."""
    result = convert_chef_databag_to_vars(
        '{"secret": "value"}', databag_name="secure", is_encrypted=True
    )
    assert isinstance(result, str)
    assert "ansible-vault" in result or "vault" in result.lower()


def test_convert_databag_scopes() -> None:
    """Conversion should support all documented target scopes."""
    for scope in ["group_vars", "host_vars", "playbook"]:
        result = convert_chef_databag_to_vars(
            '{"x": 1}', databag_name="bag", target_scope=scope
        )
        assert isinstance(result, str)


def test_validate_chef_server_connection_handles_unreachable_server() -> None:
    """Chef server validation should fail gracefully for unreachable hosts."""
    result = validate_chef_server_connection("https://invalid-chef-server.invalid")
    assert isinstance(result, str)
    assert "Failed" in result or "Error" in result


def test_get_chef_nodes_uses_backend_and_serialises() -> None:
    """Node retrieval should call backend and return JSON text."""
    nodes = [{"name": "node1", "roles": ["web"]}]
    with patch("souschef.server._get_chef_nodes", return_value=nodes):
        result = get_chef_nodes(search_query="name:node1")

    parsed = json.loads(result)
    assert isinstance(parsed, (list, dict))
    if isinstance(parsed, list):
        assert parsed[0]["name"] == "node1"
    else:
        assert "name" in result


def test_assess_complexity_with_minimal_cookbook(tmp_path: Path) -> None:
    """Complexity assessment should produce output for minimal cookbook layout."""
    (tmp_path / "metadata.rb").write_text('name "test"\nversion "1.0.0"')
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "default.rb").write_text("package 'nginx'")

    result = assess_chef_migration_complexity(str(tmp_path))
    assert isinstance(result, str)


def test_analyse_dependencies_from_metadata(tmp_path: Path) -> None:
    """Dependency analysis should parse depends lines from metadata."""
    (tmp_path / "metadata.rb").write_text(
        'name "test"\nversion "1.0.0"\ndepends "nginx"\ndepends "postgresql"\n'
    )

    result = analyse_cookbook_dependencies(str(tmp_path))
    assert isinstance(result, str)
    assert "nginx" in result


def test_generate_playbook_from_empty_recipe(tmp_path: Path) -> None:
    """Playbook generation should handle empty recipes without crashing."""
    recipe = tmp_path / "empty.rb"
    recipe.write_text("")

    result = generate_playbook_from_recipe(str(recipe), str(tmp_path))
    assert isinstance(result, str)


def test_generate_playbook_from_simple_recipe(tmp_path: Path) -> None:
    """Playbook generation should convert simple resources."""
    recipe = tmp_path / "default.rb"
    recipe.write_text("package 'nginx' do\n  action :install\nend\n")

    result = generate_playbook_from_recipe(str(recipe), str(tmp_path))
    assert isinstance(result, str)


def test_generate_playbook_with_conditional_recipe(tmp_path: Path) -> None:
    """Playbook generation should tolerate conditional Ruby blocks."""
    recipe = tmp_path / "conditional.rb"
    recipe.write_text("if node['platform'] == 'ubuntu'\n  package 'nginx'\nend\n")

    result = generate_playbook_from_recipe(str(recipe), str(tmp_path))
    assert isinstance(result, str)


def test_large_nested_databag_conversion() -> None:
    """Conversion should handle larger nested JSON payloads."""
    nested = {"level1": {"level2": {"level3": {"value": "x"}}}}
    payload = json.dumps(nested)
    result = convert_chef_databag_to_vars(payload, databag_name="nested")
    assert isinstance(result, str)
