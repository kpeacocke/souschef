"""Unit tests for souschef/orchestrators/chef.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAnalyseCookbookDependencies:
    """Tests for analyse_cookbook_dependencies."""

    @patch("souschef.orchestrators.chef.assessment")
    def test_delegates_to_assessment(self, mock_assessment: MagicMock) -> None:
        """Test delegation to assessment module."""
        mock_assessment.analyse_cookbook_dependencies.return_value = "deps output"

        from souschef.orchestrators.chef import analyse_cookbook_dependencies

        result = analyse_cookbook_dependencies("/path/to/cookbooks")

        mock_assessment.analyse_cookbook_dependencies.assert_called_once_with(
            "/path/to/cookbooks"
        )
        assert result == "deps output"


class TestAssessSingleCookbookWithAi:
    """Tests for assess_single_cookbook_with_ai."""

    @patch("souschef.orchestrators.chef.assessment")
    def test_delegates_with_defaults(self, mock_assessment: MagicMock) -> None:
        """Test delegation with default AI parameters."""
        expected = {"score": 5}
        mock_assessment.assess_single_cookbook_with_ai.return_value = expected

        from souschef.orchestrators.chef import assess_single_cookbook_with_ai

        result = assess_single_cookbook_with_ai("/path/to/cookbook")

        mock_assessment.assess_single_cookbook_with_ai.assert_called_once_with(
            "/path/to/cookbook",
            ai_provider="anthropic",
            api_key="",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=4000,
            project_id="",
            base_url="",
        )
        assert result == expected

    @patch("souschef.orchestrators.chef.assessment")
    def test_passes_custom_ai_params(self, mock_assessment: MagicMock) -> None:
        """Test that custom AI parameters are forwarded."""
        mock_assessment.assess_single_cookbook_with_ai.return_value = {}

        from souschef.orchestrators.chef import assess_single_cookbook_with_ai

        assess_single_cookbook_with_ai(
            "/path/to/cookbook",
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            project_id="proj1",
            base_url="https://api.example.com",
        )

        mock_assessment.assess_single_cookbook_with_ai.assert_called_once_with(
            "/path/to/cookbook",
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
            project_id="proj1",
            base_url="https://api.example.com",
        )


class TestParseChefMigrationAssessment:
    """Tests for parse_chef_migration_assessment."""

    @patch("souschef.orchestrators.chef.assessment")
    def test_delegates_to_assessment(self, mock_assessment: MagicMock) -> None:
        """Test delegation to assessment module."""
        expected = {"cookbooks": []}
        mock_assessment.parse_chef_migration_assessment.return_value = expected

        from souschef.orchestrators.chef import parse_chef_migration_assessment

        result = parse_chef_migration_assessment("/path/to/cookbooks")

        mock_assessment.parse_chef_migration_assessment.assert_called_once_with(
            "/path/to/cookbooks"
        )
        assert result == expected


class TestCalculateActivityBreakdown:
    """Tests for calculate_activity_breakdown."""

    @patch("souschef.orchestrators.chef.assessment")
    def test_delegates_with_defaults(self, mock_assessment: MagicMock) -> None:
        """Test delegation with default migration_strategy."""
        expected = {"phases": []}
        mock_assessment.calculate_activity_breakdown.return_value = expected

        from souschef.orchestrators.chef import calculate_activity_breakdown

        result = calculate_activity_breakdown("/path/to/cookbook")

        mock_assessment.calculate_activity_breakdown.assert_called_once_with(
            "/path/to/cookbook",
            migration_strategy="phased",
        )
        assert result == expected

    @patch("souschef.orchestrators.chef.assessment")
    def test_passes_custom_strategy(self, mock_assessment: MagicMock) -> None:
        """Test that custom migration_strategy is forwarded."""
        mock_assessment.calculate_activity_breakdown.return_value = {}

        from souschef.orchestrators.chef import calculate_activity_breakdown

        calculate_activity_breakdown("/path/to/cookbook", migration_strategy="big_bang")

        mock_assessment.calculate_activity_breakdown.assert_called_once_with(
            "/path/to/cookbook",
            migration_strategy="big_bang",
        )


class TestOrchestrateGeneratePlaybookFromRecipe:
    """Tests for orchestrate_generate_playbook_from_recipe."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_with_defaults(self, mock_orch: MagicMock) -> None:
        """Test delegation with default cookbook_path."""
        mock_orch.orchestrate_generate_playbook_from_recipe.return_value = "---"

        from souschef.orchestrators.chef import (
            orchestrate_generate_playbook_from_recipe,
        )

        result = orchestrate_generate_playbook_from_recipe("/path/to/recipe.rb")

        mock_orch.orchestrate_generate_playbook_from_recipe.assert_called_once_with(
            recipe_path="/path/to/recipe.rb",
            cookbook_path="",
        )
        assert result == "---"

    @patch("souschef.orchestrators.chef.orchestration")
    def test_passes_cookbook_path(self, mock_orch: MagicMock) -> None:
        """Test that cookbook_path is forwarded."""
        mock_orch.orchestrate_generate_playbook_from_recipe.return_value = "---"

        from souschef.orchestrators.chef import (
            orchestrate_generate_playbook_from_recipe,
        )

        orchestrate_generate_playbook_from_recipe(
            "/path/to/recipe.rb",
            cookbook_path="/path/to/cookbook",
        )

        mock_orch.orchestrate_generate_playbook_from_recipe.assert_called_once_with(
            recipe_path="/path/to/recipe.rb",
            cookbook_path="/path/to/cookbook",
        )


