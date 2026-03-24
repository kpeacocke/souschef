"""Orchestration helpers for Chef analysis and conversion UI flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import souschef.assessment as assessment
import souschef.orchestration as orchestration


def analyse_cookbook_dependencies(cookbook_paths: str) -> str:
    """Analyse Chef cookbook dependencies for UI consumption."""
    return assessment.analyse_cookbook_dependencies(cookbook_paths)


def assess_single_cookbook_with_ai(
    cookbook_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> dict[str, Any]:
    """Run AI-assisted assessment for a single Chef cookbook."""
    return assessment.assess_single_cookbook_with_ai(
        cookbook_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        base_url=base_url,
    )


def parse_chef_migration_assessment(cookbook_paths: str) -> dict[str, Any]:
    """Run rule-based assessment for one or more Chef cookbooks."""
    return assessment.parse_chef_migration_assessment(cookbook_paths)


def calculate_activity_breakdown(
    cookbook_path: str,
    migration_strategy: str = "phased",
) -> dict[str, Any]:
    """Calculate activity breakdown for cookbook migration planning."""
    return assessment.calculate_activity_breakdown(
        cookbook_path,
        migration_strategy=migration_strategy,
    )


def orchestrate_generate_playbook_from_recipe(
    recipe_path: str,
    cookbook_path: str = "",
) -> str:
    """Generate a playbook from a Chef recipe path."""
    return orchestration.orchestrate_generate_playbook_from_recipe(
        recipe_path=recipe_path,
        cookbook_path=cookbook_path,
    )


def orchestrate_generate_playbook_from_recipe_with_ai(
    recipe_path: str,
    ai_provider: str,
    api_key: str,
    model: str,
    temperature: float,
    max_tokens: int,
    project_id: str = "",
    base_url: str = "",
    project_recommendations: dict[str, Any] | None = None,
    cookbook_path: str = "",
) -> str:
    """Generate a playbook from a Chef recipe path using AI assistance."""
    return orchestration.orchestrate_generate_playbook_from_recipe_with_ai(
        recipe_path=recipe_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        base_url=base_url,
        project_recommendations=project_recommendations,
        cookbook_path=cookbook_path,
    )


def orchestrate_template_conversion(cookbook_path: str) -> dict[str, Any]:
    """Convert cookbook templates through the orchestration layer."""
    return orchestration.orchestrate_template_conversion(cookbook_path)


def orchestrate_repository_generation(
    output_path: str,
    repo_type: Any,
    org_name: str = "myorg",
    init_git: bool = True,
) -> Any:
    """Generate an Ansible repository through the orchestration layer."""
    return orchestration.orchestrate_repository_generation(
        output_path=output_path,
        repo_type=repo_type,
        org_name=org_name,
        init_git=init_git,
    )


def orchestrate_conversion_analysis(
    cookbook_path: str = "",
    output_path: str = "",
    num_recipes: int = 0,
    num_roles: int = 0,
    has_multiple_apps: bool = False,
    needs_multi_env: bool = True,
    ai_provider: str = "",
    api_key: str = "",
    model: str = "",
) -> Any:
    """Analyse conversion output through the orchestration layer."""
    return orchestration.orchestrate_conversion_analysis(
        cookbook_path=cookbook_path,
        output_path=output_path,
        num_recipes=num_recipes,
        num_roles=num_roles,
        has_multiple_apps=has_multiple_apps,
        needs_multi_env=needs_multi_env,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
    )


def orchestrate_validate_conversion(
    conversion_type: str,
    result_content: str,
    output_format: str = "text",
) -> str:
    """Validate converted content through the assessment layer."""
    return assessment.validate_conversion(
        conversion_type,
        result_content,
        output_format=output_format,
    )


def orchestrate_cookbook_metadata_parsing(
    cookbook_path: str,
) -> dict[str, str | list[str]]:
    """Parse cookbook metadata through the orchestration layer."""
    return orchestration.orchestrate_cookbook_metadata_parsing(cookbook_path)


def orchestrate_get_storage_manager() -> Any:
    """Access the storage manager through the orchestration layer."""
    return orchestration.orchestrate_get_storage_manager()


def orchestrate_get_blob_storage() -> Any:
    """Access blob storage through the orchestration layer."""
    return orchestration.orchestrate_get_blob_storage()


def orchestrate_calculate_file_fingerprint(file_path: Path) -> str:
    """Calculate a file fingerprint through the orchestration layer."""
    return orchestration.orchestrate_calculate_file_fingerprint(file_path)
