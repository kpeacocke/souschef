"""SousChef MCP Server - Chef to Ansible conversion assistant."""

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Create a new FastMCP server
mcp = FastMCP("souschef")

# Chef resource to Ansible module mappings
RESOURCE_MAPPINGS = {
    "package": "ansible.builtin.package",
    "apt_package": "ansible.builtin.apt",
    "yum_package": "ansible.builtin.yum",
    "service": "ansible.builtin.service",
    "systemd_unit": "ansible.builtin.systemd",
    "template": "ansible.builtin.template",
    "file": "ansible.builtin.file",
    "directory": "ansible.builtin.file",
    "execute": "ansible.builtin.command",
    "bash": "ansible.builtin.shell",
    "script": "ansible.builtin.script",
    "user": "ansible.builtin.user",
    "group": "ansible.builtin.group",
    "cron": "ansible.builtin.cron",
    "mount": "ansible.builtin.mount",
    "git": "ansible.builtin.git",
}

# Chef action to Ansible state mappings
ACTION_TO_STATE = {
    "create": "present",
    "delete": "absent",
    "remove": "absent",
    "install": "present",
    "upgrade": "latest",
    "purge": "absent",
    "enable": "started",
    "disable": "stopped",
    "start": "started",
    "stop": "stopped",
    "restart": "restarted",
    "reload": "reloaded",
}

# ERB to Jinja2 pattern mappings
ERB_PATTERNS = {
    # Variable output: <%= var %> -> {{ var }}
    "output": (r"<%=\s*(.+?)\s*%>", r"{{ \1 }}"),
    # Variable with node prefix: <%= node['attr'] %> -> {{ attr }}
    "node_attr": (r"<%=\s*node\[(['\"])(.+?)\1\]\s*%>", r"{{ \2 }}"),
    # If statements: <% if condition %> -> {% if condition %}
    "if_start": (r"<%\s*if\s+(.+?)\s*%>", r"{% if \1 %}"),
    # Unless (negated if): <% unless condition %> -> {% if not condition %}
    "unless": (r"<%\s*unless\s+(.+?)\s*%>", r"{% if not \1 %}"),
    # Else: <% else %> -> {% else %}
    "else": (r"<%\s*else\s*%>", r"{% else %}"),
    # Elsif: <% elsif condition %> -> {% elif condition %}
    "elsif": (r"<%\s*elsif\s+(.+?)\s*%>", r"{% elif \1 %}"),
    # End: <% end %> -> {% endif %}
    "end": (r"<%\s*end\s*%>", r"{% endif %}"),
    # Each loop: <% array.each do |item| %> -> {% for item in array %}
    # Use [^%]+ to prevent matching across %> boundaries
    "each": (r"<%\s*([^%]+?)\.each\s+do\s+\|(\w+)\|\s*%>", r"{% for \2 in \1 %}"),
}


