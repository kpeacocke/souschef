"""
Comprehensive tests for workflow helper functions and utilities.

Tests AI conversion workflows, string parsing helpers, simulation configs,
and assessment analysis functions that drive the core conversion logic.
"""

import json
from unittest.mock import MagicMock, Mock, patch

from souschef.converters.playbook import (
    _clean_ai_playbook_response,
    _create_ai_conversion_prompt,
    _handle_quote_transition,
    _initialize_ai_client,
    _is_quote_char,
    _should_split_at_comma,
    _update_nesting_depths,
    _validate_and_fix_playbook,
)
from souschef.server import (
    configure_migration_simulation,
    get_version_combination_info,
    list_migration_version_combinations,
)


class TestAIClientInitialization:
    """Test AI client initialization for different providers."""

    def test_initialize_anthropic_client(self):
        """Test Anthropic client initialization."""
        import sys

        mock_client = MagicMock()
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            result = _initialize_ai_client("anthropic", "test-key")

            assert result == mock_client
            mock_anthropic.Anthropic.assert_called_once_with(api_key="test-key")

    def test_initialize_openai_client(self):
        """Test OpenAI client initialization."""
        import sys

        mock_client = MagicMock()
        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict(sys.modules, {"openai": mock_openai}):
            result = _initialize_ai_client("openai", "test-key")

            assert result == mock_client
            mock_openai.OpenAI.assert_called_once_with(api_key="test-key")

    def test_initialize_watson_client_success(self):
        """Test Watson client initialization with valid URL."""
        with (
            patch("souschef.converters.playbook.APIClient") as mock_api_client,
            patch(
                "souschef.converters.playbook.validate_user_provided_url"
            ) as mock_validate,
        ):
            mock_client = MagicMock()
            mock_api_client.return_value = mock_client
            mock_validate.return_value = "https://validated-url.com"

            result = _initialize_ai_client(
                "watson", "test-key", project_id="proj-123", base_url="https://test.com"
            )

            assert result == mock_client
            mock_api_client.assert_called_once_with(
                api_key="test-key",
                project_id="proj-123",
                url="https://validated-url.com",
            )

    def test_initialize_watson_client_invalid_url(self):
        """Test Watson client initialization with invalid URL."""
        with (
            patch("souschef.converters.playbook.APIClient", MagicMock()),
            patch(
                "souschef.converters.playbook.validate_user_provided_url",
                side_effect=ValueError("Invalid URL"),
            ),
        ):
            result = _initialize_ai_client(
                "watson", "test-key", base_url="invalid://url"
            )

            assert "Error" in result
            assert "Invalid Watsonx base URL" in result

    def test_initialize_watson_client_unavailable(self):
        """Test Watson client when library unavailable."""
        with patch("souschef.converters.playbook.APIClient", None):
            result = _initialize_ai_client("watson", "test-key")

            assert "Error" in result
            assert "ibm_watsonx_ai library not available" in result

    def test_initialize_lightspeed_client_success(self):
        """Test Lightspeed client initialization."""
        with (
            patch("souschef.converters.playbook.requests", MagicMock()),
            patch(
                "souschef.converters.playbook.validate_user_provided_url",
                return_value="https://validated.com",
            ),
        ):
            result = _initialize_ai_client(
                "lightspeed", "test-key", base_url="https://api.redhat.com"
            )

            assert isinstance(result, dict)
            assert result["api_key"] == "test-key"
            assert result["base_url"] == "https://validated.com"

    def test_initialize_lightspeed_client_invalid_url(self):
        """Test Lightspeed client with invalid URL."""
        with (
            patch("souschef.converters.playbook.requests", MagicMock()),
            patch(
                "souschef.converters.playbook.validate_user_provided_url",
                side_effect=ValueError("Invalid URL"),
            ),
        ):
            result = _initialize_ai_client(
                "lightspeed", "test-key", base_url="bad://url"
            )

            assert "Error" in result
            assert "Invalid Lightspeed base URL" in result

    def test_initialize_lightspeed_requests_unavailable(self):
        """Test Lightspeed when requests library unavailable."""
        with patch("souschef.converters.playbook.requests", None):
            result = _initialize_ai_client("lightspeed", "test-key")

            assert "Error" in result
            assert "requests library not available" in result

    def test_initialize_github_copilot_client(self):
        """Test GitHub Copilot returns unsupported message."""
        result = _initialize_ai_client("github_copilot", "test-key")

        assert "Error" in result
        assert "GitHub Copilot does not have a public REST API" in result
        assert "IDE integrations" in result

    def test_initialize_unsupported_provider(self):
        """Test initialization with unsupported provider."""
        result = _initialize_ai_client("unknown_provider", "test-key")

        assert "Error" in result
        assert "Unsupported AI provider" in result


