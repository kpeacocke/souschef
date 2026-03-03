"""Unit tests for the conversion rules engine module."""

from typing import Any

from souschef.converters.conversion_rules import (
    ConversionRule,
    RuleEngine,
    RulePriority,
    RuleType,
    build_default_rule_engine,
    create_custom_rule,
    create_package_rule,
    create_service_rule,
)


class TestRulePriority:
    """Test RulePriority enum."""

    def test_rule_priority_values(self) -> None:
        """Test RulePriority enum has correct values."""
        assert RulePriority.CRITICAL.value == 0
        assert RulePriority.HIGH.value == 1
        assert RulePriority.NORMAL.value == 2
        assert RulePriority.LOW.value == 3

    def test_rule_priority_ordering(self) -> None:
        """Test RulePriority ordering."""
        priorities = [RulePriority.LOW, RulePriority.CRITICAL, RulePriority.NORMAL]
        sorted_prio = sorted(priorities, key=lambda p: p.value)
        assert sorted_prio[0] == RulePriority.CRITICAL
        assert sorted_prio[-1] == RulePriority.LOW

    def test_rule_priority_comparison(self) -> None:
        """Test RulePriority comparisons."""
        assert RulePriority.CRITICAL.value < RulePriority.HIGH.value
        assert RulePriority.HIGH.value < RulePriority.NORMAL.value


class TestRuleType:
    """Test RuleType enum."""

    def test_rule_type_values(self) -> None:
        """Test RuleType enum has all defined types."""
        assert RuleType.PATTERN_MATCH.value == "pattern_match"
        assert RuleType.RESOURCE_NAME.value == "resource_name"
        assert RuleType.ATTRIBUTE_BASED.value == "attribute_based"
        assert RuleType.CONDITIONAL.value == "conditional"
        assert RuleType.CUSTOM.value == "custom"

    def test_rule_type_count(self) -> None:
        """Test RuleType has exactly 5 rule types."""
        assert len(list(RuleType)) == 5


class TestConversionRuleBasics:
    """Test ConversionRule basic functionality."""

    def test_rule_initialization(self) -> None:
        """Test ConversionRule initialization."""
        rule = ConversionRule(
            name="test_rule",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package$",
            description="Test rule",
        )
        assert rule.name == "test_rule"
        assert rule.rule_type == RuleType.PATTERN_MATCH
        assert rule.priority == RulePriority.NORMAL
        assert rule.pattern == r"^package$"
        assert rule.description == "Test rule"
        assert rule.enabled is True
        assert rule.conditions == []
        assert rule.transformation is None

    def test_rule_initialization_with_priority(self) -> None:
        """Test ConversionRule initialization with custom priority."""
        rule = ConversionRule(
            name="critical_rule",
            rule_type=RuleType.RESOURCE_NAME,
            priority=RulePriority.CRITICAL,
        )
        assert rule.priority == RulePriority.CRITICAL

    def test_rule_initialization_defaults(self) -> None:
        """Test ConversionRule initialization with defaults."""
        rule = ConversionRule(
            name="minimal",
            rule_type=RuleType.CUSTOM,
        )
        assert rule.priority == RulePriority.NORMAL
        assert rule.pattern is None
        assert rule.description == ""


