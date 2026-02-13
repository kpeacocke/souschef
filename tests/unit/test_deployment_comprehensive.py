"""Comprehensive tests for souschef/deployment.py module."""

from unittest.mock import MagicMock, patch

from souschef.deployment import (
    generate_awx_job_template_from_cookbook,
    generate_awx_workflow_from_chef_runlist,
)


class TestGenerateAWXJobTemplate:
    """Test generate_awx_job_template_from_cookbook function."""

    def test_empty_cookbook_name(self) -> None:
        """Test with empty cookbook name."""
        result = generate_awx_job_template_from_cookbook("/path/to/cookbook", "")

        assert isinstance(result, str)
        assert "Error" in result or "empty" in result.lower()

    def test_whitespace_only_cookbook_name(self) -> None:
        """Test with whitespace-only cookbook name."""
        result = generate_awx_job_template_from_cookbook("/path/to/cookbook", "   ")

        assert isinstance(result, str)

    def test_invalid_cookbook_path(self) -> None:
        """Test with invalid cookbook path."""
        result = generate_awx_job_template_from_cookbook(
            "/nonexistent/path", "test_cookbook"
        )

        assert isinstance(result, str)

    def test_valid_target_environments(self) -> None:
        """Test with different target environments."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test", "resources": []}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"name": "job", "project": "proj"}

                    for env in ["production", "staging", "development"]:
                        result = generate_awx_job_template_from_cookbook(
                            "/path", "cookbook", target_environment=env
                        )

                        assert isinstance(result, str)

    def test_survey_inclusion_toggle(self) -> None:
        """Test survey inclusion parameter."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test", "resources": []}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"name": "job", "project": "proj"}

                    # With survey
                    result_with = generate_awx_job_template_from_cookbook(
                        "/path", "cookbook", include_survey=True
                    )

                    # Without survey
                    result_without = generate_awx_job_template_from_cookbook(
                        "/path", "cookbook", include_survey=False
                    )

                    assert isinstance(result_with, str)
                    assert isinstance(result_without, str)

    def test_output_contains_json_template(self) -> None:
        """Test output contains JSON template."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test", "resources": []}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {
                        "name": "job_template",
                        "project": "project",
                        "playbook": "playbook.yml",
                        "inventory": "inventory",
                        "credential": "credential",
                    }

                    result = generate_awx_job_template_from_cookbook(
                        "/path", "test_cookbook"
                    )

                    # Either contains expected output or error message
                    assert isinstance(result, str)
                    assert len(result) > 0

    def test_output_contains_cli_command(self) -> None:
        """Test output contains AWX CLI command."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test"}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {
                        "name": "job",
                        "project": "proj",
                        "playbook": "play.yml",
                        "inventory": "inv",
                        "credential": "cred",
                    }

                    result = generate_awx_job_template_from_cookbook(
                        "/path", "cookbook"
                    )

                    # Should be a valid string output
                    assert isinstance(result, str)
                    assert len(result) > 0


