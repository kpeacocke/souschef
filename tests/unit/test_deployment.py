"""
Tests for souschef.deployment module.

These tests cover AWX/Tower integration, deployment strategies, and
Chef cookbook analysis for deployment planning.
"""

from unittest.mock import patch


class TestCanaryDeploymentValidation:
    """Test canary deployment input validation."""

    def test_validate_canary_inputs_success(self):
        """Test successful validation of canary inputs."""
        from souschef.deployment import _validate_canary_inputs

        steps, error = _validate_canary_inputs("test-app", 20, "10,20")
        assert steps == [10, 20]
        assert error is None

    def test_validate_canary_inputs_invalid_percentage(self):
        """Test validation fails with invalid percentage."""
        from souschef.deployment import _validate_canary_inputs

        steps, error = _validate_canary_inputs("test-app", 150, "10,20")
        assert steps is None
        assert error is not None
        assert "Canary percentage must be between" in error

    def test_validate_canary_inputs_zero_percentage(self):
        """Test validation fails with zero percentage."""
        from souschef.deployment import _validate_canary_inputs

        steps, error = _validate_canary_inputs("test-app", 0, "10,20")
        assert steps is None
        assert error is not None
        assert "Canary percentage must be between" in error

    def test_validate_canary_inputs_empty_app_name(self):
        """Test validation fails with empty app name."""
        from souschef.deployment import _validate_canary_inputs

        steps, error = _validate_canary_inputs("", 20, "10,20")
        assert steps is None
        assert error is not None
        assert "Application name cannot be empty" in error

    def test_validate_canary_inputs_invalid_steps(self):
        """Test validation fails with steps outside valid range."""
        from souschef.deployment import _validate_canary_inputs

        steps, error = _validate_canary_inputs("test-app", 20, "10,150")
        assert steps is None
        assert error is not None
        assert "must be between 1 and 100" in error

    def test_validate_canary_inputs_unordered_steps(self):
        """Test validation fails with unordered steps."""
        from souschef.deployment import _validate_canary_inputs

        steps, error = _validate_canary_inputs("test-app", 20, "50,10")
        assert steps is None
        assert error is not None
        assert "ascending order" in error


class TestCanaryWorkflowBuilding:
    """Test canary workflow guide generation."""

    def test_build_canary_workflow_guide_basic(self):
        """Test basic canary workflow guide generation."""
        from souschef.deployment import _build_canary_workflow_guide

        result = _build_canary_workflow_guide(20, [10, 20])

        assert "## Deployment Workflow:" in result
        assert "Step 1: 10% traffic" in result
        assert "Step 2: 20% traffic" in result
        assert "Monitor" in result

    def test_build_canary_workflow_guide_single_step(self):
        """Test workflow guide with single deployment step."""
        from souschef.deployment import _build_canary_workflow_guide

        result = _build_canary_workflow_guide(50, [100])

        assert "Step 1: 100% traffic" in result
        assert "full rollout" in result
        assert "Monitor" in result


class TestCanaryOutputFormatting:
    """Test canary deployment output formatting."""

    def test_format_canary_output_success(self):
        """Test formatting canary deployment output."""
        from souschef.deployment import _format_canary_output

        strategy = {
            "canary_playbook": "- name: Deploy\n  task: deploy",
            "monitoring": "- name: Monitor\n  task: monitor",
            "progressive_rollout": "- name: Rollout\n  task: rollout",
            "rollback": "- name: Rollback\n  task: rollback",
        }

        result = _format_canary_output(
            "test-app",
            20,
            "10,20",
            [10, 20],
            strategy,
        )

        assert "Canary Deployment Strategy" in result
        assert "Application: test-app" in result
        assert "Initial Canary: 20%" in result
        assert "Rollout Steps: 10,20" in result


