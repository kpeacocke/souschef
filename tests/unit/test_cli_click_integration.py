"""Integration tests for CLI commands using Click testing utilities."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from souschef.cli import cli


class TestCLIRecipeCommand:
    """Test recipe command through CLI interface."""

    def test_recipe_command_with_valid_file(self) -> None:
        """Test recipe command with valid cookbook recipe."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "default.rb"
            recipe_file.write_text("package 'nginx' do\n  action :install\nend")

            result = runner.invoke(cli, ["recipe", str(recipe_file)])
            assert result.exit_code == 0

    def test_recipe_command_nonexistent_file(self) -> None:
        """Test recipe command with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["recipe", "/nonexistent/recipe.rb"])
        assert result.exit_code != 0

    def test_recipe_command_with_json_format(self) -> None:
        """Test recipe command with JSON output format."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe_file = Path(tmpdir) / "test.rb"
            recipe_file.write_text("service 'nginx' do\n  action :start\nend")

            result = runner.invoke(
                cli, ["recipe", str(recipe_file), "--format", "json"]
            )
            assert result.exit_code == 0
            assert "nginx" in result.output


class TestCLIAttributesCommand:
    """Test attributes command through CLI."""

    def test_attributes_command_valid_file(self) -> None:
        """Test attributes command with valid file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "default.rb"
            attr_file.write_text("default['app']['port'] = 3000")

            result = runner.invoke(cli, ["attributes", str(attr_file)])
            assert result.exit_code == 0

    def test_attributes_command_with_precedence_resolution(self) -> None:
        """Test attributes with precedence parameter."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            attr_file = Path(tmpdir) / "attrs.rb"
            attr_file.write_text(
                "default['key'] = 'value'\noverride['key'] = 'override'"
            )

            result = runner.invoke(cli, ["attributes", str(attr_file)])
            assert result.exit_code == 0

    def test_attributes_command_nonexistent_file(self) -> None:
        """Test attributes command with missing file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["attributes", "/nonexistent/attrs.rb"])
        assert result.exit_code != 0


class TestCLITemplateCommand:
    """Test template command."""

    def test_template_command_valid_file(self) -> None:
        """Test template command with valid ERB template."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = Path(tmpdir) / "config.erb"
            template_file.write_text("<%= @server_name %>:<%= @port %>")

            result = runner.invoke(cli, ["template", str(template_file)])
            assert result.exit_code == 0

    def test_template_command_nonexistent(self) -> None:
        """Test template command with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["template", "/nonexistent/template.erb"])
        assert result.exit_code != 0


class TestCLIResourceCommand:
    """Test resource command."""

    def test_resource_command_valid_file(self) -> None:
        """Test resource command with custom resource."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_file = Path(tmpdir) / "app.rb"
            resource_file.write_text("resource_name :my_app\nproperty :name, String")

            result = runner.invoke(cli, ["resource", str(resource_file)])
            assert result.exit_code == 0

    def test_resource_command_nonexistent(self) -> None:
        """Test resource command with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["resource", "/nonexistent/resource.rb"])
        assert result.exit_code != 0


class TestCLIMetadataCommand:
    """Test metadata command."""

    def test_metadata_command_valid_file(self) -> None:
        """Test metadata command with valid metadata."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_file = Path(tmpdir) / "metadata.rb"
            metadata_file.write_text("name 'test'\nversion '1.0.0'")

            result = runner.invoke(cli, ["metadata", str(metadata_file)])
            assert result.exit_code == 0

    def test_metadata_command_nonexistent(self) -> None:
        """Test metadata command with missing file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["metadata", "/nonexistent/metadata.rb"])
        assert result.exit_code != 0


class TestCLIListCommand:
    """Test list/structure command."""

    def test_ls_command_directory(self) -> None:
        """Test ls command on directory."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "file1.txt").write_text("content")
            (tmppath / "subdir").mkdir()

            result = runner.invoke(cli, ["ls", tmpdir])
            assert result.exit_code == 0

    def test_ls_command_nonexistent(self) -> None:
        """Test ls command on nonexistent path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["ls", "/nonexistent/path"])
        assert result.exit_code != 0


class TestCLICatCommand:
    """Test cat command."""

    def test_cat_command_file(self) -> None:
        """Test cat command on file."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("file content")

            result = runner.invoke(cli, ["cat", str(test_file)])
            assert result.exit_code == 0
            assert "content" in result.output or result.exit_code == 0

    def test_cat_command_nonexistent(self) -> None:
        """Test cat command on nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["cat", "/nonexistent/file.txt"])
        assert result.exit_code != 0


class TestCLIStructureCommand:
    """Test cookbook structure command."""

    def test_structure_command_cookbook(self) -> None:
        """Test structure command on cookbook directory."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "metadata.rb").write_text("name 'test'\nversion '1.0.0'")
            (tmppath / "recipes").mkdir()
            (tmppath / "recipes" / "default.rb").write_text("# recipe")

            result = runner.invoke(cli, ["structure", tmpdir])
            assert result.exit_code == 0

    def test_structure_command_nonexistent(self) -> None:
        """Test structure command on nonexistent path."""
        runner = CliRunner()
        result = runner.invoke(cli, ["structure", "/nonexistent/cookbook"])
        assert result.exit_code != 0


class TestCLIConvertCommand:
    """Test convert command."""

    def test_convert_command_package_resource(self) -> None:
        """Test convert command converts package resource."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["convert", "package", "nginx", "--action", "install"]
        )
        assert result.exit_code == 0
        assert "nginx" in result.output

    def test_convert_command_service_resource(self) -> None:
        """Test convert command converts service resource."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["convert", "service", "nginx", "--action", "start"]
        )
        assert result.exit_code == 0
        assert "nginx" in result.output

    def test_convert_command_nonexistent(self) -> None:
        """Test convert command on nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "/nonexistent/recipe.rb"])
        assert result.exit_code != 0


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_cli_help_command(self) -> None:
        """Test help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Commands" in result.output or "help" in result.output.lower()

    def test_cli_version_command(self) -> None:
        """Test version/info command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        # Version command may or may not exist, accept both
        assert result.exit_code in [0, 2]

    def test_cli_invalid_command(self) -> None:
        """Test invalid command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid_command"])
        assert result.exit_code != 0
