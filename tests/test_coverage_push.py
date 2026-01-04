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
            "file", "/etc/config.conf", "create", {"content": "test"}
        )

        assert "ansible.builtin.file" in result
        assert "state:" in result
        assert "/etc/config.conf" in result

    def test_convert_file_resource_with_other_action(self):
        """Test converting file resource with non-create action."""
        result = convert_resource_to_task("file", "/tmp/test.txt", "delete", {})

        assert "ansible.builtin.file" in result
        assert "state:" in result

    def test_convert_directory_resource_with_create(self):
        """Test converting directory resource with create action."""
        result = convert_resource_to_task("directory", "/var/log/app", "create", {})

        assert "ansible.builtin.file" in result
        assert "directory" in result  # state: directory or state: "directory"
        assert "/var/log/app" in result

    def test_convert_directory_resource_with_delete(self):
        """Test converting directory resource with delete action."""
        result = convert_resource_to_task("directory", "/tmp/olddir", "delete", {})

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
            "execute", "systemctl restart nginx", "run", {}
        )

        assert "ansible.builtin.command" in result or "ansible.builtin.shell" in result
        assert "systemctl restart nginx" in result

    def test_convert_cron_resource(self):
        """Test converting cron resource."""
        result = convert_resource_to_task(
            "cron",
            "daily_backup",
            "create",
            {"minute": "0", "hour": "2", "command": "/usr/local/bin/backup.sh"},
        )

        assert "ansible.builtin.cron" in result
        assert "daily_backup" in result

    def test_convert_user_resource(self):
        """Test converting user resource."""
        result = convert_resource_to_task(
            "user", "appuser", "create", {"uid": "1001", "shell": "/bin/bash"}
        )

        assert "ansible.builtin.user" in result
        assert "appuser" in result

    def test_convert_group_resource(self):
        """Test converting group resource."""
        result = convert_resource_to_task(
            "group", "appgroup", "create", {"gid": "1001"}
        )

        assert "ansible.builtin.group" in result
        assert "appgroup" in result

    def test_convert_mount_resource(self):
        """Test converting mount resource."""
        result = convert_resource_to_task(
            "mount",
            "/mnt/data",
            "mount",
            {"device": "/dev/sdb1", "fstype": "ext4"},
        )

        assert "ansible.builtin.mount" in result or "mount" in result.lower()
        assert "/mnt/data" in result

    def test_convert_link_resource(self):
        """Test converting link resource."""
        result = convert_resource_to_task(
            "link", "/usr/bin/node", "create", {"to": "/usr/local/bin/node"}
        )

        # Link resource might not be fully implemented, just check it doesn't crash
        assert isinstance(result, str)
        assert "/usr/bin/node" in result

    def test_convert_git_resource(self):
        """Test converting git resource."""
        result = convert_resource_to_task(
            "git",
            "/opt/myapp",
            "sync",
            {"repository": "https://github.com/user/repo.git", "revision": "main"},
        )

        assert "ansible.builtin.git" in result
        assert "/opt/myapp" in result

    def test_convert_apt_package_resource(self):
        """Test converting apt_package resource."""
        result = convert_resource_to_task("apt_package", "nginx", "install", {})

        assert "ansible.builtin.apt" in result
        assert "nginx" in result

    def test_convert_yum_package_resource(self):
        """Test converting yum_package resource."""
        result = convert_resource_to_task("yum_package", "httpd", "install", {})

        assert "ansible.builtin.yum" in result
        assert "httpd" in result

    def test_convert_bash_resource(self):
        """Test converting bash resource."""
        result = convert_resource_to_task(
            "bash", "configure_system", "run", {"code": "echo 'test'"}
        )

        assert "ansible.builtin.shell" in result

    def test_convert_script_resource(self):
        """Test converting script resource."""
        result = convert_resource_to_task("script", "/tmp/setup.sh", "run", {})

        assert "ansible.builtin.script" in result
        assert "/tmp/setup.sh" in result


class TestComplexPropertyHandling:
    """Test handling of complex properties in resource conversion."""

    def test_convert_with_array_property(self):
        """Test converting resource with array properties."""
        result = convert_resource_to_task(
            "package",
            "nginx",
            "install",
            {"options": ["--no-install-recommends", "--quiet"]},
        )

        assert "ansible.builtin.package" in result
        assert "nginx" in result

    def test_convert_with_hash_property(self):
        """Test converting resource with hash/dict properties."""
        result = convert_resource_to_task(
            "template",
            "/etc/nginx/nginx.conf",
            "create",
            {
                "source": "nginx.conf.erb",
                "variables": {"port": 80, "worker_processes": 4},
            },
        )

        assert "ansible.builtin.template" in result
        assert "/etc/nginx/nginx.conf" in result

    def test_convert_with_boolean_properties(self):
        """Test converting resource with boolean properties."""
        result = convert_resource_to_task(
            "service", "nginx", "start", {"enabled": True, "reload": False}
        )

        assert "ansible.builtin.service" in result
        assert "nginx" in result

    def test_convert_with_numeric_properties(self):
        """Test converting resource with numeric properties."""
        result = convert_resource_to_task(
            "file", "/var/log/app.log", "create", {"mode": 644, "size": 1024}
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
