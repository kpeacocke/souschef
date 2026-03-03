"""Tests for playbook variable extraction helpers."""

from souschef.converters.playbook import (
    _extract_content_variables,
    _extract_mode_variables,
    _extract_ownership_variables,
    _extract_recipe_variables,
    _extract_version_variable,
)


def test_extract_version_variable_found() -> None:
    """Test version variable extraction when present."""
    content = "package 'nginx' do\n  version '1.2.3'\nend"
    result = _extract_version_variable(content)

    assert result == {"package_version": '"1.2.3"'}


def test_extract_version_variable_missing() -> None:
    """Test version variable extraction when absent."""
    content = "package 'nginx' do\n  action :install\nend"
    result = _extract_version_variable(content)

    assert result == {}


def test_extract_content_variables_content_and_source() -> None:
    """Test content and template source extraction."""
    content = """
    file '/etc/app.conf' do
      content 'value'
    end

    template '/etc/app.conf' do
      source 'app.conf.erb'
    end
    """
    result = _extract_content_variables(content)

    assert result["file_content"] == '"value"'
    assert result["template_source"] == '"app.conf.erb"'


def test_extract_content_variables_missing() -> None:
    """Test content extraction when no matches."""
    content = "package 'nginx' do\n  action :install\nend"
    result = _extract_content_variables(content)

    assert result == {}


def test_extract_ownership_variables_skips_root() -> None:
    """Test owner/group extraction skips root."""
    content = """
    file '/etc/app.conf' do
      owner 'root'
      group 'root'
    end
    """
    result = _extract_ownership_variables(content)

    assert result == {}


def test_extract_ownership_variables_non_root() -> None:
    """Test owner/group extraction for non-root values."""
    content = """
    file '/etc/app.conf' do
      owner 'appuser'
      group 'appgroup'
    end
    """
    result = _extract_ownership_variables(content)

    assert result["file_owner"] == '"appuser"'
    assert result["file_group"] == '"appgroup"'


def test_extract_mode_variables_single() -> None:
    """Test mode extraction for a single mode value."""
    content = "file '/etc/app.conf' do\n  mode '0644'\nend"
    result = _extract_mode_variables(content)

    assert result == {"file_mode": '"0644"'}


def test_extract_mode_variables_multiple() -> None:
    """Test mode extraction for multiple different modes."""
    content = """
    file '/etc/app.conf' do
      mode '0644'
    end
    directory '/etc/app' do
      mode '0755'
    end
    """
    result = _extract_mode_variables(content)

    assert result == {"directory_mode": '"0755"', "file_mode": '"0644"'}


def test_extract_recipe_variables_combined() -> None:
    """Test combined variable extraction from recipe."""
    content = """
    package 'nginx' do
      version '1.2.3'
    end

    file '/etc/app.conf' do
      content 'value'
      owner 'appuser'
      group 'appgroup'
      mode '0644'
    end
    """
    result = _extract_recipe_variables(content)

    assert result["package_version"] == '"1.2.3"'
    assert result["file_content"] == '"value"'
    assert result["file_owner"] == '"appuser"'
    assert result["file_group"] == '"appgroup"'
    assert result["file_mode"] == '"0644"'
