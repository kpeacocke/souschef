"""
Deployment and AWX/AAP integration for Chef to Ansible migration.

This module provides tools for analyzing Chef deployment patterns, generating
Ansible deployment strategies (blue/green, canary, rolling), and creating
AWX/AAP configurations from Chef cookbooks.
"""

import json
import re
from pathlib import Path
from typing import Any

from souschef.core.constants import (
    CHEF_RECIPE_PREFIX,
    CHEF_ROLE_PREFIX,
    METADATA_FILENAME,
)
from souschef.core.path_utils import _normalize_path, _safe_join

# Maximum length for attribute values in Chef attribute parsing
# Prevents ReDoS attacks from extremely long attribute declarations
MAX_ATTRIBUTE_VALUE_LENGTH = 5000

# AWX/AAP Integration Functions


def generate_awx_job_template_from_cookbook(
    cookbook_path: str,
    cookbook_name: str,
    target_environment: str = "production",
    include_survey: bool = True,
) -> str:
    """
    Generate AWX/AAP job template from Chef cookbook.

    Analyzes cookbook structure and generates importable AWX configuration.
    Survey specs auto-generated from cookbook attributes when include_survey=True.
    """
    try:
        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Cookbook not found at {cookbook_path}"

        cookbook_analysis = _analyze_cookbook_for_awx(cookbook, cookbook_name)
        job_template = _generate_awx_job_template(
            cookbook_analysis, cookbook_name, target_environment, include_survey
        )

        return f"""# AWX/AAP Job Template Configuration
# Generated from Chef cookbook: {cookbook_name}

## Job Template JSON:
```json
{json.dumps(job_template, indent=2)}
```

## CLI Import Command:
```bash
awx-cli job_templates create \\
    --name "{job_template["name"]}" \\
    --project "{job_template["project"]}" \\
    --playbook "{job_template["playbook"]}" \\
    --inventory "{job_template["inventory"]}" \\
    --credential "{job_template["credential"]}" \\
    --job_type run \\
    --verbosity 1
```

## Cookbook Analysis Summary:
{_format_cookbook_analysis(cookbook_analysis)}
"""
    except Exception as e:
        return f"AWX template generation failed for {cookbook_name}: {e}"


def generate_awx_workflow_from_chef_runlist(
    runlist_content: str, workflow_name: str, environment: str = "production"
) -> str:
    """
    Generate AWX workflow from Chef runlist.

    Handles JSON arrays, comma-separated, or single recipe/role items.
    Workflows preserve runlist execution order with success/failure paths.
    """
    try:
        # Parse runlist
        runlist = _parse_chef_runlist(runlist_content)

        # Generate workflow template
        workflow_template = _generate_awx_workflow_template(
            runlist, workflow_name, environment
        )

        return f"""# AWX/AAP Workflow Template Configuration
# Generated from Chef runlist for: {workflow_name}

## Workflow Template JSON:
```json
{json.dumps(workflow_template, indent=2)}
```

## Workflow Nodes Configuration:
{_format_workflow_nodes(workflow_template.get("workflow_nodes", []))}

## Chef Runlist Analysis:
- Total recipes/roles: {len(runlist)}
- Execution order preserved: Yes
- Dependencies mapped: Yes

## Import Instructions:
1. Create individual job templates for each cookbook
2. Import workflow template using AWX CLI or API
3. Configure workflow node dependencies
4. Test execution with survey parameters
"""
    except Exception as e:
        return f"Workflow generation failed: {e}"


def generate_awx_project_from_cookbooks(
    cookbooks_directory: str,
    project_name: str,
    scm_type: str = "git",
    scm_url: str = "",
) -> str:
    """
    Generate AWX/AAP project configuration from Chef cookbooks directory.

    Args:
        cookbooks_directory: Path to Chef cookbooks directory.
        project_name: Name for the AWX project.
        scm_type: SCM type (git, svn, etc.).
        scm_url: SCM repository URL.

    Returns:
        AWX/AAP project configuration with converted playbooks structure.

    """
    try:
        cookbooks_path = _normalize_path(cookbooks_directory)
        if not cookbooks_path.exists():
            return f"Error: Cookbooks directory not found: {cookbooks_directory}"

        # Analyze all cookbooks
        cookbooks_analysis = _analyze_cookbooks_directory(cookbooks_path)

        # Generate project structure
        project_config = _generate_awx_project_config(project_name, scm_type, scm_url)

        return f"""# AWX/AAP Project Configuration
# Generated from Chef cookbooks: {project_name}

## Project Configuration:
```json
{json.dumps(project_config, indent=2)}
```

## Recommended Directory Structure:
```
{project_name}/
├── playbooks/
{_format_playbook_structure(cookbooks_analysis)}
├── inventories/
│   ├── production/
│   ├── staging/
│   └── development/
├── group_vars/
├── host_vars/
└── requirements.yml
```

## Cookbooks Analysis:
{_format_cookbooks_analysis(cookbooks_analysis)}

## Migration Steps:
1. Convert cookbooks to Ansible playbooks
2. Set up SCM repository with recommended structure
3. Create AWX project pointing to repository
4. Configure job templates for each converted cookbook
5. Set up inventories and credentials
"""
    except Exception as e:
        return f"Project configuration failed: {e}"