class TestConversionRuleConditions:
    """Test ConversionRule condition management."""

    def test_add_condition(self) -> None:
        """Test adding a condition to a rule."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CONDITIONAL,
        )

        def condition(res: dict) -> bool:
            return res.get("type") == "package"

        rule.add_condition(condition)
        assert len(rule.conditions) == 1

    def test_add_multiple_conditions(self) -> None:
        """Test adding multiple conditions."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CONDITIONAL,
        )
        rule.add_condition(lambda res: res.get("type") == "package")
        rule.add_condition(lambda res: res.get("action") == "install")
        assert len(rule.conditions) == 2

    def test_conditions_order_preserved(self) -> None:
        """Test that conditions are evaluated in order."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CONDITIONAL,
        )

        def cond1(res: dict) -> bool:
            return res.get("step") == 1

        def cond2(res: dict) -> bool:
            return res.get("step") == 2

        rule.add_condition(cond1)
        rule.add_condition(cond2)
        assert rule.conditions[0] == cond1
        assert rule.conditions[1] == cond2


class TestConversionRuleMatching:
    """Test ConversionRule matching logic."""

    def test_pattern_matching_matches(self) -> None:
        """Test pattern matching when pattern matches."""
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package",
        )
        resource = {"type": "package", "body": "package 'httpd'"}
        assert rule.matches(resource) is True

    def test_pattern_matching_no_match(self) -> None:
        """Test pattern matching when pattern does not match."""
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package",
        )
        resource = {"type": "service", "body": "service 'httpd'"}
        assert rule.matches(resource) is False

    def test_resource_name_matching(self) -> None:
        """Test resource name matching."""
        rule = ConversionRule(
            name="httpd",
            rule_type=RuleType.RESOURCE_NAME,
            pattern=r"httpd",
        )
        resource = {"name": "httpd", "body": "package 'httpd'"}
        assert rule.matches(resource) is True

    def test_matching_with_conditions_all_pass(self) -> None:
        """Test matching with all conditions passing."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CONDITIONAL,
        )
        rule.add_condition(lambda res: res.get("type") == "package")
        rule.add_condition(lambda res: res.get("action") == "install")

        resource = {"type": "package", "action": "install"}
        assert rule.matches(resource) is True

    def test_matching_with_conditions_one_fails(self) -> None:
        """Test matching when one condition fails."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CONDITIONAL,
        )
        rule.add_condition(lambda res: res.get("type") == "package")
        rule.add_condition(lambda res: res.get("action") == "install")

        resource = {"type": "package", "action": "remove"}
        assert rule.matches(resource) is False

    def test_matching_without_pattern_or_conditions(self) -> None:
        """Test matching when rule has no pattern or conditions."""
        rule = ConversionRule(
            name="default",
            rule_type=RuleType.CUSTOM,
        )
        resource = {"type": "any", "body": "anything"}
        assert rule.matches(resource) is True

    def test_matching_disabled_rule(self) -> None:
        """Test that disabled rules don't match."""
        rule = ConversionRule(
            name="disabled",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"package",
        )
        rule.enabled = False
        resource = {"type": "package"}
        assert rule.matches(resource) is False


class TestConversionRuleTransformation:
    """Test ConversionRule transformation logic."""

    def test_set_transformation(self) -> None:
        """Test setting a transformation function."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CUSTOM,
        )

        def trans(body: str) -> str:
            return "ansible: " + body

        rule.set_transformation(trans)
        assert rule.transformation == trans

    def test_apply_with_transformation(self) -> None:
        """Test applying a transformation."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CUSTOM,
        )
        rule.set_transformation(lambda body: "package: " + body)
        result = rule.apply("httpd")
        assert result == "package: httpd"

    def test_apply_without_transformation(self) -> None:
        """Test applying when no transformation is set."""
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CUSTOM,
        )
        result = rule.apply("httpd")
        assert result == "httpd"

    def test_apply_with_complex_transformation(self) -> None:
        """Test applying complex transformation."""
        rule = ConversionRule(
            name="service",
            rule_type=RuleType.RESOURCE_NAME,
        )
        rule.set_transformation(lambda body: "ansible.builtin.service:\n  name: httpd")
        result = rule.apply("service 'httpd' do")
        assert "ansible.builtin.service" in result


class TestConversionRuleExport:
    """Test ConversionRule export functionality."""

    def test_to_dict_basic(self) -> None:
        """Test exporting rule to dictionary."""
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package$",
            description="Convert package resources",
        )
        data = rule.to_dict()
        assert data["name"] == "package"
        assert data["type"] == "pattern_match"
        assert data["priority"] == 2
        assert data["pattern"] == r"^package$"
        assert data["description"] == "Convert package resources"
        assert data["enabled"] is True

    def test_to_dict_with_transformation(self) -> None:
        """Test exporting rule with transformation."""
        rule = ConversionRule(
            name="service",
            rule_type=RuleType.RESOURCE_NAME,
        )
        rule.set_transformation(lambda body: "transformed")
        data = rule.to_dict()
        assert "has_transformation" in data
        assert data["has_transformation"] is True
        assert data["enabled"] is True