class TestAIConversionPromptCreation:
    """Test AI conversion prompt building."""

    def test_create_basic_prompt_without_recommendations(self):
        """Test basic prompt creation without project recommendations."""
        raw_content = "package 'nginx' do\n  action :install\nend"
        parsed_content = "Resource 1: package\nName: nginx"
        recipe_name = "default.rb"

        result = _create_ai_conversion_prompt(
            raw_content, parsed_content, recipe_name, project_recommendations=None
        )

        assert "You are an expert at converting Chef recipes" in result
        assert raw_content in result
        assert parsed_content in result
        assert recipe_name in result
        assert "CHEF RECIPE CONTENT:" in result
        assert "PARSED RECIPE ANALYSIS:" in result

    def test_create_prompt_with_project_recommendations(self):
        """Test prompt creation with project recommendations."""
        raw_content = "service 'nginx' do\n  action :start\nend"
        parsed_content = "Resource 1: service"
        recipe_name = "webserver.rb"
        recommendations = {
            "project_complexity": "High",
            "migration_strategy": "Phased",
            "project_effort_days": 45.5,
            "dependency_density": 0.75,
            "recommendations": [
                "Start with core infrastructure",
                "Test database migrations first",
                "Use staging environment",
            ],
        }

        result = _create_ai_conversion_prompt(
            raw_content,
            parsed_content,
            recipe_name,
            project_recommendations=recommendations,
        )

        assert "PROJECT CONTEXT:" in result
        assert "High" in result
        assert "Phased" in result
        assert "45.5" in result
        assert "0.75" in result
        assert "Start with core infrastructure" in result
        assert "Test database migrations first" in result

    def test_create_prompt_limits_recommendations(self):
        """Test that prompt limits recommendations to first 5."""
        recommendations = {
            "project_complexity": "Medium",
            "migration_strategy": "Big-bang",
            "project_effort_days": 20.0,
            "dependency_density": 0.5,
            "recommendations": [f"Recommendation {i}" for i in range(10)],
        }

        result = _create_ai_conversion_prompt(
            "content", "parsed", "test.rb", project_recommendations=recommendations
        )

        # Should contain first 5 recommendations
        for i in range(5):
            assert f"Recommendation {i}" in result

        # Should NOT contain recommendations 5-9
        for i in range(5, 10):
            assert f"Recommendation {i}" not in result

    def test_create_prompt_handles_empty_recommendations_list(self):
        """Test prompt with empty recommendations list."""
        recommendations = {
            "project_complexity": "Low",
            "migration_strategy": "Parallel",
            "project_effort_days": 10.0,
            "dependency_density": 0.2,
            "recommendations": [],
        }

        result = _create_ai_conversion_prompt(
            "content", "parsed", "test.rb", project_recommendations=recommendations
        )

        assert "PROJECT CONTEXT:" in result
        assert "Low" in result
        # Should not crash with empty recommendations


