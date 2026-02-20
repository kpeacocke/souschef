"""
Tests for souschef/converters/advanced_resource.py module.

Tests advanced Chef resource conversion parsing including guards,
notifications, search queries, and handler generation.
"""

import pytest

from souschef.converters.advanced_resource import (
    convert_guard_to_ansible_when,
    estimate_conversion_complexity,
    generate_advanced_handler_yaml,
    parse_resource_guards,
    parse_resource_notifications,
    parse_resource_search,
)


class TestParseResourceGuards:
    """Test parsing Chef resource guards."""

    def test_parse_only_if_guard(self):
        """Test parsing only_if guard."""
        resource_body = """
        service 'nginx' do
          action :start
          only_if 'test -f /etc/nginx/nginx.conf'
        end
        """

        result = parse_resource_guards(resource_body)

        assert isinstance(result, dict)
        assert "only_if" in result or len(result) > 0

    def test_parse_not_if_guard(self):
        """Test parsing not_if guard."""
        resource_body = """
        execute 'install-package' do
          command 'apt-get install nginx'
          not_if 'which nginx'
        end
        """

        result = parse_resource_guards(resource_body)

        assert isinstance(result, dict)

    def test_parse_multiple_guards(self):
        """Test parsing resource with multiple guards."""
        resource_body = """
        template '/etc/app.conf' do
          source 'app.conf.erb'
          only_if { File.exist?('/opt/app') }
          not_if { system('pgrep -f app') }
        end
        """

        result = parse_resource_guards(resource_body)

        assert isinstance(result, dict)

    def test_parse_guard_with_ruby_block(self):
        """Test parsing guard with Ruby block."""
        resource_body = """
        package 'nodejs' do
          action :install
          only_if { File.read('/proc/version').include?('Ubuntu') }
        end
        """

        result = parse_resource_guards(resource_body)

        assert isinstance(result, dict)

    def test_parse_no_guards(self):
        """Test parsing resource without guards."""
        resource_body = """
        service 'nginx' do
          action :start
        end
        """

        result = parse_resource_guards(resource_body)

        assert isinstance(result, dict)

    def test_parse_guard_with_special_characters(self):
        """Test parsing guard with special shell characters."""
        resource_body = """
        execute 'check-status' do
          command 'systemctl status nginx | grep active'
          only_if 'test "$?" = "0"'
        end
        """

        result = parse_resource_guards(resource_body)

        assert isinstance(result, dict)


class TestParseResourceNotifications:
    """Test parsing Chef resource notifications."""

    def test_parse_notifies_single(self):
        """Test parsing single notification."""
        resource_body = """
        template '/etc/nginx/nginx.conf' do
          source 'nginx.conf.erb'
          notifies :restart, 'service[nginx]'
        end
        """

        result = parse_resource_notifications(resource_body)

        assert isinstance(result, list)

    def test_parse_notifies_multiple(self):
        """Test parsing multiple notifications."""
        resource_body = """
        package 'nodejs' do
          action :install
          notifies :restart, 'service[app]'
          notifies :run, 'execute[sync-data]'
        end
        """

        result = parse_resource_notifications(resource_body)

        assert isinstance(result, list)

    def test_parse_subscribes(self):
        """Test parsing subscribes notification."""
        resource_body = """
        service 'nginx' do
          action :nothing
          subscribes :restart, 'template[/etc/nginx/nginx.conf]'
        end
        """

        result = parse_resource_notifications(resource_body)

        assert isinstance(result, list)

    def test_parse_notification_with_immediately(self):
        """Test parsing notification with immediate execution."""
        resource_body = """
        template '/etc/app.conf' do
          source 'app.conf.erb'
          notifies :restart, 'service[app]', :immediately
        end
        """

        result = parse_resource_notifications(resource_body)

        assert isinstance(result, list)

    def test_parse_notification_with_delayed(self):
        """Test parsing delayed notification."""
        resource_body = """
        file '/tmp/marker' do
          content 'updated'
          notifies :run, 'ruby_block[process]', :delayed
        end
        """

        result = parse_resource_notifications(resource_body)

        assert isinstance(result, list)

    def test_parse_no_notifications(self):
        """Test parsing resource without notifications."""
        resource_body = """
        directory '/var/cache/app' do
          owner 'appuser'
          mode '0755'
        end
        """

        result = parse_resource_notifications(resource_body)

        assert isinstance(result, list)


class TestParseResourceSearch:
    """Test parsing Chef search queries in resources."""

    def test_parse_search_in_ruby_block(self):
        """Test parsing search() in resource."""
        resource_body = """
        ruby_block 'find-nodes' do
          block do
            results = search(:node, 'role:webserver')
            puts results.length
          end
        end
        """

        result = parse_resource_search(resource_body)

        assert isinstance(result, dict)

    def test_parse_search_with_query(self):
        """Test parsing search with specific query."""
        resource_body = """
        ruby_block 'configure-nodes' do
          block do
            nodes = search(:node, 'environment:production AND platform:ubuntu')
            nodes.each { |n| puts n['hostname'] }
          end
        end
        """

        result = parse_resource_search(resource_body)

        assert isinstance(result, dict)

    def test_parse_search_data_bag(self):
        """Test parsing data bag search."""
        resource_body = """
        ruby_block 'load-secrets' do
          block do
            secrets = search(:vault, 'id:production_keys')
            puts secrets
          end
        end
        """

        result = parse_resource_search(resource_body)

        assert isinstance(result, dict)


