"""Integration tests using real files and fixtures."""

from pathlib import Path

import pytest

from souschef.server import (
    convert_resource_to_task,
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_custom_resource,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_COOKBOOK = FIXTURES_DIR / "sample_cookbook"


class TestRealFileOperations:
    """Test actual file operations with real fixtures."""

    def test_read_real_metadata(self):
        """Test reading a real metadata.rb file."""
        result = read_cookbook_metadata(str(SAMPLE_COOKBOOK / "metadata.rb"))

        assert "name: nginx" in result
        assert "maintainer: Chef Software, Inc." in result
        assert "version: 12.0.0" in result
        assert "depends: logrotate, systemd" in result
        assert "supports: ubuntu, debian, centos, redhat" in result

    def test_read_real_recipe(self):
        """Test reading a real recipe file."""
        content = read_file(str(SAMPLE_COOKBOOK / "recipes" / "default.rb"))

        assert isinstance(content, str)
        assert "package 'nginx' do" in content
        assert "service 'nginx' do" in content
        assert "template '/etc/nginx/nginx.conf' do" in content

    def test_parse_real_recipe(self):
        """Test parsing a real recipe with multiple resources."""
        result = parse_recipe(str(SAMPLE_COOKBOOK / "recipes" / "default.rb"))

        # Should find multiple resources
        assert "Resource 1:" in result
        assert "Type: package" in result
        assert "Name: nginx" in result
        assert "Type: service" in result
        assert "Type: template" in result
        assert "Type: directory" in result
        assert "Type: file" in result

    def test_parse_real_attributes(self):
        """Test parsing a real attributes file."""
        result = parse_attributes(str(SAMPLE_COOKBOOK / "attributes" / "default.rb"))

        assert "default[nginx.port] = 80" in result
        assert "default[nginx.ssl_port] = 443" in result
        assert "override[nginx.worker_rlimit_nofile] = 65536" in result
        assert "normal[nginx.server_tokens] = 'off'" in result
        # Test nested attributes
        assert "nginx.ssl.protocols" in result

    def test_list_real_cookbook_structure(self):
        """Test listing a real cookbook structure."""
        result = list_cookbook_structure(str(SAMPLE_COOKBOOK))

        assert "recipes/" in result
        assert "default.rb" in result
        assert "attributes/" in result
        assert "metadata/" in result
        assert "metadata.rb" in result

    def test_list_real_directory(self):
        """Test listing a real directory."""
        result = list_directory(str(SAMPLE_COOKBOOK))

        assert isinstance(result, list)
        assert "metadata.rb" in result
        assert "recipes" in result
        assert "attributes" in result


@pytest.mark.parametrize(
    "invalid_path",
    [
        "/nonexistent/path",
        str(FIXTURES_DIR / "does_not_exist"),
    ],
)
def test_invalid_paths(invalid_path):
    """Test that invalid paths return error messages."""
    result = read_file(invalid_path)
    assert isinstance(result, str)
    assert "Error:" in result or "An error occurred:" in result


@pytest.mark.parametrize(
    "file_path,expected_content",
    [
        ("metadata.rb", "name 'nginx'"),
        ("recipes/default.rb", "package 'nginx'"),
        ("attributes/default.rb", "default['nginx']['port']"),
    ],
)
def test_read_various_files(file_path, expected_content):
    """Test reading various file types from the cookbook."""
    full_path = SAMPLE_COOKBOOK / file_path
    content = read_file(str(full_path))

    assert isinstance(content, str)
    assert expected_content in content


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_directory(self, tmp_path):
        """Test listing an empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = list_directory(str(empty_dir))
        assert result == []

    def test_directory_with_hidden_files(self, tmp_path):
        """Test listing directory with hidden files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / ".hidden").write_text("hidden")
        (test_dir / "visible.txt").write_text("visible")

        result = list_directory(str(test_dir))
        assert ".hidden" in result
        assert "visible.txt" in result

    def test_recipe_with_no_resources(self, tmp_path):
        """Test parsing a recipe file with only comments."""
        recipe_file = tmp_path / "empty.rb"
        recipe_file.write_text("# Only comments\n# No resources here\n")

        result = parse_recipe(str(recipe_file))
        assert "Warning: No Chef resources found" in result

    def test_attributes_with_no_attributes(self, tmp_path):
        """Test parsing an attributes file with no attributes."""
        attr_file = tmp_path / "empty.rb"
        attr_file.write_text("# Only comments\n")

        result = parse_attributes(str(attr_file))
        assert "Warning: No attributes found" in result

    def test_cookbook_with_no_structure(self, tmp_path):
        """Test a directory that's not a cookbook."""
        not_cookbook = tmp_path / "not_cookbook"
        not_cookbook.mkdir()

        result = list_cookbook_structure(str(not_cookbook))
        assert "Warning: No standard cookbook structure found" in result


