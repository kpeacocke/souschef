"""
Command-line interface for SousChef.

Provides easy access to Chef cookbook parsing and conversion tools.
"""

import json
import sys
from pathlib import Path
from typing import Any, NoReturn, TypedDict

import click

from souschef import __version__
from souschef.ansible_upgrade import (
    UpgradePlan,
    assess_ansible_environment,
    detect_python_version,
    generate_upgrade_plan,
    validate_collection_compatibility,
)
from souschef.converters.playbook import generate_playbook_from_recipe
from souschef.core.ansible_versions import format_version_display, get_eol_status
from souschef.core.logging import configure_logging
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
    _safe_join,
    safe_write_text,
)
from souschef.migration_config import (
    DeploymentTarget,
    MigrationConfig,
    MigrationStandard,
    ValidationTool,
    get_migration_config_from_user,
)
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


def _validate_user_path(path_input: str | None) -> Path:
    """
    Validate and sanitize user-supplied path input.

    Ensures path is safe to use by resolving and validating it exists.

    Args:
        path_input: User-supplied path string or None.

    Returns:
        Validated absolute path as Path object.

    Raises:
        ValueError: If path is invalid or unsafe.

    """
    if path_input is None:
        # Use current directory as safe default
        return Path.cwd()

    try:
        # Resolve to absolute path and validate it exists
        validated_path = Path(path_input).resolve()

        if not validated_path.exists():
            raise ValueError(f"Path does not exist: {validated_path}")

        return validated_path
    except OSError as e:
        raise ValueError(f"Invalid path: {e}") from e


class ConversionResults(TypedDict):
    """Type definition for cookbook conversion results."""

    cookbook_name: str
    recipes: dict[str, str]
    templates: dict[str, str]
    attributes: dict[str, str]
    metadata: dict[str, str] | str


# CI/CD job description constants
CI_JOB_LINT = "  • Lint (cookstyle/foodcritic)"
CI_JOB_UNIT_TESTS = "  • Unit Tests (ChefSpec)"
CI_JOB_INTEGRATION_TESTS = "  • Integration Tests (Test Kitchen)"

# File name constants
METADATA_FILENAME = "metadata.rb"


def _resolve_output_path(output: str | None, default_path: Path) -> Path:
    """Normalise and validate output paths for generated files."""
    try:
        workspace_root = _get_workspace_root()
        if output:
            resolved_path = _ensure_within_base_path(
                _normalize_path(output), workspace_root
            )
        else:
            resolved_path = _ensure_within_base_path(
                default_path.resolve(), workspace_root
            )
    except ValueError as exc:  # noqa: TRY003
        click.echo(f"Invalid output path: {exc}", err=True)
        raise click.Abort() from exc

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path


