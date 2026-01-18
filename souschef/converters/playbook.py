"""
Chef recipe to Ansible playbook and inventory conversion.

This module provides tools to convert Chef recipes to complete Ansible playbooks,
convert Chef search queries to Ansible inventory structures, and generate dynamic
inventory scripts.
"""

import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from souschef.converters.resource import (
    _convert_chef_resource_to_ansible,
    _format_ansible_task,
)
from souschef.core.constants import (
    ANSIBLE_SERVICE_MODULE,
    ATTRIBUTE_PREFIX,
    ERROR_PREFIX,
    JINJA2_VAR_REPLACEMENT,
    NODE_PREFIX,
    REGEX_QUOTE_DO_END,
    REGEX_RESOURCE_BRACKET,
    REGEX_RUBY_INTERPOLATION,
    REGEX_WHITESPACE_QUOTE,
    VALUE_PREFIX,
)
from souschef.core.path_utils import _normalize_path, _safe_join
from souschef.parsers.attributes import parse_attributes
from souschef.parsers.recipe import parse_recipe

# Optional AI provider imports
try:
    import requests  # type: ignore[import-untyped]
except ImportError:
    requests = None

try:
    from ibm_watsonx_ai import (  # type: ignore[import-not-found]
        APIClient,
    )
except ImportError:
    APIClient = None

# Maximum length for guard condition patterns in regex matching
MAX_GUARD_LENGTH = 500


def generate_playbook_from_recipe(recipe_path: str) -> str:
    """
    Generate a complete Ansible playbook from a Chef recipe.

    Args:
        recipe_path: Path to the Chef recipe (.rb) file.

    Returns:
        Complete Ansible playbook in YAML format with tasks, handlers, and
        variables.

    """
    try:
        # First, parse the recipe to extract resources
        recipe_content: str = parse_recipe(recipe_path)

        if recipe_content.startswith(ERROR_PREFIX):
            return recipe_content

        # Parse the raw recipe file for advanced features
        recipe_file = _normalize_path(recipe_path)
        if not recipe_file.exists():
            return f"{ERROR_PREFIX} Recipe file does not exist: {recipe_path}"

        raw_content = recipe_file.read_text()

        # Generate playbook structure
        playbook: str = _generate_playbook_structure(
            recipe_content, raw_content, recipe_file
        )

        return playbook

    except Exception as e:
        return f"Error generating playbook: {e}"