class TestGenerateCanaryDeploymentStrategy:
    """Test high-level canary deployment strategy generation."""

    def test_generate_canary_deployment_strategy_success(self):
        """Test successful canary deployment strategy generation."""
        from souschef.deployment import generate_canary_deployment_strategy

        result = generate_canary_deployment_strategy(
            app_name="test-app",
            canary_percentage=20,
            rollout_steps="10,20",
        )

        assert "Application: test-app" in result
        assert "Initial Canary: 20%" in result
        assert "Rollout Steps: 10,20" in result

    def test_generate_canary_deployment_strategy_invalid_percentage(self):
        """Test canary strategy fails with invalid percentage."""
        from souschef.deployment import generate_canary_deployment_strategy

        result = generate_canary_deployment_strategy(
            app_name="test-app",
            canary_percentage=150,
            rollout_steps="10,20",
        )
        assert "Error" in result
        assert "Canary percentage must be between" in result

    def test_generate_canary_deployment_strategy_empty_app_name(self):
        """Test canary strategy fails with empty app name."""
        from souschef.deployment import generate_canary_deployment_strategy

        result = generate_canary_deployment_strategy(
            app_name="",
            canary_percentage=20,
            rollout_steps="10,20",
        )
        assert "Error" in result
        assert "Application name cannot be empty" in result


class TestGenerateBlueGreenDeploymentPlaybook:
    """Test blue-green deployment playbook generation."""

    def test_generate_blue_green_playbook_success(self):
        """Test successful blue-green playbook generation."""
        from souschef.deployment import generate_blue_green_deployment_playbook

        result = generate_blue_green_deployment_playbook(
            app_name="test-app",
            health_check_url="/health",
        )

        assert "Blue/Green Deployment Playbook" in result
        assert "Application: test-app" in result
        assert "Deploy to blue environment" in result or "Usage Instructions" in result

    def test_generate_blue_green_playbook_invalid_health_check(self):
        """Test blue-green playbook with invalid health check URL."""
        from souschef.deployment import generate_blue_green_deployment_playbook

        result = generate_blue_green_deployment_playbook(
            app_name="test-app",
            health_check_url="https://example.com/health",
        )

        assert "Error" in result
        assert "must be a path starting with '/'" in result

    def test_generate_blue_green_playbook_empty_app_name(self):
        """Test blue-green playbook with empty app name."""
        from souschef.deployment import generate_blue_green_deployment_playbook

        result = generate_blue_green_deployment_playbook(
            app_name="",
            health_check_url="/health",
        )

        assert "Error" in result
        assert "Application name cannot be empty" in result


class TestConvertChefDeploymentToAnsibleStrategy:
    """Test Chef deployment to Ansible strategy conversion."""

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_convert_chef_deployment_basic(self, mock_validate, tmp_path):
        """Test basic Chef deployment conversion."""
        from souschef.deployment import convert_chef_deployment_to_ansible_strategy

        cookbook_dir = tmp_path / "test_cookbook"
        cookbook_dir.mkdir()
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        mock_validate.return_value = cookbook_dir

        result = convert_chef_deployment_to_ansible_strategy(
            cookbook_path="/fake/path",
        )

        assert "Ansible Deployment Strategy" in result
        assert "Detected Pattern:" in result

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_convert_chef_deployment_nonexistent_path(self, mock_validate):
        """Test conversion fails with nonexistent cookbook path."""
        # Mock validation failure
        from souschef.core.errors import ChefFileNotFoundError
        from souschef.deployment import convert_chef_deployment_to_ansible_strategy

        mock_validate.side_effect = ChefFileNotFoundError(
            "/nonexistent/path", "cookbook"
        )

        result = convert_chef_deployment_to_ansible_strategy(
            cookbook_path="/nonexistent/path",
        )

        assert "could not find" in result.lower()


class TestParseChefRunlist:
    """Test Chef runlist parsing."""

    def test_parse_chef_runlist_basic(self):
        """Test parsing basic Chef runlist."""
        from souschef.deployment import _parse_chef_runlist

        runlist = "recipe[apache2::default], recipe[mysql::server]"
        result = _parse_chef_runlist(runlist)

        assert len(result) == 2
        assert "apache2::default" in result
        assert "mysql::server" in result

    def test_parse_chef_runlist_with_roles(self):
        """Test parsing runlist with roles."""
        from souschef.deployment import _parse_chef_runlist

        runlist = "role[web], recipe[apache2::default]"
        result = _parse_chef_runlist(runlist)

        assert "role[web]" in result or "web" in result
        assert "apache2::default" in result


class TestExtractCookbookAttributes:
    """Test cookbook attribute extraction."""

    def test_extract_cookbook_attributes_basic(self):
        """Test extracting basic cookbook attributes."""
        from souschef.deployment import _extract_cookbook_attributes

        content = """
        default['apache']['port'] = 80
        default['apache']['user'] = 'www-data'
        """
        result = _extract_cookbook_attributes(content)

        assert isinstance(result, dict)
        # Should find attribute patterns (may extract 0 or more)

    def test_extract_cookbook_attributes_empty(self):
        """Test extraction with empty content."""
        from souschef.deployment import _extract_cookbook_attributes

        result = _extract_cookbook_attributes("")
        assert isinstance(result, dict)


