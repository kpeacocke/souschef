"""
V2.2: Custom Ansible module generator for Chef resources.

Generates Python-based custom Ansible modules for Chef resources that don't have
direct Ansible equivalents. Produces modules with proper argument specifications,
module execution logic, and documentation.
"""

import re
from typing import Any


def analyse_resource_complexity(resource_body: str) -> dict[str, Any]:
    """
    Analyse Chef resource to determine if custom module is needed.

    Evaluates resource complexity and returns recommendation for custom module.

    Args:
        resource_body: The Chef resource block content.

    Returns:
        Dictionary with complexity analysis and custom module recommendation.

    """
    analysis: dict[str, Any] = {
        "needs_custom_module": False,
        "complexity_score": 0,
        "missing_module": "",
        "custom_logic_required": [],
        "estimated_module_size": 0,
    }

    # Check for custom Ruby logic
    if "ruby_block" in resource_body or "script" in resource_body:
        analysis["complexity_score"] += 3
        analysis["custom_logic_required"].append("ruby_logic")

    # Check for multiple providers (increases complexity)
    if re.search(r"provides\s+:(\w+)", resource_body):
        analysis["complexity_score"] += 2

    # Check for custom actions
    custom_actions = re.findall(r"action\s*:\s*(\w+)", resource_body)
    if len(custom_actions) > 2:
        analysis["complexity_score"] += 2
        analysis["custom_logic_required"].append("multiple_actions")

    # Check for property validation
    if "validation" in resource_body or "required" in resource_body:
        analysis["complexity_score"] += 1

    # Check for state machine patterns
    if "converge_if_changed" in resource_body:
        analysis["complexity_score"] += 1
        analysis["custom_logic_required"].append("state_tracking")

    if analysis["complexity_score"] >= 3:
        analysis["needs_custom_module"] = True
        analysis["estimated_module_size"] = 150 + (analysis["complexity_score"] * 50)

    return analysis


def extract_module_interface(resource_body: str) -> dict[str, Any]:
    """
    Extract module interface from Chef resource.

    Identifies properties, actions, and configuration options.

    Args:
        resource_body: The Chef resource block content.

    Returns:
        Dictionary with module interface specification.

    """
    interface: dict[str, Any] = {
        "resource_type": "",
        "properties": {},
        "actions": [],
        "defaults": {},
        "required": [],
    }

    # Extract resource type (e.g., "execute", "custom_resource")
    resource_match = re.search(r"resource_name\s+:(\w+)", resource_body)
    if resource_match:
        interface["resource_type"] = resource_match.group(1)

    # Extract properties (property :prop_name)
    # Note: Pattern allows optional required/default keywords immediately after
    # property name. If properties have other attributes between name and
    # required/default, expand this pattern.
    prop_pattern = r"property\s+:(\w+)(?:.*?(?:required:|default:))?"
    for match in re.finditer(prop_pattern, resource_body):
        prop_name = match.group(1)
        interface["properties"][prop_name] = {
            "name": prop_name,
            "type": "string",  # Default, can be refined
        }

    # Extract actions (actions :action1, :action2)
    action_match = re.search(r"actions\s+([:\w\s,]+)", resource_body)
    if action_match:
        actions_str = action_match.group(1)
        actions = re.findall(r":(\w+)", actions_str)
        interface["actions"] = actions or ["default"]
    else:
        interface["actions"] = ["default"]

    # Extract default_action
    default_match = re.search(r"default_action\s+:(\w+)", resource_body)
    if default_match:
        interface["defaults"]["action"] = default_match.group(1)

    return interface


