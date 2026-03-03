"""
Focused coverage tests for souschef.deployment module.

This test suite targets the 43 uncovered lines (92% coverage) in deployment.py,
focusing on error paths, edge cases, and exception handling.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAnalyseRecipesErrorHandling:
    """Test recipe analysis with error handling and edge cases."""

    def test_analyse_recipes_empty_directory(self) -> None:
        """Test recipe analysis with empty recipes directory."""
        from souschef.deployment import _analyse_recipes

        with patch("souschef.deployment._safe_join") as mock_join:
            recipes_dir = MagicMock()
            recipes_dir.exists.return_value = True
            recipes_dir.glob.return_value = []
            mock_join.return_value = recipes_dir

            result = _analyse_recipes(Path("/fake"))

            assert result == []
            assert isinstance(result, list)

    def test_analyse_recipes_directory_not_exists(self) -> None:
        """Test recipe analysis when recipes directory does not exist."""
        from souschef.deployment import _analyse_recipes

        with patch("souschef.deployment._safe_join") as mock_join:
            recipes_dir = MagicMock()
            recipes_dir.exists.return_value = False
            mock_join.return_value = recipes_dir

            result = _analyse_recipes(Path("/fake"))

            assert result == []

    def test_analyse_recipes_multiple_recipes(self) -> None:
        """Test recipe analysis with multiple recipe files."""
        from souschef.deployment import _analyse_recipes

        with patch("souschef.deployment._safe_join") as mock_join:
            recipes_dir = MagicMock()
            recipes_dir.exists.return_value = True

            # Mock recipe files
            recipe1 = MagicMock()
            recipe1.stem = "default"
            recipe1.stat.return_value.st_size = 1024

            recipe2 = MagicMock()
            recipe2.stem = "server"
            recipe2.stat.return_value.st_size = 2048

            recipes_dir.glob.return_value = [recipe1, recipe2]
            mock_join.return_value = recipes_dir

            result = _analyse_recipes(Path("/fake"))

            assert len(result) == 2
            assert result[0]["name"] == "default"
            assert result[0]["size"] == 1024
            assert result[1]["name"] == "server"
            assert result[1]["size"] == 2048


class TestAnalyseAttributesForSurveyErrorHandling:
    """Test attribute analysis with error handling."""

    def test_analyse_attributes_for_survey_empty_directory(self) -> None:
        """Test attribute analysis with empty attributes directory."""
        from souschef.deployment import _analyse_attributes_for_survey

        with patch("souschef.deployment._safe_join") as mock_join:
            attributes_dir = MagicMock()
            attributes_dir.exists.return_value = True
            attributes_dir.glob.return_value = []
            mock_join.return_value = attributes_dir

            attributes, survey_fields = _analyse_attributes_for_survey(Path("/fake"))

            assert attributes == {}
            assert survey_fields == []

    def test_analyse_attributes_for_survey_directory_not_exists(self) -> None:
        """Test attribute analysis when directory does not exist."""
        from souschef.deployment import _analyse_attributes_for_survey

        with patch("souschef.deployment._safe_join") as mock_join:
            attributes_dir = MagicMock()
            attributes_dir.exists.return_value = False
            mock_join.return_value = attributes_dir

            attributes, survey_fields = _analyse_attributes_for_survey(Path("/fake"))

            assert attributes == {}
            assert survey_fields == []

    def test_analyse_attributes_for_survey_malformed_file(self) -> None:
        """Test attribute analysis handles malformed attribute files gracefully."""
        from souschef.deployment import _analyse_attributes_for_survey

        with (
            patch("souschef.deployment._safe_join") as mock_join,
            patch("builtins.open", side_effect=OSError("File read error")),
        ):
            attributes_dir = MagicMock()
            attributes_dir.exists.return_value = True

            attr_file = MagicMock()
            attr_file.open.side_effect = OSError("File read error")
            attributes_dir.glob.return_value = [attr_file]
            mock_join.return_value = attributes_dir

            attributes, survey_fields = _analyse_attributes_for_survey(Path("/fake"))

            assert attributes == {}
            assert survey_fields == []

    def test_analyse_attributes_for_survey_with_valid_attributes(self) -> None:
        """Test attribute analysis with valid attribute file content."""
        from souschef.deployment import _analyse_attributes_for_survey

        with patch("souschef.deployment._safe_join") as mock_join:
            attributes_dir = MagicMock()
            attributes_dir.exists.return_value = True

            # Mock attributes file
            attr_file = MagicMock()
            attr_file.open.return_value.__enter__.return_value.read.return_value = (
                "default['port'] = '80'\ndefault['user'] = 'root'"
            )
            attributes_dir.glob.return_value = [attr_file]
            mock_join.return_value = attributes_dir

            # Mock _extract_cookbook_attributes
            with patch(
                "souschef.deployment._extract_cookbook_attributes"
            ) as mock_extract:
                mock_extract.return_value = {"port": "80", "user": "root"}

                with patch(
                    "souschef.deployment._generate_survey_fields_from_attributes"
                ) as mock_survey:
                    mock_survey.return_value = [
                        {"variable": "port", "question_name": "Port"},
                        {"variable": "user", "question_name": "User"},
                    ]

                    attributes, survey_fields = _analyse_attributes_for_survey(
                        Path("/fake")
                    )

                    assert len(attributes) == 2
                    assert len(survey_fields) == 2


class TestAnalyseMetadataDependenciesErrorHandling:
    """Test metadata dependency analysis with error handling."""

    def test_analyse_metadata_dependencies_file_not_exists(self) -> None:
        """Test metadata analysis when metadata file does not exist."""
        from souschef.deployment import _analyse_metadata_dependencies

        with patch("souschef.deployment._safe_join") as mock_join:
            metadata_file = MagicMock()
            metadata_file.exists.return_value = False
            mock_join.return_value = metadata_file

            result = _analyse_metadata_dependencies(Path("/fake"))

            assert result == []

    def test_analyse_metadata_dependencies_read_error(self) -> None:
        """Test metadata analysis handles read errors gracefully."""
        from souschef.deployment import _analyse_metadata_dependencies

        with patch("souschef.deployment._safe_join") as mock_join:
            metadata_file = MagicMock()
            metadata_file.exists.return_value = True
            metadata_file.open.side_effect = OSError("Read error")
            mock_join.return_value = metadata_file

            result = _analyse_metadata_dependencies(Path("/fake"))

            assert result == []

    def test_analyse_metadata_dependencies_skip_exception(self) -> None:
        """Test metadata analysis silently skips when extraction fails."""
        from souschef.deployment import _analyse_metadata_dependencies

        with (
            patch("souschef.deployment._safe_join") as mock_join,
            patch("souschef.deployment._extract_cookbook_dependencies") as mock_extract,
        ):
            metadata_file = MagicMock()
            metadata_file.exists.return_value = True
            metadata_file.open.return_value.__enter__.return_value.read.return_value = (
                "depends 'apache2'"
            )
            mock_join.return_value = metadata_file

            # Simulate extraction error
            mock_extract.side_effect = Exception("Parse error")

            result = _analyse_metadata_dependencies(Path("/fake"))

            assert result == []


class TestCollectStaticFilesErrorHandling:
    """Test static files collection with error handling."""

    def test_collect_static_files_no_directories(self) -> None:
        """Test collecting files when templates and files directories don't exist."""
        from souschef.deployment import _collect_static_files

        with patch("souschef.deployment._safe_join") as mock_join:

            def safe_join_side_effect(path: Path, subdir: str) -> MagicMock:
                dir_mock = MagicMock()
                dir_mock.exists.return_value = False
                return dir_mock

            mock_join.side_effect = safe_join_side_effect

            templates, files = _collect_static_files(Path("/fake"))

            assert templates == []
            assert files == []

    def test_collect_static_files_templates_only(self) -> None:
        """Test collecting files with only templates directory existing."""
        from souschef.deployment import _collect_static_files

        with patch("souschef.deployment._safe_join") as mock_join:
            # Create mock directory structure
            templates_dir = MagicMock()
            templates_dir.exists.return_value = True
            file1 = MagicMock()
            file1.name = "default.erb"
            file1.is_file.return_value = True
            templates_dir.rglob.return_value = [file1]

            files_dir = MagicMock()
            files_dir.exists.return_value = False

            def safe_join_side_effect(path: Path, subdir: str) -> MagicMock:
                if subdir == "templates":
                    return templates_dir
                return files_dir

            mock_join.side_effect = safe_join_side_effect

            templates, files = _collect_static_files(Path("/fake"))

            assert len(templates) == 1
            assert templates[0] == "default.erb"
            assert files == []

    def test_collect_static_files_files_only(self) -> None:
        """Test collecting files with only files directory existing."""
        from souschef.deployment import _collect_static_files

        with patch("souschef.deployment._safe_join") as mock_join:
            templates_dir = MagicMock()
            templates_dir.exists.return_value = False

            files_dir = MagicMock()
            files_dir.exists.return_value = True
            file1 = MagicMock()
            file1.name = "script.sh"
            file1.is_file.return_value = True
            files_dir.rglob.return_value = [file1]

            def safe_join_side_effect(path: Path, subdir: str) -> MagicMock:
                if subdir == "templates":
                    return templates_dir
                return files_dir

            mock_join.side_effect = safe_join_side_effect

            templates, files = _collect_static_files(Path("/fake"))

            assert templates == []
            assert len(files) == 1
            assert files[0] == "script.sh"


