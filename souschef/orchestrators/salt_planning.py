"""
Shared Salt migration planning helpers.

Centralises plan rendering and inventory payload shaping so the MCP server
and UI orchestrator expose the same Salt migration behaviour without
duplicated logic.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def build_salt_migration_plan(
    salt_dir: str,
    complexity_json: str,
    timeline_weeks: int = 8,
    target_platform: str = "aap",
) -> str:
    """Build a Salt migration plan from a raw complexity payload."""
    try:
        data = json.loads(complexity_json)
    except json.JSONDecodeError:
        return complexity_json

    if "error" in data:
        return str(data["error"])

    summary = data.get("summary", {})
    complexity_level = summary.get("complexity_level", "medium")
    total_files = summary.get("total_files", 0)
    total_states = summary.get("total_states", 0)
    effort_days = summary.get("estimated_effort_days", 0)
    effort_days_sc = summary.get("estimated_effort_days_with_souschef", 0)
    high_files = summary.get("high_complexity_files", [])
    module_breakdown = summary.get("module_breakdown", {})

    platform_guidance = {
        "aap": (
            "**Target Platform: Ansible Automation Platform (AAP)**\n\n"
            "- Import roles into AAP Execution Environments\n"
            "- Use AAP Projects for SCM-backed role storage\n"
            "- Configure AAP Inventories to replace Salt targeting\n"
            "- Leverage AAP Surveys for parameterised execution\n"
            "- Use AAP Credentials for vault-encrypted pillar data"
        ),
        "awx": (
            "**Target Platform: AWX (Open Source)**\n\n"
            "- Use AWX Projects linked to Git repositories\n"
            "- Configure AWX Inventories using dynamic inventory plugins\n"
            "- Store sensitive pillar data in AWX Credentials\n"
            "- Use AWX Job Templates to replace Salt highstate execution"
        ),
        "ansible_core": (
            "**Target Platform: Ansible Core (CLI)**\n\n"
            "- Run playbooks with `ansible-playbook site.yml`\n"
            "- Use Ansible Vault for sensitive pillar variables\n"
            "- Manage inventory with static or dynamic inventory files\n"
            "- Use `ansible-pull` for decentralised execution similar to Salt minions"
        ),
    }
    platform_text = platform_guidance.get(
        target_platform,
        f"**Target Platform: {target_platform}**\n\nRefer to platform documentation.",
    )

    phase1_weeks = max(1, timeline_weeks // 4)
    phase2_weeks = max(1, timeline_weeks // 4)
    phase3_weeks = max(2, timeline_weeks // 3)
    phase4_weeks = max(
        1,
        timeline_weeks - phase1_weeks - phase2_weeks - phase3_weeks,
    )

    top_modules = sorted(
        module_breakdown.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:5]
    module_list = (
        "\n".join(f"  - `{module}` ({count} states)" for module, count in top_modules)
        if top_modules
        else "  - No modules detected"
    )
    high_files_list = (
        "\n".join(f"  - `{file_name}`" for file_name in high_files[:10])
        if high_files
        else "  - None identified"
    )

    return f"""# SaltStack to Ansible Migration Plan

## Overview

| Metric | Value |
|--------|-------|
| Salt Directory | `{salt_dir}` |
| Total SLS Files | {total_files} |
| Total States | {total_states} |
| Complexity Level | {complexity_level.upper()} |
| Estimated Effort (manual) | {effort_days} days |
| Estimated Effort (with SousChef) | {effort_days_sc} days |
| Target Timeline | {timeline_weeks} weeks |

## Platform Guidance

{platform_text}

## Migration Phases

### Phase 1: Assessment and Preparation (Weeks 1-{phase1_weeks})

**Objectives:** Inventory all Salt states, identify dependencies, set up tooling.

**Tasks:**
- Run `assess_salt_migration_complexity` on all state directories
- Map Salt pillar data to Ansible group_vars/host_vars structure
- Identify custom execution modules requiring Ansible module equivalents
- Set up target {target_platform} environment
- Establish Git repository structure for Ansible roles
- Configure CI/CD pipeline for Ansible testing

### Phase 2: Simple State Conversion

Weeks {phase1_weeks + 1}-{phase1_weeks + phase2_weeks}

**Objectives:** Convert low-complexity SLS files using SousChef automation.

**Tasks:**
- Run `convert_salt_to_ansible` for LOW complexity states
- Run `convert_salt_directory_to_ansible` for batch conversion
- Review and validate generated playbooks
- Test converted roles against development environment
- Convert pillar files using `convert_salt_pillar_to_vars`

### Phase 3: Complex State Conversion

Weeks {phase1_weeks + phase2_weeks + 1}-{phase1_weeks + phase2_weeks + phase3_weeks}

**Objectives:** Tackle medium/high-complexity states requiring manual refinement.

**Tasks:**
- Review high-complexity files manually
- Refine handlers, requisites, and Jinja expressions
- Convert top.sls to inventory using `generate_salt_inventory`
- Build integration tests for converted roles
- Validate idempotency and rollback behaviour

### Phase 4: Cutover and Optimisation

Weeks {phase1_weeks + phase2_weeks + phase3_weeks + 1}-{timeline_weeks}

**Objectives:** Production rollout and operational hardening.

**Tasks:**
- Execute staged cutover by environment
- Compare Salt and Ansible run outputs
- Optimise inventories, variables, and execution patterns
- Retire obsolete Salt states and documentation

## Focus Areas

### Highest-volume modules
{module_list}

### Files needing manual attention
{high_files_list}

### Final hardening window
- Reserve {phase4_weeks} week(s) for cutover, rollback planning, and runbook updates
"""


def build_salt_inventory_payload(
    top_json: str,
    inventory_renderer: Callable[[dict[str, Any]], str],
) -> str:
    """Build an inventory JSON payload from raw top.sls parse output."""
    try:
        top_data = json.loads(top_json)
    except json.JSONDecodeError:
        return json.dumps({"error": top_json})

    if "Error" in top_json and "environments" not in top_data:
        return json.dumps({"error": top_json})

    inventory = inventory_renderer(top_data)
    groups: list[str] = []
    hosts: list[str] = []
    for line in inventory.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            groups.append(stripped[1:-1])
        elif stripped and not stripped.startswith("#") and not stripped.startswith("["):
            hosts.append(stripped)

    return json.dumps(
        {"inventory": inventory, "groups": groups, "hosts": hosts},
        indent=2,
    )
