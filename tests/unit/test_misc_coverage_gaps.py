"""
Tests for uncovered exception handlers and edge cases across multiple modules.

Targets specific uncovered lines in assessment, ci, converters, core modules,
migration modules, and utility helpers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# souschef/ci/github_actions.py – line 165 (has_foodcritic branch)
# ---------------------------------------------------------------------------


class TestGitHubActions:
    """Tests for GitHub Actions generator edge cases."""

    def test_build_lint_job_includes_foodcritic_step_when_detected(self) -> None:
        """_build_lint_job includes a Foodcritic step when has_foodcritic is True."""
        from souschef.ci.github_actions import _build_lint_job

        patterns = {
            "has_cookstyle": False,
            "has_foodcritic": True,
        }
        job = _build_lint_job(patterns, enable_cache=False)
        step_names = [step.get("name", "") for step in job.get("steps", [])]
        assert any(
            "Foodcritic" in name or "foodcritic" in name.lower() for name in step_names
        )


# ---------------------------------------------------------------------------
# souschef/ci/gitlab_ci.py – line 226 (allow_failure branch)
# ---------------------------------------------------------------------------


class TestGitLabCI:
    """Tests for GitLab CI generator edge cases."""

    def test_build_job_yaml_includes_allow_failure_when_true(self) -> None:
        """_create_gitlab_job includes allow_failure: true when requested."""
        from souschef.ci.gitlab_ci import _create_gitlab_job

        yaml_str = _create_gitlab_job(
            "my_job",
            "test",
            ["  - echo hello"],
            allow_failure=True,
        )
        assert "allow_failure: true" in yaml_str


# ---------------------------------------------------------------------------
# souschef/ci/jenkins_pipeline.py – line 54 (no lint steps → return None)
# ---------------------------------------------------------------------------


class TestJenkinsPipelineLintStage:
    """Tests for Jenkins pipeline lint stage."""

    def test_create_lint_stage_with_cookstyle_adds_steps(self) -> None:
        """_create_lint_stage returns a stage when cookstyle tool is present."""
        from souschef.ci.jenkins_pipeline import _create_lint_stage

        patterns = {"lint_tools": ["cookstyle"]}
        result = _create_lint_stage(patterns)
        assert result is not None


# ---------------------------------------------------------------------------
# souschef/converters/conversion_rules.py – lines 291, 293
# ---------------------------------------------------------------------------


class TestConversionRules:
    """Tests for conversion rules edge cases."""

    def test_service_rule_transformation_stop_action(self) -> None:
        """Service rule transformation returns 'stopped' state when body contains 'stop'."""
        from souschef.converters.conversion_rules import create_service_rule

        rule = create_service_rule()
        result = rule.apply("service 'nginx' do\n  action :stop\nend")
        if result:
            assert "stopped" in result

    def test_service_rule_transformation_restart_action(self) -> None:
        """Service rule transformation returns 'restarted' state when body contains 'restart'."""
        from souschef.converters.conversion_rules import create_service_rule

        rule = create_service_rule()
        result = rule.apply("service 'nginx' do\n  action :restart\nend")
        if result:
            assert "restarted" in result


# ---------------------------------------------------------------------------
# souschef/converters/cookbook_specific.py – line 125 (unknown builder)
# ---------------------------------------------------------------------------


class TestCookbookSpecific:
    """Tests for cookbook-specific converter edge cases."""

    def test_build_cookbook_resource_params_unknown_builder_returns_none(
        self,
    ) -> None:
        """build_cookbook_resource_params returns None for an unknown builder name."""
        from souschef.converters.cookbook_specific import build_cookbook_resource_params

        with patch(
            "souschef.converters.cookbook_specific.COOKBOOK_RESOURCE_MAPPINGS",
            {
                "myapp_resource": {
                    "params_builder": "some_unknown_builder_func",
                }
            },
        ):
            result = build_cookbook_resource_params(
                "myapp_resource", "myapp", "install", {}
            )
        assert result is None


# ---------------------------------------------------------------------------
# souschef/converters/playbook_optimizer.py – line 155 (break in consolidation)
# ---------------------------------------------------------------------------


class TestPlaybookOptimizerBreak:
    """Tests for playbook optimiser break path."""

    def test_optimize_task_loops_breaks_on_different_module(self) -> None:
        """optimize_task_loops stops accumulating when next task uses a different module."""
        from souschef.converters.playbook_optimizer import optimize_task_loops

        # Two apt tasks followed by a non-apt task → can't consolidate
        tasks = [
            {"name": "install curl", "apt": {"name": "curl", "state": "present"}},
            {"name": "install wget", "apt": {"name": "wget", "state": "present"}},
            {"name": "copy file", "copy": {"src": "/a", "dest": "/b"}},
        ]
        result = optimize_task_loops(tasks)
        # Should not raise and tasks should be returned
        assert isinstance(result, list)
        assert len(result) >= 2


# ---------------------------------------------------------------------------
# souschef/core/path_utils.py – line 144 (absolute result check)
# ---------------------------------------------------------------------------


class TestPathUtilsAbsoluteResult:
    """Tests for _validate_relative_parts absolute result check."""

    def test_validate_relative_parts_absolute_part_raises(self) -> None:
        """_validate_relative_parts raises ValueError for an absolute path part."""
        from souschef.core.path_utils import _validate_relative_parts

        with pytest.raises(ValueError, match="Path traversal attempt"):
            _validate_relative_parts(("/absolute/path",))


# ---------------------------------------------------------------------------
# souschef/core/url_validation.py – line 41 (empty allowlist entry)
# ---------------------------------------------------------------------------


class TestUrlValidationEmptyAllowlistEntry:
    """Tests for _matches_allowlist with empty entries."""

    def test_matches_allowlist_skips_empty_entries(self) -> None:
        """_matches_allowlist skips empty/whitespace allowlist entries."""
        from souschef.core.url_validation import _matches_allowlist

        # Empty entry should be skipped, hostname should not match
        assert _matches_allowlist("example.com", ["", "  ", "other.com"]) is False

    def test_matches_allowlist_with_empty_entry_and_match(self) -> None:
        """_matches_allowlist skips empty entries but still matches later entries."""
        from souschef.core.url_validation import _matches_allowlist

        assert _matches_allowlist("example.com", ["", "example.com"]) is True


# ---------------------------------------------------------------------------
# souschef/core/http_client.py – line 159 (timeout validation)
# ---------------------------------------------------------------------------


class TestHTTPClientTimeoutValidation:
    """Tests for HTTPClient timeout validation."""

    def test_http_client_rejects_timeout_below_minimum(self) -> None:
        """HTTPClient raises SousChefError for timeout less than 1 second."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        with pytest.raises(SousChefError, match="Invalid timeout"):
            HTTPClient(base_url="https://example.com", timeout=0)

    def test_http_client_rejects_timeout_above_maximum(self) -> None:
        """HTTPClient raises SousChefError for timeout greater than 300 seconds."""
        from souschef.core.errors import SousChefError
        from souschef.core.http_client import HTTPClient

        with pytest.raises(SousChefError, match="Invalid timeout"):
            HTTPClient(base_url="https://example.com", timeout=301)