class TestOrchestrateGeneratePlaybookFromRecipeWithAi:
    """Tests for orchestrate_generate_playbook_from_recipe_with_ai."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_with_all_params(self, mock_orch: MagicMock) -> None:
        """Test delegation with all parameters."""
        mock_orch.orchestrate_generate_playbook_from_recipe_with_ai.return_value = "---"

        from souschef.orchestrators.chef import (
            orchestrate_generate_playbook_from_recipe_with_ai,
        )

        result = orchestrate_generate_playbook_from_recipe_with_ai(
            "/path/to/recipe.rb",
            ai_provider="anthropic",
            api_key="sk-key",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=4000,
        )

        mock_orch.orchestrate_generate_playbook_from_recipe_with_ai.assert_called_once_with(
            recipe_path="/path/to/recipe.rb",
            ai_provider="anthropic",
            api_key="sk-key",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
            max_tokens=4000,
            project_id="",
            base_url="",
            project_recommendations=None,
            cookbook_path="",
        )
        assert result == "---"


class TestOrchestrateTemplateConversion:
    """Tests for orchestrate_template_conversion."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_correctly(self, mock_orch: MagicMock) -> None:
        """Test delegation to orchestration module."""
        expected = {"templates": []}
        mock_orch.orchestrate_template_conversion.return_value = expected

        from souschef.orchestrators.chef import orchestrate_template_conversion

        result = orchestrate_template_conversion("/path/to/cookbook")

        mock_orch.orchestrate_template_conversion.assert_called_once_with(
            "/path/to/cookbook"
        )
        assert result == expected