class TestGenerateAWXJobTemplateErrorHandling:
    """Test AWX job template generation with error handling."""

    def test_generate_awx_job_template_empty_cookbook_name(self) -> None:
        """Test job template generation rejects empty cookbook name."""
        from souschef.deployment import generate_awx_job_template_from_cookbook

        result = generate_awx_job_template_from_cookbook(
            cookbook_path="/fake",
            cookbook_name="",
        )

        assert "Error: Cookbook name cannot be empty" in result
        assert "Suggestion:" in result

    def test_generate_awx_job_template_whitespace_name(self) -> None:
        """Test job template generation rejects whitespace-only cookbook name."""
        from souschef.deployment import generate_awx_job_template_from_cookbook

        result = generate_awx_job_template_from_cookbook(
            cookbook_path="/fake",
            cookbook_name="   ",
        )

        assert "Error: Cookbook name cannot be empty" in result

    def test_generate_awx_job_template_survey_field_generation(self) -> None:
        """Test AWX job template survey field generation logic."""
        from souschef.deployment import _generate_awx_job_template

        analysis = {
            "name": "test",
            "recipes": [],
            "attributes": {},
            "dependencies": [],
            "templates": [],
            "files": [],
            "survey_fields": [
                {"variable": "port", "question_name": "Port"},
                {"variable": "user", "question_name": "User"},
            ],
        }

        result = _generate_awx_job_template(
            analysis, "test", "production", include_survey=True
        )

        assert isinstance(result, dict)
        assert result["survey_enabled"] is True
        assert "survey_spec" in result
        assert len(result["survey_spec"]["spec"]) == 2