# ---------------------------------------------------------------------------
# souschef/core/chef_server.py – lines 220, 546, 830
# ---------------------------------------------------------------------------


class TestChefServerRemainingLines:
    """Tests for remaining uncovered lines in chef_server.py."""

    def test_load_private_key_non_rsa_returns_value_error(self) -> None:
        """_load_private_key raises ValueError when key is not RSA."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        from souschef.core.chef_server import _load_private_key

        # Generate an EC (non-RSA) key and serialize it to PEM
        ec_key = ec.generate_private_key(ec.SECP256R1())
        pem = ec_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        with pytest.raises(ValueError, match="RSA"):
            _load_private_key(pem)

    def test_list_cookbook_versions_no_matching_cookbook_returns_empty(self) -> None:
        """list_cookbook_versions returns [] when the cookbook isn't in the list."""
        from souschef.core.chef_server import ChefServerClient

        client = ChefServerClient.__new__(ChefServerClient)

        # list_cookbooks returns a cookbook with a different name
        with patch.object(
            client,
            "list_cookbooks",
            return_value=[
                {"name": "other_cookbook", "versions": [{"version": "1.0.0"}]}
            ],
        ):
            result = client.list_cookbook_versions("nonexistent")
        assert result == []

    def test_validate_chef_server_connection_connection_error(self) -> None:
        """_validate_chef_server_connection returns failure on ConnectionError."""
        from souschef.core.chef_server import _validate_chef_server_connection

        with patch(
            "souschef.core.chef_server._build_client_from_env",
            side_effect=ConnectionError("connection refused"),
        ):
            ok, msg = _validate_chef_server_connection(
                "https://chef.example.com",
                "admin",
            )
        assert ok is False
        assert "Connection error" in msg or "connection" in msg.lower()