class TestPlaybookResponseCleaning:
    """Test AI playbook response cleaning."""

    def test_clean_valid_yaml_response(self):
        """Test cleaning valid YAML response."""
        ai_response = """---
- name: Install nginx
  package:
    name: nginx
    state: present"""

        result = _clean_ai_playbook_response(ai_response)

        assert result == ai_response

    def test_clean_response_with_markdown_codeblocks(self):
        """Test cleaning response with markdown code blocks."""
        ai_response = """```yaml
---
- name: Install nginx
  package:
    name: nginx
```"""

        result = _clean_ai_playbook_response(ai_response)

        assert "```" not in result
        assert "---" in result
        assert "Install nginx" in result

    def test_clean_response_without_yaml_marker(self):
        """Test cleaning YAML without --- marker."""
        ai_response = """- name: Configure service
  service:
    name: nginx
    state: started"""

        result = _clean_ai_playbook_response(ai_response)

        assert "Configure service" in result
        assert not result.startswith("Error")

    def test_clean_empty_response(self):
        """Test cleaning empty AI response."""
        result = _clean_ai_playbook_response("")

        assert "Error" in result
        assert "empty response" in result

    def test_clean_whitespace_only_response(self):
        """Test cleaning whitespace-only response."""
        result = _clean_ai_playbook_response("   \n\n  \t  ")

        assert "Error" in result
        assert "empty response" in result

    def test_clean_invalid_non_yaml_response(self):
        """Test cleaning response that doesn't look like YAML."""
        result = _clean_ai_playbook_response(
            "This is just plain text without YAML structure"
        )

        assert "Error" in result
        assert "does not appear to be valid YAML" in result


class TestPlaybookValidationAndFix:
    """Test playbook validation and self-correction."""

    def test_validate_already_valid_playbook(self):
        """Test validation skips fixing for valid playbook."""
        playbook = """---
- name: Test playbook
  hosts: all
  tasks:
    - name: Install package
      package:
        name: nginx"""

        with (
            patch(
                "souschef.converters.playbook._validate_playbook_yaml",
                return_value=None,
            ),
            patch("souschef.converters.playbook._run_ansible_lint", return_value=None),
        ):
            result = _validate_and_fix_playbook(
                playbook, Mock(), "anthropic", "claude-3-opus", 0.5, 2048
            )

            assert result == playbook

    def test_validate_passes_through_error_prefix(self):
        """Test validation passes through existing error messages."""
        error_playbook = "Error: Something went wrong"

        result = _validate_and_fix_playbook(
            error_playbook, Mock(), "openai", "gpt-4", 0.5, 2048
        )

        assert result == error_playbook

    def test_validate_attempts_fix_on_yaml_error(self):
        """Test validation attempts AI fix on YAML parse error."""
        invalid_playbook = "---\n- name: Test\n  bad_yaml: [unclosed"

        with (
            patch(
                "souschef.converters.playbook._validate_playbook_yaml",
                side_effect=[
                    "YAML parse error: unclosed bracket",  # First call - original playbook
                    None,  # Second call - fixed playbook (valid YAML)
                ],
            ),
            patch(
                "souschef.converters.playbook._run_ansible_lint",
                return_value=None,
            ),
            patch(
                "souschef.converters.playbook._call_ai_api",
                return_value="---\n- name: Test\n  hosts: all",
            ),
            patch(
                "souschef.converters.playbook._clean_ai_playbook_response",
                return_value="---\n- name: Test\n  hosts: all",
            ),
        ):
            mock_client = Mock()
            result = _validate_and_fix_playbook(
                invalid_playbook, mock_client, "anthropic", "claude-3-opus", 0.5, 2048
            )

            assert "Test" in result
            assert "hosts: all" in result

    def test_validate_returns_original_on_fix_failure(self):
        """Test validation returns original playbook when fix fails."""
        playbook = "---\n- name: Test"

        with (
            patch(
                "souschef.converters.playbook._validate_playbook_yaml",
                return_value="Some error",
            ),
            patch(
                "souschef.converters.playbook._run_ansible_lint",
                return_value=None,
            ),
            patch(
                "souschef.converters.playbook._call_ai_api",
                side_effect=Exception("API failed"),
            ),
        ):
            result = _validate_and_fix_playbook(
                playbook, Mock(), "openai", "gpt-4", 0.5, 2048
            )

            # Should return original playbook on exception
            assert result == playbook

    def test_validate_handles_cleaned_response_error(self):
        """Test validation when cleaned response still has errors."""
        playbook = "---\n- name: Test"

        with (
            patch(
                "souschef.converters.playbook._validate_playbook_yaml",
                side_effect=[
                    "Initial error",  # First call
                    None,  # Second call (after fix attempt)
                ],
            ),
            patch(
                "souschef.converters.playbook._run_ansible_lint",
                return_value=None,
            ),
            patch(
                "souschef.converters.playbook._call_ai_api",
                return_value="Invalid response",
            ),
            patch(
                "souschef.converters.playbook._clean_ai_playbook_response",
                return_value="Error: Still invalid",
            ),
        ):
            result = _validate_and_fix_playbook(
                playbook, Mock(), "openai", "gpt-4", 0.5, 2048
            )

            # Should return original when fix produces error
            assert result == playbook