class TestExtractCookbookDependencies:
    """Test cookbook dependency extraction."""

    def test_extract_cookbook_dependencies_basic(self):
        """Test extracting cookbook dependencies."""
        from souschef.deployment import _extract_cookbook_dependencies

        content = """
        depends 'apache2', '~> 1.0'
        depends 'mysql', '>= 2.0'
        """
        result = _extract_cookbook_dependencies(content)

        assert isinstance(result, list)
        assert "apache2" in result
        assert "mysql" in result

    def test_extract_cookbook_dependencies_empty(self):
        """Test extraction with no dependencies."""
        from souschef.deployment import _extract_cookbook_dependencies

        result = _extract_cookbook_dependencies("")
        assert isinstance(result, list)
        assert len(result) == 0


class TestGenerateSurveyFieldsFromAttributes:
    """Test AWX survey field generation from attributes."""

    def test_generate_survey_fields_basic(self):
        """Test generating survey fields from attributes."""
        from souschef.deployment import _generate_survey_fields_from_attributes

        attributes = {
            "port": "80",
            "user": "www-data",
        }
        result = _generate_survey_fields_from_attributes(attributes)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_generate_survey_fields_empty(self):
        """Test generation with empty attributes."""
        from souschef.deployment import _generate_survey_fields_from_attributes

        result = _generate_survey_fields_from_attributes({})
        assert isinstance(result, list)
        assert len(result) == 0


class TestDetectDeploymentPatterns:
    """Test deployment pattern detection."""

    def test_detect_patterns_from_content_blue_green(self):
        """Test detecting blue-green deployment pattern."""
        from souschef.deployment import _detect_patterns_from_content

        content = """
        # Blue environment deployment
        service 'app-blue' do
          action :start
        end
        # Green environment deployment
        service 'app-green' do
          action :start
        end
        """
        result = _detect_patterns_from_content(content)

        assert isinstance(result, list)
        # May detect patterns (0 or more)

    def test_detect_patterns_from_content_canary(self):
        """Test detecting canary deployment pattern."""
        from souschef.deployment import _detect_patterns_from_content

        content = """
        # Canary deployment
        percentage = 20
        if percentage < 100
          # Deploy to subset
        end
        """
        result = _detect_patterns_from_content(content)

        assert isinstance(result, list)

    def test_detect_patterns_from_content_empty(self):
        """Test pattern detection with empty content."""
        from souschef.deployment import _detect_patterns_from_content

        result = _detect_patterns_from_content("")
        assert isinstance(result, list)


class TestExtractDeploymentSteps:
    """Test deployment step extraction."""

    def test_extract_deployment_steps_basic(self):
        """Test extracting deployment steps from content."""
        from souschef.deployment import _extract_deployment_steps

        content = """
        # Step 1: Deploy application
        # Step 2: Run migrations
        # Step 3: Restart services
        """
        result = _extract_deployment_steps(content)

        assert isinstance(result, list)

    def test_extract_deployment_steps_empty(self):
        """Test extraction with no steps."""
        from souschef.deployment import _extract_deployment_steps

        result = _extract_deployment_steps("")
        assert isinstance(result, list)


class TestExtractHealthChecks:
    """Test health check extraction."""

    def test_extract_health_checks_basic(self):
        """Test extracting health checks from recipe content."""
        from souschef.deployment import _extract_health_checks

        content = """
        http_request 'health-check' do
          url 'http://localhost:8080/health'
        end
        """
        result = _extract_health_checks(content)

        assert isinstance(result, list)

    def test_extract_health_checks_empty(self):
        """Test extraction with no health checks."""
        from souschef.deployment import _extract_health_checks

        result = _extract_health_checks("")
        assert isinstance(result, list)


class TestExtractServiceManagement:
    """Test service management extraction."""

    def test_extract_service_management_basic(self):
        """Test extracting service management from content."""
        from souschef.deployment import _extract_service_management

        content = """
        service 'apache2' do
          action [:enable, :start]
        end
        service 'mysql' do
          action :restart
        end
        """
        result = _extract_service_management(content)

        assert isinstance(result, list)

    def test_extract_service_management_empty(self):
        """Test extraction with no services."""
        from souschef.deployment import _extract_service_management

        result = _extract_service_management("")
        assert isinstance(result, list)


