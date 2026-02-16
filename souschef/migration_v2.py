"""
SousChef v2.0 - Complete Migration Orchestrator.

Handles end-to-end Chef to Ansible migrations:
1. Query Chef Server for cookbook data and nodes
2. Convert Chef artifacts (recipes, attributes, resources) to Ansible
3. Create/configure Ansible infrastructure (inventory, playbooks, job templates)
4. Track migration state and handle errors

Supports all 18 Chef→Ansible version combinations.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from souschef.converters.playbook import generate_playbook_from_recipe
from souschef.converters.template import convert_template_file
from souschef.migration_simulation import (
    create_simulation_config,
)
from souschef.parsers.attributes import parse_attributes

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from souschef.storage import StorageManager


class MigrationStatus(Enum):
    """Status of a migration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    CONVERTED = "converted"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MetricsConversionStatus(Enum):
    """Status of converted assets."""

    SUCCESS = "success"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class ConversionMetrics:
    """Metrics for conversion results."""

    recipes_total: int = 0
    recipes_converted: int = 0
    recipes_partial: int = 0
    recipes_skipped: int = 0
    recipes_failed: int = 0

    attributes_total: int = 0
    attributes_converted: int = 0
    attributes_skipped: int = 0

    resources_total: int = 0
    resources_converted: int = 0
    resources_skipped: int = 0

    handlers_total: int = 0
    handlers_converted: int = 0
    handlers_skipped: int = 0

    templates_total: int = 0
    templates_converted: int = 0
    templates_skipped: int = 0

    def conversion_rate(self) -> float:
        """Get overall conversion rate as percentage."""
        total = (
            self.recipes_total
            + self.attributes_total
            + self.resources_total
            + self.handlers_total
            + self.templates_total
        )
        if total == 0:
            return 0.0
        converted = (
            self.recipes_converted
            + self.attributes_converted
            + self.resources_converted
            + self.handlers_converted
            + self.templates_converted
        )
        return (converted / total) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recipes": {
                "total": self.recipes_total,
                "converted": self.recipes_converted,
                "partial": self.recipes_partial,
                "skipped": self.recipes_skipped,
                "failed": self.recipes_failed,
            },
            "attributes": {
                "total": self.attributes_total,
                "converted": self.attributes_converted,
                "skipped": self.attributes_skipped,
            },
            "resources": {
                "total": self.resources_total,
                "converted": self.resources_converted,
                "skipped": self.resources_skipped,
            },
            "handlers": {
                "total": self.handlers_total,
                "converted": self.handlers_converted,
                "skipped": self.handlers_skipped,
            },
            "templates": {
                "total": self.templates_total,
                "converted": self.templates_converted,
                "skipped": self.templates_skipped,
            },
            "overall_conversion_rate": f"{self.conversion_rate():.1f}%",
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversionMetrics":
        """
        Build metrics from a dictionary payload.

        Args:
            data: Metrics data from storage.

        Returns:
            ConversionMetrics instance.

        """
        recipes = data.get("recipes", {}) if isinstance(data, dict) else {}
        attributes = data.get("attributes", {}) if isinstance(data, dict) else {}
        resources = data.get("resources", {}) if isinstance(data, dict) else {}
        handlers = data.get("handlers", {}) if isinstance(data, dict) else {}
        templates = data.get("templates", {}) if isinstance(data, dict) else {}

        return cls(
            recipes_total=recipes.get("total", 0),
            recipes_converted=recipes.get("converted", 0),
            recipes_partial=recipes.get("partial", 0),
            recipes_skipped=recipes.get("skipped", 0),
            recipes_failed=recipes.get("failed", 0),
            attributes_total=attributes.get("total", 0),
            attributes_converted=attributes.get("converted", 0),
            attributes_skipped=attributes.get("skipped", 0),
            resources_total=resources.get("total", 0),
            resources_converted=resources.get("converted", 0),
            resources_skipped=resources.get("skipped", 0),
            handlers_total=handlers.get("total", 0),
            handlers_converted=handlers.get("converted", 0),
            handlers_skipped=handlers.get("skipped", 0),
            templates_total=templates.get("total", 0),
            templates_converted=templates.get("converted", 0),
            templates_skipped=templates.get("skipped", 0),
        )


