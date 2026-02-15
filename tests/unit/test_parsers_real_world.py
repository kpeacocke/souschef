"""Integration tests for parsers with realistic Chef cookbook content."""

import tempfile
from pathlib import Path

from souschef.parsers.attributes import parse_attributes
from souschef.parsers.metadata import parse_cookbook_metadata
from souschef.parsers.recipe import parse_recipe
from souschef.parsers.resource import parse_custom_resource
from souschef.parsers.template import parse_template


class TestRecipeParserEdgeCases:
    """Test recipe parser with edge cases and complex scenarios."""

    def test_parse_recipe_with_dynamic_block_names(self) -> None:
        """Test recipe with computed resource names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "dynamic.rb"
            recipe_file.write_text("""
['nginx', 'apache2', 'httpd'].each do |pkg|
  package pkg do
    action :install
  end
end

%w(ssh telnet ftp).each do |svc|
  service svc do
    action :remove
  end
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_file_operations(self) -> None:
        """Test recipe with file management operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "files.rb"
            recipe_file.write_text("""
%w(/var/www /var/cache /var/run).each do |dir|
  directory dir do
    owner 'www-data'
    group 'www-data'
    mode '0755'
  end
end

bash 'setup_dirs' do
  code 'mkdir -p /app/{bin,lib,config}'
end

file '/etc/app/config.yml' do
  mode '0644'
  owner 'root'
  group 'root'
  action :create_if_missing
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_multiple_actions(self) -> None:
        """Test resources with multiple explicit actions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "multi_action.rb"
            recipe_file.write_text("""
service 'nginx' do
  action [:enable, :start]
end

package 'curl' do
  action :install
end

execute 'setup' do
  action :run
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_subscriptions(self) -> None:
        """Test resources with subscribes and subscribes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "subscriptions.rb"
            recipe_file.write_text("""
package 'app' do
  action :install
  notifies :run, 'bash[setup]'
end

bash 'setup' do
  code 'app --setup'
  action :nothing
end

template '/etc/app.conf' do
  source 'app.conf.erb'
  subscribes :create, 'bash[setup]'
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_recipe_with_attribute_references(self) -> None:
        """Test recipes using node attribute references."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "attrs.rb"
            recipe_file.write_text("""
package node['packages']['web_server']

service node['services']['main'] do
  pattern node['process']['pattern']
  action [:enable, :start]
end

directory node['app']['home'] do
  owner node['app']['user']
  group node['app']['group']
  mode node['permissions']['dir']
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)


class TestAttributeParserEdgeCases:
    """Test attribute parser with complex scenarios."""

    def test_parse_attributes_with_operators(self) -> None:
        """Test attributes with various Ruby operators."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "operators.rb"
            attr_file.write_text("""
default['value1'] = 100 + 50
default['value2'] = 'string' + '_concat'
default['value3'] = ['a', 'b'] + ['c', 'd']
default['value4'] = Hash.new if something?
default['value5'] ||= 'default'
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_parse_attributes_with_method_calls(self) -> None:
        """Test attributes with method calls on values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "methods.rb"
            attr_file.write_text("""
default['user'] = ENV['USER'] || 'nobody'
default['home'] = File.expand_path('~')
default['version'] = '1.0.0'.split('.')[0]
default['config_dir'] = "/opt/app/#{node['version']}"
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)

    def test_parse_attributes_multiblock(self) -> None:
        """Test attributes with multiline hashes and arrays."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "multiblock.rb"
            attr_file.write_text("""
default['config'] = {
  'database' => {
    'host' => 'localhost',
    'port' => 5432,
    'options' => {
      'timeout' => 30,
      'retry' => true
    }
  },
  'cache' => {
    'enabled' => true,
    'ttl' => 3600
  }
}

default['servers'] = [
  'server1.example.com',
  'server2.example.com',
  'server3.example.com'
]
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)


class TestMetadataParserVariations:
    """Test metadata parser with various cookbook definitions."""

    def test_parse_metadata_minimal(self) -> None:
        """Test parsing minimal metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("name 'test'\nversion '0.1.0'")

            result = parse_cookbook_metadata(str(metadata_file))
            assert isinstance(result, (str, dict))

    def test_parse_metadata_with_all_fields(self) -> None:
        """Test metadata with all possible fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("""
name 'complete'
version '1.0.0'
description 'Complete metadata'
author 'Author Name'
email 'author@example.com'
license 'Apache-2.0'

chef_version '>= 13.0'
chef_version '< 15.0'

supports 'ubuntu', '>= 16.04'
supports 'ubuntu', '>= 18.04'
supports 'ubuntu', '>= 20.04'
supports 'centos', '>= 7.0'

depends 'nginx'
depends 'postgresql', '~> 7.0'

provides 'app::install'

issues_url 'https://example.com/issues'
source_url 'https://github.com/example/repo'
""")

            result = parse_cookbook_metadata(str(metadata_file))
            assert isinstance(result, (str, dict))


class TestTemplateParserVariations:
    """Test template parser with various ERB patterns."""

    def test_parse_template_with_complex_logic(self) -> None:
        """Test template with complex control flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "complex.erb"
            template_file.write_text("""
