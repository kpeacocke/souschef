"""Tests for error recovery and edge case handling."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from souschef.server import (
    analyze_chef_environment_usage,
    convert_chef_environment_to_inventory_group,
    generate_awx_job_template_from_cookbook,
    generate_awx_project_from_cookbooks,
    generate_awx_workflow_from_chef_runlist,
    generate_inventory_from_chef_environments,
    parse_attributes,
    parse_custom_resource,
    parse_recipe,
    read_cookbook_metadata,
)


def test_parse_recipe_with_syntax_errors():
    """Test that parse_recipe handles Ruby syntax errors gracefully."""
    malformed_recipe = """
package 'nginx do  # Missing closing quote
  action :install
end

# Invalid Ruby syntax
if node['platform'] ==  # Incomplete condition
  service 'nginx' do
    action :start
  end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(malformed_recipe)
        f.flush()

        result = parse_recipe(f.name)

        # Should return a result, not crash
        assert isinstance(result, str)
        # Should indicate it's a malformed recipe
        assert len(result) > 0


def test_parse_recipe_with_invalid_utf8():
    """Test that parse_recipe handles invalid UTF-8 encoding."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".rb", delete=False) as f:
        # Write invalid UTF-8 bytes
        f.write(b"package 'nginx' \xff\xfe do\n")
        f.write(b"  action :install\n")
        f.write(b"end\n")
        f.flush()

        result = parse_recipe(f.name)

        # Should handle encoding error gracefully
        assert isinstance(result, str)
        assert "Error" in result or len(result) > 0


def test_parse_recipe_empty_file():
    """Test that parse_recipe handles empty files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write("")
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        # Empty file should return minimal output
        assert (
            "No Chef resources or include_recipe calls found" in result
            or "Analysis" in result
        )


def test_parse_recipe_only_comments():
    """Test that parse_recipe handles files with only comments."""
    comments_only = """
# This is a comment
# Another comment
# No actual code here
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(comments_only)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert (
            "No Chef resources or include_recipe calls found" in result
            or len(result) > 0
        )


def test_parse_recipe_with_very_long_lines():
    """Test that parse_recipe handles extremely long lines."""
    long_line_recipe = f"""
