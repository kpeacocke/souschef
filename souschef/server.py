"""SousChef MCP Server - Chef to Ansible conversion assistant."""

import ast
import json
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Import assessment functions with aliases to avoid name conflicts
from souschef.assessment import (
    analyze_cookbook_dependencies as _analyze_cookbook_dependencies,
)
from souschef.assessment import (
    assess_chef_migration_complexity as _assess_chef_migration_complexity,
)
from souschef.assessment import (
    generate_migration_plan as _generate_migration_plan,
)
from souschef.assessment import (
    generate_migration_report as _generate_migration_report,
)
from souschef.assessment import (
    validate_conversion as _validate_conversion,
)

# Import extracted modules
# Import private helper functions still used in server.py
from souschef.converters.habitat import (  # noqa: F401
    _add_service_build,
    _add_service_dependencies,
    _add_service_environment,
    _add_service_ports,
    _add_service_volumes,
    _build_compose_service,
    _extract_default_port,
    _map_habitat_deps_to_apt,
    _needs_data_volume,
    _validate_docker_image_name,
    _validate_docker_network_name,
)
from souschef.converters.habitat import (
    convert_habitat_to_dockerfile as _convert_habitat_to_dockerfile,
)
from souschef.converters.habitat import (
    generate_compose_from_habitat as _generate_compose_from_habitat,
)

# Re-exports of playbook internal functions for backward compatibility (tests)
from souschef.converters.playbook import (  # noqa: F401
    _add_general_recommendations,
    _convert_chef_block_to_ansible,
    _convert_chef_condition_to_ansible,
    _convert_guards_to_when_conditions,
    _create_handler,
    _create_handler_with_timing,
    _determine_query_complexity,
    _extract_chef_guards,
    _extract_enhanced_notifications,
    _extract_guard_patterns,
    _extract_search_patterns_from_cookbook,
    _extract_search_patterns_from_file,
    _find_search_patterns_in_content,
    _generate_ansible_inventory_from_search,
    _generate_group_name_from_condition,
    _generate_inventory_script_content,
    _get_current_timestamp,
    _parse_chef_search_query,
    _parse_guard_array,
    _parse_search_condition,
    _process_subscribes,
)

# Import playbook converter functions
from souschef.converters.playbook import (
    analyze_chef_search_patterns as _analyze_chef_search_patterns,
)
from souschef.converters.playbook import (
    convert_chef_search_to_inventory as _convert_chef_search_to_inventory,
)
from souschef.converters.playbook import (
    generate_dynamic_inventory_script as _generate_dynamic_inventory_script,
)
from souschef.converters.playbook import (
    generate_playbook_from_recipe as _generate_playbook_from_recipe,
)
from souschef.converters.resource import (  # noqa: F401
    _convert_chef_resource_to_ansible,
    _format_ansible_task,
    _get_file_params,
    _get_service_params,
)
from souschef.converters.resource import (
    convert_resource_to_task as _convert_resource_to_task,
)

# Re-exports for backward compatibility (used by tests) - DO NOT REMOVE
# These imports are intentionally exposed for external test access
from souschef.core.constants import (  # noqa: F401
    ACTION_TO_STATE,
    ANSIBLE_SERVICE_MODULE,
    ERROR_PREFIX,
    REGEX_RESOURCE_BRACKET,
    RESOURCE_MAPPINGS,
)

# Import core utilities
from souschef.core.path_utils import _normalize_path, _safe_join  # noqa: F401

# Re-exports for backward compatibility (used by tests) - DO NOT REMOVE
# These imports are intentionally exposed for external test access
from souschef.core.ruby_utils import (  # noqa: F401
    _normalize_ruby_value,
)

# Re-exports for backward compatibility (used by tests) - DO NOT REMOVE
# These imports are intentionally exposed for external test access
from souschef.core.validation import (  # noqa: F401
    ValidationCategory,
    ValidationEngine,
    ValidationLevel,
    ValidationResult,
)

# Import validation framework
# Re-exports of deployment internal functions for backward compatibility (tests)
# Public re-exports of deployment functions for test backward compatibility
# Note: MCP tool wrappers exist for some of these, but tests import directly
from souschef.deployment import (  # noqa: F401
    _analyze_cookbook_for_awx,
    _analyze_cookbooks_directory,
    _detect_deployment_patterns_in_recipe,
    _extract_cookbook_attributes,
    _extract_cookbook_dependencies,
    _format_chef_resources_analysis,
    _format_cookbook_analysis,
    _format_deployment_patterns,
    _generate_deployment_migration_recommendations,
    _generate_survey_fields_from_attributes,
    _parse_chef_runlist,
    _recommend_ansible_strategies,
    analyze_chef_application_patterns,
    convert_chef_deployment_to_ansible_strategy,
    generate_awx_inventory_source_from_chef,
    generate_awx_job_template_from_cookbook,
    generate_awx_project_from_cookbooks,
    generate_awx_workflow_from_chef_runlist,
    generate_blue_green_deployment_playbook,
    generate_canary_deployment_strategy,
)

# Re-exports for backward compatibility (used by tests)
# These are imported and re-exported intentionally
from souschef.deployment import (
    analyze_chef_application_patterns as _analyze_chef_application_patterns,
)
from souschef.deployment import (
    convert_chef_deployment_to_ansible_strategy as _convert_chef_deployment_to_ansible_strategy,
)
from souschef.deployment import (
    generate_awx_inventory_source_from_chef as _generate_awx_inventory_source_from_chef,
)
from souschef.deployment import (
    generate_awx_job_template_from_cookbook as _generate_awx_job_template_from_cookbook,
)
from souschef.deployment import (
    generate_awx_project_from_cookbooks as _generate_awx_project_from_cookbooks,
)
from souschef.deployment import (
    generate_awx_workflow_from_chef_runlist as _generate_awx_workflow_from_chef_runlist,
)
from souschef.deployment import (
    generate_blue_green_deployment_playbook as _generate_blue_green_deployment_playbook,
)
from souschef.deployment import (
    generate_canary_deployment_strategy as _generate_canary_deployment_strategy,
)

# Import filesystem operations
from souschef.filesystem import list_directory as _list_directory
from souschef.filesystem import read_file as _read_file
from souschef.parsers.attributes import (  # noqa: F401
    _extract_attributes,
    _format_attributes,
    _format_resolved_attributes,
    _get_precedence_level,
    _resolve_attribute_precedence,
)

# Import parser functions
from souschef.parsers.attributes import parse_attributes as _parse_attributes
from souschef.parsers.habitat import (  # noqa: F401
    _extract_plan_array,
    _extract_plan_exports,
    _extract_plan_function,
    _extract_plan_var,
    _update_quote_state,
)

# Import Habitat parser internal functions for backward compatibility
from souschef.parsers.habitat import parse_habitat_plan as _parse_habitat_plan