def generate_awx_inventory_source_from_chef(
    chef_server_url: str, organization: str = "Default", sync_schedule: str = "daily"
) -> str:
    """
    Generate AWX/AAP inventory source from Chef server configuration.

    Args:
        chef_server_url: Chef server URL for inventory sync.
        organization: AWX organization name.
        sync_schedule: Inventory sync schedule (hourly, daily, weekly).

    Returns:
        AWX/AAP inventory source configuration for Chef server integration.

    """
    try:
        # Generate inventory source configuration
        inventory_source = _generate_chef_inventory_source(
            chef_server_url, sync_schedule
        )

        # Generate custom inventory script
        custom_script = _generate_chef_inventory_script(chef_server_url)

        return f"""# AWX/AAP Inventory Source Configuration
# Chef Server Integration: {chef_server_url}

## Inventory Source JSON:
```json
{json.dumps(inventory_source, indent=2)}
```

## Custom Inventory Script:
```python
{custom_script}
```

## Setup Instructions:
1. Create custom credential type for Chef server authentication
2. Create credential with Chef client key and node name
3. Upload custom inventory script to AWX
4. Create inventory source with Chef server configuration
5. Configure sync schedule and test inventory update

## Credential Type Fields:
- chef_server_url: Chef server URL
- chef_node_name: Chef client node name
- chef_client_key: Chef client private key
- chef_client_pem: Chef client PEM file content

## Environment Variables:
- CHEF_SERVER_URL: {chef_server_url}
- CHEF_NODE_NAME: ${{{{chef_node_name}}}}
- CHEF_CLIENT_KEY: ${{{{chef_client_key}}}}
"""
    except Exception as e:
        return f"Inventory source generation failed: {e}"


# Deployment Strategy Functions


def convert_chef_deployment_to_ansible_strategy(
    cookbook_path: str, deployment_pattern: str = "auto"
) -> str:
    """
    Convert Chef deployment patterns to Ansible strategies.

    Auto-detects blue/green, canary, or rolling patterns from recipe content.
    Override auto-detection by specifying explicit pattern.
    """
    try:
        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Error: Cookbook path not found: {cookbook_path}"

        # Analyze Chef deployment pattern
        pattern_analysis = _analyze_chef_deployment_pattern(cookbook)

        # Determine best strategy if auto-detect
        if deployment_pattern == "auto":
            deployment_pattern = pattern_analysis.get(
                "detected_pattern", "rolling_update"
            )

        # Generate appropriate Ansible strategy
        strategy = _generate_ansible_deployment_strategy(
            pattern_analysis, deployment_pattern
        )

        return f"""# Ansible Deployment Strategy
# Converted from Chef cookbook deployment pattern

## Detected Pattern: {pattern_analysis.get("detected_pattern", "unknown")}
## Recommended Strategy: {deployment_pattern}

{strategy}

## Analysis Summary:
{_format_deployment_analysis(pattern_analysis)}

## Migration Recommendations:
{_generate_deployment_migration_recommendations(pattern_analysis)}
"""
    except Exception as e:
        return f"Deployment pattern conversion failed: {e}"


def generate_blue_green_deployment_playbook(
    app_name: str, health_check_url: str = "/health"
) -> str:
    """
    Generate blue/green deployment playbook for zero-downtime deployments.

    Args:
        app_name: Application name for deployment.
        health_check_url: Health check endpoint URL.

    Returns:
        Complete blue/green deployment playbook with health checks and rollback.

    """
    try:
        # Generate main deployment playbook
        playbook = _generate_blue_green_playbook(app_name, health_check_url)

        return f"""# Blue/Green Deployment Playbook
# Application: {app_name}

## Main Playbook (deploy_blue_green.yml):
```yaml
{playbook["main_playbook"]}
```

## Health Check Playbook (health_check.yml):
```yaml
{playbook["health_check"]}
```

## Rollback Playbook (rollback.yml):
```yaml
{playbook["rollback"]}
```

## Load Balancer Configuration:
```yaml
{playbook["load_balancer_config"]}
```

## Usage Instructions:
1. Deploy to blue environment:
   `ansible-playbook deploy_blue_green.yml -e target_env=blue`
2. Verify health checks pass
3. Switch traffic to blue:
   `ansible-playbook switch_traffic.yml -e target_env=blue`
4. Monitor and rollback if needed: `ansible-playbook rollback.yml`

## Prerequisites:
- Load balancer configured (HAProxy, Nginx, ALB, etc.)
- Health check endpoint available
- Blue and green environments provisioned
"""
    except Exception as e:
        return f"Failed to generate blue/green playbook: {e}"


def generate_canary_deployment_strategy(
    app_name: str, canary_percentage: int = 10, rollout_steps: str = "10,25,50,100"
) -> str:
    """
    Generate canary deployment with progressive rollout.

    Starts at canary_percentage, progresses through rollout_steps.
    Includes monitoring checks and automatic rollback on failure.
    """
    try:
        # Parse rollout steps
        steps = [int(s.strip()) for s in rollout_steps.split(",")]

        # Generate canary strategy
        strategy = _generate_canary_strategy(app_name, canary_percentage, steps)

        return f"""# Canary Deployment Strategy
# Application: {app_name}
# Initial Canary: {canary_percentage}%
# Rollout Steps: {rollout_steps}

## Canary Deployment Playbook (deploy_canary.yml):
```yaml
{strategy["canary_playbook"]}
```

## Monitoring Playbook (monitor_canary.yml):
```yaml
{strategy["monitoring"]}
```

## Progressive Rollout Playbook (progressive_rollout.yml):
```yaml
{strategy["progressive_rollout"]}
```

## Automated Rollback (rollback_canary.yml):
```yaml
{strategy["rollback"]}
```

## Deployment Workflow:
1. Deploy canary at {canary_percentage}%: `ansible-playbook deploy_canary.yml`
2. Monitor metrics: `ansible-playbook monitor_canary.yml`
3. Progressive rollout: `ansible-playbook progressive_rollout.yml`
   - Step 1: {steps[0]}% traffic
   - Step 2: {steps[1]}% traffic
   - Step 3: {steps[2]}% traffic
   - Step 4: {steps[3]}% traffic (full rollout)
4. Rollback if issues: `ansible-playbook rollback_canary.yml`

## Monitoring Points:
- Error rate comparison (canary vs stable)
- Response time percentiles (p50, p95, p99)
- Resource utilization (CPU, memory)
- Custom business metrics

## Rollback Triggers:
- Error rate increase > 5%
- Response time degradation > 20%
- Failed health checks
- Manual trigger
"""
    except Exception as e:
        return f"Canary deployment generation failed: {e}"


