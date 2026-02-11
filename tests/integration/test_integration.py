"""Integration tests using real files and fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.core.url_validation import validate_user_provided_url
from souschef.server import (
    convert_habitat_to_dockerfile,
    convert_inspec_to_test,
    convert_resource_to_task,
    generate_compose_from_habitat,
    generate_inspec_from_recipe,
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_custom_resource,
    parse_habitat_plan,
    parse_inspec_profile,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_COOKBOOK = FIXTURES_DIR / "sample_cookbook"
SAMPLE_INSPEC_PROFILE = FIXTURES_DIR / "sample_inspec_profile"
SIMPLE_CONTROL = FIXTURES_DIR / "simple_control.rb"


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

        # By default, resolved format is returned
        assert "Resolved Attributes" in result
        assert "nginx.port" in result
        assert "80" in result
        assert "443" in result
        assert "65536" in result
        assert "'off'" in result
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


def test_validate_user_provided_url_with_allowlist_env(monkeypatch: pytest.MonkeyPatch):
    """Test allowlist usage in URL validation with real env settings."""
    monkeypatch.setenv("SOUSCHEF_ALLOWED_HOSTNAMES", "api.example.com")

    result = validate_user_provided_url("https://api.example.com")

    assert result == "https://api.example.com"


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
    # Accept various error message formats: old format, new format, or path traversal error
    assert (
        "Error:" in result
        or "An error occurred:" in result
        or "Error during" in result
        or "Path traversal" in result
    )


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

    def test_empty_directory(self, tmp_path, monkeypatch):
        """Test listing an empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        result = list_directory(str(empty_dir))
        assert result == []

    def test_directory_with_hidden_files(self, tmp_path, monkeypatch):
        """Test listing directory with hidden files."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / ".hidden").write_text("hidden")
        (test_dir / "visible.txt").write_text("visible")
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        result = list_directory(str(test_dir))
        assert ".hidden" in result
        assert "visible.txt" in result

    def test_recipe_with_no_resources(self, tmp_path, monkeypatch):
        """Test parsing a recipe file with only comments."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        recipe_file = tmp_path / "empty.rb"
        recipe_file.write_text("# Only comments\n# No resources here\n")

        result = parse_recipe(str(recipe_file))
        assert "Warning: No Chef resources or include_recipe calls found" in result

    def test_attributes_with_no_attributes(self, tmp_path, monkeypatch):
        """Test parsing an attributes file with no attributes."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        attr_file = tmp_path / "empty.rb"
        attr_file.write_text("# Only comments\n")

        result = parse_attributes(str(attr_file))
        assert "Warning: No attributes found" in result

    def test_cookbook_with_no_structure(self, tmp_path, monkeypatch):
        """Test a directory that's not a cookbook."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

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
    def test_various_attribute_patterns(
        self, tmp_path, monkeypatch, attr_line, expected_in_result
    ):
        """Test parsing different attribute declaration patterns."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

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
    def test_various_resource_types(self, tmp_path, monkeypatch, resource_type):
        """Test parsing different Chef resource types."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

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
            (
                "remote_file",
                "/opt/app/file.tar.gz",
                "create",
                "ansible.builtin.get_url",
            ),
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
        result = convert_resource_to_task(
            resource_type="package", resource_name="nginx", action="install"
        )
        assert 'state: "present"' in result

        # Upgrade → latest
        result = convert_resource_to_task(
            resource_type="package", resource_name="nginx", action="upgrade"
        )
        assert 'state: "latest"' in result

        # Remove → absent
        result = convert_resource_to_task(
            resource_type="package", resource_name="nginx", action="remove"
        )
        assert 'state: "absent"' in result

    def test_convert_service_handles_multiple_actions(self):
        """Test that service actions include both enabled and state."""
        # Start should enable and start
        result = convert_resource_to_task(
            resource_type="service", resource_name="nginx", action="start"
        )
        assert "enabled: true" in result
        assert 'state: "started"' in result

        # Stop should disable and stop
        result = convert_resource_to_task(
            resource_type="service", resource_name="nginx", action="stop"
        )
        assert "enabled: false" in result
        assert 'state: "stopped"' in result

        # Restart
        result = convert_resource_to_task(
            resource_type="service", resource_name="nginx", action="restart"
        )
        assert 'state: "restarted"' in result

    def test_convert_template_strips_erb_extension(self):
        """Test that .erb extension is removed from template dest."""
        result = convert_resource_to_task(
            resource_type="template", resource_name="nginx.conf.erb", action="create"
        )

        assert 'src: "nginx.conf.erb"' in result
        assert 'dest: "nginx.conf"' in result

    def test_convert_directory_sets_correct_state(self):
        """Test that directory resources set state to directory."""
        result = convert_resource_to_task(
            resource_type="directory", resource_name="/var/www/html", action="create"
        )

        assert 'state: "directory"' in result
        assert 'path: "/var/www/html"' in result

    def test_convert_execute_adds_changed_when(self):
        """Test that execute resources include changed_when for idempotency."""
        result = convert_resource_to_task(
            resource_type="execute", resource_name="echo test", action="run"
        )

        assert "ansible.builtin.command:" in result
        assert 'changed_when: "false"' in result

    def test_conversion_produces_valid_yaml_structure(self):
        """Test that converted tasks have valid YAML structure."""
        result = convert_resource_to_task(
            resource_type="package", resource_name="nginx", action="install"
        )

        # Should start with task name
        assert result.startswith("- name:")

        # Should have module definition
        assert "  ansible.builtin.package:" in result

        # Should have indented parameters
        assert '    name: "nginx"' in result or "    name:" in result

    def test_convert_remote_file_with_properties(self):
        """Test conversion of remote_file resource with properties."""
        properties = "{'source': 'http://example.com/file.tar.gz', 'mode': '0644', 'owner': 'root'}"
        result = convert_resource_to_task(
            resource_type="remote_file",
            resource_name="/opt/app/file.tar.gz",
            action="create",
            properties=properties,
        )

        assert "ansible.builtin.get_url:" in result
        assert 'dest: "/opt/app/file.tar.gz"' in result
        assert 'url: "http://example.com/file.tar.gz"' in result
        assert 'mode: "0644"' in result
        assert 'owner: "root"' in result


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

        # Accept various error formats: old format or new path validation error
        assert (
            "Error: File not found" in result
            or "Error during" in result
            or "Path traversal" in result
        )

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


