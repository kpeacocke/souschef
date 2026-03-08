"""Tests for orchestration layer."""

from unittest.mock import MagicMock, patch

from souschef.orchestration import (
    orchestrate_conversion_analysis,
    orchestrate_cookbook_metadata_parsing,
    orchestrate_get_blob_storage,
    orchestrate_get_storage_manager,
    orchestrate_playbook_generation,
    orchestrate_repository_generation,
    orchestrate_requirements_parsing,
    orchestrate_template_conversion,
)


class TestPlaybookGeneration:
    """Test playbook generation orchestration."""

    @patch("souschef.orchestration.generate_playbook_from_recipe")
    def test_orchestrate_playbook_generation_without_ai(
        self, mock_generate: MagicMock
    ) -> None:
        """Test playbook generation without AI."""
        mock_generate.return_value = "---\n- name: Test playbook\n  hosts: all"

        result = orchestrate_playbook_generation(
            cookbook_path="/path/to/cookbook",
            recipe_name="default",
            use_ai=False,
        )

        assert result == "---\n- name: Test playbook\n  hosts: all"
        mock_generate.assert_called_once_with(
            recipe_path="/path/to/cookbook/recipes/default.rb",
            cookbook_path="/path/to/cookbook",
        )

    @patch("souschef.orchestration.generate_playbook_from_recipe_with_ai")
    def test_orchestrate_playbook_generation_with_ai(
        self, mock_generate_ai: MagicMock
    ) -> None:
        """Test playbook generation with AI (covers lines 63-70)."""
        mock_generate_ai.return_value = (
            "---\n- name: AI-generated playbook\n  hosts: all"
        )

        result = orchestrate_playbook_generation(
            cookbook_path="/path/to/cookbook",
            recipe_name="default",
            use_ai=True,
            ai_provider="anthropic",
            ai_model="claude-3-sonnet",
        )

        assert result == "---\n- name: AI-generated playbook\n  hosts: all"
        mock_generate_ai.assert_called_once_with(
            recipe_path="/path/to/cookbook/recipes/default.rb",
            ai_provider="anthropic",
            model="claude-3-sonnet",
            cookbook_path="/path/to/cookbook",
        )


class TestTemplateConversion:
    """Test template conversion orchestration."""

    @patch("souschef.orchestration.convert_cookbook_templates")
    def test_orchestrate_template_conversion(self, mock_convert: MagicMock) -> None:
        """Test template conversion (covers line 91)."""
        mock_convert.return_value = "Converted 3 templates"

        result = orchestrate_template_conversion(cookbook_path="/path/to/cookbook")

        assert result == "Converted 3 templates"
        mock_convert.assert_called_once_with("/path/to/cookbook")


class TestRepositoryGeneration:
    """Test repository generation orchestration."""

    @patch("souschef.orchestration.generate_ansible_repository")
    def test_orchestrate_repository_generation(self, mock_generate: MagicMock) -> None:
        """Test repository generation (covers line 185, 206)."""
        mock_generate.return_value = {
            "status": "success",
            "path": "/path/to/repo",
            "files_created": 10,
        }

        result = orchestrate_repository_generation(
            output_path="/path/to/repo",
            repo_type="standard",
            org_name="testorg",
            init_git=True,
        )

        assert result == {
            "status": "success",
            "path": "/path/to/repo",
            "files_created": 10,
        }
        mock_generate.assert_called_once_with(
            output_path="/path/to/repo",
            repo_type="standard",
            org_name="testorg",
            init_git=True,
        )


