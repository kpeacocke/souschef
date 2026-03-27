"""Orchestration helpers for Bash migration UI flows."""

from __future__ import annotations

from typing import Any

import souschef.converters.bash_to_ansible as bash_to_ansible
import souschef.parsers.bash as bash_parser


def parse_bash_script_content(content: str) -> dict[str, Any]:
    """Parse Bash script content for UI display."""
    return bash_parser.parse_bash_script_content(content)


def convert_bash_content_to_ansible(
    content: str,
    script_path: str = "script.sh",
) -> str:
    """Convert Bash script content to an Ansible playbook response."""
    return bash_to_ansible.convert_bash_content_to_ansible(
        content,
        script_path=script_path,
    )


def generate_ansible_role_from_bash(
    content: str,
    role_name: str = "bash_converted",
    script_path: str = "script.sh",
) -> str:
    """Generate an Ansible role structure from Bash script content."""
    return bash_to_ansible.generate_ansible_role_from_bash(
        content,
        role_name=role_name,
        script_path=script_path,
    )