class TestParseChefRunlistEdgeCases:
    """Test Chef runlist parsing with edge cases."""

    @pytest.mark.parametrize(
        "input_runlist,expected_count",
        [
            ("recipe[apache2::default]", 1),
            ("recipe[apache2::default], recipe[mysql::server]", 2),
            ('["recipe[apache2::default]", "recipe[mysql::server]"]', 2),
            ("role[webserver]", 1),
            ("role[webserver], recipe[apache2::default]", 2),
        ],
    )
    def test_parse_chef_runlist_variants(
        self, input_runlist: str, expected_count: int
    ) -> None:
        """Test parsing various runlist formats."""
        from souschef.deployment import _parse_chef_runlist

        result = _parse_chef_runlist(input_runlist)

        assert len(result) == expected_count
        assert all(isinstance(item, str) for item in result)

    def test_parse_chef_runlist_empty_string(self) -> None:
        """Test parsing empty runlist string."""
        from souschef.deployment import _parse_chef_runlist

        result = _parse_chef_runlist("")

        assert isinstance(result, list)
        # Empty string may produce empty list or list with empty string

    def test_parse_chef_runlist_whitespace_only(self) -> None:
        """Test parsing whitespace-only runlist."""
        from souschef.deployment import _parse_chef_runlist

        result = _parse_chef_runlist("   ")

        assert isinstance(result, list)