class TestAttributeParsing:
    """Test various attribute declaration patterns."""

    @pytest.mark.parametrize(
        "attr_line,expected_in_result",
        [
            ("default['nginx']['port'] = 80", "nginx.port"),
            ("override['app']['timeout'] = 30", "app.timeout"),
            ("normal['service']['name'] = 'web'", "service.name"),
            ("default['deep']['nested']['attr'] = 'value'", "deep.nested.attr"),
        ],
    )
    def test_various_attribute_patterns(self, tmp_path, attr_line, expected_in_result):
        """Test parsing different attribute declaration patterns."""
        attr_file = tmp_path / "test.rb"
        attr_file.write_text(attr_line)

        result = parse_attributes(str(attr_file))
        assert expected_in_result in result


class TestRecipeParsing:
    """Test various recipe resource patterns."""

    @pytest.mark.parametrize(
        "resource_type",
        [
            "package",
            "service",
            "template",
            "file",
            "directory",
            "execute",
            "user",
            "group",
        ],
    )
    def test_various_resource_types(self, tmp_path, resource_type):
        """Test parsing different Chef resource types."""
        recipe_file = tmp_path / "test.rb"
        recipe_content = f"{resource_type} 'test_resource' do\n  action :create\nend\n"
        recipe_file.write_text(recipe_content)

        result = parse_recipe(str(recipe_file))
        assert f"Type: {resource_type}" in result
        assert "Name: test_resource" in result


def test_benchmark_parse_recipe(benchmark):
    """Benchmark recipe parsing performance."""
    recipe_path = str(SAMPLE_COOKBOOK / "recipes" / "default.rb")

    result = benchmark(parse_recipe, recipe_path)

    # Ensure it still works correctly
    assert "Resource 1:" in result


def test_benchmark_parse_attributes(benchmark):
    """Benchmark attribute parsing performance."""
    attr_path = str(SAMPLE_COOKBOOK / "attributes" / "default.rb")

    result = benchmark(parse_attributes, attr_path)

    # Ensure it still works correctly
    assert "nginx.port" in result