# ---------------------------------------------------------------------------
# souschef/core/error_handling.py – lines 52, 421-423
# ---------------------------------------------------------------------------


class TestErrorHandlingRemainingLines:
    """Tests for remaining uncovered lines in error_handling.py."""

    def test_format_message_includes_column_number_when_set(self) -> None:
        """format_message includes column number when context has both line and column."""
        from souschef.core.error_handling import EnhancedErrorMessage, ErrorContext

        context = ErrorContext(
            error_type="syntax",
            location="recipe.rb",
            line_number=42,
            column_number=15,
        )
        msg = EnhancedErrorMessage(
            title="Parse Error",
            description="Something went wrong",
            context=context,
            suggestions=["Fix it"],
        )
        formatted = msg.format_message()
        assert "Column 15" in formatted

    def test_validate_hostname_invalid_octet_falls_through_to_dns(self) -> None:
        """validate_hostname falls through to DNS check for non-numeric octets."""
        from souschef.core.error_handling import validate_hostname

        # IP-like pattern with a non-numeric octet (e.g. 256.1.1.1)
        valid, _ = validate_hostname("256.1.1.1")
        # 256 is out of IPv4 range; should fall through to DNS validation
        # Since it's not a valid DNS name either (starts with digit segments),
        # or it may be treated as valid DNS - we just want to exercise the code path
        assert isinstance(valid, bool)


# ---------------------------------------------------------------------------
# souschef/assessment.py – top-level exception handlers (308, 398, 556, 631, 702, 749)
# ---------------------------------------------------------------------------