def _safe_write_file(content: str, output: str | None, default_path: Path) -> Path:
    """
    Safely write content to a validated file path.

    Args:
        content: Content to write to file.
        output: Optional user-specified output path.
        default_path: Default path if output not specified.

    Returns:
        The path where content was written.

    Raises:
        click.Abort: If path validation or write fails.

    """
    validated_path = _resolve_output_path(output, default_path)
    try:
        # Separate validation from write to satisfy SonarQube path construction rules
        with validated_path.open("w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        click.echo(f"Error writing file: {e}", err=True)
        raise click.Abort() from e
    return validated_path


@click.group()
@click.version_option(version=__version__, prog_name="souschef")
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
    Analyse an entire Chef cookbook.

    COOKBOOK_PATH: Path to the cookbook root directory

    This command analyses the cookbook structure, metadata, recipes,
    attributes, templates, and custom resources.
    """
    cookbook_dir = Path(cookbook_path)

    click.echo(f"Analysing cookbook: {cookbook_dir.name}")
    click.echo("=" * 50)

    # Parse metadata
    metadata_file = cookbook_dir / METADATA_FILENAME
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

    # Convert and save if output directory specified
    if output and not dry_run:
        _save_cookbook_conversion(cookbook_dir, output)
    elif output and dry_run:
        click.echo(f"\n💾 Would save results to: {output}")
        click.echo("(Dry run - no files will be written)")


def _save_cookbook_conversion(cookbook_dir: Path, output_path: str) -> None:
    """
    Convert and save cookbook to Ansible format.

    Args:
        cookbook_dir: Path to Chef cookbook directory
        output_path: Path to output directory for Ansible files

    """
    workspace_root = _get_workspace_root()
    output_dir = _ensure_within_base_path(_normalize_path(output_path), workspace_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"\n💾 Saving conversion to: {output_dir}")
    click.echo("=" * 50)

    results: ConversionResults = {
        "cookbook_name": cookbook_dir.name,
        "recipes": {},
        "templates": {},
        "attributes": {},
        "metadata": {},
    }

    # Convert metadata
    metadata_file = cookbook_dir / METADATA_FILENAME
    if metadata_file.exists():
        click.echo("Converting metadata...")
        metadata_result = read_cookbook_metadata(str(metadata_file))
        results["metadata"] = metadata_result

        # Save metadata as README
        readme_path = _safe_join(output_dir, "README.md")
        readme_content = (
            f"# {cookbook_dir.name} - Converted from Chef\n\n"
            "## Metadata\n\n"
            f"{metadata_result}"
        )
        safe_write_text(readme_path, output_dir, readme_content)
        click.echo(f"  ✓ Saved metadata to {readme_path}")

    # Convert recipes to playbooks
    recipes_dir = cookbook_dir / "recipes"
    playbooks_dir = _safe_join(output_dir, "playbooks")
    if recipes_dir.exists():
        playbooks_dir.mkdir(parents=True, exist_ok=True)
        click.echo("\nConverting recipes to playbooks...")

        for recipe_file in recipes_dir.glob("*.rb"):
            playbook_name = recipe_file.stem
            playbook_content = generate_playbook_from_recipe(str(recipe_file))

            playbook_path = _safe_join(playbooks_dir, f"{playbook_name}.yml")
            safe_write_text(playbook_path, output_dir, playbook_content)

            results["recipes"][playbook_name] = str(playbook_path)
            click.echo(f"  ✓ Converted {recipe_file.name} → {playbook_path}")

    # Convert templates
    templates_dir = cookbook_dir / "templates" / "default"
    output_templates_dir = _safe_join(output_dir, "templates")
    if templates_dir.exists():
        from souschef.converters.template import convert_template_file

        output_templates_dir.mkdir(parents=True, exist_ok=True)
        click.echo("\nConverting ERB templates to Jinja2...")

        for template_file in templates_dir.glob("*.erb"):
            template_result = convert_template_file(str(template_file))

            if template_result.get("success"):
                jinja_name = template_file.stem + ".j2"
                jinja_path = _safe_join(output_templates_dir, jinja_name)
                safe_write_text(
                    jinja_path,
                    output_dir,
                    template_result.get("jinja2_template", ""),
                )

                results["templates"][template_file.name] = str(jinja_path)
                click.echo(f"  ✓ Converted {template_file.name} → {jinja_path}")
            else:
                click.echo(f"  ✗ Failed to convert {template_file.name}")

    # Parse and save attributes
    attributes_dir = cookbook_dir / "attributes"
    if attributes_dir.exists():
        vars_dir = _safe_join(output_dir, "vars")
        vars_dir.mkdir(parents=True, exist_ok=True)
        click.echo("\nExtracting attributes...")

        for attr_file in attributes_dir.glob("*.rb"):
            attr_result = parse_attributes(str(attr_file))

            # Save as YAML vars file
            vars_name = attr_file.stem + ".yml"
            vars_path = _safe_join(vars_dir, vars_name)
            vars_content = (
                "# Converted from Chef attributes\n"
                f"# Source: {attr_file.name}\n\n"
                f"{attr_result}"
            )
            safe_write_text(vars_path, output_dir, vars_content)

            results["attributes"][attr_file.name] = str(vars_path)
            click.echo(f"  ✓ Extracted {attr_file.name} → {vars_path}")

    # Save conversion summary
    summary_path = _safe_join(output_dir, "conversion_summary.json")
    safe_write_text(summary_path, output_dir, json.dumps(results, indent=2))

    click.echo("\n✅ Conversion complete!")
    click.echo(f"📁 Output directory: {output_dir}")
    click.echo(f"📄 Summary: {summary_path}")


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

    This command analyses the cookbook for CI patterns (Test Kitchen,
    lint tools, test suites) and generates an appropriate Jenkinsfile
    with stages for linting, testing, and convergence.

    Examples:
      souschef generate-jenkinsfile ./mycookbook

      souschef generate-jenkinsfile ./mycookbook -o Jenkinsfile.new

      souschef generate-jenkinsfile ./mycookbook --pipeline-type scripted

      souschef generate-jenkinsfile ./mycookbook --no-parallel

    """
    try:
        safe_cookbook_path = str(_normalize_path(cookbook_path))
        result = generate_jenkinsfile_from_chef(
            cookbook_path=safe_cookbook_path,
            pipeline_type=pipeline_type,
            enable_parallel="yes" if parallel else "no",
        )

        # Determine output path
        _resolve_output_path(output, default_path=Path.cwd() / "Jenkinsfile")

        # Write Jenkinsfile using safe write helper
        written_path = _safe_write_file(
            result, output, default_path=Path.cwd() / "Jenkinsfile"
        )
        click.echo(f"✓ Generated {pipeline_type} Jenkinsfile: {written_path}")

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

    This command analyses the cookbook for CI patterns (Test Kitchen,
    lint tools, test suites) and generates an appropriate GitLab CI
    configuration with jobs for linting, testing, and convergence.

    Examples:
      souschef generate-gitlab-ci ./mycookbook

      souschef generate-gitlab-ci ./mycookbook -o .gitlab-ci.test.yml

      souschef generate-gitlab-ci ./mycookbook --no-cache

      souschef generate-gitlab-ci ./mycookbook --no-artifacts

    """
    try:
        safe_cookbook_path = str(_normalize_path(cookbook_path))
        result = generate_gitlab_ci_from_chef(
            cookbook_path=safe_cookbook_path,
            enable_cache="yes" if cache else "no",
            enable_artifacts="yes" if artifacts else "no",
        )

        # Write GitLab CI config using safe write helper
        written_path = _safe_write_file(
            result, output, default_path=Path.cwd() / ".gitlab-ci.yml"
        )
        click.echo(f"✓ Generated GitLab CI configuration: {written_path}")

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

    This command analyses the cookbook for CI patterns (Test Kitchen,
    lint tools, test suites) and generates an appropriate GitHub Actions
    workflow with jobs for linting, testing, and convergence.

    Examples:
      souschef generate-github-workflow ./mycookbook

      souschef generate-github-workflow ./mycookbook -o .github/workflows/test.yml

      souschef generate-github-workflow ./mycookbook --no-cache

      souschef generate-github-workflow ./mycookbook --workflow-name "CI Pipeline"

    """
    try:
        safe_cookbook_path = str(_normalize_path(cookbook_path))
        result = generate_github_workflow_from_chef(
            cookbook_path=safe_cookbook_path,
            workflow_name=workflow_name,
            enable_cache="yes" if cache else "no",
            enable_artifacts="yes" if artifacts else "no",
        )

        # Determine output path
        if output:
            output_path = _resolve_output_path(output, Path.cwd() / "ci.yml")
        else:
            workflows_dir = Path.cwd() / ".github" / "workflows"
            workflows_dir.mkdir(parents=True, exist_ok=True)
            output_path = _resolve_output_path(None, workflows_dir / "ci.yml")

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

    This command analyses the performance of parsing all cookbook components
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
        # Validate input paths
        cookbook_dir = _validate_user_path(cookbook_path)

        # Validate output path (doesn't need to exist, but validate parent)
        try:
            output_dir = Path(output_path).resolve()
            # Check parent directory is accessible
            parent = output_dir.parent
            if not parent.exists():
                msg = f"Output parent directory does not exist: {parent}"
                raise ValueError(msg)
        except OSError as e:
            raise ValueError(f"Invalid output path: {e}") from e

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
        playbook_yaml = generate_playbook_from_recipe(str(recipe_file))

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

    Analyses the cookbook and provides complexity level, recipe/resource counts,
    estimated migration effort, and recommendations. Used by Terraform provider.

    Example:
        souschef assess-cookbook --cookbook-path /chef/cookbooks/nginx --format json

    """
    try:
        # Validate path before using it
        cookbook_dir = _validate_user_path(cookbook_path)
        if not cookbook_dir.is_dir():
            click.echo(f"Error: {cookbook_path} is not a directory", err=True)
            sys.exit(1)

        # Analyse cookbook
        analysis = _analyse_cookbook_for_assessment(cookbook_dir)

        if output_format == "json":
            click.echo(json.dumps(analysis))
        else:
            _display_assessment_text(cookbook_dir.name, analysis)

    except Exception as e:
        click.echo(f"Error assessing cookbook: {e}", err=True)
        sys.exit(1)


def _analyse_cookbook_for_assessment(cookbook_dir: Path) -> dict:
    """Analyse cookbook and return assessment data."""
    recipe_count = 0
    resource_count = 0
    recipes_dir = cookbook_dir / "recipes"

    if recipes_dir.exists():
        recipe_files = list(recipes_dir.glob("*.rb"))
        recipe_count = len(recipe_files)
        for recipe_file in recipe_files:
            content = recipe_file.read_text()
            resource_count += content.count(" do\n") + content.count(" do\r\n")

    # Determine complexity
    if recipe_count == 0:
        complexity = "Low"
        estimated_hours = 0.5
    elif recipe_count <= 3 and resource_count <= 10:
        complexity = "Low"
        estimated_hours = resource_count * 0.5
    elif recipe_count <= 10 and resource_count <= 50:
        complexity = "Medium"
        estimated_hours = resource_count * 1.0
    else:
        complexity = "High"
        estimated_hours = resource_count * 1.5

    recommendations = (
        f"Cookbook has {recipe_count} recipes with {resource_count} resources. "
    )
    if complexity == "Low":
        recommendations += "Straightforward migration recommended."
    elif complexity == "Medium":
        recommendations += "Moderate effort required. Consider phased approach."
    else:
        recommendations += (
            "Complex migration. Recommend incremental migration strategy."
        )

    return {
        "complexity": complexity,
        "recipe_count": recipe_count,
        "resource_count": resource_count,
        "estimated_hours": estimated_hours,
        "recommendations": recommendations,
    }


def _display_assessment_text(cookbook_name: str, analysis: dict) -> None:
    """Display assessment in human-readable text format."""
    click.echo(f"\nCookbook: {cookbook_name}")
    click.echo("=" * 50)
    click.echo(f"Complexity: {analysis['complexity']}")
    click.echo(f"Recipe Count: {analysis['recipe_count']}")
    click.echo(f"Resource Count: {analysis['resource_count']}")
    click.echo(f"Estimated Hours: {analysis['estimated_hours']}")
    click.echo(f"\nRecommendations:\n{analysis['recommendations']}")


@cli.command("convert-habitat")
@click.option(
    "--plan-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Habitat plan.sh file",
)
@click.option(
    "--output-path",
    required=True,
    type=click.Path(),
    help="Directory where Dockerfile will be written",
)
@click.option(
    "--base-image",
    default="ubuntu:latest",
    help="Base Docker image to use (default: ubuntu:latest)",
)
def convert_habitat(plan_path: str, output_path: str, base_image: str) -> None:
    r"""
    Convert a Chef Habitat plan to a Dockerfile.

    Analyses the Habitat plan.sh file and generates an equivalent Dockerfile
    for containerised deployment. Used by Terraform provider.

    Example:
        souschef convert-habitat --plan-path /hab/plans/nginx/plan.sh \
            --output-path /docker/nginx --base-image ubuntu:22.04

    """
    try:
        # Validate input paths
        plan_file = _validate_user_path(plan_path)
        if not plan_file.is_file():
            click.echo(f"Error: {plan_path} is not a file", err=True)
            sys.exit(1)

        # Validate output path
        try:
            output_dir = Path(output_path).resolve()
            parent = output_dir.parent
            if not parent.exists():
                msg = f"Output parent directory does not exist: {parent}"
                raise ValueError(msg)
        except OSError as e:
            raise ValueError(f"Invalid output path: {e}") from e

        output_dir.mkdir(parents=True, exist_ok=True)

        # Call server function to convert
        from souschef.server import convert_habitat_to_dockerfile

        dockerfile_content = convert_habitat_to_dockerfile(str(plan_path), base_image)

        # Write Dockerfile
        dockerfile_path = output_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)

        click.echo(f"Successfully converted Habitat plan to {dockerfile_path}")
        click.echo(f"Dockerfile size: {len(dockerfile_content)} bytes")

    except Exception as e:
        click.echo(f"Error converting Habitat plan: {e}", err=True)
        sys.exit(1)


@cli.command("convert-inspec")
@click.option(
    "--profile-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the InSpec profile directory",
)
@click.option(
    "--output-path",
    required=True,
    type=click.Path(),
    help="Directory where converted tests will be written",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["testinfra", "serverspec", "goss", "ansible"]),
    default="testinfra",
    help="Output test framework format (default: testinfra)",
)
def convert_inspec(profile_path: str, output_path: str, output_format: str) -> None:
    r"""
    Convert a Chef InSpec profile to various test frameworks.

    Analyses the InSpec profile and generates equivalent tests in the
    specified framework. Supports TestInfra, Serverspec, Goss, and Ansible.

    Example:
        souschef convert-inspec --profile-path /inspec/profiles/linux \
            --output-path /tests/testinfra --format testinfra

    """
    try:
        # Validate input paths
        profile_dir = _validate_user_path(profile_path)
        if not profile_dir.is_dir():
            click.echo(f"Error: {profile_path} is not a directory", err=True)
            sys.exit(1)

        # Validate output path
        try:
            output_dir = Path(output_path).resolve()
            parent = output_dir.parent
            if not parent.exists():
                msg = f"Output parent directory does not exist: {parent}"
                raise ValueError(msg)
        except OSError as e:
            raise ValueError(f"Invalid output path: {e}") from e

        output_dir.mkdir(parents=True, exist_ok=True)

        # Call server function to convert
        from souschef.server import convert_inspec_to_test

        test_content = convert_inspec_to_test(str(profile_path), output_format)

        # Determine output filename based on format
        filename_map = {
            "testinfra": "test_spec.py",
            "serverspec": "spec_helper.rb",
            "goss": "goss.yaml",
            "ansible": "assert.yml",
        }
        output_filename = filename_map.get(output_format, "test.txt")

        # Write test file
        test_file_path = output_dir / output_filename
        test_file_path.write_text(test_content)

        click.echo(f"Successfully converted InSpec profile to {output_format} format")
        click.echo(f"Test file: {test_file_path}")
        click.echo(f"File size: {len(test_content)} bytes")

    except Exception as e:
        click.echo(f"Error converting InSpec profile: {e}", err=True)
        sys.exit(1)


@cli.command("convert-cookbook")
@click.option(
    "--cookbook-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Chef cookbook directory",
)
@click.option(
    "--output-path",
    required=True,
    type=click.Path(),
    help="Directory where the Ansible role will be created",
)
@click.option(
    "--assessment-file",
    type=click.Path(exists=True),
    help="Path to JSON file with assessment results for optimization",
)
@click.option(
    "--role-name",
    help="Name for the Ansible role (defaults to cookbook name)",
)
@click.option(
    "--skip-templates",
    is_flag=True,
    help="Skip conversion of ERB templates to Jinja2",
)
@click.option(
    "--skip-attributes",
    is_flag=True,
    help="Skip conversion of attributes to Ansible variables",
)
@click.option(
    "--skip-recipes",
    is_flag=True,
    help="Skip conversion of recipes to Ansible tasks",
)
def convert_cookbook(
    cookbook_path: str,
    output_path: str,
    assessment_file: str | None = None,
    role_name: str | None = None,
    skip_templates: bool = False,
    skip_attributes: bool = False,
    skip_recipes: bool = False,
) -> None:
    r"""
    Convert an entire Chef cookbook to a complete Ansible role.

    Performs comprehensive conversion including recipes, templates, attributes,
    and proper Ansible role structure. Can use assessment data for optimization.

    Example:
        souschef convert-cookbook --cookbook-path /chef/cookbooks/nginx \\
                                 --output-path /ansible/roles \\
                                 --assessment-file assessment.json

    """
    try:
        # Validate input paths
        _validate_user_path(cookbook_path)

        # Validate output path
        try:
            output_dir = Path(output_path).resolve()
            parent = output_dir.parent
            if not parent.exists():
                msg = f"Output parent directory does not exist: {parent}"
                raise ValueError(msg)
        except OSError as e:
            raise ValueError(f"Invalid output path: {e}") from e

        # Load assessment data if provided
        assessment_data = ""
        if assessment_file:
            assessment_path = _validate_user_path(assessment_file)
            assessment_data = assessment_path.read_text()

        # Call server function
        from souschef.server import convert_cookbook_comprehensive

        result = convert_cookbook_comprehensive(
            cookbook_path=cookbook_path,
            output_path=output_path,
            assessment_data=assessment_data,
            include_templates=not skip_templates,
            include_attributes=not skip_attributes,
            include_recipes=not skip_recipes,
            role_name=role_name or "",
        )

        click.echo(result)

    except Exception as e:
        click.echo(f"Error converting cookbook: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--port", default=8501, help="Port to run the Streamlit app on")
def ui(port: int) -> None:
    """
    Launch the SousChef Visual Migration Planning Interface.

    Opens a web-based interface for interactive Chef to Ansible migration planning,
    cookbook analysis, and visualization.
    """
    import subprocess

    try:
        # Launch Streamlit app
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "souschef/ui/app.py",
            "--server.port",
            str(port),
        ]
        click.echo(f"Starting SousChef UI on http://localhost:{port}")
        click.echo("Press Ctrl+C to stop the server")

        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        click.echo(f"Error starting UI: {e}", err=True)
        sys.exit(1)
    except ImportError:
        click.echo(
            "Streamlit is not installed. Install with: pip install streamlit", err=True
        )
        sys.exit(1)


@cli.command("validate-chef-server")
@click.option("--server-url", prompt="Chef Server URL", help="Chef Server base URL")
@click.option("--node-name", default="admin", help="Chef node name for authentication")
def validate_chef_server(server_url: str, node_name: str) -> None:
    """
    Validate Chef Server connectivity and configuration.

    Tests the connection to the Chef Server REST API to ensure it's
    reachable and properly configured.
    """
    click.echo("🔍 Validating Chef Server connection...")
    from souschef.core.chef_server import _validate_chef_server_connection

    success, message = _validate_chef_server_connection(server_url, node_name)

    if success:
        click.echo(f"✅ {message}")
    else:
        click.echo(f"❌ {message}", err=True)
        sys.exit(1)


def _display_node_text(node: dict) -> None:
    """Display a single node's information in text format."""
    click.echo(f"\n  📍 {node.get('name', 'unknown')}")
    click.echo(f"     Environment: {node.get('environment', '_default')}")
    click.echo(f"     Platform: {node.get('platform', 'unknown')}")
    if node.get("ipaddress"):
        click.echo(f"     IP: {node['ipaddress']}")
    if node.get("fqdn"):
        click.echo(f"     FQDN: {node['fqdn']}")
    if node.get("roles"):
        click.echo(f"     Roles: {', '.join(node['roles'])}")


def _output_chef_nodes(nodes: list, output_json: bool) -> None:
    """Output nodes in requested format."""
    if output_json:
        click.echo(json.dumps(nodes, indent=2))
    else:
        for node in nodes:
            _display_node_text(node)


@cli.command("query-chef-nodes")
@click.option("--search-query", default="*:*", help="Chef search query for nodes")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def query_chef_nodes(search_query: str, output_json: bool) -> None:
    """
    Query Chef Server for nodes matching search criteria.

    Retrieves nodes from Chef Server that match the provided search query,
    extracting role assignments, environment, platform, and IP address
    information for dynamic inventory generation.
    """
    import os

    if not os.environ.get("CHEF_SERVER_URL"):
        click.echo("❌ CHEF_SERVER_URL not set", err=True)
        sys.exit(1)

    click.echo(f"🔎 Querying Chef Server for nodes matching: {search_query}")

    from souschef.converters.playbook import get_chef_nodes

    try:
        nodes = get_chef_nodes(search_query)

        if not nodes:
            click.echo("ℹ️  No nodes found matching the search query")
            return

        click.echo(f"Found {len(nodes)} nodes:")
        _output_chef_nodes(nodes, output_json)
    except Exception as e:
        click.echo(f"❌ Error querying Chef Server: {e}", err=True)
        sys.exit(1)


@cli.command("convert-template-ai")
@click.argument("erb_path", type=click.Path(exists=True))
@click.option("--ai/--no-ai", default=True, help="Use AI enhancement")
@click.option("--output", type=click.Path(), help="Output path for template")
def convert_template_ai(erb_path: str, ai: bool, output: str | None) -> None:
    """
    Convert an ERB template to Jinja2 with optional AI assistance.

    Converts Chef ERB templates to Ansible Jinja2 format with optional
    AI-based validation and improvement for complex Ruby logic.
    """
    click.echo(f"🔄 Converting template: {erb_path}")
    if ai:
        click.echo("✨ Using AI enhancement for complex conversions")
    else:
        click.echo("📝 Using rule-based conversion only")

    from souschef.converters.template import convert_template_with_ai

    try:
        result = convert_template_with_ai(erb_path, ai_service=None)

        if result.get("success"):
            method = result.get("conversion_method", "unknown")
            click.echo(f"✅ Conversion successful ({method})")

            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result.get("jinja2_output", ""))
                click.echo(f"💾 Converted template saved to: {output}")
            else:
                click.echo("\nConverted Template:")
                click.echo("-" * 50)
                click.echo(result.get("jinja2_output", ""))
                click.echo("-" * 50)

            if result.get("warnings"):
                click.echo("\n⚠️  Warnings:")
                for warning in result["warnings"]:
                    click.echo(f"  - {warning}")
        else:
            error_msg = result.get("error", "Unknown error")
            click.echo(f"❌ Conversion failed: {error_msg}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error converting template: {e}", err=True)
        sys.exit(1)