class TestChefToAnsibleConversion:
    """Test Chef to Ansible conversion with various resource types."""

    @pytest.mark.parametrize(
        "resource_type,resource_name,action,expected_module",
        [
            ("package", "nginx", "install", "ansible.builtin.package"),
            ("service", "nginx", "start", "ansible.builtin.service"),
            ("file", "/etc/config", "create", "ansible.builtin.file"),
            ("directory", "/var/www", "create", "ansible.builtin.file"),
            ("template", "app.conf.erb", "create", "ansible.builtin.template"),
            ("execute", "systemctl daemon-reload", "run", "ansible.builtin.command"),
            ("user", "appuser", "create", "ansible.builtin.user"),
            ("group", "appgroup", "create", "ansible.builtin.group"),
        ],
    )
    def test_convert_various_resources(
        self, resource_type, resource_name, action, expected_module
    ):
        """Test conversion of various Chef resource types."""
        result = convert_resource_to_task(resource_type, resource_name, action)

        assert expected_module in result
        assert resource_name in result
        assert "name:" in result

    def test_convert_package_preserves_action_semantics(self):
        """Test that package actions map correctly to Ansible states."""
        # Install → present
        result = convert_resource_to_task("package", "nginx", "install")
        assert 'state: "present"' in result

        # Upgrade → latest
        result = convert_resource_to_task("package", "nginx", "upgrade")
        assert 'state: "latest"' in result

        # Remove → absent
        result = convert_resource_to_task("package", "nginx", "remove")
        assert 'state: "absent"' in result

    def test_convert_service_handles_multiple_actions(self):
        """Test that service actions include both enabled and state."""
        # Start should enable and start
        result = convert_resource_to_task("service", "nginx", "start")
        assert "enabled: true" in result
        assert 'state: "started"' in result

        # Stop should disable and stop
        result = convert_resource_to_task("service", "nginx", "stop")
        assert "enabled: false" in result
        assert 'state: "stopped"' in result

        # Restart
        result = convert_resource_to_task("service", "nginx", "restart")
        assert 'state: "restarted"' in result

    def test_convert_template_strips_erb_extension(self):
        """Test that .erb extension is removed from template dest."""
        result = convert_resource_to_task("template", "nginx.conf.erb", "create")

        assert 'src: "nginx.conf.erb"' in result
        assert 'dest: "nginx.conf"' in result

    def test_convert_directory_sets_correct_state(self):
        """Test that directory resources set state to directory."""
        result = convert_resource_to_task("directory", "/var/www/html", "create")

        assert 'state: "directory"' in result
        assert 'path: "/var/www/html"' in result

    def test_convert_execute_adds_changed_when(self):
        """Test that execute resources include changed_when for idempotency."""
        result = convert_resource_to_task("execute", "echo test", "run")

        assert "ansible.builtin.command:" in result
        assert 'changed_when: "false"' in result

    def test_conversion_produces_valid_yaml_structure(self):
        """Test that converted tasks have valid YAML structure."""
        result = convert_resource_to_task("package", "nginx", "install")

        # Should start with task name
        assert result.startswith("- name:")

        # Should have module definition
        assert "  ansible.builtin.package:" in result

        # Should have indented parameters
        assert '    name: "nginx"' in result or "    name:" in result


def test_benchmark_conversion(benchmark):
    """Benchmark Chef to Ansible conversion performance."""
    result = benchmark(convert_resource_to_task, "package", "nginx", "install")

    # Ensure it still works correctly
    assert "ansible.builtin.package" in result


