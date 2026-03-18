"""Orchestration helpers for Puppet migration UI flows."""

from __future__ import annotations

import souschef.converters.puppet_to_ansible as puppet_to_ansible
import souschef.parsers.puppet as puppet_parser


def parse_puppet_manifest(manifest_path: str) -> str:
    """Parse a Puppet manifest for UI analysis."""
    return puppet_parser.parse_puppet_manifest(manifest_path)


def parse_puppet_module(module_path: str) -> str:
    """Parse a Puppet module for UI analysis."""
    return puppet_parser.parse_puppet_module(module_path)


def convert_puppet_manifest_to_ansible(manifest_path: str) -> str:
    """Convert a Puppet manifest to Ansible YAML."""
    return puppet_to_ansible.convert_puppet_manifest_to_ansible(manifest_path)


def convert_puppet_module_to_ansible(module_path: str) -> str:
    """Convert a Puppet module to Ansible YAML."""
    return puppet_to_ansible.convert_puppet_module_to_ansible(module_path)


def convert_puppet_manifest_to_ansible_with_ai(
    manifest_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """Convert a Puppet manifest to Ansible YAML using AI assistance."""
    return puppet_to_ansible.convert_puppet_manifest_to_ansible_with_ai(
        manifest_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        base_url=base_url,
    )


def convert_puppet_module_to_ansible_with_ai(
    module_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """Convert a Puppet module to Ansible YAML using AI assistance."""
    return puppet_to_ansible.convert_puppet_module_to_ansible_with_ai(
        module_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        base_url=base_url,
    )


def get_puppet_ansible_module_map() -> dict[str, str]:
    """Return the Puppet to Ansible module mapping for UI display."""
    return puppet_to_ansible.get_puppet_ansible_module_map()