def _build_config_from_cli_args(
    deployment_target: str | None,
    migration_standard: str | None,
    inventory_source: str | None,
    validation_tools: tuple[str, ...],
    python_version: str | None,
    ansible_version: str | None,
) -> MigrationConfig:
    """Build migration config from CLI arguments."""
    config = MigrationConfig()

    if deployment_target:
        config.deployment_target = DeploymentTarget(deployment_target)
    if migration_standard:
        config.migration_standard = MigrationStandard(migration_standard)
    if inventory_source:
        config.inventory_source = inventory_source
    if validation_tools:
        config.validation_tools = [ValidationTool(tool) for tool in validation_tools]
    if python_version:
        config.target_python_version = python_version
    if ansible_version:
        config.target_ansible_version = ansible_version

    return config


def _output_migration_config(config_dict: dict, output: str | None) -> None:
    """Output migration configuration to file or stdout."""
    if output:
        # Save to file
        output_path = _resolve_output_path(output, Path("migration-config.json"))
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2)
        click.echo(f"✅ Configuration saved to: {output_path}")
    else:
        # Print to stdout
        click.echo("\n" + "=" * 60)
        click.echo("Migration Configuration")
        click.echo("=" * 60)
        click.echo(json.dumps(config_dict, indent=2))
        click.echo("=" * 60)