class TestTemplateParsingIntegration:
    """Integration tests for ERB template parsing."""

    def test_parse_simple_template(self):
        """Test parsing a simple ERB template."""
        template_path = SAMPLE_COOKBOOK / "templates" / "default" / "simple.txt.erb"
        result = parse_template(str(template_path))

        # Should return valid JSON
        import json

        data = json.loads(result)

        assert "variables" in data
        assert "jinja2_template" in data
        assert "original_file" in data

        # Should extract variables
        assert "username" in data["variables"]
        assert "email" in data["variables"]
        assert "role" in data["variables"]
        assert "premium" in data["variables"]

        # Should convert to Jinja2
        jinja2 = data["jinja2_template"]
        assert "{{ username }}" in jinja2
        assert "{{ email }}" in jinja2
        assert "{% if premium %}" in jinja2
        assert "{% endif %}" in jinja2

    def test_parse_nginx_config_template(self):
        """Test parsing nginx configuration ERB template."""
        template_path = SAMPLE_COOKBOOK / "templates" / "default" / "nginx.conf.erb"
        result = parse_template(str(template_path))

        import json

        data = json.loads(result)

        # Should extract node attributes as variables
        variables = data["variables"]
        assert "nginx']['port" in variables
        assert "nginx']['server_name" in variables
        assert "nginx']['ssl_enabled" in variables

        # Should convert conditionals
        jinja2 = data["jinja2_template"]
        assert "{% if " in jinja2
        assert "{% endif %}" in jinja2
        assert "{% if not " in jinja2  # unless converted to if not

    def test_parse_config_yaml_template(self):
        """Test parsing config YAML ERB template with loops."""
        template_path = SAMPLE_COOKBOOK / "templates" / "default" / "config.yml.erb"
        result = parse_template(str(template_path))

        import json

        data = json.loads(result)

        # Should extract variables
        variables = data["variables"]
        assert "app_name" in variables
        assert "version" in variables
        assert "environment" in variables
        assert "feature" in variables  # From loop iterator

        # Should convert each loop to for
        jinja2 = data["jinja2_template"]
        assert "{% for feature in " in jinja2
        assert "{% endfor %}" in jinja2

        # Should convert elsif to elif
        assert "{% elif " in jinja2

    @pytest.mark.parametrize(
        "template_name,expected_vars",
        [
            ("simple.txt.erb", ["username", "email", "role", "premium"]),
            (
                "nginx.conf.erb",
                [
                    "nginx']['port",
                    "nginx']['server_name",
                    "nginx']['ssl_enabled",
                ],
            ),
            ("config.yml.erb", ["app_name", "version", "environment"]),
        ],
    )
    def test_parse_templates_extract_variables(self, template_name, expected_vars):
        """Test that all templates extract expected variables."""
        template_path = SAMPLE_COOKBOOK / "templates" / "default" / template_name
        result = parse_template(str(template_path))

        import json

        data = json.loads(result)
        variables = data["variables"]

        for var in expected_vars:
            assert var in variables, f"Expected variable '{var}' not found"

    @pytest.mark.parametrize(
        "template_name,erb_pattern,jinja2_pattern",
        [
            ("simple.txt.erb", "<%=", "{{"),
            ("nginx.conf.erb", "<% if", "{% if"),
            ("nginx.conf.erb", "<% unless", "{% if not"),
            ("config.yml.erb", ".each do", "{% for"),
            ("config.yml.erb", "<% elsif", "{% elif"),
        ],
    )
    def test_erb_to_jinja2_conversion(self, template_name, erb_pattern, jinja2_pattern):
        """Test ERB patterns are converted to Jinja2."""
        template_path = SAMPLE_COOKBOOK / "templates" / "default" / template_name
        result = parse_template(str(template_path))

        import json

        data = json.loads(result)
        jinja2 = data["jinja2_template"]

        # ERB pattern should be gone
        assert erb_pattern not in jinja2 or erb_pattern.startswith(".each")

        # Jinja2 pattern should be present
        assert jinja2_pattern in jinja2

    def test_template_not_found(self):
        """Test parsing non-existent template."""
        result = parse_template("/nonexistent/template.erb")

        assert "Error: File not found" in result

    def test_parse_template_preserves_content(self):
        """Test that non-ERB content is preserved during conversion."""
        template_path = SAMPLE_COOKBOOK / "templates" / "default" / "simple.txt.erb"
        result = parse_template(str(template_path))

        import json

        data = json.loads(result)
        jinja2 = data["jinja2_template"]

        # Static content should be preserved
        assert "Hello" in jinja2
        assert "Your settings:" in jinja2
        assert "Email:" in jinja2
        assert "Role:" in jinja2
        assert "Premium features enabled!" in jinja2


def test_benchmark_template_parsing(benchmark):
    """Benchmark ERB template parsing performance."""
    template_path = SAMPLE_COOKBOOK / "templates" / "default" / "nginx.conf.erb"

    result = benchmark(parse_template, str(template_path))

    # Ensure it still works correctly
    import json

    data = json.loads(result)
    assert "variables" in data
    assert "jinja2_template" in data


