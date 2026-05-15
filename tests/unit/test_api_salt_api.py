"""Coverage tests for Salt API facade exports."""

from __future__ import annotations

from souschef.api import salt_api
from souschef.orchestrators import salt as salt_orchestrator


def test_salt_api_reexports_orchestrator_functions() -> None:
    """Salt API symbols should point to orchestrator implementations."""
    assert salt_api.assess_salt_complexity is salt_orchestrator.assess_salt_complexity
    assert (
        salt_api.convert_salt_directory_to_roles
        is salt_orchestrator.convert_salt_directory_to_roles
    )
    assert (
        salt_api.convert_salt_sls_to_ansible
        is salt_orchestrator.convert_salt_sls_to_ansible
    )
    assert salt_api.generate_salt_inventory is salt_orchestrator.generate_salt_inventory
    assert salt_api.parse_salt_directory is salt_orchestrator.parse_salt_directory
    assert salt_api.parse_salt_pillar is salt_orchestrator.parse_salt_pillar
    assert salt_api.parse_salt_sls is salt_orchestrator.parse_salt_sls
    assert salt_api.plan_salt_migration is salt_orchestrator.plan_salt_migration


def test_salt_api_all_exports_expected_symbols() -> None:
    """``__all__`` should advertise all public Salt API symbols."""
    assert salt_api.__all__ == [
        "assess_salt_complexity",
        "convert_salt_directory_to_roles",
        "convert_salt_sls_to_ansible",
        "generate_salt_inventory",
        "parse_salt_directory",
        "parse_salt_pillar",
        "parse_salt_sls",
        "plan_salt_migration",
    ]