class TestGenerateAWXWorkflowEdgeCases:
    """Test AWX workflow generation with edge cases."""

    def test_generate_awx_workflow_empty_runlist(self) -> None:
        """Test workflow generation rejects empty runlist."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        result = generate_awx_workflow_from_chef_runlist(
            runlist_content="",
            workflow_name="test",
        )

        assert "Error" in result
        assert "cannot be empty" in result

    def test_generate_awx_workflow_whitespace_runlist(self) -> None:
        """Test workflow generation rejects whitespace-only runlist."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        result = generate_awx_workflow_from_chef_runlist(
            runlist_content="   ",
            workflow_name="test",
        )

        assert "Error" in result
        assert "cannot be empty" in result

    def test_generate_awx_workflow_empty_workflow_name(self) -> None:
        """Test workflow generation rejects empty workflow name."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        result = generate_awx_workflow_from_chef_runlist(
            runlist_content="recipe[apache2::default]",
            workflow_name="",
        )

        assert "Error" in result
        assert "Workflow name cannot be empty" in result

    def test_generate_awx_workflow_whitespace_name(self) -> None:
        """Test workflow generation rejects whitespace-only workflow name."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        result = generate_awx_workflow_from_chef_runlist(
            runlist_content="recipe[apache2::default]",
            workflow_name="   ",
        )

        assert "Error" in result
        assert "Workflow name cannot be empty" in result

    def test_generate_awx_workflow_runlist_parsing_empty_result(self) -> None:
        """Test workflow generation handles empty runlist parsing result."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        with patch("souschef.deployment._parse_chef_runlist") as mock_parse:
            mock_parse.return_value = []

            result = generate_awx_workflow_from_chef_runlist(
                runlist_content="invalid[format]",
                workflow_name="test-workflow",
            )

            assert "Error" in result
            assert "parsing resulted in no items" in result


class TestGenerateAWXProjectEdgeCases:
    """Test AWX project generation with edge cases."""

    def test_generate_awx_project_empty_project_name(self) -> None:
        """Test project generation rejects empty project name."""
        from souschef.deployment import generate_awx_project_from_cookbooks

        result = generate_awx_project_from_cookbooks(
            cookbooks_directory="/fake",
            project_name="",
        )

        assert "Error" in result
        assert "Project name cannot be empty" in result

    def test_generate_awx_project_whitespace_name(self) -> None:
        """Test project generation rejects whitespace-only project name."""
        from souschef.deployment import generate_awx_project_from_cookbooks

        result = generate_awx_project_from_cookbooks(
            cookbooks_directory="/fake",
            project_name="   ",
        )

        assert "Error" in result
        assert "Project name cannot be empty" in result

    @patch("souschef.deployment._analyse_cookbooks_directory")
    @patch("souschef.deployment.validate_directory_exists")
    def test_generate_awx_project_valid_structure(
        self,
        mock_validate: MagicMock,
        mock_analyse: MagicMock,
    ) -> None:
        """Test project generation produces valid output."""
        from souschef.deployment import generate_awx_project_from_cookbooks

        mock_validate.return_value = Path("/cookbooks")
        mock_analyse.return_value = {
            "total_cookbooks": 2,
            "cookbooks": {
                "apache2": {
                    "recipes": [{"name": "default"}],
                    "attributes": {},
                    "templates": [],
                    "files": [],
                },
                "mysql": {
                    "recipes": [{"name": "server"}],
                    "attributes": {},
                    "templates": [],
                    "files": [],
                },
            },
            "total_recipes": 2,
            "total_templates": 0,
            "total_files": 0,
        }

        result = generate_awx_project_from_cookbooks(
            cookbooks_directory="/fake",
            project_name="test-project",
        )

        assert "AWX/AAP Project" in result
        assert "test-project" in result
        assert "apache2" in result or "recipes" in result


class TestGenerateAWXInventorySourceEdgeCases:
    """Test AWX inventory source generation with edge cases."""

    def test_generate_awx_inventory_source_empty_url(self) -> None:
        """Test inventory source generation rejects empty Chef server URL."""
        from souschef.deployment import generate_awx_inventory_source_from_chef

        result = generate_awx_inventory_source_from_chef(
            chef_server_url="",
        )

        assert "Error" in result
        assert "Chef server URL cannot be empty" in result

    def test_generate_awx_inventory_source_whitespace_url(self) -> None:
        """Test inventory source generation rejects whitespace-only URL."""
        from souschef.deployment import generate_awx_inventory_source_from_chef

        result = generate_awx_inventory_source_from_chef(
            chef_server_url="   ",
        )

        assert "Error" in result
        assert "Chef server URL cannot be empty" in result

    def test_generate_awx_inventory_source_invalid_url_format(self) -> None:
        """Test inventory source generation handles invalid URL format."""
        from souschef.deployment import generate_awx_inventory_source_from_chef

        with patch("souschef.deployment.validate_user_provided_url") as mock_validate:
            mock_validate.side_effect = ValueError("Invalid URL format")

            result = generate_awx_inventory_source_from_chef(
                chef_server_url="not-a-valid-url",
            )

            assert "Error" in result
            assert "Invalid Chef server URL" in result

    def test_generate_chef_inventory_script_content(self) -> None:
        """Test Chef inventory script contains required content."""
        from souschef.deployment import _generate_chef_inventory_script

        result = _generate_chef_inventory_script(
            chef_server_url="https://chef.example.com"
        )

        assert isinstance(result, str)
        assert "chef.example.com" in result
        assert "python" in result.lower()
        assert "inventory" in result.lower()

    def test_generate_chef_inventory_source_schedule_mapping(self) -> None:
        """Test Chef inventory source schedule mapping."""
        from souschef.deployment import _generate_chef_inventory_source

        result_daily = _generate_chef_inventory_source(
            "https://chef.example.com", "daily"
        )
        result_hourly = _generate_chef_inventory_source(
            "https://chef.example.com", "hourly"
        )
        result_weekly = _generate_chef_inventory_source(
            "https://chef.example.com", "weekly"
        )

        # Verify different timeouts for different schedules
        assert result_daily["update_cache_timeout"] == 86400
        assert result_hourly["update_cache_timeout"] == 3600
        assert result_weekly["update_cache_timeout"] == 604800


class TestConvertChefDeploymentEdgeCases:
    """Test Chef deployment conversion with edge cases."""

    def test_convert_chef_deployment_invalid_pattern(self) -> None:
        """Test conversion rejects invalid deployment pattern."""
        from souschef.deployment import convert_chef_deployment_to_ansible_strategy

        with patch("souschef.deployment.validate_cookbook_structure") as mock_validate:
            mock_validate.return_value = Path("/cookbook")

            result = convert_chef_deployment_to_ansible_strategy(
                cookbook_path="/fake",
                deployment_pattern="invalid_pattern",
            )

            assert "Error" in result
            assert "Invalid deployment pattern" in result
            assert "invalid_pattern" in result

    @patch("souschef.deployment._analyse_chef_deployment_pattern")
    @patch("souschef.deployment.validate_cookbook_structure")
    def test_convert_chef_deployment_auto_detection(
        self,
        mock_validate: MagicMock,
        mock_analyse: MagicMock,
    ) -> None:
        """Test deployment conversion with auto-detection."""
        from souschef.deployment import convert_chef_deployment_to_ansible_strategy

        mock_validate.return_value = Path("/cookbook")
        mock_analyse.return_value = {
            "detected_pattern": "blue_green",
            "deployment_steps": [],
            "health_checks": [],
            "service_management": [],
        }

        with patch(
            "souschef.deployment._generate_ansible_deployment_strategy"
        ) as mock_gen:
            mock_gen.return_value = "## Blue/Green Strategy"

            result = convert_chef_deployment_to_ansible_strategy(
                cookbook_path="/fake",
                deployment_pattern="auto",
            )

            assert "Ansible Deployment Strategy" in result
            assert "auto" in result.lower() or "detected" in result.lower()


class TestAnalyseChefDeploymentPatternEdgeCases:
    """Test Chef deployment pattern analysis with edge cases."""

    @patch("souschef.deployment._safe_join")
    def test_analyse_chef_deployment_pattern_no_recipes(
        self, mock_join: MagicMock
    ) -> None:
        """Test pattern analysis when recipes directory doesn't exist."""
        from souschef.deployment import _analyse_chef_deployment_pattern

        recipes_dir = MagicMock()
        recipes_dir.exists.return_value = False
        mock_join.return_value = recipes_dir

        result = _analyse_chef_deployment_pattern(Path("/fake"))

        assert isinstance(result, dict)
        assert result["deployment_steps"] == []
        assert result["health_checks"] == []

    @patch("souschef.deployment._safe_join")
    def test_analyse_chef_deployment_pattern_malformed_recipe(
        self, mock_join: MagicMock
    ) -> None:
        """Test pattern analysis handles malformed recipes gracefully."""
        from souschef.deployment import _analyse_chef_deployment_pattern

        recipes_dir = MagicMock()
        recipes_dir.exists.return_value = True

        recipe = MagicMock()
        recipe.open.side_effect = OSError("Read error")
        recipes_dir.glob.return_value = [recipe]
        mock_join.return_value = recipes_dir

        result = _analyse_chef_deployment_pattern(Path("/fake"))

        assert isinstance(result, dict)
        # Should still return valid structure despite read error


