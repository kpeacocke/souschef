"""Tests for converters/advanced_resource.py module."""

from souschef.converters.advanced_resource import (
    convert_guard_to_ansible_when,
    estimate_conversion_complexity,
    generate_advanced_handler_yaml,
    parse_resource_guards,
    parse_resource_notifications,
    parse_resource_search,
)


class TestParseResourceGuards:
    """Test parse_resource_guards function."""

    def test_only_if_guard(self) -> None:
        """Should extract only_if guard."""
        resource_body = 'only_if "test -f /tmp/file"'
        result = parse_resource_guards(resource_body)
        assert result["only_if"] == "test -f /tmp/file"

    def test_not_if_guard(self) -> None:
        """Should extract not_if guard."""
        resource_body = 'not_if "test -f /tmp/file"'
        result = parse_resource_guards(resource_body)
        assert result["not_if"] == "test -f /tmp/file"

    def test_ignore_failure_guard(self) -> None:
        """Should extract ignore_failure guard."""
        resource_body = "ignore_failure true"
        result = parse_resource_guards(resource_body)
        assert result["ignore_failure"] is True

    def test_multiple_guards(self) -> None:
        """Should extract multiple guards."""
        resource_body = """
        only_if "test -f /tmp/file"
        not_if "/usr/bin/test -f /var/lock"
        ignore_failure true
        """
        result = parse_resource_guards(resource_body)
        assert "only_if" in result
        assert "not_if" in result
        assert result["ignore_failure"] is True

    def test_no_guards(self) -> None:
        """Should return empty dict when no guards present."""
        resource_body = "action :install"
        result = parse_resource_guards(resource_body)
        assert result == {}

    def test_single_quoted_guard(self) -> None:
        """Should handle single-quoted guards."""
        resource_body = "only_if 'test -d /var/log'"
        result = parse_resource_guards(resource_body)
        assert result["only_if"] == "test -d /var/log"


class TestParseResourceNotifications:
    """Test parse_resource_notifications function."""

    def test_notifies_immediately(self) -> None:
        """Should extract notifies with immediately timing."""
        resource_body = """
        notifies :restart, 'service[apache2]', :immediately
        """
        result = parse_resource_notifications(resource_body)
        assert len(result) == 1
        assert result[0]["type"] == "notifies"
        assert result[0]["action"] == "restart"
        assert result[0]["resource_type"] == "service"
        assert result[0]["resource_name"] == "apache2"
        assert result[0]["timing"] == "immediately"

    def test_notifies_delayed(self) -> None:
        """Should extract notifies with delayed timing."""
        resource_body = """
        notifies :run, 'execute[rebuild]', :delayed
        """
        result = parse_resource_notifications(resource_body)
        assert len(result) == 1
        assert result[0]["timing"] == "delayed"

    def test_subscribes(self) -> None:
        """Should extract subscribes subscription."""
        resource_body = """
        subscribes :notify, 'template[config]'
        """
        result = parse_resource_notifications(resource_body)
        assert len(result) == 1
        assert result[0]["type"] == "subscribes"
        assert result[0]["action"] == "notify"
        assert result[0]["resource_type"] == "template"
        assert result[0]["resource_name"] == "config"

    def test_multiple_notifications(self) -> None:
        """Should extract multiple notifications."""
        resource_body = """
        notifies :restart, 'service[nginx]', :immediately
        notifies :reload, 'service[php-fpm]', :delayed
        subscribes :create, 'file[lockfile]'
        """
        result = parse_resource_notifications(resource_body)
        assert len(result) == 3

    def test_no_notifications(self) -> None:
        """Should return empty list when no notifications present."""
        resource_body = "action :install"
        result = parse_resource_notifications(resource_body)
        assert result == []


class TestConvertGuardToAnsibleWhen:
    """Test convert_guard_to_ansible_when function."""

    def test_only_if_conversion(self) -> None:
        """Should convert only_if to ansible when clause."""
        result = convert_guard_to_ansible_when("only_if", "test -f /tmp/file")
        assert result == "command_result.rc == 0"

    def test_not_if_conversion(self) -> None:
        """Should convert not_if to ansible when clause."""
        result = convert_guard_to_ansible_when("not_if", "test -f /tmp/file")
        assert result == "command_result.rc != 0"

    def test_unknown_guard_type(self) -> None:
        """Should return empty string for unknown guard type."""
        result = convert_guard_to_ansible_when("unknown", "condition")
        assert result == ""