# Re-export InSpec internal functions for backward compatibility (tests)
from souschef.parsers.inspec import (  # noqa: F401
    _convert_inspec_to_ansible_assert,
    _convert_inspec_to_testinfra,
    _extract_inspec_describe_blocks,
    _generate_inspec_from_resource,
    _parse_inspec_control,
)
from souschef.parsers.metadata import (  # noqa: F401
    _extract_metadata,
    _format_cookbook_structure,
    _format_metadata,
)
from souschef.parsers.metadata import (
    list_cookbook_structure as _list_cookbook_structure,
)
from souschef.parsers.metadata import read_cookbook_metadata as _read_cookbook_metadata
from souschef.parsers.recipe import (  # noqa: F401
    _extract_conditionals,
    _extract_resources,
    _format_resources,
)
from souschef.parsers.recipe import parse_recipe as _parse_recipe
from souschef.parsers.resource import (  # noqa: F401
    _extract_resource_actions,
    _extract_resource_properties,
)
from souschef.parsers.resource import parse_custom_resource as _parse_custom_resource
from souschef.parsers.template import (  # noqa: F401
    _convert_erb_to_jinja2,
    _extract_code_block_variables,
    _extract_heredoc_strings,
    _extract_node_attribute_path,
    _extract_output_variables,
    _extract_template_variables,
    _strip_ruby_comments,
)

# Import internal functions for backward compatibility (used by tests)
from souschef.parsers.template import parse_template as _parse_template

# Create a new FastMCP server
mcp = FastMCP("souschef")

# Error message templates
ERROR_FILE_NOT_FOUND = "Error: File not found at {path}"
ERROR_IS_DIRECTORY = "Error: {path} is a directory, not a file"
ERROR_PERMISSION_DENIED = "Error: Permission denied for {path}"

# Validation Framework Classes


@mcp.tool()
def parse_template(path: str) -> str:
    """
    Parse a Chef ERB template file and convert to Jinja2.

    Args:
        path: Path to the ERB template file.

    Returns:
        JSON string with extracted variables and Jinja2-converted template.

    """
    return _parse_template(path)


@mcp.tool()
def parse_custom_resource(path: str) -> str:
    """
    Parse a Chef custom resource or LWRP file.

    Args:
        path: Path to the custom resource (.rb) file.

    Returns:
        JSON string with extracted properties, actions, and metadata.

    """
    return _parse_custom_resource(path)


@mcp.tool()
def list_directory(path: str) -> list[str] | str:
    """
    List the contents of a directory.

    Args:
        path: The path to the directory to list.

    Returns:
        A list of filenames in the directory, or an error message.

    """
    result: list[str] | str = _list_directory(path)
    return result


@mcp.tool()
def read_file(path: str) -> str:
    """
    Read the contents of a file.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file, or an error message.

    """
    result: str = _read_file(path)
    return result


@mcp.tool()
def read_cookbook_metadata(path: str) -> str:
    """
    Parse Chef cookbook metadata.rb file.

    Args:
        path: Path to the metadata.rb file.

    Returns:
        Formatted string with extracted metadata.

    """
    return _read_cookbook_metadata(path)


@mcp.tool()
def parse_recipe(path: str) -> str:
    """
    Parse a Chef recipe file and extract resources.

    Args:
        path: Path to the recipe (.rb) file.

    Returns:
        Formatted string with extracted Chef resources and their properties.

    """
    return _parse_recipe(path)


@mcp.tool()
def parse_attributes(path: str, resolve_precedence: bool = True) -> str:
    """
    Parse a Chef attributes file and extract attribute definitions.

    Analyzes attributes file and extracts all attribute definitions with their
    precedence levels and values. By default, resolves precedence conflicts
    to show the winning value for each attribute path.

    Chef attribute precedence (lowest to highest):
    1. default - Normal default value
    2. force_default - Forced default, higher than regular default
    3. normal - Normal attribute set by cookbook
    4. override - Override values
    5. force_override - Forced override, cannot be overridden
    6. automatic - Automatically detected by Ohai (highest precedence)

    Args:
        path: Path to the attributes (.rb) file.
        resolve_precedence: If True (default), resolves precedence conflicts
            and shows only winning values. If False, shows all attributes.

    Returns:
        Formatted string with extracted attributes.

    """
    return _parse_attributes(path, resolve_precedence)


@mcp.tool()
def list_cookbook_structure(path: str) -> str:
    """
    List the structure of a Chef cookbook directory.

    Args:
        path: Path to the cookbook root directory.

    Returns:
        Formatted string showing the cookbook structure.

    """
    return _list_cookbook_structure(path)


@mcp.tool()
def convert_resource_to_task(
    resource_type: str, resource_name: str, action: str = "create", properties: str = ""
) -> str:
    """
    Convert a Chef resource to an Ansible task.

    Args:
        resource_type: The Chef resource type (e.g., 'package', 'service').
        resource_name: The name of the resource.
        action: The Chef action (e.g., 'install', 'start', 'create').
        properties: Additional resource properties as a string representation.

    Returns:
        YAML representation of the equivalent Ansible task.

    """
    return _convert_resource_to_task(resource_type, resource_name, action, properties)


def _extract_resource_subscriptions(
    resource: dict[str, str], raw_content: str
) -> list[dict[str, str]]:
    """
    Extract subscription information with timing constraints for a resource.

    Args:
        resource: Resource dictionary.
        raw_content: Raw recipe content.

    Returns:
        List of subscription dictionaries with timing information.

    """
    subscriptions = []

    # Enhanced subscribes pattern that captures timing
    subscribes_pattern = re.compile(
        r'subscribes\s+:(\w+),\s*[\'"]([^\'"]+)[\'"](?:\s*,\s*:(\w+))?', re.IGNORECASE
    )

    # Find all subscribes declarations
    subscribes_matches = subscribes_pattern.findall(raw_content)

    for action, target, timing in subscribes_matches:
        # Parse target like 'service[nginx]' or 'template[/etc/nginx/nginx.conf]'
        target_match = re.match(REGEX_RESOURCE_BRACKET, target)
        if target_match:
            target_type = target_match.group(1)
            target_name = target_match.group(2)

            # Check if this resource is what the subscription refers to
            if resource["type"] == target_type and resource["name"] == target_name:
                subscriptions.append(
                    {
                        "action": action,
                        "resource_type": target_type,
                        "resource_name": target_name,
                        "timing": timing
                        or "delayed",  # Default to delayed if not specified
                    }
                )

    return subscriptions


@mcp.tool()
def _parse_controls_from_directory(profile_path: Path) -> list[dict[str, Any]]:
    """
    Parse all control files from an InSpec profile directory.

    Args:
        profile_path: Path to the InSpec profile directory.

    Returns:
        List of parsed controls.

    Raises:
        FileNotFoundError: If controls directory doesn't exist.
        RuntimeError: If error reading control files.

    """
    controls_dir = _safe_join(profile_path, "controls")
    if not controls_dir.exists():
        raise FileNotFoundError(f"No controls directory found in {profile_path}")

    controls = []
    for control_file in controls_dir.glob("*.rb"):
        try:
            content = control_file.read_text()
            file_controls = _parse_inspec_control(content)
            for ctrl in file_controls:
                ctrl["file"] = str(control_file.relative_to(profile_path))
            controls.extend(file_controls)
        except Exception as e:
            raise RuntimeError(f"Error reading {control_file}: {e}") from e

    return controls


def _parse_controls_from_file(profile_path: Path) -> list[dict[str, Any]]:
    """
    Parse controls from a single InSpec control file.

    Args:
        profile_path: Path to the control file.

    Returns:
        List of parsed controls.

    Raises:
        RuntimeError: If error reading the file.

    """
    try:
        content = profile_path.read_text()
        controls = _parse_inspec_control(content)
        for ctrl in controls:
            ctrl["file"] = profile_path.name
        return controls
    except Exception as e:
        raise RuntimeError(f"Error reading file: {e}") from e


