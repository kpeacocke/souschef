"""PowerShell migration API facade."""

from souschef.orchestrators.powershell import (
    analyze_powershell_migration_fidelity,
    convert_powershell_content_to_ansible,
    generate_ansible_requirements,
    generate_powershell_awx_job_template,
    generate_powershell_role_structure,
    generate_windows_group_vars,
    generate_windows_inventory,
    parse_powershell_content,
)

__all__ = [
    "analyze_powershell_migration_fidelity",
    "convert_powershell_content_to_ansible",
    "generate_ansible_requirements",
    "generate_powershell_awx_job_template",
    "generate_powershell_role_structure",
    "generate_windows_group_vars",
    "generate_windows_inventory",
    "parse_powershell_content",
]