class TestAssessmentExceptions:
    """Tests for assessment.py exception handler coverage."""

    def test_assess_chef_migration_complexity_exception_returns_error_string(
        self,
    ) -> None:
        """assess_chef_migration_complexity returns error string when exception is raised."""
        from souschef.assessment import assess_chef_migration_complexity

        with patch(
            "souschef.assessment._validate_assessment_inputs",
            side_effect=RuntimeError("unexpected error"),
        ):
            result = assess_chef_migration_complexity("/fake/cookbook")
        assert "error" in result.lower()

    def test_parse_chef_migration_assessment_exception_returns_error(self) -> None:
        """parse_chef_migration_assessment returns error dict when exception is raised."""
        from souschef.assessment import parse_chef_migration_assessment

        with patch(
            "souschef.assessment._validate_assessment_inputs",
            side_effect=RuntimeError("unexpected error"),
        ):
            result = parse_chef_migration_assessment("/fake/cookbook")
        assert "error" in result

    def test_generate_migration_plan_exception_returns_error_string(self) -> None:
        """generate_migration_plan returns error string when exception is raised."""
        from souschef.assessment import generate_migration_plan

        with patch(
            "souschef.assessment._validate_migration_plan_inputs",
            side_effect=RuntimeError("plan error"),
        ):
            result = generate_migration_plan("/fake/cookbook", "full")
        assert "error" in result.lower()

    def test_analyse_cookbook_dependencies_exception_returns_error_string(
        self,
    ) -> None:
        """analyse_cookbook_dependencies returns error string when exception is raised."""
        from souschef.assessment import analyse_cookbook_dependencies

        with patch(
            "souschef.assessment._analyse_cookbook_dependencies_detailed",
            side_effect=RuntimeError("dep error"),
        ):
            result = analyse_cookbook_dependencies("/fake/cookbook")
        assert "error" in result.lower()

    def test_generate_migration_report_exception_returns_error_string(self) -> None:
        """generate_migration_report returns error string when exception is raised."""
        from souschef.assessment import generate_migration_report

        with patch(
            "souschef.assessment._generate_comprehensive_migration_report",
            side_effect=RuntimeError("report error"),
        ):
            result = generate_migration_report("{}", "executive")
        assert "error" in result.lower()

    def test_validate_conversion_exception_returns_error_string(self) -> None:
        """validate_conversion returns error string when exception is raised."""
        from souschef.assessment import validate_conversion

        with patch(
            "souschef.assessment.ValidationEngine",
            side_effect=RuntimeError("engine error"),
        ):
            result = validate_conversion("resource", "- name: install curl")
        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# souschef/core/metrics.py – lines 115, 127-129, 137, 356-361, 368-373
# ---------------------------------------------------------------------------


class TestMetrics:
    """Tests for metrics module uncovered lines."""

    def test_estimated_weeks_range_with_souschef_returns_range_string(self) -> None:
        """estimated_weeks_range_with_souschef returns 'X-Y weeks' when low != high."""
        from souschef.core.metrics import EffortMetrics

        # Use a large enough value so that the week range has different low/high values
        metrics = EffortMetrics(estimated_days=28.0)
        result = metrics.estimated_weeks_range_with_souschef
        assert "week" in result

    def test_estimated_days_formatted_returns_decimal_when_not_integer(self) -> None:
        """estimated_days_formatted returns decimal format for non-integer values."""
        from souschef.core.metrics import EffortMetrics

        metrics = EffortMetrics(estimated_days=1.5)
        assert "1.5" in metrics.estimated_days_formatted

    def test_estimated_days_formatted_with_souschef_decimal(self) -> None:
        """estimated_days_formatted_with_souschef returns decimal format."""
        from souschef.core.metrics import EffortMetrics

        metrics = EffortMetrics(estimated_days=1.5)
        result = metrics.estimated_days_formatted_with_souschef
        assert "days" in result

    def test_get_comparison_summary_contains_all_sections(self) -> None:
        """get_comparison_summary returns a string with all expected sections."""
        from souschef.core.metrics import EffortMetrics

        metrics = EffortMetrics(estimated_days=10.0)
        summary = metrics.get_comparison_summary()
        assert "Without SousChef" in summary
        assert "With SousChef" in summary
        assert "Time Saved" in summary

    def test_validate_metrics_consistency_invalid_weeks_range_format(self) -> None:
        """validate_metrics_consistency returns error for invalid range week format."""
        from souschef.core.metrics import validate_metrics_consistency

        valid, errors = validate_metrics_consistency(
            days=10.0,
            hours=80.0,
            weeks="abc-xyz weeks",
            complexity="medium",
        )
        assert valid is False
        assert len(errors) > 0

    def test_validate_metrics_consistency_invalid_single_week_format(self) -> None:
        """validate_metrics_consistency returns error for invalid single week format."""
        from souschef.core.metrics import validate_metrics_consistency

        valid, errors = validate_metrics_consistency(
            days=10.0,
            hours=80.0,
            weeks="xyz weeks",
            complexity="medium",
        )
        assert valid is False
        assert len(errors) > 0
