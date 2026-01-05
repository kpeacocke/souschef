"""
Command-line interface for SousChef.

Provides easy access to Chef cookbook parsing and conversion tools.
"""

import json
import sys
from pathlib import Path
from typing import NoReturn

import click

from souschef.server import (
    convert_inspec_to_test,
    convert_resource_to_task,
    generate_inspec_from_recipe,
    list_cookbook_structure,
    list_directory,
    parse_attributes,
    parse_custom_resource,
    parse_inspec_profile,
    parse_recipe,
    parse_template,
    read_cookbook_metadata,
    read_file,
)


@click.group()
@click.version_option(version="0.1.0", prog_name="souschef")
def cli() -> None:
    """
    SousChef - Chef to Ansible conversion toolkit.

    Parse Chef cookbooks and convert resources to Ansible playbooks.
    """


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
def recipe(path: str, output_format: str) -> None:
    """
    Parse a Chef recipe file and extract resources.

    PATH: Path to the recipe (.rb) file
    """
    result = parse_recipe(path)
    _output_result(result, output_format)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="json",
)
def template(path: str, output_format: str) -> None:
    """
    Parse a Chef ERB template and convert to Jinja2.

    PATH: Path to the template (.erb) file
    """
    result = parse_template(path)
    _output_result(result, output_format)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
def attributes(path: str, output_format: str) -> None:
    """
    Parse Chef attributes file.

    PATH: Path to the attributes (.rb) file
    """
    result = parse_attributes(path)
    _output_result(result, output_format)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="json",
)
def resource(path: str, output_format: str) -> None:
    """
    Parse a custom resource or LWRP file.

    PATH: Path to the custom resource (.rb) file
    """
    result = parse_custom_resource(path)
    _output_result(result, output_format)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def metadata(path: str) -> None:
    """
    Parse cookbook metadata.rb file.

    PATH: Path to the metadata.rb file
    """
    result = read_cookbook_metadata(path)
    click.echo(result)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def structure(path: str) -> None:
    """
    List the structure of a Chef cookbook.

    PATH: Path to the cookbook root directory
    """
    result = list_cookbook_structure(path)
    click.echo(result)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def ls(path: str) -> None:
    """
    List contents of a directory.

    PATH: Path to the directory
    """
    result = list_directory(path)
    if isinstance(result, list):
        for item in result:
            click.echo(item)
    else:
        click.echo(result, err=True)
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def cat(path: str) -> None:
    """
    Read and display file contents.

    PATH: Path to the file
    """
    result = read_file(path)
    click.echo(result)


@cli.command()
@click.argument("resource_type")
@click.argument("resource_name")
@click.option("--action", default="create", help="Chef action (default: create)")
@click.option(
    "--properties",
    default="",
    help="Additional properties (JSON string)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
)
def convert(
    resource_type: str,
    resource_name: str,
    action: str,
    properties: str,
    output_format: str,
) -> None:
    """
    Convert a Chef resource to Ansible task.

    RESOURCE_TYPE: Chef resource type (e.g., package, service, template)

    RESOURCE_NAME: Resource name (e.g., nginx, /etc/config.conf)

    Examples:
      souschef convert package nginx --action install

      souschef convert service nginx --action start

      souschef convert template /etc/nginx/nginx.conf --action create

    """
    result = convert_resource_to_task(resource_type, resource_name, action, properties)

    if output_format == "json":
        # Parse YAML and convert to JSON for consistency
        try:
            import yaml

            data = yaml.safe_load(result)
            click.echo(json.dumps(data, indent=2))
        except ImportError:
            click.echo("Warning: PyYAML not installed, outputting as YAML", err=True)
            click.echo(result)
        except Exception:
            # If parsing fails, output as-is
            click.echo(result)
    else:
        click.echo(result)


def _display_recipe_summary(recipe_file: Path) -> None:
    """Display a summary of a recipe file."""
    click.echo(f"\n  {recipe_file.name}:")
    recipe_result = parse_recipe(str(recipe_file))
    lines = recipe_result.split("\n")
    click.echo("    " + "\n    ".join(lines[:10]))
    if len(lines) > 10:
        click.echo(f"    ... ({len(lines) - 10} more lines)")


def _display_resource_summary(resource_file: Path) -> None:
    """Display a summary of a custom resource file."""
    click.echo(f"\n  {resource_file.name}:")
    resource_result = parse_custom_resource(str(resource_file))
    try:
        data = json.loads(resource_result)
        click.echo(f"    Type: {data.get('resource_type')}")
        click.echo(f"    Properties: {len(data.get('properties', []))}")
        click.echo(f"    Actions: {', '.join(data.get('actions', []))}")
    except json.JSONDecodeError:
        click.echo(f"    {resource_result[:100]}")


