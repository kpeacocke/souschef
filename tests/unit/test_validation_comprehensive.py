"""Comprehensive validation tests to cover mutation survivors."""

from unittest.mock import patch

from souschef.core.validation import (
    ValidationCategory,
    ValidationEngine,
    ValidationLevel,
    ValidationResult,
    _format_validation_results_summary,
)


class TestValidationSummaryFormatting:
    """Test exact output formatting for validation summaries."""

    def test_format_summary_no_issues(self):
        """Test exact formatting when no issues are present."""
        summary = _format_validation_results_summary(
            "resource", {"errors": 0, "warnings": 0, "info": 0}
        )

        expected = (
            "# Validation Summary for resource Conversion\n\n"
            "✅ **All validation checks passed!** No issues found.\n\n"
            "Errors: 0\n"
            "Warnings: 0\n"
            "Info: 0\n"
        )

        assert summary == expected

    def test_format_summary_with_errors(self):
        """Test exact formatting when errors are present."""
        summary = _format_validation_results_summary(
            "recipe", {"errors": 1, "warnings": 2, "info": 3}
        )

        expected = (
            "# Validation Summary for recipe Conversion\n\n"
            "❌ **Validation Results:**\n"
            "• Errors: 1\n"
            "• Warnings: 2\n"
            "• Info: 3\n\n"
            "**Status:** Failed\n"
        )

        assert summary == expected

    def test_format_summary_with_warnings(self):
        """Test exact formatting when warnings are present."""
        summary = _format_validation_results_summary(
            "recipe", {"errors": 0, "warnings": 1, "info": 0}
        )

        expected = (
            "# Validation Summary for recipe Conversion\n\n"
            "⚠️ **Validation Results:**\n"
            "• Errors: 0\n"
            "• Warnings: 1\n"
            "• Info: 0\n\n"
            "**Status:** Warning\n"
        )

        assert summary == expected

    def test_format_summary_with_info(self):
        """Test exact formatting when only info is present."""
        summary = _format_validation_results_summary(
            "template", {"errors": 0, "warnings": 0, "info": 2}
        )

        expected = (
            "# Validation Summary for template Conversion\n\n"
            "ℹ️ **Validation Results:**\n"
            "• Errors: 0\n"
            "• Warnings: 0\n"
            "• Info: 2\n\n"
            "**Status:** Passed with info\n"
        )

        assert summary == expected


class TestValidationResultFormatting:
    """Test validation result string formatting."""

    def test_validation_result_repr_with_all_fields(self):
        """Test representation formatting includes all fields."""
        result = ValidationResult(
            level=ValidationLevel.ERROR,
            category=ValidationCategory.SECURITY,
            message="Risk found",
            location="task 1",
            suggestion="Review and fix",
        )

        expected = (
            "[ERROR] [security] Risk found\n"
            "  Location: task 1\n"
            "  Suggestion: Review and fix"
        )

        assert repr(result) == expected

    def test_validation_result_repr_message_only(self):
        """Test representation with message only."""
        result = ValidationResult(
            level=ValidationLevel.INFO,
            category=ValidationCategory.PERFORMANCE,
            message="Tip",
        )

        expected = "[INFO] [performance] Tip"

        assert repr(result) == expected