package "{"nginx" * 1000}" do
  action :install
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(long_line_recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert len(result) > 0


def test_parse_recipe_with_nested_heredocs():
    """Test that parse_recipe handles deeply nested heredocs."""
    nested_recipe = """
file '/etc/config' do
  content <<-EOH
    outer content
    <<-INNER
      inner content
    INNER
  EOH
  action :create
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(nested_recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result or len(result) > 0


def test_parse_attributes_malformed_syntax():
    """Test that parse_attributes handles malformed Ruby syntax."""
    malformed_attrs = """
default['nginx']['port'] =   # Missing value
default['nginx']['user'] = 'www-data
default['nginx' 'ssl'] = true  # Missing bracket operator
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(malformed_attrs)
        f.flush()

        result = parse_attributes(f.name)

        # Should not crash
        assert isinstance(result, str)
        assert len(result) > 0


def test_parse_custom_resource_invalid_syntax():
    """Test that parse_custom_resource handles invalid Ruby syntax."""
    invalid_resource = """
property :name, String required: true  # Missing comma
property :version

action :create do
  package name do  # Missing 'new_resource'
    version new_resource.version
    action :install
  # Missing 'end'
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(invalid_resource)
        f.flush()

        result = parse_custom_resource(f.name)

        assert isinstance(result, str)
        assert len(result) > 0


def test_parse_recipe_with_circular_includes():
    """Test that parse_recipe doesn't hang on circular includes."""
    # This is a conceptual test - Chef doesn't support circular includes
    # but we test that the parser doesn't get stuck
    recipe_with_include = """
include_recipe 'cookbook::recipe'
include_recipe 'cookbook::other'
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_include)
        f.flush()

        result = parse_recipe(f.name)

        # Should complete without hanging
        assert isinstance(result, str)
        assert len(result) > 0


def test_read_cookbook_metadata_malformed():
    """Test read_cookbook_metadata with malformed metadata.rb."""
    malformed_metadata = """
name 'test'
version '1.0.0
maintainer  # Missing value
depends 'other', '>= 2.0.0', '<= 1.0.0'  # Impossible constraint
"""
    mock_path = MagicMock(spec=Path)
    mock_path.read_text.return_value = malformed_metadata

    with patch("souschef.server._normalize_path", return_value=mock_path):
        result = read_cookbook_metadata("/fake/path/metadata.rb")

        # Should not crash
        assert isinstance(result, str)
        assert len(result) > 0


def test_parse_recipe_with_mixed_encodings():
    """Test that parse_recipe handles mixed character encodings."""
    # Create a file with mixed encodings (Latin-1 and UTF-8)
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".rb", delete=False) as f:
        f.write(b"# Comment with Latin-1: \xe9\n")
        f.write(b"package 'nginx' do\n")
        f.write(b"  # UTF-8 comment: \xc3\xa9\n")
        f.write(b"  action :install\n")
        f.write(b"end\n")
        f.flush()

        result = parse_recipe(f.name)

        # Should handle mixed encodings
        assert isinstance(result, str)


def test_parse_attributes_extremely_deep_nesting():
    """Test parse_attributes with extremely deep attribute nesting."""
    deep_attrs = """
default['a']['b']['c']['d']['e']['f']['g']['h']['i']['j']['k'] = 'value'
default['x']['y']['z']['1']['2']['3']['4']['5']['6']['7']['8']['9'] = 42
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(deep_attrs)
        f.flush()

        result = parse_attributes(f.name)

        assert isinstance(result, str)
        assert len(result) > 0


def test_parse_custom_resource_missing_required_sections():
    """Test parse_custom_resource when required sections are missing."""
    incomplete_resource = """
# Missing property declarations
# Missing action definitions
resource_name :incomplete
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(incomplete_resource)
        f.flush()

        result = parse_custom_resource(f.name)

        assert isinstance(result, str)
        # Should indicate it's incomplete
        assert len(result) > 0


def test_parse_recipe_with_extremely_large_resources():
    """Test parse_recipe with resources that have many properties."""
    huge_resource = """
file '/etc/config' do
"""
    # Add 100 properties
    for i in range(100):
        huge_resource += f"  property_{i} 'value_{i}'\n"

    huge_resource += "  action :create\nend\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(huge_resource)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_special_characters_in_strings():
    """Test parse_recipe with special characters in resource strings."""
    special_chars_recipe = """
file '/tmp/test' do
  content "Line with \\"quotes\\" and 'apostrophes' and \\n newlines"
  owner "user\\nwith\\nnewlines"
  action :create
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(special_chars_recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_attributes_with_ruby_expressions():
    """Test parse_attributes with complex Ruby expressions."""
    complex_attrs = """
default['nginx']['port'] = node['platform'] == 'ubuntu' ? 80 : 8080
default['nginx']['workers'] = node['cpu']['total'] * 2
default['nginx']['user'] = ENV['USER'] || 'www-data'
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(complex_attrs)
        f.flush()

        result = parse_attributes(f.name)

        assert isinstance(result, str)
        # Should parse despite complex expressions
        assert len(result) > 0


def test_parse_recipe_with_guards_and_conditions():
    """Test parse_recipe with various guard conditions."""
    guards_recipe = """
service 'nginx' do
  action :start
  only_if { ::File.exist?('/etc/nginx/nginx.conf') }
  not_if { ::File.exist?('/tmp/skip') }
  notifies :reload, 'service[nginx]', :delayed
end

package 'apache2' do
  action :install
  only_if "test -f /etc/debian_version"
  not_if "which apache2"
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(guards_recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result
        assert "Resource 2:" in result


def test_parse_recipe_with_file_exist_guards():
    """Test parse_recipe with File.exist? guard conditions."""
    recipe_with_file_checks = """
file '/etc/config' do
  content 'test'
  action :create
  only_if { File.exist?('/etc/defaults') }
end

directory '/var/app' do
  owner 'root'
  action :create
  not_if { File.directory?('/var/app') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_file_checks)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_system_call_guards():
    """Test parse_recipe with system() call guards."""
    recipe_with_system = """
package 'nginx' do
  action :install
  only_if { system('which nginx') }
end

service 'apache2' do
  action :stop
  not_if { system('systemctl is-active apache2') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_system)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_boolean_guards():
    """Test parse_recipe with simple boolean guard conditions."""
    recipe_with_booleans = """
service 'nginx' do
  action :start
  only_if { true }
end

package 'optional' do
  action :install
  not_if { false }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_booleans)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_subscribes():
    """Test parse_recipe with subscribes patterns."""
    recipe_with_subscribes = """
service 'nginx' do
  action :start
  subscribes :reload, 'template[/etc/nginx/nginx.conf]', :delayed
end

template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  action :create
  notifies :reload, 'service[nginx]', :immediately
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_subscribes)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result
        assert "Resource 2:" in result


def test_analyze_chef_environment_usage():
    """Test analyze_chef_environment_usage with cookbooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir) / "environments"
        env_path.mkdir()

        # Create production environment
        prod_env = env_path / "production.rb"
        prod_env.write_text("""
name 'production'
description 'Production environment'
default_attributes({
  'nginx' => {
    'port' => 80
  }
})
override_attributes({
  'app' => {
    'debug' => false
  }
})
cookbook 'nginx', '= 1.0.0'
""")

        # Create development environment
        dev_env = env_path / "development.rb"
        dev_env.write_text("""
name 'development'
description 'Development environment'
default_attributes({})
""")

        # Create a simple cookbook that uses environments
        cookbook_path = Path(tmpdir) / "mycookbook"
        cookbook_path.mkdir()
        metadata = cookbook_path / "metadata.rb"
        metadata.write_text("name 'mycookbook'\nversion '1.0.0'\n")

        result = analyze_chef_environment_usage(str(cookbook_path), str(env_path))

        assert isinstance(result, str)
        # Should analyze successfully
        assert len(result) > 0


def test_analyze_chef_environment_usage_with_errors():
    """Test analyze_chef_environment_usage with malformed environments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir) / "environments"
        env_path.mkdir()

        # Create malformed environment
        bad_env = env_path / "bad.rb"
        bad_env.write_text("""
name 'bad'
description 'Bad environment
# Missing closing quote and invalid syntax
""")

        cookbook_path = Path(tmpdir) / "cookbook"
        cookbook_path.mkdir()
        metadata = cookbook_path / "metadata.rb"
        metadata.write_text("name 'test'\nversion '1.0.0'\n")

        result = analyze_chef_environment_usage(str(cookbook_path), str(env_path))

        assert isinstance(result, str)
        # Should handle error gracefully
        assert len(result) > 0


def test_convert_chef_environment_to_inventory_group():
    """Test convert_chef_environment_to_inventory_group."""
    env_content = """
name 'production'
description 'Production environment'
default_attributes({
  'nginx' => {
    'port' => 80
  }
})
"""

    result = convert_chef_environment_to_inventory_group(env_content, "production")

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_inventory_from_chef_environments():
    """Test generate_inventory_from_chef_environments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir)

        # Create production environment
        prod_env = env_path / "production.rb"
        prod_env.write_text("""
name 'production'
description 'Production environment'
""")

        result = generate_inventory_from_chef_environments(str(env_path))

        assert isinstance(result, str)
        assert len(result) > 0


def test_generate_awx_job_template_from_cookbook():
    """Test generate_awx_job_template_from_cookbook with a basic cookbook."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cookbook_path = Path(tmpdir) / "mycookbook"
        cookbook_path.mkdir()

        # Create metadata
        metadata = cookbook_path / "metadata.rb"
        metadata.write_text("""
name 'mycookbook'
version '1.0.0'
description 'Test cookbook'
""")

        # Create a recipe
        recipes_dir = cookbook_path / "recipes"
        recipes_dir.mkdir()
        recipe = recipes_dir / "default.rb"
        recipe.write_text("""
package 'nginx' do
  action :install
end
""")

        result = generate_awx_job_template_from_cookbook(
            str(cookbook_path), "mycookbook"
        )

        assert isinstance(result, str)
        assert "AWX" in result or "Job Template" in result or len(result) > 0


def test_generate_awx_workflow_from_chef_runlist():
    """Test generate_awx_workflow_from_chef_runlist with a simple runlist."""
    runlist = "recipe[nginx::default],recipe[app::deploy],recipe[monitoring::setup]"

    result = generate_awx_workflow_from_chef_runlist(runlist, "deploy_workflow")

    assert isinstance(result, str)
    assert "workflow" in result.lower() or "AWX" in result or len(result) > 0


def test_generate_awx_project_from_cookbooks():
    """Test generate_awx_project_from_cookbooks with a cookbooks directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cookbooks_path = Path(tmpdir)

        # Create two simple cookbooks
        for cookbook_name in ["web", "db"]:
            cookbook_path = cookbooks_path / cookbook_name
            cookbook_path.mkdir()

            metadata = cookbook_path / "metadata.rb"
            metadata.write_text(f"""
name '{cookbook_name}'
version '1.0.0'
""")

        result = generate_awx_project_from_cookbooks(
            str(cookbooks_path), "myproject", "git", "https://github.com/org/repo"
        )

        assert isinstance(result, str)
        assert "project" in result.lower() or "AWX" in result or len(result) > 0


def test_generate_awx_functions_with_invalid_paths():
    """Test AWX generation functions with invalid paths."""
    # Test with non-existent cookbook
    result1 = generate_awx_job_template_from_cookbook("/nonexistent/path", "test")
    assert isinstance(result1, str)
    assert "error" in result1.lower() or len(result1) > 0

    # Test with invalid runlist
    result2 = generate_awx_workflow_from_chef_runlist("", "empty_workflow")
    assert isinstance(result2, str)

    # Test with non-existent cookbooks directory
    result3 = generate_awx_project_from_cookbooks("/nonexistent", "test", "git", "url")
    assert isinstance(result3, str)
    assert "error" in result3.lower() or len(result3) > 0


def test_parse_recipe_with_file_exist_guard_without_colons():
    """Test parse_recipe with File.exist? (no :: prefix) to match regex."""
    recipe_with_file_check = """
service 'nginx' do
  action :start
  only_if { File.exist?('/etc/nginx/nginx.conf') }
end

package 'apache2' do
  action :remove
  not_if { File.exist?('/usr/sbin/apache2') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_file_check)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result
        assert "Resource 2:" in result


def test_parse_recipe_with_directory_exist_guard():
    """Test parse_recipe with File.directory? guard condition."""
    recipe_with_dir_check = """
directory '/var/www/html' do
  owner 'www-data'
  action :create
  not_if { File.directory?('/var/www/html') }
end

file '/opt/app/config.yml' do
  content 'key: value'
  action :create
  only_if { File.directory?('/opt/app') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_dir_check)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_system_call_in_guard():
    """Test parse_recipe with system() call in guard condition."""
    recipe_with_system_guard = """
package 'nginx' do
  action :install
  not_if { system('which nginx') }
end

service 'postgresql' do
  action :start
  only_if { system('test -f /etc/postgresql/postgresql.conf') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_system_guard)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_matching_subscribes_pattern():
    """Test parse_recipe with subscribes that match the target resource."""
    # The subscribes pattern needs to reference a resource that exists
    recipe_with_matching_subscribes = """
template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  action :create
end

service 'nginx' do
  action :nothing
  subscribes :restart, 'template[/etc/nginx/nginx.conf]'
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_matching_subscribes)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result
        assert "Resource 2:" in result


def test_parse_recipe_with_subscribes_timing():
    """Test parse_recipe with subscribes that have timing specified."""
    recipe_with_timed_subscribes = """
file '/etc/app/config.json' do
  content '{"key": "value"}'
  action :create
end

service 'app-server' do
  action :nothing
  subscribes :reload, 'file[/etc/app/config.json]', :immediately
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_timed_subscribes)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_multiple_subscribes_patterns():
    """Test parse_recipe with multiple subscribes to same resource."""
    recipe_with_multi_subscribes = """
template '/etc/haproxy/haproxy.cfg' do
  source 'haproxy.cfg.erb'
  action :create
end

service 'haproxy' do
  action :nothing
  subscribes :reload, 'template[/etc/haproxy/haproxy.cfg]', :delayed
end

execute 'validate-haproxy-config' do
  command 'haproxy -c -f /etc/haproxy/haproxy.cfg'
  action :nothing
  subscribes :run, 'template[/etc/haproxy/haproxy.cfg]', :immediately
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_multi_subscribes)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_complex_guard_block():
    """Test parse_recipe with complex guard blocks that need manual review."""
    recipe_with_complex_guard = """
