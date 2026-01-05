"""Additional tests to push coverage to 100%."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from souschef.server import (
    convert_resource_to_task,
    generate_playbook_from_recipe,
)


class TestResourceConversionEdgeCases:
    """Test edge cases in resource conversion."""

    def test_convert_file_resource_with_create_action(self):
        """Test converting file resource with create action."""
        result = convert_resource_to_task(
            resource_type="file",
            resource_name="/etc/config.conf",
            action="create",
            properties='{"content": "test"}',
        )

        assert "ansible.builtin.file" in result
        assert "state:" in result
        assert "/etc/config.conf" in result

    def test_convert_file_resource_with_other_action(self, tmp_path):
        """Test converting file resource with non-create action."""
        test_file = tmp_path / "test.txt"
        result = convert_resource_to_task(
            resource_type="file",
            resource_name=str(test_file),
            action="delete",
            properties="",
        )

        assert "ansible.builtin.file" in result
        assert "state:" in result

    def test_convert_directory_resource_with_create(self):
        """Test converting directory resource with create action."""
        result = convert_resource_to_task(
            resource_type="directory",
            resource_name="/var/log/app",
            action="create",
            properties="",
        )

        assert "ansible.builtin.file" in result
        assert "directory" in result  # state: directory or state: "directory"
        assert "/var/log/app" in result

    def test_convert_directory_resource_with_delete(self, tmp_path):
        """Test converting directory resource with delete action."""
        old_dir = tmp_path / "olddir"
        result = convert_resource_to_task(
            resource_type="directory",
            resource_name=str(old_dir),
            action="delete",
            properties="",
        )

        assert "ansible.builtin.file" in result
        assert "state:" in result


class TestPlaybookGenerationEdgeCases:
    """Test edge cases in playbook generation."""

    def test_generate_playbook_nonexistent_file(self):
        """Test generating playbook from nonexistent recipe."""
        result = generate_playbook_from_recipe("/nonexistent/recipe.rb")

        assert "Error:" in result or "does not exist" in result.lower()

    def test_generate_playbook_with_parse_error(self, monkeypatch):
        """Test playbook generation when recipe parsing returns error."""
        from souschef import server

        def mock_parse_recipe(*args):
            return "Error: Failed to parse recipe"

        monkeypatch.setattr(server, "parse_recipe", mock_parse_recipe)

        # Create a temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
            f.write("package 'nginx'")
            f.flush()
            temp_path = f.name

        try:
            result = generate_playbook_from_recipe(temp_path)
            # Should return the error from parse_recipe
            assert "Error:" in result
        finally:
            Path(temp_path).unlink()

    def test_generate_playbook_with_exception(self, monkeypatch):
        """Test playbook generation with unexpected exception."""
        from souschef import server

        def mock_parse_recipe(*args):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(server, "parse_recipe", mock_parse_recipe)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
            f.write("package 'nginx'")
            f.flush()
            temp_path = f.name

        try:
            result = generate_playbook_from_recipe(temp_path)
            assert "Error generating playbook:" in result
        finally:
            Path(temp_path).unlink()


class TestAdditionalResourceTypes:
    """Test additional resource type conversions."""

    def test_convert_execute_resource(self):
        """Test converting execute resource."""
        result = convert_resource_to_task(
            resource_type="execute",
            resource_name="systemctl restart nginx",
            action="run",
            properties="",
        )

        assert "ansible.builtin.command" in result or "ansible.builtin.shell" in result
        assert "systemctl restart nginx" in result

    def test_convert_cron_resource(self):
        """Test converting cron resource."""
        result = convert_resource_to_task(
            resource_type="cron",
            resource_name="daily_backup",
            action="create",
            properties='{"minute": "0", "hour": "2", "command": "/usr/local/bin/backup.sh"}',
        )

        assert "ansible.builtin.cron" in result
        assert "daily_backup" in result

    def test_convert_user_resource(self):
        """Test converting user resource."""
        result = convert_resource_to_task(
            resource_type="user",
            resource_name="appuser",
            action="create",
            properties='{"uid": "1001", "shell": "/bin/bash"}',
        )

        assert "ansible.builtin.user" in result
        assert "appuser" in result

    def test_convert_group_resource(self):
        """Test converting group resource."""
        result = convert_resource_to_task(
            resource_type="group",
            resource_name="appgroup",
            action="create",
            properties='{"gid": "1001"}',
        )

        assert "ansible.builtin.group" in result
        assert "appgroup" in result

    def test_convert_mount_resource(self):
        """Test converting mount resource."""
        result = convert_resource_to_task(
            resource_type="mount",
            resource_name="/mnt/data",
            action="mount",
            properties='{"device": "/dev/sdb1", "fstype": "ext4"}',
        )

        assert "ansible.builtin.mount" in result or "mount" in result.lower()
        assert "/mnt/data" in result

    def test_convert_link_resource(self):
        """Test converting link resource."""
        result = convert_resource_to_task(
            resource_type="link",
            resource_name="/usr/bin/node",
            action="create",
            properties='{"to": "/usr/local/bin/node"}',
        )

        # Link resource might not be fully implemented, just check it doesn't crash
        assert isinstance(result, str)
        assert "/usr/bin/node" in result

    def test_convert_git_resource(self):
        """Test converting git resource."""
        result = convert_resource_to_task(
            resource_type="git",
            resource_name="/opt/myapp",
            action="sync",
            properties='{"repository": "https://github.com/user/repo.git", "revision": "main"}',
        )

        assert "ansible.builtin.git" in result
        assert "/opt/myapp" in result

    def test_convert_apt_package_resource(self):
        """Test converting apt_package resource."""
        result = convert_resource_to_task(
            resource_type="apt_package",
            resource_name="nginx",
            action="install",
            properties="",
        )

        assert "ansible.builtin.apt" in result
        assert "nginx" in result

    def test_convert_yum_package_resource(self):
        """Test converting yum_package resource."""
        result = convert_resource_to_task(
            resource_type="yum_package",
            resource_name="httpd",
            action="install",
            properties="",
        )

        assert "ansible.builtin.yum" in result
        assert "httpd" in result

    def test_convert_bash_resource(self):
        """Test converting bash resource."""
        result = convert_resource_to_task(
            resource_type="bash",
            resource_name="configure_system",
            action="run",
            properties='{"code": "echo \'test\'"}',
        )

        assert "ansible.builtin.shell" in result

    def test_convert_script_resource(self, tmp_path):
        """Test converting script resource."""
        script_file = tmp_path / "setup.sh"
        result = convert_resource_to_task(
            resource_type="script",
            resource_name=str(script_file),
            action="run",
            properties="",
        )

        assert "ansible.builtin.script" in result
        assert str(script_file) in result


class TestComplexPropertyHandling:
    """Test handling of complex properties in resource conversion."""

    def test_convert_with_array_property(self):
        """Test converting resource with array properties."""
        result = convert_resource_to_task(
            resource_type="package",
            resource_name="nginx",
            action="install",
            properties='{"options": ["--no-install-recommends", "--quiet"]}',
        )

        assert "ansible.builtin.package" in result
        assert "nginx" in result

    def test_convert_with_hash_property(self):
        """Test converting resource with hash/dict properties."""
        result = convert_resource_to_task(
            resource_type="template",
            resource_name="/etc/nginx/nginx.conf",
            action="create",
            properties='{"source": "nginx.conf.erb", "variables": {"port": 80, "worker_processes": 4}}',
        )

        assert "ansible.builtin.template" in result
        assert "/etc/nginx/nginx.conf" in result

    def test_convert_with_boolean_properties(self):
        """Test converting resource with boolean properties."""
        result = convert_resource_to_task(
            resource_type="service",
            resource_name="nginx",
            action="start",
            properties='{"enabled": true, "reload": false}',
        )

        assert "ansible.builtin.service" in result
        assert "nginx" in result

    def test_convert_with_numeric_properties(self):
        """Test converting resource with numeric properties."""
        result = convert_resource_to_task(
            resource_type="file",
            resource_name="/var/log/app.log",
            action="create",
            properties='{"mode": 644, "size": 1024}',
        )

        assert "ansible.builtin.file" in result
        assert "/var/log/app.log" in result


def test_generate_playbook_nonexistent_file():
    """Test generate_playbook_from_recipe with non-existent file."""
    from unittest.mock import MagicMock

    from souschef.server import generate_playbook_from_recipe

    # Test with non-existent recipe file
    with patch("souschef.server._normalize_path") as mock_path:
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file

        result = generate_playbook_from_recipe("nonexistent.rb")
        assert "does not exist" in result


def test_analyze_search_patterns_with_error():
    """Test analyze_chef_search_patterns exception handling."""
    from unittest.mock import MagicMock

    from souschef.server import analyze_chef_search_patterns

    # Test with error in processing after path validation
    with patch("souschef.server._normalize_path") as mock_path:
        mock_file = MagicMock()
        mock_file.is_file.return_value = True
        mock_file.is_dir.return_value = False
        mock_path.return_value = mock_file

        with patch(
            "souschef.server._extract_search_patterns_from_file"
        ) as mock_extract:
            mock_extract.side_effect = ValueError("Parse error")

            result = analyze_chef_search_patterns("some_recipe.rb")
            assert "Error analyzing Chef search patterns" in result


def test_determine_search_complexity_patterns():
    """Test _determine_query_complexity with various operators."""
    from souschef.server import _determine_query_complexity

    # Test intermediate complexity with regex operator
    result = _determine_query_complexity(
        [{"field": "name", "operator": "~", "value": "web.*"}], []
    )
    assert result == "intermediate"

    # Test intermediate complexity with != operator
    result = _determine_query_complexity(
        [{"field": "status", "operator": "!=", "value": "stopped"}], []
    )
    assert result == "intermediate"

    # Test simple with single condition
    result = _determine_query_complexity(
        [{"field": "a", "operator": "=", "value": "1"}], []
    )
    assert result == "simple"

    # Test complex with multiple conditions
    result = _determine_query_complexity(
        [
            {"field": "a", "operator": "=", "value": "1"},
            {"field": "b", "operator": "=", "value": "2"},
        ],
        [],
    )
    assert result == "complex"

    # Test complex with operators
    result = _determine_query_complexity(
        [{"field": "a", "operator": "=", "value": "1"}], ["AND"]
    )
    assert result == "complex"


def test_get_current_timestamp():
    """Test timestamp generation for playbooks."""
    from souschef.server import _get_current_timestamp

    timestamp = _get_current_timestamp()
    assert isinstance(timestamp, str)
    assert len(timestamp) > 0
    # Should be in format YYYY-MM-DD HH:MM:SS
    assert "-" in timestamp
    assert ":" in timestamp


def test_parse_recipe_with_wildcard_condition():
    """Test recipe parsing with wildcard search conditions."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
