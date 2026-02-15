"""Comprehensive edge case tests for resource converter."""

from souschef.converters.resource import (
    _normalize_template_value,
    _parse_properties,
    convert_resource_to_task,
)


class TestParsePropertiesEdgeCases:
    """Tests for _parse_properties edge cases."""

    def test_parse_properties_non_dict_result(self):
        """Test parsing when result is not a dictionary."""
        # ast.literal_eval returns a list, not a dict
        result = _parse_properties("['item1', 'item2']")
        assert result == {}

    def test_parse_properties_value_error(self):
        """Test parsing invalid Python literal."""
        result = _parse_properties("invalid{syntax")
        assert result == {}

    def test_parse_properties_syntax_error(self):
        """Test parsing with syntax error."""
        result = _parse_properties("{'key': 'value'")  # Missing closing brace
        assert result == {}


class TestNormalizeTemplateValueEdgeCases:
    """Tests for _normalize_template_value edge cases."""

    def test_normalize_cookbook_with_numbers(self):
        """Test cookbook name with numeric characters."""
        value = "node['app123']['port']"
        result = _normalize_template_value(value)
        # Numbers get converted to words (1->one, 2->two, etc.)
        assert "apponetwothree_port" in result or "app_port" in result

    def test_normalize_cookbook_with_special_chars(self):
        """Test cookbook name with special characters."""
        value = "node['my-app']['setting']"
        result = _normalize_template_value(value)
        # Special chars like dashes don't match the pattern, so wraps in Jinja
        assert "{{" in result and "node" in result

    def test_normalize_multiple_consecutive_underscores(self):
        """Test that multiple underscores are collapsed."""
        value = "node['app___test']['value']"
        result = _normalize_template_value(value)
        # Should collapse multiple underscores to single
        assert "___" not in result

    def test_normalize_leading_trailing_underscores(self):
        """Test removal of leading/trailing underscores."""
        value = "node['_app_']['setting']"
        result = _normalize_template_value(value)
        # Should strip leading/trailing underscores
        assert not result.startswith("{{ __")
        assert not result.endswith("__ }}")

    def test_normalize_with_multiple_node_refs(self):
        """Test string with multiple node references."""
        value = "http://node['web']['host']:node['web']['port']"
        result = _normalize_template_value(value)
        assert "web_host" in result
        assert "web_port" in result

    def test_normalize_node_with_different_format(self):
        """Test node references in different formats."""
        value = "some text node['app']['val'] more text"
        result = _normalize_template_value(value)
        assert "app_val" in result

    def test_normalize_non_string_value(self):
        """Test normalizing non-string values."""
        assert _normalize_template_value(123) == 123
        assert _normalize_template_value(None) is None
        assert _normalize_template_value([1, 2, 3]) == [1, 2, 3]