class TestBlueGreenDeploymentEdgeCases:
    """Test blue-green deployment generation with edge cases."""

    def test_generate_blue_green_playbook_invalid_health_url_absolute(self) -> None:
        """Test blue-green generation rejects absolute health check URLs."""
        from souschef.deployment import generate_blue_green_deployment_playbook

        result = generate_blue_green_deployment_playbook(
            app_name="test-app",
            health_check_url="http://example.com/health",  # NOSONAR
        )

        assert "Error" in result
        assert "must be a path starting with '/'" in result

    def test_generate_blue_green_playbook_valid_health_url(self) -> None:
        """Test blue-green generation accepts valid health check URLs."""
        from souschef.deployment import generate_blue_green_deployment_playbook

        result = generate_blue_green_deployment_playbook(
            app_name="test-app",
            health_check_url="/api/health",
        )

        assert "Blue/Green Deployment Playbook" in result
        assert "test-app" in result

    def test_generate_blue_green_playbook_structure(self) -> None:
        """Test blue-green playbook contains required components."""
        from souschef.deployment import _generate_blue_green_playbook

        playbook = _generate_blue_green_playbook("test-app", "/health")

        assert isinstance(playbook, dict)
        assert "main_playbook" in playbook
        assert "health_check" in playbook
        assert "rollback" in playbook
        assert "load_balancer_config" in playbook


