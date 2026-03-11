"""
Orchestration layer for UI operations.

This module provides high-level orchestration functions for the UI layer,
coordinating parsers, converters, generators, and storage operations.

According to the SousChef architecture (docs/ARCHITECTURE.md), the UI layer
(Layer 7) should only depend on orchestrators (Layer 6) and core (Layer 1).
This module serves as the orchestration layer bridge until the orchestrators/
directory is created.

Design Principles:
- UI calls orchestration → orchestration calls domain logic (parsers/converters)
- Orchestration handles workflow coordination and error handling
- Orchestration manages storage access for UI
"""

from pathlib import Path
from typing import Any

# Layer 3: Domain Logic (allowed for orchestration layer)
from souschef.converters.playbook import (
    generate_playbook_from_recipe,
    generate_playbook_from_recipe_with_ai,
)
from souschef.converters.template import convert_cookbook_templates
from souschef.generators.repo import (
    analyse_conversion_output,
    generate_ansible_repository,
)
from souschef.parsers.ansible_inventory import parse_requirements_yml
from souschef.parsers.metadata import parse_cookbook_metadata

# Layer 2: Storage (allowed for orchestration layer)
from souschef.storage import get_blob_storage, get_storage_manager
from souschef.storage.database import (
    ConversionResult,  # Re-export for UI layer
    calculate_file_fingerprint,
)

# ============================================================================
# Cookbook Migration Orchestration
# ============================================================================


def orchestrate_playbook_generation(
    cookbook_path: str,
    recipe_name: str,
    use_ai: bool = False,
    ai_provider: str | None = None,
    ai_model: str | None = None,
) -> str:
    """
    Orchestrate playbook generation from a Chef recipe.

    Args:
        cookbook_path: Path to Chef cookbook.
        recipe_name: Name of recipe to convert.
        use_ai: Whether to use AI-powered conversion.
        ai_provider: AI provider (e.g., "anthropic", "openai").
        ai_model: AI model to use.

    Returns:
        Generated Ansible playbook as YAML string.

    """
    recipe_path = str(Path(cookbook_path) / "recipes" / f"{recipe_name}.rb")

    if use_ai and ai_provider and ai_model:
        return generate_playbook_from_recipe_with_ai(
            recipe_path=recipe_path,
            ai_provider=ai_provider,
            model=ai_model,
            cookbook_path=cookbook_path,
        )
    return generate_playbook_from_recipe(
        recipe_path=recipe_path,
        cookbook_path=cookbook_path,
    )


def orchestrate_generate_playbook_from_recipe(
    recipe_path: str,
    cookbook_path: str | None = None,
) -> str:
    """Orchestrate deterministic playbook generation from a recipe path."""
    return generate_playbook_from_recipe(
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
    project_recommendations: str | None = None,
    cookbook_path: str | None = None,
) -> str:
    """Orchestrate AI-assisted playbook generation from a recipe path."""
    return generate_playbook_from_recipe_with_ai(
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


def orchestrate_template_conversion(
    cookbook_path: str,
) -> dict[str, Any]:
    """
    Orchestrate conversion of Chef templates (ERB) to Ansible templates (Jinja2).

    Args:
        cookbook_path: Path to Chef cookbook.

    Returns:
        Template conversion result details.

    """
    return convert_cookbook_templates(cookbook_path)


def orchestrate_repository_generation(
    output_path: str,
    repo_type: Any,  # RepoType | str
    org_name: str = "myorg",
    init_git: bool = True,
) -> Any:
    """
    Orchestrate generation of complete Ansible repository from Chef cookbooks.

    Args:
        output_path: Path where Ansible repository will be generated.
        repo_type: Type of repository structure to generate.
        org_name: Organisation name for the repository.
        init_git: Whether to initialise a git repository.

    Returns:
        Dictionary with generation results.

    """
    return generate_ansible_repository(
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
    """
    Orchestrate analysis of conversion output.

    Args:
        cookbook_path: Path to Chef cookbook (preferred).
        output_path: Path to converted Ansible output (fallback for compatibility).
        num_recipes: Number of recipes converted.
        num_roles: Number of roles that would be created.
        has_multiple_apps: Whether multiple applications are being managed.
        needs_multi_env: Whether multi-environment support is needed.
        ai_provider: AI provider for smarter analysis (optional).
        api_key: API key for AI provider (optional).
        model: AI model to use (optional).

    Returns:
        Repository type recommendation or analysis results.

    """
    # Use cookbook_path if provided, otherwise fall back to output_path
    # for backward compatibility
    path = cookbook_path or output_path
    return analyse_conversion_output(
        cookbook_path=path,
        num_recipes=num_recipes,
        num_roles=num_roles,
        has_multiple_apps=has_multiple_apps,
        needs_multi_env=needs_multi_env,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
    )


def orchestrate_cookbook_metadata_parsing(
    cookbook_path: str,
) -> dict[str, str | list[str]]:
    """
    Orchestrate parsing of Chef cookbook metadata.

    Args:
        cookbook_path: Path to Chef cookbook.

    Returns:
        Parsed metadata as formatted string.

    """
    return parse_cookbook_metadata(path=cookbook_path)


# ============================================================================
# Ansible Validation Orchestration
# ============================================================================


def orchestrate_requirements_parsing(
    requirements_file: str,
) -> dict[str, str]:
    """
    Orchestrate parsing of Ansible requirements.yml file.

    Args:
        requirements_file: Path to requirements.yml file.

    Returns:
        Parsed requirements structure.

    """
    return parse_requirements_yml(requirements_path=requirements_file)


# ============================================================================
# Storage Access Orchestration
# ============================================================================


def orchestrate_get_storage_manager() -> Any:
    """
    Orchestrate access to storage manager for UI operations.

    The storage manager provides database operations for analyses,
    migrations, and history tracking.

    Returns:
        Storage manager instance.

    """
    return get_storage_manager()


def orchestrate_get_blob_storage() -> Any:
    """
    Orchestrate access to blob storage for UI operations.

    The blob storage provides file/artifact storage for cookbooks,
    playbooks, and other large artifacts.

    Returns:
        Blob storage instance.

    """
    return get_blob_storage()


def orchestrate_calculate_file_fingerprint(file_path: Path) -> str:
    """Orchestrate file fingerprint calculation for UI/storage workflows."""
    return calculate_file_fingerprint(file_path)


# ============================================================================
# Re-exports for backward compatibility with existing tests
# ============================================================================

# These are re-exported to maintain backward compatibility with tests that
# may import these orchestration functions from this module.
__all__ = [
    "orchestrate_playbook_generation",
    "orchestrate_generate_playbook_from_recipe",
    "orchestrate_generate_playbook_from_recipe_with_ai",
    "orchestrate_template_conversion",
    "orchestrate_repository_generation",
    "orchestrate_conversion_analysis",
    "orchestrate_cookbook_metadata_parsing",
    "orchestrate_requirements_parsing",
    "orchestrate_get_storage_manager",
    "orchestrate_get_blob_storage",
    "orchestrate_calculate_file_fingerprint",
    "ConversionResult",  # Re-exported type for UI layer
]