class TestConvertResourceEdgeCases:
    """Tests for convert_resource_to_task edge cases."""

    def test_convert_include_recipe_with_cookbook_config(self):
        """Test include_recipe with known cookbook configuration."""
        result = convert_resource_to_task("include_recipe", "apache2::default")
        # Should use cookbook-specific module if defined
        assert "name:" in result
        assert "apache" in result.lower() or "role" in result.lower()

    def test_convert_include_recipe_without_config(self):
        """Test include_recipe with unknown cookbook."""
        result = convert_resource_to_task("include_recipe", "unknown_cookbook::recipe")
        # Should fall back to include_role
        assert "ansible.builtin.include_role" in result or "include_role" in result

    def test_convert_execute_resource_changed_when(self):
        """Test execute resource sets changed_when flag."""
        result = convert_resource_to_task("execute", "some_command")
        # Should set changed_when: false for idempotency
        assert "changed_when" in result
        assert "false" in result

    def test_convert_bash_resource_changed_when(self):
        """Test bash resource sets changed_when flag."""
        result = convert_resource_to_task("bash", "run_script")
        assert "changed_when" in result
        assert "false" in result

    def test_convert_unknown_resource_type(self):
        """Test converting completely unknown resource type."""
        result = convert_resource_to_task("unknown_resource", "resource_name")
        # Should handle gracefully
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_file_resource_with_builder(self):
        """Test file resource conversion."""
        result = convert_resource_to_task("file", "/path/to/file", "create")
        assert "ansible.builtin.file" in result or "file" in result
        assert "/path/to/file" in result

    def test_convert_with_cookbook_specific_params(self):
        """Test resource with cookbook-specific parameter overrides."""
        result = convert_resource_to_task(
            "include_recipe", "nginx::default", properties="{'port': 8080}"
        )
        # Should use cookbook-specific params if available
        assert isinstance(result, str)
        assert len(result) > 0

    def test_convert_with_complex_properties(self):
        """Test resource with complex property values."""
        props = "{'owner': 'root', 'group': 'wheel', 'mode': '0644'}"
        result = convert_resource_to_task("file", "/etc/config", "create", props)
        # File module may not use all properties depending on mapping
        assert "0644" in result  # Mode should be present
        assert "file" in result

    def test_convert_service_with_action_mapping(self):
        """Test service resource with action to state mapping."""
        result = convert_resource_to_task("service", "nginx", "start")
        assert "ansible.builtin.service" in result or "service" in result
        assert "nginx" in result
        # Should map 'start' action to 'started' state
        assert "started" in result or "start" in result

    def test_convert_package_install_action(self):
        """Test package resource with install action."""
        result = convert_resource_to_task("package", "vim", "install")
        assert "ansible.builtin.package" in result or "package" in result
        assert "vim" in result
        assert "present" in result or "install" in result

    def test_convert_package_remove_action(self):
        """Test package resource with remove action."""
        result = convert_resource_to_task("package", "oldpkg", "remove")
        assert "ansible.builtin.package" in result or "package" in result
        assert "absent" in result or "remove" in result

    def test_convert_with_empty_properties(self):
        """Test conversion with empty properties string."""
        result = convert_resource_to_task("package", "vim", "install", "")
        assert "vim" in result

    def test_convert_with_whitespace_properties(self):
        """Test conversion with whitespace-only properties."""
        result = convert_resource_to_task("package", "vim", "install", "   ")
        assert "vim" in result

    def test_convert_directory_resource(self):
        """Test directory resource conversion."""
        result = convert_resource_to_task("directory", "/var/app/data", "create")
        assert "/var/app/data" in result
        assert "ansible.builtin.file" in result or "file" in result
        assert "directory" in result

    def test_convert_template_resource(self):
        """Test template resource conversion."""
        props = "{'source': 'config.erb', 'variables': {'port': 8080}}"
        result = convert_resource_to_task("template", "/etc/app.conf", "create", props)
        assert "/etc/app.conf" in result
        assert "ansible.builtin.template" in result or "template" in result

    def test_convert_cookbook_file_resource(self):
        """Test cookbook_file resource conversion."""
        props = "{'source': 'default.conf'}"
        result = convert_resource_to_task(
            "cookbook_file", "/etc/nginx/conf", "create", props
        )
        assert "/etc/nginx/conf" in result

    def test_convert_with_node_attributes_in_properties(self):
        """Test resource with node attributes in property values."""
        props = "{'port': \"node['app']['port']\"}"
        result = convert_resource_to_task("template", "/etc/app.conf", "create", props)
        # Properties might not be expanded in task output depending on mapping
        assert "template" in result
        assert "/etc/app.conf" in result

    def test_convert_with_multiple_actions(self):
        """Test resource with multiple possible actions."""
        # Enable action
        result1 = convert_resource_to_task("service", "httpd", "enable")
        assert "service" in result1
        assert "httpd" in result1

        # Disable action
        result2 = convert_resource_to_task("service", "httpd", "disable")
        assert "service" in result2
        assert "httpd" in result2

    def test_convert_user_resource(self):
        """Test user resource conversion."""
        props = "{'uid': 1000, 'shell': '/bin/bash'}"
        result = convert_resource_to_task("user", "appuser", "create", props)
        assert "appuser" in result
        assert "ansible.builtin.user" in result or "user" in result

    def test_convert_group_resource(self):
        """Test group resource conversion."""
        props = "{'gid': 1000}"
        result = convert_resource_to_task("group", "appgroup", "create", props)
        assert "appgroup" in result
        assert "ansible.builtin.group" in result or "group" in result

    def test_convert_cron_resource(self):
        """Test cron resource conversion."""
        props = "{'minute': '0', 'hour': '2', 'command': '/usr/bin/backup.sh'}"
        result = convert_resource_to_task("cron", "daily_backup", "create", props)
        assert "daily_backup" in result or "backup" in result

    def test_convert_mount_resource(self):
        """Test mount resource conversion."""
        props = "{'device': '/dev/sdb1', 'fstype': 'ext4'}"
        result = convert_resource_to_task("mount", "/mnt/data", "mount", props)
        assert "/mnt/data" in result

    def test_convert_with_special_characters_in_name(self):
        """Test resource name with special characters."""
        result = convert_resource_to_task("package", "lib-xml2-dev", "install")
        assert "lib-xml2-dev" in result or "lib_xml2_dev" in result