class TestCanaryDeploymentEdgeCases:
    """Test canary deployment with edge cases."""

    @pytest.mark.parametrize(
        "app_name,percentage,steps,expect_error",
        [
            ("", 10, "10,20", True),
            ("app", 0, "10,20", True),
            ("app", 101, "10,20", True),
            ("app", 1, "1,100", False),
            ("app", 50, "50,100", False),
            ("app", 100, "100", False),
        ],
    )
    def test_validate_canary_inputs_parametrised(
        self,
        app_name: str,
        percentage: int,
        steps: str,
        expect_error: bool,
    ) -> None:
        """Test canary validation with various input combinations."""
        from souschef.deployment import _validate_canary_inputs

        result_steps, error = _validate_canary_inputs(app_name, percentage, steps)

        if expect_error:
            assert error is not None
            assert result_steps is None
        else:
            assert error is None
            assert result_steps is not None

    def test_generate_canary_strategy_structure(self) -> None:
        """Test canary strategy contains required playbooks."""
        from souschef.deployment import _generate_canary_strategy

        strategy = _generate_canary_strategy("test-app", 10, [10, 25, 50, 100])

        assert isinstance(strategy, dict)
        assert "canary_playbook" in strategy
        assert "monitoring" in strategy
        assert "progressive_rollout" in strategy
        assert "rollback" in strategy


class TestAnalyseApplicationCookbookErrorHandling:
    """Test application cookbook analysis with error handling."""

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_analyse_application_cookbook_invalid_type(
        self, mock_validate: MagicMock
    ) -> None:
        """Test application pattern analysis rejects invalid application type."""
        from souschef.deployment import analyse_chef_application_patterns

        mock_validate.return_value = Path("/cookbook")

        result = analyse_chef_application_patterns(
            cookbook_path="/fake",
            application_type="invalid_type",
        )

        assert "Error" in result
        assert "Invalid application type" in result

    @patch("souschef.deployment._analyse_application_cookbook")
    @patch("souschef.deployment.validate_cookbook_structure")
    def test_analyse_application_cookbook_valid_type(
        self,
        mock_validate: MagicMock,
        mock_analyse: MagicMock,
    ) -> None:
        """Test application pattern analysis with valid application types."""
        from souschef.deployment import analyse_chef_application_patterns

        mock_validate.return_value = Path("/cookbook")
        mock_analyse.return_value = {
            "application_type": "web_application",
            "deployment_patterns": [],
            "resources": ["package", "template"],
            "complexity": "medium",
            "effort_estimate": "2-3 weeks",
            "risk_level": "medium",
        }

        result = analyse_chef_application_patterns(
            cookbook_path="/fake",
            application_type="web_application",
        )

        assert "Chef Application Patterns Analysis" in result

    @pytest.mark.parametrize(
        "app_type",
        ["web_application", "database", "service", "batch", "api"],
    )
    @patch("souschef.deployment._analyse_application_cookbook")
    @patch("souschef.deployment.validate_cookbook_structure")
    def test_analyse_application_valid_app_types(
        self,
        mock_validate: MagicMock,
        mock_analyse: MagicMock,
        app_type: str,
    ) -> None:
        """Test application analysis supports all valid application types."""
        from souschef.deployment import analyse_chef_application_patterns

        mock_validate.return_value = Path("/cookbook")
        mock_analyse.return_value = {
            "application_type": app_type,
            "deployment_patterns": [],
            "resources": [],
            "complexity": "medium",
            "effort_estimate": "2-3 weeks",
            "risk_level": "medium",
        }

        result = analyse_chef_application_patterns(
            cookbook_path="/fake",
            application_type=app_type,
        )

        assert "Error" not in result or app_type not in result