class TestGuardConversion:
    """Test converting Chef guards to Ansible when."""

    def test_convert_only_if_command(self):
        """Test converting only_if to when."""
        result = convert_guard_to_ansible_when(
            "only_if", "test -f /etc/nginx/nginx.conf"
        )

        assert isinstance(result, str)

    def test_convert_not_if_command(self):
        """Test converting not_if to when."""
        result = convert_guard_to_ansible_when("not_if", "which nginx")

        assert isinstance(result, str)

    def test_convert_guard_with_ruby_syntax(self):
        """Test converting Ruby block guard."""
        result = convert_guard_to_ansible_when("only_if", "File.exist?('/opt/app')")

        assert isinstance(result, str)


class TestGenerateAdvancedHandlerYaml:
    """Test generating Ansible handler YAML."""

    def test_generate_single_handler(self):
        """Test generating single handler."""
        notifications = [{"action": "restart", "resource": "service[nginx]"}]

        result = generate_advanced_handler_yaml(notifications)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_multiple_handlers(self):
        """Test generating multiple handlers."""
        notifications = [
            {"action": "restart", "resource": "service[app]"},
            {"action": "reload", "resource": "service[nginx]"},
            {"action": "run", "resource": "execute[sync]"},
        ]

        result = generate_advanced_handler_yaml(notifications)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_handlers_with_timing(self):
        """Test generating handlers with timing."""
        notifications = [
            {"action": "restart", "resource": "service[app]", "timing": "immediately"},
            {"action": "reload", "resource": "service[nginx]", "timing": "delayed"},
        ]

        result = generate_advanced_handler_yaml(notifications)

        assert isinstance(result, str)

    def test_generate_empty_handlers(self):
        """Test generating with no notifications."""
        result = generate_advanced_handler_yaml([])

        assert isinstance(result, str)


class TestEstimateConversionComplexity:
    """Test estimation of conversion complexity."""

    def test_estimate_simple_resource(self):
        """Test complexity of simple resource."""
        resource_body = """
        service 'nginx' do
          action :start
        end
        """

        result = estimate_conversion_complexity(resource_body)

        assert isinstance(result, str)

    def test_estimate_complex_resource(self):
        """Test complexity of resource with guards and notifications."""
        resource_body = """
        template '/etc/app.conf' do
          source 'app.conf.erb'
          variables lazy { { servers: search(:node, 'role:backend') } }
          only_if { File.exist?('/opt/app') }
          notifies :restart, 'service[app]', :immediately
        end
        """

        result = estimate_conversion_complexity(resource_body)

        assert isinstance(result, str)

    def test_estimate_resource_with_ruby_logic(self):
        """Test complexity of resource with embedded Ruby."""
        resource_body = """
        ruby_block 'complex-logic' do
          block do
            results = search(:node, 'role:webserver')
            results.each do |node|
              puts node['hostname']
              node['ips'].each { |ip| puts ip }
            end
          end
        end
        """

        result = estimate_conversion_complexity(resource_body)

        assert isinstance(result, str)

    def test_estimate_resource_with_conditionals(self):
        """Test complexity with multiple conditions."""
        resource_body = """
        execute 'install-dep' do
          command 'apt-get install package'
          only_if { File.exist?('/etc/ubuntu-release') }
          not_if { which('package') }
          notifies :run, 'execute[config]'
        end
        """

        result = estimate_conversion_complexity(resource_body)

        assert isinstance(result, str)


class TestIntegrationAdvancedResource:
    """Integration tests for advanced resource conversion."""

    def test_parse_and_convert_complete_recipe(self):
        """Test parsing and converting complete recipe."""
        resource_body = """
        directory '/etc/myapp' do
          owner 'appuser'
          group 'appgroup'
          mode '0755'
        end

        template '/etc/myapp/config.yml' do
          source 'config.yml.erb'
          variables lazy { { servers: search(:node, 'role:backend') } }
          notifies :restart, 'service[myapp]'
          only_if { File.exist?('/etc/myapp') }
        end

        service 'myapp' do
          action :nothing
          subscribes :restart, 'template[/etc/myapp/config.yml]'
        end
        """

        guards = parse_resource_guards(resource_body)
        notifications = parse_resource_notifications(resource_body)
        searches = parse_resource_search(resource_body)
        complexity = estimate_conversion_complexity(resource_body)

        assert isinstance(guards, dict)
        assert isinstance(notifications, list)
        assert isinstance(searches, dict)
        assert isinstance(complexity, str)

    def test_parse_multiple_resources(self):
        """Test parsing multiple individual resources."""
        resources = [
            "service 'nginx' do\n  action :start\nend",
            "package 'nodejs' do\n  action :install\nend",
            "file '/tmp/app' do\n  content 'data'\nend",
        ]

        for resource in resources:
            guards = parse_resource_guards(resource)
            notifications = parse_resource_notifications(resource)
            assert isinstance(guards, dict)
            assert isinstance(notifications, list)


class TestPropertyBasedAdvancedResource:
    """Property-based tests for advanced resources."""

    @pytest.mark.parametrize("guard_type", ["only_if", "not_if"])
    def test_all_guard_types(self, guard_type):
        """Test conversion of all guard types."""
        condition = "test -f /etc/config"
        result = convert_guard_to_ansible_when(guard_type, condition)

        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "resource_type",
        [
            "service",
            "package",
            "template",
            "file",
            "execute",
            "directory",
            "ruby_block",
        ],
    )
    def test_parse_various_resource_types(self, resource_type):
        """Test parsing various resource types."""
        resource_body = f"""
        {resource_type} 'test-resource' do
          action :start
          only_if 'test -f /tmp/marker'
        end
        """

        guards = parse_resource_guards(resource_body)
        notifications = parse_resource_notifications(resource_body)

        assert isinstance(guards, dict)
        assert isinstance(notifications, list)