class TestRuleEngine:
    """Test RuleEngine functionality."""

    def test_engine_initialization(self) -> None:
        """Test RuleEngine initialization."""
        engine = RuleEngine()
        assert len(engine.rules) == 0
        assert engine.default_rule is None

    def test_register_rule(self) -> None:
        """Test registering a rule."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package$",
        )
        engine.register_rule(rule)
        assert len(engine.rules) == 1
        assert engine.get_rule("package") == rule

    def test_register_multiple_rules(self) -> None:
        """Test registering multiple rules."""
        engine = RuleEngine()
        rule1 = ConversionRule(name="rule1", rule_type=RuleType.PATTERN_MATCH)
        rule2 = ConversionRule(name="rule2", rule_type=RuleType.RESOURCE_NAME)
        engine.register_rule(rule1)
        engine.register_rule(rule2)
        assert len(engine.rules) == 2

    def test_unregister_rule(self) -> None:
        """Test unregistering a rule."""
        engine = RuleEngine()
        rule = ConversionRule(name="test", rule_type=RuleType.CUSTOM)
        engine.register_rule(rule)
        assert engine.unregister_rule("test") is True
        assert len(engine.rules) == 0

    def test_unregister_nonexistent_rule(self) -> None:
        """Test unregistering a non-existent rule."""
        engine = RuleEngine()
        assert engine.unregister_rule("nonexistent") is False

    def test_get_rule_exists(self) -> None:
        """Test getting a registered rule."""
        engine = RuleEngine()
        rule = ConversionRule(name="test", rule_type=RuleType.CUSTOM)
        engine.register_rule(rule)
        retrieved = engine.get_rule("test")
        assert retrieved == rule

    def test_get_rule_not_exists(self) -> None:
        """Test getting a non-existent rule."""
        engine = RuleEngine()
        assert engine.get_rule("nonexistent") is None

    def test_set_default_rule(self) -> None:
        """Test setting a default rule."""
        engine = RuleEngine()
        rule = ConversionRule(name="default", rule_type=RuleType.CUSTOM)
        engine.set_default_rule(rule)
        assert engine.default_rule == rule

    def test_find_matching_rule_single_match(self) -> None:
        """Test finding a matching rule."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package",
        )
        engine.register_rule(rule)

        resource = {"type": "package", "body": "package 'httpd'"}
        matched = engine.find_matching_rule(resource)
        assert matched == rule

    def test_find_matching_rule_no_match(self) -> None:
        """Test finding a rule when no rules match."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package",
        )
        engine.register_rule(rule)

        resource = {"type": "service", "body": "service 'httpd'"}
        matched = engine.find_matching_rule(resource)
        assert matched is None

    def test_find_matching_rule_priority(self) -> None:
        """Test that higher priority rules are matched first."""
        engine = RuleEngine()
        low_rule = ConversionRule(
            name="low",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.LOW,
        )
        critical_rule = ConversionRule(
            name="critical",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.CRITICAL,
        )
        engine.register_rule(low_rule)
        engine.register_rule(critical_rule)

        resource: dict[str, Any] = {}
        matched = engine.find_matching_rule(resource)
        assert matched == critical_rule

    def test_find_all_matching_rules(self) -> None:
        """Test finding all matching rules."""
        engine = RuleEngine()
        rule1 = ConversionRule(
            name="rule1",
            rule_type=RuleType.CUSTOM,
        )
        rule2 = ConversionRule(
            name="rule2",
            rule_type=RuleType.CUSTOM,
        )
        default_rule = ConversionRule(
            name="default",
            rule_type=RuleType.CUSTOM,
        )
        engine.register_rule(rule1)
        engine.register_rule(rule2)
        engine.set_default_rule(default_rule)

        resource = {"body": ""}
        matches = engine.find_all_matching_rules(resource)
        assert len(matches) == 2  # Only registered rules, not default rule

    def test_apply_rule_success(self) -> None:
        """Test successfully applying a rule."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CUSTOM,
        )
        rule.set_transformation(lambda body: "transformed_" + body)
        engine.register_rule(rule)

        resource = {"body": "original"}
        result, applied_rule = engine.apply_rule(resource)
        assert result == "transformed_original"
        assert applied_rule == rule

    def test_apply_rule_no_match(self) -> None:
        """Test applying rule when no rule matches."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package$",
        )
        engine.register_rule(rule)

        resource = {"type": "service", "body": "content"}
        result, applied_rule = engine.apply_rule(resource)
        assert result is None
        assert applied_rule is None

    def test_apply_rule_with_default(self) -> None:
        """Test applying rule with default fallback."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="package",
            rule_type=RuleType.PATTERN_MATCH,
            pattern=r"^package$",
        )
        default_rule = ConversionRule(
            name="default",
            rule_type=RuleType.CUSTOM,
        )
        default_rule.set_transformation(lambda body: "default_" + body)
        engine.register_rule(rule)
        engine.set_default_rule(default_rule)

        resource = {"type": "service", "body": "content"}
        result, applied_rule = engine.apply_rule(resource)
        assert result == "default_content"
        assert applied_rule == default_rule

    def test_get_statistics(self) -> None:
        """Test getting engine statistics."""
        engine = RuleEngine()
        rule1 = ConversionRule(name="rule1", rule_type=RuleType.CUSTOM)
        rule2 = ConversionRule(name="rule2", rule_type=RuleType.CUSTOM)
        rule2.enabled = False
        engine.register_rule(rule1)
        engine.register_rule(rule2)

        stats = engine.get_statistics()
        assert stats["total_rules"] == 2
        assert stats["enabled_rules"] == 1
        assert stats["disabled_rules"] == 1
        assert stats["has_default_rule"] is False

    def test_get_statistics_with_default(self) -> None:
        """Test statistics when default rule is set."""
        engine = RuleEngine()
        default = ConversionRule(name="default", rule_type=RuleType.CUSTOM)
        engine.set_default_rule(default)
        stats = engine.get_statistics()
        assert stats["has_default_rule"] is True

    def test_export_rules(self) -> None:
        """Test exporting all rules."""
        engine = RuleEngine()
        rule = ConversionRule(
            name="test",
            rule_type=RuleType.CUSTOM,
            description="Test rule",
        )
        engine.register_rule(rule)

        exported = engine.export_rules()
        assert "rules" in exported
        assert "version" in exported
        assert "statistics" in exported
        assert len(exported["rules"]) == 1
        assert exported["rules"][0]["name"] == "test"


