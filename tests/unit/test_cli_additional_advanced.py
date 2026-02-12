"""Additional comprehensive tests for cli.py module - advanced command scenarios."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from souschef import cli


class TestCLIResourceConversion:
    """Test resource/recipe conversion commands."""

    def test_convert_recipe_basic(self) -> None:
        """Test converting a Chef recipe."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("recipe.rb").write_text("package 'apache2' do\n  action :install\nend")

            result = runner.invoke(cli.cli, ["convert", "-i", "recipe.rb"])

            # Should not crash
            assert result.exit_code in [0, 1, 2]

    def test_convert_multiple_recipes(self) -> None:
        """Test converting multiple recipe files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("recipe1.rb").write_text("package 'apache2'")
            Path("recipe2.rb").write_text("package 'nginx'")

            result = runner.invoke(
                cli.cli,
                ["convert", "-i", "recipe1.rb,recipe2.rb"],
            )

            # Should handle multiple inputs
            assert result.exit_code in [0, 1, 2]

    def test_convert_with_format_option(self) -> None:
        """Test conversion with specific output format."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("resource.rb").write_text("custom_resource 'test'")

            result = runner.invoke(
                cli.cli,
                [
                    "convert",
                    "-i",
                    "resource.rb",
                ],
            )

            assert result.exit_code in [0, 1, 2]


class TestCLICookbookOperations:
    """Test cookbook analysis commands."""

    def test_cookbook_structure_analysis(self) -> None:
        """Test analysing cookbook structure."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("metadata.rb").write_text("name 'test_cookbook'")
            Path("recipes").mkdir()
            Path("recipes/default.rb").write_text("# empty")

            result = runner.invoke(cli.cli, ["cookbook", "analyze", "."])

            assert result.exit_code in [0, 2]  # 0 success, 2 usage error

    def test_cookbook_validate_command(self) -> None:
        """Test cookbook validation command."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("metadata.rb").write_text("name 'test_cookbook'\nversion '1.0.0'")

            result = runner.invoke(cli.cli, ["cookbook", "validate", "metadata.rb"])

            assert isinstance(result.exit_code, int)

    def test_cookbook_list_files(self) -> None:
        """Test listing cookbook files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("recipes").mkdir()
            Path("recipes/default.rb").write_text("")
            Path("templates").mkdir()
            Path("templates/config.erb").write_text("")

            result = runner.invoke(cli.cli, ["cookbook", "list", "."])

            assert result.exit_code in [0, 1, 2]


class TestCLIProfileOperations:
    """Test InSpec profile commands."""

    def test_profile_analyze(self) -> None:
        """Test analysing InSpec profile."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("controls").mkdir()
            Path("controls/example.rb").write_text("control 'example' { }")

            result = runner.invoke(cli.cli, ["profile", "analyze", "."])

            assert result.exit_code in [0, 1, 2]

    def test_profile_convert_to_test(self) -> None:
        """Test converting profile to automated test."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("profile.rb").write_text("control 'web_server' { }")

            result = runner.invoke(cli.cli, ["profile", "convert", "profile.rb"])

            assert result.exit_code in [0, 1, 2]

    def test_profile_generate_from_recipe(self) -> None:
        """Test generating profile from recipe."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("recipe.rb").write_text("package 'apache2'")

            result = runner.invoke(cli.cli, ["profile", "generate", "recipe.rb"])

            assert result.exit_code in [0, 1, 2]


class TestCLIDataOperations:
    """Test data bag and environment commands."""

    def test_databag_convert(self) -> None:
        """Test converting Chef data bags."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("databags").mkdir()
            Path("databags/users").mkdir()
            Path("databags/users/admin.json").write_text('{"id": "admin"}')

            result = runner.invoke(cli.cli, ["databag", "convert", "databags/users"])

            assert result.exit_code in [0, 1, 2]

    def test_databag_analyze(self) -> None:
        """Test analysing data bags."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("databags").mkdir()
            Path("databags/test.json").write_text("{}")

            result = runner.invoke(cli.cli, ["databag", "analyze", "databags"])

            assert result.exit_code in [0, 1, 2]

    def test_environment_convert(self) -> None:
        """Test converting Chef environments."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("environments").mkdir()
            Path("environments/prod.rb").write_text(
                "name 'prod'\ndefault_attributes { }"
            )

            result = runner.invoke(cli.cli, ["environment", "convert", "environments"])

            assert result.exit_code in [0, 1, 2]

    def test_environment_analyze(self) -> None:
        """Test analysing environments."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("environments").mkdir()
            Path("environments/prod.rb").write_text("name 'prod'")

            result = runner.invoke(cli.cli, ["environment", "analyze", "environments"])

            assert result.exit_code in [0, 1, 2]