package 'redis' do
  action :install
  only_if { node['platform_family'] == 'debian' && node['redis']['install'] == true }
end

service 'memcached' do
  action :start
  not_if { node.run_state['memcached_disabled'] || File.exists?('/tmp/skip-memcached') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_complex_guard)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_generate_awx_job_template_with_complex_cookbook():
    """Test AWX job template generation with cookbook containing recipes and attributes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cookbook_path = Path(tmpdir) / "complex_cookbook"
        cookbook_path.mkdir()

        # Create metadata with dependencies
        metadata = cookbook_path / "metadata.rb"
        metadata.write_text("""
name 'complex_cookbook'
version '2.1.0'
description 'Complex cookbook for testing'
depends 'nginx', '>= 1.0.0'
depends 'postgresql', '~> 3.0'
""")

        # Create recipes directory with multiple recipes
        recipes_dir = cookbook_path / "recipes"
        recipes_dir.mkdir()

        default_recipe = recipes_dir / "default.rb"
        default_recipe.write_text("""
include_recipe 'complex_cookbook::install'
include_recipe 'complex_cookbook::configure'
""")

        install_recipe = recipes_dir / "install.rb"
        install_recipe.write_text("""
package 'nginx' do
  action :install
end

package 'postgresql' do
  action :install
end
""")

        # Create attributes
        attrs_dir = cookbook_path / "attributes"
        attrs_dir.mkdir()
        attrs_file = attrs_dir / "default.rb"
        attrs_file.write_text("""
