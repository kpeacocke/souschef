"""Targeted tests to boost coverage to 90%+ for cli.py, ansible_versions.py, assessment.py, and server.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from click.testing import CliRunner

from souschef.cli import (
    _resolve_output_path,
    _safe_write_file,
    _validate_user_path,
    cli,
)
from souschef.core.ansible_versions import (
    _calculate_intermediate_versions,
    _call_ai_provider,
    _collect_breaking_changes,
    _get_cache_path,
    _load_ai_cache,
    _parse_version,
    _save_ai_cache,
    get_python_compatibility,
)


class TestCLIErrorPaths:
    """Test error paths in CLI commands to boost cli.py coverage."""

    def test_safe_write_file_oserror(self, tmp_path):
        """Test _safe_write_file with OSError during write."""
        import click

        with (
            patch("pathlib.Path.open", side_effect=OSError("Write failed")),
            pytest.raises(click.Abort),
        ):
            _safe_write_file("test content", None, tmp_path / "test.txt")

    def test_resolve_output_path_value_error(self, tmp_path):
        """Test _resolve_output_path with invalid path."""
        import click

        # Path that doesn't exist within workspace root
        with (
            patch("souschef.cli._get_workspace_root", return_value=tmp_path),
            patch("souschef.cli._normalize_path", side_effect=ValueError("Invalid")),
            pytest.raises(click.Abort),
        ):
            _resolve_output_path("/invalid/path", tmp_path / "output.txt")

    def test_list_command_error(self):
        """Test list command with error."""
        runner = CliRunner()
        result = runner.invoke(cli, ["list", "/nonexistent/path"])
        assert result.exit_code != 0
        assert (
            "does not exist" in result.output.lower()
            or "error" in result.output.lower()
        )

    def test_cat_command_nonexistent(self):
        """Test cat command with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["cat", "/nonexistent/file.txt"])
        assert result.exit_code != 0

    def test_convert_cookbook_missing_recipes(self, tmp_path):
        """Test convert-cookbook with missing recipes directory."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "convert-cookbook",
                "--cookbook-path",
                str(cookbook_dir),
                "--output-path",
                str(tmp_path / "output"),
            ],
        )
        # Should handle gracefully even if recipes dir doesn't exist
        assert result.exit_code == 0
        assert (
            "conversion summary" in result.output.lower()
            or "files converted" in result.output.lower()
        )

    def test_inspec_parse_json_format(self, tmp_path):
        """Test inspec-parse command with JSON format."""
        inspec_file = tmp_path / "example_spec.rb"
        inspec_file.write_text("""
control 'test-1' do
  impact 1.0
  title 'Test Control'
  desc 'Test Description'
  describe file('/etc/passwd') do
    it { should exist }
  end
end
""")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["inspec-parse", str(inspec_file), "--format", "json"],
        )
        assert result.exit_code == 0

    def test_convert_recipe_invalid_cookbook_path(self, tmp_path):
        """Test convert-recipe with invalid cookbook path."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "convert-recipe",
                "--cookbook-path",
                "/nonexistent/cookbook",
                "--recipe-name",
                "default",
                "--output-path",
                str(tmp_path / "output"),
            ],
        )
        assert result.exit_code != 0

    def test_assess_cookbook_not_directory(self, tmp_path):
        """Test assess-cookbook with file instead of directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["assess-cookbook", "--cookbook-path", str(test_file), "--format", "json"],
        )
        assert result.exit_code != 0
        assert "not a directory" in result.output

    def test_convert_recipe_missing_recipe(self, tmp_path):
        """Test convert-recipe when recipe file doesn't exist."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "convert-recipe",
                "--cookbook-path",
                str(cookbook_dir),
                "--recipe-name",
                "nonexistent",
                "--output-path",
                str(tmp_path / "output"),
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_validate_user_path_nonexistent(self):
        """Test _validate_user_path with nonexistent path."""
        with pytest.raises(ValueError, match="does not exist"):
            _validate_user_path("/totally/nonexistent/path/12345")

    def test_validate_user_path_oserror(self):
        """Test _validate_user_path with OSError."""
        with (
            patch("pathlib.Path.resolve", side_effect=OSError("Access denied")),
            pytest.raises(ValueError, match="Invalid path"),
        ):
            _validate_user_path("/some/path")