class TestCustomResourceParsing:
    """Test parsing custom resources and LWRPs."""

    @pytest.mark.parametrize(
        "resource_file,expected_name,expected_type",
        [
            ("app_config.rb", "app_config", "custom_resource"),
            ("database.rb", "database", "lwrp"),
            ("simple.rb", "simple", "custom_resource"),
        ],
    )
    def test_parse_custom_resource_types(
        self, resource_file, expected_name, expected_type
    ):
        """Test parsing different custom resource types."""
        resource_path = SAMPLE_COOKBOOK / "resources" / resource_file
        result = parse_custom_resource(str(resource_path))

        import json

        data = json.loads(result)

        assert data["resource_name"] == expected_name
        assert data["resource_type"] == expected_type

    def test_parse_app_config_resource(self):
        """Test parsing app_config.rb with modern properties."""
        resource_path = SAMPLE_COOKBOOK / "resources" / "app_config.rb"
        result = parse_custom_resource(str(resource_path))

        import json

        data = json.loads(result)

        # Check basic metadata
        assert data["resource_name"] == "app_config"
        assert data["resource_type"] == "custom_resource"
        assert data["resource_file"] == str(resource_path)

        # Check properties
        properties = data["properties"]
        assert len(properties) == 6

        # Find specific properties
        config_name = next(p for p in properties if p["name"] == "config_name")
        assert config_name["type"] == "String"
        assert config_name.get("name_property") is True

        port = next(p for p in properties if p["name"] == "port")
        assert port["type"] == "Integer"
        assert port["default"] == "8080"

        ssl_enabled = next(p for p in properties if p["name"] == "ssl_enabled")
        assert ssl_enabled["default"] == "false"

        # Check actions
        assert "create" in data["actions"]
        assert "delete" in data["actions"]
        assert data["default_action"] == "create"

    def test_parse_database_lwrp(self):
        """Test parsing database.rb LWRP resource."""
        resource_path = SAMPLE_COOKBOOK / "resources" / "database.rb"
        result = parse_custom_resource(str(resource_path))

        import json

        data = json.loads(result)

        # Check LWRP metadata
        assert data["resource_name"] == "database"
        assert data["resource_type"] == "lwrp"

        # Check attributes (LWRP style)
        properties = data["properties"]
        assert len(properties) == 6

        # Find specific attributes
        db_name = next(p for p in properties if p["name"] == "db_name")
        assert db_name["type"] == "String"
        assert db_name.get("name_property") is True

        port = next(p for p in properties if p["name"] == "port")
        assert port["type"] == "Integer"
        assert port["default"] == "5432"

        username = next(p for p in properties if p["name"] == "username")
        assert username.get("required") is True

        # Check actions (LWRP actions declaration)
        assert "create" in data["actions"]
        assert "drop" in data["actions"]
        assert "backup" in data["actions"]
        assert data["default_action"] == "create"

    def test_parse_simple_resource(self):
        """Test parsing simple.rb minimal custom resource."""
        resource_path = SAMPLE_COOKBOOK / "resources" / "simple.rb"
        result = parse_custom_resource(str(resource_path))

        import json

        data = json.loads(result)

        # Check basic structure
        assert data["resource_name"] == "simple"
        assert len(data["properties"]) == 2
        assert len(data["actions"]) == 2
        assert "enable" in data["actions"]
        assert "disable" in data["actions"]

    def test_parse_custom_resource_with_provider(self):
        """Test that provider files exist for LWRPs."""
        provider_path = SAMPLE_COOKBOOK / "providers" / "database.rb"

        # Verify provider file exists
        assert provider_path.exists()

        # Read provider content
        content = read_file(str(provider_path))
        assert "action :create do" in content
        assert "action :drop do" in content
        assert "action :backup do" in content


def test_benchmark_custom_resource_parsing(benchmark):
    """Benchmark custom resource parsing performance."""
    resource_path = SAMPLE_COOKBOOK / "resources" / "app_config.rb"

    result = benchmark(parse_custom_resource, str(resource_path))

    # Ensure it still works correctly
    import json

    data = json.loads(result)
    assert "properties" in data
    assert "actions" in data
    assert data["resource_name"] == "app_config"