def parse_inspec_profile(path: str) -> str:
    """
    Parse an InSpec profile and extract controls.

    Args:
        path: Path to InSpec profile directory or control file (.rb).

    Returns:
        JSON string with parsed controls, or error message.

    """
    try:
        profile_path = _normalize_path(path)

        if not profile_path.exists():
            return f"Error: Path does not exist: {path}"

        if profile_path.is_dir():
            controls = _parse_controls_from_directory(profile_path)
        elif profile_path.is_file():
            controls = _parse_controls_from_file(profile_path)
        else:
            return f"Error: Invalid path type: {path}"

        return json.dumps(
            {
                "profile_path": str(profile_path),
                "controls_count": len(controls),
                "controls": controls,
            },
            indent=2,
        )

    except (FileNotFoundError, RuntimeError) as e:
        return f"Error: {e}"
    except Exception as e:
        return f"An error occurred while parsing InSpec profile: {e}"


@mcp.tool()
def convert_inspec_to_test(inspec_path: str, output_format: str = "testinfra") -> str:
    """
    Convert InSpec controls to Ansible test format.

    Args:
        inspec_path: Path to InSpec profile or control file.
        output_format: Output format ('testinfra' or 'ansible_assert').

    Returns:
        Converted test code or error message.

    """
    try:
        # First parse the InSpec profile
        parse_result = parse_inspec_profile(inspec_path)

        # Check if parsing failed
        if parse_result.startswith(ERROR_PREFIX):
            return parse_result

        # Parse JSON result
        profile_data = json.loads(parse_result)
        controls = profile_data["controls"]

        if not controls:
            return "Error: No controls found in InSpec profile"

        # Convert each control
        converted_tests = []

        if output_format == "testinfra":
            converted_tests.append("import pytest")
            converted_tests.append("")
            converted_tests.append("")
            for control in controls:
                test_code = _convert_inspec_to_testinfra(control)
                converted_tests.append(test_code)

        elif output_format == "ansible_assert":
            converted_tests.append("---")
            converted_tests.append("# Validation tasks converted from InSpec")
            converted_tests.append("")
            for control in controls:
                assert_code = _convert_inspec_to_ansible_assert(control)
                converted_tests.append(assert_code)
                converted_tests.append("")

        else:
            error_msg = (
                f"Error: Unsupported format '{output_format}'. "
                "Use 'testinfra' or 'ansible_assert'"
            )
            return error_msg

        return "\n".join(converted_tests)

    except Exception as e:
        return f"An error occurred while converting InSpec: {e}"