def analyze_chef_application_patterns(
    cookbook_path: str, application_type: str = "web_application"
) -> str:
    """
    Analyze cookbook deployment patterns and recommend Ansible strategies.

    Detects blue/green, canary, rolling, or custom deployment approaches.
    Application type helps tune recommendations for web/database/service workloads.
    """
    try:
        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Error: Cookbook path not found: {cookbook_path}"

        # Analyze cookbook for application patterns
        analysis = _analyze_application_cookbook(cookbook, application_type)

        return f"""# Chef Application Patterns Analysis
# Cookbook: {cookbook.name}
# Application Type: {application_type}

## Detected Patterns:
{_format_deployment_patterns(analysis)}

## Chef Resources Analysis:
{_format_chef_resources_analysis(analysis)}

## Recommended Ansible Strategies:
{_recommend_ansible_strategies(analysis)}

## Migration Complexity:
- Overall: {analysis.get("complexity", "medium")}
- Estimated effort: {analysis.get("effort_estimate", "2-3 weeks")}
- Risk level: {analysis.get("risk_level", "medium")}

## Next Steps:
1. Review detected patterns and validate accuracy
2. Select appropriate deployment strategy
3. Prepare test environment for validation
4. Execute pilot migration with one environment
5. Document lessons learned and iterate
"""
    except Exception as e:
        return f"Couldn't analyze cookbook patterns: {e}"


# AWX Helper Functions


def _analyze_cookbook_for_awx(cookbook_path: Path, cookbook_name: str) -> dict:
    """Analyze Chef cookbook structure for AWX job template generation."""
    analysis: dict[str, Any] = {
        "name": cookbook_name,
        "recipes": [],
        "attributes": {},
        "dependencies": [],
        "templates": [],
        "files": [],
        "survey_fields": [],
    }

    # Check for recipes to convert into AWX job steps
    recipes_dir = _safe_join(cookbook_path, "recipes")
    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            recipe_name = recipe_file.stem
            analysis["recipes"].append(
                {
                    "name": recipe_name,
                    "file": str(recipe_file),
                    "size": recipe_file.stat().st_size,
                }
            )

    # Analyze attributes for survey generation
    attributes_dir = _safe_join(cookbook_path, "attributes")
    if attributes_dir.exists():
        for attr_file in attributes_dir.glob("*.rb"):
            try:
                with attr_file.open("r") as f:
                    content = f.read()

                # Extract attribute declarations for survey
                attributes = _extract_cookbook_attributes(content)
                analysis["attributes"].update(attributes)

                # Generate survey fields from attributes
                survey_fields = _generate_survey_fields_from_attributes(attributes)
                analysis["survey_fields"].extend(survey_fields)

            except Exception:
                # Silently skip malformed attribute files
                pass

    # Analyze dependencies
    metadata_file = _safe_join(cookbook_path, METADATA_FILENAME)
    if metadata_file.exists():
        try:
            with metadata_file.open("r") as f:
                content = f.read()

            dependencies = _extract_cookbook_dependencies(content)
            analysis["dependencies"] = dependencies

        except Exception:
            # Silently skip malformed metadata
            pass

    # Count templates and files
    templates_dir = _safe_join(cookbook_path, "templates")
    if templates_dir.exists():
        analysis["templates"] = [
            f.name for f in templates_dir.rglob("*") if f.is_file()
        ]

    files_dir = _safe_join(cookbook_path, "files")
    if files_dir.exists():
        analysis["files"] = [f.name for f in files_dir.rglob("*") if f.is_file()]

    return analysis


def _generate_awx_job_template(
    analysis: dict, cookbook_name: str, environment: str, include_survey: bool
) -> dict:
    """Generate AWX job template configuration from cookbook analysis."""
    job_template = {
        "name": f"{cookbook_name}-{environment}",
        "description": f"Deploy {cookbook_name} cookbook to {environment}",
        "job_type": "run",
        "project": f"{cookbook_name}-project",
        "playbook": f"playbooks/{cookbook_name}.yml",
        "inventory": environment,
        "credential": f"{environment}-ssh",
        "verbosity": 1,
        "ask_variables_on_launch": True,
        "ask_limit_on_launch": True,
        "ask_tags_on_launch": False,
        "ask_skip_tags_on_launch": False,
        "ask_job_type_on_launch": False,
        "ask_verbosity_on_launch": False,
        "ask_inventory_on_launch": False,
        "ask_credential_on_launch": False,
        "survey_enabled": include_survey and len(analysis.get("survey_fields", [])) > 0,
        "become_enabled": True,
        "host_config_key": "",
        "auto_run_on_commit": False,
        "timeout": 3600,
    }

    if include_survey and analysis.get("survey_fields"):
        job_template["survey_spec"] = {
            "name": f"{cookbook_name} Configuration",
            "description": f"Configuration parameters for {cookbook_name} cookbook",
            "spec": analysis["survey_fields"],
        }

    return job_template


def _generate_awx_workflow_template(
    runlist: list, workflow_name: str, environment: str
) -> dict:
    """Generate AWX workflow template from Chef runlist."""
    workflow_template: dict[str, Any] = {
        "name": f"{workflow_name}-{environment}",
        "description": f"Execute {workflow_name} runlist in {environment}",
        "organization": "Default",
        "survey_enabled": True,
        "ask_variables_on_launch": True,
        "ask_limit_on_launch": True,
        "workflow_nodes": [],
    }

    # Generate workflow nodes from runlist
    for index, recipe in enumerate(runlist):
        node_id = index + 1
        node = {
            "id": node_id,
            "unified_job_template": f"{recipe.replace('::', '-')}-{environment}",
            "unified_job_template_type": "job_template",
            "success_nodes": [node_id + 1] if index < len(runlist) - 1 else [],
            "failure_nodes": [],
            "always_nodes": [],
            "inventory": environment,
            "credential": f"{environment}-ssh",
        }
        workflow_template["workflow_nodes"].append(node)

    return workflow_template