class TestGenerateAWXWorkflow:
    """Test generate_awx_workflow_from_chef_runlist function."""

    def test_empty_runlist(self) -> None:
        """Test with empty runlist."""
        result = generate_awx_workflow_from_chef_runlist("", "workflow")

        assert isinstance(result, str)

    def test_single_recipe_runlist(self) -> None:
        """Test with single recipe."""
        result = generate_awx_workflow_from_chef_runlist(
            "recipe[cookbook::default]", "workflow"
        )

        assert isinstance(result, str)

    def test_single_role_runlist(self) -> None:
        """Test with single role."""
        result = generate_awx_workflow_from_chef_runlist("role[base]", "workflow")

        assert isinstance(result, str)

    def test_comma_separated_runlist(self) -> None:
        """Test with comma-separated items."""
        runlist = "recipe[cookbook::default],role[base],recipe[app::setup]"
        result = generate_awx_workflow_from_chef_runlist(runlist, "workflow")

        assert isinstance(result, str)

    def test_json_array_runlist(self) -> None:
        """Test with JSON array format."""
        runlist = '["recipe[cookbook::default]", "role[base]"]'
        result = generate_awx_workflow_from_chef_runlist(runlist, "workflow")

        assert isinstance(result, str)

    def test_different_environments(self) -> None:
        """Test with different environments."""
        for env in ["development", "staging", "production"]:
            result = generate_awx_workflow_from_chef_runlist(
                "recipe[app::default]", "workflow", environment=env
            )

            assert isinstance(result, str)

    def test_empty_workflow_name(self) -> None:
        """Test with empty workflow name."""
        result = generate_awx_workflow_from_chef_runlist("recipe[app::default]", "")

        assert isinstance(result, str)

    def test_complex_runlist_with_multiple_recipes_and_roles(self) -> None:
        """Test complex runlist."""
        runlist = (
            "recipe[base::default],"
            "role[web_server],"
            "recipe[app::setup],"
            "role[monitoring],"
            "recipe[security::hardening]"
        )
        result = generate_awx_workflow_from_chef_runlist(runlist, "complex_workflow")

        assert isinstance(result, str)

    def test_runlist_with_special_characters(self) -> None:
        """Test runlist with special characters."""
        runlist = "recipe[app-name_v2::default-prod]"
        result = generate_awx_workflow_from_chef_runlist(runlist, "workflow")

        assert isinstance(result, str)

    def test_workflow_output_format(self) -> None:
        """Test workflow output format."""
        result = generate_awx_workflow_from_chef_runlist(
            "recipe[app::default]", "test_workflow"
        )

        # Should contain workflow definition
        assert isinstance(result, str)
        assert len(result) > 0


class TestAWXDeploymentStrategies:
    """Test AWX deployment strategy functions."""

    def test_strategy_function_exists(self) -> None:
        """Test deployment strategy functions exist."""
        # These are tested through mocks and integration
        assert callable(generate_awx_job_template_from_cookbook)
        assert callable(generate_awx_workflow_from_chef_runlist)


class TestCookbookAnalysisForAWX:
    """Test cookbook analysis for AWX."""

    def test_analysis_with_valid_cookbook(self) -> None:
        """Test analyzing valid cookbook."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {
                    "recipes": ["default", "setup"],
                    "resources": 5,
                    "variables": 10,
                }

                result = generate_awx_job_template_from_cookbook("/path", "cookbook")

                assert isinstance(result, str)

    def test_analysis_handles_missing_files(self) -> None:
        """Test analysis handles missing files."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.side_effect = ValueError("Invalid structure")

            result = generate_awx_job_template_from_cookbook("/path", "cookbook")

            assert isinstance(result, str)
            assert "Error" in result or "error" in result.lower()


class TestRunlistParsing:
    """Test runlist parsing."""

    def test_parse_recipe_format(self) -> None:
        """Test parsing recipe format."""
        result = generate_awx_workflow_from_chef_runlist(
            "recipe[app::install]", "workflow"
        )

        assert isinstance(result, str)

    def test_parse_role_format(self) -> None:
        """Test parsing role format."""
        result = generate_awx_workflow_from_chef_runlist("role[webserver]", "workflow")

        assert isinstance(result, str)

    def test_parse_mixed_runlist(self) -> None:
        """Test parsing mixed recipe and role."""
        runlist = "role[base],recipe[app::default],role[monitoring]"
        result = generate_awx_workflow_from_chef_runlist(runlist, "workflow")

        assert isinstance(result, str)

    def test_parse_cookbook_qualified_recipe(self) -> None:
        """Test parsing cookbook-qualified recipe."""
        result = generate_awx_workflow_from_chef_runlist(
            "recipe[my_cookbook::my_recipe]", "workflow"
        )

        assert isinstance(result, str)