@cli.command("configure-migration")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save configuration to JSON file (default: print to stdout)",
)
@click.option(
    "--deployment-target",
    type=click.Choice(["app", "awx", "aap", "native"]),
    help="Target deployment platform (app/awx/aap/native)",
)
@click.option(
    "--migration-standard",
    type=click.Choice(["standard", "flat", "hybrid"]),
    help="Migration strategy (standard/flat/hybrid)",
)
@click.option(
    "--inventory-source",
    help="Inventory source (e.g., chef-server, static-file)",
)
@click.option(
    "--validation-tools",
    multiple=True,
    type=click.Choice(["tox-ansible", "molecule", "ansible-lint", "custom"]),
    help="Validation tools to use (can specify multiple)",
)
@click.option(
    "--python-version",
    help="Target Python version (e.g., 3.9, 3.10)",
)
@click.option(
    "--ansible-version",
    help="Target Ansible version (e.g., 2.13, 2.14)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Run interactive questionnaire (ignores other options)",
)
def configure_migration(
    output: str | None,
    deployment_target: str | None,
    migration_standard: str | None,
    inventory_source: str | None,
    validation_tools: tuple[str, ...],
    python_version: str | None,
    ansible_version: str | None,
    interactive: bool,
) -> None:
    """
    Configure Chef to Ansible migration settings.

    Run interactively with --interactive/-i flag, or provide specific
    configuration options via command-line arguments.

    Examples:
        # Interactive mode (recommended)
        souschef configure-migration --interactive

        # Non-interactive with specific options
        souschef configure-migration --deployment-target awx \
            --migration-standard standard \
            --validation-tools ansible-lint \
            --validation-tools molecule

        # Save configuration to file
        souschef configure-migration -i --output migration-config.json

    """
    try:
        if interactive or not any(
            [
                deployment_target,
                migration_standard,
                inventory_source,
                validation_tools,
                python_version,
                ansible_version,
            ]
        ):
            # Run interactive questionnaire
            config = get_migration_config_from_user()
        else:
            # Build config from CLI arguments
            config = _build_config_from_cli_args(
                deployment_target,
                migration_standard,
                inventory_source,
                validation_tools,
                python_version,
                ansible_version,
            )

        # Convert to dict for output
        config_dict = config.to_dict()
        _output_migration_config(config_dict, output)

    except Exception as e:
        click.echo(f"❌ Error configuring migration: {e}", err=True)
        sys.exit(1)