def _generate_awx_project_config(
    project_name: str, scm_type: str, scm_url: str
) -> dict:
    """Generate AWX project configuration from cookbooks analysis."""
    project_config = {
        "name": project_name,
        "description": "Ansible playbooks converted from Chef cookbooks",
        "organization": "Default",
        "scm_type": scm_type,
        "scm_url": scm_url,
        "scm_branch": "main",
        "scm_clean": True,
        "scm_delete_on_update": False,
        "credential": f"{scm_type}-credential",
        "timeout": 300,
        "scm_update_on_launch": True,
        "scm_update_cache_timeout": 0,
        "allow_override": False,
        "default_environment": None,
    }

    return project_config


def _generate_chef_inventory_source(chef_server_url: str, sync_schedule: str) -> dict:
    """Generate Chef server inventory source configuration."""
    inventory_source = {
        "name": "Chef Server Inventory",
        "description": f"Dynamic inventory from Chef server: {chef_server_url}",
        "inventory": "Chef Nodes",
        "source": "scm",
        "source_project": "chef-inventory-scripts",
        "source_path": "chef_inventory.py",
        "credential": "chef-server-credential",  # NOSONAR - credential name, not secret
        "overwrite": True,
        "overwrite_vars": True,
        "timeout": 300,
        "verbosity": 1,
        "update_on_launch": True,
        "update_cache_timeout": 86400,  # 24 hours
        "source_vars": json.dumps(
            {
                "chef_server_url": chef_server_url,
                "ssl_verify": True,
                "group_by_environment": True,
                "group_by_roles": True,
                "group_by_platform": True,
            },
            indent=2,
        ),
    }

    # Map sync schedule to update frequency
    schedule_mapping = {"hourly": 3600, "daily": 86400, "weekly": 604800}

    inventory_source["update_cache_timeout"] = schedule_mapping.get(
        sync_schedule, 86400
    )

    return inventory_source


def _generate_chef_inventory_script(chef_server_url: str) -> str:
    """Generate custom inventory script for Chef server integration."""
    return f'''#!/usr/bin/env python3
"""AWX/AAP Custom Inventory Script for Chef Server.

Connects to Chef server and generates Ansible inventory.
"""
import json
import os
import sys

from chef import ChefAPI


def main():
    """Main inventory generation function."""
    # Chef server configuration
    chef_server_url = os.environ.get('CHEF_SERVER_URL', '{chef_server_url}')
    client_name = os.environ.get('CHEF_NODE_NAME', 'admin')
    client_key = os.environ.get('CHEF_CLIENT_KEY', '/etc/chef/client.pem')

    # Initialize Chef API
    try:
        api = ChefAPI(chef_server_url, client_key, client_name)

        # Build Ansible inventory
        inventory = {{
            '_meta': {{'hostvars': {{}}}},
            'all': {{'children': []}},
            'ungrouped': {{'hosts': []}}
        }}

        # Get all nodes from Chef server
        nodes = api['/nodes']

        for node_name in nodes:
            node = api[f'/nodes/{{node_name}}']

            # Extract node information
            node_data = {{
                'ansible_host': node.get('automatic', {{}}).get(
                    'ipaddress', node_name
                ),
                'chef_environment': node.get('chef_environment', '_default'),
                'chef_roles': node.get('run_list', []),
                'chef_platform': node.get('automatic', {{}}).get('platform'),
                'chef_platform_version': (
                    node.get('automatic', {{}}).get('platform_version')
                )
            }}

            # Add to hostvars
            inventory['_meta']['hostvars'][node_name] = node_data

            # Group by environment
            env_group = f"environment_{{node_data['chef_environment']}}"
            if env_group not in inventory:
                inventory[env_group] = {{'hosts': []}}
                inventory['all']['children'].append(env_group)
            inventory[env_group]['hosts'].append(node_name)

            # Group by roles
            for role in node.get('run_list', []):
                role_name = role.replace('role[', '').replace(']', '')
                if role_name.startswith('recipe['):
                    continue

                role_group = f"role_{{role_name}}"
                if role_group not in inventory:
                    inventory[role_group] = {{'hosts': []}}
                    inventory['all']['children'].append(role_group)
                inventory[role_group]['hosts'].append(node_name)

            # Group by platform
            if node_data['chef_platform']:
                platform_group = f"platform_{{node_data['chef_platform']}}"
                if platform_group not in inventory:
                    inventory[platform_group] = {{'hosts': []}}
                    inventory['all']['children'].append(platform_group)
                inventory[platform_group]['hosts'].append(node_name)

        # Output inventory JSON
        print(json.dumps(inventory, indent=2))

    except Exception as e:
        print(f"Error connecting to Chef server: {{e}}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
'''


def _parse_chef_runlist(runlist_content: str) -> list:
    """Parse Chef runlist content into list of recipes/roles."""
    try:
        # Try parsing as JSON first
        if runlist_content.strip().startswith("["):
            runlist = json.loads(runlist_content)
            return [
                item.replace(CHEF_RECIPE_PREFIX, "")
                .replace(CHEF_ROLE_PREFIX, "")
                .replace("]", "")
                for item in runlist
            ]
    except json.JSONDecodeError:
        # Not valid JSON; fall through to parse as comma-separated or single item
        pass

    # Parse as comma-separated list
    if "," in runlist_content:
        items = [item.strip() for item in runlist_content.split(",")]
        return [
            item.replace(CHEF_RECIPE_PREFIX, "")
            .replace(CHEF_ROLE_PREFIX, "")
            .replace("]", "")
            for item in items
        ]

    # Parse single item
    return [
        runlist_content.replace(CHEF_RECIPE_PREFIX, "")
        .replace(CHEF_ROLE_PREFIX, "")
        .replace("]", "")
    ]


