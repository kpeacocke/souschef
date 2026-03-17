"""Ansible artifact generators."""

from souschef.generators.powershell import (
    analyze_powershell_migration_fidelity,
    generate_ansible_requirements,
    generate_powershell_awx_job_template,
    generate_powershell_role_structure,
    generate_windows_group_vars,
    generate_windows_inventory,
)
from souschef.generators.repo import (
    RepoType,
    analyse_conversion_output,
    generate_ansible_repository,
)

__all__ = [
    "RepoType",
    "analyse_conversion_output",
    "generate_ansible_repository",
    "analyze_powershell_migration_fidelity",
    "generate_ansible_requirements",
    "generate_powershell_awx_job_template",
    "generate_powershell_role_structure",
    "generate_windows_group_vars",
    "generate_windows_inventory",
]
