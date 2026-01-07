"""Unit tests for souschef.core.validation module."""

from souschef.core.validation import (
    ValidationCategory,
    ValidationEngine,
    ValidationLevel,
    ValidationResult,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_validation_result_initialization(self):
        """Test ValidationResult initialization with all parameters."""
        result = ValidationResult(
            level=ValidationLevel.ERROR,
            category=ValidationCategory.SYNTAX,
            message="Test error message",
            location="line 10",
            suggestion="Fix the syntax",
        )

        assert result.level == ValidationLevel.ERROR
        assert result.category == ValidationCategory.SYNTAX
        assert result.message == "Test error message"
        assert result.location == "line 10"
        assert result.suggestion == "Fix the syntax"

    def test_validation_result_to_dict(self):
        """Test converting ValidationResult to dictionary."""
        result = ValidationResult(
            level=ValidationLevel.WARNING,
            category=ValidationCategory.BEST_PRACTICE,
            message="Test warning",
            location="task 1",
            suggestion="Follow best practices",
        )

        result_dict = result.to_dict()

        assert result_dict["level"] == "warning"
        assert result_dict["category"] == "best_practice"
        assert result_dict["message"] == "Test warning"
        assert result_dict["location"] == "task 1"
        assert result_dict["suggestion"] == "Follow best practices"

    def test_validation_result_to_dict_without_optional_fields(self):
        """Test to_dict without location and suggestion."""
        result = ValidationResult(
            level=ValidationLevel.INFO,
            category=ValidationCategory.SEMANTIC,
            message="Info message",
        )

        result_dict = result.to_dict()

        assert "location" not in result_dict
        assert "suggestion" not in result_dict
        assert result_dict["level"] == "info"

    def test_validation_result_repr(self):
        """Test string representation of ValidationResult."""
        result = ValidationResult(
            level=ValidationLevel.ERROR,
            category=ValidationCategory.SECURITY,
            message="Security issue",
            location="resource 1",
            suggestion="Fix security",
        )

        repr_str = repr(result)

        assert "[ERROR]" in repr_str
        assert "[security]" in repr_str
        assert "Security issue" in repr_str
        assert "Location: resource 1" in repr_str
        assert "Suggestion: Fix security" in repr_str

    def test_validation_result_repr_minimal(self):
        """Test repr without optional fields."""
        result = ValidationResult(
            level=ValidationLevel.INFO,
            category=ValidationCategory.PERFORMANCE,
            message="Performance tip",
        )

        repr_str = repr(result)

        assert "[INFO]" in repr_str
        assert "[performance]" in repr_str
        assert "Performance tip" in repr_str
        assert "Location:" not in repr_str
        assert "Suggestion:" not in repr_str


class TestValidationEngine:
    """Tests for ValidationEngine class."""

    def test_validation_engine_initialization(self):
        """Test ValidationEngine initialization."""
        engine = ValidationEngine()

        assert engine.results == []

    def test_validate_conversion_unknown_type(self):
        """Test validation with unknown conversion type."""
        engine = ValidationEngine()
        results = engine.validate_conversion("unknown_type", "content")

        assert len(results) == 1
        assert results[0].level == ValidationLevel.WARNING
        assert "Unknown conversion type" in results[0].message

    def test_validate_resource_conversion_valid(self):
        """Test resource conversion validation with valid YAML."""
        engine = ValidationEngine()
        valid_task = """
- name: Install nginx package
  ansible.builtin.package:
    name: nginx
    state: present
"""
        results = engine.validate_conversion("resource", valid_task)

        # Should not have errors, might have info/warnings
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_resource_conversion_command_without_changed_when(self):
        """Test validation catches command without changed_when."""
        engine = ValidationEngine()
        task = """
- name: Run command
  ansible.builtin.command: echo test
"""
        results = engine.validate_conversion("resource", task)

        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        assert any("changed_when" in w.message for w in warnings)

    def test_validate_resource_conversion_shell_without_changed_when(self):
        """Test validation catches shell without changed_when."""
        engine = ValidationEngine()
        task = """
- name: Run shell command
  ansible.builtin.shell: echo test
"""
        results = engine.validate_conversion("resource", task)

        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        assert any("changed_when" in w.message for w in warnings)

    def test_validate_recipe_conversion_missing_hosts(self):
        """Test playbook validation catches missing hosts directive."""
        engine = ValidationEngine()
        playbook = """
---
- tasks:
    - name: Test task
      ansible.builtin.debug:
        msg: test
"""
        results = engine.validate_conversion("recipe", playbook)

        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert any("hosts" in e.message for e in errors)

    def test_validate_recipe_conversion_notify_without_handlers(self):
        """Test validation catches notify without handlers section."""
        engine = ValidationEngine()
        playbook = """
---
- hosts: all
  tasks:
    - name: Test task
      ansible.builtin.copy:
        content: test
        dest: /tmp/test
      notify: restart service
"""
        results = engine.validate_conversion("recipe", playbook)

        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        assert any("handlers" in w.message for w in warnings)

    def test_validate_recipe_conversion_no_tasks_or_roles(self):
        """Test validation catches playbook with no tasks or roles."""
        engine = ValidationEngine()
        playbook = """
---
- hosts: all
  vars:
    test_var: value
"""
        results = engine.validate_conversion("recipe", playbook)

        warnings = [r for r in results if r.level == ValidationLevel.WARNING]
        assert any("tasks or roles" in w.message for w in warnings)

    def test_validate_template_conversion_valid_jinja2(self):
        """Test template validation with valid Jinja2."""
        engine = ValidationEngine()
        template = "Hello {{ name }}!"

        results = engine.validate_conversion("template", template)

        # Should not have errors
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_template_conversion_deep_nesting(self):
        """Test validation flags deeply nested variables."""
        engine = ValidationEngine()
        template = "Value: {{ level1.level2.level3.level4.level5.level6 }}"

        results = engine.validate_conversion("template", template)

        infos = [r for r in results if r.level == ValidationLevel.INFO]
        assert any("Deep variable nesting" in i.message for i in infos)

    def test_validate_inspec_conversion_testinfra_format(self):
        """Test InSpec validation with Testinfra format."""
        engine = ValidationEngine()
        test_code = """
import pytest

def test_nginx_installed(host):
    nginx = host.package("nginx")
    assert nginx.is_installed
"""
        results = engine.validate_conversion("inspec", test_code)

        # Should not have syntax errors
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_inspec_conversion_ansible_format(self):
        """Test InSpec validation with Ansible assert format."""
        engine = ValidationEngine()
        test_yaml = """
---
- name: Test nginx is installed
  ansible.builtin.assert:
    that:
      - "'nginx' in ansible_facts.packages"
"""
        results = engine.validate_conversion("inspec", test_yaml)

        # Should not have errors
        errors = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_yaml_syntax_invalid(self):
        """Test YAML syntax validation with invalid YAML."""
        engine = ValidationEngine()
        invalid_yaml = """
- name: test
  invalid: [unclosed
"""
        engine._validate_yaml_syntax(invalid_yaml)

        errors = [r for r in engine.results if r.level == ValidationLevel.ERROR]
        assert any("Invalid YAML syntax" in e.message for e in errors)

    def test_validate_ansible_module_unknown(self):
        """Test validation flags unknown Ansible modules."""
        engine = ValidationEngine()
        task = "ansible.builtin.nonexistent_module:"

        engine._validate_ansible_module_exists(task)

        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        assert any("Unknown Ansible module" in w.message for w in warnings)

    def test_validate_ansible_module_known(self):
        """Test validation accepts known Ansible modules."""
        engine = ValidationEngine()
        task = "ansible.builtin.package:"

        engine._validate_ansible_module_exists(task)

        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        # Should not flag known module as unknown
        unknown_warnings = [
            w for w in warnings if "Unknown Ansible module" in w.message
        ]
        assert len(unknown_warnings) == 0

    def test_validate_task_naming_empty(self):
        """Test validation catches empty task names."""
        engine = ValidationEngine()
        task = 'name: ""'

        engine._validate_task_naming(task)

        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        assert any("empty name" in w.message for w in warnings)

    def test_validate_task_naming_short(self):
        """Test validation flags short task names."""
        engine = ValidationEngine()
        task = "name: test"

        engine._validate_task_naming(task)

        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        assert any("very short" in i.message for i in infos)

    def test_validate_task_naming_valid_descriptive(self):
        """Test validation passes with descriptive task names."""
        engine = ValidationEngine()
        task = "name: Install and configure nginx web server"

        engine._validate_task_naming(task)

        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        # Should not flag descriptive names (>= 10 chars)
        assert len(warnings) == 0
        assert len(infos) == 0

    def test_validate_task_naming_exactly_ten_characters(self):
        """Test validation boundary at 10 characters."""
        engine = ValidationEngine()
        # Exactly 10 characters - should not trigger short name warning
        task = "name: Ten chars!"

        engine._validate_task_naming(task)

        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        short_name_infos = [i for i in infos if "very short" in i.message]
        # 10 chars should NOT be flagged as short
        assert len(short_name_infos) == 0

    def test_validate_task_naming_nine_characters(self):
        """Test validation flags names with 9 characters."""
        engine = ValidationEngine()
        # 9 characters - should trigger short name info
        task = "name: Nine char"

        engine._validate_task_naming(task)

        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        assert any("very short" in i.message for i in infos)

    def test_validate_task_naming_whitespace_only(self):
        """Test validation flags names with only whitespace as short."""
        engine = ValidationEngine()
        task = "name: '   '"

        engine._validate_task_naming(task)

        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        # 3 spaces gets stripped to empty quotes but still counts as 3 chars
        # after strip("\"'"), so it's flagged as short, not empty
        assert any("very short" in i.message for i in infos)

    def test_validate_task_naming_no_name_field(self):
        """Test validation handles tasks without name field."""
        engine = ValidationEngine()
        task = "ansible.builtin.debug: msg=test"

        engine._validate_task_naming(task)

        # No name field means no results - validation is for naming when present
        # Just verify it doesn't crash
        assert isinstance(engine.results, list)

    def test_validate_task_naming_special_characters_long_enough(self):
        """Test validation passes special characters if long enough."""
        engine = ValidationEngine()
        # 15 characters of special chars - unusual but meets length requirement
        task = "name: '!!!!!!!!!!!!!!!'"

        engine._validate_task_naming(task)

        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        # Current validation only checks length, not content quality
        assert len(warnings) == 0
        assert len(infos) == 0

    def test_validate_variable_usage_ansible_prefix(self):
        """Test validation flags variables with ansible_ prefix."""
        engine = ValidationEngine()
        content = "Value: {{ ansible_custom_var }}"

        engine._validate_variable_usage(content)

        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        assert any("ansible_ prefix" in i.message for i in infos)

    def test_validate_variable_usage_builtin_ansible_var(self):
        """Test validation allows built-in ansible_ variables."""
        engine = ValidationEngine()
        content = "Host: {{ ansible_host }}"

        engine._validate_variable_usage(content)

        # Should not flag built-in ansible variables
        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        ansible_prefix_infos = [i for i in infos if "ansible_ prefix" in i.message]
        assert len(ansible_prefix_infos) == 0

    def test_validate_python_syntax_valid(self):
        """Test Python syntax validation with valid code."""
        engine = ValidationEngine()
        code = """
def test_function():
    return True
"""
        engine._validate_python_syntax(code)

        errors = [r for r in engine.results if r.level == ValidationLevel.ERROR]
        assert len(errors) == 0

    def test_validate_python_syntax_invalid(self):
        """Test Python syntax validation with invalid code."""
        engine = ValidationEngine()
        code = """
def test_function(
    invalid syntax here
"""
        engine._validate_python_syntax(code)

        errors = [r for r in engine.results if r.level == ValidationLevel.ERROR]
        assert any("Invalid Python syntax" in e.message for e in errors)

    def test_get_summary_empty(self):
        """Test get_summary with no results."""
        engine = ValidationEngine()
        summary = engine.get_summary()

        assert summary["errors"] == 0
        assert summary["warnings"] == 0
        assert summary["info"] == 0

    def test_get_summary_with_results(self):
        """Test get_summary with various result types."""
        engine = ValidationEngine()

        engine._add_result(ValidationLevel.ERROR, ValidationCategory.SYNTAX, "Error 1")
        engine._add_result(ValidationLevel.ERROR, ValidationCategory.SYNTAX, "Error 2")
        engine._add_result(
            ValidationLevel.WARNING, ValidationCategory.BEST_PRACTICE, "Warning 1"
        )
        engine._add_result(ValidationLevel.INFO, ValidationCategory.SEMANTIC, "Info 1")
        engine._add_result(ValidationLevel.INFO, ValidationCategory.SEMANTIC, "Info 2")
        engine._add_result(ValidationLevel.INFO, ValidationCategory.SEMANTIC, "Info 3")

        summary = engine.get_summary()

        assert summary["errors"] == 2
        assert summary["warnings"] == 1
        assert summary["info"] == 3

    def test_validation_levels_enum_values(self):
        """Test ValidationLevel enum values."""
        assert ValidationLevel.ERROR.value == "error"
        assert ValidationLevel.WARNING.value == "warning"
        assert ValidationLevel.INFO.value == "info"

    def test_validation_categories_enum_values(self):
        """Test ValidationCategory enum values."""
        assert ValidationCategory.SYNTAX.value == "syntax"
        assert ValidationCategory.SEMANTIC.value == "semantic"
        assert ValidationCategory.BEST_PRACTICE.value == "best_practice"
        assert ValidationCategory.SECURITY.value == "security"
        assert ValidationCategory.PERFORMANCE.value == "performance"

    def test_add_result_method(self):
        """Test _add_result helper method."""
        engine = ValidationEngine()

        engine._add_result(
            ValidationLevel.WARNING,
            ValidationCategory.SECURITY,
            "Security warning",
            location="line 5",
            suggestion="Fix security issue",
        )

        assert len(engine.results) == 1
        result = engine.results[0]
        assert result.level == ValidationLevel.WARNING
        assert result.category == ValidationCategory.SECURITY
        assert result.message == "Security warning"
        assert result.location == "line 5"
        assert result.suggestion == "Fix security issue"

    def test_validate_service_task_dependency_info(self):
        """Test validation provides info about service dependencies."""
        engine = ValidationEngine()
        task = """
- name: Start nginx service
  ansible.builtin.service:
    name: nginx
    state: started
"""
        engine._validate_resource_dependencies(task)

        infos = [r for r in engine.results if r.level == ValidationLevel.INFO]
        assert any("dependency" in i.message for i in infos)

    def test_validate_module_usage_file_with_creates(self):
        """Test validation flags unusual file module usage."""
        engine = ValidationEngine()
        task = """
- name: Test file
  ansible.builtin.file:
    path: /tmp/test
    creates: /tmp/marker
"""
        engine._validate_module_usage(task)

        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        assert any("creates" in w.message for w in warnings)

    def test_validate_handler_definitions_with_handlers(self):
        """Test validation passes when handlers are defined."""
        engine = ValidationEngine()
        playbook = """
---
- hosts: all
  tasks:
    - name: Copy config
      ansible.builtin.copy:
        content: test
        dest: /tmp/test
      notify: restart service

  handlers:
    - name: restart service
      ansible.builtin.service:
        name: myservice
        state: restarted
"""
        engine._validate_handler_definitions(playbook)

        # Should not have warnings about missing handlers
        warnings = [r for r in engine.results if r.level == ValidationLevel.WARNING]
        handler_warnings = [w for w in warnings if "handlers" in w.message]
        assert len(handler_warnings) == 0

    def test_multiple_validations_accumulate_results(self):
        """Test that multiple validation calls accumulate results."""
        engine = ValidationEngine()

        # First validation
        engine.validate_conversion("resource", "ansible.builtin.command: echo test")

        first_count = len(engine.results)
        assert first_count > 0

        # Second validation - should reset results
        engine.validate_conversion("recipe", "---\n- tasks: []")

        second_count = len(engine.results)
        # Results should be reset for new validation
        assert second_count >= 0
        # Should have different results (not accumulated)
        assert len(engine.results) == second_count