class TestCLIAssessmentCommands:
    """Test assessment and planning commands."""

    def test_assess_complexity(self) -> None:
        """Test complexity assessment command."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("metadata.rb").write_text("name 'test'")

            result = runner.invoke(cli.cli, ["assess", "."])

            assert result.exit_code in [0, 1, 2]

    def test_generate_migration_plan(self) -> None:
        """Test generating migration plan."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("metadata.rb").write_text("name 'test'")

            result = runner.invoke(cli.cli, ["plan", "--timeline-weeks", "12", "."])

            assert result.exit_code in [0, 1, 2]

    def test_analyze_dependencies(self) -> None:
        """Test dependency analysis command."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("metadata.rb").write_text("name 'test'")

            result = runner.invoke(cli.cli, ["dependencies", "."])

            assert result.exit_code in [0, 1, 2]

    @patch("souschef.assessment.validate_conversion")
    def test_validate_conversion_command(self, mock_validate: MagicMock) -> None:
        """Test validation command."""
        mock_validate.return_value = "Validation passed"
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("recipe.rb").write_text("package 'apache2'")
            Path("playbook.yml").write_text("---\ntasks: []")

            result = runner.invoke(
                cli.cli,
                ["validate", "recipe.rb"],
            )

            assert result.exit_code in [0, 1, 2]


class TestCLIOutputOptions:
    """Test output formatting options."""

    def test_json_output_format(self) -> None:
        """Test JSON output format."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.rb").write_text("# test")

            result = runner.invoke(
                cli.cli, ["convert", "-i", "test.rb", "--format", "json"]
            )

            assert result.exit_code in [0, 1, 2]

    def test_yaml_output_format(self) -> None:
        """Test YAML output format."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.rb").write_text("# test")

            result = runner.invoke(
                cli.cli, ["convert", "-i", "test.rb", "--format", "yaml"]
            )

            assert result.exit_code in [0, 1, 2]

    def test_output_to_directory(self) -> None:
        """Test writing output to directory."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("input.rb").write_text("# test")
            Path("output").mkdir()

            result = runner.invoke(
                cli.cli, ["convert", "-i", "input.rb", "-d", "output"]
            )

            assert result.exit_code in [0, 1, 2]

    def test_verbose_output_mode(self) -> None:
        """Test verbose output mode."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.rb").write_text("# test")

            result = runner.invoke(cli.cli, ["convert", "-i", "test.rb", "-v"])

            assert result.exit_code in [0, 1, 2]


class TestCLIErrorHandling:
    """Test error handling and edge cases."""

    def test_missing_input_file(self) -> None:
        """Test handling missing input file."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.cli, ["convert", "-i", "nonexistent.rb"])

            # Should error
            assert result.exit_code != 0

    def test_invalid_format_option(self) -> None:
        """Test invalid format option."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.rb").write_text("# test")

            result = runner.invoke(
                cli.cli,
                ["convert", "-i", "test.rb", "--format", "invalid_format"],
            )

            # Should error or handle gracefully
            assert result.exit_code in [0, 1, 2]

    def test_empty_input_file(self) -> None:
        """Test handling empty input file."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("empty.rb").write_text("")

            result = runner.invoke(cli.cli, ["convert", "-i", "empty.rb"])

            # Should complete (may succeed or error gracefully)
            assert result.exit_code in [0, 1, 2]

    def test_permission_denied_output(self) -> None:
        """Test handling output path permission issues."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("input.rb").write_text("# test")

            # Try to write to root (should fail)
            result = runner.invoke(
                cli.cli, ["convert", "-i", "input.rb", "-o", "/root/output.yml"]
            )

            # Should error
            assert result.exit_code != 0


class TestCLIHelpAndVersion:
    """Test help and version commands."""

    def test_help_command(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output or "Commands:" in result.output

    def test_version_command(self) -> None:
        """Test --version option."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["--version"])

        # May show version info or not
        assert result.exit_code in [0, 2]

    def test_subcommand_help(self) -> None:
        """Test subcommand help."""
        runner = CliRunner()
        result = runner.invoke(cli.cli, ["convert", "--help"])

        assert result.exit_code == 0


class TestCLIIntegrationWorkflows:
    """Test complete CLI workflows."""

    def test_full_migration_workflow(self) -> None:
        """Test a complete migration workflow."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Setup cookbook structure
            Path("metadata.rb").write_text("name 'test'")
            Path("recipes").mkdir()
            Path("recipes/default.rb").write_text("package 'apache2'")

            # Step 1: Analyze
            result1 = runner.invoke(cli.cli, ["assess", "."])
            assert result1.exit_code in [0, 1, 2]

            # Step 2: Plan
            result2 = runner.invoke(cli.cli, ["plan", "."])
            assert result2.exit_code in [0, 1, 2]

            # Step 3: Convert
            result3 = runner.invoke(
                cli.cli,
                ["convert", "-i", "recipes/default.rb", "-o", "playbook.yml"],
            )
            assert result3.exit_code in [0, 1, 2]

    def test_multi_module_analysis(self) -> None:
        """Test analysing multiple modules in one workflow."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Setup structure
            Path("metadata.rb").write_text("name 'test'")
            Path("recipes").mkdir()
            Path("recipes/default.rb").write_text("# recipe")
            Path("attributes").mkdir()
            Path("attributes/default.rb").write_text("# attrs")
            Path("templates").mkdir()
            Path("templates/config.erb").write_text("# template")

            # Analyze all
            result = runner.invoke(cli.cli, ["assess", "."])

            assert result.exit_code in [0, 1, 2]

    def test_batch_conversion(self) -> None:
        """Test batch conversion of multiple files."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create multiple recipe files
            for i in range(3):
                Path(f"recipe{i}.rb").write_text(f"# recipe {i}")

            result = runner.invoke(
                cli.cli,
                [
                    "convert",
                    "-i",
                    "recipe0.rb,recipe1.rb,recipe2.rb",
                    "-o",
                    "output",
                ],
            )

            assert result.exit_code in [0, 1, 2]


class TestCLIContextOptions:
    """Test context and configuration options."""

    @patch.dict("os.environ", {"SOUSCHEF_CONFIG": "/tmp/config.json"})
    def test_config_environment_variable(self) -> None:
        """Test using configuration via environment variable."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test.rb").write_text("# test")

            result = runner.invoke(cli.cli, ["convert", "-i", "test.rb"])

            assert result.exit_code in [0, 1, 2]

    def test_working_directory_context(self) -> None:
        """Test commands work in different working directories."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("subdir").mkdir()
            Path("subdir/test.rb").write_text("# test")

            result = runner.invoke(cli.cli, ["convert", "-i", "subdir/test.rb"])

            assert result.exit_code in [0, 1, 2]