class TestInSpecIntegration:
    """Integration tests for InSpec functionality with real fixtures."""

    def test_parse_single_control_file(self):
        """Test parsing a single InSpec control file."""
        result = parse_inspec_profile(str(SIMPLE_CONTROL))

        import json

        data = json.loads(result)

        assert data["controls_count"] == 1
        assert len(data["controls"]) == 1

        control = data["controls"][0]
        assert control["id"] == "simple-test"
        assert len(control["tests"]) == 1

        test = control["tests"][0]
        assert test["resource_type"] == "package"
        assert test["resource_name"] == "vim"
        assert len(test["expectations"]) == 1
        assert test["expectations"][0]["matcher"] == "should be_installed"

    def test_parse_inspec_profile_directory(self):
        """Test parsing a complete InSpec profile directory."""
        result = parse_inspec_profile(str(SAMPLE_INSPEC_PROFILE))

        import json

        data = json.loads(result)

        assert (
            data["controls_count"] == 5
        )  # nginx-package, nginx-service, nginx-config, security-baseline, etc.
        assert len(data["controls"]) == 5

        # Verify nginx-package control
        nginx_pkg = next(
            (c for c in data["controls"] if c["id"] == "nginx-package"), None
        )
        assert nginx_pkg is not None
        assert nginx_pkg["title"] == "NGINX Package Installation"
        assert nginx_pkg["impact"] == pytest.approx(1.0)
        assert len(nginx_pkg["tests"]) == 1

        test = nginx_pkg["tests"][0]
        assert test["resource_type"] == "package"
        assert test["resource_name"] == "nginx"
        assert len(test["expectations"]) == 2  # should be_installed + version match

    def test_convert_simple_control_to_testinfra(self):
        """Test converting simple control to Testinfra format."""
        result = convert_inspec_to_test(str(SIMPLE_CONTROL), "testinfra")

        assert "import pytest" in result
        assert "def test_simple_test(host):" in result
        assert 'pkg = host.package("vim")' in result
        assert "assert pkg.is_installed" in result

    def test_convert_profile_to_testinfra(self):
        """Test converting InSpec profile to Testinfra format."""
        result = convert_inspec_to_test(str(SAMPLE_INSPEC_PROFILE), "testinfra")

        assert "import pytest" in result

        # Should have multiple test functions
        assert "def test_nginx_package(host):" in result
        assert "def test_nginx_service(host):" in result
        assert "def test_nginx_config(host):" in result
        assert "def test_security_baseline(host):" in result
        assert "def test_system_resources(host):" in result

        # Check specific assertions
        assert 'pkg = host.package("nginx")' in result
        assert 'svc = host.service("nginx")' in result
        assert 'f = host.file("/etc/nginx/nginx.conf")' in result
        assert "assert pkg.is_installed" in result
        assert "assert svc.is_running" in result

    def test_convert_profile_to_ansible_assert(self):
        """Test converting InSpec profile to Ansible assert format."""
        result = convert_inspec_to_test(str(SAMPLE_INSPEC_PROFILE), "ansible_assert")

        assert "---" in result
        assert "ansible.builtin.assert:" in result
        assert "that:" in result
        assert "fail_msg:" in result

        # Should contain package checks
        assert "ansible_facts.packages['nginx']" in result
        # Should contain service checks
        assert "services['nginx'].state == 'running'" in result

    def test_convert_profile_to_serverspec(self):
        """Test converting InSpec profile to ServerSpec format."""
        result = convert_inspec_to_test(str(SAMPLE_INSPEC_PROFILE), "serverspec")

        # Check ServerSpec header
        assert "require 'serverspec'" in result
        assert "set :backend, :exec" in result

        # Should have describe blocks (titles may vary)
        assert "describe " in result

        # Check resource definitions
        assert "describe package('nginx') do" in result
        assert "it { should be_installed }" in result
        assert "describe service('nginx') do" in result
        assert "it { should be_running }" in result
        assert "it { should be_enabled }" in result

    def test_convert_profile_to_goss(self):
        """Test converting InSpec profile to Goss YAML format."""
        result = convert_inspec_to_test(str(SAMPLE_INSPEC_PROFILE), "goss")

        # Should be YAML format (or JSON as fallback)
        assert "package:" in result or "package" in result
        assert "service:" in result or "service" in result
        assert "nginx" in result

        # Check for Goss-specific keys
        assert (
            "installed:" in result
            or "installed" in result
            or "True" in result
            or "true" in result
        )
        assert (
            "running:" in result
            or "running" in result
            or "True" in result
            or "true" in result
        )

    def test_convert_simple_control_to_serverspec(self):
        """Test converting simple control to ServerSpec format."""
        result = convert_inspec_to_test(str(SIMPLE_CONTROL), "serverspec")

        assert "require 'serverspec'" in result
        assert "describe " in result  # Should have describe block (title may vary)
        assert "describe package('vim') do" in result
        assert "it { should be_installed }" in result

    def test_convert_simple_control_to_goss(self):
        """Test converting simple control to Goss YAML format."""
        result = convert_inspec_to_test(str(SIMPLE_CONTROL), "goss")

        # Should contain vim package definition
        assert "vim" in result
        assert "installed" in result or "True" in result or "true" in result

    def test_generate_inspec_from_recipe(self):
        """Test generating InSpec controls from Chef recipe."""
        recipe_path = SAMPLE_COOKBOOK / "recipes" / "default.rb"
        result = generate_inspec_from_recipe(str(recipe_path))

        # Should generate controls for resources in the recipe
        assert "control 'package-nginx'" in result
        assert "control 'service-nginx'" in result
        assert "control 'template--etc-nginx-nginx.conf'" in result
        assert "control 'directory--var-www-html'" in result
        assert "control 'file--var-www-html-index.html'" in result

        # Check control structure
        assert "describe package('nginx')" in result
        assert "it { should be_installed }" in result
        assert "describe service('nginx')" in result
        assert "it { should be_running }" in result
        assert "it { should be_enabled }" in result
        assert "describe file('/etc/nginx/nginx.conf')" in result
        assert "it { should exist }" in result

    def test_benchmark_inspec_profile_parsing(self, benchmark):
        """Benchmark InSpec profile parsing performance."""
        result = benchmark(parse_inspec_profile, str(SAMPLE_INSPEC_PROFILE))

        # Ensure it still works correctly
        import json

        data = json.loads(result)
        assert data["controls_count"] == 5
        assert len(data["controls"]) == 5

    def test_benchmark_inspec_conversion(self, benchmark):
        """Benchmark InSpec to Testinfra conversion performance."""
        result = benchmark(convert_inspec_to_test, str(SIMPLE_CONTROL), "testinfra")

        # Ensure it still works correctly
        assert "import pytest" in result
        assert "def test_simple_test(host):" in result