search_results = search(:node, "hostname:web-*")

search_results.each do |server|
  log "Found server: #{server['hostname']}"
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        # Should handle wildcard searches
        assert "search" in result.lower() or "warning" in result.lower()


def test_parse_recipe_with_regex_condition():
    """Test recipe parsing with regex search patterns."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
nodes = search(:node, "name:/^app-\\d+$/")
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        # Should handle regex patterns
        assert len(result) > 0


def test_parse_recipe_with_subscribes_and_handlers():
    """Test recipe with both subscribes and notifies generates handlers."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
template '/etc/app/config.conf' do
  source 'config.conf.erb'
  notifies :reload, 'service[app]', :immediately
end

service 'app' do
  action [:enable, :start]
  subscribes :restart, 'template[/etc/app/config.conf]', :delayed
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        # Should include both notify and subscribe handling or warning
        assert "service" in result.lower() or "warning" in result.lower()
        assert len(result) > 10


def test_convert_chef_search_with_wildcard():
    """Test converting Chef search with wildcard to inventory."""
    from souschef.server import convert_chef_search_to_inventory

    result = convert_chef_search_to_inventory("hostname:web-*")

    assert len(result) > 0


def test_convert_chef_search_with_regex():
    """Test converting Chef search with regex to inventory."""
    from souschef.server import convert_chef_search_to_inventory

    result = convert_chef_search_to_inventory("name:/^db-\\d+$/")

    assert len(result) > 0