class TestFactoryFunctions:
    """Test factory functions for creating rules."""

    def test_create_package_rule(self) -> None:
        """Test creating a package rule."""
        rule = create_package_rule()
        assert rule.name == "package_resource"
        assert rule.rule_type == RuleType.RESOURCE_NAME
        assert rule.priority == RulePriority.HIGH

    def test_create_package_rule_transformation(self) -> None:
        """Test package rule transformation."""
        rule = create_package_rule()
        result = rule.apply("package 'httpd'")
        assert "ansible.builtin.package" in result

    def test_create_service_rule(self) -> None:
        """Test creating a service rule."""
        rule = create_service_rule()
        assert rule.name == "service_resource"
        assert rule.rule_type == RuleType.RESOURCE_NAME

    def test_create_service_rule_transformation(self) -> None:
        """Test service rule transformation."""
        rule = create_service_rule()
        result = rule.apply("service 'httpd' do")
        assert "ansible.builtin.service" in result

    def test_create_custom_rule(self) -> None:
        """Test creating a custom rule."""
        rule = create_custom_rule(
            name="custom_rule",
            pattern=r"custom_.*",
            description="Custom test rule",
            transformation=lambda body: "custom_" + body,
        )
        assert rule.name == "custom_rule"
        assert rule.pattern == r"custom_.*"
        assert rule.description == "Custom test rule"

    def test_create_custom_rule_with_transformation(self) -> None:
        """Test creating custom rule with transformation."""

        def transformation(body: str) -> str:
            return "custom_" + body

        rule = create_custom_rule(
            name="test",
            pattern=r"test",
            description="Test rule",
            transformation=transformation,
        )
        assert rule.transformation == transformation
        result = rule.apply("test_body")
        assert result == "custom_test_body"

    def test_build_default_rule_engine(self) -> None:
        """Test building a default rule engine."""
        engine = build_default_rule_engine()
        assert len(engine.rules) >= 2  # At least package and service

    def test_default_engine_has_package_rule(self) -> None:
        """Test default engine has package rule."""
        engine = build_default_rule_engine()
        package_rule = engine.get_rule("package_resource")
        assert package_rule is not None
        assert package_rule.name == "package_resource"

    def test_default_engine_has_service_rule(self) -> None:
        """Test default engine has service rule."""
        engine = build_default_rule_engine()
        service_rule = engine.get_rule("service_resource")
        assert service_rule is not None
        assert service_rule.name == "service_resource"

    def test_default_engine_functionality(self) -> None:
        """Test default engine can process resources."""
        engine = build_default_rule_engine()
        package_resource = {"type": "package"}
        _, rule = engine.apply_rule(package_resource)
        assert rule is not None