class TestStringParsingHelpers:
    """Test string parsing helper functions."""

    def test_is_quote_char_single_quote(self):
        """Test single quote detection."""
        assert _is_quote_char("'") is True

    def test_is_quote_char_double_quote(self):
        """Test double quote detection."""
        assert _is_quote_char('"') is True

    def test_is_quote_char_not_quote(self):
        """Test non-quote character."""
        assert _is_quote_char("a") is False
        assert _is_quote_char("{") is False
        assert _is_quote_char(" ") is False

    def test_handle_quote_transition_enter_single_quote(self):
        """Test entering single-quoted string."""
        in_quotes, quote_char = _handle_quote_transition("'", False, None)
        assert in_quotes is True
        assert quote_char == "'"

    def test_handle_quote_transition_exit_single_quote(self):
        """Test exiting single-quoted string."""
        in_quotes, quote_char = _handle_quote_transition("'", True, "'")
        assert in_quotes is False
        assert quote_char is None

    def test_handle_quote_transition_enter_double_quote(self):
        """Test entering double-quoted string."""
        in_quotes, quote_char = _handle_quote_transition('"', False, None)
        assert in_quotes is True
        assert quote_char == '"'

    def test_handle_quote_transition_wrong_quote_type(self):
        """Test encountering different quote type while in quotes."""
        in_quotes, quote_char = _handle_quote_transition('"', True, "'")
        assert in_quotes is True
        assert quote_char == "'"

    def test_update_nesting_depths_open_brace(self):
        """Test opening brace increases depth."""
        brace, bracket = _update_nesting_depths("{", 0, 0)
        assert brace == 1
        assert bracket == 0

    def test_update_nesting_depths_close_brace(self):
        """Test closing brace decreases depth."""
        brace, bracket = _update_nesting_depths("}", 2, 0)
        assert brace == 1
        assert bracket == 0

    def test_update_nesting_depths_open_bracket(self):
        """Test opening bracket increases depth."""
        brace, bracket = _update_nesting_depths("[", 0, 0)
        assert brace == 0
        assert bracket == 1

    def test_update_nesting_depths_close_bracket(self):
        """Test closing bracket decreases depth."""
        brace, bracket = _update_nesting_depths("]", 0, 3)
        assert brace == 0
        assert bracket == 2

    def test_update_nesting_depths_regular_char(self):
        """Test regular character doesn't change depths."""
        brace, bracket = _update_nesting_depths("a", 2, 3)
        assert brace == 2
        assert bracket == 3

    def test_should_split_at_comma_outside_nesting(self):
        """Test comma outside nesting should split."""
        result = _should_split_at_comma(",", False, 0, 0)
        assert result is True

    def test_should_split_at_comma_inside_quotes(self):
        """Test comma inside quotes should not split."""
        result = _should_split_at_comma(",", True, 0, 0)
        assert result is False

    def test_should_split_at_comma_inside_braces(self):
        """Test comma inside braces should not split."""
        result = _should_split_at_comma(",", False, 1, 0)
        assert result is False

    def test_should_split_at_comma_inside_brackets(self):
        """Test comma inside brackets should not split."""
        result = _should_split_at_comma(",", False, 0, 1)
        assert result is False

    def test_should_split_not_comma(self):
        """Test non-comma character should not split."""
        result = _should_split_at_comma("x", False, 0, 0)
        assert result is False