class TestConversionAnalysis:
    """Test conversion analysis orchestration."""

    @patch("souschef.orchestration.analyse_conversion_output")
    def test_orchestrate_conversion_analysis_with_cookbook_path(
        self, mock_analyse: MagicMock
    ) -> None:
        """Test conversion analysis with cookbook_path (covers line 206)."""
        mock_analyse.return_value = {"recommendation": "standard", "confidence": 0.95}

        result = orchestrate_conversion_analysis(
            cookbook_path="/path/to/cookbook",
            num_recipes=5,
            num_roles=2,
            has_multiple_apps=False,
            needs_multi_env=True,
        )

        assert result == {"recommendation": "standard", "confidence": 0.95}
        mock_analyse.assert_called_once_with(
            cookbook_path="/path/to/cookbook",
            num_recipes=5,
            num_roles=2,
            has_multiple_apps=False,
            needs_multi_env=True,
            ai_provider="",
            api_key="",
            model="",
        )

    @patch("souschef.orchestration.analyse_conversion_output")
    def test_orchestrate_conversion_analysis_with_output_path_fallback(
        self, mock_analyse: MagicMock
    ) -> None:
        """Test conversion analysis falls back to output_path."""
        mock_analyse.return_value = {"recommendation": "collection"}

        result = orchestrate_conversion_analysis(
            output_path="/path/to/output",
            num_recipes=10,
            num_roles=5,
            has_multiple_apps=True,
            needs_multi_env=True,
        )

        assert result == {"recommendation": "collection"}
        # Should use output_path when cookbook_path is empty
        mock_analyse.assert_called_once_with(
            cookbook_path="/path/to/output",
            num_recipes=10,
            num_roles=5,
            has_multiple_apps=True,
            needs_multi_env=True,
            ai_provider="",
            api_key="",
            model="",
        )

    @patch("souschef.orchestration.analyse_conversion_output")
    def test_orchestrate_conversion_analysis_with_ai(
        self, mock_analyse: MagicMock
    ) -> None:
        """Test conversion analysis with AI parameters."""
        mock_analyse.return_value = {
            "recommendation": "monorepo",
            "reasoning": "AI analysis",
        }

        result = orchestrate_conversion_analysis(
            cookbook_path="/path/to/cookbook",
            num_recipes=20,
            num_roles=10,
            has_multiple_apps=True,
            needs_multi_env=True,
            ai_provider="openai",
            api_key="sk-test",
            model="gpt-4",
        )

        assert result == {"recommendation": "monorepo", "reasoning": "AI analysis"}
        mock_analyse.assert_called_once_with(
            cookbook_path="/path/to/cookbook",
            num_recipes=20,
            num_roles=10,
            has_multiple_apps=True,
            needs_multi_env=True,
            ai_provider="openai",
            api_key="sk-test",
            model="gpt-4",
        )


class TestCookbookMetadataParsing:
    """Test cookbook metadata parsing orchestration."""

    @patch("souschef.orchestration.parse_cookbook_metadata")
    def test_orchestrate_cookbook_metadata_parsing(self, mock_parse: MagicMock) -> None:
        """Test cookbook metadata parsing."""
        mock_parse.return_value = "name: test-cookbook\nversion: 1.0.0"

        result = orchestrate_cookbook_metadata_parsing(
            cookbook_path="/path/to/cookbook"
        )

        assert result == "name: test-cookbook\nversion: 1.0.0"
        mock_parse.assert_called_once_with(path="/path/to/cookbook")


class TestRequirementsParsing:
    """Test requirements parsing orchestration."""

    @patch("souschef.orchestration.parse_requirements_yml")
    def test_orchestrate_requirements_parsing(self, mock_parse: MagicMock) -> None:
        """Test requirements parsing."""
        mock_parse.return_value = {
            "collections": [{"name": "ansible.posix", "version": "1.5.4"}]
        }

        result = orchestrate_requirements_parsing(
            requirements_file="/path/to/requirements.yml"
        )

        assert result == {
            "collections": [{"name": "ansible.posix", "version": "1.5.4"}]
        }
        mock_parse.assert_called_once_with(
            requirements_path="/path/to/requirements.yml"
        )


class TestStorageOrchestration:
    """Test storage orchestration."""

    @patch("souschef.orchestration.get_storage_manager")
    def test_orchestrate_get_storage_manager(self, mock_get: MagicMock) -> None:
        """Test get storage manager."""
        mock_manager = MagicMock()
        mock_get.return_value = mock_manager

        result = orchestrate_get_storage_manager()

        assert result == mock_manager
        mock_get.assert_called_once_with()

    @patch("souschef.orchestration.get_blob_storage")
    def test_orchestrate_get_blob_storage(self, mock_get: MagicMock) -> None:
        """Test get blob storage (covers line 239)."""
        mock_blob = MagicMock()
        mock_get.return_value = mock_blob

        result = orchestrate_get_blob_storage()

        assert result == mock_blob
        mock_get.assert_called_once_with()