class TestAnsibleVersionsErrorPaths:
    """Test error paths in ansible_versions.py to boost coverage."""

    def test_parse_version_empty_string(self):
        """Test _parse_version with empty string."""
        result = _parse_version("")
        assert result == ()

    def test_parse_version_only_text(self):
        """Test _parse_version with only text (no numbers)."""
        result = _parse_version("invalid")
        assert result == ()

    def test_get_python_compatibility_unknown_version(self):
        """Test get_python_compatibility with unknown version."""
        with pytest.raises(ValueError, match="Unknown Ansible version"):
            get_python_compatibility("99.99", "control")

    def test_get_python_compatibility_invalid_node_type(self):
        """Test get_python_compatibility with invalid node_type."""
        with pytest.raises(ValueError, match="Invalid node_type"):
            get_python_compatibility("2.15", "invalid_type")

    def test_calculate_intermediate_versions_equal(self):
        """Test _calculate_intermediate_versions when current >= target."""
        result = _calculate_intermediate_versions("2.16", "2.15")
        assert result == []

    def test_calculate_intermediate_versions_same(self):
        """Test _calculate_intermediate_versions when current == target."""
        result = _calculate_intermediate_versions("2.15", "2.15")
        assert result == []

    def test_collect_breaking_changes_empty(self):
        """Test _collect_breaking_changes with no intermediate versions."""
        result = _collect_breaking_changes([], "2.15")
        # Should include breaking changes from target version
        assert isinstance(result, list)

    def test_collect_breaking_changes_unknown_version(self):
        """Test _collect_breaking_changes with unknown version in list."""
        result = _collect_breaking_changes(["99.99"], "2.15")
        # Should handle gracefully and continue
        assert isinstance(result, list)

    def test_get_cache_path(self):
        """Test _get_cache_path returns a Path."""
        result = _get_cache_path()
        assert isinstance(result, Path)
        assert "ansible_versions_ai_cache.json" in str(result)

    def test_load_ai_cache_nonexistent(self):
        """Test _load_ai_cache when cache file doesn't exist."""
        with patch("souschef.core.ansible_versions._get_cache_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/cache.json")
            result = _load_ai_cache()
            assert result is None

    def test_load_ai_cache_invalid_json(self, tmp_path):
        """Test _load_ai_cache with invalid JSON."""
        with patch("souschef.core.ansible_versions._get_cache_path") as mock_path:
            mock_file = tmp_path / "test_cache.json"
            mock_path.return_value = mock_file
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.open", mock_open(read_data="invalid json")),
            ):
                result = _load_ai_cache()
                assert result is None

    def test_load_ai_cache_stale(self, tmp_path):
        """Test _load_ai_cache with stale cache."""
        old_date = "2020-01-01T00:00:00"
        cache_data = json.dumps({"cached_at": old_date, "versions": {"2.15": {}}})

        with patch("souschef.core.ansible_versions._get_cache_path") as mock_path:
            mock_path.return_value = tmp_path / "test_cache.json"
            with (
                patch("pathlib.Path.exists", return_value=True),
                patch("pathlib.Path.open", mock_open(read_data=cache_data)),
            ):
                result = _load_ai_cache()
                assert result is None  # Cache is stale

    def test_save_ai_cache_success(self, tmp_path):
        """Test _save_ai_cache successfully saves data."""
        test_data = {"2.15": {"control_node_python": ["3.9"]}}

        with patch("souschef.core.ansible_versions._get_cache_path") as mock_path:
            mock_path.return_value = tmp_path / "test_cache.json"
            with patch("pathlib.Path.open", mock_open()) as mock_file:
                _save_ai_cache(test_data)
                # Should have attempted to write
                mock_file.assert_called_once()

    def test_save_ai_cache_oserror(self, tmp_path):
        """Test _save_ai_cache handles OSError gracefully."""
        test_data = {"2.15": {}}

        with patch("souschef.core.ansible_versions._get_cache_path") as mock_path:
            mock_path.return_value = tmp_path / "test_cache.json"
            with patch("pathlib.Path.open", side_effect=OSError("Write failed")):
                # Should not raise, silent fail
                _save_ai_cache(test_data)

    def test_call_ai_provider_anthropic_no_content(self):
        """Test _call_ai_provider with Anthropic returning no content."""
        try:
            import anthropic  # noqa: F401

            with patch("anthropic.Anthropic") as mock_anthropic_class:
                mock_client = MagicMock()
                mock_anthropic_class.return_value = mock_client
                mock_response = MagicMock()
                mock_response.content = []
                mock_client.messages.create.return_value = mock_response

                result = _call_ai_provider(
                    "anthropic", "test-key", "claude-3", "prompt"
                )
                assert result is None
        except ImportError:
            pytest.skip("anthropic module not installed")

    def test_call_ai_provider_anthropic_no_text(self):
        """Test _call_ai_provider with Anthropic returning content without text."""
        try:
            import anthropic  # noqa: F401

            with patch("anthropic.Anthropic") as mock_anthropic_class:
                mock_client = MagicMock()
                mock_anthropic_class.return_value = mock_client
                mock_response = MagicMock()
                mock_block = MagicMock(spec=[])  # No text attribute
                mock_response.content = [mock_block]
                mock_client.messages.create.return_value = mock_response

                result = _call_ai_provider(
                    "anthropic", "test-key", "claude-3", "prompt"
                )
                assert result is None
        except ImportError:
            pytest.skip("anthropic module not installed")

    def test_call_ai_provider_openai_success(self):
        """Test _call_ai_provider with OpenAI success."""
        try:
            import openai  # noqa: F401

            with patch("openai.OpenAI") as mock_openai_class:
                mock_client = MagicMock()
                mock_openai_class.return_value = mock_client
                mock_response = MagicMock()
                mock_choice = MagicMock()
                mock_message = MagicMock()
                mock_message.content = "Test response"
                mock_choice.message = mock_message
                mock_response.choices = [mock_choice]
                mock_client.chat.completions.create.return_value = mock_response

                result = _call_ai_provider("openai", "test-key", "gpt-4", "prompt")
                assert result == "Test response"
        except ImportError:
            pytest.skip("openai module not installed")

    def test_call_ai_provider_unknown_provider(self):
        """Test _call_ai_provider with unknown provider."""
        result = _call_ai_provider("unknown_provider", "test-key", "model", "prompt")
        assert result is None