class TestVersionCombinationsAndSimulation:
    """Test version combination and simulation configuration."""

    def test_get_version_combinations_returns_valid_json(self):
        """Test version combinations returns valid JSON."""
        result = list_migration_version_combinations()

        # Should be valid JSON
        data = json.loads(result)
        assert "combinations" in data
        assert "total" in data
        assert isinstance(data["combinations"], list)
        assert isinstance(data["total"], int)

    def test_get_version_combinations_includes_required_fields(self):
        """Test combinations include all required fields."""
        result = list_migration_version_combinations()
        data = json.loads(result)

        if data["combinations"]:
            combo = data["combinations"][0]
            assert "chef_version" in combo
            assert "target_platform" in combo
            assert "target_version" in combo
            assert "execution_model" in combo
            assert "ansible_version" in combo
            assert "requires_fips" in combo
            assert "requires_signing" in combo

    def test_get_version_combination_info_valid(self):
        """Test version combination info for a valid pairing."""
        result = get_version_combination_info(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
        )

        data = json.loads(result)
        assert "error" not in data
        assert "auth_protocol" in data
        assert "execution_model" in data
        assert "ansible_version" in data
        assert "available_endpoints" in data
        assert "job_template_structure" in data

    def test_get_version_combination_info_invalid(self):
        """Test version combination info for an invalid pairing."""
        result = get_version_combination_info(
            chef_version="99.99.99",
            target_platform="invalid",
            target_version="0.0.1",
        )

        data = json.loads(result)
        assert data.get("valid") is False
        assert "error" in data

    def test_configure_migration_simulation_with_valid_versions(self):
        """Test simulation configuration with valid versions."""
        result = configure_migration_simulation(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            fips_mode="no",
        )

        data = json.loads(result)
        assert data["configured"] is True
        assert data["chef_version"] == "14.15.6"
        assert data["target_platform"] == "awx"
        assert data["target_version"] == "24.6.1"
        assert "auth_protocol" in data
        assert "execution_model" in data
        assert "ansible_version" in data

    def test_configure_migration_simulation_with_fips_enabled(self):
        """Test simulation configuration with FIPS mode enabled."""
        result = configure_migration_simulation(
            chef_version="14.15.6",
            target_platform="aap",
            target_version="2.4.0",
            fips_mode="yes",
        )

        data = json.loads(result)
        assert data["configured"] is True
        assert data["features"]["fips_mode"] is True

    def test_configure_migration_simulation_with_invalid_combination(self):
        """Test simulation configuration with invalid version combination."""
        result = configure_migration_simulation(
            chef_version="99.99.99",
            target_platform="invalid_platform",
            target_version="1.0.0",
            fips_mode="no",
        )

        data = json.loads(result)
        # Should return error for invalid combination
        assert (
            "error" in data
            or "configured" not in data
            or data.get("configured") is False
        )

    def test_configure_migration_simulation_includes_mock_data(self):
        """Test simulation includes mock endpoints and headers."""
        result = configure_migration_simulation(
            chef_version="14.15.6",
            target_platform="awx",
            target_version="24.6.1",
            fips_mode="no",
        )

        data = json.loads(result)
        if data.get("configured"):
            assert "mock_endpoints" in data
            assert "job_template_template" in data
            assert "mock_headers" in data
            assert "simulation_ready" in data

    def test_configure_migration_simulation_fips_variations(self):
        """Test FIPS mode accepts various truthy values."""
        for fips_value in ["yes", "true", "1", "YES", "True"]:
            result = configure_migration_simulation(
                chef_version="14.15.6",
                target_platform="aap",
                target_version="2.4.0",
                fips_mode=fips_value,
            )

            data = json.loads(result)
            if data.get("configured"):
                assert data["features"]["fips_mode"] is True

    def test_configure_migration_simulation_fips_false_variations(self):
        """Test FIPS mode recognizes falsy values."""
        for fips_value in ["no", "false", "0", "NO", "False"]:
            result = configure_migration_simulation(
                chef_version="14.15.6",
                target_platform="awx",
                target_version="24.6.1",
                fips_mode=fips_value,
            )

            data = json.loads(result)
            if data.get("configured"):
                assert data["features"]["fips_mode"] is False
