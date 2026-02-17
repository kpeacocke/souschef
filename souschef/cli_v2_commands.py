"""
V2 migration command group for SousChef CLI.

Provides the v2 migration orchestrator workflow and state tracking.
"""

import json
import sys
from pathlib import Path
from typing import Any

import click

from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
)
from souschef.migration_v2 import MigrationOrchestrator, MigrationStatus


def register_v2_commands(cli: Any) -> None:
    """
    Register v2 command group with the main CLI.

    Args:
        cli: The main Click CLI group to register commands with.

    """
    # Create the v2 group and register it
    v2_group = create_v2_group()
    cli.add_command(v2_group, name="v2")


def create_v2_group() -> click.Group:
    """
    Create and return the v2 command group.

    Returns:
        Click Group containing all v2 migration commands.

    """

    @click.group("v2")
    def v2() -> None:
        """
        SousChef v2 migration commands.

        Provides the v2 migration orchestrator workflow and state tracking.
        """

    # Register v2 commands to the group
    v2.add_command(v2_migrate)
    v2.add_command(v2_status)
    v2.add_command(v2_list)
    v2.add_command(v2_rollback)

    return v2


def _validate_user_path(path_input: str | None) -> Path:
    """
    Validate and sanitise user-supplied path input.

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

        if not validated_path.exists():  # NOSONAR
            raise ValueError(f"Path does not exist: {validated_path}")

        return validated_path
    except OSError as e:
        raise ValueError(f"Invalid path: {e}") from e


def _resolve_output_path(output: str | None, default_path: Path) -> Path:
    """
    Normalise and validate output paths for generated files.

    Args:
        output: User-specified output path or None.
        default_path: Default path if output not specified.

    Returns:
        Validated and resolved Path.

    Raises:
        click.Abort: If path validation fails.

    """
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


def _output_result(result: str, output_format: str) -> None:
    """
    Output conversion result in the specified format.

    Args:
        result: The result content to output.
        output_format: Output format ('text' or 'json').

    """
    if output_format == "json":
        # Ensure valid JSON
        try:
            json_obj = json.loads(result)
            click.echo(json.dumps(json_obj, indent=2))
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON result")
            sys.exit(1)
    else:
        click.echo(result)


@click.command("migrate")
@click.option(
    "--cookbook-path",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Chef cookbook directory",
)
@click.option(
    "--chef-version",
    required=True,
    help="Chef Infra Client version (e.g., 15.10.91)",
)
@click.option(
    "--target-platform",
    required=True,
    type=click.Choice(["tower", "awx", "aap"], case_sensitive=False),
    help="Target automation platform (tower/awx/aap)",
)
@click.option(
    "--target-version",
    required=True,
    help="Target platform version (e.g., 2.4.0)",
)
@click.option(
    "--chef-server-url",
    default=None,
    help="Chef Server URL (optional)",
)
@click.option(
    "--chef-organisation",
    default=None,
    help="Chef organisation name (optional)",
)
@click.option(
    "--chef-client-name",
    default=None,
    help="Chef client name (optional)",
)
@click.option(
    "--chef-client-key-path",
    type=click.Path(exists=True),
    default=None,
    help="Path to Chef client key file (optional)",
)
@click.option(
    "--chef-client-key",
    default=None,
    help="Inline Chef client key content (optional)",
)
@click.option(
    "--chef-query",
    default="*",
    help="Chef search query for nodes (default: *)",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    help="Skip playbook validation",
)
@click.option(
    "--save-state",
    is_flag=True,
    help="Persist migration state to storage",
)
@click.option(
    "--analysis-id",
    type=int,
    default=None,
    help="Optional analysis ID to link the migration history",
)
@click.option(
    "--output-type",
    type=click.Choice(["playbook", "role", "collection"]),
    default="playbook",
    help="Output type recorded in history",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(),
    help="Save result to file instead of printing to stdout",
)
def v2_migrate(  # noqa: S107  # NOSONAR
    cookbook_path: str,
    chef_version: str,
    target_platform: str,
    target_version: str,
    chef_server_url: str | None,
    chef_organisation: str | None,
    chef_client_name: str | None,
    chef_client_key_path: str | None,
    chef_client_key: str | None,
    chef_query: str,
    skip_validation: bool,
    save_state: bool,
    analysis_id: int | None,
    output_type: str,
    output_format: str,
    output_path: str | None,
) -> None:
    """
    Run the v2 migration orchestrator for a cookbook.

    Executes analysis, conversion, and optional validation. Optionally
    saves migration state to the storage layer for later retrieval.
    """
    # Group parameters into logical dictionaries to reduce complexity
    chef_server_config = {
        "url": chef_server_url,
        "organisation": chef_organisation,
        "client_name": chef_client_name,
        "client_key_path": chef_client_key_path,
        "client_key": chef_client_key,
        "query": chef_query,
    }
    output_config = {
        "type": output_type,
        "format": output_format,
        "path": output_path,
    }
    migration_options = {
        "skip_validation": skip_validation,
        "save_state": save_state,
        "analysis_id": analysis_id,
    }
    _run_v2_migration(
        cookbook_path=cookbook_path,
        chef_version=chef_version,
        target_platform=target_platform,
        target_version=target_version,
        chef_server_config=chef_server_config,
        output_config=output_config,
        migration_options=migration_options,
    )


def _run_v2_migration(
    cookbook_path: str,
    chef_version: str,
    target_platform: str,
    target_version: str,
    chef_server_config: dict[str, Any],
    output_config: dict[str, Any],
    migration_options: dict[str, Any],
) -> None:
    """Execute v2 migration with grouped parameter sets for reduced complexity."""
    try:
        cookbook_dir = _validate_user_path(cookbook_path)
        if not cookbook_dir.is_dir():
            click.echo(f"Error: {cookbook_path} is not a directory", err=True)
            sys.exit(1)

        orchestrator = MigrationOrchestrator(
            chef_version=chef_version,
            target_platform=target_platform,
            target_version=target_version,
        )

        result = orchestrator.migrate_cookbook(
            str(cookbook_dir),
            skip_validation=migration_options["skip_validation"],
            chef_server_url=chef_server_config["url"],
            chef_organisation=chef_server_config["organisation"],
            chef_client_name=chef_server_config["client_name"],
            chef_client_key_path=chef_server_config["client_key_path"],
            chef_client_key=chef_server_config["client_key"],
            chef_query=chef_server_config["query"],
        )

        storage_id = None
        if migration_options["save_state"]:
            storage_id = orchestrator.save_state(
                output_type=output_config["type"],
                analysis_id=migration_options["analysis_id"],
            )

        payload = result.to_dict()
        if storage_id is not None:
            payload["storage_id"] = storage_id

        output_content = json.dumps(payload, indent=2)
        if output_config["path"]:
            _safe_write_file(
                output_content,
                output_config["path"],
                Path("migration-result.json"),
            )
            click.echo(f"Result saved to: {output_config['path']}")
        else:
            _output_result(output_content, output_config["format"])

        if result.status == MigrationStatus.FAILED:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error running v2 migration: {e}", err=True)
        sys.exit(1)


@click.command("status")
@click.option(
    "--migration-id",
    required=True,
    help="Migration ID to load from storage",
)
@click.option(
    "--limit",
    type=int,
    default=500,
    help="Maximum number of history entries to scan",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(),
    help="Save result to file instead of printing to stdout",
)
def v2_status(
    migration_id: str,
    limit: int,
    output_format: str,
    output_path: str | None,
) -> None:
    """
    Load a saved v2 migration state by ID.

    Scans stored conversion history for a matching migration ID.
    """
    try:
        result = MigrationOrchestrator.load_state(
            migration_id,
            limit=limit,
        )

        if result is None:
            click.echo("Migration ID not found in storage", err=True)
            sys.exit(1)

        output_content = json.dumps(result.to_dict(), indent=2)
        if output_path:
            _safe_write_file(
                output_content,
                output_path,
                Path(f"migration-{migration_id}.json"),
            )
            click.echo(f"Result saved to: {output_path}")
        else:
            _output_result(output_content, output_format)

    except Exception as e:
        click.echo(f"Error loading migration state: {e}", err=True)
        sys.exit(1)


@click.command("list")
@click.option(
    "--cookbook-name",
    default=None,
    help="Filter by cookbook name (optional)",
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of migrations to show (default: 20)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format (default: text)",
)
def v2_list(
    cookbook_name: str | None,
    limit: int,
    output_format: str,
) -> None:
    """
    List recent v2 migrations from storage.

    Shows migration history with status, timestamps, and conversion metrics.
    Optionally filter by cookbook name.
    """
    try:
        from souschef.storage import get_storage_manager

        storage = get_storage_manager()
        conversions = storage.get_conversion_history(
            cookbook_name=cookbook_name,
            limit=limit,
        )

        if not conversions:
            click.echo("No migrations found in storage")
            return

        if output_format == "json":
            _display_migrations_json(conversions)
        else:
            _display_migrations_text(conversions, limit)

    except Exception as e:
        click.echo(f"Error listing migrations: {e}", err=True)
        sys.exit(1)


def _display_migrations_json(conversions: list[Any]) -> None:
    """Display migrations in JSON format."""
    output = []
    for conv in conversions:
        # Extract migration data if available
        migration_data = (
            json.loads(conv.conversion_data) if conv.conversion_data else {}
        )
        migration_result = migration_data.get("migration_result", {})

        output.append(
            {
                "id": conv.id,
                "cookbook_name": conv.cookbook_name,
                "output_type": conv.output_type,
                "status": conv.status,
                "files_generated": conv.files_generated,
                "created_at": conv.created_at,
                "migration_id": migration_result.get("migration_id"),
                "migration_status": migration_result.get("status"),
            }
        )
    click.echo(json.dumps(output, indent=2))


def _display_migrations_text(conversions: list[Any], limit: int) -> None:
    """Display migrations in text format."""
    click.echo(f"\n{'=' * 80}")
    click.echo(f"Recent Migrations (showing {len(conversions)} of {limit} max)")
    click.echo(f"{'=' * 80}\n")

    for conv in conversions:
        migration_data = (
            json.loads(conv.conversion_data) if conv.conversion_data else {}
        )
        migration_result = migration_data.get("migration_result", {})
        migration_id = migration_result.get("migration_id", "N/A")

        click.echo(f"ID: {conv.id}")
        click.echo(f"Migration ID: {migration_id[:16]}...")
        click.echo(f"Cookbook: {conv.cookbook_name}")
        click.echo(f"Status: {conv.status}")
        click.echo(f"Files Generated: {conv.files_generated}")
        click.echo(f"Created: {conv.created_at}")

        metrics = migration_result.get("metrics", {})
        recipes_converted = metrics.get("recipes_converted", 0)
        recipes_total = metrics.get("recipes_total", 0)
        if recipes_total > 0:
            conversion_rate = (recipes_converted / recipes_total) * 100
            click.echo(f"Conversion Rate: {conversion_rate:.1f}%")

        click.echo(f"{'-' * 80}\n")


@click.command("rollback")
@click.option(
    "--url",
    required=True,
    help="Ansible platform URL (e.g., https://tower.example.com)",
)
@click.option(
    "--username",
    required=True,
    help="Username for authentication",
)
@click.option(
    "--password",
    required=True,
    help="Password for authentication",
)
@click.option(
    "--migration-id",
    required=True,
    help="Migration ID to rollback (load from storage first)",
)
@click.option(
    "--limit",
    type=int,
    default=500,
    help="Maximum number of history entries to scan when loading state",
)
def v2_rollback(
    url: str,
    username: str,
    password: str,
    migration_id: str,
    limit: int,
) -> None:
    """
    Rollback a v2 migration by deleting created Ansible infrastructure.

    Loads the migration state from storage and deletes all created resources
    (job template, inventory, project, execution environment) from the target
    Ansible platform.
    """
    try:
        # Load migration state from storage
        result = MigrationOrchestrator.load_state(
            migration_id,
            limit=limit,
        )

        if result is None:
            click.echo("Migration ID not found in storage", err=True)
            sys.exit(1)

        # Check if migration was deployed
        if result.status != MigrationStatus.DEPLOYED:
            status_msg = (
                f"Migration {migration_id} is not deployed "
                f"(status: {result.status.value})"
            )
            click.echo(status_msg, err=True)
            click.echo("Only deployed migrations can be rolled back.", err=True)
            sys.exit(1)

        # Create orchestrator with same config
        orchestrator = MigrationOrchestrator(
            chef_version=result.chef_version,
            target_platform=result.target_platform,
            target_version=result.target_version,
        )
        orchestrator.result = result
        orchestrator.migration_id = migration_id

        # Perform rollback
        click.echo(f"Rolling back migration {migration_id}...")
        orchestrator.rollback(url, (username, password))

        if orchestrator.result.status == MigrationStatus.ROLLED_BACK:
            click.echo("Rollback successful!")
            click.echo(
                f"Deleted {len(orchestrator.result.playbooks_generated)} resources"
            )
        else:
            click.echo("Rollback failed", err=True)
            if orchestrator.result.errors:
                for error in orchestrator.result.errors:
                    click.echo(f"  - {error.get('error', 'Unknown error')}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error during rollback: {e}", err=True)
        sys.exit(1)
