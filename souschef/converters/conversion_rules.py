"""
V2.2: Custom rule engine for Chef to Ansible resource conversion.

Provides extensible rule system for defining custom resource conversion patterns,
allowing users to define how specific Chef resources should be converted to Ansible.

Rules support pattern matching, conditional logic, and custom transformation functions.
"""

import re
from collections.abc import Callable
from enum import Enum
from typing import Any

# Type alias for rule application result
RuleResult = tuple[str | None, "ConversionRule | None"]


class RulePriority(Enum):
    """Rule priority levels for evaluation order."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class RuleType(Enum):
    """Types of conversion rules."""

    PATTERN_MATCH = "pattern_match"
    RESOURCE_NAME = "resource_name"
    ATTRIBUTE_BASED = "attribute_based"
    CONDITIONAL = "conditional"
    CUSTOM = "custom"


class ConversionRule:
    """
    Represents a single Chef to Ansible conversion rule.

    A rule defines conditions under which a resource conversion should be applied
    and provides the transformation logic.
    """

    def __init__(
        self,
        name: str,
        rule_type: RuleType,
        priority: RulePriority = RulePriority.NORMAL,
        pattern: str | None = None,
        description: str = "",
    ) -> None:
        """
        Initialize conversion rule.

        Args:
            name: Unique name for the rule.
            rule_type: Type of rule.
            priority: Priority for rule evaluation (lower = earlier).
            pattern: Optional regex pattern for matching.
            description: Human-readable rule description.

        """
        self.name = name
        self.rule_type = rule_type
        self.priority = priority
        self.pattern = pattern
        self.description = description
        self.conditions: list[Callable[[dict[str, Any]], bool]] = []
        self.transformation: Callable[[str], str] | None = None
        self.enabled = True

    def add_condition(self, condition: Callable[[dict[str, Any]], bool]) -> None:
        """Add a condition that must be satisfied."""
        self.conditions.append(condition)

    def set_transformation(self, transformation: Callable[[str], str]) -> None:
        """Set the transformation function."""
        self.transformation = transformation

    def matches(self, resource: dict[str, Any]) -> bool:
        """
        Check if rule matches the given resource.

        Args:
            resource: Resource dictionary with name, type, body, etc.

        Returns:
            True if all conditions are satisfied.

        """
        if not self.enabled:
            return False

        if self.pattern:
            pattern_match = bool(re.search(self.pattern, resource.get("body", "")))
            if not pattern_match:
                return False

        return all(condition(resource) for condition in self.conditions)

    def apply(self, resource_body: str) -> str:
        """
        Apply rule transformation to resource.

        Args:
            resource_body: The Chef resource code.

        Returns:
            Transformed Ansible representation.

        """
        if self.transformation:
            return self.transformation(resource_body)
        return resource_body

    def to_dict(self) -> dict[str, Any]:
        """Export rule as dictionary."""
        return {
            "name": self.name,
            "type": self.rule_type.value,
            "priority": self.priority.value,
            "description": self.description,
            "pattern": self.pattern,
            "enabled": self.enabled,
            "conditions_count": len(self.conditions),
            "has_transformation": self.transformation is not None,
        }


class RuleEngine:
    """
    Engine for managing and applying conversion rules.

    Maintains a set of rules (sorted by priority) and evaluates them against
    Chef resources to determine the best conversion approach.
    """

    def __init__(self) -> None:
        """Initialize the rule engine."""
        self.rules: list[ConversionRule] = []
        self.default_rule: ConversionRule | None = None
        self._rule_index: dict[str, ConversionRule] = {}

    def register_rule(self, rule: ConversionRule) -> None:
        """
        Register a conversion rule.

        Args:
            rule: The conversion rule to register.

        """
        self.rules.append(rule)
        self._rule_index[rule.name] = rule
        self._sort_rules()

    def unregister_rule(self, rule_name: str) -> bool:
        """
        Unregister a rule by name.

        Args:
            rule_name: Name of the rule to remove.

        Returns:
            True if rule was found and removed.

        """
        if rule_name in self._rule_index:
            rule = self._rule_index[rule_name]
            self.rules.remove(rule)
            del self._rule_index[rule_name]
            return True
        return False

    def get_rule(self, rule_name: str) -> ConversionRule | None:
        """Get a rule by name."""
        return self._rule_index.get(rule_name)

    def set_default_rule(self, rule: ConversionRule) -> None:
        """Set default rule to apply when no other rules match."""
        self.default_rule = rule

    def _sort_rules(self) -> None:
        """Sort rules by priority (lower priority value = higher priority)."""
        self.rules.sort(key=lambda r: r.priority.value)

    def find_matching_rule(self, resource: dict[str, Any]) -> ConversionRule | None:
        """
        Find the first rule that matches the resource.

        Args:
            resource: Resource dictionary.

        Returns:
            Matching rule or default rule if no match found.

        """
        for rule in self.rules:
            if rule.matches(resource):
                return rule
        return self.default_rule

    def find_all_matching_rules(self, resource: dict[str, Any]) -> list[ConversionRule]:
        """Find all rules that match the resource."""
        return [rule for rule in self.rules if rule.matches(resource)]

    def apply_rule(self, resource: dict[str, Any]) -> RuleResult:
        """
        Apply best matching rule to resource.

        Args:
            resource: Resource dictionary.

        Returns:
            Tuple of (transformed_code, applied_rule).

        """
        rule = self.find_matching_rule(resource)
        if rule:
            transformed = rule.apply(resource.get("body", ""))
            return transformed, rule
        return None, None

    def get_statistics(self) -> dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "disabled_rules": sum(1 for r in self.rules if not r.enabled),
            "has_default_rule": self.default_rule is not None,
            "rules": [r.to_dict() for r in self.rules],
        }

    def export_rules(self) -> dict[str, Any]:
        """Export all rules as dictionary."""
        return {
            "version": "1.0",
            "rules": [r.to_dict() for r in self.rules],
            "default_rule": (self.default_rule.name if self.default_rule else None),
            "statistics": self.get_statistics(),
        }


def create_package_rule() -> ConversionRule:
    """Create rule for package resource conversion."""
    rule = ConversionRule(
        name="package_resource",
        rule_type=RuleType.RESOURCE_NAME,
        priority=RulePriority.HIGH,
        description="Convert Chef package resources to Ansible package module",
    )

    def package_condition(resource: dict[str, Any]) -> bool:
        """Check if resource is a package resource."""
        return "package" in resource.get("body", "")

    rule.add_condition(package_condition)

    def package_transformation(body: str) -> str:
        """Transform package resource to Ansible task."""
        return """- name: Install package
  ansible.builtin.package:
    name: "{{ package_name }}"
    state: present"""

    rule.set_transformation(package_transformation)
    return rule


def create_service_rule() -> ConversionRule:
    """Create rule for service resource conversion."""
    rule = ConversionRule(
        name="service_resource",
        rule_type=RuleType.RESOURCE_NAME,
        priority=RulePriority.HIGH,
        description="Convert Chef service resources to Ansible service module",
    )

    def service_condition(resource: dict[str, Any]) -> bool:
        """Check if resource is a service resource."""
        body = resource.get("body", "")
        return body.startswith("service ")

    rule.add_condition(service_condition)

    def service_transformation(body: str) -> str:
        """Transform service resource to Ansible task."""
        action = "started"
        if "stop" in body:
            action = "stopped"
        elif "restart" in body:
            action = "restarted"

        return f"""- name: Manage service
  ansible.builtin.service:
    name: "{{ service_name }}"
    state: {action}
    enabled: yes"""

    rule.set_transformation(service_transformation)
    return rule


def create_custom_rule(
    name: str,
    pattern: str,
    description: str,
    transformation: Callable[[str], str],
) -> ConversionRule:
    """
    Create a custom conversion rule.

    Args:
        name: Rule name.
        pattern: Regex pattern to match.
        description: Rule description.
        transformation: Function to transform matched resources.

    Returns:
        New conversion rule.

    """
    rule = ConversionRule(
        name=name,
        rule_type=RuleType.CUSTOM,
        priority=RulePriority.NORMAL,
        pattern=pattern,
        description=description,
    )
    rule.set_transformation(transformation)
    return rule


def build_default_rule_engine() -> RuleEngine:
    """
    Build a rule engine with default set of rules.

    Returns:
        Configured rule engine with standard conversion rules.

    """
    engine = RuleEngine()

    # Add default rules
    engine.register_rule(create_package_rule())
    engine.register_rule(create_service_rule())

    # Set a basic default rule
    default = ConversionRule(
        name="default",
        rule_type=RuleType.PATTERN_MATCH,
        priority=RulePriority.LOW,
        description="Default rule for unmatched resources",
    )

    def default_transformation(body: str) -> str:
        """Wrap resource in debug task for manual conversion."""
        return """- name: TODO - Manual conversion required
  debug:
    msg: "This resource requires manual conversion"
  # Original resource code:
  # ' + body.replace('\n', '\n  # ') + '"
"""

    default.set_transformation(default_transformation)
    engine.set_default_rule(default)

    return engine