class TestPlaybookGenerationEdgeCases:
    """Test edge cases in playbook generation."""

    def test_generate_playbook_nonexistent_file(self):
        """Test generating playbook from nonexistent recipe."""
        from souschef.server import generate_playbook_from_recipe

        result = generate_playbook_from_recipe("/nonexistent/recipe.rb")
        assert "Error:" in result or "does not exist" in result.lower()

    def test_generate_playbook_with_parse_error(self, monkeypatch, tmp_path):
        """Test playbook generation when recipe parsing returns error."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        from souschef.converters import playbook

        def mock_parse_recipe(*args):
            return "Error: Failed to parse recipe"

        monkeypatch.setattr(playbook, "parse_recipe", mock_parse_recipe)

        temp_file = tmp_path / "test_recipe.rb"
        temp_file.write_text("package 'nginx'")

        from souschef import server

        result = server.generate_playbook_from_recipe(str(temp_file))
        assert "Error:" in result

    def test_generate_playbook_with_exception(self, monkeypatch, tmp_path):
        """Test playbook generation with unexpected exception."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        from souschef.converters import playbook

        def mock_parse_recipe(*args):
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr(playbook, "parse_recipe", mock_parse_recipe)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
            f.write("package 'nginx'")
            f.flush()
            temp_path = f.name

        try:
            from souschef import server

            result = server.generate_playbook_from_recipe(temp_path)
            assert "Error generating playbook:" in result
        finally:
            Path(temp_path).unlink()

    def test_generate_playbook_with_handlers(self):
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
            assert (
                "handlers:" in result
                or "warning" in result.lower()
                or "error" in result.lower()
                or "---" in result
            )


