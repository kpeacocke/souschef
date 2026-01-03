"""Snapshot tests for Chef-to-Ansible conversion outputs.

These tests ensure that the conversion logic produces consistent output
and helps prevent regressions in the generated Ansible playbooks and templates.
"""

import tempfile

from souschef.server import (
    convert_chef_databag_to_vars,
    convert_chef_deployment_to_ansible_strategy,
    convert_chef_environment_to_inventory_group,
    convert_chef_search_to_inventory,
    convert_inspec_to_test,
    convert_resource_to_task,
    parse_recipe,
    parse_template,
)


def test_convert_package_resource_to_task_snapshot(snapshot):
    """Snapshot test for package resource conversion."""
    resource = {
        "type": "package",
        "name": "nginx",
        "action": "install",
        "properties": {"version": "1.18.0"},
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_service_resource_to_task_snapshot(snapshot):
    """Snapshot test for service resource conversion."""
    resource = {
        "type": "service",
        "name": "nginx",
        "action": "start",
        "properties": {"enabled": "true"},
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_template_resource_to_task_snapshot(snapshot):
    """Snapshot test for template resource conversion."""
    resource = {
        "type": "template",
        "name": "/etc/nginx/nginx.conf",
        "action": "create",
        "properties": {
            "source": "nginx.conf.erb",
            "owner": "root",
            "group": "root",
            "mode": "0644",
        },
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_file_resource_to_task_snapshot(snapshot):
    """Snapshot test for file resource conversion."""
    resource = {
        "type": "file",
        "name": "/etc/app/config.json",
        "action": "create",
        "properties": {"content": '{"key": "value"}', "mode": "0600"},
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_directory_resource_to_task_snapshot(snapshot):
    """Snapshot test for directory resource conversion."""
    resource = {
        "type": "directory",
        "name": "/var/www/html",
        "action": "create",
        "properties": {"owner": "www-data", "group": "www-data", "mode": "0755"},
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_execute_resource_to_task_snapshot(snapshot):
    """Snapshot test for execute resource conversion."""
    resource = {
        "type": "execute",
        "name": "reload-systemd",
        "action": "run",
        "properties": {"command": "systemctl daemon-reload"},
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_parse_simple_recipe_snapshot(snapshot):
    """Snapshot test for simple recipe parsing."""
    recipe = """
package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()
        result = parse_recipe(f.name)
    assert result == snapshot


def test_parse_recipe_with_notifies_snapshot(snapshot):
    """Snapshot test for recipe with notifies."""
    recipe = """
template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  notifies :reload, 'service[nginx]', :delayed
  action :create
end

service 'nginx' do
  action [:enable, :start]
  supports :reload => true
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()
        result = parse_recipe(f.name)
    assert result == snapshot


def test_parse_recipe_with_guards_snapshot(snapshot):
    """Snapshot test for recipe with guard conditions."""
    recipe = """
package 'postgresql' do
  action :install
  only_if do
    File.exist?('/etc/postgresql')
  end
end

service 'postgresql' do
  action :start
  not_if { system('pgrep postgres') }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()
        result = parse_recipe(f.name)
    assert result == snapshot


def test_parse_erb_template_snapshot(snapshot):
    """Snapshot test for ERB template parsing."""
    template = """
server {
    listen <%= node['nginx']['port'] %>;
    server_name <%= node['nginx']['server_name'] %>;

    root <%= node['nginx']['document_root'] %>;
    index index.html index.htm;

    <% if node['nginx']['ssl_enabled'] %>
    ssl on;
    ssl_certificate <%= node['nginx']['ssl_cert'] %>;
    <% end %>

    location / {
        try_files $uri $uri/ =404;
    }
}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".erb", delete=False) as f:
        f.write(template)
        f.flush()
        result = parse_template(f.name)
        # Parse result and exclude the original_file path which changes each run
        import json

        result_dict = json.loads(result)
        result_dict.pop("original_file", None)
        result = json.dumps(result_dict, indent=2)
    assert result == snapshot


def test_convert_chef_search_to_inventory_snapshot(snapshot):
    """Snapshot test for Chef search to inventory conversion."""
    search_query = "role:webserver AND environment:production"
    result = convert_chef_search_to_inventory(search_query)
    assert result == snapshot


def test_convert_chef_databag_to_vars_snapshot(snapshot):
    """Snapshot test for databag to vars conversion."""
    databag_content = """
{
  "id": "database",
  "host": "db.example.com",
  "port": 5432,
  "username": "app_user",
  "pool_size": 10
}
"""
    result = convert_chef_databag_to_vars(databag_content, "database", "production")
    assert result == snapshot


def test_convert_chef_environment_to_inventory_snapshot(snapshot):
    """Snapshot test for environment to inventory conversion."""
    env_content = """
name 'production'
description 'Production environment'
default_attributes({
  'nginx' => {
    'port' => 80,
    'worker_processes' => 4
  },
  'app' => {
    'debug' => false,
    'log_level' => 'info'
  }
})
override_attributes({
  'app' => {
    'max_connections' => 1000
  }
})
cookbook 'nginx', '= 2.0.0'
cookbook 'postgresql', '~> 3.1'
"""
    result = convert_chef_environment_to_inventory_group(env_content, "production")
    assert result == snapshot


def test_convert_inspec_to_testinfra_snapshot(snapshot):
    """Snapshot test for InSpec to TestInfra conversion."""
    inspec_code = """
describe package('nginx') do
  it { should be_installed }
end

describe service('nginx') do
  it { should be_running }
  it { should be_enabled }
end

describe port(80) do
  it { should be_listening }
end

describe file('/etc/nginx/nginx.conf') do
  it { should exist }
  its('mode') { should cmp '0644' }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(inspec_code)
        f.flush()
        result = convert_inspec_to_test(f.name, "testinfra")
    assert result == snapshot


def test_convert_inspec_to_molecule_snapshot(snapshot):
    """Snapshot test for InSpec to Molecule conversion."""
    inspec_code = """
describe package('postgresql') do
  it { should be_installed }
end

describe service('postgresql') do
  it { should be_running }
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(inspec_code)
        f.flush()
        result = convert_inspec_to_test(f.name, "molecule")
    assert result == snapshot


def test_convert_chef_deployment_strategy_snapshot(snapshot):
    """Snapshot test for Chef deployment to Ansible strategy conversion."""
    deployment_config = """
{
  "strategy": "rolling",
  "batch_size": 5,
  "max_failures": 2,
  "health_check": {
    "type": "http",
    "endpoint": "/health",
    "timeout": 30
  }
}
"""
    result = convert_chef_deployment_to_ansible_strategy(
        deployment_config, "web_deploy"
    )
    assert result == snapshot


def test_parse_recipe_with_multiple_actions_snapshot(snapshot):
    """Snapshot test for recipe with multiple resource actions."""
    recipe = """
service 'apache2' do
  action [:stop, :disable]
end

package 'apache2' do
  action :remove
end

package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()
        result = parse_recipe(f.name)
    assert result == snapshot


def test_parse_recipe_with_variables_snapshot(snapshot):
    """Snapshot test for recipe with node attributes."""
    recipe = """
nginx_port = node['nginx']['port'] || 80
document_root = node['nginx']['document_root']

package 'nginx' do
  action :install
end

template '/etc/nginx/sites-available/default' do
  source 'default-site.conf.erb'
  variables(
    :port => nginx_port,
    :document_root => document_root
  )
  notifies :reload, 'service[nginx]'
  action :create
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()
        result = parse_recipe(f.name)
    assert result == snapshot


def test_parse_complex_erb_template_snapshot(snapshot):
    """Snapshot test for complex ERB template with loops and conditionals."""
    template = """
# <%= @description %>
# Generated on <%= Time.now.strftime('%Y-%m-%d') %>

[main]
server_name = <%= @server_name %>
port = <%= @port %>

<% @servers.each do |server| -%>
[server_<%= server['name'] %>]
host = <%= server['host'] %>
port = <%= server['port'] %>
<% if server['ssl_enabled'] -%>
ssl = true
cert = <%= server['ssl_cert'] %>
<% end -%>
<% end -%>

<% unless @disabled_features.empty? -%>
[disabled]
<% @disabled_features.each do |feature| -%>
<%= feature %> = false
<% end -%>
<% end -%>
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".erb", delete=False) as f:
        f.write(template)
        f.flush()
        result = parse_template(f.name)
        # Parse result and exclude the original_file path which changes each run
        import json

        result_dict = json.loads(result)
        result_dict.pop("original_file", None)
        result = json.dumps(result_dict, indent=2)
    assert result == snapshot


def test_convert_user_resource_to_task_snapshot(snapshot):
    """Snapshot test for user resource conversion."""
    resource = {
        "type": "user",
        "name": "appuser",
        "action": "create",
        "properties": {
            "uid": "1001",
            "gid": "1001",
            "shell": "/bin/bash",
            "home": "/home/appuser",
        },
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_group_resource_to_task_snapshot(snapshot):
    """Snapshot test for group resource conversion."""
    resource = {
        "type": "group",
        "name": "appgroup",
        "action": "create",
        "properties": {"gid": "1001"},
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_convert_cron_resource_to_task_snapshot(snapshot):
    """Snapshot test for cron resource conversion."""
    resource = {
        "type": "cron",
        "name": "daily_backup",
        "action": "create",
        "properties": {
            "minute": "0",
            "hour": "2",
            "command": "/usr/local/bin/backup.sh",
            "user": "root",
        },
    }
    result = convert_resource_to_task(resource, "")
    assert result == snapshot


def test_parse_recipe_with_include_recipe_snapshot(snapshot):
    """Snapshot test for recipe with include_recipe statements."""
    recipe = """
include_recipe 'nginx::default'
include_recipe 'postgresql::server'

template '/etc/app/config.yml' do
  source 'config.yml.erb'
  action :create
end
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rb", delete=False) as f:
        f.write(recipe)
        f.flush()
        result = parse_recipe(f.name)
    assert result == snapshot


def test_convert_databag_with_nested_structure_snapshot(snapshot):
    """Snapshot test for databag with nested structure."""
    databag_content = """
{
  "id": "application",
  "database": {
    "host": "localhost",
    "port": 5432,
    "credentials": {
      "username": "app",
      "password_key": "vault/db/password"
    }
  },
  "cache": {
    "type": "redis",
    "servers": ["redis1:6379", "redis2:6379"]
  }
}
"""
    result = convert_chef_databag_to_vars(databag_content, "application", "staging")
    assert result == snapshot