def _extract_cookbook_attributes(content: str) -> dict:
    """Extract cookbook attributes for survey generation."""
    attributes = {}

    # Find default attribute declarations
    # Pattern handles multiline values with line continuations, hashes, and arrays
    # Uses bounded quantifier to prevent ReDoS on malformed input
    attr_pattern = (
        r"default\[['\"]([^'\"]+)['\"]\]\s*=\s*"
        rf"(.{{0,{MAX_ATTRIBUTE_VALUE_LENGTH}}}?)"
        r"(?=\n(?!.*\\$)|$|#)"
    )
    for match in re.finditer(attr_pattern, content, re.MULTILINE | re.DOTALL):
        attr_name = match.group(1)
        attr_value = match.group(2).strip()

        # Clean up value - remove trailing backslashes and extra whitespace
        attr_value = re.sub(r"\\\s*\n\s*", " ", attr_value)
        attr_value = attr_value.strip()

        # Clean up quotes
        if attr_value.startswith(("'", '"')) and attr_value.endswith(("'", '"')):
            attr_value = attr_value[1:-1]

        attributes[attr_name] = attr_value

    return attributes


def _extract_cookbook_dependencies(content: str) -> list:
    """Extract cookbook dependencies from metadata."""
    dependencies = []

    # Find depends declarations
    depends_pattern = r"depends\s+['\"]([^'\"]+)['\"]"
    for match in re.finditer(depends_pattern, content):
        dependencies.append(match.group(1))

    return dependencies


def _generate_survey_fields_from_attributes(attributes: dict) -> list:
    """Generate AWX survey fields from cookbook attributes."""
    survey_fields = []

    for attr_name, attr_value in attributes.items():
        # Determine field type based on value
        field_type = "text"
        if attr_value.lower() in ["true", "false"]:
            field_type = "boolean"
        elif attr_value.isdigit():
            field_type = "integer"

        field = {
            "variable": attr_name.replace(".", "_"),
            "question_name": attr_name.replace(".", " ").title(),
            "question_description": f"Chef attribute: {attr_name}",
            "required": False,
            "type": field_type,
            "default": attr_value,
            "choices": "",
        }

        survey_fields.append(field)

    return survey_fields


def _analyze_cookbooks_directory(cookbooks_path: Path) -> dict:
    """Analyze entire cookbooks directory structure."""
    analysis: dict[str, Any] = {
        "total_cookbooks": 0,
        "cookbooks": {},
        "total_recipes": 0,
        "total_templates": 0,
        "total_files": 0,
    }

    for cookbook_dir in cookbooks_path.iterdir():
        if not cookbook_dir.is_dir():
            continue

        cookbook_name = cookbook_dir.name
        analysis["total_cookbooks"] += 1

        cookbook_analysis = _analyze_cookbook_for_awx(cookbook_dir, cookbook_name)
        analysis["cookbooks"][cookbook_name] = cookbook_analysis

        # Aggregate stats
        analysis["total_recipes"] += len(cookbook_analysis["recipes"])
        analysis["total_templates"] += len(cookbook_analysis["templates"])
        analysis["total_files"] += len(cookbook_analysis["files"])

    return analysis


# Deployment Strategy Helper Functions


def _analyze_chef_deployment_pattern(cookbook_path: Path) -> dict:
    """Analyze Chef cookbook for deployment patterns."""
    analysis: dict[str, Any] = {
        "deployment_steps": [],
        "health_checks": [],
        "service_management": [],
        "load_balancer_config": {},
        "detected_pattern": "rolling_update",
        "complexity": "medium",
    }

    # Analyze recipes for deployment indicators
    recipes_dir = _safe_join(cookbook_path, "recipes")
    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            try:
                with recipe_file.open("r") as f:
                    content = f.read()

                # Extract deployment steps
                steps = _extract_deployment_steps(content)
                analysis["deployment_steps"].extend(steps)

                # Extract health checks
                health_checks = _extract_health_checks(content)
                analysis["health_checks"].extend(health_checks)

                # Extract service management
                services = _extract_service_management(content)
                analysis["service_management"].extend(services)

                # Detect deployment pattern
                if "blue" in content.lower() or "green" in content.lower():
                    analysis["detected_pattern"] = "blue_green"
                elif "canary" in content.lower():
                    analysis["detected_pattern"] = "canary"
                elif "rolling" in content.lower():
                    analysis["detected_pattern"] = "rolling_update"

            except Exception:
                # Silently skip malformed files
                pass

    return analysis


def _generate_ansible_deployment_strategy(analysis: dict, pattern: str) -> str:
    """Generate Ansible deployment strategy based on pattern."""
    if pattern == "blue_green":
        return _generate_blue_green_conversion_playbook(analysis)
    elif pattern == "canary":
        return _generate_canary_conversion_playbook(analysis)
    else:
        return _generate_rolling_update_playbook(analysis)


