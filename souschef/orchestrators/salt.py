"""Orchestration helpers for Salt migration UI flows."""

from __future__ import annotations

import souschef.converters.salt as salt_converter
import souschef.parsers.salt as salt_parser
from souschef.orchestrators.salt_planning import (
    build_salt_inventory_payload,
    build_salt_migration_plan,
)


def parse_salt_sls(sls_path: str) -> str:
    """Parse a Salt SLS file for UI display."""
    return salt_parser.parse_salt_sls(sls_path)


def convert_salt_sls_to_ansible(
    sls_path: str,
    playbook_name: str = "salt_migration",
) -> str:
    """Convert a Salt SLS file to Ansible YAML."""
    return salt_converter.convert_salt_sls_to_ansible(sls_path, playbook_name)


def parse_salt_pillar(pillar_path: str) -> str:
    """Parse a Salt pillar file for UI display."""
    return salt_parser.parse_salt_pillar(pillar_path)


def parse_salt_directory(salt_dir: str) -> str:
    """Parse a Salt state directory for UI display."""
    return salt_parser.parse_salt_directory(salt_dir)


def assess_salt_complexity(salt_dir: str) -> str:
    """Assess Salt migration complexity for UI display."""
    return salt_parser.assess_salt_complexity(salt_dir)


def convert_salt_directory_to_roles(salt_dir: str, output_dir: str) -> str:
    """Convert a Salt state directory into an Ansible roles structure."""
    return salt_converter.convert_salt_directory_to_roles(salt_dir, output_dir)


def plan_salt_migration(
    salt_dir: str,
    timeline_weeks: int = 8,
    target_platform: str = "aap",
) -> str:
    """Generate a Salt-to-Ansible migration plan from assessed complexity."""
    complexity_json = salt_parser.assess_salt_complexity(salt_dir)
    return build_salt_migration_plan(
        salt_dir=salt_dir,
        complexity_json=complexity_json,
        timeline_weeks=timeline_weeks,
        target_platform=target_platform,
    )


def generate_salt_inventory(top_path: str) -> str:
    """Generate an Ansible inventory from a Salt top.sls file."""
    top_json = salt_parser.parse_salt_top(top_path)
    return build_salt_inventory_payload(
        top_json=top_json,
        inventory_renderer=salt_converter.top_to_ansible_inventory,
    )
