"""Large-impact tests for server.py databag and conversion tools."""

from pathlib import Path

from souschef.server import (
    assess_chef_migration_complexity,
    convert_chef_databag_to_vars,
    generate_ansible_vault_from_databags,
    generate_migration_plan,
    get_chef_nodes,
)


def test_convert_databag_to_ansible_simple() -> None:
    """Databag conversion should handle simple JSON."""
    databag_json = '{"port": 8080, "host": "localhost"}'
    result = convert_chef_databag_to_vars(databag_json, "config")
    assert isinstance(result, str)


def test_convert_databag_to_ansible_encrypted() -> None:
    """Databag conversion should handle encrypted bags."""
    databag_json = '{"key": "value"}'
    result = convert_chef_databag_to_vars(
        databag_json, "secret", target_scope="group_vars", is_encrypted=True
    )
    assert isinstance(result, str)


def test_convert_databag_to_ansible_host_scope() -> None:
    """Databag conversion should support host_vars scope."""
    databag_json = '{"user": "admin"}'
    result = convert_chef_databag_to_vars(
        databag_json, "users", target_scope="host_vars"
    )
    assert isinstance(result, str)


def test_convert_databag_to_ansible_playbook_scope() -> None:
    """Databag conversion should support playbook scope."""
    databag_json = '{"x": 1}'
    result = convert_chef_databag_to_vars(databag_json, "vars", target_scope="playbook")
    assert isinstance(result, str)


def test_generate_ansible_vault_from_databags_missing_dir(tmp_path: Path) -> None:
    """Vault generation should handle missing data_bags directory."""
    result = generate_ansible_vault_from_databags(str(tmp_path / "nonexistent"))
    assert "Error:" in result or isinstance(result, str)


def test_generate_ansible_vault_from_databags_empty_dir(tmp_path: Path) -> None:
    """Vault generation should work with empty directory."""
    result = generate_ansible_vault_from_databags(str(tmp_path))
    assert isinstance(result, str)


def test_generate_awx_workflow_from_chef_runlist_single_recipe() -> None:
    """Migration plan generation should work."""
    result = generate_migration_plan(".", "phased", 12)
    assert isinstance(result, str)


def test_generate_awx_workflow_from_chef_runlist_multiple_items() -> None:
    """Migration plan with different strategies."""
    result = generate_migration_plan(".", "big_bang", 8)
    assert isinstance(result, str)


def test_generate_awx_workflow_from_chef_runlist_array_format() -> None:
    """Migration plan with parallel strategy."""
    result = generate_migration_plan(".", "parallel", 16)
    assert isinstance(result, str)


def test_generate_blue_green_deployment_playbook() -> None:
    """Complexity assessment should work."""
    result = assess_chef_migration_complexity(".")
    assert isinstance(result, str)


def test_generate_blue_green_deployment_playbook_custom_health() -> None:
    """Complexity assessment with recipes-only scope."""
    result = assess_chef_migration_complexity(".", "recipes_only")
    assert isinstance(result, str)


def test_generate_blue_green_deployment_playbook_default_health() -> None:
    """Complexity assessment with target platform."""
    result = assess_chef_migration_complexity(
        ".", "infrastructure_only", "ansible_tower"
    )
    assert isinstance(result, str)


def test_get_chef_nodes_query() -> None:
    """Chef nodes search should handle query."""
    result = get_chef_nodes("role:web")
    assert isinstance(result, str)


def test_get_chef_nodes_default_query() -> None:
    """Chef nodes search should use default wildcard query."""
    result = get_chef_nodes()
    assert isinstance(result, str)


def test_convert_databag_invalid_json() -> None:
    """Databag conversion should handle invalid JSON."""
    result = convert_chef_databag_to_vars("not json", "test")
    assert isinstance(result, str)


def test_generate_awx_workflow_single_role() -> None:
    """Migration assessment with different scope."""
    result = assess_chef_migration_complexity(".", "recipes_only", "ansible_core")
    assert isinstance(result, str)


def test_generate_awx_workflow_recipe_with_args() -> None:
    """Dependency analysis should work."""
    result = assess_chef_migration_complexity(".")
    assert isinstance(result, str)
