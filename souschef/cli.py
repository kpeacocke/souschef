"""
Command-line interface for SousChef.

Provides easy access to Chef cookbook parsing and conversion tools.
"""

import json
import sys
from pathlib import Path
from typing import NoReturn

import click

from souschef.assessment import assess_chef_migration_complexity
from souschef.converters.playbook import generate_playbook_from_recipe
from souschef.profiling import (
    generate_cookbook_performance_report,
    profile_function,
)
from souschef.server import (
    convert_inspec_to_test,
    convert_resource_to_task,
    generate_github_workflow_from_chef,
    generate_gitlab_ci_from_chef,
    generate_inspec_from_recipe,
    generate_jenkinsfile_from_chef,
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

# CI/CD job description constants
CI_JOB_LINT = "  • Lint (cookstyle/foodcritic)"
CI_JOB_UNIT_TESTS = "  • Unit Tests (ChefSpec)"
CI_JOB_INTEGRATION_TESTS = "  • Integration Tests (Test Kitchen)"


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
    type=click.Choice(["testinfra", "ansible_assert", "serverspec", "goss"]),
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


@cli.command()
@click.argument("cookbook_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path for Jenkinsfile (default: ./Jenkinsfile)",
)
@click.option(
    "--pipeline-type",
    type=click.Choice(["declarative", "scripted"]),
    default="declarative",
    help="Jenkins pipeline type (default: declarative)",
)
@click.option(
    "--parallel/--no-parallel",
    default=True,
    help="Enable parallel test execution (default: enabled)",
)
def generate_jenkinsfile(
    cookbook_path: str, output: str | None, pipeline_type: str, parallel: bool
) -> None:
    """
    Generate Jenkinsfile for Chef cookbook CI/CD.

    COOKBOOK_PATH: Path to the Chef cookbook root directory

    This command analyzes the cookbook for CI patterns (Test Kitchen,
    lint tools, test suites) and generates an appropriate Jenkinsfile
    with stages for linting, testing, and convergence.

    Examples:
      souschef generate-jenkinsfile ./mycookbook

      souschef generate-jenkinsfile ./mycookbook -o Jenkinsfile.new

      souschef generate-jenkinsfile ./mycookbook --pipeline-type scripted

      souschef generate-jenkinsfile ./mycookbook --no-parallel

    """
    try:
        result = generate_jenkinsfile_from_chef(
            cookbook_path=cookbook_path,
            pipeline_type=pipeline_type,
            enable_parallel="yes" if parallel else "no",
        )

        # Determine output path
        output_path = Path(output) if output else Path.cwd() / "Jenkinsfile"

        # Write Jenkinsfile
        output_path.write_text(result)
        click.echo(f"✓ Generated {pipeline_type} Jenkinsfile: {output_path}")

        # Show summary
        click.echo("\nGenerated Pipeline Stages:")
        if "stage('Lint')" in result or "stage 'Lint'" in result:
            click.echo(CI_JOB_LINT)
        if "stage('Unit Tests')" in result or "stage 'Unit Tests'" in result:
            click.echo(CI_JOB_UNIT_TESTS)
        integration_stage = (
            "stage('Integration Tests')" in result
            or "stage 'Integration Tests'" in result
        )
        if integration_stage:
            click.echo(CI_JOB_INTEGRATION_TESTS)

        if parallel:
            click.echo("\nParallel execution: Enabled")
        else:
            click.echo("\nParallel execution: Disabled")

    except Exception as e:
        click.echo(f"Error generating Jenkinsfile: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("cookbook_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path for .gitlab-ci.yml (default: ./.gitlab-ci.yml)",
)
@click.option(
    "--cache/--no-cache",
    default=True,
    help="Enable dependency caching (default: enabled)",
)
@click.option(
    "--artifacts/--no-artifacts",
    default=True,
    help="Enable test report artifacts (default: enabled)",
)
def generate_gitlab_ci(
    cookbook_path: str, output: str | None, cache: bool, artifacts: bool
) -> None:
    """
    Generate .gitlab-ci.yml for Chef cookbook CI/CD.

    COOKBOOK_PATH: Path to the Chef cookbook root directory

    This command analyzes the cookbook for CI patterns (Test Kitchen,
    lint tools, test suites) and generates an appropriate GitLab CI
    configuration with jobs for linting, testing, and convergence.

    Examples:
      souschef generate-gitlab-ci ./mycookbook

      souschef generate-gitlab-ci ./mycookbook -o .gitlab-ci.test.yml

      souschef generate-gitlab-ci ./mycookbook --no-cache

      souschef generate-gitlab-ci ./mycookbook --no-artifacts

    """
    try:
        result = generate_gitlab_ci_from_chef(
            cookbook_path=cookbook_path,
            enable_cache="yes" if cache else "no",
            enable_artifacts="yes" if artifacts else "no",
        )

        # Determine output path
        output_path = Path(output) if output else Path.cwd() / ".gitlab-ci.yml"

        # Write GitLab CI config
        output_path.write_text(result)
        click.echo(f"✓ Generated GitLab CI configuration: {output_path}")

        # Show summary
        click.echo("\nGenerated CI Jobs:")
        if "cookstyle:" in result or "foodcritic:" in result:
            click.echo(CI_JOB_LINT)
        if "unit-test:" in result or "chefspec:" in result:
            click.echo(CI_JOB_UNIT_TESTS)
        if "integration-test:" in result or "kitchen-" in result:
            click.echo(CI_JOB_INTEGRATION_TESTS)

        click.echo(f"\nCache: {'Enabled' if cache else 'Disabled'}")
        click.echo(f"Artifacts: {'Enabled' if artifacts else 'Disabled'}")

    except Exception as e:
        click.echo(f"Error generating GitLab CI configuration: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("cookbook_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path for workflow (default: ./.github/workflows/ci.yml)",
)
@click.option(
    "--workflow-name",
    default="Chef Cookbook CI",
    help="GitHub Actions workflow name (default: Chef Cookbook CI)",
)
@click.option(
    "--cache/--no-cache",
    default=True,
    help="Enable dependency caching (default: enabled)",
)
@click.option(
    "--artifacts/--no-artifacts",
    default=True,
    help="Enable test report artifacts (default: enabled)",
)
def generate_github_workflow(
    cookbook_path: str,
    output: str | None,
    workflow_name: str,
    cache: bool,
    artifacts: bool,
) -> None:
    """
    Generate GitHub Actions workflow for Chef cookbook CI/CD.

    COOKBOOK_PATH: Path to the Chef cookbook root directory

    This command analyzes the cookbook for CI patterns (Test Kitchen,
    lint tools, test suites) and generates an appropriate GitHub Actions
    workflow with jobs for linting, testing, and convergence.

    Examples:
      souschef generate-github-workflow ./mycookbook

      souschef generate-github-workflow ./mycookbook -o .github/workflows/test.yml

      souschef generate-github-workflow ./mycookbook --no-cache

      souschef generate-github-workflow ./mycookbook --workflow-name "CI Pipeline"

    """
    try:
        result = generate_github_workflow_from_chef(
            cookbook_path=cookbook_path,
            workflow_name=workflow_name,
            enable_cache="yes" if cache else "no",
            enable_artifacts="yes" if artifacts else "no",
        )

        # Determine output path
        if output:
            output_path = Path(output)
        else:
            workflows_dir = Path.cwd() / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            output_path = workflows_dir / "ci.yml"

        # Write workflow file
        output_path.write_text(result)
        click.echo(f"✓ Generated GitHub Actions workflow: {output_path}")

        # Show summary
        click.echo("\nGenerated Workflow Jobs:")
        if "lint:" in result:
            click.echo(CI_JOB_LINT)
        if "unit-test:" in result:
            click.echo(CI_JOB_UNIT_TESTS)
        if "integration-test:" in result:
            click.echo(CI_JOB_INTEGRATION_TESTS)

        click.echo(f"\nCache: {'Enabled' if cache else 'Disabled'}")
        click.echo(f"Artifacts: {'Enabled' if artifacts else 'Disabled'}")

    except Exception as e:
        click.echo(f"Error generating GitHub Actions workflow: {e}", err=True)
        sys.exit(1)


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


@cli.command()
@click.argument("cookbook_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save report to file instead of printing to stdout",
)
def profile(cookbook_path: str, output: str | None) -> None:
    """
    Profile cookbook parsing performance and generate optimization report.

    COOKBOOK_PATH: Path to the Chef cookbook to profile

    This command analyzes the performance of parsing all cookbook components
    (recipes, attributes, resources, templates) and provides recommendations
    for optimization.
    """
    try:
        click.echo(f"Profiling cookbook: {cookbook_path}")
        click.echo("This may take a moment for large cookbooks...")

        report = generate_cookbook_performance_report(cookbook_path)
        report_text = str(report)

        if output:
            Path(output).write_text(report_text)
            click.echo(f"✓ Performance report saved to: {output}")
        else:
            click.echo(report_text)

    except Exception as e:
        click.echo(f"Error profiling cookbook: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument(
    "operation",
    type=click.Choice(["recipe", "attributes", "resource", "template"]),
)
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed function call statistics",
)
def profile_operation(operation: str, path: str, detailed: bool) -> None:
    """
    Profile a single parsing operation in detail.

    OPERATION: Type of operation to profile
    PATH: Path to the file to parse

    This command profiles a single parsing operation and shows
    execution time, memory usage, and optionally detailed function statistics.
    """
    operation_map = {
        "recipe": parse_recipe,
        "attributes": parse_attributes,
        "resource": parse_custom_resource,
        "template": parse_template,
    }

    func = operation_map[operation]

    try:
        click.echo(f"Profiling {operation} parsing: {path}")

        if detailed:
            from souschef.profiling import detailed_profile_function

            _, profile_result = detailed_profile_function(func, path)
            click.echo(str(profile_result))
            if profile_result.function_stats.get("top_functions"):
                click.echo("\nDetailed Function Statistics:")
                click.echo(profile_result.function_stats["top_functions"])
        else:
            _, profile_result = profile_function(func, path)
            click.echo(str(profile_result))

    except Exception as e:
        click.echo(f"Error profiling operation: {e}", err=True)
        sys.exit(1)