class TestAnalyseCookbooksDirectoryEdgeCases:
    """Test cookbooks directory analysis with edge cases."""

    @patch("souschef.deployment._analyse_cookbook_for_awx")
    def test_analyse_cookbooks_directory_empty(self, mock_analyse: MagicMock) -> None:
        """Test directory analysis with no cookbooks."""
        from souschef.deployment import _analyse_cookbooks_directory

        with patch.object(Path, "iterdir") as mock_iterdir:
            mock_iterdir.return_value = []

            result = _analyse_cookbooks_directory(Path("/fake"))

            assert result["total_cookbooks"] == 0
            assert result["total_recipes"] == 0

    @patch("souschef.deployment._analyse_cookbook_for_awx")
    def test_analyse_cookbooks_directory_mixed_content(
        self, mock_analyse: MagicMock
    ) -> None:
        """Test directory analysis filters out non-directory entries."""
        from souschef.deployment import _analyse_cookbooks_directory

        mock_analyse.return_value = {
            "name": "test",
            "recipes": [{"name": "default"}],
            "attributes": {},
            "dependencies": [],
            "templates": [],
            "files": [],
            "survey_fields": [],
        }

        with patch.object(Path, "iterdir") as mock_iterdir:
            # Create mock entries - mix of directories and files
            dir1 = MagicMock()
            dir1.is_dir.return_value = True
            dir1.name = "apache2"

            file1 = MagicMock()
            file1.is_dir.return_value = False
            file1.name = "README.md"

            dir2 = MagicMock()
            dir2.is_dir.return_value = True
            dir2.name = "mysql"

            mock_iterdir.return_value = [dir1, file1, dir2]

            result = _analyse_cookbooks_directory(Path("/fake"))

            # Should only process directories, not the file
            assert result["total_cookbooks"] == 2


class TestExtractAttributesEdgeCases:
    """Test attribute extraction with edge cases."""

    @pytest.mark.parametrize(
        "content",
        [
            "default['app']['port'] = 8080",
            'default["app"]["user"] = "www-data"',
            "default['app']['hosts'] = ['localhost', 'example.com']",
            "default['multi']['level']['key'] = 'value'",
        ],
    )
    def test_extract_cookbook_attributes_various_formats(self, content: str) -> None:
        """Test attribute extraction with various attribute formats."""
        from souschef.deployment import _extract_cookbook_attributes

        result = _extract_cookbook_attributes(content)

        assert isinstance(result, dict)

    def test_extract_cookbook_attributes_long_value_protection(self) -> None:
        """Test attribute extraction protects against ReDoS with long values."""
        from souschef.deployment import _extract_cookbook_attributes

        # Create content with extremely long attribute value
        long_value = "x" * 10000  # Exceeds MAX_ATTRIBUTE_VALUE_LENGTH
        content = f"default['app']['config'] = '{long_value}'"

        result = _extract_cookbook_attributes(content)

        # Should not cause regex failure or timeout
        assert isinstance(result, dict)


class TestExtractDependenciesEdgeCases:
    """Test dependency extraction with edge cases."""

    @pytest.mark.parametrize(
        "content",
        [
            "depends 'apache2'",
            'depends "mysql", ">= 2.0"',
            "depends 'postgresql', '~> 3.0'",
            'depends "redis"',
        ],
    )
    def test_extract_cookbook_dependencies_various_formats(self, content: str) -> None:
        """Test dependency extraction with various formats."""
        from souschef.deployment import _extract_cookbook_dependencies

        result = _extract_cookbook_dependencies(content)

        assert isinstance(result, list)

    def test_extract_cookbook_dependencies_multiple(self) -> None:
        """Test extraction of multiple dependencies."""
        from souschef.deployment import _extract_cookbook_dependencies

        content = """
        depends 'apache2'
        depends 'mysql'
        depends 'php'
        """

        result = _extract_cookbook_dependencies(content)

        assert len(result) == 3
        assert all(isinstance(dep, str) for dep in result)