@mcp.tool()
def parse_template(path: str) -> str:
    """Parse a Chef ERB template file and convert to Jinja2.

    Args:
        path: Path to the ERB template file.

    Returns:
        JSON string with extracted variables and Jinja2-converted template.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        # Extract variables
        variables = _extract_template_variables(content)

        # Convert ERB to Jinja2
        jinja2_content = _convert_erb_to_jinja2(content)

        result = {
            "original_file": str(file_path),
            "variables": sorted(variables),
            "jinja2_template": jinja2_content,
        }

        import json

        return json.dumps(result, indent=2)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _strip_ruby_comments(content: str) -> str:
    """Remove Ruby comments from code.

    Args:
        content: Ruby code content.

    Returns:
        Content with comments removed.

    """
    # Remove single-line comments but preserve strings
    lines = []
    for line in content.split("\n"):
        # Skip if line is only a comment
        if line.strip().startswith("#"):
            continue
        # Remove inline comments (simple approach - doesn't handle # in strings)
        comment_pos = line.find("#")
        if comment_pos > 0:
            # Check if # is inside a string by counting quotes before it
            before_comment = line[:comment_pos]
            single_quotes = before_comment.count("'") - before_comment.count("\\'")
            double_quotes = before_comment.count('"') - before_comment.count('\\"')
            # If odd number of quotes, # is inside a string
            if single_quotes % 2 == 0 and double_quotes % 2 == 0:
                line = line[:comment_pos]
        lines.append(line)
    return "\n".join(lines)


def _extract_output_variables(content: str, variables: set[str]) -> None:
    """Extract variables from <%= %> output tags.

    Args:
        content: Raw ERB template content.
        variables: Set to add found variables to (modified in place).

    """
    output_vars = re.findall(r"<%=\s*(.+?)\s*%>", content)
    for var in output_vars:
        var = var.strip()
        if var.startswith("node["):
            attr_path = _extract_node_attribute_path(var)
            if attr_path:
                variables.add(attr_path)
        elif var.startswith("@"):
            # Instance variables: @var -> var
            variables.add(var[1:])
        else:
            # Extract the base variable name
            base_var = re.match(r"(\w+)", var)
            if base_var:
                variables.add(base_var.group(1))


def _extract_node_attribute_path(node_ref: str) -> str:
    """Extract attribute path from a node reference.

    Args:
        node_ref: Node reference like "node['attr']['subattr']".

    Returns:
        Cleaned attribute path like "attr']['subattr".

    """
    # Extract the full attribute path
    attr_path = node_ref[5:]  # Remove 'node['
    # Remove the leading quote if present
    if attr_path and attr_path[0] in ("'", '"'):
        attr_path = attr_path[1:]
    # Remove the trailing ] and quote if present
    if attr_path and (attr_path.endswith("']") or attr_path.endswith('"]')):
        attr_path = attr_path[:-2]
    elif attr_path and attr_path[-1] == "]":
        attr_path = attr_path[:-1]
    return attr_path


def _extract_code_block_variables(content: str, variables: set[str]) -> None:  # noqa: C901
    """Extract variables from <% %> code blocks.

    Args:
        content: Raw ERB template content.
        variables: Set to add found variables to (modified in place).

    """
    code_blocks = re.findall(r"<%\s+(.+?)\s+%>", content, re.DOTALL)
    for code in code_blocks:
        # Handle Ruby string interpolation: "text #{var} more"
        interpolated = re.findall(r"#\{([^}]+)\}", code)
        for expr in interpolated:
            # Extract variable name from expression
            var_match = re.match(r"[\w.\[\]'\"]+", expr.strip())
            if var_match:
                variables.add(var_match.group())

        # Handle node attributes in conditionals
        if "node[" in code:
            # Find all node attribute references in this code block
            # Use greedy match to capture full nested path: node['a']['b']['c']
            node_matches = re.finditer(r"node\[.+\]", code)
            for match in node_matches:
                attr_path = _extract_node_attribute_path(match.group())
                if attr_path:
                    variables.add(attr_path)

        if code.startswith(("if ", "unless ", "elsif ")):
            # Extract variables from conditions (non-node variables)
            var_refs = re.findall(r"\b(\w+)", code)
            for var in var_refs:
                if var not in ["if", "unless", "elsif", "end", "do", "node"]:
                    variables.add(var)
        elif ".each" in code:
            # Extract array variable and iterator
            match = re.search(r"(\w+)\.each\s+do\s+\|(\w+)\|", code)
            if match:
                variables.add(match.group(1))  # Array variable
                variables.add(match.group(2))  # Iterator variable


def _extract_template_variables(content: str) -> set[str]:
    """Extract all variables used in an ERB template.

    Args:
        content: Raw ERB template content.

    Returns:
        Set of variable names found in the template.

    """
    variables: set[str] = set()

    # Extract from output tags
    _extract_output_variables(content, variables)

    # Extract from code blocks
    _extract_code_block_variables(content, variables)

    return variables


def _convert_erb_to_jinja2(content: str) -> str:
    """Convert ERB template syntax to Jinja2.

    Args:
        content: Raw ERB template content.

    Returns:
        Template content converted to Jinja2 syntax.

    """
    result = content

    # Apply each conversion pattern in order
    # Start with most specific patterns first

    # Convert node attribute access: <%= node['attr'] %> -> {{ attr }}
    result = re.sub(ERB_PATTERNS["node_attr"][0], ERB_PATTERNS["node_attr"][1], result)

    # Convert each loops
    result = re.sub(ERB_PATTERNS["each"][0], ERB_PATTERNS["each"][1], result)

    # Convert conditionals
    result = re.sub(ERB_PATTERNS["unless"][0], ERB_PATTERNS["unless"][1], result)
    result = re.sub(ERB_PATTERNS["elsif"][0], ERB_PATTERNS["elsif"][1], result)
    result = re.sub(ERB_PATTERNS["if_start"][0], ERB_PATTERNS["if_start"][1], result)
    result = re.sub(ERB_PATTERNS["else"][0], ERB_PATTERNS["else"][1], result)

    # Convert end statements - need to handle both endfor and endif
    # First pass: replace all ends with temporary markers
    result = re.sub(r"<%\s*end\s*%>", "<<<END_MARKER>>>", result)

    # Second pass: replace markers from last to first
    parts = result.split("<<<END_MARKER>>>")
    final_result = ""

    for i, part in enumerate(parts):
        final_result += part

        if i < len(parts) - 1:  # Not the last part
            # Count control structures in the accumulated result
            for_count = final_result.count("{% for ")
            endfor_count = final_result.count("{% endfor %}")

            # Find the last unclosed structure
            last_if = final_result.rfind("{% if")
            last_for = final_result.rfind("{% for")

            if (for_count - endfor_count) > 0 and last_for > last_if:
                final_result += "{% endfor %}"
            else:
                final_result += "{% endif %}"

    result = final_result

    # Convert variable output (do this last to not interfere with other patterns)
    result = re.sub(ERB_PATTERNS["output"][0], ERB_PATTERNS["output"][1], result)

    # Clean up instance variables: @var -> var
    result = re.sub(r"\{\{\s*@(\w+)\s*\}\}", r"{{ \1 }}", result)
    # Clean up @var in conditionals and other control structures
    result = re.sub(r"@(\w+)", r"\1", result)

    return result


def _extract_heredoc_strings(content: str) -> dict[str, str]:
    """Extract heredoc strings from Ruby code.

    Args:
        content: Ruby code content.

    Returns:
        Dictionary mapping heredoc markers to their content.

    """
    heredocs = {}
    # Match heredoc patterns: <<-MARKER or <<MARKER
    heredoc_pattern = r"<<-?(\w+)\s*\n(.*?)^\s*\1\s*$"
    for match in re.finditer(heredoc_pattern, content, re.DOTALL | re.MULTILINE):
        marker = match.group(1)
        content_text = match.group(2)
        heredocs[marker] = content_text
    return heredocs


def _normalize_ruby_value(value: str) -> str:
    """Normalize Ruby value representation.

    Args:
        value: Raw Ruby value string.

    Returns:
        Normalized value string.

    """
    value = value.strip()
    # Handle symbols: :symbol -> "symbol"
    if value.startswith(":") and value[1:].replace("_", "").isalnum():
        return f'"{value[1:]}"'
    # Handle arrays: [:a, :b] -> ["a", "b"]
    if value.startswith("[") and value.endswith("]"):
        # Simple symbol array conversion
        value = re.sub(r":([\w_]+)", r'"\1"', value)
    return value


def _extract_resource_properties(content: str) -> list[dict[str, Any]]:
    """Extract property definitions from custom resource.

    Args:
        content: Raw content of custom resource file.

    Returns:
        List of dictionaries containing property information.

    """
    properties = []
    # Strip comments
    clean_content = _strip_ruby_comments(content)

    # Match modern property syntax: property :name, Type, options
    # Updated to handle multi-line definitions and complex types like [true, false]
    property_pattern = (
        r"property\s+:(\w+),\s*([^,\n\[]+(?:\[[^\]]+\])?)"
        r",?\s*([^\n]*?)(?:\n|$)"
    )
    for match in re.finditer(property_pattern, clean_content, re.MULTILINE):
        prop_name = match.group(1)
        prop_type = match.group(2).strip()
        prop_options = match.group(3) if match.group(3) else ""

        prop_info: dict[str, Any] = {
            "name": prop_name,
            "type": prop_type,
        }

        # Extract name_property
        name_property_check = (
            "name_property: true" in prop_options
            or "name_attribute: true" in prop_options
        )
        if name_property_check:
            prop_info["name_property"] = True

        # Extract default value
        default_match = re.search(r"default:\s*([^,\n]+)", prop_options)
        if default_match:
            prop_info["default"] = default_match.group(1).strip()

        # Extract required
        if "required: true" in prop_options:
            prop_info["required"] = True

        properties.append(prop_info)

    # Match LWRP attribute syntax: attribute :name, kind_of: Type
    attribute_pattern = r"attribute\s+:(\w+)(?:,\s*(.+?))?\s*(?:\n|$)"
    for match in re.finditer(attribute_pattern, content, re.MULTILINE):
        attr_name = match.group(1)
        attr_options = match.group(2) if match.group(2) else ""

        attr_info: dict[str, Any] = {
            "name": attr_name,
            "type": "Any",  # Default type
        }

        # Extract type from kind_of
        kind_of_match = re.search(r"kind_of:\s*(\w+)", attr_options)
        if kind_of_match:
            attr_info["type"] = kind_of_match.group(1)

        # Extract name_attribute
        if "name_attribute: true" in attr_options:
            attr_info["name_property"] = True

        # Extract default value
        default_match = re.search(r"default:\s*([^,\n]+)", attr_options)
        if default_match:
            attr_info["default"] = default_match.group(1).strip()

        # Extract required
        if "required: true" in attr_options:
            attr_info["required"] = True

        properties.append(attr_info)

    return properties


def _extract_resource_actions(content: str) -> dict[str, Any]:
    """Extract action definitions from custom resource.

    Args:
        content: Raw content of custom resource file.

    Returns:
        Dictionary with actions list and default action.

    """
    result: dict[str, Any] = {
        "actions": [],
        "default_action": None,
    }

    # Extract modern action blocks: action :name do ... end
    action_pattern = r"action\s+:(\w+)\s+do"
    for match in re.finditer(action_pattern, content):
        action_name = match.group(1)
        if action_name not in result["actions"]:
            result["actions"].append(action_name)

    # Extract LWRP-style actions declaration: actions :create, :drop
    actions_decl = re.search(r"actions\s+(.+?)(?:\n|$)", content)
    if actions_decl:
        action_symbols = re.findall(r":(\w+)", actions_decl.group(1))
        for action in action_symbols:
            if action not in result["actions"]:
                result["actions"].append(action)

    # Extract default action
    default_match = re.search(r"default_action\s+:(\w+)", content)
    if default_match:
        result["default_action"] = default_match.group(1)

    return result


@mcp.tool()
def parse_custom_resource(path: str) -> str:
    """Parse a Chef custom resource or LWRP file.

    Args:
        path: Path to the custom resource (.rb) file.

    Returns:
        JSON string with extracted properties, actions, and metadata.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        # Determine resource type
        resource_type = "custom_resource" if "property" in content else "lwrp"

        # Extract properties/attributes
        properties = _extract_resource_properties(content)

        # Extract actions
        actions_info = _extract_resource_actions(content)

        result = {
            "resource_file": str(file_path),
            "resource_name": file_path.stem,
            "resource_type": resource_type,
            "properties": properties,
            "actions": actions_info["actions"],
            "default_action": actions_info["default_action"],
        }

        import json

        return json.dumps(result, indent=2)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