@cli.command("convert-recipe")
@click.option(
    "--cookbook-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Chef cookbook directory",
)
@click.option(
    "--recipe-name",
    default="default",
    help="Name of the recipe to convert (default: default)",
)
@click.option(
    "--output-path",
    required=True,
    type=click.Path(),
    help="Directory where Ansible playbook will be written",
)
def convert_recipe(cookbook_path: str, recipe_name: str, output_path: str) -> None:
    r"""
    Convert a Chef recipe to an Ansible playbook.

    This command converts a Chef recipe to an Ansible playbook and writes
    it to the specified output path. Used by the Terraform provider.

    Example:
        souschef convert-recipe --cookbook-path /chef/cookbooks/nginx \\
                                --recipe-name default \\
                                --output-path /ansible/playbooks

    """
    try:
        cookbook_dir = Path(cookbook_path)
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check recipe exists
        recipe_file = cookbook_dir / "recipes" / f"{recipe_name}.rb"
        if not recipe_file.exists():
            click.echo(
                f"Error: Recipe {recipe_name}.rb not found in {cookbook_path}/recipes",
                err=True,
            )
            sys.exit(1)

        # Get cookbook name
        metadata_file = cookbook_dir / "metadata.rb"
        cookbook_name = cookbook_dir.name  # Default to directory name

        if metadata_file.exists():
            metadata_result = read_cookbook_metadata(str(metadata_file))
            # Try to parse cookbook name from metadata
            for line in metadata_result.split("\n"):
                if line.startswith("name"):
                    cookbook_name = line.split(":", 1)[1].strip()
                    break

        # Generate playbook
        click.echo(f"Converting {cookbook_name}::{recipe_name} to Ansible...")
        playbook_yaml = generate_playbook_from_recipe(
            str(recipe_file), cookbook_name, recipe_name
        )

        # Write output
        output_file = output_dir / f"{recipe_name}.yml"
        output_file.write_text(playbook_yaml)

        click.echo(f"✓ Playbook written to: {output_file}")
        click.echo(f"  Size: {len(playbook_yaml)} bytes")

    except Exception as e:
        click.echo(f"Error converting recipe: {e}", err=True)
        sys.exit(1)