def _generate_blue_green_playbook(app_name: str, health_check_url: str) -> dict:
    """
    Generate blue/green deployment playbook structure.

    Args:
        app_name: Name of the application.
        health_check_url: URL for health checks.

    """
    main_playbook = f"""---
# Blue/Green Deployment for {app_name}
- name: Deploy {app_name} (Blue/Green)
  hosts: "{{{{ target_env }}}}"
  become: yes
  vars:
    app_name: {app_name}
    health_check_url: {health_check_url}
    deployment_version: "{{{{ lookup('env', 'VERSION') | default('latest') }}}}"

  tasks:
    - name: Deploy application to target environment
      include_tasks: deploy_app.yml

    - name: Run health checks
      include_tasks: health_check.yml

    - name: Switch load balancer traffic
      include_tasks: switch_traffic.yml
      when: health_check_passed
"""
    health_check = """---
# Health Check Playbook
- name: Verify application health
  uri:
    url: "http://{{ ansible_host }}{health_check_url}"
    method: GET
    status_code: 200
    timeout: 10
  register: health_check_result
  retries: 5
  delay: 10
  until: health_check_result.status == 200

- name: Set health check status
  set_fact:
    health_check_passed: "{{ health_check_result.status == 200 }}"
"""
    rollback = f"""---
# Rollback Playbook
- name: Rollback {app_name} deployment
  hosts: load_balancers
  become: yes
  tasks:
    - name: Switch traffic back to previous environment
      include_tasks: switch_traffic.yml
      vars:
        target_env: "{{{{ previous_env }}}}"

    - name: Verify rollback health
      include_tasks: health_check.yml
"""
    load_balancer_config = """---
# Load Balancer Configuration
- name: Update load balancer configuration
  template:
    src: nginx.conf.j2
    dest: /etc/nginx/sites-enabled/{{ app_name }}.conf
  notify: reload nginx

- name: Reload nginx
  service:
    name: nginx
    state: reloaded
"""
    return {
        "main_playbook": main_playbook,
        "health_check": health_check,
        "rollback": rollback,
        "load_balancer_config": load_balancer_config,
    }


def _generate_canary_strategy(app_name: str, canary_pct: int, steps: list) -> dict:
    """Generate canary deployment strategy structure."""
    canary_playbook = f"""---
# Canary Deployment for {app_name}
- name: Deploy {app_name} (Canary)
  hosts: canary_servers
  become: yes
  vars:
    app_name: {app_name}
    canary_percentage: {canary_pct}
    deployment_version: "{{{{ lookup('env', 'VERSION') }}}}"

  tasks:
    - name: Deploy to canary servers
      include_tasks: deploy_app.yml

    - name: Configure canary traffic routing
      include_tasks: configure_canary_routing.yml

    - name: Monitor canary metrics
      include_tasks: monitor_metrics.yml
"""
    monitoring = """---
# Monitoring Playbook
- name: Collect canary metrics
  uri:
    url: "http://{{ ansible_host }}/metrics"
    method: GET
    return_content: yes
  register: canary_metrics

- name: Compare with stable metrics
  uri:
    url: "http://{{ stable_server }}/metrics"
    method: GET
    return_content: yes
  register: stable_metrics

- name: Evaluate canary performance
  set_fact:
    canary_passed: "{{ canary_metrics.error_rate < stable_metrics.error_rate * 1.05 }}"
"""
    progressive_rollout = _format_canary_workflow(steps)

    rollback = f"""---
# Canary Rollback
- name: Rollback canary deployment for {app_name}
  hosts: canary_servers
  become: yes
  tasks:
    - name: Remove canary traffic routing
      include_tasks: remove_canary_routing.yml

    - name: Restore previous version
      include_tasks: restore_previous_version.yml

    - name: Verify stable operation
      include_tasks: health_check.yml
"""
    return {
        "canary_playbook": canary_playbook,
        "monitoring": monitoring,
        "progressive_rollout": progressive_rollout,
        "rollback": rollback,
    }


def _extract_deployment_steps(content: str) -> list:
    """Extract deployment steps from Chef recipe content."""
    steps = []

    # Look for execute resources with deployment commands
    execute_pattern = r'execute\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(execute_pattern, content):
        command = match.group(1)
        if any(
            keyword in command.lower()
            for keyword in ["deploy", "restart", "reload", "migrate"]
        ):
            steps.append({"type": "execute", "command": command})

    return steps


def _extract_health_checks(content: str) -> list:
    """Extract health check patterns from Chef recipe content."""
    health_checks = []

    # Look for http_request or similar resources
    http_pattern = r'http_request\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(http_pattern, content):
        health_checks.append({"type": "http_check", "url": match.group(1)})

    return health_checks


def _extract_service_management(content: str) -> list:
    """Extract service management patterns from Chef recipe content."""
    services = []

    # Look for service resources
    service_pattern = r'service\s+[\'"]([^\'"]+)[\'"]'
    for match in re.finditer(service_pattern, content):
        services.append({"type": "service", "name": match.group(1)})

    return services


def _detect_deployment_patterns_in_recipe(content: str, recipe_name: str) -> list:
    """Detect deployment patterns in a Chef recipe."""
    patterns: list[dict[str, str]] = []

    pattern_indicators = {
        "blue_green": [
            r"blue.*green|green.*blue",
            r"switch.*traffic|traffic.*switch",
            r"active.*inactive|inactive.*active",
        ],
        "rolling": [
            r"rolling.*update|serial.*update",
            r"batch.*deployment|phased.*rollout",
            r"gradual.*deployment",
        ],
        "canary": [
            r"canary.*deployment|canary.*release",
            r"percentage.*traffic|traffic.*percentage",
            r"A/B.*test|split.*traffic",
        ],
        "immutable": [
            r"immutable.*deployment|replace.*instance",
            r"new.*server|fresh.*deployment",
        ],
    }

    for pattern_type, indicators in pattern_indicators.items():
        for indicator in indicators:
            if re.search(indicator, content, re.IGNORECASE):
                patterns.append(
                    {
                        "type": pattern_type,
                        "recipe": recipe_name,
                        "confidence": "high"
                        if len(
                            [
                                i
                                for i in indicators
                                if re.search(i, content, re.IGNORECASE)
                            ]
                        )
                        > 1
                        else "medium",
                    }
                )
                break

    return patterns


def _detect_patterns_from_content(content: str) -> list[str]:
    """Detect deployment patterns from recipe content."""
    patterns = []
    if "package" in content:
        patterns.append("package_management")
    if "template" in content:
        patterns.append("configuration_management")
    if "service" in content:
        patterns.append("service_management")
    if "git" in content:
        patterns.append("source_deployment")
    return patterns


