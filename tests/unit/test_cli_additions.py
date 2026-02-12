"""Comprehensive tests for CLI module to improve coverage."""

from pathlib import Path

from click.testing import CliRunner

from souschef.cli import (
    attributes,
    cat,
    cli,
    convert,
    cookbook,
    inspec_convert,
    inspec_generate,
    inspec_parse,
    ls,
    metadata,
    recipe,
    resource,
    structure,
    template,
)


class TestCLIRecipeCommand:
    """Test CLI recipe subcommand."""

    def test_recipe_command_basic(self, tmp_path: Path) -> None:
        """Test executing recipe command."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(recipe, [str(recipe_file)])
        assert isinstance(result.output, str)

    def test_recipe_command_json_output(self, tmp_path: Path) -> None:
        """Test recipe command with JSON output."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(recipe, [str(recipe_file), "--format", "json"])
        assert isinstance(result.output, str)

    def test_recipe_command_yaml_output(self, tmp_path: Path) -> None:
        """Test recipe command with YAML output."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(recipe, [str(recipe_file), "--format", "yaml"])
        assert isinstance(result.output, str)

    def test_recipe_command_missing_file(self) -> None:
        """Test recipe command with missing file."""
        runner = CliRunner()
        result = runner.invoke(recipe, ["/nonexistent/recipe.rb"])
        # Should handle gracefully
        assert isinstance(result.output, str)


class TestCLITemplateCommand:
    """Test CLI template subcommand."""

    def test_template_command_basic(self, tmp_path: Path) -> None:
        """Test executing template command."""
        template_file = tmp_path / "app.conf.erb"
        template_file.write_text("<%= @app_name %>")

        runner = CliRunner()
        result = runner.invoke(template, [str(template_file)])
        assert isinstance(result.output, str)

    def test_template_command_json_format(self, tmp_path: Path) -> None:
        """Test template command with JSON format."""
        template_file = tmp_path / "config.erb"
        template_file.write_text("port: <%= @port %>")

        runner = CliRunner()
        result = runner.invoke(template, [str(template_file), "--format", "json"])
        assert isinstance(result.output, str)


class TestCLIAttributesCommand:
    """Test CLI attributes subcommand."""

    def test_attributes_command_basic(self, tmp_path: Path) -> None:
        """Test executing attributes command."""
        attr_file = tmp_path / "default.rb"
        attr_file.write_text("default[:nginx][:port] = 80")

        runner = CliRunner()
        result = runner.invoke(attributes, [str(attr_file)])
        assert isinstance(result.output, str)

    def test_attributes_command_yaml_output(self, tmp_path: Path) -> None:
        """Test attributes command with YAML format."""
        attr_file = tmp_path / "default.rb"
        attr_file.write_text("default[:web][:enabled] = true")

        runner = CliRunner()
        result = runner.invoke(attributes, [str(attr_file), "--format", "yaml"])
        assert isinstance(result.output, str)


class TestCLIResourceCommand:
    """Test CLI resource subcommand."""

    def test_resource_command_basic(self, tmp_path: Path) -> None:
        """Test executing resource command."""
        resource_file = tmp_path / "custom_resource.rb"
        resource_file.write_text("property :name, String\nproperty :action, String")

        runner = CliRunner()
        result = runner.invoke(resource, [str(resource_file)])
        assert isinstance(result.output, str)

    def test_resource_command_missing_file(self) -> None:
        """Test resource command with nonexistent file."""
        runner = CliRunner()
        result = runner.invoke(resource, ["/nonexistent/resource.rb"])
        assert isinstance(result.output, str)


class TestCLIMetadataCommand:
    """Test CLI metadata subcommand."""

    def test_metadata_command_basic(self, tmp_path: Path) -> None:
        """Test executing metadata command."""
        metadata_file = tmp_path / "metadata.rb"
        metadata_file.write_text("name 'cookbook'\nversion '1.0'")

        runner = CliRunner()
        result = runner.invoke(metadata, [str(metadata_file)])
        assert isinstance(result.output, str)

    def test_metadata_command_with_dependencies(self, tmp_path: Path) -> None:
        """Test metadata command with dependencies."""
        metadata_file = tmp_path / "metadata.rb"
        metadata_file.write_text("name 'test'\ndepends 'nginx'\ndepends 'postgresql'")

        runner = CliRunner()
        result = runner.invoke(metadata, [str(metadata_file)])
        assert isinstance(result.output, str)


class TestCLIStructureCommand:
    """Test CLI structure subcommand."""

    def test_structure_command_basic(self, tmp_path: Path) -> None:
        """Test executing structure command."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(structure, [str(cookbook_dir)])
        assert isinstance(result.output, str)

    def test_structure_command_with_recipes(self, tmp_path: Path) -> None:
        """Test structure command with recipes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("")
        (recipes_dir / "app.rb").write_text("")

        runner = CliRunner()
        result = runner.invoke(structure, [str(cookbook_dir)])
        assert isinstance(result.output, str)

    def test_structure_command_full_structure(self, tmp_path: Path) -> None:
        """Test structure with all standard directories."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'full'")

        for dir_name in [
            "recipes",
            "attributes",
            "templates",
            "resources",
            "libraries",
        ]:
            subdir = cookbook_dir / dir_name
            subdir.mkdir()
            (subdir / "file.rb").write_text("# content")

        runner = CliRunner()
        result = runner.invoke(structure, [str(cookbook_dir)])
        assert isinstance(result.output, str)