class TestParseResourceSearch:
    """Test parse_resource_search function."""

    def test_search_extraction(self) -> None:
        """Should extract search pattern."""
        resource_body = "search(:node, 'role:webserver')"
        result = parse_resource_search(resource_body)
        assert result["index"] == "node"
        assert result["query"] == "role:webserver"
        assert "recommended_conversion" in result

    def test_search_with_role_index(self) -> None:
        """Should extract search with role index."""
        resource_body = "search(:role, 'name:webserver')"
        result = parse_resource_search(resource_body)
        assert result["index"] == "role"
        assert result["query"] == "name:webserver"

    def test_no_search(self) -> None:
        """Should return empty dict when no search present."""
        resource_body = "action :install"
        result = parse_resource_search(resource_body)
        assert result == {}


class TestGenerateAdvancedHandlerYaml:
    """Test generate_advanced_handler_yaml function."""

    def test_empty_notifications(self) -> None:
        """Should return empty string for empty notifications."""
        result = generate_advanced_handler_yaml([])
        assert result == ""

    def test_single_notification(self) -> None:
        """Should generate handler YAML for single notification."""
        notifications = [
            {
                "type": "notifies",
                "action": "restart",
                "resource_type": "service",
                "resource_name": "apache2",
                "timing": "delayed",
            }
        ]
        result = generate_advanced_handler_yaml(notifications)
        assert "handlers:" in result
        assert "service_apache2_restart" in result
        assert "apache2" in result

    def test_immediate_handler(self) -> None:
        """Should mark immediate handlers with listen."""
        notifications = [
            {
                "type": "notifies",
                "action": "reload",
                "resource_type": "service",
                "resource_name": "nginx",
                "timing": "immediately",
            }
        ]
        result = generate_advanced_handler_yaml(notifications)
        assert "immediate_notify" in result

    def test_multiple_handlers(self) -> None:
        """Should generate handlers for multiple notifications."""
        notifications = [
            {
                "type": "notifies",
                "action": "restart",
                "resource_type": "service",
                "resource_name": "apache2",
                "timing": "delayed",
            },
            {
                "type": "subscribes",
                "action": "notify",
                "resource_type": "file",
                "resource_name": "config",
            },
        ]
        result = generate_advanced_handler_yaml(notifications)
        assert "service_apache2_restart" in result
        assert "file_config_notify" in result


class TestEstimateConversionComplexity:
    """Test estimate_conversion_complexity function."""

    def test_simple_resource(self) -> None:
        """Should classify simple resource."""
        resource_body = "action :install"
        result = estimate_conversion_complexity(resource_body)
        assert result == "simple"

    def test_moderate_with_guards(self) -> None:
        """Should classify resource with guards as moderate."""
        resource_body = """
        only_if "test -f /tmp/file"
        not_if "test -d /var"
        """
        result = estimate_conversion_complexity(resource_body)
        assert result == "moderate"

    def test_moderate_with_search(self) -> None:
        """Should classify resource with search as moderate."""
        resource_body = "search(:node, 'role:webserver')"
        result = estimate_conversion_complexity(resource_body)
        assert result == "moderate"

    def test_complex_multiple_factors(self) -> None:
        """Should classify resource with multiple complexity factors."""
        resource_body = """
        only_if "test -f /file"
        not_if "test -d /dir"
        notifies :restart, 'service[apache2]'
        search(:node, 'role:web')
        lazy true
        """
        result = estimate_conversion_complexity(resource_body)
        assert result == "complex"

    def test_simple_with_notification(self) -> None:
        """Should classify resource with single notification as simple."""
        resource_body = "notifies :restart, 'service[apache2]'"
        result = estimate_conversion_complexity(resource_body)
        assert result == "simple"

    def test_moderate_with_multiple_actions(self) -> None:
        """Should classify resource with multiple actions as moderate."""
        resource_body = """
        action :create
        action :delete
        action :install
        """
        result = estimate_conversion_complexity(resource_body)
        assert result == "moderate"

    def test_simple_with_lazy_only(self) -> None:
        """Should classify lazy-only resource as moderate when with guards."""
        resource_body = """
        lazy true
        only_if "test -f /file"
        """
        result = estimate_conversion_complexity(resource_body)
        assert result == "moderate"

    def test_simple_single_action(self) -> None:
        """Should return simple for single action (only 1 complexity factor)."""
        resource_body = "package 'nginx'\naction :install"
        result = estimate_conversion_complexity(resource_body)
        assert result == "simple"

    def test_simple_no_complexity_factors(self) -> None:
        """Should return simple for truly clean resource body."""
        resource_body = "package 'nginx'"
        result = estimate_conversion_complexity(resource_body)
        assert result == "simple"