def generate_playbook_from_recipe_with_ai(
    recipe_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """
    Generate an AI-enhanced Ansible playbook from a Chef recipe.

    Uses AI to intelligently convert Chef recipes to Ansible playbooks,
    considering context, best practices, and optimization opportunities.

    Args:
        recipe_path: Path to the Chef recipe (.rb) file.
        ai_provider: AI provider to use ('anthropic', 'openai', 'watson',
            'lightspeed'). Note: 'github_copilot' is listed but not supported as
            GitHub Copilot does not have a public REST API.
        api_key: API key for the AI provider.
        model: AI model to use.
        temperature: Creativity/randomness parameter (0.0-2.0).
        max_tokens: Maximum tokens to generate.
        project_id: Project ID for IBM Watsonx (required for watson provider).
        base_url: Custom base URL for the AI provider.

    Returns:
        AI-generated Ansible playbook in YAML format.

    """
    try:
        # Parse the recipe file
        recipe_file = _normalize_path(recipe_path)
        if not recipe_file.exists():
            return f"{ERROR_PREFIX} Recipe file does not exist: {recipe_path}"

        raw_content = recipe_file.read_text()

        # Get basic recipe parsing for context
        parsed_content = parse_recipe(recipe_path)
        if parsed_content.startswith(ERROR_PREFIX):
            return parsed_content

        # Use AI to generate the playbook
        ai_playbook = _generate_playbook_with_ai(
            raw_content,
            parsed_content,
            recipe_file.name,
            ai_provider,
            api_key,
            model,
            temperature,
            max_tokens,
            project_id,
            base_url,
        )

        return ai_playbook

    except Exception as e:
        return f"Error generating AI-enhanced playbook: {e}"


def _generate_playbook_with_ai(
    raw_content: str,
    parsed_content: str,
    recipe_name: str,
    ai_provider: str,
    api_key: str,
    model: str,
    temperature: float,
    max_tokens: int,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """Generate Ansible playbook using AI for intelligent conversion."""
    try:
        # Initialize AI client based on provider
        client = _initialize_ai_client(ai_provider, api_key, project_id, base_url)
        if isinstance(client, str):  # Error message returned
            return client

        # Create the AI prompt
        prompt = _create_ai_conversion_prompt(raw_content, parsed_content, recipe_name)

        # Call the AI API and get response
        ai_response = _call_ai_api(
            client, ai_provider, prompt, model, temperature, max_tokens
        )

        # Clean and validate the AI response
        cleaned_playbook = _clean_ai_playbook_response(ai_response)

        # Validate with ansible-lint and self-correct if possible
        cleaned_playbook = _validate_and_fix_playbook(
            cleaned_playbook, client, ai_provider, model, temperature, max_tokens
        )

        return cleaned_playbook

    except ImportError as e:
        return f"{ERROR_PREFIX} AI library not available: {e}"
    except Exception as e:
        return f"{ERROR_PREFIX} AI conversion failed: {e}"


def _initialize_ai_client(
    ai_provider: str, api_key: str, project_id: str = "", base_url: str = ""
) -> Any:
    """Initialize AI client based on provider."""
    if ai_provider.lower() == "anthropic":
        import anthropic

        return anthropic.Anthropic(api_key=api_key)
    elif ai_provider.lower() == "openai":
        import openai

        return openai.OpenAI(api_key=api_key)
    elif ai_provider.lower() == "watson":
        if APIClient is None:
            return f"{ERROR_PREFIX} ibm_watsonx_ai library not available"

        return APIClient(
            api_key=api_key,
            project_id=project_id,
            url=base_url or "https://us-south.ml.cloud.ibm.com",
        )
    elif ai_provider.lower() == "lightspeed":
        if requests is None:
            return f"{ERROR_PREFIX} requests library not available"

        return {
            "api_key": api_key,
            "base_url": base_url or "https://api.redhat.com",
        }
    elif ai_provider.lower() == "github_copilot":
        return (
            f"{ERROR_PREFIX} GitHub Copilot does not have a public REST API. "
            "GitHub Copilot is only available through IDE integrations and "
            "cannot be used "
            "for programmatic API calls. Please use Anthropic Claude, OpenAI, or IBM "
            "Watsonx instead."
        )
    else:
        return f"{ERROR_PREFIX} Unsupported AI provider: {ai_provider}"


def _call_ai_api(
    client: Any,
    ai_provider: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call the appropriate AI API based on provider."""
    if ai_provider.lower() == "anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return str(response.content[0].text)
    elif ai_provider.lower() == "watson":
        response = client.generate_text(
            model_id=model,
            input=prompt,
            parameters={
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "min_new_tokens": 1,
            },
        )
        return str(response["results"][0]["generated_text"])
    elif ai_provider.lower() == "lightspeed":
        if requests is None:
            return f"{ERROR_PREFIX} requests library not available"

        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        response = requests.post(
            f"{client['base_url']}/v1/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code == 200:
            return str(response.json()["choices"][0]["text"])
        else:
            return (
                f"{ERROR_PREFIX} Red Hat Lightspeed API error: "
                f"{response.status_code} - {response.text}"
            )
    elif ai_provider.lower() == "github_copilot":
        if requests is None:
            return f"{ERROR_PREFIX} requests library not available"

        headers = {
            "Authorization": f"Bearer {client['api_key']}",
            "Content-Type": "application/json",
            "User-Agent": "SousChef/1.0",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        # GitHub Copilot uses OpenAI-compatible chat completions endpoint
        response = requests.post(
            f"{client['base_url']}/copilot/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code == 200:
            return str(response.json()["choices"][0]["message"]["content"])
        else:
            return (
                f"{ERROR_PREFIX} GitHub Copilot API error: "
                f"{response.status_code} - {response.text}"
            )
    else:  # OpenAI
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return str(response.choices[0].message.content)


def _create_ai_conversion_prompt(
    raw_content: str, parsed_content: str, recipe_name: str
) -> str:
    """Create a comprehensive prompt for AI conversion."""
    return f"""You are an expert at converting Chef recipes to Ansible playbooks.
Your task is to convert the following Chef recipe into a high-quality,
production-ready Ansible playbook.

CHEF RECIPE CONTENT:
{raw_content}

PARSED RECIPE ANALYSIS:
{parsed_content}

RECIPE NAME: {recipe_name}

CONVERSION REQUIREMENTS:

1. **Understand the Intent**: Analyze what this Chef recipe is trying to
   accomplish. Look at the resources, their properties, and the overall
   workflow.

2. **Best Practices**: Generate Ansible code that follows Ansible best
   practices:
   - Use appropriate modules (ansible.builtin.* when possible)
   - Include proper error handling and idempotency
   - Use meaningful variable names
   - Include comments explaining complex logic
   - Handle edge cases and failure scenarios

3. **Resource Mapping**: Convert Chef resources to appropriate Ansible
   modules:
   - package → ansible.builtin.package or specific package managers
   - service → ansible.builtin.service
   - file/directory → ansible.builtin.file
   - template → ansible.builtin.template
   - execute → ansible.builtin.command/shell
   - user/group → ansible.builtin.user/group
   - mount → ansible.builtin.mount

4. **Variables and Facts**: Convert Chef node attributes to Ansible
   variables/facts appropriately.

5. **Conditionals**: Convert Chef guards (only_if/not_if) to Ansible when
   conditions.

6. **Notifications**: Convert Chef notifications to Ansible handlers where
   appropriate.

7. **Idempotency**: Ensure the playbook is idempotent and can be run
   multiple times safely.

8. **Error Handling**: Include proper error handling and rollback
   considerations.

9. **Task Ordering**: CRITICAL: Ensure tasks are ordered logically.
   - Install packages BEFORE configuring them.
   - create users/groups BEFORE using them in file permissions.
   - Place configuration files BEFORE starting/restarting services.
   - Ensure directories exist BEFORE creating files in them.

10. **Handlers**: Verify that all notified handlers are actually defined
    in the handlers section.

OUTPUT FORMAT:
Return ONLY a valid YAML Ansible playbook. Do not include any explanation,
markdown formatting, or code blocks. The output should be pure YAML that can
be directly used as an Ansible playbook.

The playbook should include:
- A proper name
- Appropriate hosts (default to 'all')
- Variables section if needed
- Tasks section with all converted resources
- Handlers section if notifications are used
- Any necessary pre_tasks or post_tasks

Example structure:
---
- name: Convert of {recipe_name}
  hosts: all
  become: true
  vars:
    # Variables here
  tasks:
    # Tasks here
  handlers:
    # Handlers here

Focus on creating a functional, well-structured Ansible playbook that achieves
the same outcome as the Chef recipe."""


def _clean_ai_playbook_response(ai_response: str) -> str:
    """Clean and validate the AI-generated playbook response."""
    if not ai_response or not ai_response.strip():
        return f"{ERROR_PREFIX} AI returned empty response"

    # Remove markdown code blocks if present
    cleaned = re.sub(r"```\w*\n?", "", ai_response)
    cleaned = cleaned.strip()

    # Basic validation - check if it looks like YAML
    if not cleaned.startswith("---") and not cleaned.startswith("- name:"):
        return f"{ERROR_PREFIX} AI response does not appear to be valid YAML playbook"

    # Try to parse as YAML to validate structure
    try:
        import yaml

        yaml.safe_load(cleaned)
    except Exception as e:
        return f"{ERROR_PREFIX} AI generated invalid YAML: {e}"

    return cleaned


def _validate_and_fix_playbook(
    playbook_content: str,
    client: Any,
    ai_provider: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Validate playbook with ansible-lint and attempt AI self-correction."""
    if playbook_content.startswith(ERROR_PREFIX):
        return playbook_content

    validation_error = _run_ansible_lint(playbook_content)
    if not validation_error:
        return playbook_content

    # Limit simple loops to 1 retry for now to save tokens/time
    fix_prompt = f"""The Ansible playbook you generated has validation errors.
Please fix the errors below and return the corrected playbook.

ERRORS:
{validation_error}

PLAYBOOK:
{playbook_content}

Ensure the logical ordering of tasks is correct (e.g., packages installed before
config files, config files before services).
Return ONLY the corrected YAML playbook.
Do NOT include any introduction, cleanup text, explanations, or markdown code blocks.
Just the YAML content.
"""

    try:
        fixed_response = _call_ai_api(
            client, ai_provider, fix_prompt, model, temperature, max_tokens
        )
        cleaned_response = _clean_ai_playbook_response(fixed_response)

        # If the cleaner returns an error string, it means the fixed response
        # was still invalid
        if cleaned_response.startswith(ERROR_PREFIX):
            # Fallback to the original (valid-but-lint-failing) playbook
            # rather than returning an error string
            return playbook_content

        return cleaned_response
    except Exception:
        # If fix fails, return original with warning (or original error)
        return playbook_content


def _run_ansible_lint(playbook_content: str) -> str | None:
    """Run ansible-lint on the playbook content."""
    # Check if ansible-lint is available
    if shutil.which("ansible-lint") is None:
        return None

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tmp:
            tmp.write(playbook_content)
            tmp_path = tmp.name

        # Run ansible-lint
        # We ignore return code because we want to capture output even on failure
        result = subprocess.run(
            ["ansible-lint", "--nocolor", "-p", tmp_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return result.stdout + "\n" + result.stderr

        return None
    except Exception:
        return None
    finally:
        if "tmp_path" in locals() and Path(tmp_path).exists():
            Path(tmp_path).unlink()


def convert_chef_search_to_inventory(search_query: str) -> str:
    """
    Convert a Chef search query to Ansible inventory patterns and groups.

    Args:
        search_query: Chef search query (e.g.,
            "role:web AND environment:production").

    Returns:
        JSON string with Ansible inventory patterns and group definitions.

    """
    try:
        # Parse the Chef search query
        search_info = _parse_chef_search_query(search_query)

        # Convert to Ansible inventory patterns
        inventory_config = _generate_ansible_inventory_from_search(search_info)

        return json.dumps(inventory_config, indent=2)

    except Exception as e:
        return f"Error converting Chef search: {e}"


def generate_dynamic_inventory_script(search_queries: str) -> str:
    """
    Generate a Python dynamic inventory script from Chef search queries.

    Args:
        search_queries: JSON string containing Chef search queries and group
            names.

    Returns:
        Complete Python script for Ansible dynamic inventory.

    """
    try:
        queries_data = json.loads(search_queries)

        # Generate dynamic inventory script
        script_content = _generate_inventory_script_content(queries_data)

        return script_content

    except json.JSONDecodeError:
        return "Error: Invalid JSON format for search queries"
    except Exception as e:
        return f"Error generating dynamic inventory script: {e}"


def analyse_chef_search_patterns(recipe_or_cookbook_path: str) -> str:
    """
    Analyse recipes/cookbooks to extract search patterns for inventory planning.

    Args:
        recipe_or_cookbook_path: Path to Chef recipe file or cookbook directory.

    Returns:
        JSON string with discovered search patterns and recommended inventory
        structure.

    """
    try:
        path_obj = _normalize_path(recipe_or_cookbook_path)

        if path_obj.is_file():
            # Single recipe file
            search_patterns = _extract_search_patterns_from_file(path_obj)
        elif path_obj.is_dir():
            # Cookbook directory
            search_patterns = _extract_search_patterns_from_cookbook(path_obj)
        else:
            return f"Error: Path {recipe_or_cookbook_path} does not exist"

        # Generate inventory recommendations
        recommendations = _generate_inventory_recommendations(search_patterns)

        return json.dumps(
            {
                "discovered_searches": search_patterns,
                "inventory_recommendations": recommendations,
            },
            indent=2,
        )

    except Exception as e:
        return f"Error analyzing Chef search patterns: {e}"


# Chef search query parsing


def _determine_search_index(normalized_query: str) -> str:
    """Determine the search index from the query."""
    index_match = re.match(r"^(\w+):", normalized_query)
    if index_match:
        potential_index = index_match.group(1)
        if potential_index in ["role", "environment", "tag", "platform"]:
            return "node"  # These are node attributes
        return potential_index
    return "node"


def _extract_query_parts(
    normalized_query: str,
) -> tuple[list[dict[str, str]], list[str]]:
    """Extract conditions and operators from query."""
    operator_pattern = r"\s{1,50}(AND|OR|NOT)\s{1,50}"
    parts = re.split(operator_pattern, normalized_query, flags=re.IGNORECASE)

    conditions: list[dict[str, str]] = []
    operators: list[str] = []

    for part in parts:
        part = part.strip()
        if part.upper() in ["AND", "OR", "NOT"]:
            operators.append(part.upper())
        elif part:  # Non-empty condition
            condition = _parse_search_condition(part)
            if condition:
                conditions.append(condition)

    return conditions, operators


def _determine_query_complexity(
    conditions: list[dict[str, str]], operators: list[str]
) -> str:
    """Determine query complexity level."""
    if len(conditions) > 1 or operators:
        return "complex"
    elif any(cond.get("operator") in ["~", "!="] for cond in conditions):
        return "intermediate"
    return "simple"


def _parse_chef_search_query(query: str) -> dict[str, Any]:
    """Parse a Chef search query into structured components."""
    normalized_query = query.strip()

    search_info: dict[str, Any] = {
        "original_query": query,
        "index": _determine_search_index(normalized_query),
        "conditions": [],
        "logical_operators": [],
        "complexity": "simple",
    }

    conditions, operators = _extract_query_parts(normalized_query)

    search_info["conditions"] = conditions
    search_info["logical_operators"] = operators
    search_info["complexity"] = _determine_query_complexity(conditions, operators)

    return search_info


def _parse_search_condition(condition: str) -> dict[str, str]:
    """Parse a single search condition."""
    # Handle different condition patterns
    patterns = [
        # Wildcard search: role:web*
        (r"^(\w+):([^:]*\*)$", "wildcard"),
        # Regex search: role:~web.*
        (r"^(\w+):~(.+)$", "regex"),
        # Not equal: role:!web
        (r"^(\w+):!(.+)$", "not_equal"),
        # Range: memory:(>1024 AND <4096)
        (r"^(\w+):\(([^)]+)\)$", "range"),
        # Simple key:value
        (r"^(\w+):(.+)$", "equal"),
        # Tag search: tags:web
        (r"^tags?:(.+)$", "tag"),
    ]

    for pattern, condition_type in patterns:
        match = re.match(pattern, condition.strip())
        if match:
            if condition_type == "tag":
                return {
                    "type": condition_type,
                    "key": "tags",
                    "value": match.group(1),
                    "operator": "contains",
                }
            elif condition_type in ["wildcard", "regex", "not_equal", "range"]:
                return {
                    "type": condition_type,
                    "key": match.group(1),
                    "value": match.group(2),
                    "operator": condition_type,
                }
            else:  # equal
                return {
                    "type": condition_type,
                    "key": match.group(1),
                    "value": match.group(2),
                    "operator": "equal",
                }

    # Fallback for unrecognized patterns
    return {
        "type": "unknown",
        "key": "unknown",
        "value": condition,
        "operator": "equal",
    }


# Ansible inventory generation


def _should_use_dynamic_inventory(search_info: dict[str, Any]) -> bool:
    """Determine if dynamic inventory is needed based on search complexity."""
    return (
        search_info["complexity"] != "simple"
        or len(search_info["conditions"]) > 1
        or any(
            cond.get("operator") in ["regex", "wildcard", "range"]
            for cond in search_info["conditions"]
        )
    )


def _create_group_config_for_equal_condition(
    condition: dict[str, str],
) -> dict[str, Any]:
    """Create group configuration for equal operator conditions."""
    group_config: dict[str, Any] = {"hosts": [], "vars": {}, "children": []}
    key = condition["key"]
    value = condition["value"]

    if key == "role":
        group_config["hosts"] = [f"# Hosts with role: {value}"]
        return group_config
    elif key == "environment":
        group_config["vars"]["environment"] = value
        group_config["hosts"] = [f"# Hosts in environment: {value}"]
        return group_config
    elif key == "platform":
        group_config["vars"]["ansible_os_family"] = value.capitalize()
        group_config["hosts"] = [f"# {value} hosts"]
        return group_config
    elif key == "tags":
        group_config["vars"]["tags"] = [value]
        group_config["hosts"] = [f"# Hosts tagged with: {value}"]
        return group_config

    return group_config


def _create_group_config_for_pattern_condition(
    condition: dict[str, str],
) -> dict[str, Any]:
    """Create group configuration for wildcard/regex conditions."""
    operator = condition["operator"]
    pattern_type = "pattern" if operator == "wildcard" else "regex"
    return {
        "hosts": [
            (
                f"# Hosts matching {pattern_type}: "
                f"{condition['key']}:{condition['value']}"
            )
        ],
        "vars": {},
        "children": [],
    }


def _generate_group_name_from_condition(condition: dict[str, str], index: int) -> str:
    """Generate an Ansible group name from a search condition."""
    # Sanitize values for group names
    key = condition.get("key", "unknown").lower()
    value = condition.get("value", "unknown").lower()

    # Remove special characters and replace with underscores
    key = re.sub(r"[^a-z0-9_]", "_", key)
    value = re.sub(r"[^a-z0-9_]", "_", value)

    # Create meaningful group name
    if condition.get("operator") == "equal":
        return f"{key}_{value}"
    elif condition.get("operator") == "wildcard":
        return f"{key}_wildcard_{index}"
    elif condition.get("operator") == "regex":
        return f"{key}_regex_{index}"
    elif condition.get("operator") == "not_equal":
        return f"not_{key}_{value}"
    else:
        return f"search_condition_{index}"


def _process_search_condition(
    condition: dict[str, str], index: int, inventory_config: dict[str, Any]
) -> None:
    """Process a single search condition and update inventory config."""
    group_name = _generate_group_name_from_condition(condition, index)

    if condition["operator"] == "equal":
        group_config = _create_group_config_for_equal_condition(condition)
        # Add role variable if it's a role condition
        if condition["key"] == "role":
            inventory_config["variables"][f"{group_name}_role"] = condition["value"]
    elif condition["operator"] in ["wildcard", "regex"]:
        group_config = _create_group_config_for_pattern_condition(condition)
        inventory_config["dynamic_script_needed"] = True
    else:
        group_config = {"hosts": [], "vars": {}, "children": []}

    inventory_config["groups"][group_name] = group_config


def _generate_ansible_inventory_from_search(
    search_info: dict[str, Any],
) -> dict[str, Any]:
    """Generate Ansible inventory structure from parsed Chef search."""
    inventory_config: dict[str, Any] = {
        "inventory_type": "static",
        "groups": {},
        "host_patterns": [],
        "variables": {},
        "dynamic_script_needed": False,
    }

    # Determine if we need dynamic inventory
    if _should_use_dynamic_inventory(search_info):
        inventory_config["inventory_type"] = "dynamic"
        inventory_config["dynamic_script_needed"] = True

    # Process each condition
    for i, condition in enumerate(search_info["conditions"]):
        _process_search_condition(condition, i, inventory_config)

    # Handle logical operators by creating combined groups
    if search_info["logical_operators"]:
        combined_group_name = "combined_search_results"
        inventory_config["groups"][combined_group_name] = {
            "children": list(inventory_config["groups"].keys()),
            "vars": {"chef_search_query": search_info["original_query"]},
        }

    return inventory_config


def _generate_inventory_script_content(queries_data: list[dict[str, str]]) -> str:
    """Generate Python dynamic inventory script content."""
    script_template = '''#!/usr/bin/env python3
"""Dynamic Ansible Inventory Script.

Generated from Chef search queries by SousChef

This script converts Chef search queries to Ansible inventory groups.
Requires: python-requests (for Chef server API)
"""
import json
import sys
import argparse
from typing import Dict, List, Any

# Chef server configuration
CHEF_SERVER_URL = "https://your-chef-server"
CLIENT_NAME = "your-client-name"
CLIENT_KEY_PATH = "/path/to/client.pem"

# Search query to group mappings
SEARCH_QUERIES = {search_queries_json}


def get_chef_nodes(search_query: str) -> List[Dict[str, Any]]:
    """Query Chef server for nodes matching search criteria.

    Args:
        search_query: Chef search query string

    Returns:
        List of node objects from Chef server
    """
    # TODO: Implement Chef server API client
    # This is a placeholder - implement Chef server communication
    # using python-chef library or direct API calls

    # Example structure of what this should return:
    return [
        {
            "name": "web01.example.com",
            "roles": ["web"],
            "environment": "production",
            "platform": "ubuntu",
            "ipaddress": "10.0.1.10"
        }
    ]


def build_inventory() -> Dict[str, Any]:
    """Build Ansible inventory from Chef searches.

    Returns:
        Ansible inventory dictionary
    """
    inventory = {
        "_meta": {
            "hostvars": {}
        }
    }

    for group_name, search_query in SEARCH_QUERIES.items():
        inventory[group_name] = {
            "hosts": [],
            "vars": {
                "chef_search_query": search_query
            }
        }

        try:
            nodes = get_chef_nodes(search_query)

            for node in nodes:
                hostname = node.get("name", node.get("fqdn", "unknown"))
                inventory[group_name]["hosts"].append(hostname)

                # Add host variables
                inventory["_meta"]["hostvars"][hostname] = {
                    "chef_roles": node.get("roles", []),
                    "chef_environment": node.get("environment", ""),
                    "chef_platform": node.get("platform", ""),
                    "ansible_host": node.get("ipaddress", hostname)
                }

        except Exception as e:
            print(
                f"Error querying Chef server for group {group_name}: {e}",
                file=sys.stderr,
            )

    return inventory


def main():
    """Main entry point for dynamic inventory script."""
    parser = argparse.ArgumentParser(
        description="Dynamic Ansible Inventory from Chef"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all groups and hosts"
    )
    parser.add_argument("--host", help="Get variables for specific host")

    args = parser.parse_args()

    if args.list:
        inventory = build_inventory()
        print(json.dumps(inventory, indent=2))
    elif args.host:
        # Return empty dict for host-specific queries
        # All host vars are included in _meta/hostvars
        print(json.dumps({}))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
'''

    # Convert queries_data to JSON string for embedding
    queries_json = json.dumps(
        {
            item.get("group_name", f"group_{i}"): item.get("search_query", "")
            for i, item in enumerate(queries_data)
        },
        indent=4,
    )

    return script_template.replace("{search_queries_json}", queries_json)


# Search pattern extraction


def _extract_search_patterns_from_file(file_path: Path) -> list[dict[str, str]]:
    """Extract Chef search patterns from a single recipe file."""
    try:
        content = file_path.read_text()
        return _find_search_patterns_in_content(content, str(file_path))
    except Exception:
        return []


def _extract_search_patterns_from_cookbook(cookbook_path: Path) -> list[dict[str, str]]:
    """Extract Chef search patterns from all files in a cookbook."""
    patterns = []

    # Search in recipes directory
    recipes_dir = _safe_join(cookbook_path, "recipes")
    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            file_patterns = _extract_search_patterns_from_file(recipe_file)
            patterns.extend(file_patterns)

    # Search in libraries directory
    libraries_dir = _safe_join(cookbook_path, "libraries")
    if libraries_dir.exists():
        for library_file in libraries_dir.glob("*.rb"):
            file_patterns = _extract_search_patterns_from_file(library_file)
            patterns.extend(file_patterns)

    # Search in resources directory
    resources_dir = _safe_join(cookbook_path, "resources")
    if resources_dir.exists():
        for resource_file in resources_dir.glob("*.rb"):
            file_patterns = _extract_search_patterns_from_file(resource_file)
            patterns.extend(file_patterns)

    return patterns


def _find_search_patterns_in_content(
    content: str, file_path: str
) -> list[dict[str, str]]:
    """Find Chef search patterns in file content."""
    patterns = []

    # Common Chef search patterns
    search_patterns = [
        # search(:node, "role:web")
        r'search\s*\(\s*:?(\w+)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
        # partial_search(:node, "environment:production")
        r'partial_search\s*\(\s*:?(\w+)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
        # data_bag_item with search-like queries
        r'data_bag_item\s*\(\s*[\'"](\w+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
        # Node attribute queries that imply searches
        r'node\[[\'"](\w+)[\'"]\]\[[\'"]([^\'"]+)[\'"]\]',
    ]

    for pattern in search_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            if "search" in pattern:
                # Full search patterns
                search_type = match.group(1)
                query = match.group(2)
                patterns.append(
                    {
                        "type": "search",
                        "index": search_type,
                        "query": query,
                        "file": file_path,
                        "context": _extract_context(content, match),
                    }
                )
            elif "data_bag_item" in pattern:
                # Data bag patterns (related to search)
                bag_name = match.group(1)
                item_name = match.group(2)
                patterns.append(
                    {
                        "type": "data_bag_access",
                        "bag": bag_name,
                        "item": item_name,
                        "file": file_path,
                        "context": _extract_context(content, match),
                    }
                )
            else:
                # Node attribute patterns
                attr_key = match.group(1)
                attr_value = match.group(2)
                patterns.append(
                    {
                        "type": "node_attribute",
                        "key": attr_key,
                        "value": attr_value,
                        "file": file_path,
                        "context": _extract_context(content, match),
                    }
                )

    return patterns


def _extract_context(content: str, match: re.Match[str]) -> str:
    """Extract context around a regex match."""
    start = max(0, match.start() - 50)
    end = min(len(content), match.end() + 50)
    context = content[start:end].strip()

    # Clean up context
    lines = context.split("\n")
    if len(lines) > 3:
        # Keep middle line and one line before/after
        mid = len(lines) // 2
        lines = lines[mid - 1 : mid + 2]

    return "...".join(lines)


# Inventory recommendations


def _count_pattern_types(patterns: list[dict[str, str]]) -> dict[str, int]:
    """Count pattern types from list of patterns."""
    pattern_types: dict[str, int] = {}
    for pattern in patterns:
        ptype = pattern.get("type", "unknown")
        pattern_types[ptype] = pattern_types.get(ptype, 0) + 1
    return pattern_types


def _extract_groups_from_query(query: str) -> tuple[str | None, str | None]:
    """Extract role and environment from a single query."""
    role = None
    env = None
    if "role:" in query:
        role_match = re.search(r"role:([^\s]+)", query)
        if role_match:
            role = role_match.group(1)
    if "environment:" in query:
        env_match = re.search(r"environment:([^\s]+)", query)
        if env_match:
            env = env_match.group(1)
    return role, env


def _extract_role_and_environment_groups(
    patterns: list[dict[str, str]],
) -> tuple[set[str], set[str]]:
    """Extract role and environment groups from patterns."""
    role_groups: set[str] = set()
    environment_groups: set[str] = set()

    for pattern in patterns:
        if pattern.get("type") != "search":
            continue
        role, env = _extract_groups_from_query(pattern.get("query", ""))
        if role:
            role_groups.add(role)
        if env:
            environment_groups.add(env)

    return role_groups, environment_groups


def _add_group_recommendations(
    recommendations: dict[str, Any],
    role_groups: set[str],
    environment_groups: set[str],
) -> None:
    """Add group recommendations based on discovered groups."""
    for role in role_groups:
        recommendations["groups"][f"role_{role}"] = {
            "description": f"Hosts with Chef role: {role}",
            "vars": {"chef_role": role},
        }

    for env in environment_groups:
        recommendations["groups"][f"env_{env}"] = {
            "description": f"Hosts in Chef environment: {env}",
            "vars": {"chef_environment": env},
        }


def _add_general_recommendations(
    recommendations: dict[str, Any], patterns: list[dict[str, str]]
) -> None:
    """Add general migration recommendations based on patterns."""
    if len(patterns) > 5:
        recommendations["notes"].append(
            "Complex search patterns - consider Chef server integration"
        )

    if any(p.get("type") == "data_bag_access" for p in patterns):
        recommendations["notes"].append(
            "Data bag access detected - consider Ansible Vault migration"
        )


def _generate_inventory_recommendations(
    patterns: list[dict[str, str]],
) -> dict[str, Any]:
    """Generate inventory structure recommendations from search patterns."""
    recommendations: dict[str, Any] = {
        "groups": {},
        "structure": "static",  # vs dynamic
        "variables": {},
        "notes": [],
    }

    # Count pattern types and recommend structure
    pattern_types = _count_pattern_types(patterns)
    if pattern_types.get("search", 0) > 2:
        recommendations["structure"] = "dynamic"
        recommendations["notes"].append(
            "Multiple search patterns detected - dynamic inventory recommended"
        )

    # Extract and add group recommendations
    role_groups, environment_groups = _extract_role_and_environment_groups(patterns)
    _add_group_recommendations(recommendations, role_groups, environment_groups)

    # Add general recommendations
    _add_general_recommendations(recommendations, patterns)

    return recommendations


# Playbook generation


def _build_playbook_header(recipe_name: str) -> list[str]:
    """Build playbook header with metadata."""
    return [
        "---",
        f"# Ansible playbook generated from Chef recipe: {recipe_name}",
        f"# Generated by SousChef on {_get_current_timestamp()}",
        "",
        "- name: Configure system using converted Chef recipe",
        "  hosts: all",
        "  become: true",
        "  gather_facts: true",
        "",
        "  vars:",
        "    # Variables extracted from Chef recipe",
    ]


def _add_playbook_variables(
    playbook_lines: list[str], raw_content: str, recipe_file: Path
) -> None:
    """Extract and add variables section to playbook."""
    variables = _extract_recipe_variables(raw_content)

    # Try to parse attributes file
    attributes_path = recipe_file.parent.parent / "attributes" / "default.rb"
    if attributes_path.exists():
        attributes_content = parse_attributes(str(attributes_path))
        if not attributes_content.startswith(
            "Error:"
        ) and not attributes_content.startswith("Warning:"):
            # Parse the resolved attributes
            attr_vars = _extract_attribute_variables(attributes_content)
            variables.update(attr_vars)

    for var_name, var_value in variables.items():
        playbook_lines.append(f"    {var_name}: {var_value}")

    if not variables:
        playbook_lines.append("    # No variables found")

    playbook_lines.extend(["", "  tasks:"])


def _convert_and_collect_resources(
    parsed_content: str, raw_content: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert Chef resources to Ansible tasks and collect handlers."""
    resources = _extract_resources_from_parsed_content(parsed_content, raw_content)
    tasks = []
    handlers = []

    for resource in resources:
        task_result = _convert_resource_to_task_dict(resource, raw_content)
        tasks.append(task_result["task"])
        if task_result["handlers"]:
            handlers.extend(task_result["handlers"])

    return tasks, handlers


def _format_item_lines(item_yaml: str) -> list[str]:
    """Format a single task/handler's YAML lines with proper indentation."""
    formatted = []
    for i, line in enumerate(item_yaml.split("\n")):
        if i == 0 or line.strip():  # First line gets 4-space indent
            formatted.append(f"    {line}")
        else:  # Empty lines preserved as-is
            formatted.append(line)
    return formatted


def _add_formatted_items(
    playbook_lines: list[str],
    items: list[dict[str, Any]],
    default_message: str,
) -> None:
    """Add formatted tasks or handlers to playbook."""
    if not items:
        playbook_lines.append(f"    {default_message}")
        return

    for i, item in enumerate(items):
        if i > 0:
            playbook_lines.append("")
        playbook_lines.extend(_format_item_lines(_format_ansible_task(item)))


def _generate_playbook_structure(
    parsed_content: str, raw_content: str, recipe_file: Path
) -> str:
    """Generate complete playbook structure from parsed recipe content."""
    playbook_lines = _build_playbook_header(recipe_file.name)
    _add_playbook_variables(playbook_lines, raw_content, recipe_file)

    # Convert resources to tasks and handlers
    tasks, handlers = _convert_and_collect_resources(parsed_content, raw_content)

    # Add tasks section
    _add_formatted_items(playbook_lines, tasks, "# No tasks found")

    # Add handlers section if any
    if handlers:
        playbook_lines.extend(["", "  handlers:"])
        _add_formatted_items(playbook_lines, handlers, "")

    return "\n".join(playbook_lines)


def _get_current_timestamp() -> str:
    """Get current timestamp for playbook generation."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Variable extraction


def _extract_version_variable(raw_content: str) -> dict[str, str]:
    """Extract version specification from recipe content."""
    version_pattern = re.compile(r"version\s+['\"]([^'\"]+)['\"]")
    versions = version_pattern.findall(raw_content)
    if versions:
        return {"package_version": f'"{versions[0]}"'}
    return {}


def _extract_content_variables(raw_content: str) -> dict[str, str]:
    """Extract content and source specifications from recipe content."""
    variables = {}

    # Extract content specifications
    content_pattern = re.compile(r"content\s+['\"]([^'\"]*)['\"]", re.DOTALL)
    contents = content_pattern.findall(raw_content)
    if contents:
        variables["file_content"] = f'"{contents[0]}"'

    # Extract source specifications for templates
    source_pattern = re.compile(r"source\s+['\"]([^'\"]+)['\"]")
    sources = source_pattern.findall(raw_content)
    if sources:
        variables["template_source"] = f'"{sources[0]}"'

    return variables


def _extract_ownership_variables(raw_content: str) -> dict[str, str]:
    """Extract owner and group specifications from recipe content."""
    variables = {}

    # Extract owner specifications
    owner_pattern = re.compile(r"owner\s+['\"]([^'\"]+)['\"]")
    owners = owner_pattern.findall(raw_content)
    if owners and owners[0] not in ["root"]:  # Skip default root
        variables["file_owner"] = f'"{owners[0]}"'

    # Extract group specifications
    group_pattern = re.compile(r"group\s+['\"]([^'\"]+)['\"]")
    groups = group_pattern.findall(raw_content)
    if groups and groups[0] not in ["root"]:  # Skip default root
        variables["file_group"] = f'"{groups[0]}"'

    return variables


def _extract_mode_variables(raw_content: str) -> dict[str, str]:
    """Extract mode specifications from recipe content."""
    # Extract mode specifications
    mode_pattern = re.compile(r"mode\s+['\"]([^'\"]+)['\"]")
    modes = mode_pattern.findall(raw_content)
    unique_modes = list(set(modes))

    if len(unique_modes) == 1:
        return {"file_mode": f'"{unique_modes[0]}"'}
    elif len(unique_modes) > 1:
        return {"directory_mode": '"0755"', "file_mode": '"0644"'}
    return {}


def _convert_ruby_value_to_yaml(ruby_value: str) -> str:  # noqa: C901
    """Convert Ruby value syntax to YAML-compatible format."""
    ruby_value = ruby_value.strip()

    # Handle Ruby hash syntax { key => value, ... }
    if ruby_value.startswith("{") and ruby_value.endswith("}"):
        return _convert_ruby_hash_to_yaml(ruby_value)

    # Handle arrays [item1, item2, ...]
    if ruby_value.startswith("[") and ruby_value.endswith("]"):
        return _convert_ruby_array_to_yaml(ruby_value)

    # Handle primitive values (strings, numbers, booleans, nil)
    return _convert_primitive_value(ruby_value)


def _is_attribute_separator(line: str) -> bool:
    """Check if a line indicates the start of a new attribute or metadata."""
    stripped = line.strip()
    return (
        stripped.startswith(ATTRIBUTE_PREFIX)
        or stripped.startswith("Precedence: ")
        or stripped.startswith("=")
        or stripped.startswith("Total attributes:")
        or stripped.startswith("⚠️")
    )


def _collect_value_lines(lines: list[str], start_index: int) -> tuple[list[str], int]:
    """Collect all lines belonging to a value until the next attribute separator."""
    value_lines = []
    i = start_index

    while i < len(lines):
        next_line = lines[i]
        if _is_attribute_separator(next_line):
            break
        value_lines.append(lines[i])
        i += 1

    return value_lines, i


def _extract_attribute_variables(attributes_content: str) -> dict[str, str]:
    """Extract Ansible variables from parsed Chef attributes."""
    variables = {}
    lines = attributes_content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(ATTRIBUTE_PREFIX):
            current_attr = line.split(ATTRIBUTE_PREFIX)[1]
            i += 1  # Move to next line to look for Value:

            # Find and collect value lines
            value_lines, i = _find_and_collect_value_lines(lines, i)

            # Process the collected value lines
            if current_attr and value_lines:
                full_value = "\n".join(value_lines).strip()
                ansible_var = _convert_chef_attr_path_to_ansible_var(current_attr)
                yaml_value = _convert_ruby_value_to_yaml(full_value)
                variables[ansible_var] = yaml_value
        else:
            i += 1

    return variables


def _find_and_collect_value_lines(
    lines: list[str], start_index: int
) -> tuple[list[str], int]:
    """
    Find the Value: line and collect all value lines until next attribute separator.

    Find the Value: line and collect all value lines until next attribute separator.
    """
    value_lines: list[str] = []
    i = start_index

    # Look for the Value: line
    while i < len(lines):
        next_line = lines[i]
        if next_line.strip().startswith(VALUE_PREFIX):
            # Found value start, collect all value lines
            value_start = next_line.split(VALUE_PREFIX, 1)[1]
            collected_lines, i = _collect_value_lines(lines, i + 1)
            value_lines = [value_start] + collected_lines
            break
        elif _is_attribute_separator(next_line):
            # Hit another attribute before finding value
            break
        i += 1
    else:
        # No more lines
        i += 1

    return value_lines, i


def _convert_ruby_hash_to_yaml(ruby_hash: str) -> str:
    """Convert Ruby hash syntax { key => value, ... } to YAML flow style."""
    try:
        # Remove outer braces
        hash_content = ruby_hash[1:-1].strip()
        if not hash_content:
            return "{}"

        # Split by commas, respecting nested structures
        yaml_pairs = _split_by_commas_with_nesting(hash_content)

        # Convert each pair from Ruby syntax to YAML
        flow_pairs = []
        for pair in yaml_pairs:
            if "=>" in pair:
                key_part, value_part = pair.split("=>", 1)
                key = key_part.strip()
                value = value_part.strip()

                # Remove quotes from key if present
                key = key.strip("'\"")

                # Convert value recursively if it's complex
                value = _convert_ruby_value_to_yaml(value)
                flow_pairs.append(f"{key}: {value}")
            else:
                # Malformed pair, keep as comment
                flow_pairs.append(f"# TODO: Fix malformed pair: {pair}")

        return "{" + ", ".join(flow_pairs) + "}" if flow_pairs else "{}"

    except Exception:
        # If conversion fails, return as-is with a comment
        return f"# TODO: Convert Ruby hash: {ruby_hash}"


def _convert_ruby_array_to_yaml(ruby_array: str) -> str:
    """Convert Ruby array syntax [item1, item2, ...] to YAML flow style."""
    try:
        # Remove outer brackets
        array_content = ruby_array[1:-1].strip()
        if not array_content:
            return "[]"

        # Split by commas, respecting nested structures
        items = _split_by_commas_with_nesting(array_content)

        # Convert items recursively if they're complex
        flow_items = [_convert_ruby_value_to_yaml(item) for item in items]

        return "[" + ", ".join(flow_items) + "]" if flow_items else "[]"

    except Exception:
        return ruby_array  # Return as-is if parsing fails


def _split_by_commas_with_nesting(content: str) -> list[str]:
    """Split content by commas while respecting nested braces and brackets."""
    parts = []
    current_part = ""
    in_quotes = False
    quote_char = None
    brace_depth = 0
    bracket_depth = 0

    for char in content:
        if _is_quote_char(char) and brace_depth == 0 and bracket_depth == 0:
            in_quotes, quote_char = _handle_quote_transition(
                char, in_quotes, quote_char
            )
        elif not in_quotes:
            brace_depth, bracket_depth = _update_nesting_depths(
                char, brace_depth, bracket_depth
            )
            if _should_split_at_comma(char, in_quotes, brace_depth, bracket_depth):
                parts.append(current_part.strip())
                current_part = ""
                continue

        current_part += char

    # Add the last part
    if current_part.strip():
        parts.append(current_part.strip())

    return parts


def _is_quote_char(char: str) -> bool:
    """Check if character is a quote."""
    return char in ['"', "'"]


def _handle_quote_transition(
    char: str, in_quotes: bool, quote_char: str | None
) -> tuple[bool, str | None]:
    """Handle quote character transitions."""
    if not in_quotes:
        return True, char
    elif char == quote_char:
        return False, None
    return in_quotes, quote_char


def _update_nesting_depths(
    char: str, brace_depth: int, bracket_depth: int
) -> tuple[int, int]:
    """Update brace and bracket nesting depths."""
    if char == "{":
        brace_depth += 1
    elif char == "}":
        brace_depth -= 1
    elif char == "[":
        bracket_depth += 1
    elif char == "]":
        bracket_depth -= 1
    return brace_depth, bracket_depth


def _should_split_at_comma(
    char: str, in_quotes: bool, brace_depth: int, bracket_depth: int
) -> bool:
    """Determine if we should split at this comma."""
    return char == "," and not in_quotes and brace_depth == 0 and bracket_depth == 0


def _convert_primitive_value(ruby_value: str) -> str:
    """Convert primitive Ruby values (strings, numbers, booleans, nil)."""
    # Handle quoted strings
    if (
        ruby_value.startswith('"')
        and ruby_value.endswith('"')
        or ruby_value.startswith("'")
        and ruby_value.endswith("'")
    ):
        return ruby_value  # Already properly quoted

    # Handle numbers
    try:
        int(ruby_value)
        return ruby_value
    except ValueError:
        pass

    try:
        float(ruby_value)
        return ruby_value
    except ValueError:
        pass

    # Handle booleans
    if ruby_value.lower() in ["true", "false"]:
        return ruby_value.lower()

    # Handle nil
    if ruby_value.lower() == "nil":
        return "null"

    # For strings that aren't quoted, quote them
    return f'"{ruby_value}"'


def _convert_chef_attr_path_to_ansible_var(attr_path: str) -> str:
    """Convert Chef attribute path to Ansible variable name."""
    # Replace dots with underscores, handle special cases
    parts = attr_path.split(".")
    if len(parts) >= 2:
        # For cookbook-specific attrs like '301.version' -> 'threeohone_version'
        cookbook_name = parts[0]
        attr_name = "_".join(parts[1:])

        # Convert numbers to words for readability
        number_words = {
            "301": "threeohone",
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
            "6": "six",
            "7": "seven",
            "8": "eight",
            "9": "nine",
            "0": "zero",
        }

        # Replace digits with words
        readable_cookbook = "".join(number_words.get(c, c) for c in cookbook_name)
        return f"{readable_cookbook}_{attr_name}"

    # Fallback: just replace dots with underscores
    return attr_path.replace(".", "_")


def _extract_recipe_variables(raw_content: str) -> dict[str, str]:
    """Extract variables from Chef recipe content."""
    variables = {}

    # Combine all extracted variables
    variables.update(_extract_version_variable(raw_content))
    variables.update(_extract_content_variables(raw_content))
    variables.update(_extract_ownership_variables(raw_content))
    variables.update(_extract_mode_variables(raw_content))

    return variables


# Resource extraction and conversion


def _parse_resource_block(block: str) -> dict[str, str] | None:
    """Parse a single resource (or include_recipe) block into a dictionary."""
    trimmed = block.strip()
    if not trimmed:
        return None

    # Handle include_recipe blocks emitted by parse_recipe
    if trimmed.startswith("Include Recipe"):
        recipe_match = re.search(r"Recipe:\s*([^\n]+)", block)
        if not recipe_match:
            return None
        return {
            "type": "include_recipe",
            "name": recipe_match.group(1).strip(),
            "action": "include",
            "properties": "",
        }

    if not trimmed.startswith("Resource"):
        return None

    resource: dict[str, str] = {}

    # Extract resource type
    type_match = re.search(r"Type:\s*(\w+)", block)
    if type_match:
        resource["type"] = type_match.group(1)

    # Extract resource name
    name_match = re.search(r"Name:\s*([^\n]+)", block)
    if name_match:
        resource["name"] = name_match.group(1).strip()

    # Extract action (default to "create")
    action_match = re.search(r"Action:\s*([^\n]+)", block)
    resource["action"] = action_match.group(1).strip() if action_match else "create"

    # Extract properties
    props_match = re.search(r"Properties:\n?((?:(?!\n\n).)*)", block, re.DOTALL)
    resource["properties"] = props_match.group(1).strip() if props_match else ""

    # Return None if missing required fields
    if not resource.get("type") or not resource.get("name"):
        return None

    return resource


def _extract_resources_from_parsed_content(
    parsed_content: str, raw_content: str
) -> list[dict[str, str]]:
    """Extract resource information from parsed recipe content."""
    resource_blocks = re.split(
        r"\n(?=(Resource \d+:|Include Recipe \d+:))", parsed_content
    )
    resources = []
    for block in resource_blocks:
        resource = _parse_resource_block(block)
        if resource:
            # Find position in raw_content to preserve order
            position = _find_resource_position_in_raw(resource, raw_content)
            resource["_position"] = position  # type: ignore
            resources.append(resource)

    # Sort by position to preserve original order
    resources.sort(key=lambda r: r.get("_position", 999999))

    # Remove position key
    for r in resources:
        r.pop("_position", None)

    return resources


def _find_resource_position_in_raw(resource: dict[str, str], raw_content: str) -> int:
    """Find the position of a resource in raw content."""
    if resource["type"] == "include_recipe":
        pattern = rf'include_recipe\s+[\'"]({re.escape(resource["name"])})[\'"]'
    elif resource["type"] == "nodejs_npm":
        pattern = rf'nodejs_npm\s+[\'"]({re.escape(resource["name"])})[\'"]'
    else:
        # Generic pattern
        pattern = rf'{resource["type"]}\s+[\'"]({re.escape(resource["name"])})[\'"]'

    match = re.search(pattern, raw_content)
    return match.start() if match else 999999


def _extract_nodejs_npm_version(raw_content: str, package_name: str) -> str | None:
    """Extract version for nodejs_npm resources from raw recipe content."""
    pattern = (
        rf"nodejs_npm\s+[\"']{re.escape(package_name)}[\"']\s+do"
        rf"(?P<body>.{{0,400}}?)^end"
    )
    match = re.search(pattern, raw_content, re.DOTALL | re.MULTILINE)
    if not match:
        return None

    body = match.group("body")
    version_match = re.search(r"version\s+([^\n#]+)", body)
    if not version_match:
        return None

    return version_match.group(1).strip()


# Notification handling


def _extract_notify_declarations(
    resource: dict[str, str], raw_content: str
) -> list[tuple[str, str, str]]:
    """Extract notifies declarations from a resource block."""
    resource_type_escaped = resource["type"]
    resource_name_escaped = re.escape(resource["name"])
    resource_pattern = (
        resource_type_escaped
        + REGEX_WHITESPACE_QUOTE
        + resource_name_escaped
        + REGEX_QUOTE_DO_END
    )
    resource_match = re.search(resource_pattern, raw_content, re.DOTALL | re.MULTILINE)

    if not resource_match:
        return []

    resource_block = resource_match.group(1)
    notify_pattern = re.compile(
        r'notifies\s+:(\w+),\s*[\'"]([^\'\"]+)[\'"]\s*,?\s*:?(\w+)?'
    )
    return notify_pattern.findall(resource_block)


def _extract_subscribe_declarations(raw_content: str) -> list[tuple[str, str, str]]:
    """Extract subscribes declarations from raw content."""
    subscribes_pattern = re.compile(
        r'subscribes\s+:(\w+),\s*[\'"]([^\'\"]+)[\'"]\s*,?\s*:?(\w+)?'
    )
    return subscribes_pattern.findall(raw_content)


def _process_notifications(
    notifications: list[tuple[str, str, str]],
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    """Process notification declarations and create handlers."""
    handlers = []
    for notify_action, notify_target, _notify_timing in notifications:
        target_match = re.match(REGEX_RESOURCE_BRACKET, notify_target)
        if target_match:
            target_type = target_match.group(1)
            target_name = target_match.group(2)

            handler = _create_handler(notify_action, target_type, target_name)
            if handler:
                if "notify" not in task:
                    task["notify"] = []
                task["notify"].append(handler["name"])
                handlers.append(handler)

    return handlers


def _process_subscribes(
    resource: dict[str, str],
    subscribes: list[tuple[str, str, str]],
    raw_content: str,
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    """Process subscribes declarations and create handlers."""
    handlers = []
    for sub_action, sub_target, _sub_timing in subscribes:
        target_match = re.match(REGEX_RESOURCE_BRACKET, sub_target)
        if not target_match:
            continue

        target_type = target_match.group(1)
        target_name = target_match.group(2)

        if resource["type"] != target_type or resource["name"] != target_name:
            continue

        subscriber_pattern = (
            rf"(\w+)\s+['\"]?[^'\"]*['\"]?\s+do\s*.{{0,1000}}?"
            rf"subscribes\s+:{sub_action}"
        )
        subscriber_match = re.search(subscriber_pattern, raw_content, re.DOTALL)

        if subscriber_match:
            subscriber_type = subscriber_match.group(1)
            handler = _create_handler(sub_action, subscriber_type, resource["name"])
            if handler:
                if "notify" not in task:
                    task["notify"] = []
                task["notify"].append(handler["name"])
                handlers.append(handler)

    return handlers


def _convert_resource_to_task_dict(
    resource: dict[str, str], raw_content: str
) -> dict[str, Any]:
    """Convert a Chef resource to an Ansible task dictionary with handlers."""
    # Enrich nodejs_npm resources with version info when it could not be parsed
    if resource["type"] == "nodejs_npm" and not resource.get("properties"):
        extracted_version = _extract_nodejs_npm_version(raw_content, resource["name"])
        if extracted_version is not None:
            resource["properties"] = str({"version": extracted_version})

    # Convert basic resource to task
    task = _convert_chef_resource_to_ansible(
        resource["type"], resource["name"], resource["action"], resource["properties"]
    )

    # Extract and convert Chef guards to Ansible when conditions
    guards = _extract_chef_guards(resource, raw_content)
    if guards:
        task.update(guards)

    # Process all handlers
    handlers = []

    # Handle enhanced notifications with timing
    notifications = _extract_enhanced_notifications(resource, raw_content)
    for notification in notifications:
        handler = _create_handler_with_timing(
            notification["action"],
            notification["target_type"],
            notification["target_name"],
            notification["timing"],
        )
        if handler:
            if "notify" not in task:
                task["notify"] = []
            task["notify"].append(handler["name"])
            handlers.append(handler)

    # Handle basic notifies declarations
    notifies = _extract_notify_declarations(resource, raw_content)
    handlers.extend(_process_notifications(notifies, task))

    # Handle subscribes (reverse notifications)
    subscribes = _extract_subscribe_declarations(raw_content)
    handlers.extend(_process_subscribes(resource, subscribes, raw_content, task))

    return {"task": task, "handlers": handlers}


def _create_handler(
    action: str, resource_type: str, resource_name: str
) -> dict[str, Any]:
    """Create an Ansible handler from Chef notification."""
    # Map Chef actions to Ansible states
    action_mappings = {
        "reload": "reloaded",
        "restart": "restarted",
        "start": "started",
        "stop": "stopped",
        "enable": "started",  # enabling usually means start too
        "run": "run",
    }

    if resource_type == "service":
        ansible_state = action_mappings.get(action, action)

        handler: dict[str, Any] = {
            "name": f"{action.capitalize()} {resource_name}",
            ANSIBLE_SERVICE_MODULE: {"name": resource_name, "state": ansible_state},
        }

        if action == "enable":
            handler[ANSIBLE_SERVICE_MODULE]["enabled"] = True

        return handler

    elif resource_type == "execute":
        handler = {
            "name": f"Run {resource_name}",
            "ansible.builtin.command": {"cmd": resource_name},
        }
        return handler

    return {}


def _extract_enhanced_notifications(
    resource: dict[str, str], raw_content: str
) -> list[dict[str, str]]:
    """Extract notification information with timing constraints for a resource."""
    notifications = []

    # Find the resource block in raw content
    resource_type_escaped = resource["type"]
    resource_name_escaped = re.escape(resource["name"])
    resource_pattern = (
        resource_type_escaped
        + REGEX_WHITESPACE_QUOTE
        + resource_name_escaped
        + REGEX_QUOTE_DO_END
    )
    resource_match = re.search(resource_pattern, raw_content, re.DOTALL | re.MULTILINE)

    if resource_match:
        resource_block = resource_match.group(1)

        # Enhanced notifies pattern that captures timing
        notify_pattern = re.compile(
            r'notifies\s+:(\w+),\s*[\'"]([^\'"]+)[\'"]\s*(?:,\s*:(\w+))?'
        )
        notifies = notify_pattern.findall(resource_block)

        for notify_action, notify_target, notify_timing in notifies:
            # Parse target like 'service[nginx]'
            target_match = re.match(REGEX_RESOURCE_BRACKET, notify_target)
            if target_match:
                target_type = target_match.group(1)
                target_name = target_match.group(2)

                notifications.append(
                    {
                        "action": notify_action,
                        "target_type": target_type,
                        "target_name": target_name,
                        "timing": notify_timing or "delayed",  # Default to delayed
                    }
                )

    return notifications


def _create_handler_with_timing(
    action: str, resource_type: str, resource_name: str, timing: str
) -> dict[str, Any]:
    """Create an Ansible handler with timing considerations."""
    handler = _create_handler(action, resource_type, resource_name)
    if handler:
        # Add timing metadata (can be used by Ansible playbook optimization)
        handler["_chef_timing"] = timing

        # For immediate timing, we could add listen/notify optimization
        if timing == "immediate":
            handler["_priority"] = "immediate"
            # Note: Ansible handlers always run at the end, but we can document
            # the original Chef timing intention for migration planning
            handler["# NOTE"] = "Chef immediate timing - consider task ordering"

    return handler


# Chef guard conversion


def _find_resource_block(resource: dict[str, str], raw_content: str) -> str | None:
    """Find the resource block in raw content."""
    resource_type_escaped = resource["type"]
    resource_name_escaped = re.escape(resource["name"])
    resource_pattern = (
        resource_type_escaped
        + REGEX_WHITESPACE_QUOTE
        + resource_name_escaped
        + REGEX_QUOTE_DO_END
    )
    resource_match = re.search(resource_pattern, raw_content, re.DOTALL | re.MULTILINE)

    if resource_match:
        return resource_match.group(1)
    return None


def _extract_guard_patterns(
    resource_block: str,
) -> tuple[list[str], list[str], list[str], list[str], list[str], list[str]]:
    """Extract all guard patterns from resource block including enhanced support."""
    # Extract only_if conditions
    only_if_pattern = re.compile(
        rf'only_if\s+[\'"]([^\'"]{{{1},{MAX_GUARD_LENGTH}}})[\'"]'
    )
    only_if_matches = only_if_pattern.findall(resource_block)

    # Extract not_if conditions
    not_if_pattern = re.compile(
        rf'not_if\s+[\'"]([^\'"]{{{1},{MAX_GUARD_LENGTH}}})[\'"]'
    )
    not_if_matches = not_if_pattern.findall(resource_block)

    # Extract only_if blocks (Ruby code blocks)
    only_if_block_pattern = re.compile(r"only_if\s+do\b(.*?)\bend", re.DOTALL)
    only_if_block_matches = only_if_block_pattern.findall(resource_block)

    # Extract not_if blocks (Ruby code blocks)
    not_if_block_pattern = re.compile(r"not_if\s+do\b(.*?)\bend", re.DOTALL)
    not_if_block_matches = not_if_block_pattern.findall(resource_block)

    # Extract only_if with curly brace blocks (lambda/proc syntax)
    only_if_lambda_pattern = re.compile(
        rf"only_if\s+\{{([^}}]{{{1},{MAX_GUARD_LENGTH}}})\}}", re.DOTALL
    )
    only_if_lambda_matches = only_if_lambda_pattern.findall(resource_block)
    only_if_block_matches.extend(only_if_lambda_matches)

    # Extract not_if with curly brace blocks (lambda/proc syntax)
    not_if_lambda_pattern = re.compile(
        rf"not_if\s+\{{([^}}]{{{1},{MAX_GUARD_LENGTH}}})\}}", re.DOTALL
    )
    not_if_lambda_matches = not_if_lambda_pattern.findall(resource_block)
    not_if_block_matches.extend(not_if_lambda_matches)

    # Extract only_if arrays [condition1, condition2]
    only_if_array_pattern = re.compile(
        rf"only_if\s+\[([^\]]{{{1},{MAX_GUARD_LENGTH}}})\]", re.DOTALL
    )
    only_if_array_matches = only_if_array_pattern.findall(resource_block)

    # Extract not_if arrays [condition1, condition2]
    not_if_array_pattern = re.compile(
        rf"not_if\s+\[([^\]]{{{1},{MAX_GUARD_LENGTH}}})\]", re.DOTALL
    )
    not_if_array_matches = not_if_array_pattern.findall(resource_block)

    return (
        only_if_matches,
        not_if_matches,
        only_if_block_matches,
        not_if_block_matches,
        only_if_array_matches,
        not_if_array_matches,
    )


def _process_only_if_guards(
    only_if_conditions: list[str],
    only_if_blocks: list[str],
    only_if_arrays: list[str],
) -> list[str]:
    """Process only_if guards and convert to Ansible when conditions."""
    when_conditions = []

    # Process only_if conditions
    for condition in only_if_conditions:
        ansible_condition = _convert_chef_condition_to_ansible(condition)
        if ansible_condition:
            when_conditions.append(ansible_condition)

    # Process only_if blocks
    for block in only_if_blocks:
        ansible_condition = _convert_chef_block_to_ansible(block, positive=True)
        if ansible_condition:
            when_conditions.append(ansible_condition)

    # Process only_if arrays (multiple conditions with AND logic)
    for array_content in only_if_arrays:
        array_conditions = _parse_guard_array(array_content, negate=False)
        when_conditions.extend(array_conditions)

    return when_conditions


def _process_not_if_guards(
    not_if_conditions: list[str],
    not_if_blocks: list[str],
    not_if_arrays: list[str],
) -> list[str]:
    """Process not_if guards and convert to Ansible when conditions."""
    when_conditions = []

    # Process not_if conditions (these become when conditions with negation)
    for condition in not_if_conditions:
        ansible_condition = _convert_chef_condition_to_ansible(condition, negate=True)
        if ansible_condition:
            when_conditions.append(ansible_condition)

    # Process not_if blocks
    for block in not_if_blocks:
        ansible_condition = _convert_chef_block_to_ansible(block, positive=False)
        if ansible_condition:
            when_conditions.append(ansible_condition)

    # Process not_if arrays (multiple conditions with AND logic, negated)
    for array_content in not_if_arrays:
        array_conditions = _parse_guard_array(array_content, negate=True)
        when_conditions.extend(array_conditions)

    return when_conditions


def _convert_guards_to_when_conditions(
    only_if_conditions: list[str],
    not_if_conditions: list[str],
    only_if_blocks: list[str],
    not_if_blocks: list[str],
    only_if_arrays: list[str],
    not_if_arrays: list[str],
) -> list[str]:
    """Convert Chef guards to Ansible when conditions with enhanced support."""
    when_conditions = []

    # Process only_if guards
    when_conditions.extend(
        _process_only_if_guards(only_if_conditions, only_if_blocks, only_if_arrays)
    )

    # Process not_if guards
    when_conditions.extend(
        _process_not_if_guards(not_if_conditions, not_if_blocks, not_if_arrays)
    )

    return when_conditions


def _extract_chef_guards(resource: dict[str, str], raw_content: str) -> dict[str, Any]:
    """Extract Chef guards (only_if, not_if) and convert to Ansible when conditions."""
    guards: dict[str, Any] = {}

    # Find the resource block in raw content
    resource_block = _find_resource_block(resource, raw_content)
    if not resource_block:
        return guards

    # Extract all guard patterns
    (
        only_if_conditions,
        not_if_conditions,
        only_if_blocks,
        not_if_blocks,
        only_if_arrays,
        not_if_arrays,
    ) = _extract_guard_patterns(resource_block)

    # Convert to Ansible when conditions
    when_conditions = _convert_guards_to_when_conditions(
        only_if_conditions,
        not_if_conditions,
        only_if_blocks,
        not_if_blocks,
        only_if_arrays,
        not_if_arrays,
    )

    # Format the when clause
    if when_conditions:
        if len(when_conditions) == 1:
            guards["when"] = when_conditions[0]
        else:
            # Multiple conditions - combine with 'and'
            guards["when"] = when_conditions

    return guards


def _is_opening_delimiter(char: str, in_quotes: bool) -> bool:
    """Check if character is an opening delimiter."""
    return char == "{" and not in_quotes


def _is_closing_delimiter(char: str, in_quotes: bool) -> bool:
    """Check if character is a closing delimiter."""
    return char == "}" and not in_quotes


def _is_quote_character(char: str) -> bool:
    """Check if character is a quote."""
    return char in ['"', "'"]


def _should_split_here(char: str, in_quotes: bool, in_block: int) -> bool:
    """Determine if we should split at this comma."""
    return char == "," and not in_quotes and in_block == 0


def _split_guard_array_parts(array_content: str) -> list[str]:
    """
    Split array content by commas, respecting quotes and blocks.

    Handles Chef guard arrays like: ['test -f /file', { block }, "string"]
    Tracks quote state and brace nesting to avoid splitting inside strings or blocks.

    Args:
        array_content: Raw array content string

    Returns:
        List of array parts split by commas

    """
    parts = []
    current_part = ""
    in_quotes = False
    in_block = 0
    quote_char = None

    for char in array_content:
        # Handle quote transitions
        if _is_quote_character(char) and not in_block:
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None

        # Handle block nesting
        elif _is_opening_delimiter(char, in_quotes):
            in_block += 1
        elif _is_closing_delimiter(char, in_quotes):
            in_block -= 1

        # Handle splits at commas
        elif _should_split_here(char, in_quotes, in_block):
            parts.append(current_part.strip())
            current_part = ""
            continue

        current_part += char

    # Add final part if not empty
    if current_part.strip():
        parts.append(current_part.strip())

    return parts


def _extract_lambda_body(part: str) -> str:
    """Extract lambda body from lambda syntax."""
    if "->" in part:
        return part.split("->", 1)[1].strip()
    if "lambda" in part and "{" in part:
        return part.split("{", 1)[1].rsplit("}", 1)[0].strip()
    return ""


def _process_guard_array_part(part: str, negate: bool) -> str | None:
    """Process a single guard array part and convert to Ansible condition."""
    part = part.strip()
    if not part:
        return None

    # Handle string conditions
    if part.startswith(("'", '"')) and part.endswith(("'", '"')):
        condition_str = part[1:-1]
        return _convert_chef_condition_to_ansible(condition_str, negate=negate)

    # Handle block conditions
    if part.startswith("{") and part.endswith("}"):
        block_content = part[1:-1].strip()
        return _convert_chef_block_to_ansible(block_content, positive=not negate)

    # Handle lambda syntax
    if part.startswith("lambda") or part.startswith("->"):
        lambda_body = _extract_lambda_body(part)
        if lambda_body:
            return _convert_chef_block_to_ansible(lambda_body, positive=not negate)

    return None


def _parse_guard_array(array_content: str, negate: bool = False) -> list[str]:
    """Parse Chef guard array content and convert to Ansible conditions."""
    parts = _split_guard_array_parts(array_content)
    conditions = []

    for part in parts:
        condition = _process_guard_array_part(part, negate)
        if condition:
            conditions.append(condition)

    return conditions


def _convert_chef_condition_to_ansible(condition: str, negate: bool = False) -> str:
    """Convert a Chef condition string to Ansible when condition."""
    # Common Chef to Ansible condition mappings
    condition_mappings = {
        # File existence checks
        r'File\.exist\?\([\'"]([^\'"]+)[\'"]\)': (
            r'ansible_check_mode or {{ "\1" is file }}'
        ),
        r'File\.directory\?\([\'"]([^\'"]+)[\'"]\)': (
            r'ansible_check_mode or {{ "\1" is directory }}'
        ),
        r'File\.executable\?\([\'"]([^\'"]+)[\'"]\)': (
            r'ansible_check_mode or {{ "\1" is executable }}'
        ),
        # Package checks
        r'system\([\'"]which\s+(\w+)[\'"]\)': (
            r'ansible_check_mode or {{ ansible_facts.packages["\1"] is defined }}'
        ),
        # Service checks
        r'system\([\'"]systemctl\s+is-active\s+(\w+)[\'"]\)': (
            r"ansible_check_mode or "
            r'{{ ansible_facts.services["\1"].state == "running" }}'
        ),
        r'system\([\'"]service\s+(\w+)\s+status[\'"]\)': (
            r"ansible_check_mode or "
            r'{{ ansible_facts.services["\1"].state == "running" }}'
        ),
        # Platform checks
        r"platform\?": r"ansible_facts.os_family",
        r"platform_family\?": r"ansible_facts.os_family",
        # Node attribute checks
        r'node\[[\'"]([^\'"]+)[\'"]\]': r'hostvars[inventory_hostname]["\1"]',
        r"node\.([a-zA-Z_][a-zA-Z0-9_.]*)": r'hostvars[inventory_hostname]["\1"]',
    }

    # Apply mappings
    converted = condition
    for chef_pattern, ansible_replacement in condition_mappings.items():
        converted = re.sub(
            chef_pattern, ansible_replacement, converted, flags=re.IGNORECASE
        )

    # Handle simple command checks
    if converted == condition:  # No mapping found, treat as shell command
        converted = (
            f"ansible_check_mode or {{ ansible_facts.env.PATH is defined "
            f'and "{condition}" | length > 0 }}'
        )

    if negate:
        converted = f"not ({converted})"

    return converted


def _handle_file_existence_block(block: str, positive: bool) -> str | None:
    """Handle File.exist? patterns in Chef blocks."""
    file_exist_patterns = [
        r'File\.exist\?\([\'"]([^\'"]+)[\'"]\)',
        r'File\.exists\?\([\'"]([^\'"]+)[\'"]\)',
        r'File\.exist\?\("([^"]+)"\)',
        r'File\.exist\?\((["\'])?#\{([^}]+)\}\1\)',
    ]

    for pattern in file_exist_patterns:
        file_match = re.search(pattern, block)
        if file_match:
            path = file_match.group(1) if len(file_match.groups()) >= 1 else ""
            if "#{" in path:
                path = re.sub(REGEX_RUBY_INTERPOLATION, JINJA2_VAR_REPLACEMENT, path)
            # Use Ansible's native Jinja2 file test for better performance
            condition = f'ansible_check_mode or "{path}" is file'
            return condition if positive else f"not ({condition})"

    return None


def _handle_directory_existence_block(block: str, positive: bool) -> str | None:
    """Handle File.directory? patterns in Chef blocks."""
    dir_patterns = [
        r'File\.directory\?\([\'"]([^\'"]+)[\'"]\)',
        r'File\.directory\?\("([^"]+)"\)',
    ]

    for pattern in dir_patterns:
        dir_match = re.search(pattern, block)
        if dir_match:
            path = dir_match.group(1)
            if "#{" in path:
                path = re.sub(REGEX_RUBY_INTERPOLATION, JINJA2_VAR_REPLACEMENT, path)
            # Use Ansible's native Jinja2 directory test for better performance
            condition = f'ansible_check_mode or "{path}" is directory'
            return condition if positive else f"not ({condition})"

    return None


def _handle_command_execution_block(block: str, positive: bool) -> str | None:
    """Handle system() and backtick command execution patterns."""
    system_patterns = [
        r'system\([\'"]([^\'"]+)[\'"]\)',
        r"`([^`]+)`",
    ]

    for pattern in system_patterns:
        system_match = re.search(pattern, block)
        if system_match:
            cmd = system_match.group(1)
            if cmd.startswith("which "):
                pkg = cmd.split()[1]
                condition = (
                    f"ansible_check_mode or ansible_facts.packages['{pkg}'] is defined"
                )
            else:
                condition = "ansible_check_mode or true  # TODO: Review shell command"
            return condition if positive else f"not ({condition})"

    return None


def _handle_node_attribute_block(block: str, positive: bool) -> str | None:
    """Handle node attribute checks in Chef blocks."""
    if NODE_PREFIX in block or "node." in block:
        converted = re.sub(
            r"node\[['\"]([^'\"]+)['\"]\]",
            r"hostvars[inventory_hostname]['\1']",
            block,
        )
        converted = re.sub(
            r"node\.([a-zA-Z_]\w*)",
            r"hostvars[inventory_hostname]['\1']",
            converted,
        )
        return converted if positive else f"not ({converted})"

    return None


def _handle_platform_check_block(block: str, positive: bool) -> str | None:
    """Handle platform? and platform_family? checks."""
    if "platform?" in block.lower() or "platform_family?" in block.lower():
        condition = "ansible_facts.os_family is defined"
        return condition if positive else f"not ({condition})"

    return None


def _convert_chef_block_to_ansible(block: str, positive: bool = True) -> str:
    """Convert a Chef condition block to Ansible when condition."""
    block = block.strip()

    # Handle simple boolean returns
    if block.lower() in ["true", "false"]:
        is_true = block.lower() == "true"
        return str(is_true if positive else not is_true).lower()

    # Handle ::File prefix (Chef's scope resolution)
    block = block.replace("::File.", "File.")

    # Try each handler in sequence
    handlers = [
        _handle_file_existence_block,
        _handle_directory_existence_block,
        _handle_command_execution_block,
        _handle_node_attribute_block,
        _handle_platform_check_block,
    ]

    for handler in handlers:
        condition = handler(block, positive)
        if condition is not None:
            return condition

    # For complex blocks, create a comment indicating manual review needed
    return f"# TODO: Review Chef block condition: {block[:50]}..."