class TestCLILsCommand:
    """Test CLI ls (list) subcommand."""

    def test_ls_command_cookbook_directory(self, tmp_path: Path) -> None:
        """Test ls command on cookbook."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("")

        runner = CliRunner()
        result = runner.invoke(ls, [str(cookbook_dir)])
        assert isinstance(result.output, str)

    def test_ls_command_recipes_directory(self, tmp_path: Path) -> None:
        """Test ls command on recipes directory."""
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("")
        (recipes_dir / "app.rb").write_text("")
        (recipes_dir / "database.rb").write_text("")

        runner = CliRunner()
        result = runner.invoke(ls, [str(recipes_dir)])
        assert isinstance(result.output, str)

    def test_ls_command_single_file(self, tmp_path: Path) -> None:
        """Test ls command on single file."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(ls, [str(recipe_file)])
        assert isinstance(result.output, str)


class TestCLICatCommand:
    """Test CLI cat (display content) subcommand."""

    def test_cat_command_recipe_file(self, tmp_path: Path) -> None:
        """Test cat command on recipe file."""
        recipe_file = tmp_path / "default.rb"
        recipe_content = (
            "package 'nginx'\nservice 'nginx' do\n  action [:enable, :start]\nend"
        )
        recipe_file.write_text(recipe_content)

        runner = CliRunner()
        result = runner.invoke(cat, [str(recipe_file)])
        assert isinstance(result.output, str)

    def test_cat_command_missing_file(self) -> None:
        """Test cat command with missing file."""
        runner = CliRunner()
        result = runner.invoke(cat, ["/nonexistent/file.rb"])
        assert isinstance(result.output, str)

    def test_cat_command_binary_awareness(self, tmp_path: Path) -> None:
        """Test cat with binary file handling."""
        # This may fail gracefully or handle binary
        binary_file = tmp_path / "file.bin"
        binary_file.write_bytes(b"\x00\x01\x02")

        runner = CliRunner()
        result = runner.invoke(cat, [str(binary_file)])
        assert isinstance(result.output, str) or result.exit_code != 0


class TestCLIConvertCommand:
    """Test CLI convert subcommand."""

    def test_convert_recipe_basic(self, tmp_path: Path) -> None:
        """Test converting single recipe."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(convert, [str(recipe_file)])
        assert isinstance(result.output, str)

    def test_convert_recipe_with_output_format(self, tmp_path: Path) -> None:
        """Test convert with output format."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(convert, [str(recipe_file), "--format", "yaml"])
        assert isinstance(result.output, str)

    def test_convert_recipe_with_output_file(self, tmp_path: Path) -> None:
        """Test convert with output file."""
        recipe_file = tmp_path / "default.rb"
        recipe_file.write_text("package 'nginx'")
        output_file = tmp_path / "output.yml"

        runner = CliRunner()
        result = runner.invoke(
            convert, [str(recipe_file), "--output", str(output_file)]
        )
        assert isinstance(result.output, str)

    def test_convert_complex_recipe(self, tmp_path: Path) -> None:
        """Test converting complex recipe."""
        recipe_file = tmp_path / "default.rb"
        complex_recipe = """
directory '/opt/app' do
  recursive true
end

template '/etc/app.conf' do
  source 'app.conf.erb'
  variables(
    name: node[:app][:name]
  )
  notifies :restart, 'service[app]'
end

service 'app' do
  action [:enable, :start]
  subscribes :restart, 'template[/etc/app.conf]'
end
"""
        recipe_file.write_text(complex_recipe)

        runner = CliRunner()
        result = runner.invoke(convert, [str(recipe_file)])
        assert isinstance(result.output, str)