class TestValidationEngineSubvalidators:
    """Test validation engine sub-validator routing and invocations."""

    def test_recipe_conversion_invokes_subvalidators(self):
        """Test recipe validation invokes all subvalidators."""
        engine = ValidationEngine()

        with (
            patch.object(engine, "_validate_yaml_syntax") as yaml_val,
            patch.object(engine, "_validate_variable_usage") as var_val,
            patch.object(engine, "_validate_handler_definitions") as hand_val,
            patch.object(engine, "_validate_playbook_structure") as play_val,
        ):
            engine._validate_recipe_conversion("content")
            yaml_val.assert_called_once_with("content")
            var_val.assert_called_once_with("content")
            hand_val.assert_called_once_with("content")
            play_val.assert_called_once_with("content")

    def test_resource_conversion_invokes_subvalidators(self):
        """Test resource validation invokes all subvalidators."""
        engine = ValidationEngine()

        with (
            patch.object(engine, "_validate_yaml_syntax") as yaml_val,
            patch.object(engine, "_validate_ansible_module_exists") as mod_val,
            patch.object(engine, "_validate_idempotency") as idemp_val,
            patch.object(engine, "_validate_resource_dependencies") as dep_val,
            patch.object(engine, "_validate_task_naming") as name_val,
            patch.object(engine, "_validate_module_usage") as usage_val,
        ):
            engine._validate_resource_conversion("content")
            yaml_val.assert_called_once_with("content")
            mod_val.assert_called_once_with("content")
            idemp_val.assert_called_once_with("content")
            dep_val.assert_called_once_with("content")
            name_val.assert_called_once_with("content")
            usage_val.assert_called_once_with("content")

    def test_template_conversion_invokes_subvalidators(self):
        """Test template validation invokes all subvalidators."""
        engine = ValidationEngine()

        with (
            patch.object(engine, "_validate_jinja2_syntax") as jinja_val,
            patch.object(engine, "_validate_variable_references") as var_val,
        ):
            engine._validate_template_conversion("content")
            jinja_val.assert_called_once_with("content")
            var_val.assert_called_once_with("content")

    def test_inspec_conversion_python_path(self):
        """Test InSpec with Python markers uses Python validator."""
        engine = ValidationEngine()

        with patch.object(engine, "_validate_python_syntax") as python_val:
            engine._validate_inspec_conversion("import pytest\n")
            python_val.assert_called_once_with("import pytest\n")

    def test_inspec_conversion_ruby_path(self):
        """Test InSpec with Ruby markers uses Ruby validator."""
        engine = ValidationEngine()

        with patch.object(engine, "_validate_ruby_syntax") as ruby_val:
            engine._validate_inspec_conversion("require 'serverspec'\n")
            ruby_val.assert_called_once()

    def test_inspec_conversion_yaml_path(self):
        """Test InSpec with YAML markers uses YAML validator."""
        engine = ValidationEngine()

        with patch.object(engine, "_validate_yaml_syntax") as yaml_val:
            engine._validate_inspec_conversion("---\npackage:\n  nginx")
            yaml_val.assert_called_once()


class TestValidationDetailsPreservation:
    """Test that validation details are correctly preserved and used."""

    def test_module_usage_result_contains_category(self):
        """Test module usage warning sets correct category."""
        engine = ValidationEngine()
        engine._validate_module_usage(
            "- name: File\n  ansible.builtin.file:\n    creates: /tmp/a"
        )

        result = engine.results[0]
        assert result.category == ValidationCategory.BEST_PRACTICE

    def test_handler_missing_result_contains_category(self):
        """Test missing handler warning sets correct category."""
        engine = ValidationEngine()
        engine._validate_handler_definitions("notify: restart")

        result = engine.results[0]
        assert result.category == ValidationCategory.SEMANTIC

    def test_idempotency_result_includes_suggestion(self):
        """Test idempotency warning includes actionable suggestion."""
        engine = ValidationEngine()
        engine._validate_idempotency(
            "- name: Run\n  ansible.builtin.command: /bin/test"
        )

        result = engine.results[0]
        assert "changed_when" in result.suggestion

    def test_dependency_result_includes_handler_suggestion(self):
        """Test service dependency info mentions handlers."""
        engine = ValidationEngine()
        engine._validate_resource_dependencies(
            "- name: Start\n  ansible.builtin.service:\n    state: started"
        )

        result = engine.results[0]
        assert "handler" in result.suggestion

    def test_jinja2_syntax_error_includes_details(self):
        """Test Jinja2 syntax error includes exception details."""
        import sys
        import types

        class DummyEnvironment:
            def __init__(self, autoescape=True):
                self.autoescape = autoescape

            def parse(self, _template):
                raise ValueError("unmatched brace")

        dummy_module = types.ModuleType("jinja2")
        dummy_module.Environment = DummyEnvironment
        sys.modules["jinja2"] = dummy_module

        try:
            engine = ValidationEngine()
            engine._validate_jinja2_syntax("{{")

            result = engine.results[0]
            assert "unmatched brace" in result.message
        finally:
            del sys.modules["jinja2"]

    def test_nesting_warning_includes_variable_name(self):
        """Test nesting warning includes the specific variable."""
        engine = ValidationEngine()
        engine._validate_variable_references("{{ app.config.db.host.name.value }}")

        result = engine.results[0]
        assert "app.config.db.host.name.value" in result.message

    def test_yaml_error_includes_suggestion(self):
        """Test YAML syntax error includes fix suggestion."""
        engine = ValidationEngine()
        engine._validate_yaml_syntax("- name: bad\n  - indent")

        result = engine.results[0]
        assert "indentation" in result.suggestion