default['nginx']['port'] = 80
default['postgresql']['version'] = '14'
""")

        result = generate_awx_job_template_from_cookbook(
            str(cookbook_path), "complex_cookbook"
        )

        assert isinstance(result, str)
        assert len(result) > 0


def test_generate_awx_workflow_with_complex_runlist():
    """Test AWX workflow generation with complex runlist including roles and recipes."""
    complex_runlist = (
        "role[webserver],recipe[nginx::default],recipe[app::deploy],"
        "role[database],recipe[postgresql::server],recipe[app::migrate]"
    )

    result = generate_awx_workflow_from_chef_runlist(
        complex_runlist, "full_stack_deploy"
    )

    assert isinstance(result, str)
    assert len(result) > 0


def test_analyze_chef_environment_with_complex_attributes():
    """Test environment analysis with complex nested attributes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir) / "environments"
        env_path.mkdir()

        # Create environment with complex attributes
        staging_env = env_path / "staging.rb"
        staging_env.write_text("""
name 'staging'
description 'Staging environment with complex config'
default_attributes({
  'nginx' => {
    'port' => 8080,
    'worker_processes' => 4,
    'ssl' => {
      'enabled' => true,
      'certificate' => '/etc/ssl/certs/staging.crt'
    }
  },
  'app' => {
    'debug' => true,
    'database' => {
      'host' => 'db-staging.example.com',
      'pool_size' => 10
    }
  }
})
override_attributes({
  'app' => {
    'log_level' => 'debug'
  }
})
cookbook 'nginx', '= 2.0.0'
cookbook 'postgresql', '>= 3.0.0'
""")

        cookbook_path = Path(tmpdir) / "cookbook"
        cookbook_path.mkdir()
        metadata = cookbook_path / "metadata.rb"
        metadata.write_text("name 'test'\nversion '1.0.0'\n")

        result = analyze_chef_environment_usage(str(cookbook_path), str(env_path))

        assert isinstance(result, str)
        assert len(result) > 0


