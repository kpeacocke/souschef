"""Validation framework for Chef-to-Ansible conversions."""

import ast
import re
from enum import Enum
from typing import Any


class ValidationLevel(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(str, Enum):
    """Category of validation check."""

    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    BEST_PRACTICE = "best_practice"
    SECURITY = "security"
    PERFORMANCE = "performance"


class ValidationResult:
    """
    Result from a validation check.

    Attributes:
        level: Severity level of the validation issue.
        category: Category of the validation check.
        message: Human-readable message describing the issue.
        location: Optional location information (line number, resource name, etc.).
        suggestion: Optional suggestion for fixing the issue.

    """

    def __init__(
        self,
        level: ValidationLevel,
        category: ValidationCategory,
        message: str,
        location: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        """
        Initialize validation result.

        Args:
            level: Severity level.
            category: Validation category.
            message: Issue description.
            location: Optional location information.
            suggestion: Optional fix suggestion.

        """
        self.level = level
        self.category = category
        self.message = message
        self.location = location
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, Any]:
        """
        Convert validation result to dictionary.

        Returns:
            Dictionary representation of the validation result.

        """
        result = {
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
        }
        if self.location:
            result["location"] = self.location
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result

    def __repr__(self) -> str:
        """
        Return string representation of validation result.

        Returns:
            Formatted string representation.

        """
        parts = [f"[{self.level.value.upper()}] [{self.category.value}] {self.message}"]
        if self.location:
            parts.append(f"  Location: {self.location}")
        if self.suggestion:
            parts.append(f"  Suggestion: {self.suggestion}")
        return "\n".join(parts)


class ValidationEngine:
    """
    Engine for validating Chef-to-Ansible conversions.

    Provides validation across syntax, semantics, best practices, security,
    and performance categories.
    """

    def __init__(self) -> None:
        """Initialize validation engine."""
        self.results: list[ValidationResult] = []

    def validate_conversion(
        self, conversion_type: str, result: str
    ) -> list[ValidationResult]:
        """
        Validate a Chef-to-Ansible conversion.

        Args:
            conversion_type: Type of conversion ('recipe', 'resource', etc.).
            result: Resulting Ansible code or configuration.

        Returns:
            List of validation results.

        """
        self.results = []

        if conversion_type == "resource":
            self._validate_resource_conversion(result)
        elif conversion_type == "recipe":
            self._validate_recipe_conversion(result)
        elif conversion_type == "template":
            self._validate_template_conversion(result)
        elif conversion_type == "inspec":
            self._validate_inspec_conversion(result)
        else:
            self.results.append(
                ValidationResult(
                    ValidationLevel.WARNING,
                    ValidationCategory.SYNTAX,
                    f"Unknown conversion type: {conversion_type}",
                )
            )

        return self.results

    # Alias for backward compatibility
    validate_converted_content = validate_conversion

    def _add_result(
        self,
        level: ValidationLevel,
        category: ValidationCategory,
        message: str,
        location: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        """
        Add a validation result.

        Args:
            level: Severity level.
            category: Validation category.
            message: Issue description.
            location: Optional location.
            suggestion: Optional suggestion.

        """
        self.results.append(
            ValidationResult(level, category, message, location, suggestion)
        )

    def _validate_resource_conversion(self, result: str) -> None:
        """
        Validate Chef resource to Ansible task conversion.

        Args:
            result: Resulting Ansible task.

        """
        # Syntax validation
        self._validate_yaml_syntax(result)
        self._validate_ansible_module_exists(result)

        # Semantic validation
        self._validate_idempotency(result)
        self._validate_resource_dependencies(result)

        # Best practice validation
        self._validate_task_naming(result)
        self._validate_module_usage(result)

    def _validate_recipe_conversion(self, result: str) -> None:
        """
        Validate Chef recipe to Ansible playbook conversion.

        Args:
            result: Resulting Ansible playbook.

        """
        # Syntax validation
        self._validate_yaml_syntax(result)

        # Semantic validation
        self._validate_variable_usage(result)
        self._validate_handler_definitions(result)

        # Best practice validation
        self._validate_playbook_structure(result)

    def _validate_template_conversion(self, result: str) -> None:
        """
        Validate Chef template to Jinja2 conversion.

        Args:
            result: Resulting Jinja2 template.

        """
        # Syntax validation
        self._validate_jinja2_syntax(result)

        # Semantic validation
        self._validate_variable_references(result)

    def _validate_inspec_conversion(self, result: str) -> None:
        """
        Validate InSpec to test framework conversion.

        Args:
            result: Resulting test code.

        """
        # Syntax validation
        if "import pytest" in result:
            # Testinfra format
            self._validate_python_syntax(result)
        elif "---" in result:
            # Ansible assert format
            self._validate_yaml_syntax(result)

    def _validate_yaml_syntax(self, yaml_content: str) -> None:
        """
        Validate YAML syntax.

        Args:
            yaml_content: YAML content to validate.

        """
        try:
            import yaml
        except ImportError:
            # YAML library unavailable, skip validation
            return

        try:
            yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            self._add_result(
                ValidationLevel.ERROR,
                ValidationCategory.SYNTAX,
                f"Invalid YAML syntax: {e}",
                suggestion="Check YAML indentation and structure",
            )

    def _validate_ansible_module_exists(self, task: str) -> None:
        """
        Validate that Ansible module exists.

        Args:
            task: Ansible task YAML.

        """
        # Extract module name from task
        module_pattern = r"ansible\.builtin\.(\w+):"
        match = re.search(module_pattern, task)
        if match:
            module_name = match.group(1)
            # Check if it's a known module
            known_modules = {
                "package",
                "apt",
                "yum",
                "dnf",
                "service",
                "systemd",
                "template",
                "file",
                "copy",
                "command",
                "shell",
                "user",
                "group",
                "cron",
                "lineinfile",
                "blockinfile",
                "assert",
                "debug",
                "set_fact",
                "include_tasks",
                "import_tasks",
            }
            if module_name not in known_modules:
                self._add_result(
                    ValidationLevel.WARNING,
                    ValidationCategory.SYNTAX,
                    f"Unknown Ansible module: {module_name}",
                    suggestion="Verify module name and Ansible version support",
                )

    def _validate_idempotency(self, task: str) -> None:
        """
        Validate task idempotency.

        Args:
            task: Ansible task YAML.

        """
        # Check for command/shell without changed_when
        if (
            "ansible.builtin.command:" in task or "ansible.builtin.shell:" in task
        ) and "changed_when:" not in task:
            self._add_result(
                ValidationLevel.WARNING,
                ValidationCategory.BEST_PRACTICE,
                "Command/shell task without changed_when may report incorrect changes",
                suggestion='Add changed_when: "false" or appropriate condition',
            )

    def _validate_resource_dependencies(self, task: str) -> None:
        """
        Validate resource dependencies and ordering.

        Args:
            task: Ansible task YAML.

        """
        # Check for service before package
        if "ansible.builtin.service:" in task and "state:" in task:
            self._add_result(
                ValidationLevel.INFO,
                ValidationCategory.SEMANTIC,
                "Service task should have dependency on package installation",
                suggestion="Consider adding handler or dependency chain",
            )

    def _validate_task_naming(self, task: str) -> None:
        """
        Validate task naming conventions.

        Args:
            task: Ansible task YAML.

        """
        # Extract task name
        name_pattern = r"name:\s*([^\n]+)"
        match = re.search(name_pattern, task)
        if match:
            task_name = match.group(1).strip("\"'")
            # Check naming conventions
            if not task_name:
                self._add_result(
                    ValidationLevel.WARNING,
                    ValidationCategory.BEST_PRACTICE,
                    "Task has empty name",
                    suggestion="Provide descriptive task name",
                )
            elif len(task_name) < 10:
                self._add_result(
                    ValidationLevel.INFO,
                    ValidationCategory.BEST_PRACTICE,
                    "Task name is very short",
                    suggestion="Consider more descriptive task name",
                )

    def _validate_module_usage(self, task: str) -> None:
        """
        Validate proper module usage.

        Args:
            task: Ansible task YAML.

        """
        # Check for deprecated patterns
        if "ansible.builtin.file:" in task and "creates:" in task:
            self._add_result(
                ValidationLevel.WARNING,
                ValidationCategory.BEST_PRACTICE,
                "Using 'creates' with file module is unusual",
                suggestion="Consider using appropriate state parameter",
            )

    def _extract_jinja2_variables(self, content: str) -> set[str]:
        """
        Extract Jinja2 variable references from content.

        Args:
            content: Content containing Jinja2 variables.

        Returns:
            Set of variable names found.

        """
        var_pattern = r"\{\{\s*([\w.]+)\s*\}\}"
        return set(re.findall(var_pattern, content))

    def _validate_variable_usage(self, content: str) -> None:
        """
        Validate variable usage in playbook.

        Args:
            content: Playbook content.

        """
        # Check for undefined variables (basic check)
        variables = self._extract_jinja2_variables(content)

        # Check for common issues
        for var in variables:
            if var.startswith("ansible_") and var not in {
                "ansible_facts",
                "ansible_check_mode",
                "ansible_host",
                "ansible_port",
            }:
                self._add_result(
                    ValidationLevel.INFO,
                    ValidationCategory.SEMANTIC,
                    f"Variable '{var}' uses ansible_ prefix",
                    suggestion="Verify this is an Ansible built-in variable",
                )

    def _validate_handler_definitions(self, content: str) -> None:
        """
        Validate handler definitions and usage.

        Args:
            content: Playbook content.

        """
        # Check if handlers are referenced but not defined
        notify_pattern = r"notify:\s*([^\n]+)"
        notifies = set(re.findall(notify_pattern, content))

        if notifies and "handlers:" not in content:
            self._add_result(
                ValidationLevel.WARNING,
                ValidationCategory.SEMANTIC,
                "Tasks reference handlers but no handlers section found",
                suggestion="Add handlers section or remove notify directives",
            )

    def _validate_playbook_structure(self, content: str) -> None:
        """
        Validate playbook structure and organization.

        Args:
            content: Playbook content.

        """
        # Check for required playbook elements
        if "hosts:" not in content:
            self._add_result(
                ValidationLevel.ERROR,
                ValidationCategory.SYNTAX,
                "Playbook missing 'hosts' directive",
                suggestion="Add hosts directive to specify target hosts",
            )

        if "tasks:" not in content and "roles:" not in content:
            self._add_result(
                ValidationLevel.WARNING,
                ValidationCategory.SYNTAX,
                "Playbook has no tasks or roles",
                suggestion="Add tasks or roles to the playbook",
            )

    def _validate_jinja2_syntax(self, template: str) -> None:
        """
        Validate Jinja2 template syntax.

        Args:
            template: Jinja2 template content.

        """
        try:
            from jinja2 import Environment

            env = Environment(autoescape=True)
            env.parse(template)
        except Exception as e:
            self._add_result(
                ValidationLevel.ERROR,
                ValidationCategory.SYNTAX,
                f"Invalid Jinja2 syntax: {e}",
                suggestion="Check template syntax and variable references",
            )

    def _validate_variable_references(self, template: str) -> None:
        """
        Validate variable references in template.

        Args:
            template: Template content.

        """
        # Check for undefined variable patterns
        variables = self._extract_jinja2_variables(template)

        # Check for potential issues
        for var in variables:
            if "." in var:
                parts = var.split(".")
                if len(parts) > 5:
                    self._add_result(
                        ValidationLevel.INFO,
                        ValidationCategory.BEST_PRACTICE,
                        f"Deep variable nesting: {var}",
                        suggestion="Consider flattening variable structure",
                    )

    def _validate_python_syntax(self, code: str) -> None:
        """
        Validate Python code syntax.

        Args:
            code: Python code to validate.

        """
        try:
            ast.parse(code)
        except SyntaxError as e:
            self._add_result(
                ValidationLevel.ERROR,
                ValidationCategory.SYNTAX,
                f"Invalid Python syntax: {e}",
                suggestion="Check Python code syntax",
            )

    def get_summary(self) -> dict[str, int]:
        """
        Get summary of validation results.

        Returns:
            Dictionary with counts by level.

        """
        summary = {"errors": 0, "warnings": 0, "info": 0}
        for result in self.results:
            if result.level == ValidationLevel.ERROR:
                summary["errors"] += 1
            elif result.level == ValidationLevel.WARNING:
                summary["warnings"] += 1
            elif result.level == ValidationLevel.INFO:
                summary["info"] += 1
        return summary
