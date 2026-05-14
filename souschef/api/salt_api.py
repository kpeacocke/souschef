"""Salt migration API facade."""

from souschef.orchestrators.salt import (
    assess_salt_complexity,
    convert_salt_directory_to_roles,
    convert_salt_sls_to_ansible,
    generate_salt_inventory,
    parse_salt_directory,
    parse_salt_pillar,
    parse_salt_sls,
    plan_salt_migration,
)

__all__ = [
    "assess_salt_complexity",
    "convert_salt_directory_to_roles",
    "convert_salt_sls_to_ansible",
    "generate_salt_inventory",
    "parse_salt_directory",
    "parse_salt_pillar",
    "parse_salt_sls",
    "plan_salt_migration",
]