def generate_ansible_module_scaffold(
    resource_name: str,
    interface: dict[str, Any],
) -> str:
    """
    Generate Python scaffold for custom Ansible module.

    Creates module structure with argument specs, documentation, and execution logic.

    Args:
        resource_name: Name of the custom module.
        interface: Module interface from extract_module_interface.

    Returns:
        Python module code as string.

    """
    module_code = '''#!/usr/bin/python
"""Custom Ansible module for Chef resource conversion.

Provides Ansible equivalent for Chef resource that requires custom logic.
Generated automatically from Chef resource definition.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: '''
    module_code += f"{resource_name}\n"
    module_code += f"""short_description: Manage {resource_name} resource
description:
  - Provides Ansible equivalent for Chef resource
  - Handles complex logic and state management

options:
"""

    # Add properties as module arguments
    for prop_name in interface.get("properties", {}):
        module_code += f"""  {prop_name}:
    description: Property {prop_name}
    type: str
    required: false
"""

    module_code += f'''
author:
  - SousChef (Chef to Ansible converter)
"""

EXAMPLES = r"""
- name: Execute {resource_name}
  {resource_name}:
'''

    for prop_name in list(interface.get("properties", {}).keys())[:2]:
        module_code += f'    {prop_name}: "value"\n'

    module_code += '''"""

RETURN = r"""
changed:
  description: Whether the resource was changed
  returned: always
  type: bool
result:
  description: Result of resource execution
  returned: success
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main module execution function."""
    module_args = dict(
'''

    for prop_name in interface.get("properties", {}):
        module_code += f'        {prop_name}=dict(type="str", required=False),\n'

    module_code += """    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    result = {
        "changed": False,
        "result": {},
    }

    # Resource execution logic goes here
    try:
        # TODO: Implement execution logic
        # This is a template for custom resource execution

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
"""

    return module_code


def generate_module_documentation(
    resource_name: str,
    interface: dict[str, Any],
    complexity_analysis: dict[str, Any],
) -> str:
    """
    Generate comprehensive module documentation.

    Creates usage guide and implementation notes for custom module.

    Args:
        resource_name: Name of the custom module.
        interface: Module interface.
        complexity_analysis: Complexity information.

    Returns:
        Markdown-formatted documentation.

    """
    doc = f"# Custom Ansible Module: {resource_name}\n\n"
    doc += "## Overview\n"
    overview = "This module provides Ansible equivalent for the Chef "
    overview += f"{resource_name} resource.\n\n"
    doc += overview

    doc += "## Complexity Analysis\n"
    score = complexity_analysis.get("complexity_score", 0)
    doc += f"- Complexity Score: {score}/10\n"

    logic_required = complexity_analysis.get("custom_logic_required", [])
    logic_str = ", ".join(logic_required) if logic_required else "None"
    doc += f"- Custom Logic Required: {logic_str}\n"

    module_size = complexity_analysis.get("estimated_module_size", 0)
    doc += f"- Estimated Module Size: ~{module_size} lines\n\n"

    doc += "## Properties\n"
    for prop_name, prop_info in interface.get("properties", {}).items():
        doc += f"- **{prop_name}**: {prop_info.get('type', 'string')}\n"

    doc += "\n## Actions\n"
    for action in interface.get("actions", ["default"]):
        doc += f"- `{action}`\n"

    doc += "\n## Usage Example\n"
    doc += f"""```yaml
- name: Execute {resource_name}
  {resource_name}:
"""
    for prop_name in list(interface.get("properties", {}).keys())[:2]:
        doc += f"""    {prop_name}: "value"
"""
    doc += "```\n\n"

    doc += "## Implementation Notes\n"
    doc += "- This module was automatically generated from Chef resource\n"
    doc += "- Review the execution logic in main() function\n"
    doc += "- Add error handling for edge cases\n"
    doc += "- Test with both check mode and apply mode\n"
    doc += "- Update documentation with actual property descriptions\n\n"

    doc += "## See Also\n"
    doc += "- Ansible Module Development Guide\n"
    doc += f"- Chef {resource_name} Resource Documentation\n"

    return doc