<% if @enabled %>
  <% @items.each_with_index do |item, idx| %>
    <% if idx > 0 %>,<% end %>
    "<%= item %>"
  <% end %>
<% else %>
  # Disabled
<% end %>
""")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_template_with_erb_comment_blocks(self) -> None:
        """Test template with various comment styles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "comments.erb"
            template_file.write_text("""
<%# This is an ERB comment %>
<% # This is Ruby comment %>
Content here <%= @var %>
<%# Multi-line
    comment block
    test %>
""")

            result = parse_template(str(template_file))
            assert isinstance(result, str)

    def test_parse_template_with_raw_erb_blocks(self) -> None:
        """Test template with raw ERB placeholders."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "raw.erb"
            template_file.write_text("""
<%% Not a real ERB tag %%>
<%= value %>
<%% Also not ERB %%>
<% if true %>
  Real ERB here
<% end %>
""")

            result = parse_template(str(template_file))
            assert isinstance(result, str)


class TestResourceParserVariations:
    """Test custom resource parser variations."""

    def test_parse_resource_with_default_action(self) -> None:
        """Test resource with default_action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "with_default.rb"
            resource_file.write_text("""
resource_name :my_resource
default_action :create

property :name, String, name_property: true

action :create do
  log 'Creating'
end

action :delete do
  log 'Deleting'
end
""")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)

    def test_parse_resource_with_property_defaults(self) -> None:
        """Test resource with property default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "prop_defaults.rb"
            resource_file.write_text("""
resource_name :configured

property :name, String, name_property: true
property :enabled, [true, false], default: true
property :timeout, Integer, default: 30
property :retries, Integer, default: 3
property :tags, Array, default: []

action :run do
  log 'Running'
end
""")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)

    def test_parse_resource_with_actions_list(self) -> None:
        """Test resource with action_class and provided_by."""
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "advanced.rb"
            resource_file.write_text("""
resource_name :advanced_resource
provides :advanced_resource
provides :my_alias

property :name, String, name_property: true
property :options, Hash, default: {}

% Check and run actions
action_class do
  def loaded_packages
    # Get installed packages
  end
end

action :install do
  log 'Installing'
end

action :configure do
  log 'Configuring'
end
""")

            result = parse_custom_resource(str(resource_file))
            assert isinstance(result, str)


class TestParserIntegrationScenarios:
    """Test parser with realistic integration scenarios."""

    def test_parse_recipe_real_world_scenario(self) -> None:
        """Test parsing a realistic full application recipe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "app_setup.rb"
            recipe_file.write_text("""
#
# Application setup recipe
#

# Include dependencies
include_recipe 'base'
include_recipe 'database'

# Update system
execute 'apt-get update' do
  action :nothing
end.run_action(:run) if node['platform_family'] == 'debian'

# Install packages
%w[git curl wget build-essential].each do |pkg|
  package pkg do
    action :install
  end
end

# Create app user
user 'appuser' do
  comment 'Application user'
  home '/home/appuser'
  shell '/bin/bash'
  action :create
end

# Create directories
%(/home/appuser/.ssh /var/www/app /var/log/app).each do |dir|
  directory dir do
    owner 'appuser'
    group 'appuser'
    recursive true
    action :create
  end
end

# Deploy code
bash 'clone_repo' do
  code 'git clone https://github.com/example/app.git /var/www/app'
  not_if { ::File.exist?('/var/www/app/.git') }
end

# Install dependencies
bash 'install_gems' do
  cwd '/var/www/app'
  code 'bundle install'
  notifies :restart, 'service[app]'
end

# Service configuration
service 'app' do
  enabled true
  running false
  action :nothing
end

# Monitoring setup
template '/etc/monitoring/app.yml' do
  source 'monitoring.yml.erb'
  variables(
    app_name: node['app']['name'],
    port: node['app']['port']
  )
end
""")

            result = parse_recipe(str(recipe_file))
            assert isinstance(result, str)

    def test_parse_attributes_real_world_scenario(self) -> None:
        """Test parsing realistic application attributes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "app.rb"
            attr_file.write_text("""
# Application configuration

default['app']['name'] = 'myapp'
default['app']['version'] = '1.0.0'
default['app']['user'] = 'appuser'
default['app']['group'] = 'appuser'
default['app']['home'] = '/var/www/app'

# Server configuration
default['app']['server']['host'] = '0.0.0.0'
default['app']['server']['port'] = node['app']['port'] || 3000
default['app']['server']['workers'] = node['cpu']['total'] || 4
default['app']['server']['timeout'] = 60

# Database configuration
default['app']['database']['adapter'] = node['db_adapter'] || 'postgresql'
default['app']['database']['host'] = node['db_host'] || 'localhost'
default['app']['database']['port'] = node['db_port'] || 5432
default['app']['database']['name'] = node['db_name'] || 'myapp_prod'

# Features
default['app']['features']['caching'] = true
default['app']['features']['compression'] = true
default['app']['features']['http2'] = true

# Logging
default['app']['logging']['level'] = node['environment'] == 'production' ? 'warn' : 'debug'
default['app']['logging']['format'] = 'json'
""")

            result = parse_attributes(str(attr_file))
            assert isinstance(result, str)