class TestGenerateSurveyFieldsEdgeCases:
    """Test survey field generation with edge cases."""

    @pytest.mark.parametrize(
        "attr_value,expected_type",
        [
            ("true", "boolean"),
            ("false", "boolean"),
            ("123", "integer"),
            ("80", "integer"),
            ("example.com", "text"),
            ("user@example.com", "text"),
        ],
    )
    def test_generate_survey_fields_type_detection(
        self, attr_value: str, expected_type: str
    ) -> None:
        """Test survey field type detection for various attribute values."""
        from souschef.deployment import _generate_survey_fields_from_attributes

        attributes = {"test_attr": attr_value}
        result = _generate_survey_fields_from_attributes(attributes)

        assert len(result) == 1
        assert result[0]["type"] == expected_type

    def test_generate_survey_fields_field_structure(self) -> None:
        """Test generated survey fields contain required structure."""
        from souschef.deployment import _generate_survey_fields_from_attributes

        attributes = {"port": "80", "enabled": "true"}
        result = _generate_survey_fields_from_attributes(attributes)

        for field in result:
            assert "variable" in field
            assert "question_name" in field
            assert "type" in field
            assert "default" in field


class TestFormatAndRecommendationFunctions:
    """Test formatting and recommendation generation functions."""

    def test_format_deployment_analysis_structure(self) -> None:
        """Test deployment analysis formatting structure."""
        from souschef.deployment import _format_deployment_analysis

        analysis = {
            "deployment_steps": [{"type": "execute"}],
            "health_checks": [{"type": "http"}],
            "service_management": [{"type": "service"}],
            "complexity": "high",
        }

        result = _format_deployment_analysis(analysis)

        assert isinstance(result, str)
        assert "Deployment steps: 1" in result
        assert "complexity" in result.lower()

    def test_format_deployment_patterns_dict_format(self) -> None:
        """Test formatting deployment patterns with dict format."""
        from souschef.deployment import _format_deployment_patterns

        analysis = {
            "deployment_patterns": [
                {"type": "blue_green", "recipe": "deploy", "confidence": "high"},
                {"type": "canary", "recipe": "canary", "confidence": "medium"},
            ]
        }

        result = _format_deployment_patterns(analysis)

        assert isinstance(result, str)
        assert "blue_green" in result.lower() or "blue" in result.lower()
        assert "canary" in result.lower()

    def test_format_chef_resources_analysis_new_format(self) -> None:
        """Test formatting Chef resources with new format."""
        from souschef.deployment import _format_chef_resources_analysis

        analysis = {
            "resources": ["package", "service", "template", "package", "package"]
        }

        result = _format_chef_resources_analysis(analysis)

        assert isinstance(result, str)
        assert "package" in result.lower() or "3" in result

    def test_recommend_ansible_strategies_no_patterns(self) -> None:
        """Test strategy recommendations with no detected patterns."""
        from souschef.deployment import _recommend_ansible_strategies

        analysis = {"deployment_patterns": []}

        result = _recommend_ansible_strategies(analysis)

        assert isinstance(result, str)
        assert len(result) > 0


class TestErrorConditionsAndExceptionHandling:
    """Test error conditions and exception handling across module."""

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_generate_awx_job_template_cookbook_validation_error(
        self, mock_validate: MagicMock
    ) -> None:
        """Test job template generation handles cookbook validation errors."""
        from souschef.core.errors import ChefFileNotFoundError
        from souschef.deployment import generate_awx_job_template_from_cookbook

        mock_validate.side_effect = ChefFileNotFoundError("/nonexistent", "cookbook")

        result = generate_awx_job_template_from_cookbook(
            cookbook_path="/nonexistent",
            cookbook_name="test",
        )

        # Check for error message (may contain "Error" or error details)
        assert "error" in result.lower() or "could not find" in result.lower()

    def test_generate_blue_green_deployment_exception_handling(self) -> None:
        """Test blue-green playbook generation exception handling."""
        from souschef.deployment import generate_blue_green_deployment_playbook

        with patch("souschef.deployment._generate_blue_green_playbook") as mock_gen:
            mock_gen.side_effect = Exception("Generation error")

            result = generate_blue_green_deployment_playbook(
                app_name="test-app",
                health_check_url="/health",
            )

            assert "Error" in result

    def test_canary_deployment_exception_handling(self) -> None:
        """Test canary deployment exception handling."""
        from souschef.deployment import generate_canary_deployment_strategy

        with patch("souschef.deployment._generate_canary_strategy") as mock_gen:
            mock_gen.side_effect = Exception("Generation error")

            result = generate_canary_deployment_strategy(
                app_name="test-app",
                canary_percentage=10,
                rollout_steps="10,20",
            )

            assert "Error" in result