def _display_template_summary(template_file: Path) -> None:
    """Display a summary of a template file."""
    click.echo(f"\n  {template_file.name}:")
    template_result = parse_template(str(template_file))
    try:
        data = json.loads(template_result)
        variables = data.get("variables", [])
        click.echo(f"    Variables: {len(variables)}")
        if variables:
            click.echo(f"    {', '.join(variables[:5])}")
            if len(variables) > 5:
                click.echo(f"    ... and {len(variables) - 5} more")
    except json.JSONDecodeError:
        click.echo(f"    {template_result[:100]}")


@cli.command()
@click.argument("cookbook_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory for converted playbook",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
def cookbook(cookbook_path: str, output: str | None, dry_run: bool) -> None:
    """
    Analyze an entire Chef cookbook.

    COOKBOOK_PATH: Path to the cookbook root directory

    This command analyzes the cookbook structure, metadata, recipes,
    attributes, templates, and custom resources.
    """
    cookbook_dir = Path(cookbook_path)

    click.echo(f"Analyzing cookbook: {cookbook_dir.name}")
    click.echo("=" * 50)

    # Parse metadata
    metadata_file = cookbook_dir / "metadata.rb"
    if metadata_file.exists():
        click.echo("\n📋 Metadata:")
        click.echo("-" * 50)
        metadata_result = read_cookbook_metadata(str(metadata_file))
        click.echo(metadata_result)

    # List structure
    click.echo("\n📁 Structure:")
    click.echo("-" * 50)
    structure_result = list_cookbook_structure(str(cookbook_dir))
    click.echo(structure_result)

    # Parse recipes
    recipes_dir = cookbook_dir / "recipes"
    if recipes_dir.exists():
        click.echo("\n🧑‍🍳 Recipes:")
        click.echo("-" * 50)
        for recipe_file in recipes_dir.glob("*.rb"):
            _display_recipe_summary(recipe_file)

    # Parse custom resources
    resources_dir = cookbook_dir / "resources"
    if resources_dir.exists():
        click.echo("\n🔧 Custom Resources:")
        click.echo("-" * 50)
        for resource_file in resources_dir.glob("*.rb"):
            _display_resource_summary(resource_file)

    # Parse templates
    templates_dir = cookbook_dir / "templates" / "default"
    if templates_dir.exists():
        click.echo("\n📄 Templates:")
        click.echo("-" * 50)
        for template_file in templates_dir.glob("*.erb"):
            _display_template_summary(template_file)

    if output and not dry_run:
        click.echo(f"\n💾 Would save results to: {output}")
        click.echo("(Full conversion not yet implemented)")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="json",
)
def inspec_parse(path: str, output_format: str) -> None:
    """
    Parse an InSpec profile or control file.

    PATH: Path to InSpec profile directory or .rb control file
    """
    result = parse_inspec_profile(path)
    _output_result(result, output_format)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["testinfra", "ansible_assert"]),
    default="testinfra",
    help="Output format for converted tests",
)
def inspec_convert(path: str, output_format: str) -> None:
    """
    Convert InSpec controls to test format.

    PATH: Path to InSpec profile directory or .rb control file
    """
    result = convert_inspec_to_test(path, output_format)
    click.echo(result)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
def inspec_generate(path: str, output_format: str) -> None:
    """
    Generate InSpec controls from Chef recipe.

    PATH: Path to Chef recipe (.rb) file
    """
    result = generate_inspec_from_recipe(path)
    _output_result(result, output_format)


def _output_json_format(result: str) -> None:
    """Output result as JSON format."""
    try:
        data = json.loads(result)
        click.echo(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        click.echo(result)


def _output_dict_as_text(data: dict) -> None:
    """Output a dictionary in human-readable text format."""
    for key, value in data.items():
        if isinstance(value, list):
            click.echo(f"{key}:")
            for item in value:
                click.echo(f"  - {item}")
        else:
            click.echo(f"{key}: {value}")


def _output_text_format(result: str) -> None:
    """Output result as text format, pretty-printing JSON if possible."""
    try:
        data = json.loads(result)
        if isinstance(data, dict):
            _output_dict_as_text(data)
        else:
            click.echo(result)
    except json.JSONDecodeError:
        click.echo(result)


def _output_result(result: str, output_format: str) -> None:
    """
    Output result in specified format.

    Args:
        result: Result string (may be JSON or plain text).
        output_format: Output format ('text' or 'json').

    """
    if output_format == "json":
        _output_json_format(result)
    else:
        _output_text_format(result)


def main() -> NoReturn:
    """Run the CLI."""
    cli()
    sys.exit(0)


if __name__ == "__main__":
    main()