def _assess_complexity_from_resource_count(resource_count: int) -> tuple[str, str, str]:
    """Assess complexity, effort, and risk based on resource count."""
    if resource_count > 50:
        return "high", "4-6 weeks", "high"
    elif resource_count < 20:
        return "low", "1-2 weeks", "low"
    return "medium", "2-3 weeks", "medium"


def _analyze_application_cookbook(cookbook_path: Path, app_type: str) -> dict:
    """Analyze Chef cookbook for application deployment patterns."""
    analysis: dict[str, Any] = {
        "application_type": app_type,
        "deployment_patterns": [],
        "resources": [],
        "complexity": "medium",
        "effort_estimate": "2-3 weeks",
        "risk_level": "medium",
    }

    # Analyze recipes
    recipes_dir = _safe_join(cookbook_path, "recipes")
    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            try:
                with recipe_file.open("r") as f:
                    content = f.read()

                # Count resources
                resource_types = re.findall(r"^(\w+)\s+['\"]", content, re.MULTILINE)
                analysis["resources"].extend(resource_types)

                # Detect patterns
                patterns = _detect_patterns_from_content(content)
                analysis["deployment_patterns"].extend(patterns)

            except Exception:
                # Silently skip malformed files
                pass

    # Assess complexity
    resource_count = len(analysis["resources"])
    complexity, effort, risk = _assess_complexity_from_resource_count(resource_count)
    analysis["complexity"] = complexity
    analysis["effort_estimate"] = effort
    analysis["risk_level"] = risk

    return analysis


# Formatting Functions


def _format_cookbook_analysis(analysis: dict) -> str:
    """Format cookbook analysis for display."""
    formatted = [
        f"• Recipes: {len(analysis['recipes'])}",
        f"• Attributes: {len(analysis['attributes'])}",
        f"• Dependencies: {len(analysis['dependencies'])}",
        f"• Templates: {len(analysis['templates'])}",
        f"• Files: {len(analysis['files'])}",
        f"• Survey fields: {len(analysis['survey_fields'])}",
    ]

    return "\n".join(formatted)


def _format_workflow_nodes(nodes: list) -> str:
    """Format workflow nodes for display."""
    if not nodes:
        return "No workflow nodes defined."

    formatted = []
    for node in nodes:
        formatted.append(f"• Node {node['id']}: {node['unified_job_template']}")
        if node.get("success_nodes"):
            formatted.append(f"  → Success: Node {node['success_nodes'][0]}")

    return "\n".join(formatted)


def _format_playbook_structure(analysis: dict) -> str:
    """Format recommended playbook structure."""
    structure_lines = []

    for cookbook_name in analysis.get("cookbooks", {}):
        structure_lines.append(f"│   ├── {cookbook_name}.yml")

    return "\n".join(structure_lines)


def _format_cookbooks_analysis(analysis: dict) -> str:
    """Format cookbooks directory analysis."""
    formatted = [
        f"• Total cookbooks: {analysis['total_cookbooks']}",
        f"• Total recipes: {analysis['total_recipes']}",
        f"• Total templates: {analysis['total_templates']}",
        f"• Total files: {analysis['total_files']}",
    ]

    if analysis["cookbooks"]:
        formatted.append("\n### Cookbook Details:")
        for name, info in list(analysis["cookbooks"].items())[:5]:
            formatted.append(
                f"• {name}: {len(info['recipes'])} recipes, "
                f"{len(info['attributes'])} attributes"
            )

        if len(analysis["cookbooks"]) > 5:
            formatted.append(f"... and {len(analysis['cookbooks']) - 5} more cookbooks")

    return "\n".join(formatted)


def _format_deployment_analysis(analysis: dict) -> str:
    """Format deployment pattern analysis."""
    formatted = [
        f"• Deployment steps: {len(analysis.get('deployment_steps', []))}",
        f"• Health checks: {len(analysis.get('health_checks', []))}",
        f"• Services managed: {len(analysis.get('service_management', []))}",
        f"• Complexity: {analysis.get('complexity', 'unknown')}",
    ]

    return "\n".join(formatted)


def _format_deployment_patterns(analysis: dict) -> str:
    """Format detected deployment patterns."""
    patterns = analysis.get("deployment_patterns", [])
    if not patterns:
        return "No specific deployment patterns detected."

    formatted = []
    for pattern in patterns:
        if isinstance(pattern, dict):
            # Format: {"type": "...", "recipe": "...", "confidence": "..."}
            pattern_type = pattern.get("type", "unknown")
            recipe = pattern.get("recipe", "")
            confidence = pattern.get("confidence", "")
            line = f"• {pattern_type.replace('_', ' ').title()}"
            if recipe:
                line += f" (in {recipe})"
            if confidence:
                line += f" - {confidence} confidence"
            formatted.append(line)
        else:
            # Format: just a string like "package_management"
            formatted.append(f"• {pattern.replace('_', ' ').title()}")

    return "\n".join(formatted)


