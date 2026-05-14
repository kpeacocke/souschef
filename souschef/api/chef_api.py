"""Chef migration API facade."""

from souschef.orchestrators.chef import (
    analyse_cookbook_dependencies,
    assess_single_cookbook_with_ai,
    calculate_activity_breakdown,
    orchestrate_calculate_file_fingerprint,
    orchestrate_conversion_analysis,
    orchestrate_cookbook_metadata_parsing,
    orchestrate_generate_playbook_from_recipe,
    orchestrate_generate_playbook_from_recipe_with_ai,
    orchestrate_get_blob_storage,
    orchestrate_get_storage_manager,
    orchestrate_repository_generation,
    orchestrate_template_conversion,
    orchestrate_validate_conversion,
    parse_chef_migration_assessment,
)

__all__ = [
    "analyse_cookbook_dependencies",
    "assess_single_cookbook_with_ai",
    "calculate_activity_breakdown",
    "orchestrate_calculate_file_fingerprint",
    "orchestrate_conversion_analysis",
    "orchestrate_cookbook_metadata_parsing",
    "orchestrate_generate_playbook_from_recipe",
    "orchestrate_generate_playbook_from_recipe_with_ai",
    "orchestrate_get_blob_storage",
    "orchestrate_get_storage_manager",
    "orchestrate_repository_generation",
    "orchestrate_template_conversion",
    "orchestrate_validate_conversion",
    "parse_chef_migration_assessment",
]