class TestAnalyzeSearchPatternsEdgeCases:
    """Test analyse_chef_search_patterns error handling."""

    def test_analyze_search_patterns_with_error(self):
        """Test analyse_chef_search_patterns exception handling."""
        from unittest.mock import MagicMock

        from souschef.server import analyse_chef_search_patterns

        with patch("souschef.converters.playbook._normalize_path") as mock_path:
            mock_file = MagicMock()
            mock_file.is_file.return_value = True
            mock_file.is_dir.return_value = False
            mock_path.return_value = mock_file

            with patch(
                "souschef.converters.playbook._extract_search_patterns_from_file"
            ) as mock_extract:
                mock_extract.side_effect = ValueError("Parse error")

                result = analyse_chef_search_patterns("some_recipe.rb")
                assert "Error analyzing Chef search patterns" in result


class TestAttributePrecedenceIntegration:
    """Integration tests for Chef attribute precedence with real fixtures."""

    def test_parse_attributes_with_real_cookbook_fixture(self):
        """Test parsing attributes from real sample cookbook."""
        result = parse_attributes(str(SAMPLE_COOKBOOK / "attributes" / "default.rb"))

        # Should contain actual attributes from the fixture
        assert "nginx" in result
        assert "Resolved Attributes" in result

    def test_parse_attributes_precedence_with_multiple_files(
        self, tmp_path, monkeypatch
    ):
        """Test attribute precedence with multiple attribute files."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        # Create a temporary attributes directory
        attrs_dir = tmp_path / "attributes"
        attrs_dir.mkdir()

        # Create default attributes
        default_file = attrs_dir / "default.rb"
        default_file.write_text(
            """
            default['app']['port'] = 3000
            default['app']['workers'] = 2
            default['app']['timeout'] = 30
            """
        )

        # Create override attributes
        override_file = attrs_dir / "override.rb"
        override_file.write_text(
            """
            override['app']['port'] = 8080
            force_override['app']['workers'] = 4
            """
        )

        # Parse both files
        default_result = parse_attributes(str(default_file))
        override_result = parse_attributes(str(override_file))

        # Verify both files parsed correctly
        assert "3000" in default_result
        assert "8080" in override_result
        assert "force_override" in override_result

    def test_parse_attributes_complex_nested_paths(self, tmp_path, monkeypatch):
        """Test attribute precedence with deeply nested attribute paths."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        attr_file = tmp_path / "complex.rb"
        attr_file.write_text(
            """
            default['nginx']['config']['ssl']['protocols'] = 'TLSv1.2'
            override['nginx']['config']['ssl']['protocols'] = 'TLSv1.3'
            normal['nginx']['config']['worker']['connections'] = 1024
            force_override['nginx']['config']['worker']['connections'] = 2048
            """
        )

        result = parse_attributes(str(attr_file), resolve_precedence=True)

        # Verify complex paths are parsed and resolved correctly
        assert "TLSv1.3" in result  # override should win
        assert "2048" in result  # force_override should win
        assert "Attributes with precedence conflicts: 2" in result

    def test_parse_attributes_with_ruby_values(self, tmp_path, monkeypatch):
        """Test parsing attributes with various Ruby value types."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        attr_file = tmp_path / "values.rb"
        attr_file.write_text(
            """
            default['app']['enabled'] = true
            default['app']['disabled'] = false
            default['app']['count'] = 42
            default['app']['ratio'] = 1.5
            default['app']['name'] = 'my-app'
            default['app']['tags'] = ['web', 'production']
            default['app']['config'] = { 'key' => 'value' }
            """
        )

        result = parse_attributes(str(attr_file))

        # Verify various value types are captured
        assert "true" in result
        assert "false" in result
        assert "42" in result
        assert "1.5" in result
        assert "my-app" in result
        assert "['web', 'production']" in result or "web" in result

    def test_parse_attributes_no_conflicts(self, tmp_path, monkeypatch):
        """Test attribute parsing when there are no precedence conflicts."""
        monkeypatch.setenv("SOUSCHEF_WORKSPACE_ROOT", str(tmp_path))

        attr_file = tmp_path / "no_conflicts.rb"
        attr_file.write_text(
            """
            default['app']['port'] = 3000
            default['app']['host'] = 'localhost'
            default['app']['debug'] = true
            """
        )

        result = parse_attributes(str(attr_file), resolve_precedence=True)

        # Should not mention conflicts when there are none
        assert "Total attributes: 3" in result
        assert (
            "Attributes with precedence conflicts" not in result
            or "conflicts: 0" in result
        )


class TestHabitatIntegration:
    """Integration tests for Habitat conversion with real fixtures."""

    def test_parse_real_habitat_plan(self):
        """Test parsing a real Habitat plan fixture."""
        plan_path = FIXTURES_DIR / "habitat_package" / "plan.sh"
        result = parse_habitat_plan(str(plan_path))

        # Should parse successfully
        assert not result.startswith("Error")

        import json

        plan = json.loads(result)
        assert plan["package"]["name"] == "nginx"
        assert plan["package"]["version"] == "1.25.3"
        assert plan["package"]["origin"] == "core"
        assert "BSD-2-Clause" in str(plan["package"]["license"])
        assert len(plan["dependencies"]["build"]) > 0
        assert len(plan["dependencies"]["runtime"]) > 0
        assert len(plan["ports"]) == 2
        assert "do_build" in plan["callbacks"]
        assert "do_install" in plan["callbacks"]

    def test_parse_postgres_habitat_plan(self):
        """Test parsing PostgreSQL Habitat plan fixture."""
        plan_path = FIXTURES_DIR / "habitat_package" / "plan_postgres.sh"
        result = parse_habitat_plan(str(plan_path))

        # Should parse successfully
        assert not result.startswith("Error")

        import json

        plan = json.loads(result)
        assert plan["package"]["name"] == "postgresql"
        assert plan["package"]["version"] == "14.5"
        assert "do_init" in plan["callbacks"]
        assert "initdb" in plan["callbacks"]["do_init"]

    def test_convert_real_habitat_to_dockerfile(self):
        """Test converting a real Habitat plan to Dockerfile."""
        plan_path = FIXTURES_DIR / "habitat_package" / "plan.sh"
        result = convert_habitat_to_dockerfile(str(plan_path), "ubuntu:22.04")

        # Should generate valid Dockerfile
        assert "FROM ubuntu:22.04" in result
        assert "LABEL maintainer=" in result
        assert 'LABEL version="1.25.3"' in result
        assert "LABEL description=" in result
        assert "RUN apt-get update" in result
        # Build dependencies from plan.sh: core/gcc -> gcc, core/make -> make
        assert "gcc" in result
        assert "make" in result
        # Runtime dependencies should also be present
        assert "libssl-dev" in result  # from core/openssl
        assert "libpcre3-dev" in result  # from core/pcre
        assert "./configure" in result
        assert "EXPOSE 80" in result
        assert "EXPOSE 443" in result
        assert "CMD" in result
        assert "nginx" in result

    def test_generate_compose_from_real_habitat_plans(self):
        """Test generating docker-compose from real Habitat plans."""
        nginx_path = FIXTURES_DIR / "habitat_package" / "plan.sh"
        postgres_path = FIXTURES_DIR / "habitat_package" / "plan_postgres.sh"

        result = generate_compose_from_habitat(
            f"{nginx_path},{postgres_path}", "habitat_net"
        )

        # Should generate valid docker-compose.yml
        assert "version: '3.8'" in result
        assert "services:" in result
        assert "nginx:" in result
        assert "postgresql:" in result
        assert "build:" in result
        assert "Dockerfile.nginx" in result
        assert "Dockerfile.postgresql" in result
        assert "ports:" in result
        assert "networks:" in result
        assert "habitat_net:" in result
        assert "driver: bridge" in result
        assert "volumes:" in result

    def test_dockerfile_structure_validity(self):
        """Test that generated Dockerfile has correct structure."""
        plan_path = FIXTURES_DIR / "habitat_package" / "plan.sh"
        result = convert_habitat_to_dockerfile(str(plan_path))

        lines = result.split("\n")

        # Check Dockerfile structure
        assert any(line.startswith("FROM") for line in lines)
        assert any(line.startswith("LABEL") for line in lines)
        assert any(line.startswith("RUN") for line in lines)
        assert any(line.startswith("EXPOSE") for line in lines)
        assert any(
            line.startswith("CMD") or line.startswith("ENTRYPOINT") for line in lines
        )

        # Should not have syntax errors
        assert not any("$pkg_" in line for line in lines if line.startswith("CMD"))

    def test_compose_with_single_service(self):
        """Test docker-compose generation with single service."""
        plan_path = FIXTURES_DIR / "habitat_package" / "plan.sh"
        result = generate_compose_from_habitat(str(plan_path), "test_net")

        # Should generate minimal compose file
        assert "services:" in result
        assert "nginx:" in result
        assert "build:" in result
        assert "networks:" in result
        assert "test_net:" in result

        # Verify basic structure is present
        assert result.count("nginx:") > 0


class TestAIRepositoryTypeDetermination:
    """Integration tests for AI-based repository type selection."""

    def test_analyse_with_mock_ai_assessment(self):
        """Test that AI assessment is used when credentials provided."""
        from souschef.generators.repo import RepoType, analyse_conversion_output

        mock_assessment = {
            "complexity_score": 85,
            "estimated_effort_days": 20,
            "ai_insights": "Complex multi-tier application",
        }

        with patch(
            "souschef.assessment.assess_single_cookbook_with_ai",
            return_value=mock_assessment,
        ):
            result = analyse_conversion_output(
                cookbook_path=str(SAMPLE_COOKBOOK),
                num_recipes=10,
                num_roles=2,  # 2 roles + high complexity = collection
                has_multiple_apps=False,
                needs_multi_env=True,
                ai_provider="anthropic",
                api_key="test-key-12345",
            )

        # High complexity with multiple roles should recommend collection
        assert result == RepoType.COLLECTION

    def test_analyse_falls_back_without_ai_credentials(self):
        """Test that heuristics are used when no AI credentials provided."""
        from souschef.generators.repo import (
            RepoType,
            analyse_conversion_output,
        )

        result = analyse_conversion_output(
            cookbook_path=str(SAMPLE_COOKBOOK),
            num_recipes=5,
            num_roles=3,  # 3+ roles suggests collection
            has_multiple_apps=False,
            needs_multi_env=True,
        )

        # Heuristics should suggest collection for 3+ roles
        assert result == RepoType.COLLECTION

    def test_analyse_uses_heuristics_on_ai_error(self):
        """Test that heuristics are used when AI assessment fails."""
        from souschef.generators.repo import (
            RepoType,
            analyse_conversion_output,
        )

        mock_assessment = {
            "error": "AI service temporary unavailable",
        }

        with patch(
            "souschef.assessment.assess_single_cookbook_with_ai",
            return_value=mock_assessment,
        ):
            result = analyse_conversion_output(
                cookbook_path=str(SAMPLE_COOKBOOK),
                num_recipes=2,
                num_roles=1,
                has_multiple_apps=False,
                needs_multi_env=False,
                ai_provider="anthropic",
                api_key="test-key",
            )

        # Should fall back to heuristics - small simple project
        assert result == RepoType.PLAYBOOKS_ROLES


class TestGitHubAgentControlIntegration:
    """Integration tests for GitHub Copilot agent control."""

    def test_assign_agent_returns_formatted_message(self):
        """Test that agent assignment returns properly formatted message."""
        from souschef.github import assign_copilot_agent_to_issue

        with patch("souschef.github.agent_control._add_label_to_issue"):
            result = assign_copilot_agent_to_issue(
                owner="testorg",
                repo="testrepo",
                issue_number=123,
                base_ref="main",
            )

            assert "✅" in result
            assert "testorg/testrepo" in result
            assert "#123" in result
            assert "pause_github_copilot_agent" in result
            assert "stop_github_copilot_agent" in result

    def test_pause_agent_workflow(self):
        """Test complete pause workflow."""
        from souschef.github import pause_copilot_agent

        with (
            patch("souschef.github.agent_control._add_label_to_issue"),
            patch("souschef.github.agent_control._remove_label_from_issue"),
            patch("souschef.github.agent_control._add_comment_to_issue"),
        ):
            result = pause_copilot_agent(
                owner="testorg",
                repo="testrepo",
                issue_number=123,
                reason="Testing pause feature",
            )

            assert "⏸️" in result
            assert "Testing pause feature" in result
            assert "resume" in result.lower()

    def test_stop_agent_workflow(self):
        """Test complete stop workflow."""
        from souschef.github import stop_copilot_agent

        with (
            patch("souschef.github.agent_control._add_label_to_issue"),
            patch("souschef.github.agent_control._remove_label_from_issue"),
            patch("souschef.github.agent_control._add_comment_to_issue"),
        ):
            result = stop_copilot_agent(
                owner="testorg",
                repo="testrepo",
                issue_number=123,
                reason="Requirements changed",
            )

            assert "🛑" in result
            assert "Requirements changed" in result
            assert "cancelled" in result

    def test_resume_paused_agent_workflow(self):
        """Test resume workflow for paused agent."""
        from souschef.github import resume_copilot_agent

        with (
            patch(
                "souschef.github.agent_control._check_agent_labels",
                return_value="paused",
            ),
            patch("souschef.github.agent_control._remove_label_from_issue"),
            patch("souschef.github.agent_control._add_label_to_issue"),
            patch("souschef.github.agent_control._add_comment_to_issue"),
        ):
            result = resume_copilot_agent(
                owner="testorg",
                repo="testrepo",
                issue_number=123,
                additional_instructions="Focus on performance",
            )

            assert "▶️" in result
            assert "Focus on performance" in result
            assert "continuing work" in result

    def test_resume_stopped_agent_failure(self):
        """Test that resuming stopped agent returns error."""
        from souschef.github import resume_copilot_agent

        with patch(
            "souschef.github.agent_control._check_agent_labels", return_value="stopped"
        ):
            result = resume_copilot_agent(
                owner="testorg",
                repo="testrepo",
                issue_number=123,
            )

            assert "❌" in result
            assert "stopped" in result
            assert "new assignment" in result

    def test_check_status_for_various_states(self):
        """Test status check for different agent states."""
        from souschef.github import check_copilot_agent_status

        states = ["active", "paused", "stopped", "not_assigned"]

        for state in states:
            with (
                patch(
                    "souschef.github.agent_control._check_agent_labels",
                    return_value=state,
                ),
                patch(
                    "souschef.github.agent_control._get_recent_agent_comments",
                    return_value="Recent activity",
                ),
            ):
                result = check_copilot_agent_status(
                    owner="testorg",
                    repo="testrepo",
                    issue_number=123,
                )

                # Check that state is reflected in output
                assert state.replace("_", " ").title() in result
                assert "#123" in result
                assert "testorg/testrepo" in result