@mcp.tool()
def list_directory(path: str) -> list[str] | str:
    """List the contents of a directory.

    Args:
        path: The path to the directory to list.

    Returns:
        A list of filenames in the directory, or an error message.

    """
    try:
        dir_path = Path(path)
        return [item.name for item in dir_path.iterdir()]
    except FileNotFoundError:
        return f"Error: Directory not found at {path}"
    except NotADirectoryError:
        return f"Error: {path} is not a directory"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except Exception as e:
        return f"An error occurred: {e}"


@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file, or an error message.

    """
    try:
        file_path = Path(path)
        return file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


@mcp.tool()
def read_cookbook_metadata(path: str) -> str:
    """Parse Chef cookbook metadata.rb file.

    Args:
        path: Path to the metadata.rb file.

    Returns:
        Formatted string with extracted metadata.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        metadata = _extract_metadata(content)

        if not metadata:
            return f"Warning: No metadata found in {path}"

        return _format_metadata(metadata)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_metadata(content: str) -> dict[str, str | list[str]]:
    """Extract metadata fields from cookbook content.

    Args:
        content: Raw content of metadata.rb file.

    Returns:
        Dictionary of extracted metadata fields.

    """
    metadata: dict[str, str | list[str]] = {}
    patterns = {
        "name": r"name\s+['\"]([^'\"]+)['\"]",
        "maintainer": r"maintainer\s+['\"]([^'\"]+)['\"]",
        "version": r"version\s+['\"]([^'\"]+)['\"]",
        "description": r"description\s+['\"]([^'\"]+)['\"]",
        "license": r"license\s+['\"]([^'\"]+)['\"]",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metadata[key] = match.group(1)

    depends = re.findall(r"depends\s+['\"]([^'\"]+)['\"]", content)
    if depends:
        metadata["depends"] = depends

    supports = re.findall(r"supports\s+['\"]([^'\"]+)['\"]", content)
    if supports:
        metadata["supports"] = supports

    return metadata


def _format_metadata(metadata: dict[str, str | list[str]]) -> str:
    """Format metadata dictionary as a readable string.

    Args:
        metadata: Dictionary of metadata fields.

    Returns:
        Formatted string representation.

    """
    result = []
    for key, value in metadata.items():
        if isinstance(value, list):
            result.append(f"{key}: {', '.join(value)}")
        else:
            result.append(f"{key}: {value}")

    return "\n".join(result)


@mcp.tool()
def parse_recipe(path: str) -> str:
    """Parse a Chef recipe file and extract resources.

    Args:
        path: Path to the recipe (.rb) file.

    Returns:
        Formatted string with extracted Chef resources and their properties.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        resources = _extract_resources(content)

        if not resources:
            return f"Warning: No Chef resources found in {path}"

        return _format_resources(resources)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_resources(content: str) -> list[dict[str, str]]:
    """Extract Chef resources from recipe content.

    Args:
        content: Raw content of recipe file.

    Returns:
        List of dictionaries containing resource information.

    """
    resources = []
    # Strip comments first
    clean_content = _strip_ruby_comments(content)

    # Match Chef resource declarations with various patterns:
    # 1. Standard: package 'nginx' do ... end
    # 2. With parentheses: package('nginx') do ... end
    # 3. Multi-line strings: package 'nginx' do\n  content <<-EOH\n  ...\n  EOH\nend
    # Use a more robust pattern that handles nested blocks
    pattern = r"(\w+)\s+(?:\()?['\"]([^'\"]+)['\"](?:\))?\s+do(.*?)^end"

    for match in re.finditer(pattern, clean_content, re.DOTALL | re.MULTILINE):
        resource_type = match.group(1)
        resource_name = match.group(2)
        resource_body = match.group(3)

        resource = {
            "type": resource_type,
            "name": resource_name,
        }

        # Extract action
        action_match = re.search(r"action\s+:(\w+)", resource_body)
        if action_match:
            resource["action"] = action_match.group(1)

        # Extract common properties
        properties = {}
        for prop_match in re.finditer(r"(\w+)\s+['\"]([^'\"]+)['\"]", resource_body):
            prop_name = prop_match.group(1)
            if prop_name not in ["action"]:
                properties[prop_name] = prop_match.group(2)

        if properties:
            resource["properties"] = str(properties)

        resources.append(resource)

    return resources


def _extract_conditionals(content: str) -> list[dict[str, str]]:
    """Extract Ruby conditionals from recipe code.

    Args:
        content: Ruby code content.

    Returns:
        List of dictionaries with conditional information.

    """
    conditionals = []

    # Match case/when statements
    case_pattern = r"case\s+(.*?)\n(.*?)^end"
    for match in re.finditer(case_pattern, content, re.DOTALL | re.MULTILINE):
        case_expr = match.group(1).strip()
        case_body = match.group(2)
        when_clauses = re.findall(r"when\s+['\"]?([^'\"\n]+)['\"]?\s*\n", case_body)
        conditionals.append(
            {
                "type": "case",
                "expression": case_expr,
                "branches": when_clauses,
            }
        )

    # Match if/elsif/else statements
    if_pattern = r"if\s+(.*?)(?:\n|$)"
    for match in re.finditer(if_pattern, content):
        condition = match.group(1).strip()
        if condition and not condition.startswith(("elsif", "end")):
            conditionals.append(
                {
                    "type": "if",
                    "condition": condition,
                }
            )

    # Match unless statements
    unless_pattern = r"unless\s+(.*?)(?:\n|$)"
    for match in re.finditer(unless_pattern, content):
        condition = match.group(1).strip()
        conditionals.append(
            {
                "type": "unless",
                "condition": condition,
            }
        )

    return conditionals


def _format_resources(resources: list[dict[str, str]]) -> str:
    """Format resources list as a readable string.

    Args:
        resources: List of resource dictionaries.

    Returns:
        Formatted string representation.

    """
    result = []
    for i, resource in enumerate(resources, 1):
        result.append(f"Resource {i}:")
        result.append(f"  Type: {resource['type']}")
        result.append(f"  Name: {resource['name']}")
        if "action" in resource:
            result.append(f"  Action: {resource['action']}")
        if "properties" in resource:
            result.append(f"  Properties: {resource['properties']}")
        result.append("")

    return "\n".join(result).rstrip()


@mcp.tool()
def parse_attributes(path: str) -> str:
    """Parse a Chef attributes file and extract attribute definitions.

    Args:
        path: Path to the attributes (.rb) file.

    Returns:
        Formatted string with extracted attributes.

    """
    try:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")

        attributes = _extract_attributes(content)

        if not attributes:
            return f"Warning: No attributes found in {path}"

        return _format_attributes(attributes)

    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory, not a file"
    except PermissionError:
        return f"Error: Permission denied for {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _extract_attributes(content: str) -> list[dict[str, str]]:
    """Extract Chef attributes from attributes file content.

    Args:
        content: Raw content of attributes file.

    Returns:
        List of dictionaries containing attribute information.

    """
    attributes = []
    # Strip comments first
    clean_content = _strip_ruby_comments(content)

    # Match attribute declarations like: default['nginx']['port'] = 80
    # Use non-capturing group (?:...) with + to match one or more brackets
    # Updated to handle multi-line values and heredocs
    pattern = (
        r"(default|override|normal)((?:\[[^\]]+\])+)\s*=\s*"
        r"(.+?)(?=\n(?:default|override|normal|case|when|end|$)|$)"
    )

    for match in re.finditer(pattern, clean_content, re.DOTALL):
        precedence = match.group(1)
        # Extract the bracket part and clean it up
        brackets = match.group(2)
        # Clean up the path - remove quotes and brackets, convert to dot notation
        attr_path = (
            brackets.replace("']['", ".")
            .replace('"]["', ".")
            .replace("['", "")
            .replace("']", "")
            .replace('["', "")
            .replace('"]', "")
        )
        value = match.group(3).strip()

        attributes.append(
            {
                "precedence": precedence,
                "path": attr_path,
                "value": value,
            }
        )

    return attributes


def _format_attributes(attributes: list[dict[str, str]]) -> str:
    """Format attributes list as a readable string.

    Args:
        attributes: List of attribute dictionaries.

    Returns:
        Formatted string representation.

    """
    result = []
    for attr in attributes:
        result.append(f"{attr['precedence']}[{attr['path']}] = {attr['value']}")

    return "\n".join(result)


@mcp.tool()
def list_cookbook_structure(path: str) -> str:
    """List the structure of a Chef cookbook directory.

    Args:
        path: Path to the cookbook root directory.

    Returns:
        Formatted string showing the cookbook structure.

    """
    try:
        cookbook_path = Path(path)

        if not cookbook_path.is_dir():
            return f"Error: {path} is not a directory"

        structure = {}
        common_dirs = [
            "recipes",
            "attributes",
            "templates",
            "files",
            "resources",
            "providers",
            "libraries",
            "definitions",
        ]

        for dir_name in common_dirs:
            dir_path = cookbook_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                files = [f.name for f in dir_path.iterdir() if f.is_file()]
                if files:
                    structure[dir_name] = files

        # Check for metadata.rb
        metadata_path = cookbook_path / "metadata.rb"
        if metadata_path.exists():
            structure["metadata"] = ["metadata.rb"]

        if not structure:
            return f"Warning: No standard cookbook structure found in {path}"

        return _format_cookbook_structure(structure)

    except PermissionError:
        return f"Error: Permission denied for {path}"
    except Exception as e:
        return f"An error occurred: {e}"


def _format_cookbook_structure(structure: dict[str, list[str]]) -> str:
    """Format cookbook structure as a readable string.

    Args:
        structure: Dictionary mapping directory names to file lists.

    Returns:
        Formatted string representation.

    """
    result = []
    for dir_name, files in structure.items():
        result.append(f"{dir_name}/")
        for file_name in sorted(files):
            result.append(f"  {file_name}")
        result.append("")

    return "\n".join(result).rstrip()


@mcp.tool()
def convert_resource_to_task(
    resource_type: str, resource_name: str, action: str = "create", properties: str = ""
) -> str:
    """Convert a Chef resource to an Ansible task.

    Args:
        resource_type: The Chef resource type (e.g., 'package', 'service').
        resource_name: The name of the resource.
        action: The Chef action (e.g., 'install', 'start', 'create').
            Defaults to 'create'.
        properties: Additional resource properties as a string representation.

    Returns:
        YAML representation of the equivalent Ansible task.

    """
    try:
        task = _convert_chef_resource_to_ansible(
            resource_type, resource_name, action, properties
        )
        return _format_ansible_task(task)
    except Exception as e:
        return f"An error occurred during conversion: {e}"


def _get_service_params(resource_name: str, action: str) -> dict[str, Any]:
    """Get Ansible service module parameters.

    Args:
        resource_name: Service name.
        action: Chef action.

    Returns:
        Dictionary of Ansible service parameters.

    """
    params: dict[str, Any] = {"name": resource_name}
    if action in ["enable", "start"]:
        params["enabled"] = True
        params["state"] = "started"
    elif action in ["disable", "stop"]:
        params["enabled"] = False
        params["state"] = "stopped"
    else:
        params["state"] = ACTION_TO_STATE.get(action, action)
    return params


def _get_file_params(
    resource_name: str, action: str, resource_type: str
) -> dict[str, Any]:
    """Get Ansible file module parameters.

    Args:
        resource_name: File/directory path.
        action: Chef action.
        resource_type: Type of file resource (file/directory/template).

    Returns:
        Dictionary of Ansible file parameters.

    """
    params: dict[str, Any] = {}

    if resource_type == "template":
        params["src"] = resource_name
        params["dest"] = resource_name.replace(".erb", "")
        if action == "create":
            params["mode"] = "0644"
    elif resource_type == "file":
        params["path"] = resource_name
        if action == "create":
            params["state"] = "file"
            params["mode"] = "0644"
        else:
            params["state"] = ACTION_TO_STATE.get(action, action)
    elif resource_type == "directory":
        params["path"] = resource_name
        params["state"] = "directory"
        if action == "create":
            params["mode"] = "0755"

    return params


def _convert_chef_resource_to_ansible(
    resource_type: str, resource_name: str, action: str, properties: str
) -> dict[str, Any]:
    """Convert Chef resource to Ansible task dictionary.

    Args:
        resource_type: The Chef resource type.
        resource_name: The name of the resource.
        action: The Chef action.
        properties: Additional properties string.

    Returns:
        Dictionary representing an Ansible task.

    """
    # Get Ansible module name
    ansible_module = RESOURCE_MAPPINGS.get(resource_type, f"# Unknown: {resource_type}")

    # Start building the task
    task: dict[str, Any] = {
        "name": f"{action.capitalize()} {resource_type} {resource_name}",
    }

    # Build module parameters based on resource type
    module_params: dict[str, Any] = {}

    if resource_type == "package":
        module_params["name"] = resource_name
        module_params["state"] = ACTION_TO_STATE.get(action, action)
    elif resource_type in ["service", "systemd_unit"]:
        module_params = _get_service_params(resource_name, action)
    elif resource_type in ["template", "file", "directory"]:
        module_params = _get_file_params(resource_name, action, resource_type)
    elif resource_type in ["execute", "bash"]:
        module_params["cmd"] = resource_name
        task["changed_when"] = "false"
    elif resource_type in ["user", "group"]:
        module_params["name"] = resource_name
        module_params["state"] = ACTION_TO_STATE.get(action, "present")
    else:
        module_params["name"] = resource_name
        if action in ACTION_TO_STATE:
            module_params["state"] = ACTION_TO_STATE[action]

    task[ansible_module] = module_params
    return task


def _format_ansible_task(task: dict[str, Any]) -> str:
    """Format an Ansible task dictionary as YAML.

    Args:
        task: Dictionary representing an Ansible task.

    Returns:
        YAML-formatted string.

    """
    import json

    # Simple YAML formatting (basic implementation)
    result = []
    result.append("- name: " + task["name"])

    for key, value in task.items():
        if key == "name":
            continue

        if isinstance(value, dict):
            result.append(f"  {key}:")
            for param_key, param_value in value.items():
                if isinstance(param_value, str):
                    result.append(f'    {param_key}: "{param_value}"')
                else:
                    result.append(f"    {param_key}: {json.dumps(param_value)}")
        else:
            if isinstance(value, str):
                result.append(f'  {key}: "{value}"')
            else:
                result.append(f"  {key}: {json.dumps(value)}")

    return "\n".join(result)


def main() -> None:
    """Run the SousChef MCP server.

    This is the main entry point for running the server.
    """
    mcp.run()


if __name__ == "__main__":
    main()