class TestOrchestrateRepositoryGeneration:
    """Tests for orchestrate_repository_generation."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_with_defaults(self, mock_orch: MagicMock) -> None:
        """Test delegation with default parameters."""
        mock_orch.orchestrate_repository_generation.return_value = "/output/path"

        from souschef.orchestrators.chef import orchestrate_repository_generation

        result = orchestrate_repository_generation("/output", repo_type="galaxy")

        mock_orch.orchestrate_repository_generation.assert_called_once_with(
            output_path="/output",
            repo_type="galaxy",
            org_name="myorg",
            init_git=True,
        )
        assert result == "/output/path"


class TestOrchestrateConversionAnalysis:
    """Tests for orchestrate_conversion_analysis."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_with_defaults(self, mock_orch: MagicMock) -> None:
        """Test delegation with default parameters."""
        mock_orch.orchestrate_conversion_analysis.return_value = {"analysis": {}}

        from souschef.orchestrators.chef import orchestrate_conversion_analysis

        result = orchestrate_conversion_analysis()

        mock_orch.orchestrate_conversion_analysis.assert_called_once_with(
            cookbook_path="",
            output_path="",
            num_recipes=0,
            num_roles=0,
            has_multiple_apps=False,
            needs_multi_env=True,
            ai_provider="",
            api_key="",
            model="",
        )
        assert result == {"analysis": {}}

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_with_params(self, mock_orch: MagicMock) -> None:
        """Test delegation with explicit parameters."""
        mock_orch.orchestrate_conversion_analysis.return_value = {}

        from souschef.orchestrators.chef import orchestrate_conversion_analysis

        orchestrate_conversion_analysis(
            cookbook_path="/path",
            output_path="/out",
            num_recipes=3,
            num_roles=2,
            has_multiple_apps=True,
            needs_multi_env=False,
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
        )

        mock_orch.orchestrate_conversion_analysis.assert_called_once_with(
            cookbook_path="/path",
            output_path="/out",
            num_recipes=3,
            num_roles=2,
            has_multiple_apps=True,
            needs_multi_env=False,
            ai_provider="openai",
            api_key="sk-key",
            model="gpt-4",
        )


class TestOrchestrateCookbookMetadataParsing:
    """Tests for orchestrate_cookbook_metadata_parsing."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_correctly(self, mock_orch: MagicMock) -> None:
        """Test delegation to orchestration module."""
        expected: dict[str, str | list[str]] = {
            "name": "my_cookbook",
            "version": "1.0.0",
        }
        mock_orch.orchestrate_cookbook_metadata_parsing.return_value = expected

        from souschef.orchestrators.chef import orchestrate_cookbook_metadata_parsing

        result = orchestrate_cookbook_metadata_parsing("/path/to/cookbook")

        mock_orch.orchestrate_cookbook_metadata_parsing.assert_called_once_with(
            "/path/to/cookbook"
        )
        assert result == expected


class TestOrchestrateGetStorageManager:
    """Tests for orchestrate_get_storage_manager."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_correctly(self, mock_orch: MagicMock) -> None:
        """Test delegation to orchestration module."""
        mock_manager = MagicMock()
        mock_orch.orchestrate_get_storage_manager.return_value = mock_manager

        from souschef.orchestrators.chef import orchestrate_get_storage_manager

        result = orchestrate_get_storage_manager()

        mock_orch.orchestrate_get_storage_manager.assert_called_once_with()
        assert result is mock_manager


class TestOrchestrateGetBlobStorage:
    """Tests for orchestrate_get_blob_storage."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_correctly(self, mock_orch: MagicMock) -> None:
        """Test delegation to orchestration module."""
        mock_blob = MagicMock()
        mock_orch.orchestrate_get_blob_storage.return_value = mock_blob

        from souschef.orchestrators.chef import orchestrate_get_blob_storage

        result = orchestrate_get_blob_storage()

        mock_orch.orchestrate_get_blob_storage.assert_called_once_with()
        assert result is mock_blob


class TestOrchestrateCalculateFileFingerprint:
    """Tests for orchestrate_calculate_file_fingerprint."""

    @patch("souschef.orchestrators.chef.orchestration")
    def test_delegates_correctly(self, mock_orch: MagicMock) -> None:
        """Test delegation to orchestration module."""
        mock_orch.orchestrate_calculate_file_fingerprint.return_value = "abc123"

        from souschef.orchestrators.chef import orchestrate_calculate_file_fingerprint

        file_path = Path("/path/to/file.rb")
        result = orchestrate_calculate_file_fingerprint(file_path)

        mock_orch.orchestrate_calculate_file_fingerprint.assert_called_once_with(
            file_path
        )
        assert result == "abc123"