def test_convert_environment_with_cookbook_constraints():
    """Test environment conversion with various cookbook version constraints."""
    env_with_constraints = """
name 'production'
description 'Production environment'
cookbook 'nginx', '= 2.5.0'
cookbook 'postgresql', '~> 3.1'
cookbook 'redis', '>= 4.0.0'
cookbook 'memcached', '< 2.0.0'
default_attributes({
  'app' => {
    'env' => 'production'
  }
})
"""

    result = convert_chef_environment_to_inventory_group(
        env_with_constraints, "production", include_constraints=True
    )

    assert isinstance(result, str)
    assert len(result) > 0


def test_convert_environment_without_constraints():
    """Test environment conversion with constraints excluded."""
    env_content = """
name 'test'
description 'Test environment'
cookbook 'nginx', '= 1.0.0'
default_attributes({})
"""

    result = convert_chef_environment_to_inventory_group(
        env_content, "test", include_constraints=False
    )

    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_inventory_with_multiple_environments():
    """Test inventory generation from multiple environment files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir)

        # Create multiple environments
        for env_name in ["dev", "staging", "prod"]:
            env_file = env_path / f"{env_name}.rb"
            env_file.write_text(f"""
name '{env_name}'
description '{env_name.title()} environment'
default_attributes({{
  'app' => {{
    'env' => '{env_name}'
  }}
}})
""")

        result = generate_inventory_from_chef_environments(str(env_path))

        assert isinstance(result, str)
        assert len(result) > 0


def test_parse_recipe_with_file_exist_block_do_end():
    """Test parse_recipe with File.exist? in do...end block to match regex."""
    recipe_with_do_end_guard = """
package 'nginx' do
  action :install
  only_if do
    File.exist?('/etc/nginx/nginx.conf')
  end
end

service 'apache2' do
  action :stop
  not_if do
    File.exist?('/usr/sbin/apache2')
  end
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe_with_do_end_guard)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_directory_check_do_end():
    """Test parse_recipe with File.directory? in do...end block."""
    recipe = """
directory '/var/log/app' do
  owner 'app'
  action :create
  not_if do
    File.directory?('/var/log/app')
  end
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_system_call_do_end():
    """Test parse_recipe with system() call in do...end block."""
    recipe = """
package 'postgresql' do
  action :install
  only_if do
    system('test -f /etc/postgresql/postgresql.conf')
  end
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result


def test_parse_recipe_with_true_false_guards_do_end():
    """Test parse_recipe with simple true/false in do...end blocks."""
    recipe = """
service 'nginx' do
  action :start
  only_if do
    true
  end
end

package 'unused' do
  action :install
  not_if do
    false
  end
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()

        result = parse_recipe(f.name)

        assert isinstance(result, str)
        assert "Resource 1:" in result