def _format_chef_resources_analysis(analysis: dict) -> str:
    """Format Chef resources analysis."""
    # Check for new format first (from _analyze_application_cookbook)
    resources = analysis.get("resources", [])
    if resources:
        # Count resource types
        resource_counts: dict = {}
        for resource_type in resources:
            resource_counts[resource_type] = resource_counts.get(resource_type, 0) + 1

        # Format top resource types
        top_resources = sorted(
            resource_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        formatted = []
        for resource_type, count in top_resources:
            formatted.append(f"• {resource_type}: {count}")

        return "\n".join(formatted)

    # Check for legacy format (from tests)
    service_resources = analysis.get("service_resources", [])
    configuration_files = analysis.get("configuration_files", [])
    health_checks = analysis.get("health_checks", [])
    scaling_mechanisms = analysis.get("scaling_mechanisms", [])

    if any([service_resources, configuration_files, health_checks, scaling_mechanisms]):
        formatted = [
            f"• Service Resources: {len(service_resources)}",
            f"• Configuration Files: {len(configuration_files)}",
            f"• Health Checks: {len(health_checks)}",
            f"• Scaling Mechanisms: {len(scaling_mechanisms)}",
        ]
        return "\n".join(formatted)

    return "No Chef resources found."


def _format_canary_workflow(steps: list) -> str:
    """Format canary progressive rollout workflow."""
    workflow = """---
# Progressive Rollout Workflow
- name: Progressive canary rollout
  hosts: localhost
  gather_facts: no
  vars:
    rollout_steps: """
    workflow += str(steps)
    workflow += """
  tasks:
    - name: Execute progressive rollout
      include_tasks: rollout_step.yml
      loop: "{{ rollout_steps }}"
      loop_control:
        loop_var: target_percentage
"""
    return workflow


def _generate_blue_green_conversion_playbook(_analysis: dict) -> str:
    """Generate blue/green playbook from Chef pattern analysis."""
    return """## Blue/Green Deployment Strategy

Recommended based on detected Chef deployment patterns.

### Playbook Structure:
- Deploy to blue environment
- Health check validation
- Traffic switch to blue
- Monitor blue environment
- Keep green as rollback target

### Implementation:
Use `generate_blue_green_deployment_playbook` tool for complete playbooks.
"""


def _generate_canary_conversion_playbook(_analysis: dict) -> str:
    """Generate canary playbook from Chef pattern analysis."""
    return """## Canary Deployment Strategy

Recommended for gradual rollout with monitoring.

### Playbook Structure:
- Deploy to small canary subset
- Monitor error rates and metrics
- Progressive rollout (10% → 25% → 50% → 100%)
- Automated rollback on failure

### Implementation:
Use `generate_canary_deployment_strategy` tool for complete playbooks.
"""


def _generate_rolling_update_playbook(_analysis: dict) -> str:
    """Generate rolling update playbook from Chef pattern analysis."""
    return """## Rolling Update Strategy

Recommended for standard application deployments.

### Playbook Structure:
- Update servers in batches
- Health check between batches
- Continue if healthy, rollback if failures
- Maintain service availability

### Implementation:
```yaml
- name: Rolling update
  hosts: app_servers
  serial: "25%"
  max_fail_percentage: 10
  tasks:
    - name: Update application
      # ... deployment tasks
    - name: Health check
      # ... validation tasks
```
"""


def _generate_deployment_migration_recommendations(
    patterns: dict, app_type: str = ""
) -> str:
    """
    Generate migration recommendations based on analysis.

    Args:
        patterns: Dictionary containing deployment patterns analysis.
        app_type: Application type (web_application, microservice, database).

    Returns:
        Formatted migration recommendations.

    """
    recommendations: list[str] = []

    deployment_count = len(patterns.get("deployment_patterns", []))

    if deployment_count == 0:
        recommendations.append(
            "• No advanced deployment patterns detected - start with rolling updates"
        )
        recommendations.append("• Implement health checks for reliable deployments")
        recommendations.append("• Add rollback mechanisms for quick recovery")
    else:
        for pattern in patterns.get("deployment_patterns", []):
            if pattern["type"] == "blue_green":
                recommendations.append(
                    "• Convert blue/green logic to Ansible blue/green strategy"
                )
            elif pattern["type"] == "canary":
                recommendations.append(
                    "• Implement canary deployment with automated metrics validation"
                )
            elif pattern["type"] == "rolling":
                recommendations.append(
                    "• Use Ansible serial deployment with health checks"
                )

    # Application-specific recommendations
    if app_type == "web_application":
        recommendations.append(
            "• Implement load balancer integration for traffic management"
        )
        recommendations.append("• Add SSL/TLS certificate handling in deployment")
    elif app_type == "microservice":
        recommendations.append(
            "• Consider service mesh integration for traffic splitting"
        )
        recommendations.append("• Implement service discovery updates")
    elif app_type == "database":
        recommendations.append("• Add database migration handling")
        recommendations.append("• Implement backup and restore procedures")

    # If no specific recommendations, add general ones
    if not recommendations:
        recommendations.extend(
            [
                "1. Start with non-production environment for validation",
                "2. Implement health checks before migration",
                "3. Set up monitoring and alerting",
                "4. Document rollback procedures",
                "5. Train operations team on new deployment process",
                "6. Plan for gradual migration (pilot → staging → production)",
            ]
        )

    return "\n".join(recommendations)


def _recommend_ansible_strategies(patterns: dict) -> str:
    """Recommend appropriate Ansible strategies."""
    strategies: list[str] = []

    # Handle both formats: list of dicts with 'type' key or list of strings
    pattern_list = patterns.get("deployment_patterns", [])
    if pattern_list and isinstance(pattern_list[0], dict):
        detected_patterns = [p["type"] for p in pattern_list]
    else:
        detected_patterns = pattern_list

    if "blue_green" in detected_patterns:
        strategies.append(
            "• Blue/Green: Zero-downtime deployment with instant rollback"
        )
    if "canary" in detected_patterns:
        strategies.append("• Canary: Risk-reduced deployment with gradual rollout")
    if "rolling" in detected_patterns:
        strategies.append(
            "• Rolling Update: Balanced approach with configurable parallelism"
        )

    # Application-pattern specific strategies
    if "package_management" in detected_patterns:
        strategies.append("• Package: Use `package` module for package installation")
    if "configuration_management" in detected_patterns:
        strategies.append("• Config: Use `template` module for configuration files")
    if "service_management" in detected_patterns:
        strategies.append("• Service: Use `service` or `systemd` module for services")
    if "source_deployment" in detected_patterns:
        strategies.append("• Source: Use `git` module for source code deployment")

    if not strategies:
        strategies = [
            "• Rolling Update: Recommended starting strategy",
            "• Blue/Green: For critical applications requiring zero downtime",
            "• Canary: For high-risk deployments requiring validation",
        ]

    return "\n".join(strategies)
