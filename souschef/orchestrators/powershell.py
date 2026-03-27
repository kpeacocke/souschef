"""Orchestration helpers for PowerShell migration UI flows."""

from __future__ import annotations

import souschef.converters.powershell as powershell_converter
import souschef.generators.powershell as powershell_generators
import souschef.parsers.powershell as powershell_parser


def parse_powershell_content(content: str, source: str = "<inline>") -> str:
    """Parse PowerShell script content for UI display."""
    return powershell_parser.parse_powershell_content(content, source)


def convert_powershell_content_to_ansible(
    content: str,
    playbook_name: str = "powershell_migration",
    hosts: str = "windows",
    source: str = "<inline>",
) -> str:
    """Convert PowerShell script content to an Ansible playbook response."""
    return powershell_converter.convert_powershell_content_to_ansible(
        content,
        playbook_name=playbook_name,
        hosts=hosts,
        source=source,
    )


def analyze_powershell_migration_fidelity(parsed_ir: dict[str, object]) -> str:
    """Analyse migration fidelity for parsed PowerShell actions."""
    return powershell_generators.analyze_powershell_migration_fidelity(parsed_ir)


def generate_windows_inventory(*args: object, **kwargs: object) -> str:
    """Generate Windows inventory content for enterprise artefacts."""
    return powershell_generators.generate_windows_inventory(
        hosts=None,
        winrm_port=5986,
        use_ssl=True,
        validate_certs=False,
        winrm_transport="ntlm",
    )


def generate_windows_group_vars(
    ansible_user: str = "Administrator",
    winrm_port: int = 5986,
    use_ssl: bool = True,
    validate_certs: bool = False,
    winrm_transport: str = "ntlm",
) -> str:
    """Generate group vars content for enterprise artefacts."""
    return powershell_generators.generate_windows_group_vars(
        ansible_user=ansible_user,
        winrm_port=winrm_port,
        use_ssl=use_ssl,
        validate_certs=validate_certs,
        winrm_transport=winrm_transport,
    )


def generate_ansible_requirements(parsed_ir: dict[str, object] | None = None) -> str:
    """Generate the Ansible requirements file for enterprise artefacts."""
    return powershell_generators.generate_ansible_requirements(parsed_ir)


def generate_powershell_role_structure(
    parsed_ir: dict[str, object],
    role_name: str = "windows_provisioning",
    playbook_name: str = "site",
    hosts: str = "windows",
) -> dict[str, str]:
    """Generate the Ansible role file structure for parsed PowerShell IR."""
    return powershell_generators.generate_powershell_role_structure(
        parsed_ir,
        role_name=role_name,
        playbook_name=playbook_name,
        hosts=hosts,
    )


def generate_powershell_awx_job_template(
    parsed_ir: dict[str, object],
    job_template_name: str = "Windows PowerShell Migration",
    playbook: str = "site.yml",
    inventory: str = "windows-inventory",
    project: str = "windows-migration-project",
    credential_name: str = "windows-winrm-credential",
    environment: str = "production",
    include_survey: bool = True,
) -> str:
    """Generate an AWX job template for Windows automation."""
    return powershell_generators.generate_powershell_awx_job_template(
        parsed_ir,
        job_template_name=job_template_name,
        playbook=playbook,
        inventory=inventory,
        project=project,
        credential_name=credential_name,
        environment=environment,
        include_survey=include_survey,
    )