def _extract_resources_from_parse_result(parse_result: str) -> list[dict[str, Any]]:
    """
    Extract resource data from recipe parse result.

    Args:
        parse_result: Output from parse_recipe function.

    Returns:
        List of resource dictionaries with type, name, and properties.

    """
    resources = []
    current_resource: dict[str, Any] = {}

    for line in parse_result.split("\n"):
        line = line.strip()

        if line.startswith("Resource"):
            if current_resource:
                resources.append(current_resource)
            current_resource = {}
        elif line.startswith("Type:"):
            current_resource["type"] = line.split(":", 1)[1].strip()
        elif line.startswith("Name:"):
            current_resource["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("Properties:"):
            # Parse properties dict
            props_str = line.split(":", 1)[1].strip()
            try:
                current_resource["properties"] = ast.literal_eval(props_str)
            except Exception:
                current_resource["properties"] = {}

    if current_resource:
        resources.append(current_resource)

    return resources


@mcp.tool()
def generate_inspec_from_recipe(recipe_path: str) -> str:
    """
    Generate InSpec controls from a Chef recipe.

    Args:
        recipe_path: Path to Chef recipe file.

    Returns:
        InSpec control code or error message.

    """
    try:
        # First parse the recipe
        recipe_result: str = parse_recipe(recipe_path)

        if recipe_result.startswith(ERROR_PREFIX):
            return recipe_result

        # Extract resources from parsed output
        resources = _extract_resources_from_parse_result(recipe_result)

        if not resources:
            return "Error: No resources found in recipe"

        # Generate InSpec controls
        controls = [
            "# InSpec controls generated from Chef recipe",
            f"# Source: {recipe_path}",
            "",
        ]

        for resource in resources:
            if "type" in resource and "name" in resource:
                control_code: str = _generate_inspec_from_resource(
                    resource["type"],
                    resource["name"],
                    resource.get("properties", {}),
                )
                controls.append(control_code)

        return "\n".join(controls)

    except Exception as e:
        return f"An error occurred while generating InSpec controls: {e}"


@mcp.tool()
def convert_chef_databag_to_vars(
    databag_content: str,
    databag_name: str,
    item_name: str = "default",
    is_encrypted: bool = False,
    target_scope: str = "group_vars",
) -> str:
    """
    Convert Chef data bag to Ansible variables format.

    Args:
        databag_content: JSON content of the Chef data bag
        databag_name: Name of the data bag
        item_name: Name of the data bag item (default: "default")
        is_encrypted: Whether the data bag is encrypted
        target_scope: Variable scope ("group_vars", "host_vars", or "playbook")

    Returns:
        Ansible variables YAML content or vault file structure

    """
    try:
        import yaml

        # Parse the data bag content
        try:
            parsed_databag = json.loads(databag_content)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format in data bag: {e}"

        # Convert to Ansible variables format
        ansible_vars = _convert_databag_to_ansible_vars(
            parsed_databag, databag_name, item_name, is_encrypted
        )

        if is_encrypted:
            # Generate vault file structure
            vault_content = _generate_vault_content(ansible_vars, databag_name)
            return f"""# Encrypted data bag converted to Ansible Vault
# Original: data_bags/{databag_name}/{item_name}.json
# Usage: ansible-vault encrypt {target_scope}/{databag_name}_vault.yml

{vault_content}

---
# Instructions:
# 1. Save this content to {target_scope}/{databag_name}_vault.yml
# 2. Encrypt with: ansible-vault encrypt {target_scope}/{databag_name}_vault.yml
# 3. Reference in playbooks with: vars_files:
#    - "{target_scope}/{databag_name}_vault.yml"
"""
        else:
            # Generate regular YAML variables
            yaml_content = yaml.dump(ansible_vars, default_flow_style=False, indent=2)
            # yaml.dump adds a trailing newline, so we strip it and add back a single newline
            return f"""---
# Chef data bag converted to Ansible variables
# Original: data_bags/{databag_name}/{item_name}.json
# Target: {target_scope}/{databag_name}.yml

{yaml_content.rstrip()}
"""
    except Exception as e:
        return f"Error converting data bag to Ansible variables: {e}"


@mcp.tool()
def generate_ansible_vault_from_databags(
    databags_directory: str,
    output_directory: str = "group_vars",
    encryption_key_hint: str = "",
) -> str:
    """
    Generate Ansible Vault files from Chef data bags directory.

    Args:
        databags_directory: Path to Chef data_bags directory
        output_directory: Target directory for Ansible variables (group_vars/host_vars)
        encryption_key_hint: Hint for identifying encrypted data bags

    Returns:
        Summary of converted data bags and instructions

    """
    try:
        databags_path = _normalize_path(databags_directory)
        if not databags_path.exists():
            return f"Error: Data bags directory not found: {databags_directory}"

        conversion_results = []

        # Process each data bag directory
        for databag_dir in databags_path.iterdir():
            if not databag_dir.is_dir():
                continue

            databag_name = databag_dir.name

            # Process each item in the data bag
            for item_file in databag_dir.glob("*.json"):
                item_name = item_file.stem

                try:
                    with item_file.open() as f:
                        content = f.read()

                    # Detect if encrypted (Chef encrypted data bags have specific structure)
                    is_encrypted = _detect_encrypted_databag(content)

                    # Convert to Ansible format
                    result = convert_chef_databag_to_vars(
                        content, databag_name, item_name, is_encrypted, output_directory
                    )

                    vault_suffix = "_vault" if is_encrypted else ""
                    target_file = f"{output_directory}/{databag_name}{vault_suffix}.yml"
                    conversion_results.append(
                        {
                            "databag": databag_name,
                            "item": item_name,
                            "encrypted": is_encrypted,
                            "target_file": target_file,
                            "content": result,
                        }
                    )

                except Exception as e:
                    conversion_results.append(
                        {"databag": databag_name, "item": item_name, "error": str(e)}
                    )

        # Generate summary and file structure
        return _generate_databag_conversion_summary(
            conversion_results, output_directory
        )

    except Exception as e:
        return f"Error processing data bags directory: {e}"


@mcp.tool()
def analyze_chef_databag_usage(cookbook_path: str, databags_path: str = "") -> str:
    """
    Analyze Chef cookbook for data bag usage and provide migration recommendations.

    Args:
        cookbook_path: Path to Chef cookbook
        databags_path: Optional path to data_bags directory for cross-reference

    Returns:
        Analysis of data bag usage and migration recommendations

    """
    try:
        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Error: Cookbook path not found: {cookbook_path}"

        # Find data bag usage patterns
        usage_patterns = _extract_databag_usage_from_cookbook(cookbook)

        # Analyze data bags structure if provided
        databag_structure = {}
        if databags_path:
            databags = _normalize_path(databags_path)
            if databags.exists():
                databag_structure = _analyze_databag_structure(databags)

        # Generate recommendations
        recommendations = _generate_databag_migration_recommendations(
            usage_patterns, databag_structure
        )

        return f"""# Chef Data Bag Usage Analysis

## Data Bag Usage Patterns Found:
{_format_usage_patterns(usage_patterns)}

## Data Bag Structure Analysis:
{_format_databag_structure(databag_structure)}

## Migration Recommendations:
{recommendations}

## Conversion Steps:
1. Use convert_chef_databag_to_vars for individual data bags
2. Use generate_ansible_vault_from_databags for bulk conversion
3. Update playbooks to reference new variable files
4. Encrypt sensitive data with ansible-vault
"""
    except Exception as e:
        return f"Data bag parsing failed: {e}"


@mcp.tool()
def convert_chef_environment_to_inventory_group(
    environment_content: str, environment_name: str, include_constraints: bool = True
) -> str:
    """
    Convert Chef environment to Ansible inventory group with variables.

    Args:
        environment_content: Ruby content of the Chef environment file
        environment_name: Name of the Chef environment
        include_constraints: Whether to include cookbook version constraints

    Returns:
        Ansible inventory group configuration with variables

    """
    try:
        # Parse Chef environment content
        env_data = _parse_chef_environment_content(environment_content)

        # Convert to Ansible inventory group format
        inventory_config = _generate_inventory_group_from_environment(
            env_data, environment_name, include_constraints
        )

        return f"""---
# Chef environment converted to Ansible inventory group
# Original: environments/{environment_name}.rb
# Target: inventory/group_vars/{environment_name}.yml

{inventory_config.rstrip()}


---
# Add to your Ansible inventory (hosts.yml or hosts.ini):
# [{environment_name}]
# # Add your hosts here
#
# [all:children]
# {environment_name}
"""
    except Exception as e:
        return f"Environment conversion failed: {e}"


@mcp.tool()
def generate_inventory_from_chef_environments(
    environments_directory: str, output_format: str = "yaml"
) -> str:
    """
    Generate complete Ansible inventory from Chef environments directory.

    Args:
        environments_directory: Path to Chef environments directory
        output_format: Output format ("yaml", "ini", or "both")

    Returns:
        Complete Ansible inventory structure with environment-based groups

    """
    try:
        env_path = _normalize_path(environments_directory)
        if not env_path.exists():
            return f"Error: Environments directory not found: {environments_directory}"

        # Process all environment files
        environments = {}
        processing_results = []

        for env_file in env_path.glob("*.rb"):
            env_name = env_file.stem

            try:
                with env_file.open("r") as f:
                    content = f.read()

                env_data = _parse_chef_environment_content(content)
                environments[env_name] = env_data

                processing_results.append(
                    {
                        "environment": env_name,
                        "status": "success",
                        "attributes": len(env_data.get("default_attributes", {})),
                        "overrides": len(env_data.get("override_attributes", {})),
                        "constraints": len(env_data.get("cookbook_versions", {})),
                    }
                )

            except Exception as e:
                processing_results.append(
                    {"environment": env_name, "status": "error", "error": str(e)}
                )

        # Generate inventory structure
        return _generate_complete_inventory_from_environments(
            environments, processing_results, output_format
        )

    except Exception as e:
        return f"Error generating inventory from Chef environments: {e}"


@mcp.tool()
def analyze_chef_environment_usage(
    cookbook_path: str, environments_path: str = ""
) -> str:
    """
    Analyze Chef cookbook for environment usage.

    Provides migration recommendations.

    Args:
        cookbook_path: Path to Chef cookbook
        environments_path: Optional path to environments directory for cross-reference

    Returns:
        Analysis of environment usage and migration recommendations

    """
    try:
        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Error: Cookbook path not found: {cookbook_path}"

        # Find environment usage patterns
        usage_patterns = _extract_environment_usage_from_cookbook(cookbook)

        # Analyze environments structure if provided
        environment_structure = {}
        if environments_path:
            environments = _normalize_path(environments_path)
            if environments.exists():
                environment_structure = _analyze_environments_structure(environments)

        # Generate recommendations
        recommendations = _generate_environment_migration_recommendations(
            usage_patterns, environment_structure
        )

        return f"""# Chef Environment Usage Analysis

## Environment Usage Patterns Found:
{_format_environment_usage_patterns(usage_patterns)}

## Environment Structure Analysis:
{_format_environment_structure(environment_structure)}

## Migration Recommendations:
{recommendations}

## Conversion Steps:
1. Use convert_chef_environment_to_inventory_group for individual environments
2. Use generate_inventory_from_chef_environments for complete inventory
3. Update playbooks to use group_vars for environment-specific variables
4. Implement variable precedence hierarchy in Ansible
5. Test environment-specific deployments with new inventory structure
"""
    except Exception as e:
        return f"Error analyzing Chef environment usage: {e}"


def _parse_chef_environment_content(content: str) -> dict:
    """Parse Chef environment Ruby content into structured data."""
    env_data = {
        "name": "",
        "description": "",
        "default_attributes": {},
        "override_attributes": {},
        "cookbook_versions": {},
    }

    # Extract name
    name_match = re.search(r"name\s+['\"]([^'\"\n]{0,150})['\"]", content)
    if name_match:
        env_data["name"] = name_match.group(1)

    # Extract description
    desc_match = re.search(r"description\s+['\"]([^'\"\n]{0,300})['\"]", content)
    if desc_match:
        env_data["description"] = desc_match.group(1)

    # Extract default attributes
    default_attrs = _extract_attributes_block(content, "default_attributes")
    if default_attrs:
        env_data["default_attributes"] = default_attrs

    # Extract override attributes
    override_attrs = _extract_attributes_block(content, "override_attributes")
    if override_attrs:
        env_data["override_attributes"] = override_attrs

    # Extract cookbook version constraints
    constraints = _extract_cookbook_constraints(content)
    if constraints:
        env_data["cookbook_versions"] = constraints

    return env_data


def _extract_attributes_block(content: str, block_type: str) -> dict:
    """Extract attribute blocks from Chef environment content."""
    # Find the block start
    pattern = rf"{block_type}\s*\((.{{0,2000}}?)\)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {}

    block_content = match.group(1).strip()

    # Simple parsing of Ruby hash-like structure
    # Ruby attribute hashes use => syntax, which we convert to Python dict
    # This is intentionally simple - complex Chef DSL needs full Ruby parser
    attributes = {}

    # Parse simple key-value pairs like 'port' => '8080'
    key_value_pattern = (
        r"['\"]([^'\"]{0,100})['\"][\s:]*=>[\s:]*['\"]([^'\"]{0,200})['\"]"
    )
    for match in re.finditer(key_value_pattern, block_content):
        attr_key = match.group(1)
        attr_value = match.group(2)
        attributes[attr_key] = attr_value

    # Parse nested structures (basic support)
    nested_pattern = (
        r"['\"](([^'\"\n]{0,100}))['\"](\\s|:)*=>(\\s|:)*\\{([^}]{0,500})\\}"
    )
    for match in re.finditer(nested_pattern, block_content):
        key = match.group(1)
        nested_content = match.group(5)
        nested_attrs = {}

        for nested_match in re.finditer(key_value_pattern, nested_content):
            nested_key = nested_match.group(1)
            nested_value = nested_match.group(2)
            nested_attrs[nested_key] = nested_value

        if nested_attrs:
            attributes[key] = nested_attrs

    return attributes


def _extract_cookbook_constraints(content: str) -> dict:
    """Extract cookbook version constraints from Chef environment."""
    constraints = {}

    # Find cookbook version constraints
    cookbook_pattern = (
        r"cookbook\s+['\"]([^'\"\n]{0,100})['\"]\,\s*['\"]([^'\"\n]{0,50})['\"]"
    )
    for match in re.finditer(cookbook_pattern, content):
        cookbook = match.group(1)
        version = match.group(2)
        constraints[cookbook] = version

    return constraints


def _generate_inventory_group_from_environment(
    env_data: dict, env_name: str, include_constraints: bool
) -> str:
    """Generate Ansible inventory group configuration from environment data."""
    import yaml

    group_vars: dict[str, Any] = {}

    # Add environment metadata
    group_vars["environment_name"] = env_name
    group_vars["environment_description"] = env_data.get("description", "")

    # Convert default attributes to group variables
    default_attrs = env_data.get("default_attributes", {})
    if default_attrs:
        group_vars.update(default_attrs)

    # Add override attributes with higher precedence indication
    override_attrs = env_data.get("override_attributes", {})
    if override_attrs:
        group_vars["environment_overrides"] = override_attrs

    # Add cookbook constraints if requested
    if include_constraints:
        cookbook_versions = env_data.get("cookbook_versions", {})
        if cookbook_versions:
            group_vars["cookbook_version_constraints"] = cookbook_versions

    # Add Chef-to-Ansible mapping metadata
    group_vars["chef_migration_metadata"] = {
        "source_environment": env_name,
        "converted_by": "souschef",
        "variable_precedence": ("group_vars (equivalent to Chef default_attributes)"),
        "overrides_location": (
            "environment_overrides (requires extra_vars or host_vars)"
        ),
    }

    return yaml.dump(group_vars, default_flow_style=False, indent=2)


def _generate_complete_inventory_from_environments(
    environments: dict, results: list, output_format: str
) -> str:
    """Generate complete Ansible inventory from multiple Chef environments."""
    import yaml

    summary = f"""# Chef Environments to Ansible Inventory Conversion

## Processing Summary:
- Total environments processed: {len(results)}
- Successfully converted: {len([r for r in results if r["status"] == "success"])}
- Failed conversions: {len([r for r in results if r["status"] == "error"])}

## Environment Details:
"""
    for result in results:
        if result["status"] == "success":
            summary += (
                f"✅ {result['environment']}: {result['attributes']} attributes, "
            )
            summary += (
                f"{result['overrides']} overrides, "
                f"{result['constraints']} constraints\n"
            )
        else:
            summary += f"❌ {result['environment']}: {result['error']}\n"

    if output_format in ["yaml", "both"]:
        summary += "\n## YAML Inventory Structure:\n\n```yaml\n"

        # Generate YAML inventory
        inventory: dict[str, Any] = {"all": {"children": {}}}

        for env_name, env_data in environments.items():
            inventory["all"]["children"][env_name] = {
                "hosts": {},  # Hosts to be added manually
                "vars": _flatten_environment_vars(env_data),
            }

        summary += yaml.dump(inventory, default_flow_style=False, indent=2)
        summary += "```\n"

    if output_format in ["ini", "both"]:
        summary += "\n## INI Inventory Structure:\n\n```ini\n"
        summary += "[all:children]\n"
        for env_name in environments:
            summary += f"{env_name}\n"

        summary += "\n"
        for env_name in environments:
            summary += f"[{env_name}]\n"
            summary += "# Add your hosts here\n\n"

        summary += "```\n"

    summary += """
## Next Steps:
1. Create group_vars directory structure
2. Add environment-specific variable files
3. Populate inventory with actual hosts
4. Update playbooks to reference environment groups
5. Test variable precedence and override behavior

## File Structure to Create:
"""
    for env_name in environments:
        summary += f"- inventory/group_vars/{env_name}.yml\n"

    return summary


def _flatten_environment_vars(env_data: dict) -> dict:
    """Flatten environment data for inventory variables."""
    vars_dict = {}

    # Add basic metadata
    vars_dict["environment_name"] = env_data.get("name", "")
    vars_dict["environment_description"] = env_data.get("description", "")

    # Add default attributes
    default_attrs = env_data.get("default_attributes", {})
    vars_dict.update(default_attrs)

    # Add override attributes in a separate namespace
    override_attrs = env_data.get("override_attributes", {})
    if override_attrs:
        vars_dict["environment_overrides"] = override_attrs

    # Add cookbook constraints
    cookbook_versions = env_data.get("cookbook_versions", {})
    if cookbook_versions:
        vars_dict["cookbook_version_constraints"] = cookbook_versions

    return vars_dict


def _extract_environment_usage_from_cookbook(cookbook_path) -> list:
    """Extract environment usage patterns from Chef cookbook files."""
    patterns = []

    # Search for environment usage in Ruby files
    for ruby_file in cookbook_path.rglob("*.rb"):
        try:
            with ruby_file.open("r") as f:
                content = f.read()

            # Find environment usage patterns
            found_patterns = _find_environment_patterns_in_content(
                content, str(ruby_file)
            )
            patterns.extend(found_patterns)

        except Exception as e:
            patterns.append(
                {"file": str(ruby_file), "error": f"Could not read file: {e}"}
            )

    return patterns


def _find_environment_patterns_in_content(content: str, file_path: str) -> list:
    """Find environment usage patterns in file content."""
    patterns = []

    # Common Chef environment patterns
    environment_patterns = [
        (r"node\.chef_environment", "node.chef_environment"),
        (r"node\[['\"]\environment['\"]\]", 'node["environment"]'),
        (r"environment\s+['\"]([^'\"\n]{0,100})['\"]", "environment declaration"),
        (
            r"if\s+node\.chef_environment\s*==\s*['\"]([^'\"\n]{0,100})['\"]",
            "environment conditional",
        ),
        (r"case\s+node\.chef_environment", "environment case statement"),
        (r"search\([^)]*environment[^)]*\)", "environment in search query"),
    ]

    for pattern, pattern_type in environment_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1

            patterns.append(
                {
                    "file": file_path,
                    "line": line_num,
                    "type": pattern_type,
                    "match": match.group(0),
                    "environment_name": match.group(1)
                    if match.groups() and match.group(1)
                    else None,
                }
            )

    return patterns


def _analyze_environments_structure(environments_path) -> dict:
    """Analyze the structure of Chef environments directory."""
    structure: dict[str, Any] = {"total_environments": 0, "environments": {}}

    for env_file in environments_path.glob("*.rb"):
        structure["total_environments"] += 1
        env_name = env_file.stem

        try:
            with env_file.open("r") as f:
                content = f.read()

            env_data = _parse_chef_environment_content(content)

            structure["environments"][env_name] = {
                "name": env_data.get("name", env_name),
                "description": env_data.get("description", ""),
                "default_attributes_count": len(env_data.get("default_attributes", {})),
                "override_attributes_count": len(
                    env_data.get("override_attributes", {})
                ),
                "cookbook_constraints_count": len(
                    env_data.get("cookbook_versions", {})
                ),
                "size": env_file.stat().st_size,
            }

        except Exception as e:
            structure["environments"][env_name] = {"error": str(e)}

    return structure


def _analyze_usage_pattern_recommendations(usage_patterns: list) -> list[str]:
    """Analyze usage patterns and generate recommendations."""
    if not usage_patterns:
        return []

    recommendations = []
    environment_refs = [p for p in usage_patterns if "environment" in p.get("type", "")]
    conditional_usage = [
        p
        for p in usage_patterns
        if "conditional" in p.get("type", "") or "case" in p.get("type", "")
    ]

    recommendations.append(
        f"• Found {len(usage_patterns)} environment references in cookbook"
    )

    if environment_refs:
        recommendations.append(
            f"• {len(environment_refs)} direct environment attribute "
            f"accesses need inventory group conversion"
        )

    if conditional_usage:
        recommendations.append(
            f"• {len(conditional_usage)} conditional environment logic "
            f"needs when/group_names conditions"
        )

    return recommendations


def _analyze_structure_recommendations(env_structure: dict) -> list[str]:
    """Analyze environment structure and generate recommendations."""
    if not env_structure:
        return []

    total_envs = env_structure.get("total_environments", 0)
    if total_envs == 0:
        return []

    recommendations = [
        f"• Convert {total_envs} Chef environments to Ansible inventory groups"
    ]

    # Find complex environments
    complex_envs = [
        env_name
        for env_name, env_info in env_structure.get("environments", {}).items()
        if "error" not in env_info
        and env_info.get("default_attributes_count", 0)
        + env_info.get("override_attributes_count", 0)
        > 10
    ]

    if complex_envs:
        recommendations.append(
            f"• {len(complex_envs)} environments have >10 attributes - "
            f"consider splitting into logical variable groups"
        )

    return recommendations


def _get_general_migration_recommendations() -> list[str]:
    """Get standard migration recommendations."""
    return [
        "• Use Ansible groups to replace Chef environment-based node targeting",
        "• Convert Chef default_attributes to group_vars",
        "• Handle Chef override_attributes with extra_vars or host_vars",
        "• Implement environment-specific playbook execution with --limit",
        "• Test variable precedence matches Chef behavior",
        "• Consider using Ansible environments/staging for deployment workflows",
    ]


def _generate_environment_migration_recommendations(
    usage_patterns: list, env_structure: dict
) -> str:
    """Generate migration recommendations based on environment usage analysis."""
    recommendations = []
    recommendations.extend(_analyze_usage_pattern_recommendations(usage_patterns))
    recommendations.extend(_analyze_structure_recommendations(env_structure))
    recommendations.extend(_get_general_migration_recommendations())

    return "\n".join(recommendations)


def _format_environment_usage_patterns(patterns: list) -> str:
    """Format environment usage patterns for display."""
    if not patterns:
        return "No environment usage patterns found."

    formatted = []
    for pattern in patterns[:15]:  # Limit to first 15 for readability
        if "error" in pattern:
            formatted.append(f"❌ {pattern['file']}: {pattern['error']}")
        else:
            env_info = (
                f" (env: {pattern['environment_name']})"
                if pattern.get("environment_name")
                else ""
            )
            formatted.append(
                f"• {pattern['type']} in {pattern['file']}:{pattern['line']}{env_info}"
            )

    if len(patterns) > 15:
        formatted.append(f"... and {len(patterns) - 15} more patterns")

    return "\n".join(formatted)


def _format_environment_structure(structure: dict) -> str:
    """Format environment structure analysis for display."""
    if not structure:
        return "No environment structure provided for analysis."

    formatted = [f"• Total environments: {structure['total_environments']}"]

    if structure["environments"]:
        formatted.append("\n### Environment Details:")
        for name, info in list(structure["environments"].items())[
            :8
        ]:  # Limit for readability
            if "error" in info:
                formatted.append(f"❌ {name}: {info['error']}")
            else:
                attrs = info.get("default_attributes_count", 0)
                overrides = info.get("override_attributes_count", 0)
                constraints = info.get("cookbook_constraints_count", 0)
                formatted.append(
                    f"• {name}: {attrs} attributes, {overrides} overrides, "
                    f"{constraints} constraints"
                )

        if len(structure["environments"]) > 8:
            formatted.append(
                f"... and {len(structure['environments']) - 8} more environments"
            )

    return "\n".join(formatted)


def _convert_databag_to_ansible_vars(
    data: dict, databag_name: str, item_name: str, is_encrypted: bool
) -> dict:
    """Convert Chef data bag structure to Ansible variables format."""
    # Remove Chef-specific metadata
    ansible_vars = {}

    for key, value in data.items():
        if key == "id":  # Skip Chef ID field
            continue

        # Convert key to Ansible-friendly format
        ansible_key = (
            f"{databag_name}_{key}" if not key.startswith(databag_name) else key
        )
        ansible_vars[ansible_key] = value

    # Add metadata for tracking
    ansible_vars[f"{databag_name}_metadata"] = {
        "source": f"data_bags/{databag_name}/{item_name}.json",
        "converted_by": "souschef",
        "encrypted": is_encrypted,
    }

    return ansible_vars


def _generate_vault_content(vars_dict: dict, databag_name: str) -> str:
    """Generate Ansible Vault YAML content from variables dictionary."""
    import yaml

    # Structure for vault file
    vault_vars = {f"{databag_name}_vault": vars_dict}

    return yaml.dump(vault_vars, default_flow_style=False, indent=2)


def _detect_encrypted_databag(content: str) -> bool:
    """Detect if a Chef data bag is encrypted based on content structure."""
    try:
        databag_json = json.loads(content)

        # Chef encrypted data bags have specific fields (encrypted_data, cipher, iv, version)
        # These aren't in plaintext bags, so their presence confirms encryption
        encrypted_indicators = ["encrypted_data", "cipher", "iv", "version"]

        # Check if any encrypted indicators are present
        for indicator in encrypted_indicators:
            if indicator in databag_json:
                return True

        # Check for encrypted field patterns
        for _key, value in databag_json.items():
            if isinstance(value, dict) and "encrypted_data" in value:
                return True

        return False

    except (json.JSONDecodeError, TypeError):
        return False


def _generate_databag_conversion_summary(results: list, output_dir: str) -> str:
    """Generate summary of data bag conversion results."""
    total_bags = len(results)
    successful = len([r for r in results if "error" not in r])
    encrypted = len([r for r in results if r.get("encrypted", False)])

    summary = f"""# Data Bag Conversion Summary

## Statistics:
- Total data bags processed: {total_bags}
- Successfully converted: {successful}
- Failed conversions: {total_bags - successful}
- Encrypted data bags: {encrypted}

## Generated Files:
"""
    files_created = set()
    for result in results:
        if "error" not in result:
            target_file = result["target_file"]
            files_created.add(target_file)

    for file in sorted(files_created):
        summary += f"- {file}\n"

    summary += "\n## Conversion Details:\n"

    for result in results:
        if "error" in result:
            summary += f"❌ {result['databag']}/{result['item']}: {result['error']}\n"
        else:
            status = "🔒 Encrypted" if result["encrypted"] else "📄 Plain"
            databag_item = f"{result['databag']}/{result['item']}"
            target = result["target_file"]
            summary += f"✅ {databag_item} → {target} ({status})\n"

    summary += f"""
## Next Steps:
1. Review generated variable files in {output_dir}/
2. Encrypt vault files: `ansible-vault encrypt {output_dir}/*_vault.yml`
3. Update playbooks to include vars_files references
4. Test variable access in playbooks
5. Remove original Chef data bags after validation
"""
    return summary


def _extract_databag_usage_from_cookbook(cookbook_path) -> list:
    """Extract data bag usage patterns from Chef cookbook files."""
    patterns = []

    # Search for data bag usage in Ruby files
    for ruby_file in cookbook_path.rglob("*.rb"):
        try:
            with ruby_file.open() as f:
                content = f.read()

            # Find data bag usage patterns
            found_patterns = _find_databag_patterns_in_content(content, str(ruby_file))
            patterns.extend(found_patterns)

        except Exception as e:
            patterns.append(
                {"file": str(ruby_file), "error": f"Could not read file: {e}"}
            )

    return patterns


def _find_databag_patterns_in_content(content: str, file_path: str) -> list:
    """Find data bag usage patterns in file content."""
    patterns = []

    # Common Chef data bag patterns
    databag_patterns = [
        (r"data_bag\([\'\"]\s*([^\'\"]*)\s*[\'\"]\)", "data_bag()"),
        (
            r"data_bag_item\([\'\"]\s*([^\'\"]*)\s*[\'\"]\s*,\s*[\'\"]\s*([^\'\"]*)\s*[\'\"]\)",
            "data_bag_item()",
        ),
        (
            r"encrypted_data_bag_item\([\'\"]\s*([^\'\"]*)\s*[\'\"]\s*,\s*[\'\"]\s*([^\'\"]*)\s*[\'\"]\)",
            "encrypted_data_bag_item()",
        ),
        (r"search\(\s*:node.*data_bag.*\)", "search() with data_bag"),
    ]

    for pattern, pattern_type in databag_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1

            patterns.append(
                {
                    "file": file_path,
                    "line": line_num,
                    "type": pattern_type,
                    "match": match.group(0),
                    "databag_name": match.group(1) if match.groups() else None,
                    "item_name": match.group(2)
                    if len(match.groups()) >= 2 and match.group(2)
                    else None,
                }
            )

    return patterns


def _analyze_databag_structure(databags_path) -> dict:
    """Analyze the structure of Chef data bags directory."""
    structure: dict[str, Any] = {
        "total_databags": 0,
        "total_items": 0,
        "encrypted_items": 0,
        "databags": {},
    }

    for databag_dir in databags_path.iterdir():
        if not databag_dir.is_dir():
            continue

        databag_name = databag_dir.name
        structure["total_databags"] += 1

        items = []
        for item_file in databag_dir.glob("*.json"):
            structure["total_items"] += 1
            item_name = item_file.stem

            try:
                with item_file.open() as f:
                    content = f.read()

                is_encrypted = _detect_encrypted_databag(content)
                if is_encrypted:
                    structure["encrypted_items"] += 1

                items.append(
                    {
                        "name": item_name,
                        "encrypted": is_encrypted,
                        "size": item_file.stat().st_size,
                    }
                )

            except Exception as e:
                items.append({"name": item_name, "error": str(e)})

        structure["databags"][databag_name] = {"items": items, "item_count": len(items)}

    return structure


def _generate_databag_migration_recommendations(
    usage_patterns: list, databag_structure: dict
) -> str:
    """Generate migration recommendations based on usage analysis."""
    recommendations = []

    # Analyze usage patterns
    if usage_patterns:
        unique_databags = {
            p.get("databag_name") for p in usage_patterns if p.get("databag_name")
        }
        recommendations.append(
            f"• Found {len(usage_patterns)} data bag references "
            f"across {len(unique_databags)} different data bags"
        )

        # Check for encrypted usage
        encrypted_usage = [
            p for p in usage_patterns if "encrypted" in p.get("type", "")
        ]
        if encrypted_usage:
            recommendations.append(
                f"• {len(encrypted_usage)} encrypted data bag references "
                f"- convert to Ansible Vault"
            )

        # Check for complex patterns
        search_patterns = [p for p in usage_patterns if "search" in p.get("type", "")]
        if search_patterns:
            recommendations.append(
                f"• {len(search_patterns)} search patterns involving data bags "
                f"- may need inventory integration"
            )

    # Analyze structure
    if databag_structure:
        total_bags = databag_structure.get("total_databags", 0)
        encrypted_items = databag_structure.get("encrypted_items", 0)

        if total_bags > 0:
            recommendations.append(
                f"• Convert {total_bags} data bags to group_vars/host_vars structure"
            )

        if encrypted_items > 0:
            recommendations.append(
                f"• {encrypted_items} encrypted items need Ansible Vault conversion"
            )

    # Variable scope recommendations
    recommendations.extend(
        [
            "• Use group_vars/ for environment-specific data (production, staging)",
            "• Use host_vars/ for node-specific configurations",
            "• Consider splitting large data bags into logical variable files",
            "• Implement variable precedence hierarchy matching Chef environments",
        ]
    )

    return "\n".join(recommendations)


def _format_usage_patterns(patterns: list) -> str:
    """Format data bag usage patterns for display."""
    if not patterns:
        return "No data bag usage patterns found."

    formatted = []
    for pattern in patterns[:10]:  # Limit to first 10 for readability
        if "error" in pattern:
            formatted.append(f"❌ {pattern['file']}: {pattern['error']}")
        else:
            formatted.append(
                f"• {pattern['type']} in {pattern['file']}:{pattern['line']} "
                f"(databag: {pattern.get('databag_name', 'unknown')})"
            )

    if len(patterns) > 10:
        formatted.append(f"... and {len(patterns) - 10} more patterns")

    return "\n".join(formatted)


def _format_databag_structure(structure: dict) -> str:
    """Format data bag structure analysis for display."""
    if not structure:
        return "No data bag structure provided for analysis."

    formatted = [
        f"• Total data bags: {structure['total_databags']}",
        f"• Total items: {structure['total_items']}",
        f"• Encrypted items: {structure['encrypted_items']}",
    ]

    if structure["databags"]:
        formatted.append("\n### Data Bag Details:")
        for name, info in list(structure["databags"].items())[
            :5
        ]:  # Limit for readability
            encrypted_count = sum(
                1 for item in info["items"] if item.get("encrypted", False)
            )
            formatted.append(
                f"• {name}: {info['item_count']} items ({encrypted_count} encrypted)"
            )

        if len(structure["databags"]) > 5:
            formatted.append(f"... and {len(structure['databags']) - 5} more data bags")

    return "\n".join(formatted)


# ============================================================================
# Deployment and AWX/AAP Integration Tools
# ============================================================================
# The following tools are imported from souschef.deployment module
# - generate_awx_job_template_from_cookbook
# - generate_awx_workflow_from_chef_runlist
# - generate_awx_project_from_cookbooks
# - generate_awx_inventory_source_from_chef
# - convert_chef_deployment_to_ansible_strategy
# - generate_blue_green_deployment_playbook
# - generate_canary_deployment_strategy
# - analyze_chef_application_patterns

# Register imported deployment tools with MCP server
mcp.tool()(_generate_awx_job_template_from_cookbook)
mcp.tool()(_generate_awx_workflow_from_chef_runlist)
mcp.tool()(_generate_awx_project_from_cookbooks)
mcp.tool()(_generate_awx_inventory_source_from_chef)
mcp.tool()(_convert_chef_deployment_to_ansible_strategy)
mcp.tool()(_generate_blue_green_deployment_playbook)
mcp.tool()(_generate_canary_deployment_strategy)
mcp.tool()(_analyze_chef_application_patterns)


# ============================================================================
# Assessment and Migration Planning Tools
# ============================================================================
# Note: assess_chef_migration_complexity is defined later in this file


@mcp.tool()
def assess_chef_migration_complexity(
    cookbook_paths: str,
    migration_scope: str = "full",
    target_platform: str = "ansible_awx",
) -> str:
    """
    Assess the complexity of migrating Chef cookbooks to Ansible.

    Analyzes one or more Chef cookbooks to determine migration complexity,
    effort estimation, and potential challenges.

    Args:
        cookbook_paths: Comma-separated list of paths to Chef cookbook directories.
        migration_scope: Scope of migration (full/recipes_only/infrastructure_only).
        target_platform: Target platform (ansible_awx/ansible_core/ansible_tower).

    Returns:
        Detailed assessment report in markdown format.

    """
    return _assess_chef_migration_complexity(
        cookbook_paths, migration_scope, target_platform
    )


@mcp.tool()
def generate_migration_plan(
    cookbook_paths: str,
    migration_strategy: str = "phased",
    timeline_weeks: int = 12,
) -> str:
    """
    Generate a detailed migration plan for Chef to Ansible conversion.

    Creates a comprehensive migration plan with phases, timeline, resources,
    and risk mitigation strategies.

    Args:
        cookbook_paths: Comma-separated list of paths to Chef cookbook directories.
        migration_strategy: Migration approach (big_bang, phased, parallel).
        timeline_weeks: Target timeline in weeks.

    Returns:
        Detailed migration plan in markdown format.

    """
    return _generate_migration_plan(cookbook_paths, migration_strategy, timeline_weeks)


@mcp.tool()
def analyze_cookbook_dependencies(cookbook_paths: str) -> str:
    """
    Analyze dependencies between Chef cookbooks.

    Maps cookbook dependencies, identifies circular dependencies, and
    recommends migration order.

    Args:
        cookbook_paths: Comma-separated list of paths to Chef cookbook directories.

    Returns:
        Dependency analysis report in markdown format.

    """
    return _analyze_cookbook_dependencies(cookbook_paths)


@mcp.tool()
def generate_migration_report(
    cookbook_paths: str,
    report_format: str = "markdown",
    include_technical_details: str = "yes",
) -> str:
    """
    Generate a comprehensive migration report.

    Creates a detailed report covering assessment, planning, and recommendations
    for migrating Chef cookbooks to Ansible.

    Args:
        cookbook_paths: Comma-separated list of paths to Chef cookbook directories.
        report_format: Output format (markdown/html/json).
        include_technical_details: Include technical details (yes/no).

    Returns:
        Comprehensive migration report in markdown format.

    """
    return _generate_migration_report(
        cookbook_paths, report_format, include_technical_details
    )


@mcp.tool()
def validate_conversion(
    conversion_type: str,
    result_content: str,
    output_format: str = "text",
) -> str:
    """
    Validate converted Ansible content for correctness and best practices.

    Performs comprehensive validation of converted Ansible playbooks, roles,
    and task files to ensure they meet standards and best practices.

    Args:
        conversion_type: Type of conversion (cookbook/recipe/resource/attribute).
        result_content: The converted Ansible content to validate.
        output_format: Output format (text/json/summary).

    Returns:
        Validation report in the specified format.

    """
    return _validate_conversion(conversion_type, result_content, output_format)


# Habitat Parsing Tool


@mcp.tool()
def parse_habitat_plan(plan_path: str) -> str:
    """
    Parse a Chef Habitat plan file (plan.sh) and extract package metadata.

    Analyzes Habitat plans to extract package information, dependencies,
    ports, services, and build callbacks for container conversion.

    Args:
        plan_path: Path to the plan.sh file

    Returns:
        JSON string with parsed plan metadata

    """
    return _parse_habitat_plan(plan_path)


# Habitat conversion tools - re-export for backward compatibility
def convert_habitat_to_dockerfile(
    plan_path: str, base_image: str = "ubuntu:22.04"
) -> str:
    """
    Convert a Habitat plan to Dockerfile.

    Args:
        plan_path: Path to the Habitat plan.sh file.
        base_image: Base Docker image to use.

    Returns:
        Generated Dockerfile content.

    """
    return _convert_habitat_to_dockerfile(plan_path, base_image)


def generate_compose_from_habitat(
    plan_paths: str, network_name: str = "habitat_net"
) -> str:
    """
    Generate Docker Compose from Habitat plans.

    Args:
        plan_paths: Comma-separated paths to plan.sh files.
        network_name: Docker network name.

    Returns:
        Generated Docker Compose YAML content.

    """
    return _generate_compose_from_habitat(plan_paths, network_name)


# Playbook converter wrappers for backward compatibility
def generate_playbook_from_recipe(recipe_path: str) -> str:
    """
    Generate Ansible playbook from Chef recipe.

    Args:
        recipe_path: Path to the Chef recipe file.

    Returns:
        Generated Ansible playbook content.

    """
    return _generate_playbook_from_recipe(recipe_path)


def convert_chef_search_to_inventory(search_query: str) -> str:
    """
    Convert Chef search query to Ansible inventory.

    Args:
        search_query: Chef search query.

    Returns:
        Ansible inventory configuration.

    """
    return _convert_chef_search_to_inventory(search_query)


def generate_dynamic_inventory_script(search_queries: str) -> str:
    """
    Generate dynamic inventory script from Chef search queries.

    Args:
        search_queries: Chef search queries (one per line).

    Returns:
        Python dynamic inventory script content.

    """
    return _generate_dynamic_inventory_script(search_queries)


def analyze_chef_search_patterns(recipe_or_cookbook_path: str) -> str:
    """
    Analyze Chef search patterns in recipe or cookbook.

    Args:
        recipe_or_cookbook_path: Path to recipe or cookbook.

    Returns:
        Analysis of search patterns found.

    """
    return _analyze_chef_search_patterns(recipe_or_cookbook_path)


# AWX/AAP deployment wrappers for backward compatibility
def main() -> None:
    """
    Run the SousChef MCP server.

    This is the main entry point for running the server.
    """
    mcp.run()


if __name__ == "__main__":
    main()