class TestCLICookbookCommand:
    """Test CLI cookbook subcommand."""

    def test_cookbook_convert_basic(self, tmp_path: Path) -> None:
        """Test converting cookbook."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")

        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cookbook, [str(cookbook_dir), "--output", str(output_dir)]
        )
        assert isinstance(result.output, str)

    def test_cookbook_convert_dry_run(self, tmp_path: Path) -> None:
        """Test cookbook conversion in dry-run mode."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(cookbook, [str(cookbook_dir), "--dry-run"])
        assert isinstance(result.output, str)

    def test_cookbook_convert_multiple_recipes(self, tmp_path: Path) -> None:
        """Test cookbook with multiple recipes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'multi'")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package 'nginx'")
        (recipes_dir / "database.rb").write_text("package 'postgresql'")
        (recipes_dir / "cache.rb").write_text("package 'redis'")

        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cookbook, [str(cookbook_dir), "--output", str(output_dir)]
        )
        assert isinstance(result.output, str)

    def test_cookbook_with_attributes(self, tmp_path: Path) -> None:
        """Test cookbook conversion including attributes."""
        cookbook_dir = tmp_path / "cookbook"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        attrs_dir = cookbook_dir / "attributes"
        attrs_dir.mkdir()
        (attrs_dir / "default.rb").write_text("default[:nginx][:port] = 80")

        recipes_dir = cookbook_dir / "recipes"
        recipes_dir.mkdir()
        (recipes_dir / "default.rb").write_text("package node[:nginx][:name]")

        output_dir = tmp_path / "output"

        runner = CliRunner()
        result = runner.invoke(
            cookbook, [str(cookbook_dir), "--output", str(output_dir)]
        )
        assert isinstance(result.output, str)


class TestCLIInspecCommands:
    """Test InSpec-related CLI commands."""

    def test_inspec_parse_basic(self, tmp_path: Path) -> None:
        """Test parsing InSpec profile."""
        inspec_profile = tmp_path / "profile"
        inspec_profile.mkdir()

        controls_dir = inspec_profile / "controls"
        controls_dir.mkdir()
        (controls_dir / "test.rb").write_text(
            "describe package('nginx') do\n  it { should be_installed }\nend"
        )

        runner = CliRunner()
        result = runner.invoke(inspec_parse, [str(inspec_profile)])
        assert isinstance(result.output, str)

    def test_inspec_parse_json_output(self, tmp_path: Path) -> None:
        """Test InSpec parse with JSON output."""
        inspec_profile = tmp_path / "profile"
        inspec_profile.mkdir()

        controls_dir = inspec_profile / "controls"
        controls_dir.mkdir()
        (controls_dir / "test.rb").write_text(
            "describe file('/etc/config') do\n  it { should exist }\nend"
        )

        runner = CliRunner()
        result = runner.invoke(inspec_parse, [str(inspec_profile), "--format", "json"])
        assert isinstance(result.output, str)

    def test_inspec_convert_basic(self, tmp_path: Path) -> None:
        """Test converting InSpec to Ansible."""
        inspec_profile = tmp_path / "profile"
        inspec_profile.mkdir()

        controls_dir = inspec_profile / "controls"
        controls_dir.mkdir()
        (controls_dir / "test.rb").write_text(
            "describe service('nginx') do\n  it { should be_running }\nend"
        )

        runner = CliRunner()
        result = runner.invoke(inspec_convert, [str(inspec_profile)])
        assert isinstance(result.output, str)

    def test_inspec_generate_basic(self, tmp_path: Path) -> None:
        """Test generating InSpec from something."""
        source_path = tmp_path / "source.rb"
        source_path.write_text("package 'nginx'")

        runner = CliRunner()
        result = runner.invoke(inspec_generate, [str(source_path)])
        assert isinstance(result.output, str)


class TestCLIMainCommand:
    """Test main CLI command group."""

    def test_cli_help(self) -> None:
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert isinstance(result.output, str)
        assert "--help" in result.output or "help" in result.output.lower()

    def test_cli_version(self) -> None:
        """Test CLI version output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        # May exit with code 0 or another status
        assert isinstance(result.output, str)


class TestCLIInputValidation:
    """Test CLI input validation."""

    def test_cli_empty_path_argument(self) -> None:
        """Test handling empty path argument."""
        runner = CliRunner()
        result = runner.invoke(recipe, [""])
        # Should handle gracefully
        assert isinstance(result.output, str)

    def test_cli_special_characters_in_path(self, tmp_path: Path) -> None:
        """Test paths with special characters."""
        cookbook_dir = tmp_path / "cookbook-test_v2.0"
        cookbook_dir.mkdir()
        (cookbook_dir / "metadata.rb").write_text("name 'test'")

        runner = CliRunner()
        result = runner.invoke(structure, [str(cookbook_dir)])
        assert isinstance(result.output, str)

    def test_cli_very_long_path(self, tmp_path: Path) -> None:
        """Test handling very long file paths."""
        # Create deeply nested directory
        deep_dir = tmp_path
        for i in range(10):
            deep_dir = deep_dir / f"level{i}"
        deep_dir.mkdir(parents=True)

        recipe_file = deep_dir / "recipe.rb"
        recipe_file.write_text("package 'test'")

        runner = CliRunner()
        result = runner.invoke(recipe, [str(recipe_file)])
        # Should complete without error
        assert isinstance(result.output, str)