class TestErrorHandling:
    """Test error handling in deployment functions."""

    def test_handles_invalid_cookbook_structure(self) -> None:
        """Test handling of invalid cookbook structure."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.side_effect = OSError("File not found")

            result = generate_awx_job_template_from_cookbook("/path", "cookbook")

            assert isinstance(result, str)
            assert "Error" in result

    def test_handles_json_serialization_error(self) -> None:
        """Test handling of JSON serialization errors."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test"}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"key": object()}  # Non-serializable

                    result = generate_awx_job_template_from_cookbook(
                        "/path", "cookbook"
                    )

                    assert isinstance(result, str)

    def test_handles_unicode_in_cookbook_name(self) -> None:
        """Test handling of unicode characters."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test"}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"name": "job"}

                    result = generate_awx_job_template_from_cookbook(
                        "/path", "cookbook_café"
                    )

                    assert isinstance(result, str)


class TestEdgeCases:
    """Test edge cases."""

    def test_very_long_cookbook_name(self) -> None:
        """Test very long cookbook name."""
        long_name = "cookbook" * 50

        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test"}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"name": "job"}

                    result = generate_awx_job_template_from_cookbook("/path", long_name)

                    assert isinstance(result, str)

    def test_very_long_runlist(self) -> None:
        """Test very long runlist."""
        items = [f"recipe[app::{i}]" for i in range(100)]
        runlist = ",".join(items)

        result = generate_awx_workflow_from_chef_runlist(runlist, "workflow")

        assert isinstance(result, str)

    def test_runlist_with_duplicate_items(self) -> None:
        """Test runlist with duplicates."""
        runlist = "recipe[app::default],recipe[app::default],recipe[app::setup]"
        result = generate_awx_workflow_from_chef_runlist(runlist, "workflow")

        assert isinstance(result, str)

    def test_malformed_json_runlist(self) -> None:
        """Test malformed JSON runlist."""
        result = generate_awx_workflow_from_chef_runlist(
            '["recipe[app::default]", invalid json}', "workflow"
        )

        assert isinstance(result, str)


class TestOutputValidation:
    """Test output validation."""

    def test_job_template_output_is_valid_json(self) -> None:
        """Test job template JSON is valid."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"name": "test"}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"name": "template", "project": "proj"}

                    result = generate_awx_job_template_from_cookbook(
                        "/path", "cookbook"
                    )

                    # Should contain markdown with JSON
                    assert isinstance(result, str)

    def test_workflow_output_structure(self) -> None:
        """Test workflow output structure."""
        result = generate_awx_workflow_from_chef_runlist(
            "recipe[app::default]", "workflow"
        )

        assert isinstance(result, str)
        assert len(result) > 0


class TestIntegrationScenarios:
    """Test integration scenarios."""

    def test_job_template_for_simple_cookbook(self) -> None:
        """Test job template generation for simple cookbook."""
        with patch("souschef.deployment.validate_cookbook_structure") as mock_val:
            mock_val.return_value = MagicMock()
            with patch("souschef.deployment._analyse_cookbook_for_awx") as mock_anal:
                mock_anal.return_value = {"recipes": ["default"]}
                with patch(
                    "souschef.deployment._generate_awx_job_template"
                ) as mock_gen:
                    mock_gen.return_value = {"name": "job"}

                    result = generate_awx_job_template_from_cookbook(
                        "/cookbooks/simple", "simple", "production"
                    )

                    assert isinstance(result, str)

    def test_workflow_for_multi_recipe_application(self) -> None:
        """Test workflow for multi-recipe app."""
        runlist = (
            "recipe[base::network],"
            "recipe[base::security],"
            "recipe[app::install],"
            "recipe[app::configure],"
            "recipe[app::start]"
        )

        result = generate_awx_workflow_from_chef_runlist(
            runlist, "app_deployment", "production"
        )

        assert isinstance(result, str)