@cli.group()
def history() -> None:
    """Manage analysis and conversion history."""


@history.command(name="list")
@click.option(
    "--type",
    "history_type",
    type=click.Choice(["analysis", "conversion", "both"]),
    default="both",
    help="Type of history to list",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of results to display",
)
@click.option(
    "--cookbook",
    default=None,
    help="Filter by cookbook name",
)
def history_list(history_type: str, limit: int, cookbook: str | None) -> None:
    """List analysis and conversion history."""
    from souschef.storage import get_storage_manager

    storage_manager = get_storage_manager()

    if history_type in ["analysis", "both"]:
        click.echo("\n" + "=" * 80)
        click.echo("Analysis History")
        click.echo("=" * 80)

        analyses = storage_manager.get_analysis_history(
            cookbook_name=cookbook, limit=limit
        )

        if not analyses:
            click.echo("No analysis history found.")
        else:
            for a in analyses:
                time_saved = a.estimated_hours - a.estimated_hours_with_souschef
                click.echo(
                    f"ID: {a.id} | {a.cookbook_name} v{a.cookbook_version} | "
                    f"Complexity: {a.complexity} | "
                    f"Manual: {a.estimated_hours:.1f}h | "
                    f"AI: {a.estimated_hours_with_souschef:.1f}h | "
                    f"Saved: {time_saved:.1f}h | "
                    f"Date: {a.created_at}"
                )

    if history_type in ["conversion", "both"]:
        click.echo("\n" + "=" * 80)
        click.echo("Conversion History")
        click.echo("=" * 80)

        conversions = storage_manager.get_conversion_history(
            cookbook_name=cookbook, limit=limit
        )

        if not conversions:
            click.echo("No conversion history found.")
        else:
            for c in conversions:
                click.echo(
                    f"ID: {c.id} | {c.cookbook_name} | "
                    f"Type: {c.output_type} | "
                    f"Status: {c.status} | "
                    f"Files: {c.files_generated} | "
                    f"Date: {c.created_at}"
                )

    click.echo("")