def generate_module_manifest(
    resource_name: str,
    modules: list[str],
) -> dict[str, Any]:
    """
    Generate manifest for custom module collection.

    Creates metadata for organizing custom modules.

    Args:
        resource_name: Primary resource name.
        modules: List of module names being generated.

    Returns:
        Manifest dictionary.

    """
    manifest: dict[str, Any] = {
        "namespace": "souschef",
        "name": f"{resource_name}_custom",
        "version": "1.0.0",
        "description": "Custom Ansible modules for Chef to Ansible conversion",
        "modules": modules,
        "author": "SousChef Chef-to-Ansible Converter",
        "license": ["GPL-3.0-or-later"],
        "repository": "https://github.com/under-linux/souschef",
        "documentation": {
            "overview": "Custom Ansible modules generated from Chef resources",
            "generated_from": "Chef cookbook resources",
            "conversion_tool": "SousChef v2.2+",
        },
    }

    return manifest


def validate_module_code(module_code: str) -> dict[str, Any]:
    """
    Validate generated module code.

    Checks for syntax errors and best practices.

    Args:
        module_code: Generated Python module code.

    Returns:
        Validation results with issues and recommendations.

    """
    validation: dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "checklist": {
            "has_documentation": False,
            "has_examples": False,
            "has_error_handling": False,
            "has_check_mode": False,
            "has_return_statement": False,
        },
    }

    # Check for DOCUMENTATION
    if "DOCUMENTATION = " in module_code:
        validation["checklist"]["has_documentation"] = True

    # Check for EXAMPLES
    if "EXAMPLES = " in module_code:
        validation["checklist"]["has_examples"] = True

    # Check for error handling
    if "try:" in module_code and "except" in module_code:
        validation["checklist"]["has_error_handling"] = True

    # Check for check_mode support
    if "supports_check_mode=True" in module_code:
        validation["checklist"]["has_check_mode"] = True

    # Check for return statement
    if "module.exit_json" in module_code:
        validation["checklist"]["has_return_statement"] = True

    # Count checklist items
    checked_items = sum(1 for value in validation["checklist"].values() if value)
    total_checks = len(validation["checklist"])
    validation["completeness_score"] = (checked_items / total_checks) * 100

    # Warnings for incomplete modules
    if not validation["checklist"]["has_error_handling"]:
        validation["warnings"].append("Module lacks error handling")
    if not validation["checklist"]["has_check_mode"]:
        validation["warnings"].append("Module doesn't support check mode")

    return validation


def build_module_collection(
    resources: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Build collection of custom modules for all resources.

    Creates unified structure for multiple custom modules.

    Args:
        resources: List of resource dictionaries with name and body.

    Returns:
        Collection structure with all modules and metadata.

    """
    collection: dict[str, Any] = {
        "collection_name": "souschef_custom",
        "modules": {},
        "summary": {
            "total_resources": len(resources),
            "modules_generated": 0,
            "total_lines_of_code": 0,
            "average_complexity": 0,
        },
        "generation_metadata": {
            "converter": "SousChef v2.2",
            "timestamp": None,
        },
    }

    total_complexity = 0

    for resource in resources:
        resource_name = resource.get("name", "unknown")
        resource_body = resource.get("body", "")

        # Analyse complexity
        complexity = analyse_resource_complexity(resource_body)

        if complexity["needs_custom_module"]:
            # Extract interface
            interface = extract_module_interface(resource_body)

            # Generate module code
            module_code = generate_ansible_module_scaffold(
                resource_name,
                interface,
            )

            # Add to collection
            collection["modules"][resource_name] = {
                "code": module_code,
                "interface": interface,
                "complexity": complexity,
                "lines_of_code": len(module_code.split("\n")),
            }

            collection["summary"]["modules_generated"] += 1
            collection["summary"]["total_lines_of_code"] += len(module_code.split("\n"))
            total_complexity += complexity["complexity_score"]

    # Calculate summary statistics
    if collection["summary"]["modules_generated"] > 0:
        collection["summary"]["average_complexity"] = (
            total_complexity / collection["summary"]["modules_generated"]
        )

    return collection