class TestMutantSurvivorTargets:
    """Targeted tests to kill specific surviving mutants."""

    def test_task_naming_exact_boundary_9_chars(self):
        """Test task name exactly 9 characters (just below 10)."""
        engine = ValidationEngine()
        engine._validate_task_naming("- name: 123456789\n  ansible.builtin.debug: {}")

        assert len(engine.results) > 0
        assert any("very short" in r.message for r in engine.results)

    def test_task_naming_exactly_10_chars(self):
        """Test task name exactly 10 characters (at boundary)."""
        engine = ValidationEngine()
        engine._validate_task_naming("- name: 1234567890\n  ansible.builtin.debug: {}")

        # Should NOT generate warning for exactly 10 chars
        assert not any("very short" in r.message for r in engine.results)

    def test_task_naming_name_with_quotes(self):
        """Test task name with double quotes is properly stripped."""
        engine = ValidationEngine()
        engine._validate_task_naming('- name: "test"\n  ansible.builtin.debug: {}')

        # Should trigger short name warning
        assert len(engine.results) > 0
        assert any("very short" in r.message for r in engine.results)

    def test_task_naming_name_with_single_quotes(self):
        """Test task name with single quotes is properly stripped."""
        engine = ValidationEngine()
        engine._validate_task_naming("- name: 'test'\n  ansible.builtin.debug: {}")

        # Should trigger short name warning
        assert len(engine.results) > 0
        assert any("very short" in r.message for r in engine.results)

    def test_task_naming_mixed_whitespace(self):
        """Test task name with leading/trailing whitespace."""
        engine = ValidationEngine()
        engine._validate_task_naming(
            "- name:   long_task_name   \n  ansible.builtin.debug: {}"
        )

        # Whitespace should be stripped, name should be valid
        assert not any("very short" in r.message for r in engine.results)

    def test_module_usage_creates_with_file_exact(self):
        """Test module usage detects 'creates:' with file module."""
        engine = ValidationEngine()
        engine._validate_module_usage("ansible.builtin.file: creates: /tmp/test")

        assert len(engine.results) > 0
        assert "creates" in engine.results[0].message

    def test_module_usage_non_file_module(self):
        """Test that non-file modules don't trigger creates: warning."""
        engine = ValidationEngine()
        engine._validate_module_usage(
            "ansible.builtin.copy: src=test creates=/tmp/test"
        )

        # Should NOT trigger file+creates warning
        assert not any("creates" in r.message for r in engine.results)

    def test_ansible_module_exact_match_builtin(self):
        """Test exact module name matching for ansible.builtin modules."""
        engine = ValidationEngine()
        engine._validate_ansible_module_exists("ansible.builtin.debug")

        # Should NOT generate error for known builtin module
        assert len(engine.results) == 0

    def test_ansible_module_unknown_module_exact(self):
        """Test unknown module is caught."""
        engine = ValidationEngine()
        engine._validate_ansible_module_exists("ansible.builtin.unknown_fake:")

        assert len(engine.results) > 0
        assert "Unknown" in engine.results[0].message

    def test_idempotency_command_changed_when_present(self):
        """Test shell/command task with changed_when passes."""
        engine = ValidationEngine()
        engine._validate_idempotency(
            "- name: Test\n  ansible.builtin.command: test\n  changed_when: true"
        )

        # Should NOT generate warning with changed_when
        assert not any("idempotent" in r.message.lower() for r in engine.results)

    def test_idempotency_shell_changed_when_present(self):
        """Test shell task with changed_when passes."""
        engine = ValidationEngine()
        engine._validate_idempotency(
            "- name: Test\n  ansible.builtin.shell: test\n  changed_when: result.rc == 0"
        )

        assert not any("idempotent" in r.message.lower() for r in engine.results)

    def test_resource_dependencies_service_state_started(self):
        """Test service with state: started is detected."""
        engine = ValidationEngine()
        engine._validate_resource_dependencies(
            "- name: Start service\n  ansible.builtin.service:\n    name: apache2\n    state: started"
        )

        assert len(engine.results) > 0
        assert "service" in engine.results[0].message.lower()

    def test_resource_dependencies_non_service_no_warning(self):
        """Test non-service modules don't trigger dependency warning."""
        engine = ValidationEngine()
        engine._validate_resource_dependencies(
            "- name: Install package\n  ansible.builtin.apt:\n    name: vim"
        )

        # Should NOT generate service dependency warning
        assert not any("service" in r.message.lower() for r in engine.results)

    def test_handler_definitions_notify_present(self):
        """Test handler notify with handlers section defined."""
        engine = ValidationEngine()
        engine._validate_handler_definitions(
            "notify: restart apache\nhandlers:\n- name: restart apache"
        )

        # Should NOT warn when handlers section exists
        assert len(engine.results) == 0

    def test_handler_definitions_notify_missing(self):
        """Test notify without handlers section is caught."""
        engine = ValidationEngine()
        engine._validate_handler_definitions(
            "notify: restart apache\ntasks:\n- name: other"
        )

        assert len(engine.results) > 0
        assert "handlers" in engine.results[0].message.lower()

    def test_playbook_structure_has_hosts(self):
        """Test playbook with hosts field is valid."""
        engine = ValidationEngine()
        engine._validate_playbook_structure(
            "---\n- hosts: all\n  tasks:\n    - name: test"
        )

        # Should NOT generate error for valid playbook
        assert not any("hosts" in r.message.lower() for r in engine.results)

    def test_playbook_structure_missing_hosts(self):
        """Test playbook without hosts field is invalid."""
        engine = ValidationEngine()
        engine._validate_playbook_structure(
            "---\n- name: test\n  tasks:\n    - name: run"
        )

        assert len(engine.results) > 0
        assert "hosts" in engine.results[0].message.lower()

    def test_jinja2_syntax_valid_template(self):
        """Test valid Jinja2 template passes."""
        engine = ValidationEngine()
        engine._validate_jinja2_syntax("{{ variable }}")

        # Should NOT generate error for valid Jinja2
        assert len(engine.results) == 0

    def test_jinja2_syntax_invalid_template(self):
        """Test invalid Jinja2 template is detected."""
        engine = ValidationEngine()
        engine._validate_jinja2_syntax("{{ unclosed")

        assert len(engine.results) > 0
        assert "syntax" in engine.results[0].message.lower()

    def test_variable_usage_ansible_prefix(self):
        """Test ansible variables don't trigger undefined warning."""
        engine = ValidationEngine()
        engine._validate_variable_usage("{{ ansible_distribution }}")

        # Should NOT warn about ansible-specific variables
        assert not any("undefined" in r.message.lower() for r in engine.results)

    def test_variable_usage_builtin_only(self):
        """Test builtin variable is not flagged as undefined."""
        engine = ValidationEngine()
        engine._validate_variable_usage("{{ hostvars }}")

        assert not any("undefined" in r.message.lower() for r in engine.results)

    def test_variable_usage_custom_undefined(self):
        """Test custom ansible_ variable that's not in builtins."""
        engine = ValidationEngine()
        engine._validate_variable_usage("{{ ansible_custom_var }}")

        # Should generate info for non-standard ansible_ variables
        assert len(engine.results) > 0
        assert "ansible_custom_var" in engine.results[0].message

    def test_variable_references_shallow_nesting(self):
        """Test shallow variable nesting (< 4 levels)."""
        engine = ValidationEngine()
        engine._validate_variable_references("{{ app.config.db }}")

        # Should NOT warn about shallow nesting
        assert not any("nesting" in r.message.lower() for r in engine.results)

    def test_variable_references_deep_nesting_exactly_4(self):
        """Test exactly 4 levels of nesting (at boundary)."""
        engine = ValidationEngine()
        engine._validate_variable_references("{{ app.config.db.host }}")

        # 4 levels = 4 dots, should not trigger warning for exactly 4
        assert not any("nesting" in r.message.lower() for r in engine.results)

    def test_variable_references_deep_nesting_5plus(self):
        """Test 6+ levels of nesting (more than 5 parts) triggers warning."""
        engine = ValidationEngine()
        engine._validate_variable_references("{{ app.config.db.host.name.value }}")

        # 6 parts (5+ dots) should trigger nesting warning
        assert len(engine.results) > 0
        assert "nesting" in engine.results[0].message.lower()

    def test_python_syntax_valid_code(self):
        """Test valid Python code passes."""
        engine = ValidationEngine()
        engine._validate_python_syntax("x = 5\nprint(x)")

        # Should NOT generate error for valid Python
        assert len(engine.results) == 0

    def test_python_syntax_invalid_code(self):
        """Test invalid Python code is detected."""
        engine = ValidationEngine()
        engine._validate_python_syntax("if x >\n  print(x)")

        assert len(engine.results) > 0
        assert "syntax" in engine.results[0].message.lower()

    def test_yaml_syntax_valid_content(self):
        """Test valid YAML passes."""
        engine = ValidationEngine()
        engine._validate_yaml_syntax("- name: test\n  key: value")

        # Should NOT generate error for valid YAML
        assert len(engine.results) == 0

    def test_yaml_syntax_invalid_indentation(self):
        """Test invalid YAML indentation is detected."""
        engine = ValidationEngine()
        engine._validate_yaml_syntax("- name: test\n key: value")

        assert len(engine.results) > 0
        assert "YAML" in engine.results[0].message

    def test_inspec_conversion_python_path(self):
        """Test inspec conversion correctly routes to Python validator."""
        engine = ValidationEngine()
        engine._validate_inspec_conversion("describe command('test') do")

        # Should validate as Ruby, not Python
        assert not any(
            "syntax" in r.message.lower()
            for r in engine.results
            if "python" in r.message.lower()
        )

    def test_get_summary_with_errors(self):
        """Test summary correctly counts errors."""
        engine = ValidationEngine()
        engine._add_result(ValidationLevel.ERROR, ValidationCategory.SYNTAX, "Error 1")
        engine._add_result(ValidationLevel.ERROR, ValidationCategory.SYNTAX, "Error 2")
        engine._add_result(
            ValidationLevel.WARNING, ValidationCategory.BEST_PRACTICE, "Warning 1"
        )

        summary = engine.get_summary()
        assert summary["errors"] == 2
        assert summary["warnings"] == 1

    def test_get_summary_empty_results(self):
        """Test summary with no results."""
        engine = ValidationEngine()
        summary = engine.get_summary()

        assert summary["errors"] == 0
        assert summary["warnings"] == 0
        assert summary["info"] == 0

    def test_format_summary_conversion_type_in_title(self):
        """Test conversion type appears in summary title."""
        summary = _format_validation_results_summary(
            "habitat", {"errors": 0, "warnings": 0, "info": 0}
        )

        assert "habitat" in summary
        assert "Conversion" in summary

    def test_validation_result_dict_with_all_fields(self):
        """Test ValidationResult.to_dict includes all fields."""
        result = ValidationResult(
            ValidationLevel.ERROR,
            ValidationCategory.SYNTAX,
            "Test message",
            location="line 5",
            suggestion="Fix this",
        )

        result_dict = result.to_dict()
        assert result_dict["level"] == "error"
        assert result_dict["category"] == "syntax"
        assert result_dict["message"] == "Test message"
        assert result_dict["location"] == "line 5"
        assert result_dict["suggestion"] == "Fix this"

    def test_validation_result_dict_without_optional_fields(self):
        """Test ValidationResult.to_dict omits optional fields when absent."""
        result = ValidationResult(
            ValidationLevel.WARNING, ValidationCategory.PERFORMANCE, "Test warning"
        )

        result_dict = result.to_dict()
        assert "location" not in result_dict
        assert "suggestion" not in result_dict
        assert "level" in result_dict

    def test_validation_result_repr_with_all_fields(self):
        """Test __repr__ includes all fields."""
        result = ValidationResult(
            ValidationLevel.ERROR,
            ValidationCategory.SECURITY,
            "Security issue",
            location="line 10",
            suggestion="Add validation",
        )

        repr_str = repr(result)
        assert "ERROR" in repr_str
        assert "security" in repr_str
        assert "Security issue" in repr_str
        assert "line 10" in repr_str
        assert "Add validation" in repr_str

    def test_validation_result_repr_without_location(self):
        """Test __repr__ handles missing location."""
        result = ValidationResult(
            ValidationLevel.INFO,
            ValidationCategory.BEST_PRACTICE,
            "Info message",
            suggestion="Consider",
        )

        repr_str = repr(result)
        assert "INFO" in repr_str
        assert "Location" not in repr_str
        assert "Consider" in repr_str