@history.command(name="delete")
@click.option(
    "--type",
    "history_type",
    type=click.Choice(["analysis", "conversion"]),
    required=True,
    help="Type of record to delete",
)
@click.option(
    "--id",
    "record_id",
    type=int,
    required=True,
    help="ID of the record to delete",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def history_delete(history_type: str, record_id: int, yes: bool) -> None:
    """Delete an analysis or conversion from history."""
    from souschef.storage import get_storage_manager

    storage_manager = get_storage_manager()

    # Confirm deletion unless --yes flag is used
    if not yes and not click.confirm(
        f"Are you sure you want to delete {history_type} record {record_id}?"
    ):
        click.echo("Deletion cancelled.")
        return

    try:
        if history_type == "analysis":
            success = storage_manager.delete_analysis(record_id)
            msg = "Analysis and associated conversions deleted successfully!"
        else:
            success = storage_manager.delete_conversion(record_id)
            msg = "Conversion deleted successfully!"

        if success:
            click.echo(f"✅ {msg}")
        else:
            click.echo(f"❌ Failed to delete {history_type} record {record_id}.")
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error deleting {history_type}: {e}", err=True)
        sys.exit(1)


@cli.group()
def ansible() -> None:
    """
    Manage Ansible upgrade planning and validation.

    Provides tools to assess Ansible environments, plan upgrades,
    validate collection compatibility, and generate testing strategies.
    """


@ansible.command("assess")
@click.option(
    "--environment-path",
    type=click.Path(exists=True),
    help="Path to Ansible environment or venv (detects current if not provided)",
)
def ansible_assess(environment_path: str | None) -> None:
    """
    Assess the current Ansible environment.

    Analyses the Ansible version, Python version, installed collections,
    and environment configuration to provide a baseline for upgrade planning.

    Example:
        souschef ansible assess --environment-path /opt/ansible/venv

    """
    try:
        # Validate path before using it
        validated_path = _validate_user_path(environment_path or None)

        click.echo("Assessing Ansible environment...")
        assessment = assess_ansible_environment(str(validated_path))

        click.echo("\n" + "=" * 60)
        click.echo("Ansible Environment Assessment")
        click.echo("=" * 60)
        current = assessment.get("current_version", "Unknown")

        # Try to format with both version schemas if it's a valid version
        try:
            version_display = format_version_display(
                current, include_named=True, include_aap=False
            )
            click.echo(f"\nCurrent Ansible Version: {version_display}")
        except (ValueError, KeyError):
            click.echo(f"\nCurrent Ansible Version: {current}")

        full_version = assessment.get("current_version_full", "Unknown")
        click.echo(f"Full Version: {full_version}")
        python_ver = assessment.get("python_version", "Unknown")
        click.echo(f"Python Version: {python_ver}")

        if "installed_collections" in assessment:
            collections = assessment["installed_collections"]
            click.echo(f"\nInstalled Collections: {len(collections)}")
            for collection in collections[:10]:
                click.echo(f"  - {collection}")
            if len(collections) > 10:
                remaining = len(collections) - 10
                click.echo(f"  ... and {remaining} more")

        if "eol_date" in assessment:
            eol = assessment["eol_date"]
            click.echo(f"\nCurrent Version EOL: {eol}")

        if "warnings" in assessment:
            click.echo("\nWarnings:")
            for warning in assessment["warnings"]:
                click.echo(f"  - {warning}")

        click.echo("\nAssessment complete")

    except Exception as e:
        click.echo(f"Error assessing environment: {e}", err=True)
        sys.exit(1)


def _display_plan_section(title: str, items: list[str], icon: str = "-") -> None:
    """Display a section of plan items."""
    if not items:
        return
    click.echo(f"\n{title}:")
    for item in items[:5]:
        click.echo(f"  {icon} {item}")
    if len(items) > 5:
        click.echo(f"  ... and {len(items) - 5} more")


def _display_upgrade_plan(plan: UpgradePlan) -> None:
    """
    Display upgrade plan details.

    Args:
        plan: Upgrade plan dictionary.

    """
    upgrade_path = plan.get("upgrade_path")
    if isinstance(upgrade_path, dict):
        click.echo("\nUpgrade Path:")
        from_version = upgrade_path.get("from_version", "unknown")
        to_version = upgrade_path.get("to_version", "unknown")
        click.echo(f"  From: {from_version}")
        click.echo(f"  To: {to_version}")

        intermediate = upgrade_path.get("intermediate_versions", [])
        if isinstance(intermediate, list) and intermediate:
            click.echo("  Intermediate Versions:")
            for version in intermediate:
                click.echo(f"    - {version}")

        breaking = upgrade_path.get("breaking_changes", [])
        if isinstance(breaking, list) and breaking:
            _display_plan_section("Breaking Changes", breaking, "-")

        collection_updates = upgrade_path.get("collection_updates_needed", {})
        if isinstance(collection_updates, dict) and collection_updates:
            click.echo("\nCollection Updates Required:")
            click.echo(f"  Total: {len(collection_updates)}")

        effort = upgrade_path.get("estimated_effort_days")
        if effort is not None:
            click.echo(f"\nEstimated Effort: {effort} days")


@ansible.command("plan")
@click.option(
    "--current-version",
    required=True,
    help="Current Ansible version (e.g., '2.9', '2.10', '5.0')",
)
@click.option(
    "--target-version",
    required=True,
    help="Target Ansible version (e.g., '6.0', '7.0')",
)
def ansible_plan(current_version: str, target_version: str) -> None:
    """
    Generate an Ansible upgrade plan.

    Creates a detailed upgrade plan including breaking changes, deprecated
    features, collection compatibility issues, and recommended testing
    strategies for moving between Ansible versions.

    Example:
        souschef ansible plan --current-version 5.0 --target-version 7.0

    """
    try:
        msg = f"Generating upgrade plan from {current_version} to {target_version}..."
        click.echo(msg)
        plan = generate_upgrade_plan(current_version, target_version)

        # Try to format versions with Named Ansible schema
        try:
            current_display = format_version_display(
                current_version, include_named=True, include_aap=False
            )
            target_display = format_version_display(
                target_version, include_named=True, include_aap=False
            )
            title = f"Upgrade Plan: {current_display} → {target_display}"
        except (ValueError, KeyError):
            title = f"Upgrade Plan: {current_version} → {target_version}"

        click.echo("\n" + "=" * 60)
        click.echo(title)
        click.echo("=" * 60)

        _display_upgrade_plan(plan)
        click.echo("\nPlan generated successfully")

    except Exception as e:
        click.echo(f"Error generating upgrade plan: {e}", err=True)
        sys.exit(1)


@ansible.command("eol")
@click.option(
    "--version",
    required=True,
    help="Ansible version to check (e.g., '5.0', '6.0')",
)
def ansible_eol(version: str) -> None:
    """
    Check Ansible version end-of-life (EOL) status.

    Shows when a specific Ansible version reaches end-of-life and whether
    it's still supported. Useful for planning upgrade timelines.

    Example:
        souschef ansible eol --version 5.0

    """
    try:
        status = get_eol_status(version)

        # Try to format with both version schemas
        try:
            version_display = format_version_display(
                version, include_named=True, include_aap=False
            )
        except (ValueError, KeyError):
            version_display = version

        click.echo("\n" + "=" * 60)
        click.echo(f"{version_display} EOL Status")
        click.echo("=" * 60)

        if status.get("is_eol"):
            click.echo("Status: END OF LIFE")
            click.echo(f"EOL Date: {status.get('eol_date', 'Unknown')}")
        else:
            click.echo("Status: SUPPORTED")
            click.echo(f"EOL Date: {status.get('eol_date', 'Unknown')}")

        if "support_level" in status:
            click.echo(f"Support Level: {status['support_level']}")

        click.echo("")

    except Exception as e:
        click.echo(f"❌ Error checking EOL status: {e}", err=True)
        sys.exit(1)


def _display_collection_section(title: str, collections: list[str]) -> None:
    """Display a section of collections."""
    if not collections:
        return
    click.echo(f"\n{title}: {len(collections)}")
    for collection in collections[:5]:
        click.echo(f"  - {collection}")
    if len(collections) > 5:
        click.echo(f"  ... and {len(collections) - 5} more")


def _display_validation_results(validation: dict[str, Any]) -> None:
    """
    Display collection validation results.

    Args:
        validation: Validation result dictionary.

    """
    compat = validation.get("compatible", [])
    if compat:
        _display_collection_section("Compatible Collections", compat)

    requires = validation.get("requires_update", [])
    if requires:
        _display_collection_section("Requires Update", requires)

    maybe = validation.get("may_require_update", [])
    if maybe:
        _display_collection_section("May Require Update", maybe)

    incompat = validation.get("incompatible", [])
    if incompat:
        _display_collection_section("Incompatible", incompat)


def _parse_collections_file(file_path: str) -> dict[str, str]:
    """
    Parse a collections file (requirements.yml).

    Extracts collection names and versions from a requirements.yml file.

    Args:
        file_path: Path to the requirements.yml or similar collections file.

    Returns:
        Dictionary mapping collection names to their versions.

    Raises:
        ValueError: If the file cannot be parsed or is missing required data.

    """
    try:
        import yaml
    except ImportError as e:
        msg = (
            "PyYAML is required to parse collections files. "
            "Install with: pip install pyyaml"
        )
        raise ValueError(msg) from e

    # Validate path before using it
    try:
        validated = Path(file_path).resolve()
        if not validated.exists():
            raise ValueError(f"File does not exist: {validated}")
        if not validated.is_file():
            raise ValueError(f"Path is not a file: {validated}")
    except OSError as e:
        raise ValueError(f"Invalid file path: {e}") from e

    path = validated
    try:
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except OSError as e:
        raise ValueError(f"Cannot read collections file: {e}") from e
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in collections file: {e}") from e

    if not data:
        raise ValueError("Collections file is empty")

    collections_dict = _extract_collections_from_data(data)

    if not collections_dict:
        msg = (
            "No collections found in file. "
            "Expected 'collections' key with list of collections."
        )
        raise ValueError(msg)

    return collections_dict


def _extract_collections_from_data(data: Any) -> dict[str, str]:
    """
    Extract collections from parsed YAML data.

    Args:
        data: Parsed YAML data structure.

    Returns:
        Dictionary mapping collection names to versions.

    """
    collections_dict: dict[str, str] = {}

    # Handle the 'collections' key with a list of collection definitions
    if not isinstance(data.get("collections"), list):
        return collections_dict

    for item in data["collections"]:
        if isinstance(item, dict):
            _add_dict_collections(item, collections_dict)
        elif isinstance(item, str):
            _add_string_collections(item, collections_dict)

    return collections_dict


def _add_dict_collections(
    item: dict[str, Any], collections_dict: dict[str, str]
) -> None:
    """
    Add collections from a dictionary item.

    Args:
        item: Dictionary item from collections list.
        collections_dict: Dictionary to add collections to.

    """
    for name, version in item.items():
        if not isinstance(name, str):
            continue
        if isinstance(version, str):
            collections_dict[name] = version
        elif version is None:
            # Handle cases where version is null/unspecified
            collections_dict[name] = "*"


def _add_string_collections(item: str, collections_dict: dict[str, str]) -> None:
    """
    Add collections from a string item.

    Args:
        item: String item from collections list.
        collections_dict: Dictionary to add collections to.

    """
    # Handle simple string format "namespace.name:version"
    if ":" in item:
        name, version = item.split(":", 1)
        collections_dict[name] = version
    else:
        # No version specified, use wildcard
        collections_dict[item] = "*"


@ansible.command("validate-collections")
@click.option(
    "--collections-file",
    type=click.Path(exists=True),
    required=True,
    help="Path to requirements.yml or similar collections file",
)
@click.option(
    "--target-version",
    required=True,
    help="Target Ansible version (e.g., '6.0', '7.0')",
)
def ansible_validate_collections(collections_file: str, target_version: str) -> None:
    r"""
    Validate collection compatibility for target Ansible version.

    Analyses a collections file (requirements.yml) and checks if installed
    collections are compatible with the target Ansible version, identifying
    collections that need updates or may have breaking changes.

    Example:
        souschef ansible validate-collections \
            --collections-file requirements.yml \
            --target-version 7.0

    """
    try:
        msg = f"Validating collections for Ansible {target_version}..."
        click.echo(msg)
        # Validate path before using it
        _validate_user_path(collections_file)
        # Parse the YAML file to extract collections and versions
        collections_dict = _parse_collections_file(collections_file)
        validation = validate_collection_compatibility(collections_dict, target_version)

        click.echo("\n" + "=" * 60)
        title = f"Collection Compatibility Report - Ansible {target_version}"
        click.echo(title)
        click.echo("=" * 60)

        _display_validation_results(validation)
        click.echo("\nValidation complete")

    except Exception as e:
        click.echo(f"Error validating collections: {e}", err=True)
        sys.exit(1)


@ansible.command("detect-python")
@click.option(
    "--environment-path",
    type=click.Path(exists=True),
    help="Path to Ansible environment or venv (detects current if not provided)",
)
def ansible_detect_python(environment_path: str | None) -> None:
    """
    Detect Python version in Ansible environment.

    Identifies the Python version being used by Ansible, which is critical
    for planning upgrades as newer Ansible versions may require newer
    Python versions.

    Example:
        souschef ansible detect-python --environment-path /opt/ansible/venv

    """
    try:
        click.echo("Detecting Python version...")
        # Validate path only if provided
        validated_path = (
            _validate_user_path(environment_path) if environment_path else None
        )
        python_version = detect_python_version(
            str(validated_path) if validated_path else None
        )

        click.echo("\n" + "=" * 60)
        click.echo("Python Version Detection")
        click.echo("=" * 60)
        click.echo(f"\nPython Version: {python_version}")

        # Parse version for additional info
        version_parts = python_version.split(".")
        if len(version_parts) >= 2:
            major_minor = f"{version_parts[0]}.{version_parts[1]}"
            click.echo(f"Major.Minor: {major_minor}")

        click.echo("\nDetection complete")

    except Exception as e:
        click.echo(f"Error detecting Python version: {e}", err=True)
        sys.exit(1)


def main() -> NoReturn:
    """Run the CLI."""
    configure_logging()
    cli()
    sys.exit(0)


if __name__ == "__main__":
    main()