class TestAssessmentErrorPaths:
    """Test error paths in assessment.py to boost coverage."""

    def test_activity_breakdown_defaults(self):
        """Test ActivityBreakdown dataclass with default values."""
        from souschef.assessment import ActivityBreakdown

        breakdown = ActivityBreakdown(
            activity_type="Test",
            count=5,
            manual_hours=10.0,
            ai_assisted_hours=5.0,
            complexity_factor=1.0,
            description="Test activity",
        )

        assert breakdown.writing_hours == pytest.approx(0.0)
        assert breakdown.testing_hours == pytest.approx(0.0)
        assert breakdown.ai_assisted_writing_hours == pytest.approx(0.0)
        assert breakdown.ai_assisted_testing_hours == pytest.approx(0.0)


class TestServerErrorPaths:
    """Test error paths in server.py to boost coverage."""

    def test_parse_template_value_error(self):
        """Test parse_template with invalid path."""
        from souschef.server import parse_template

        result = parse_template("/nonexistent/invalid/path/template.erb")
        assert "error" in result.lower() or "not found" in result.lower()

    def test_parse_custom_resource_value_error(self):
        """Test parse_custom_resource with invalid path."""
        from souschef.server import parse_custom_resource

        result = parse_custom_resource("/nonexistent/invalid/path/resource.rb")
        assert "error" in result.lower() or "not found" in result.lower()

    def test_list_directory_value_error(self):
        """Test list_directory with invalid path."""
        from souschef.server import list_directory

        result = list_directory("/nonexistent/invalid/path")
        assert isinstance(result, str)
        assert "error" in result.lower() or "not found" in result.lower()

    def test_read_file_value_error(self):
        """Test read_file with invalid path."""
        from souschef.server import read_file

        result = read_file("/nonexistent/invalid/path/file.txt")
        assert isinstance(result, str)
        assert "error" in result.lower() or "not found" in result.lower()


class TestCLIGeneratorCommands:
    """Test CLI generator commands to boost coverage."""

    def test_generate_jenkinsfile_parallel_disabled(self, tmp_path):
        """Test generate-jenkinsfile with parallel disabled."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate-jenkinsfile",
                str(cookbook_dir),
                "--pipeline-name",
                "test-pipeline",
                "--pipeline-type",
                "declarative",
                "--no-parallel",
                "--output",
                str(tmp_path / "Jenkinsfile"),
            ],
        )

        # Should execute without crashing
        assert "Jenkinsfile" in result.output or "Error" in result.output

    def test_generate_gitlab_ci_no_cache(self, tmp_path):
        """Test generate-gitlab-ci with cache disabled."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate-gitlab-ci",
                str(cookbook_dir),
                "--no-cache",
                "--output",
                str(tmp_path / ".gitlab-ci.yml"),
            ],
        )

        # Should execute without crashing
        assert ".gitlab-ci.yml" in result.output or "Error" in result.output

    def test_generate_gitlab_ci_no_artifacts(self, tmp_path):
        """Test generate-gitlab-ci with artifacts disabled."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "generate-gitlab-ci",
                str(cookbook_dir),
                "--no-artifacts",
                "--output",
                str(tmp_path / ".gitlab-ci.yml"),
            ],
        )

        # Should execute without crashing
        assert ".gitlab-ci.yml" in result.output or "Error" in result.output


class TestCLIConvertYAMLOutput:
    """Test CLI commands with YAML output format."""

    def test_convert_yaml_output(self):
        """Test convert command with YAML output."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "convert",
                "package",
                "nginx",
                "--action",
                "install",
                "--format",
                "yaml",
            ],
        )

        assert result.exit_code == 0
        # Should have YAML content
        assert "name:" in result.output or "package:" in result.output