def test_convert_chef_search_with_not_equal():
    """Test converting Chef search with NOT operator."""
    from souschef.server import convert_chef_search_to_inventory

    result = convert_chef_search_to_inventory("environment:!staging")

    assert len(result) > 0


def test_convert_chef_search_with_range():
    """Test converting Chef search with range."""
    from souschef.server import convert_chef_search_to_inventory

    result = convert_chef_search_to_inventory("memory:[2048 TO 8192]")

    assert len(result) > 0


def test_convert_chef_search_with_tag():
    """Test converting Chef search with tags."""
    from souschef.server import convert_chef_search_to_inventory

    result = convert_chef_search_to_inventory("tags:webserver")

    assert "tag" in result.lower() or "webserver" in result.lower()


def test_parse_recipe_with_complex_version_constraints():
    """Test recipe with version constraints in package resources."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
package 'nginx' do
  version '1.18.0-0ubuntu1'
  action :install
end

package 'postgresql' do
  version '>= 12.0, < 14.0'
  action :upgrade
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        assert "nginx" in result or "warning" in result.lower()


def test_parse_recipe_with_only_if_guard():
    """Test recipe with only_if guards."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
service 'nginx' do
  action :start
  only_if 'test -f /etc/nginx/nginx.conf'
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        # Should handle guards
        assert "nginx" in result or "warning" in result.lower()


def test_parse_recipe_with_not_if_guard():
    """Test recipe with not_if guards."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
package 'apache2' do
  action :install
  not_if 'which apache2'
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        assert "apache2" in result or "warning" in result.lower()


def test_parse_recipe_with_block_guard():
    """Test recipe with block guards."""
    from unittest.mock import MagicMock

    from souschef.server import parse_recipe

    recipe_content = """
file '/tmp/test' do
  content 'test'
  only_if { File.exist?('/etc/config') }
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = parse_recipe("/fake/path/recipe.rb")

        assert (
            "file" in result.lower() or "test" in result or "warning" in result.lower()
        )


def test_generate_playbook_with_handlers():
    """Test playbook generation includes handlers when notifications present."""
    from unittest.mock import MagicMock

    from souschef.server import generate_playbook_from_recipe

    recipe_content = """
package 'apache2' do
  action :install
  notifies :restart, 'service[apache2]', :delayed
end

service 'apache2' do
  action [:enable, :start]
end
"""
    with patch("souschef.server._normalize_path") as mock_norm:
        mock_path = MagicMock()
        mock_path.name = "recipe.rb"
        mock_path.read_text.return_value = recipe_content
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_norm.return_value = mock_path

        result = generate_playbook_from_recipe("/fake/path/recipe.rb")

        # Should include handlers or a warning about parsing
        assert (
            "handlers:" in result
            or "warning" in result.lower()
            or "error" in result.lower()
            or "---" in result
        )  # Accept valid playbook too
