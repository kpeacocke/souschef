"""Bash migration API facade."""

from souschef.orchestrators.bash import (
    convert_bash_content_to_ansible,
    generate_ansible_role_from_bash,
    parse_bash_script_content,
)

__all__ = [
    "convert_bash_content_to_ansible",
    "generate_ansible_role_from_bash",
    "parse_bash_script_content",
]