class TestRuleEngineIntegration:
    """Integration tests for rule engine."""

    def test_complex_rule_workflow(self) -> None:
        """Test complex workflow with multiple rules."""
        engine = build_default_rule_engine()

        # Add custom rule
        custom_rule = create_custom_rule(
            name="custom_service",
            pattern=r"custom_svc_.*",
            description="Custom service rule",
            transformation=lambda b: f"custom_service: {b}",
        )
        engine.register_rule(custom_rule)

        # Test package
        _, pkg_rule = engine.apply_rule({"type": "package", "body": "package"})
        assert pkg_rule is not None

        # Test service
        _, svc_rule = engine.apply_rule({"type": "service", "body": "service 'test'"})
        assert svc_rule is not None

        # Test custom
        _, custom_matched_rule = engine.apply_rule(
            {"type": "custom_svc_test", "body": "custom_svc_test"}
        )
        assert custom_matched_rule is not None

    def test_rule_priority_affects_selection(self) -> None:
        """Test that priority affects rule selection."""
        engine = RuleEngine()

        high_rule = ConversionRule(
            name="high_priority",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.HIGH,
        )
        low_rule = ConversionRule(
            name="low_priority",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.LOW,
        )

        engine.register_rule(low_rule)
        engine.register_rule(high_rule)

        matched = engine.find_matching_rule({})
        assert matched is not None
        assert matched.name == "high_priority"

    def test_conditional_rule_with_multiple_attributes(self) -> None:
        """Test rule with multiple conditional checks."""
        rule = ConversionRule(
            name="complex",
            rule_type=RuleType.CONDITIONAL,
        )
        rule.add_condition(lambda r: r.get("type") == "service")
        rule.add_condition(lambda r: r.get("action") == "enable")
        rule.add_condition(lambda r: r.get("provider") == "systemd")

        # All conditions met
        matching_resource = {
            "type": "service",
            "action": "enable",
            "provider": "systemd",
        }
        assert rule.matches(matching_resource) is True

        # One condition fails
        nonmatching_resource = {
            "type": "service",
            "action": "enable",
            "provider": "upstart",
        }
        assert rule.matches(nonmatching_resource) is False

    def test_engine_statistics_comprehensive(self) -> None:
        """Test comprehensive statistics collection."""
        engine = RuleEngine()
        rule1 = ConversionRule(name="rule1", rule_type=RuleType.CUSTOM)
        rule2 = ConversionRule(name="rule2", rule_type=RuleType.CUSTOM)
        rule3 = ConversionRule(name="rule3", rule_type=RuleType.CUSTOM)
        rule3.enabled = False

        engine.register_rule(rule1)
        engine.register_rule(rule2)
        engine.register_rule(rule3)

        stats = engine.get_statistics()
        assert stats["total_rules"] == 3
        assert stats["enabled_rules"] == 2
        assert stats["disabled_rules"] == 1
        assert len(stats["rules"]) == 3