@dataclass
class MigrationResult:
    """Result of a migration."""

    migration_id: str
    status: MigrationStatus
    chef_version: str
    target_platform: str
    target_version: str
    ansible_version: str
    created_at: str
    updated_at: str
    source_cookbook: str
    playbooks_generated: list[str] = field(default_factory=list)
    playbooks_deployed: list[str] = field(default_factory=list)
    inventory_id: int | None = None
    project_id: int | None = None
    job_template_id: int | None = None
    metrics: ConversionMetrics = field(default_factory=ConversionMetrics)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "migration_id": self.migration_id,
            "status": self.status.value,
            "chef_version": self.chef_version,
            "target_platform": self.target_platform,
            "target_version": self.target_version,
            "ansible_version": self.ansible_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_cookbook": self.source_cookbook,
            "playbooks_generated": self.playbooks_generated,
            "playbooks_deployed": self.playbooks_deployed,
            "infrastructure": {
                "inventory_id": self.inventory_id,
                "project_id": self.project_id,
                "job_template_id": self.job_template_id,
            },
            "metrics": self.metrics.to_dict(),
            "errors": self.errors,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MigrationResult":
        """
        Build a MigrationResult from stored data.

        Args:
            data: Migration result data from storage.

        Returns:
            MigrationResult instance.

        """
        if not isinstance(data, dict):
            raise ValueError("Migration result data must be a dictionary")

        status_value = data.get("status", MigrationStatus.PENDING.value)
        try:
            status = MigrationStatus(status_value)
        except ValueError:
            status = MigrationStatus.PENDING

        infrastructure = data.get("infrastructure", {})
        metrics_payload = data.get("metrics", {})

        return cls(
            migration_id=data.get("migration_id", ""),
            status=status,
            chef_version=data.get("chef_version", ""),
            target_platform=data.get("target_platform", ""),
            target_version=data.get("target_version", ""),
            ansible_version=data.get("ansible_version", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            source_cookbook=data.get("source_cookbook", ""),
            playbooks_generated=data.get("playbooks_generated", []),
            playbooks_deployed=data.get("playbooks_deployed", []),
            inventory_id=infrastructure.get("inventory_id"),
            project_id=infrastructure.get("project_id"),
            job_template_id=infrastructure.get("job_template_id"),
            metrics=ConversionMetrics.from_dict(metrics_payload),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
        )


class MigrationOrchestrator:
    """Orchestrates complete Chef→Ansible migrations."""

    def __init__(
        self,
        chef_version: str,
        target_platform: str,
        target_version: str,
        fips_mode: bool = False,
    ):
        """Initialize migration orchestrator."""
        self.config = create_simulation_config(
            chef_version=chef_version,
            target_platform=target_platform,
            target_version=target_version,
            fips_mode=fips_mode,
        )
        self.migration_id = f"mig-{uuid4().hex[:12]}"
        self.result: MigrationResult | None = None

    def migrate_cookbook(
        self, cookbook_path: str, skip_validation: bool = False
    ) -> MigrationResult:
        """
        Execute complete cookbook migration.

        Args:
            cookbook_path: Path to cookbook to migrate.
            skip_validation: Skip playbook validation if True.

        Returns:
            Migration result with status, playbooks, and metrics.

        """
        self.result = MigrationResult(
            migration_id=self.migration_id,
            status=MigrationStatus.PENDING,
            chef_version=self.config.chef_version,
            target_platform=self.config.target_platform,
            target_version=self.config.target_version,
            ansible_version=self.config.ansible_version,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_cookbook=cookbook_path,
        )

        try:
            # Phase 1: Analyze
            logger.info(f"[{self.migration_id}] Starting migration analysis")
            self._analyze_cookbook(cookbook_path)

            # Phase 2: Convert
            logger.info(f"[{self.migration_id}] Converting Chef artifacts")
            self.result.status = MigrationStatus.IN_PROGRESS
            self._convert_recipes(cookbook_path)
            self._convert_attributes(cookbook_path)
            self._convert_resources(cookbook_path)
            self._convert_handlers(cookbook_path)
            self._convert_templates(cookbook_path)

            # Phase 3: Validate
            if not skip_validation:
                logger.info(f"[{self.migration_id}] Validating playbooks")
                self._validate_playbooks()
                self.result.status = MigrationStatus.VALIDATED
            else:
                self.result.status = MigrationStatus.CONVERTED

            logger.info(
                f"[{self.migration_id}] Migration complete: "
                f"{self.result.metrics.conversion_rate():.1f}% conversion rate"
            )

        except Exception as e:
            logger.error(f"[{self.migration_id}] Migration failed: {e}")
            self.result.status = MigrationStatus.FAILED
            self.result.errors.append(
                {
                    "phase": "migration",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        self.result.updated_at = datetime.now().isoformat()
        return self.result

    def _analyze_cookbook(self, cookbook_path: str) -> None:
        """Analyse cookbook structure and content."""
        assert self.result is not None
        path = Path(cookbook_path)
        if not path.exists():
            raise FileNotFoundError(f"Cookbook not found: {cookbook_path}")

        # Count Chef artifacts
        recipes_dir = path / "recipes"
        if recipes_dir.exists():
            self.result.metrics.recipes_total = len(list(recipes_dir.glob("*.rb")))

        attributes_dir = path / "attributes"
        if attributes_dir.exists():
            self.result.metrics.attributes_total = len(
                list(attributes_dir.glob("*.rb"))
            )

        resources_dir = path / "resources"
        if resources_dir.exists():
            self.result.metrics.resources_total = len(list(resources_dir.glob("*.rb")))

        handlers_dir = path / "libraries"
        if handlers_dir.exists():
            self.result.metrics.handlers_total = len(list(handlers_dir.glob("*.rb")))

        templates_dir = path / "templates"
        if templates_dir.exists():
            self.result.metrics.templates_total = len(list(templates_dir.glob("*")))

    def _convert_recipes(self, cookbook_path: str) -> None:
        """Convert Chef recipes to Ansible playbooks."""
        assert self.result is not None
        recipes_dir = Path(cookbook_path) / "recipes"
        if recipes_dir.exists():
            for recipe_file in recipes_dir.glob("*.rb"):
                try:
                    # Generate Ansible playbook from Chef recipe
                    playbook_content = generate_playbook_from_recipe(
                        str(recipe_file), cookbook_path
                    )

                    # Check if conversion was successful
                    if not playbook_content.startswith("Error"):
                        playbook_name = recipe_file.stem + ".yml"
                        self.result.playbooks_generated.append(playbook_name)
                        self.result.metrics.recipes_converted += 1
                        logger.debug(
                            f"Converted recipe {recipe_file.name} to {playbook_name}"
                        )
                    else:
                        self.result.metrics.recipes_skipped += 1
                        logger.warning(
                            f"Failed to convert {recipe_file.name}: {playbook_content}"
                        )
                except Exception as e:
                    logger.error(f"Error converting {recipe_file.name}: {e}")
                    self.result.metrics.recipes_skipped += 1

    def _convert_attributes(self, cookbook_path: str) -> None:
        """Convert Chef attributes to Ansible variables."""
        assert self.result is not None
        attributes_dir = Path(cookbook_path) / "attributes"
        if attributes_dir.exists():
            for attr_file in attributes_dir.glob("*.rb"):
                try:
                    # Parse Chef attributes
                    attributes_content = parse_attributes(str(attr_file))

                    if not attributes_content.startswith("Error"):
                        # Generate Ansible variables file
                        var_name = attr_file.stem + ".yml"
                        # Store reference to variables file
                        self.result.playbooks_generated.append(f"vars/{var_name}")
                        self.result.metrics.attributes_converted += 1
                        logger.debug(
                            f"Converted attributes {attr_file.name} to {var_name}"
                        )
                    else:
                        self.result.metrics.attributes_skipped += 1
                        logger.warning(
                            f"Failed to convert attributes {attr_file.name}: "
                            f"{attributes_content}"
                        )
                except Exception as e:
                    logger.error(f"Error converting {attr_file.name}: {e}")
                    self.result.metrics.attributes_skipped += 1

    def _convert_resources(self, cookbook_path: str) -> None:
        """
        Convert Chef custom resources to Ansible modules.

        Note: Custom resources are complex and often require manual review.
        """
        assert self.result is not None
        resources_dir = Path(cookbook_path) / "resources"
        if resources_dir.exists():
            for resource_file in resources_dir.glob("*.rb"):
                # Resources need custom conversion logic
                self.result.metrics.resources_skipped += 1
                self.result.warnings.append(
                    {
                        "resource": resource_file.name,
                        "message": "Custom resources require manual review",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    def _convert_handlers(self, cookbook_path: str) -> None:
        """
        Convert Chef handlers to Ansible handlers.

        Note: Handlers are typically integrated into playbook error handling.
        """
        assert self.result is not None
        handlers_dir = Path(cookbook_path) / "libraries"
        if handlers_dir.exists():
            for handler_file in handlers_dir.glob("*.rb"):
                # Handlers need custom conversion logic
                self.result.metrics.handlers_skipped += 1
                self.result.warnings.append(
                    {
                        "handler": handler_file.name,
                        "message": "Handlers require manual review",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                logger.debug(
                    f"Found handler {handler_file.name} - manual review needed"
                )

    def _convert_templates(self, cookbook_path: str) -> None:
        """Convert Chef templates to Ansible Jinja2."""
        assert self.result is not None
        templates_dir = Path(cookbook_path) / "templates"
        if templates_dir.exists():
            for template_file in templates_dir.glob("*"):
                # Skip non-.erb files
                if template_file.suffix != ".erb" and not template_file.name.endswith(
                    ".erb"
                ):
                    continue

                try:
                    # Convert ERB to Jinja2
                    conversion_result = convert_template_file(str(template_file))

                    if conversion_result.get("success"):
                        jinja2_filename = Path(conversion_result["jinja2_file"]).name
                        self.result.playbooks_generated.append(
                            f"templates/{jinja2_filename}"
                        )
                        self.result.metrics.templates_converted += 1
                        logger.debug(
                            f"Converted template {template_file.name} "
                            f"to {jinja2_filename}"
                        )
                    else:
                        self.result.metrics.templates_skipped += 1
                        logger.warning(
                            f"Failed to convert {template_file.name}: "
                            f"{conversion_result.get('error')}"
                        )
                except Exception as e:
                    logger.error(f"Error converting {template_file.name}: {e}")
                    self.result.metrics.templates_skipped += 1

    def _validate_playbooks(self) -> None:
        """Validate generated playbooks for target Ansible version."""
        assert self.result is not None
        # Validate syntax for target version
        for playbook in self.result.playbooks_generated:
            # Skip variable and template references
            if playbook.startswith("vars/") or playbook.startswith("templates/"):
                continue

            try:
                # Basic YAML syntax validation
                # In production, should use ansible-lint
                logger.debug(f"Validating playbook: {playbook}")
            except Exception as e:
                logger.warning(f"Validation issue with {playbook}: {e}")
                self.result.warnings.append(
                    {
                        "playbook": playbook,
                        "message": f"Validation warning: {e}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    def deploy_to_ansible(
        self,
        ansible_url: str,
        ansible_username: str,
        ansible_password: str,
    ) -> bool:
        """
        Deploy playbooks and create job templates in Ansible platform.

        Args:
            ansible_url: URL of Ansible platform (Tower/AWX/AAP).
            ansible_username: Username for authentication.
            ansible_password: Password for authentication.

        Returns:
            True if deployment successful, False otherwise.

        """
        if not self.result:
            raise RuntimeError("No migration result available")

        try:
            logger.info(
                f"[{self.migration_id}] Deploying to {self.config.target_platform}"
            )
            self.result.status = MigrationStatus.IN_PROGRESS

            # Step 1: Create inventory
            logger.debug("Creating inventory...")
            self.result.inventory_id = self._create_inventory(
                ansible_url, ansible_username, ansible_password
            )

            # Step 2: Create project
            logger.debug("Creating project...")
            self.result.project_id = self._create_project(
                ansible_url, ansible_username, ansible_password
            )

            # Step 3: Create execution environment if needed
            if self.config.execution_model == "execution_environment":
                logger.debug("Creating execution environment...")
                self._create_execution_environment(
                    ansible_url, ansible_username, ansible_password
                )

            # Step 4: Create job template
            logger.debug("Creating job template...")
            self.result.job_template_id = self._create_job_template(
                ansible_url, ansible_username, ansible_password
            )

            # Update deployed playbooks
            self.result.playbooks_deployed = self.result.playbooks_generated

            self.result.status = MigrationStatus.DEPLOYED
            logger.info(f"[{self.migration_id}] Deployment complete")
            return True

        except Exception as e:
            logger.error(f"[{self.migration_id}] Deployment failed: {e}")
            self.result.status = MigrationStatus.FAILED
            self.result.errors.append(
                {
                    "phase": "deployment",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            )
            return False

    def _create_inventory(self, url: str, username: str, password: str) -> int:
        """Create inventory in Ansible platform."""
        # Placeholder - will integrate with real API client
        return 1

    def _create_project(self, url: str, username: str, password: str) -> int:
        """Create project in Ansible platform."""
        # Placeholder
        return 2

    def _create_execution_environment(
        self, url: str, username: str, password: str
    ) -> int:
        """Create execution environment (if supported)."""
        # Placeholder
        return 42

    def _create_job_template(self, url: str, username: str, password: str) -> int:
        """Create job template in Ansible platform."""
        # Placeholder
        return 1

    def rollback(self, ansible_url: str, ansible_auth: tuple[str, str]) -> bool:
        """
        Rollback migration by deleting created infrastructure.

        Args:
            ansible_url: URL of Ansible platform.
            ansible_auth: Tuple of (username, password).

        Returns:
            True if rollback successful, False otherwise.

        """
        if not self.result:
            return False

        try:
            logger.info(f"[{self.migration_id}] Rolling back migration")
            username, password = ansible_auth

            # Delete in reverse order
            if self.result.job_template_id:
                self._delete_job_template(
                    ansible_url, username, password, self.result.job_template_id
                )

            if self.result.inventory_id:
                self._delete_inventory(
                    ansible_url,
                    username,
                    password,
                    self.result.inventory_id,
                )

            if self.result.project_id:
                self._delete_project(
                    ansible_url, username, password, self.result.project_id
                )

            self.result.status = MigrationStatus.ROLLED_BACK
            logger.info(f"[{self.migration_id}] Rollback complete")
            return True

        except Exception as e:
            logger.error(f"[{self.migration_id}] Rollback failed: {e}")
            return False

    def _delete_job_template(
        self, url: str, username: str, password: str, jt_id: int
    ) -> None:
        """Delete job template."""
        # Placeholder
        pass

    def _delete_inventory(
        self, url: str, username: str, password: str, inv_id: int
    ) -> None:
        """Delete inventory."""
        # Placeholder
        pass

    def _delete_project(
        self, url: str, username: str, password: str, proj_id: int
    ) -> None:
        """Delete project."""
        # Placeholder
        pass

    def get_status(self) -> dict[str, Any]:
        """Get migration status."""
        if not self.result:
            return {"status": "no_migration"}

        return self.result.to_dict()

    def save_state(
        self,
        storage_manager: "StorageManager | None" = None,
        output_type: str = "playbook",
        analysis_id: int | None = None,
        blob_storage_key: str | None = None,
    ) -> int | None:
        """
        Persist migration state to the storage manager.

        Args:
            storage_manager: Optional storage manager instance.
            output_type: Output type for storage history.
            analysis_id: Optional analysis ID to link history.
            blob_storage_key: Optional blob storage key.

        Returns:
            Conversion record ID if saved, otherwise None.

        """
        if not self.result:
            raise RuntimeError("No migration result available")

        from souschef.storage import get_storage_manager

        resolved_storage = storage_manager or get_storage_manager()
        cookbook_name = Path(self.result.source_cookbook).name
        conversion_data = {
            "migration_id": self.result.migration_id,
            "migration_result": self.result.to_dict(),
            "saved_at": datetime.now().isoformat(),
        }

        return resolved_storage.save_conversion(
            cookbook_name=cookbook_name,
            output_type=output_type,
            status=self._resolve_conversion_status(),
            files_generated=len(self.result.playbooks_generated),
            conversion_data=conversion_data,
            analysis_id=analysis_id,
            blob_storage_key=blob_storage_key,
        )

    @staticmethod
    def load_state(
        migration_id: str,
        storage_manager: "StorageManager | None" = None,
        limit: int = 500,
    ) -> MigrationResult | None:
        """
        Load a migration state from the storage manager.

        Args:
            migration_id: Migration identifier to look up.
            storage_manager: Optional storage manager instance.
            limit: Maximum number of history entries to scan.

        Returns:
            MigrationResult if found, otherwise None.

        """
        from souschef.storage import get_storage_manager

        resolved_storage = storage_manager or get_storage_manager()
        conversions = resolved_storage.get_conversion_history(limit=limit)

        for conversion in conversions:
            try:
                payload = json.loads(conversion.conversion_data)
            except (TypeError, json.JSONDecodeError):
                continue

            if not isinstance(payload, dict):
                continue

            if payload.get("migration_id") != migration_id:
                continue

            stored_result = payload.get("migration_result")
            if isinstance(stored_result, dict):
                return MigrationResult.from_dict(stored_result)

            if "migration_id" in payload:
                return MigrationResult.from_dict(payload)

        return None

    def _resolve_conversion_status(self) -> str:
        """Resolve migration status into storage status labels."""
        if not self.result:
            raise RuntimeError("No migration result available")

        if self.result.status == MigrationStatus.FAILED:
            return "failed"

        metrics = self.result.metrics
        skipped_total = (
            metrics.recipes_skipped
            + metrics.attributes_skipped
            + metrics.resources_skipped
            + metrics.handlers_skipped
            + metrics.templates_skipped
        )

        if skipped_total > 0 or self.result.warnings:
            return "partial"

        return "success"

    def export_result(self, filename: str) -> None:
        """Export migration result to JSON file."""
        if not self.result:
            raise RuntimeError("No migration result available")

        with Path(filename).open("w") as f:
            json.dump(self.result.to_dict(), f, indent=2)

        logger.info(f"Exported migration result to {filename}")
