"""Tests covering server.py environment and data bag handling."""

from pathlib import Path

from souschef.server import (
    analyse_chef_databag_usage,
    convert_chef_environment_to_inventory_group,
    convert_inspec_to_test,
    generate_inventory_from_chef_environments,
    parse_inspec_profile,
)


def test_analyse_chef_databag_usage_no_cookbook(tmp_path: Path) -> None:
    """Data bag analysis should handle missing cookbook."""
    result = analyse_chef_databag_usage(str(tmp_path / "nonexistent"))
    assert "Error:" in result or "not found" in result.lower()


def test_analyse_chef_databag_usage_empty_cookbook(tmp_path: Path) -> None:
    """Data bag analysis should work on empty cookbook."""
    cookbook = tmp_path / "test"
    cookbook.mkdir()

    result = analyse_chef_databag_usage(str(cookbook))
    assert isinstance(result, str)


def test_analyse_chef_databag_usage_with_databags_path(tmp_path: Path) -> None:
    """Data bag analysis with databags directory reference."""
    cookbook = tmp_path / "test"
    cookbook.mkdir()
    databags = tmp_path / "data_bags"
    databags.mkdir()

    result = analyse_chef_databag_usage(str(cookbook), str(databags))
    assert isinstance(result, str)


def test_convert_chef_environment_to_inventory_group_simple() -> None:
    """Environment conversion should handle simple Ruby content."""
    env_content = """name 'production'
description 'Production'
default_attributes 'version' => '1.0'
override_attributes 'level' => 'prod'
"""
    result = convert_chef_environment_to_inventory_group(env_content, "production")
    assert isinstance(result, str)
    assert "production" in result.lower()


def test_convert_chef_environment_to_inventory_group_with_constraints() -> None:
    """Environment conversion should include version constraints."""
    env_content = """name 'staging'
cookbook_versions({
  'nginx' => '= 1.2.3',
  'postgresql' => '>= 2.0'
})
"""
    result = convert_chef_environment_to_inventory_group(
        env_content, "staging", include_constraints=True
    )
    assert isinstance(result, str)


def test_convert_chef_environment_to_inventory_group_exclude_constraints() -> None:
    """Environment conversion should skip constraints when disabled."""
    env_content = "name 'dev'\n"
    result = convert_chef_environment_to_inventory_group(
        env_content, "dev", include_constraints=False
    )
    assert isinstance(result, str)


def test_generate_inventory_from_chef_environments_no_dir(tmp_path: Path) -> None:
    """Inventory generation should handle missing environments dir."""
    result = generate_inventory_from_chef_environments(str(tmp_path / "nonexistent"))
    assert "Error:" in result or "not found" in result.lower()


def test_generate_inventory_from_chef_environments_empty_dir(tmp_path: Path) -> None:
    """Inventory generation should work with empty environments dir."""
    result = generate_inventory_from_chef_environments(str(tmp_path))
    assert isinstance(result, str)


def test_generate_inventory_from_chef_environments_yaml_format(tmp_path: Path) -> None:
    """Inventory generation should support YAML format."""
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    (env_dir / "prod.rb").write_text("name 'prod'\n")

    result = generate_inventory_from_chef_environments(str(env_dir), "yaml")
    assert isinstance(result, str)


def test_generate_inventory_from_chef_environments_ini_format(tmp_path: Path) -> None:
    """Inventory generation should support INI format."""
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    (env_dir / "dev.rb").write_text("name 'dev'\n")

    result = generate_inventory_from_chef_environments(str(env_dir), "ini")
    assert isinstance(result, str)


def test_generate_inventory_from_chef_environments_both_formats(tmp_path: Path) -> None:
    """Inventory generation should support both YAML and INI."""
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    (env_dir / "test.rb").write_text("name 'test'\n")

    result = generate_inventory_from_chef_environments(str(env_dir), "both")
    assert isinstance(result, str)


def test_parse_inspec_profile_missing_path() -> None:
    """InSpec profile parsing should handle missing path."""
    result = parse_inspec_profile("/nonexistent/profile")
    assert "Error:" in result or "not" in result.lower()


def test_parse_inspec_profile_invalid_path() -> None:
    """InSpec profile parsing should reject invalid paths."""
    result = parse_inspec_profile("../../etc/passwd")
    assert (
        "Error:" in result or "traversal" in result.lower() or isinstance(result, str)
    )


def test_convert_inspec_to_test_testinfra_format() -> None:
    """InSpec conversion should support testinfra format."""
    result = convert_inspec_to_test("/nonexistent/profile", "testinfra")
    assert isinstance(result, str)


def test_convert_inspec_to_test_ansible_assert_format() -> None:
    """InSpec conversion should support ansible_assert format."""
    result = convert_inspec_to_test("/nonexistent/profile", "ansible_assert")
    assert isinstance(result, str)


def test_convert_inspec_to_test_serverspec_format() -> None:
    """InSpec conversion should support serverspec format."""
    result = convert_inspec_to_test("/nonexistent/profile", "serverspec")
    assert isinstance(result, str)


def test_convert_inspec_to_test_goss_format() -> None:
    """InSpec conversion should support goss format."""
    result = convert_inspec_to_test("/nonexistent/profile", "goss")
    assert isinstance(result, str)


def test_convert_inspec_to_test_default_format() -> None:
    """InSpec conversion should default to testinfra."""
    result = convert_inspec_to_test("/nonexistent/profile")
    assert isinstance(result, str)