@cli.command("assess-cookbook")
@click.option(
    "--cookbook-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Chef cookbook directory",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="json",
    help="Output format (default: json)",
)
def assess_cookbook(cookbook_path: str, output_format: str) -> None:
    """
    Assess a Chef cookbook for migration complexity.

    Analyzes the cookbook and provides complexity level, recipe/resource counts,
    estimated migration effort, and recommendations. Used by Terraform provider.

    Example:
        souschef assess-cookbook --cookbook-path /chef/cookbooks/nginx --format json

    """
    try:
        cookbook_dir = Path(cookbook_path)
        if not cookbook_dir.exists():
            click.echo(
                f"Error: Cookbook path does not exist: {cookbook_path}",
                err=True,
            )
            sys.exit(1)

        if not cookbook_dir.is_dir():
            click.echo(f"Error: {cookbook_path} is not a directory", err=True)
            sys.exit(1)

        # Run assessment
        result = assess_chef_migration_complexity(str(cookbook_path))

        if output_format == "json":
            # Output raw JSON for Terraform provider
            click.echo(result)
        else:
            # Parse JSON and display nicely for humans
            try:
                data = json.loads(result)
                click.echo(f"\nCookbook: {cookbook_dir.name}")
                click.echo("=" * 50)
                click.echo(f"Complexity: {data.get('complexity', 'Unknown')}")
                click.echo(f"Recipe Count: {data.get('recipe_count', 0)}")
                click.echo(f"Resource Count: {data.get('resource_count', 0)}")
                click.echo(f"Estimated Hours: {data.get('estimated_hours', 0.0)}")
                recommendations = data.get("recommendations", "None")
                click.echo(f"\nRecommendations:\n{recommendations}")
            except json.JSONDecodeError:
                click.echo(result)

    except Exception as e:
        click.echo(f"Error assessing cookbook: {e}", err=True)
        sys.exit(1)


def main() -> NoReturn:
    """Run the CLI."""
    cli()
    sys.exit(0)


if __name__ == "__main__":
    main()