class TestAssessComplexity:
    """Test complexity assessment from resource count."""

    def test_assess_complexity_low(self):
        """Test complexity assessment for low resource count."""
        from souschef.core.metrics import ComplexityLevel
        from souschef.deployment import _assess_complexity_from_resource_count

        complexity, effort, risk = _assess_complexity_from_resource_count(5)
        assert complexity == ComplexityLevel.LOW
        assert isinstance(effort, str)
        assert risk == "low"

    def test_assess_complexity_medium(self):
        """Test complexity assessment for medium resource count."""
        from souschef.core.metrics import ComplexityLevel
        from souschef.deployment import _assess_complexity_from_resource_count

        complexity, effort, risk = _assess_complexity_from_resource_count(25)
        assert complexity == ComplexityLevel.MEDIUM
        assert isinstance(effort, str)
        assert risk == "medium"

    def test_assess_complexity_high(self):
        """Test complexity assessment for high resource count."""
        from souschef.core.metrics import ComplexityLevel
        from souschef.deployment import _assess_complexity_from_resource_count

        complexity, effort, risk = _assess_complexity_from_resource_count(60)
        assert complexity == ComplexityLevel.HIGH
        assert isinstance(effort, str)
        assert risk == "high"


class TestFormatCanaryWorkflow:
    """Test canary workflow formatting."""

    def test_format_canary_workflow_basic(self):
        """Test formatting canary workflow steps."""
        from souschef.deployment import _format_canary_workflow

        steps = [
            {"percentage": 10, "duration": 300},
            {"percentage": 50, "duration": 600},
        ]
        result = _format_canary_workflow(steps)

        assert isinstance(result, str)
        assert "10" in result
        assert "50" in result


class TestExtractDetectedPatterns:
    """Test extracting detected patterns from analysis."""

    def test_extract_detected_patterns_basic(self):
        """Test extracting patterns from analysis dict."""
        from souschef.deployment import _extract_detected_patterns

        patterns = {
            "patterns": ["blue-green", "canary"],
            "other_data": "ignored",
        }
        result = _extract_detected_patterns(patterns)

        assert isinstance(result, list)

    def test_extract_detected_patterns_empty(self):
        """Test extraction with empty patterns."""
        from souschef.deployment import _extract_detected_patterns

        result = _extract_detected_patterns({})
        assert isinstance(result, list)


class TestGenerateAWXJobTemplate:
    """Test AWX job template generation."""

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_generate_awx_job_template_basic(self, mock_validate, tmp_path):
        """Test generating AWX job template from cookbook."""
        from souschef.deployment import generate_awx_job_template_from_cookbook

        cookbook_dir = tmp_path / "test_cookbook"
        cookbook_dir.mkdir()
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        mock_validate.return_value = cookbook_dir

        result = generate_awx_job_template_from_cookbook(
            cookbook_path="/fake/path",
            cookbook_name="test_cookbook",
        )

        assert "AWX/AAP Job Template" in result
        assert "test_cookbook" in result

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_generate_awx_job_template_nonexistent(self, mock_validate):
        """Test job template generation with nonexistent cookbook."""
        # Mock validation failure
        from souschef.core.errors import ChefFileNotFoundError
        from souschef.deployment import generate_awx_job_template_from_cookbook

        mock_validate.side_effect = ChefFileNotFoundError("/nonexistent", "cookbook")

        result = generate_awx_job_template_from_cookbook(
            cookbook_path="/nonexistent",
            cookbook_name="test",
        )

        assert "could not find" in result.lower()


class TestGenerateAWXProject:
    """Test AWX project generation."""

    @patch("souschef.deployment._analyse_cookbooks_directory")
    @patch("souschef.deployment.validate_directory_exists")
    def test_generate_awx_project_basic(self, mock_validate, mock_analyse):
        """Test generating AWX project from cookbooks."""
        from pathlib import Path

        from souschef.deployment import generate_awx_project_from_cookbooks

        # Mock validated directory and analysis with expected structure
        mock_validate.return_value = Path("/fake/path")
        mock_analyse.return_value = {
            "total_cookbooks": 1,
            "cookbooks": {},
            "total_recipes": 0,
            "total_templates": 0,
            "total_files": 0,
        }

        result = generate_awx_project_from_cookbooks(
            cookbooks_directory="/fake/path",
            project_name="test-project",
        )

        assert "AWX/AAP Project" in result
        assert "test-project" in result

    @patch("souschef.deployment.validate_directory_exists")
    def test_generate_awx_project_nonexistent_path(self, mock_validate):
        """Test project generation with nonexistent path."""
        # Mock validation failure
        from souschef.core.errors import ValidationError
        from souschef.deployment import generate_awx_project_from_cookbooks

        mock_validate.side_effect = ValidationError(
            "Directory", ["Directory not found"]
        )

        result = generate_awx_project_from_cookbooks(
            cookbooks_directory="/nonexistent",
            project_name="test-project",
        )

        assert "not found" in result.lower()


class TestGenerateAWXInventorySource:
    """Test AWX inventory source generation."""

    def test_generate_awx_inventory_source_basic(self):
        """Test generating AWX inventory source from Chef."""
        from souschef.deployment import generate_awx_inventory_source_from_chef

        result = generate_awx_inventory_source_from_chef(
            chef_server_url="https://chef.example.com",
            sync_schedule="0 */4 * * *",
        )

        assert "AWX Inventory Source" in result or "Inventory" in result
        assert "chef.example.com" in result

    def test_generate_chef_inventory_source_structure(self):
        """Test internal inventory source structure generation."""
        from souschef.deployment import _generate_chef_inventory_source

        result = _generate_chef_inventory_source(
            chef_server_url="https://chef.example.com",
            sync_schedule="0 */4 * * *",
        )

        assert isinstance(result, dict)
        assert "name" in result
        assert "source" in result

    def test_generate_chef_inventory_script_basic(self):
        """Test Chef inventory script generation."""
        from souschef.deployment import _generate_chef_inventory_script

        result = _generate_chef_inventory_script(
            chef_server_url="https://chef.example.com",
        )

        assert isinstance(result, str)
        assert "chef.example.com" in result
        assert "#!/usr/bin/env python" in result or "#!" in result

    def test_generate_awx_inventory_source_rejects_private_url(self):
        """Test inventory source rejects private or insecure URLs."""
        from souschef.deployment import generate_awx_inventory_source_from_chef

        result = generate_awx_inventory_source_from_chef(
            chef_server_url="http://localhost:8000",
        )

        assert "Invalid Chef server URL" in result


class TestGenerateAWXWorkflow:
    """Test AWX workflow generation."""

    def test_generate_awx_workflow_basic(self):
        """Test generating AWX workflow from Chef runlist."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        result = generate_awx_workflow_from_chef_runlist(
            runlist_content="recipe[apache2::default]",
            workflow_name="test-workflow",
        )

        assert "AWX/AAP Workflow" in result
        assert "test-workflow" in result

    def test_generate_awx_workflow_empty_runlist(self):
        """Test workflow generation with empty runlist."""
        from souschef.deployment import generate_awx_workflow_from_chef_runlist

        result = generate_awx_workflow_from_chef_runlist(
            runlist_content="",
            workflow_name="test-workflow",
        )

        assert "Error" in result
        assert "cannot be empty" in result


class TestAnalyseChefApplicationPatterns:
    """Test Chef application pattern analysis."""

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_analyse_chef_application_patterns_basic(self, mock_validate, tmp_path):
        """Test analysing Chef application patterns."""
        from souschef.deployment import analyse_chef_application_patterns

        cookbook_dir = tmp_path / "test_cookbook"
        cookbook_dir.mkdir()
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        mock_validate.return_value = cookbook_dir

        result = analyse_chef_application_patterns(
            cookbook_path="/fake/path",
        )

        assert "Chef Application Patterns Analysis" in result
        assert "test_cookbook" in result

    @patch("souschef.deployment.validate_cookbook_structure")
    def test_analyse_chef_application_patterns_nonexistent(self, mock_validate):
        """Test pattern analysis with nonexistent cookbook."""
        # Mock validation failure
        from souschef.core.errors import ChefFileNotFoundError
        from souschef.deployment import analyse_chef_application_patterns

        mock_validate.side_effect = ChefFileNotFoundError("/nonexistent", "cookbook")

        result = analyse_chef_application_patterns(
            cookbook_path="/nonexistent",
        )

        assert "could not find" in result.lower()
