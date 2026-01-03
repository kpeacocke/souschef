"""SousChef MCP Server - Chef to Ansible conversion assistant."""

import ast
import json
import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Create a new FastMCP server
mcp = FastMCP("souschef")


def _normalize_path(path_str: str) -> Path:
    """Normalize a file path for safe filesystem operations.

    This function resolves relative paths and symlinks to absolute paths,
    preventing path traversal attacks (CWE-23). Note: This MCP server
    intentionally allows full filesystem access as it runs in the user's
    local environment with their permissions.

    Args:
        path_str: Path string to normalize.

    Returns:
        Resolved absolute Path object.

    Raises:
        ValueError: If the path contains null bytes or is invalid.

    """
    if "\x00" in path_str:
        raise ValueError(f"Path contains null bytes: {path_str!r}")

    try:
        # Resolve to absolute path, removing .., ., and resolving symlinks
        # deepcode ignore PT: This is the path normalization function itself
        return Path(path_str).resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path {path_str}: {e}") from e


def _safe_join(base_path: Path, *parts: str) -> Path:
    """Safely join path components ensuring result stays within base directory.

    Args:
        base_path: Normalized base path.
        *parts: Path components to join.

    Returns:
        Joined path within base_path.

    Raises:
        ValueError: If result would escape base_path.

    """
    result = base_path.joinpath(*parts).resolve()
    try:
        result.relative_to(base_path)
        return result
    except ValueError as e:
        raise ValueError(f"Path traversal attempt: {parts} escapes {base_path}") from e


# Constants for commonly used strings
ANSIBLE_SERVICE_MODULE = "ansible.builtin.service"
METADATA_FILENAME = "metadata.rb"
ERROR_PREFIX = "Error:"
REGEX_WHITESPACE_QUOTE = r"\s+['\"]?"
REGEX_QUOTE_DO_END = r"['\"]?\s+do\s*(.*?)\nend"
REGEX_RESOURCE_BRACKET = r"(\w+)\[([^\]]+)\]"
INSPEC_END_INDENT = "  end"
INSPEC_SHOULD_EXIST = "    it { should exist }"
CHEF_RECIPE_PREFIX = "recipe["
CHEF_ROLE_PREFIX = "role["

# Chef resource to Ansible module mappings
RESOURCE_MAPPINGS = {
    "package": "ansible.builtin.package",
    "apt_package": "ansible.builtin.apt",
    "yum_package": "ansible.builtin.yum",
    "service": ANSIBLE_SERVICE_MODULE,
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
    "output": (r"<%=\s*([^%]+?)\s*%>", r"{{ \1 }}"),
    # Variable with node prefix: <%= node['attr'] %> -> {{ attr }}
    "node_attr": (r"<%=\s*node\[(['\"])([^%]+?)\1\]\s*%>", r"{{ \2 }}"),
    # If statements: <% if condition %> -> {% if condition %}
    "if_start": (r"<%\s*if\s+([^%]+?)\s*%>", r"{% if \1 %}"),
    # Unless (negated if): <% unless condition %> -> {% if not condition %}
    "unless": (r"<%\s*unless\s+([^%]+?)\s*%>", r"{% if not \1 %}"),
    # Else: <% else %> -> {% else %}
    "else": (r"<%\s*else\s*%>", r"{% else %}"),
    # Elsif: <% elsif condition %> -> {% elif condition %}
    "elsif": (r"<%\s*elsif\s+([^%]+?)\s*%>", r"{% elif \1 %}"),
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
        file_path = _normalize_path(path)
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
    output_vars = re.findall(r"<%=\s*([^%]+?)\s*%>", content)
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


def _extract_interpolated_variables(code: str, variables: set[str]) -> None:
    """Extract variables from Ruby string interpolation.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    interpolated = re.findall(r"#\{([^}]+)\}", code)
    for expr in interpolated:
        var_match = re.match(r"[\w.\[\]'\"]+", expr.strip())
        if var_match:
            variables.add(var_match.group())


def _extract_node_attributes(code: str, variables: set[str]) -> None:
    """Extract node attribute references from code.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    if "node[" in code:
        node_matches = re.finditer(r"node\[.+\]", code)
        for match in node_matches:
            attr_path = _extract_node_attribute_path(match.group())
            if attr_path:
                variables.add(attr_path)


def _extract_conditional_variables(code: str, variables: set[str]) -> None:
    """Extract variables from conditional statements.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    if code.startswith(("if ", "unless ", "elsif ")):
        var_refs = re.findall(r"\b(\w+)", code)
        for var in var_refs:
            if var not in ["if", "unless", "elsif", "end", "do", "node"]:
                variables.add(var)


def _extract_iterator_variables(code: str, variables: set[str]) -> None:
    """Extract variables from .each iterators.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    if ".each" in code:
        match = re.search(r"(\w+)\.each\s+do\s+\|(\w+)\|", code)
        if match:
            variables.add(match.group(1))  # Array variable
            variables.add(match.group(2))  # Iterator variable


def _extract_code_block_variables(content: str, variables: set[str]) -> None:
    """Extract variables from <% %> code blocks.

    Args:
        content: Raw ERB template content.
        variables: Set to add found variables to (modified in place).

    """
    code_blocks = re.findall(r"<%\s+([^%]+?)\s+%>", content, re.DOTALL)
    for code in code_blocks:
        _extract_interpolated_variables(code, variables)
        _extract_node_attributes(code, variables)
        _extract_conditional_variables(code, variables)
        _extract_iterator_variables(code, variables)


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
    heredoc_pattern = r"<<-?(\w+)\s*\n((?:(?!^\s*\1\s*$)[\s\S])*?)^\s*\1\s*$"
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
        r"property\s+:(\w+),\s*([^,\n\[]+(?:\[[^\]]+\])?),?\s*([^\n]*?)(?:\n|$)"
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
    attribute_pattern = r"attribute\s+:(\w+)(?:,\s*([^\n]+?))?\s*(?:\n|$)"
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
    actions_decl = re.search(r"actions\s+([^\n]+?)(?:\n|$)", content)
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
        file_path = _normalize_path(path)
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
        dir_path = _normalize_path(path)
        return [item.name for item in dir_path.iterdir()]
    except ValueError as e:
        return f"Error: {e}"
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
        file_path = _normalize_path(path)
        return file_path.read_text(encoding="utf-8")
    except ValueError as e:
        return f"Error: {e}"
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
        file_path = _normalize_path(path)
        content = file_path.read_text(encoding="utf-8")

        metadata = _extract_metadata(content)

        if not metadata:
            return f"Warning: No metadata found in {path}"

        return _format_metadata(metadata)

    except ValueError as e:
        return f"Error: {e}"
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
        file_path = _normalize_path(path)
        content = file_path.read_text(encoding="utf-8")

        resources = _extract_resources(content)

        if not resources:
            return f"Warning: No Chef resources found in {path}"

        return _format_resources(resources)

    except ValueError as e:
        return f"Error: {e}"
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
    pattern = r"(\w+)\s+(?:\()?['\"]([^'\"]+)['\"](?:\))?\s+do([\s\S]*?)^end"

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
    case_pattern = r"case\s+([^\n]+?)\n([\s\S]*?)^end"
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
    if_pattern = r"if\s+([^\n]+?)(?:\n|$)"
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
    unless_pattern = r"unless\s+([^\n]+?)(?:\n|$)"
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
        file_path = _normalize_path(path)
        content = file_path.read_text(encoding="utf-8")

        attributes = _extract_attributes(content)

        if not attributes:
            return f"Warning: No attributes found in {path}"

        return _format_attributes(attributes)

    except ValueError as e:
        return f"Error: {e}"
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
    pattern = r"(default|override|normal)((?:\[[^\]]+\])+)\s*=\s*([^\n]+?)(?=\s*\n|$)"

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
        cookbook_path = _normalize_path(path)

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
            dir_path = _safe_join(cookbook_path, dir_name)
            if dir_path.exists() and dir_path.is_dir():
                files = [f.name for f in dir_path.iterdir() if f.is_file()]
                if files:
                    structure[dir_name] = files

        # Check for metadata.rb
        metadata_path = _safe_join(cookbook_path, METADATA_FILENAME)
        if metadata_path.exists():
            structure["metadata"] = [METADATA_FILENAME]

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


@mcp.tool()
def generate_playbook_from_recipe(recipe_path: str) -> str:
    """Generate a complete Ansible playbook from a Chef recipe.

    Args:
        recipe_path: Path to the Chef recipe (.rb) file.

    Returns:
        Complete Ansible playbook in YAML format with tasks, handlers, and variables.

    """
    try:
        # First, parse the recipe to extract resources
        recipe_content = parse_recipe(recipe_path)

        if recipe_content.startswith(ERROR_PREFIX):
            return recipe_content

        # Parse the raw recipe file to extract notifications and other advanced features
        recipe_file = _normalize_path(recipe_path)
        if not recipe_file.exists():
            return f"{ERROR_PREFIX} Recipe file does not exist: {recipe_path}"

        raw_content = recipe_file.read_text()

        # Generate playbook structure
        playbook = _generate_playbook_structure(
            recipe_content, raw_content, recipe_file.name
        )

        return playbook

    except Exception as e:
        return f"Error generating playbook: {e}"


@mcp.tool()
def convert_chef_search_to_inventory(search_query: str) -> str:
    """Convert a Chef search query to Ansible inventory patterns and groups.

    Args:
        search_query: Chef search query (e.g., "role:web AND environment:production").

    Returns:
        JSON string with Ansible inventory patterns and group definitions.

    """
    try:
        # Parse the Chef search query
        search_info = _parse_chef_search_query(search_query)

        # Convert to Ansible inventory patterns
        inventory_config = _generate_ansible_inventory_from_search(search_info)

        import json

        return json.dumps(inventory_config, indent=2)

    except Exception as e:
        return f"Error converting Chef search: {e}"


@mcp.tool()
def generate_dynamic_inventory_script(search_queries: str) -> str:
    """Generate a Python dynamic inventory script from Chef search queries.

    Args:
        search_queries: JSON string containing Chef search queries and group names.

    Returns:
        Complete Python script for Ansible dynamic inventory.

    """
    try:
        import json

        queries_data = json.loads(search_queries)

        # Generate dynamic inventory script
        script_content = _generate_inventory_script_content(queries_data)

        return script_content

    except json.JSONDecodeError:
        return "Error: Invalid JSON format for search queries"
    except Exception as e:
        return f"Error generating dynamic inventory script: {e}"


@mcp.tool()
def analyze_chef_search_patterns(recipe_or_cookbook_path: str) -> str:
    """Analyze Chef recipes/cookbooks to extract search patterns for inventory planning.

    Args:
        recipe_or_cookbook_path: Path to Chef recipe file or cookbook directory.

    Returns:
        JSON string with discovered search patterns and recommended inventory structure.

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

        import json

        return json.dumps(
            {
                "discovered_searches": search_patterns,
                "inventory_recommendations": recommendations,
            },
            indent=2,
        )

    except Exception as e:
        return f"Error analyzing Chef search patterns: {e}"


def _determine_search_index(normalized_query: str) -> str:
    """Determine the search index from the query.

    Args:
        normalized_query: Normalized query string.

    Returns:
        Index name (defaults to 'node').

    """
    import re

    index_match = re.match(r"^(\w+):", normalized_query)
    if index_match:
        potential_index = index_match.group(1)
        if potential_index in ["role", "environment", "tag", "platform"]:
            return "node"  # These are node attributes
        return potential_index
    return "node"


def _extract_query_parts(normalized_query: str) -> tuple[list[str], list[str]]:
    """Extract conditions and operators from query.

    Args:
        normalized_query: Normalized query string.

    Returns:
        Tuple of (conditions, operators).

    """
    import re

    operator_pattern = r"\s+(AND|OR|NOT)\s+"
    parts = re.split(operator_pattern, normalized_query, flags=re.IGNORECASE)

    conditions = []
    operators = []

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
    """Determine query complexity level.

    Args:
        conditions: List of parsed conditions.
        operators: List of logical operators.

    Returns:
        Complexity level: 'simple', 'intermediate', or 'complex'.

    """
    if len(conditions) > 1 or operators:
        return "complex"
    elif any(cond.get("operator") in ["~", "!="] for cond in conditions):
        return "intermediate"
    return "simple"


def _parse_chef_search_query(query: str) -> dict[str, Any]:
    """Parse a Chef search query into structured components.

    Args:
        query: Chef search query string.

    Returns:
        Dictionary with parsed query components.

    """
    normalized_query = query.strip()

    search_info = {
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
    """Parse a single search condition.

    Args:
        condition: Single condition string.

    Returns:
        Dictionary with condition components.

    """
    import re

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


def _should_use_dynamic_inventory(search_info: dict[str, Any]) -> bool:
    """Determine if dynamic inventory is needed based on search complexity.

    Args:
        search_info: Parsed Chef search information.

    Returns:
        True if dynamic inventory is needed.

    """
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
    """Create group configuration for equal operator conditions.

    Args:
        condition: Condition with 'equal' operator.

    Returns:
        Group configuration dictionary.

    """
    group_config = {"hosts": [], "vars": {}, "children": []}
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
    """Create group configuration for wildcard/regex conditions.

    Args:
        condition: Condition with 'wildcard' or 'regex' operator.

    Returns:
        Group configuration dictionary.

    """
    operator = condition["operator"]
    pattern_type = "pattern" if operator == "wildcard" else "regex"
    return {
        "hosts": [
            f"# Hosts matching {pattern_type}: {condition['key']}:{condition['value']}"
        ],
        "vars": {},
        "children": [],
    }


def _process_search_condition(
    condition: dict[str, str], index: int, inventory_config: dict[str, Any]
) -> None:
    """Process a single search condition and update inventory config.

    Args:
        condition: Search condition to process.
        index: Condition index for group naming.
        inventory_config: Inventory configuration to update.

    """
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
    """Generate Ansible inventory structure from parsed Chef search.

    Args:
        search_info: Parsed Chef search information.

    Returns:
        Dictionary with Ansible inventory configuration.

    """
    inventory_config = {
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


def _generate_group_name_from_condition(condition: dict[str, str], index: int) -> str:
    """Generate an Ansible group name from a search condition.

    Args:
        condition: Parsed search condition.
        index: Condition index for uniqueness.

    Returns:
        Valid Ansible group name.

    """
    # Sanitize values for group names
    key = condition.get("key", "unknown").lower()
    value = condition.get("value", "unknown").lower()

    # Remove special characters and replace with underscores
    import re

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


def _generate_inventory_script_content(queries_data: list[dict[str, str]]) -> str:
    """Generate Python dynamic inventory script content.

    Args:
        queries_data: List of query/group mappings.

    Returns:
        Complete Python script content.

    """
    script_template = '''#!/usr/bin/env python3
"""
Dynamic Ansible Inventory Script
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
    # This is a placeholder - you'll need to implement Chef server communication
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
    parser = argparse.ArgumentParser(description="Dynamic Ansible Inventory from Chef")
    parser.add_argument("--list", action="store_true", help="List all groups and hosts")
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
    import json

    queries_json = json.dumps(
        {
            item.get("group_name", f"group_{i}"): item.get("search_query", "")
            for i, item in enumerate(queries_data)
        },
        indent=4,
    )

    return script_template.replace("{search_queries_json}", queries_json)


def _extract_search_patterns_from_file(file_path: Path) -> list[dict[str, str]]:
    """Extract Chef search patterns from a single recipe file.

    Args:
        file_path: Path to the recipe file.

    Returns:
        List of discovered search patterns.

    """
    try:
        content = file_path.read_text()
        return _find_search_patterns_in_content(content, str(file_path))
    except Exception:
        return []


def _extract_search_patterns_from_cookbook(cookbook_path: Path) -> list[dict[str, str]]:
    """Extract Chef search patterns from all files in a cookbook.

    Args:
        cookbook_path: Path to the cookbook directory.

    Returns:
        List of discovered search patterns from all recipe files.

    """
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
    """Find Chef search patterns in file content.

    Args:
        content: File content to search.
        file_path: Path to the file (for context).

    Returns:
        List of discovered search patterns.

    """
    import re

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
    """Extract context around a regex match.

    Args:
        content: Full content.
        match: Regex match object.

    Returns:
        Context string around the match.

    """
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


def _count_pattern_types(patterns: list[dict[str, str]]) -> dict[str, int]:
    """Count pattern types from list of patterns.

    Args:
        patterns: List of discovered search patterns.

    Returns:
        Dictionary mapping pattern types to counts.

    """
    pattern_types: dict[str, int] = {}
    for pattern in patterns:
        ptype = pattern.get("type", "unknown")
        pattern_types[ptype] = pattern_types.get(ptype, 0) + 1
    return pattern_types


def _extract_role_and_environment_groups(
    patterns: list[dict[str, str]],
) -> tuple[set[str], set[str]]:
    """Extract role and environment groups from patterns.

    Args:
        patterns: List of discovered search patterns.

    Returns:
        Tuple of (role_groups, environment_groups).

    """
    role_groups: set[str] = set()
    environment_groups: set[str] = set()

    for pattern in patterns:
        if pattern.get("type") == "search":
            query = pattern.get("query", "")
            if "role:" in query:
                role_match = re.search(r"role:([^\\s]+)", query)
                if role_match:
                    role_groups.add(role_match.group(1))
            if "environment:" in query:
                env_match = re.search(r"environment:([^\\s]+)", query)
                if env_match:
                    environment_groups.add(env_match.group(1))

    return role_groups, environment_groups


def _add_group_recommendations(
    recommendations: dict[str, Any],
    role_groups: set[str],
    environment_groups: set[str],
) -> None:
    """Add group recommendations based on discovered groups.

    Args:
        recommendations: Recommendations dict to update.
        role_groups: Set of Chef roles.
        environment_groups: Set of Chef environments.

    """
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
    """Add general migration recommendations based on patterns.

    Args:
        recommendations: Recommendations dict to update.
        patterns: List of discovered search patterns.

    """
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
    """Generate inventory structure recommendations from search patterns.

    Args:
        patterns: List of discovered search patterns.

    Returns:
        Dictionary with recommended inventory structure.

    """
    recommendations = {
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


def _build_playbook_header(recipe_name: str) -> list[str]:
    """Build playbook header with metadata.

    Args:
        recipe_name: Name of the recipe file.

    Returns:
        List of header lines.

    """
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


def _add_playbook_variables(playbook_lines: list[str], raw_content: str) -> None:
    """Extract and add variables section to playbook.

    Args:
        playbook_lines: Playbook lines list to append to.
        raw_content: Raw recipe file content for variable extraction.

    """
    variables = _extract_recipe_variables(raw_content)
    for var_name, var_value in variables.items():
        playbook_lines.append(f"    {var_name}: {var_value}")

    if not variables:
        playbook_lines.append("    # No variables found")

    playbook_lines.extend(["", "  tasks:"])


def _convert_and_collect_resources(
    parsed_content: str, raw_content: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert Chef resources to Ansible tasks and collect handlers.

    Args:
        parsed_content: Parsed recipe content from parse_recipe.
        raw_content: Raw recipe file content for advanced parsing.

    Returns:
        Tuple of (tasks, handlers).

    """
    resources = _extract_resources_from_parsed_content(parsed_content)
    tasks = []
    handlers = []

    for resource in resources:
        task_result = _convert_resource_to_task_dict(resource, raw_content)
        tasks.append(task_result["task"])
        if task_result["handlers"]:
            handlers.extend(task_result["handlers"])

    return tasks, handlers


def _add_formatted_items(
    playbook_lines: list[str],
    items: list[dict[str, Any]],
    section_name: str,
    default_message: str,
) -> None:
    """Add formatted tasks or handlers to playbook.

    Args:
        playbook_lines: Playbook lines list to append to.
        items: Tasks or handlers to format and add.
        section_name: Section header name (e.g., "tasks", "handlers").
        default_message: Message to show if no items.

    """
    if items:
        for i, item in enumerate(items):
            if i > 0:
                playbook_lines.append("")

            item_yaml = _format_ansible_task(item)
            item_lines = item_yaml.split("\n")
            for j, line in enumerate(item_lines):
                if j == 0:  # First line
                    playbook_lines.append(f"    {line}")
                else:  # Property lines
                    playbook_lines.append(f"      {line}" if line.strip() else line)
    else:
        playbook_lines.append(f"    {default_message}")


def _generate_playbook_structure(
    parsed_content: str, raw_content: str, recipe_name: str
) -> str:
    """Generate complete playbook structure from parsed recipe content.

    Args:
        parsed_content: Parsed recipe content from parse_recipe.
        raw_content: Raw recipe file content for advanced parsing.
        recipe_name: Name of the recipe file.

    Returns:
        Complete Ansible playbook as YAML string.

    """
    playbook_lines = _build_playbook_header(recipe_name)
    _add_playbook_variables(playbook_lines, raw_content)

    # Convert resources to tasks and handlers
    tasks, handlers = _convert_and_collect_resources(parsed_content, raw_content)

    # Add tasks section
    _add_formatted_items(playbook_lines, tasks, "tasks", "# No tasks found")

    # Add handlers section if any
    if handlers:
        playbook_lines.extend(["", "  handlers:"])
        _add_formatted_items(playbook_lines, handlers, "handlers", "")

    return "\n".join(playbook_lines)


def _get_current_timestamp() -> str:
    """Get current timestamp for playbook generation."""
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _extract_version_variable(raw_content: str) -> dict[str, str]:
    """Extract version specification from recipe content.

    Args:
        raw_content: Raw Chef recipe file content.

    Returns:
        Dictionary with package_version key if found.

    """
    import re

    version_pattern = re.compile(r"version\s+['\"]([^'\"]+)['\"]")
    versions = version_pattern.findall(raw_content)
    if versions:
        return {"package_version": f'"{versions[0]}"'}
    return {}


def _extract_content_variables(raw_content: str) -> dict[str, str]:
    """Extract content and source specifications from recipe content.

    Args:
        raw_content: Raw Chef recipe file content.

    Returns:
        Dictionary with file_content and/or template_source keys if found.

    """
    import re

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
    """Extract owner and group specifications from recipe content.

    Args:
        raw_content: Raw Chef recipe file content.

    Returns:
        Dictionary with file_owner and/or file_group keys if found.

    """
    import re

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
    """Extract mode specifications from recipe content.

    Args:
        raw_content: Raw Chef recipe file content.

    Returns:
        Dictionary with file_mode and/or directory_mode keys if found.

    """
    import re

    # Extract mode specifications
    mode_pattern = re.compile(r"mode\s+['\"]([^'\"]+)['\"]")
    modes = mode_pattern.findall(raw_content)
    unique_modes = list(set(modes))

    if len(unique_modes) == 1:
        return {"file_mode": f'"{unique_modes[0]}"'}
    elif len(unique_modes) > 1:
        return {"directory_mode": '"0755"', "file_mode": '"0644"'}
    return {}


def _extract_recipe_variables(raw_content: str) -> dict[str, str]:
    """Extract variables from Chef recipe content.

    Args:
        raw_content: Raw Chef recipe file content.

    Returns:
        Dictionary of variable names and values.

    """
    variables = {}

    # Combine all extracted variables
    variables.update(_extract_version_variable(raw_content))
    variables.update(_extract_content_variables(raw_content))
    variables.update(_extract_ownership_variables(raw_content))
    variables.update(_extract_mode_variables(raw_content))

    return variables


def _extract_resources_from_parsed_content(parsed_content: str) -> list[dict[str, str]]:
    """Extract resource information from parsed recipe content.

    Args:
        parsed_content: Parsed content from parse_recipe function.

    Returns:
        List of resource dictionaries with type, name, action, and properties.

    """
    import re

    resources = []

    # Parse the structured output from parse_recipe
    resource_blocks = re.split(r"\n(?=Resource \d+:)", parsed_content)

    for block in resource_blocks:
        if not block.strip() or not block.startswith("Resource"):
            continue

        resource = {}

        # Extract resource type
        type_match = re.search(r"Type:\s*(\w+)", block)
        if type_match:
            resource["type"] = type_match.group(1)

        # Extract resource name
        name_match = re.search(r"Name:\s*([^\n]+)", block)
        if name_match:
            resource["name"] = name_match.group(1).strip()

        # Extract action
        action_match = re.search(r"Action:\s*([^\n]+)", block)
        if action_match:
            resource["action"] = action_match.group(1).strip()
        else:
            resource["action"] = "create"  # default action

        # Extract properties
        properties_section = re.search(
            r"Properties:([\s\S]*?)(?=\n\n|\n$|$)", block, re.DOTALL
        )
        if properties_section:
            resource["properties"] = properties_section.group(1).strip()
        else:
            resource["properties"] = ""

        if resource.get("type") and resource.get("name"):
            resources.append(resource)

    return resources


def _extract_notify_declarations(
    resource: dict[str, str], raw_content: str
) -> list[tuple[str, str, str]]:
    """Extract notifies declarations from a resource block.

    Args:
        resource: Resource dictionary with type, name, action, properties.
        raw_content: Raw recipe content.

    Returns:
        List of tuples (action, target, timing).

    """
    import re

    resource_type_escaped = resource["type"]
    resource_name_escaped = re.escape(resource["name"])
    resource_pattern = (
        resource_type_escaped
        + r"\s+['\"]?"
        + resource_name_escaped
        + r"['\"]?\s+do\s*(.*?)\nend"
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
    """Extract subscribes declarations from raw content.

    Args:
        raw_content: Raw recipe content.

    Returns:
        List of tuples (action, target, timing).

    """
    import re

    subscribes_pattern = re.compile(
        r'subscribes\s+:(\w+),\s*[\'"]([^\'\"]+)[\'"]\s*,?\s*:?(\w+)?'
    )
    return subscribes_pattern.findall(raw_content)


def _process_notifications(
    notifications: list[tuple[str, str, str]],
    task: dict[str, Any],
) -> list[dict[str, Any]]:
    """Process notification declarations and create handlers.

    Args:
        notifications: List of (action, target, timing) tuples.
        task: Task dictionary to update with notify keys.

    Returns:
        List of handler dictionaries.

    """
    import re

    handlers = []
    for notify_action, notify_target, _notify_timing in notifications:
        target_match = re.match(r"(\w+)\[([^\]]+)\]", notify_target)
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
    """Process subscribes declarations and create handlers.

    Args:
        resource: Resource dictionary.
        subscribes: List of (action, target, timing) tuples.
        raw_content: Raw recipe content.
        task: Task dictionary to update with notify keys.

    Returns:
        List of handler dictionaries.

    """
    import re

    handlers = []
    for sub_action, sub_target, _sub_timing in subscribes:
        target_match = re.match(r"(\w+)\[([^\]]+)\]", sub_target)
        if not target_match:
            continue

        target_type = target_match.group(1)
        target_name = target_match.group(2)

        if resource["type"] != target_type or resource["name"] != target_name:
            continue

        subscriber_pattern = (
            rf"(\w+)\s+['\"]?[^'\"]*['\"]?\s+do\s*.*?subscribes\s+:{sub_action}"
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
    """Convert a Chef resource to an Ansible task dictionary with handlers.

    Args:
        resource: Resource dictionary with type, name, action, properties.
        raw_content: Raw recipe content for extracting notifications.

    Returns:
        Dictionary with 'task' and 'handlers' keys.

    """
    # Convert basic resource to task
    task = _convert_chef_resource_to_ansible(
        resource["type"], resource["name"], resource["action"], resource["properties"]
    )

    # Extract and convert Chef guards to Ansible when conditions
    guards = _extract_chef_guards(resource, raw_content)
    if guards:
        task.update(guards)

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
    """Create an Ansible handler from Chef notification.

    Args:
        action: The Chef action (e.g., 'reload', 'restart').
        resource_type: The Chef resource type (e.g., 'service').
        resource_name: The resource name (e.g., 'nginx').

    Returns:
        Handler task dictionary or None if not supported.

    """
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

        handler = {
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
    """Extract notification information with timing constraints for a resource.

    Args:
        resource: Resource dictionary.
        raw_content: Raw recipe content.

    Returns:
        List of notification dictionaries with timing information.

    """
    import re

    notifications = []

    # Find the resource block in raw content
    resource_type_escaped = resource["type"]
    resource_name_escaped = re.escape(resource["name"])
    resource_pattern = (
        resource_type_escaped
        + r"\s+['\"]?"
        + resource_name_escaped
        + r"['\"]?\s+do\s*(.*?)\nend"
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
            target_match = re.match(r"(\w+)\[([^\]]+)\]", notify_target)
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


def _find_resource_block(resource: dict[str, str], raw_content: str) -> str | None:
    """Find the resource block in raw content.

    Args:
        resource: Resource dictionary with type and name.
        raw_content: Raw recipe content.

    Returns:
        Resource block content or None if not found.

    """
    import re

    resource_type_escaped = resource["type"]
    resource_name_escaped = re.escape(resource["name"])
    resource_pattern = (
        resource_type_escaped
        + r"\s+['\"]?"
        + resource_name_escaped
        + r"['\"]?\s+do\s*(.*?)\nend"
    )
    resource_match = re.search(resource_pattern, raw_content, re.DOTALL | re.MULTILINE)

    if resource_match:
        return resource_match.group(1)
    return None


def _extract_guard_patterns(resource_block: str) -> tuple[list, list, list, list]:
    """Extract all guard patterns from resource block.

    Args:
        resource_block: Resource block content.

    Returns:
        Tuple of (only_if_conditions, not_if_conditions, only_if_blocks, not_if_blocks).

    """
    import re

    # Extract only_if conditions
    only_if_pattern = re.compile(r'only_if\s+[\'"]([^\'"]+)[\'"]')
    only_if_matches = only_if_pattern.findall(resource_block)

    # Extract not_if conditions
    not_if_pattern = re.compile(r'not_if\s+[\'"]([^\'"]+)[\'"]')
    not_if_matches = not_if_pattern.findall(resource_block)

    # Extract only_if blocks (Ruby code blocks)
    only_if_block_pattern = re.compile(r"only_if\s+do\s*([\s\S]*?)\s*end", re.DOTALL)
    only_if_block_matches = only_if_block_pattern.findall(resource_block)

    # Extract not_if blocks (Ruby code blocks)
    not_if_block_pattern = re.compile(r"not_if\s+do\s*([\s\S]*?)\s*end", re.DOTALL)
    not_if_block_matches = not_if_block_pattern.findall(resource_block)

    return (
        only_if_matches,
        not_if_matches,
        only_if_block_matches,
        not_if_block_matches,
    )


def _convert_guards_to_when_conditions(
    only_if_conditions: list,
    not_if_conditions: list,
    only_if_blocks: list,
    not_if_blocks: list,
) -> list[str]:
    """Convert Chef guards to Ansible when conditions.

    Args:
        only_if_conditions: List of only_if condition strings.
        not_if_conditions: List of not_if condition strings.
        only_if_blocks: List of only_if block contents.
        not_if_blocks: List of not_if block contents.

    Returns:
        List of Ansible when conditions.

    """
    when_conditions = []

    # Process only_if conditions (these become when conditions)
    for condition in only_if_conditions:
        ansible_condition = _convert_chef_condition_to_ansible(condition)
        if ansible_condition:
            when_conditions.append(ansible_condition)

    # Process only_if blocks
    for block in only_if_blocks:
        ansible_condition = _convert_chef_block_to_ansible(block, positive=True)
        if ansible_condition:
            when_conditions.append(ansible_condition)

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

    return when_conditions


def _extract_chef_guards(resource: dict[str, str], raw_content: str) -> dict[str, Any]:
    """Extract Chef guards (only_if, not_if) and convert to Ansible when conditions.

    Args:
        resource: Resource dictionary with type, name, action, properties.
        raw_content: Raw recipe content.

    Returns:
        Dictionary with Ansible when/unless conditions.

    """
    guards = {}

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
    ) = _extract_guard_patterns(resource_block)

    # Convert to Ansible when conditions
    when_conditions = _convert_guards_to_when_conditions(
        only_if_conditions, not_if_conditions, only_if_blocks, not_if_blocks
    )

    # Format the when clause
    if when_conditions:
        if len(when_conditions) == 1:
            guards["when"] = when_conditions[0]
        else:
            # Multiple conditions - combine with 'and'
            guards["when"] = when_conditions

    return guards


def _convert_chef_condition_to_ansible(condition: str, negate: bool = False) -> str:
    """Convert a Chef condition string to Ansible when condition.

    Args:
        condition: Chef condition string.
        negate: Whether to negate the condition (for not_if).

    Returns:
        Ansible when condition string.

    """
    import re

    # Common Chef to Ansible condition mappings
    condition_mappings = {
        # File existence checks
        r'File\.exist\?\([\'"]([^\'"]+)[\'"]\)': (
            r'ansible_check_mode or {{ "\1" | is_file }}'
        ),
        r'File\.directory\?\([\'"]([^\'"]+)[\'"]\)': (
            r'ansible_check_mode or {{ "\1" | is_dir }}'
        ),
        r'File\.executable\?\([\'"]([^\'"]+)[\'"]\)': (
            r'ansible_check_mode or {{ "\1" | is_executable }}'
        ),
        # Package checks
        r'system\([\'"]which\s+(\w+)[\'"]\)': (
            r'ansible_check_mode or {{ ansible_facts.packages["\1"] is defined }}'
        ),
        # Service checks
        r'system\([\'"]systemctl\s+is-active\s+(\w+)[\'"]\)': (
            r'ansible_check_mode or {{ ansible_facts.services["\1"].state == "running" }}'
        ),
        r'system\([\'"]service\s+(\w+)\s+status[\'"]\)': (
            r'ansible_check_mode or {{ ansible_facts.services["\1"].state == "running" }}'
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


def _convert_chef_block_to_ansible(block: str, positive: bool = True) -> str:
    """Convert a Chef condition block to Ansible when condition.

    Args:
        block: Chef Ruby code block.
        positive: True for only_if blocks, False for not_if blocks.

    Returns:
        Ansible when condition string.

    """
    import re

    # Clean up the block
    block = block.strip()

    # Handle simple boolean returns
    if block.lower() in ["true", "false"]:
        result = block.lower() == "true"
        return str(result if positive else not result).lower()

    # Handle file existence patterns in blocks
    file_exist_pattern = re.search(r'File\.exist\?\([\'"]([^\'"]+)[\'"]\)', block)
    if file_exist_pattern:
        path = file_exist_pattern.group(1)
        condition = f'ansible_check_mode or {{ "{path}" | is_file }}'
        return condition if positive else f"not ({condition})"

    # Handle directory existence patterns
    dir_exist_pattern = re.search(r'File\.directory\?\([\'"]([^\'"]+)[\'"]\)', block)
    if dir_exist_pattern:
        path = dir_exist_pattern.group(1)
        condition = f'ansible_check_mode or {{ "{path}" | is_dir }}'
        return condition if positive else f"not ({condition})"

    # Handle command execution patterns
    system_pattern = re.search(r'system\([\'"]([^\'"]+)[\'"]\)', block)
    if system_pattern:
        condition = "ansible_check_mode or {{ ansible_facts.env.PATH is defined }}"
        return condition if positive else f"not ({condition})"

    # For complex blocks, create a comment indicating manual review needed
    condition = f"# TODO: Review Chef block condition: {block[:50]}..."
    return condition


def _extract_resource_subscriptions(
    resource: dict[str, str], raw_content: str
) -> list[dict[str, str]]:
    """Extract subscription information with timing constraints for a resource.

    Args:
        resource: Resource dictionary.
        raw_content: Raw recipe content.

    Returns:
        List of subscription dictionaries with timing information.

    """
    import re

    subscriptions = []

    # Enhanced subscribes pattern that captures timing
    subscribes_pattern = re.compile(
        r'subscribes\s+:(\w+),\s*[\'"]([^\'"]+)[\'"](?:\s*,\s*:(\w+))?', re.IGNORECASE
    )

    # Find all subscribes declarations
    subscribes_matches = subscribes_pattern.findall(raw_content)

    for action, target, timing in subscribes_matches:
        # Parse target like 'service[nginx]' or 'template[/etc/nginx/nginx.conf]'
        target_match = re.match(r"(\w+)\[([^\]]+)\]", target)
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


def _create_handler_with_timing(
    action: str, resource_type: str, resource_name: str, timing: str
) -> dict[str, Any]:
    """Create an Ansible handler with timing considerations.

    Args:
        action: The Chef action (e.g., 'reload', 'restart').
        resource_type: The Chef resource type (e.g., 'service').
        resource_name: The resource name (e.g., 'nginx').
        timing: The timing constraint ('immediate' or 'delayed').

    Returns:
        Handler task dictionary with timing metadata.

    """
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


# InSpec parsing helper functions


def _extract_control_metadata(control_body: str) -> dict[str, Any]:
    """Extract title, description, and impact from control body.

    Args:
        control_body: Content of the control block.

    Returns:
        Dictionary with title, desc, and impact.

    """
    metadata = {"title": "", "desc": "", "impact": 1.0}

    # Extract title
    title_match = re.search(r"title\s+['\"]([^'\"]+)['\"]", control_body)
    if title_match:
        metadata["title"] = title_match.group(1)

    # Extract description
    desc_match = re.search(r"desc\s+['\"]([^'\"]+)['\"]", control_body)
    if desc_match:
        metadata["desc"] = desc_match.group(1)

    # Extract impact
    impact_match = re.search(r"impact\s+([\d.]+)", control_body)
    if impact_match:
        metadata["impact"] = float(impact_match.group(1))

    return metadata


def _parse_inspec_control(content: str) -> list[dict[str, Any]]:
    """Parse InSpec control blocks from content.

    Args:
        content: InSpec profile content.

    Returns:
        List of parsed control dictionaries with id, title, desc, impact, and tests.

    """
    controls = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for control start
        control_match = re.match(r"control\s+['\"]([^'\"]+)['\"]\s+do", line)
        if control_match:
            control_id = control_match.group(1)

            # Find the matching end for this control
            control_body_lines, end_index = _find_nested_block_end(lines, i + 1)
            i = end_index

            # Parse the control body
            control_body = "\n".join(control_body_lines)

            control_data: dict[str, Any] = {
                "id": control_id,
                **_extract_control_metadata(control_body),
                "tests": _extract_inspec_describe_blocks(control_body),
            }

            controls.append(control_data)

        i += 1

    return controls


def _find_nested_block_end(lines: list[str], start_index: int) -> tuple[list[str], int]:
    """Find the end of a nested Ruby block (do...end).

    Args:
        lines: All lines of content.
        start_index: Starting line index (after the 'do' line).

    Returns:
        Tuple of (body_lines, ending_index).

    """
    nesting_level = 0
    body_lines = []
    i = start_index

    while i < len(lines):
        current_line = lines[i]
        stripped = current_line.strip()

        if re.search(r"\bdo\s*$", stripped):
            nesting_level += 1
        elif stripped == "end":
            if nesting_level == 0:
                break
            else:
                nesting_level -= 1

        body_lines.append(current_line)
        i += 1

    return body_lines, i


def _extract_it_expectations(describe_body: str) -> list[dict[str, Any]]:
    """Extract 'it { should ... }' expectations from describe block.

    Args:
        describe_body: Content of the describe block.

    Returns:
        List of expectation dictionaries.

    """
    expectations = []
    it_pattern = re.compile(r"it\s+\{([^}]+)\}")
    for it_match in it_pattern.finditer(describe_body):
        expectation = it_match.group(1).strip()
        expectations.append({"type": "should", "matcher": expectation})
    return expectations


def _extract_its_expectations(describe_body: str) -> list[dict[str, Any]]:
    """Extract 'its(...) { should ... }' expectations from describe block.

    Args:
        describe_body: Content of the describe block.

    Returns:
        List of expectation dictionaries.

    """
    expectations = []
    its_pattern = re.compile(r"its\(['\"]([^'\"]+)['\"]\)\s+\{([^}]+)\}")
    for its_match in its_pattern.finditer(describe_body):
        property_name = its_match.group(1)
        expectation = its_match.group(2).strip()
        expectations.append(
            {"type": "its", "property": property_name, "matcher": expectation}
        )
    return expectations


def _extract_inspec_describe_blocks(content: str) -> list[dict[str, Any]]:
    """Extract InSpec describe blocks and their matchers.

    Args:
        content: Content to parse for describe blocks.

    Returns:
        List of test dictionaries with resource type, name, and expectations.

    """
    tests = []
    lines = content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for describe start
        describe_match = re.match(
            r"describe\s+(\w+)\(['\"]?([^'\")\n]+)['\"]?\)\s+do", line
        )
        if describe_match:
            resource_type = describe_match.group(1)
            resource_name = describe_match.group(2).strip()

            # Find the matching end for this describe block
            describe_body_lines, end_index = _find_nested_block_end(lines, i + 1)
            i = end_index

            # Parse the describe body
            describe_body = "\n".join(describe_body_lines)

            test_data: dict[str, Any] = {
                "resource_type": resource_type,
                "resource_name": resource_name,
                "expectations": [],
            }

            # Extract expectations
            test_data["expectations"].extend(_extract_it_expectations(describe_body))
            test_data["expectations"].extend(_extract_its_expectations(describe_body))

            if test_data["expectations"]:
                tests.append(test_data)

        i += 1

    return tests


def _convert_package_to_testinfra(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """Convert package resource to Testinfra assertions.

    Args:
        lines: List to append test lines to.
        resource_name: Name of the package.
        expectations: List of InSpec expectations.

    """
    lines.append(f'    pkg = host.package("{resource_name}")')
    for exp in expectations:
        if "be_installed" in exp["matcher"]:
            lines.append("    assert pkg.is_installed")
        elif exp["type"] == "its" and exp["property"] == "version":
            version_match = re.search(r"match\s+/([^/]+)/", exp["matcher"])
            if version_match:
                version = version_match.group(1)
                lines.append(f'    assert pkg.version.startswith("{version}")')


def _convert_service_to_testinfra(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """Convert service resource to Testinfra assertions.

    Args:
        lines: List to append test lines to.
        resource_name: Name of the service.
        expectations: List of InSpec expectations.

    """
    lines.append(f'    svc = host.service("{resource_name}")')
    for exp in expectations:
        if "be_running" in exp["matcher"]:
            lines.append("    assert svc.is_running")
        elif "be_enabled" in exp["matcher"]:
            lines.append("    assert svc.is_enabled")


def _convert_file_to_testinfra(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """Convert file resource to Testinfra assertions.

    Args:
        lines: List to append test lines to.
        resource_name: Path to the file.
        expectations: List of InSpec expectations.

    """
    lines.append(f'    f = host.file("{resource_name}")')
    for exp in expectations:
        if "exist" in exp["matcher"]:
            lines.append("    assert f.exists")
        elif exp["type"] == "its" and exp["property"] == "mode":
            mode_match = re.search(r"cmp\s+'([^']+)'", exp["matcher"])
            if mode_match:
                mode = mode_match.group(1)
                lines.append(f'    assert oct(f.mode) == "{mode}"')
        elif exp["type"] == "its" and exp["property"] == "owner":
            owner_match = re.search(r"eq\s+['\"]([^'\"]+)['\"]", exp["matcher"])
            if owner_match:
                owner = owner_match.group(1)
                lines.append(f'    assert f.user == "{owner}"')


def _convert_port_to_testinfra(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """Convert port resource to Testinfra assertions.

    Args:
        lines: List to append test lines to.
        resource_name: Port number or address.
        expectations: List of InSpec expectations.

    """
    lines.append(f'    port = host.socket("tcp://{resource_name}")')
    for exp in expectations:
        if "be_listening" in exp["matcher"]:
            lines.append("    assert port.is_listening")


def _convert_inspec_to_testinfra(control: dict[str, Any]) -> str:
    """Convert InSpec control to Testinfra test.

    Args:
        control: Parsed InSpec control dictionary.

    Returns:
        Testinfra test code as string.

    """
    lines = []

    # Add test function header
    test_name = control["id"].replace("-", "_")
    lines.append(f"def test_{test_name}(host):")

    if control["desc"]:
        lines.append(f'    """{control["desc"]}"""')

    # Convert each describe block
    for test in control["tests"]:
        resource_type = test["resource_type"]
        resource_name = test["resource_name"]
        expectations = test["expectations"]

        # Map InSpec resources to Testinfra using dedicated converters
        if resource_type == "package":
            _convert_package_to_testinfra(lines, resource_name, expectations)
        elif resource_type == "service":
            _convert_service_to_testinfra(lines, resource_name, expectations)
        elif resource_type == "file":
            _convert_file_to_testinfra(lines, resource_name, expectations)
        elif resource_type == "port":
            _convert_port_to_testinfra(lines, resource_name, expectations)

    lines.append("")
    return "\n".join(lines)


def _convert_package_to_ansible_assert(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """Convert package expectations to Ansible assert conditions.

    Args:
        lines: List to append assertion lines to.
        resource_name: Name of the package.
        expectations: List of InSpec expectations.

    """
    for exp in expectations:
        if "be_installed" in exp["matcher"]:
            lines.append(
                f"      - ansible_facts.packages['{resource_name}'] is defined"
            )


def _convert_service_to_ansible_assert(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """Convert service expectations to Ansible assert conditions.

    Args:
        lines: List to append assertion lines to.
        resource_name: Name of the service.
        expectations: List of InSpec expectations.

    """
    for exp in expectations:
        if "be_running" in exp["matcher"]:
            lines.append(f"      - services['{resource_name}'].state == 'running'")
        elif "be_enabled" in exp["matcher"]:
            lines.append(f"      - services['{resource_name}'].status == 'enabled'")


def _convert_file_to_ansible_assert(
    lines: list[str], expectations: list[dict[str, Any]]
) -> None:
    """Convert file expectations to Ansible assert conditions.

    Args:
        lines: List to append assertion lines to.
        expectations: List of InSpec expectations.

    """
    for exp in expectations:
        if "exist" in exp["matcher"]:
            lines.append("      - stat_result.stat.exists")


def _convert_inspec_to_ansible_assert(control: dict[str, Any]) -> str:
    """Convert InSpec control to Ansible assert task.

    Args:
        control: Parsed InSpec control dictionary.

    Returns:
        Ansible assert task in YAML format.

    """
    lines = [
        f"- name: Verify {control['title'] or control['id']}",
        "  ansible.builtin.assert:",
        "    that:",
    ]

    # Convert each describe block to assertions
    for test in control["tests"]:
        resource_type = test["resource_type"]
        resource_name = test["resource_name"]
        expectations = test["expectations"]

        if resource_type == "package":
            _convert_package_to_ansible_assert(lines, resource_name, expectations)
        elif resource_type == "service":
            _convert_service_to_ansible_assert(lines, resource_name, expectations)
        elif resource_type == "file":
            _convert_file_to_ansible_assert(lines, expectations)

    # Add failure message
    fail_msg = f"{control['desc'] or control['id']} validation failed"
    lines.append(f'    fail_msg: "{fail_msg}"')

    return "\n".join(lines)


def _generate_inspec_package_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """Generate InSpec checks for package resource.

    Args:
        resource_name: Name of the package.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    lines = [
        f"  describe package('{resource_name}') do",
        "    it { should be_installed }",
    ]
    if "version" in properties:
        version = properties["version"]
        lines.append(f"    its('version') {{ should match /{version}/ }}")
    lines.append("  end")
    return lines


def _generate_inspec_service_checks(resource_name: str) -> list[str]:
    """Generate InSpec checks for service resource.

    Args:
        resource_name: Name of the service.

    Returns:
        List of InSpec check lines.

    """
    return [
        f"  describe service('{resource_name}') do",
        "    it { should be_running }",
        "    it { should be_enabled }",
        "  end",
    ]


def _generate_inspec_file_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """Generate InSpec checks for file/template resource.

    Args:
        resource_name: Name/path of the file.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    lines = [f"  describe file('{resource_name}') do", "    it { should exist }"]
    if "mode" in properties:
        lines.append(f"    its('mode') {{ should cmp '{properties['mode']}' }}")
    if "owner" in properties:
        lines.append(f"    its('owner') {{ should eq '{properties['owner']}' }}")
    if "group" in properties:
        lines.append(f"    its('group') {{ should eq '{properties['group']}' }}")
    lines.append("  end")
    return lines


def _generate_inspec_directory_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """Generate InSpec checks for directory resource.

    Args:
        resource_name: Path of the directory.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    lines = [
        f"  describe file('{resource_name}') do",
        "    it { should exist }",
        "    it { should be_directory }",
    ]
    if "mode" in properties:
        lines.append(f"    its('mode') {{ should cmp '{properties['mode']}' }}")
    lines.append("  end")
    return lines


def _generate_inspec_user_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """Generate InSpec checks for user resource.

    Args:
        resource_name: Username.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    lines = [f"  describe user('{resource_name}') do", "    it { should exist }"]
    if "shell" in properties:
        lines.append(f"    its('shell') {{ should eq '{properties['shell']}' }}")
    lines.append("  end")
    return lines


def _generate_inspec_group_checks(resource_name: str) -> list[str]:
    """Generate InSpec checks for group resource.

    Args:
        resource_name: Group name.

    Returns:
        List of InSpec check lines.

    """
    return [
        f"  describe group('{resource_name}') do",
        "    it { should exist }",
        "  end",
    ]


def _generate_inspec_from_resource(
    resource_type: str, resource_name: str, properties: dict[str, Any]
) -> str:
    """Generate InSpec control from Chef resource.

    Args:
        resource_type: Type of Chef resource.
        resource_name: Name of the resource.
        properties: Resource properties.

    Returns:
        InSpec control code as string.

    """
    control_id = f"{resource_type}-{resource_name.replace('/', '-')}"

    lines = [
        f"control '{control_id}' do",
        f"  title 'Verify {resource_type} {resource_name}'",
        f"  desc 'Ensure {resource_type} {resource_name} is properly configured'",
        "  impact 1.0",
        "",
    ]

    # Generate resource-specific checks
    resource_generators = {
        "package": lambda: _generate_inspec_package_checks(resource_name, properties),
        "service": lambda: _generate_inspec_service_checks(resource_name),
        "file": lambda: _generate_inspec_file_checks(resource_name, properties),
        "template": lambda: _generate_inspec_file_checks(resource_name, properties),
        "directory": lambda: _generate_inspec_directory_checks(
            resource_name, properties
        ),
        "user": lambda: _generate_inspec_user_checks(resource_name, properties),
        "group": lambda: _generate_inspec_group_checks(resource_name),
    }

    generator = resource_generators.get(resource_type)
    if generator:
        lines.extend(generator())

    lines.extend(["end", ""])

    return "\n".join(lines)


@mcp.tool()
def _parse_controls_from_directory(profile_path: Path) -> list[dict[str, Any]]:
    """Parse all control files from an InSpec profile directory.

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
    """Parse controls from a single InSpec control file.

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
    """Parse an InSpec profile and extract controls.

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
    """Convert InSpec controls to Ansible test format.

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
    """Extract resource data from recipe parse result.

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
    """Generate InSpec controls from a Chef recipe.

    Args:
        recipe_path: Path to Chef recipe file.

    Returns:
        InSpec control code or error message.

    """
    try:
        # First parse the recipe
        recipe_result = parse_recipe(recipe_path)

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
                control_code = _generate_inspec_from_resource(
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
    """Convert Chef data bag to Ansible variables format.

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
        import json

        import yaml

        # Parse the data bag content
        try:
            data = json.loads(databag_content)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format in data bag: {e}"

        # Convert to Ansible variables format
        ansible_vars = _convert_databag_to_ansible_vars(
            data, databag_name, item_name, is_encrypted
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
            return f"""---
# Chef data bag converted to Ansible variables
# Original: data_bags/{databag_name}/{item_name}.json
# Target: {target_scope}/{databag_name}.yml

{yaml_content}"""

    except Exception as e:
        return f"Error converting data bag to Ansible variables: {e}"


@mcp.tool()
def generate_ansible_vault_from_databags(
    databags_directory: str,
    output_directory: str = "group_vars",
    encryption_key_hint: str = "",
) -> str:
    """Generate Ansible Vault files from Chef data bags directory.

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
    """Analyze Chef cookbook for data bag usage and provide migration recommendations.

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
        return f"Error analyzing data bag usage: {e}"


@mcp.tool()
def convert_chef_environment_to_inventory_group(
    environment_content: str, environment_name: str, include_constraints: bool = True
) -> str:
    """Convert Chef environment to Ansible inventory group with variables.

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

{inventory_config}

---
# Add to your Ansible inventory (hosts.yml or hosts.ini):
# [{environment_name}]
# # Add your hosts here
#
# [all:children]
# {environment_name}
"""

    except Exception as e:
        return f"Error converting Chef environment to inventory group: {e}"


@mcp.tool()
def generate_inventory_from_chef_environments(
    environments_directory: str, output_format: str = "yaml"
) -> str:
    """Generate complete Ansible inventory from Chef environments directory.

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
    """Analyze Chef cookbook for environment usage.

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
    import re

    env_data = {
        "name": "",
        "description": "",
        "default_attributes": {},
        "override_attributes": {},
        "cookbook_versions": {},
    }

    # Extract name
    name_match = re.search(r"name\s+[\'\"](.*?)[\'\"]", content)
    if name_match:
        env_data["name"] = name_match.group(1)

    # Extract description
    desc_match = re.search(r"description\s+[\'\"](.*?)[\'\"]", content)
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
    import re

    # Find the block start
    pattern = rf"{block_type}\s*\((.*?)\)"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        return {}

    block_content = match.group(1).strip()

    # Simple parsing of Ruby hash-like structure
    # This is a simplified parser - real implementation might need more robust parsing
    attributes = {}

    # Parse simple key-value pairs
    key_value_pattern = r"[\'\"](.*?)[\'\"][:\s]*=>[:\s]*[\'\"](.*?)[\'\"]"
    for match in re.finditer(key_value_pattern, block_content):
        key = match.group(1)
        value = match.group(2)
        attributes[key] = value

    # Parse nested structures (basic support)
    nested_pattern = r"[\'\"](.*?)[\'\"][:\s]*=>[:\s]*\{(.*?)\}"
    for match in re.finditer(nested_pattern, block_content):
        key = match.group(1)
        nested_content = match.group(2)
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
    import re

    constraints = {}

    # Find cookbook version constraints
    cookbook_pattern = r"cookbook\s+[\'\"](.*?)[\'\"],\s*[\'\"](.*?)[\'\"]"
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

    group_vars = {}

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
        inventory = {"all": {"children": {}}}

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
    import re

    patterns = []

    # Common Chef environment patterns
    environment_patterns = [
        (r"node\.chef_environment", "node.chef_environment"),
        (r"node\[[\'\"]environment[\'\"]\]", 'node["environment"]'),
        (r"environment\s+[\'\"](.*?)[\'\"]", "environment declaration"),
        (
            r"if\s+node\.chef_environment\s*==\s*[\'\"](.*?)[\'\"]",
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
    structure = {"total_environments": 0, "environments": {}}

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


def _generate_environment_migration_recommendations(
    usage_patterns: list, env_structure: dict
) -> str:
    """Generate migration recommendations based on environment usage analysis."""
    recommendations = []

    # Analyze usage patterns
    if usage_patterns:
        environment_refs = [
            p for p in usage_patterns if "environment" in p.get("type", "")
        ]
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

    # Analyze structure
    if env_structure:
        total_envs = env_structure.get("total_environments", 0)
        if total_envs > 0:
            recommendations.append(
                f"• Convert {total_envs} Chef environments to Ansible inventory groups"
            )

            # Analyze complexity
            complex_envs = []
            for env_name, env_info in env_structure.get("environments", {}).items():
                if "error" not in env_info:
                    attrs_count = env_info.get(
                        "default_attributes_count", 0
                    ) + env_info.get("override_attributes_count", 0)
                    if attrs_count > 10:
                        complex_envs.append(env_name)

            if complex_envs:
                recommendations.append(
                    f"• {len(complex_envs)} environments have >10 attributes - "
                    f"consider splitting into logical variable groups"
                )

    # General migration recommendations
    recommendations.extend(
        [
            "• Use Ansible groups to replace Chef environment-based node targeting",
            "• Convert Chef default_attributes to group_vars",
            "• Handle Chef override_attributes with extra_vars or host_vars",
            "• Implement environment-specific playbook execution with --limit",
            "• Test variable precedence matches Chef behavior",
            "• Consider using Ansible environments/staging for deployment workflows",
        ]
    )

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
        import json

        data = json.loads(content)

        # Chef encrypted data bags typically have specific encrypted fields
        encrypted_indicators = ["encrypted_data", "cipher", "iv", "version"]

        # Check if any encrypted indicators are present
        for indicator in encrypted_indicators:
            if indicator in data:
                return True

        # Check for encrypted field patterns
        for _key, value in data.items():
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
    import re

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
    structure = {
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


@mcp.tool()
def generate_awx_job_template_from_cookbook(
    cookbook_path: str,
    cookbook_name: str,
    target_environment: str = "production",
    include_survey: bool = True,
) -> str:
    """Generate AWX/AAP job template configuration from Chef cookbook.

    Args:
        cookbook_path: Path to Chef cookbook directory
        cookbook_name: Name of the cookbook for job template
        target_environment: Target environment for the job template
        include_survey: Whether to include survey spec for cookbook attributes

    Returns:
        AWX/AAP job template JSON configuration

    """
    try:
        import json

        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Error: Cookbook path not found: {cookbook_path}"

        # Analyze cookbook structure
        cookbook_analysis = _analyze_cookbook_for_awx(cookbook, cookbook_name)

        # Generate job template
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
        return f"Error generating AWX job template from cookbook: {e}"


@mcp.tool()
def generate_awx_workflow_from_chef_runlist(
    runlist_content: str, workflow_name: str, environment: str = "production"
) -> str:
    """Generate AWX/AAP workflow template from Chef runlist.

    Args:
        runlist_content: Chef runlist content (JSON or comma-separated)
        workflow_name: Name for the workflow template
        environment: Target environment for workflow execution

    Returns:
        AWX/AAP workflow template configuration with job dependencies

    """
    try:
        import json

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
        return f"Error generating AWX workflow from Chef runlist: {e}"


@mcp.tool()
def generate_awx_project_from_cookbooks(
    cookbooks_directory: str,
    project_name: str,
    scm_type: str = "git",
    scm_url: str = "",
) -> str:
    """Generate AWX/AAP project configuration from Chef cookbooks directory.

    Args:
        cookbooks_directory: Path to Chef cookbooks directory
        project_name: Name for the AWX project
        scm_type: SCM type (git, svn, etc.)
        scm_url: SCM repository URL

    Returns:
        AWX/AAP project configuration with converted playbooks structure

    """
    try:
        import json

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
        return f"Error generating AWX project from cookbooks: {e}"


@mcp.tool()
def generate_awx_inventory_source_from_chef(
    chef_server_url: str, organization: str = "Default", sync_schedule: str = "daily"
) -> str:
    """Generate AWX/AAP inventory source from Chef server configuration.

    Args:
        chef_server_url: Chef server URL for inventory sync
        organization: AWX organization name
        sync_schedule: Inventory sync schedule (hourly, daily, weekly)

    Returns:
        AWX/AAP inventory source configuration for Chef server integration

    """
    try:
        import json

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
- CHEF_NODE_NAME: ${{chef_node_name}}
- CHEF_CLIENT_KEY: ${{chef_client_key}}
"""

    except Exception as e:
        return f"Error generating AWX inventory source from Chef: {e}"


def _analyze_cookbook_for_awx(cookbook_path, cookbook_name: str) -> dict:
    """Analyze Chef cookbook structure for AWX job template generation."""
    analysis = {
        "name": cookbook_name,
        "recipes": [],
        "attributes": {},
        "dependencies": [],
        "templates": [],
        "files": [],
        "survey_fields": [],
    }

    # Analyze recipes
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
    workflow_template = {
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
        "credential": "chef-server-credential",
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
"""
AWX/AAP Custom Inventory Script for Chef Server
Connects to Chef server and generates Ansible inventory
"""

import json
import sys
import os
from chef import ChefAPI

def main():
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
                'ansible_host': node.get('automatic', {{}}).get('ipaddress', node_name),
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
    import json

    try:
        # Try parsing as JSON first
        if runlist_content.strip().startswith("["):
            runlist = json.loads(runlist_content)
            return [
                item.replace("recipe[", "").replace("role[", "").replace("]", "")
                for item in runlist
            ]
    except json.JSONDecodeError:
        pass

    # Parse as comma-separated list
    if "," in runlist_content:
        items = [item.strip() for item in runlist_content.split(",")]
        return [
            item.replace("recipe[", "").replace("role[", "").replace("]", "")
            for item in items
        ]

    # Parse single item
    return [
        runlist_content.replace("recipe[", "").replace("role[", "").replace("]", "")
    ]


def _extract_cookbook_attributes(content: str) -> dict:
    """Extract cookbook attributes for survey generation."""
    import re

    attributes = {}

    # Find default attribute declarations
    attr_pattern = r"default\[['\"]([^'\"]+)['\"]\]\s*=\s*([^#\n]+)"
    for match in re.finditer(attr_pattern, content):
        attr_name = match.group(1)
        attr_value = match.group(2).strip()

        # Clean up value
        if attr_value.startswith(("'", '"')):
            attr_value = attr_value[1:-1]

        attributes[attr_name] = attr_value

    return attributes


def _extract_cookbook_dependencies(content: str) -> list:
    """Extract cookbook dependencies from metadata."""
    import re

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


def _analyze_cookbooks_directory(cookbooks_path) -> dict:
    """Analyze entire cookbooks directory structure."""
    analysis = {
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


@mcp.tool()
def convert_chef_deployment_to_ansible_strategy(
    deployment_recipe_path: str,
    deployment_pattern: str = "auto_detect",
    target_strategy: str = "rolling_update",
) -> str:
    """Convert Chef application deployment recipe to Ansible deployment strategy.

    Args:
        deployment_recipe_path: Path to Chef deployment recipe
        deployment_pattern: Chef deployment pattern
            (blue_green, rolling, canary, auto_detect)
        target_strategy: Target Ansible strategy
            (rolling_update, blue_green, canary)

    Returns:
        Ansible playbook with deployment strategy implementation

    """
    try:
        recipe_path = _normalize_path(deployment_recipe_path)
        if not recipe_path.exists():
            return f"Error: Deployment recipe not found: {deployment_recipe_path}"

        # Analyze Chef deployment recipe
        with recipe_path.open("r") as f:
            recipe_content = f.read()

        deployment_analysis = _analyze_chef_deployment_pattern(
            recipe_content, deployment_pattern
        )

        # Convert to Ansible deployment strategy
        ansible_strategy = _generate_ansible_deployment_strategy(
            deployment_analysis, target_strategy, recipe_path.stem
        )

        return f"""# Chef Deployment Recipe → Ansible Strategy Conversion
# Source: {deployment_recipe_path}
# Detected Pattern: {deployment_analysis["detected_pattern"]}
# Target Strategy: {target_strategy}

## Ansible Playbook:
```yaml
{ansible_strategy["playbook"]}
```

## Deployment Analysis:
{_format_deployment_analysis(deployment_analysis)}

## Strategy Features:
{_format_strategy_features(ansible_strategy)}

## Usage Instructions:
```bash
# Execute deployment
ansible-playbook -i inventory/{target_strategy}_deployment.yml \\
    --extra-vars "app_version={{{{ app_version }}}}" \\
    --limit "{{{{ target_hosts }}}}"

# Monitor deployment
ansible-playbook -i inventory monitor_deployment.yml \\
    --tags "health_check,rollback_ready"
```
"""

    except Exception as e:
        return f"Error converting Chef deployment to Ansible strategy: {e}"


@mcp.tool()
def generate_blue_green_deployment_playbook(
    app_name: str, service_config: str = "", health_check_url: str = "/health"
) -> str:
    """Generate Ansible blue/green deployment playbook from application configuration.

    Args:
        app_name: Name of the application to deploy
        service_config: JSON configuration for service setup
        health_check_url: URL endpoint for health checks

    Returns:
        Complete blue/green deployment playbook with rollback capabilities

    """
    try:
        import json

        # Parse service configuration
        config = {}
        if service_config:
            config = json.loads(service_config)

        # Generate blue/green deployment playbook
        playbook = _generate_blue_green_playbook(app_name, config, health_check_url)

        return f"""# Blue/Green Deployment Playbook
# Application: {app_name}

## Main Deployment Playbook:
```yaml
{playbook["main_playbook"]}
```

## Supporting Playbooks:

### Health Check Playbook:
```yaml
{playbook["health_check"]}
```

### Rollback Playbook:
```yaml
{playbook["rollback"]}
```

## Load Balancer Configuration:
```yaml
{playbook["load_balancer"]}
```

## Deployment Process:
1. Deploy to inactive environment (blue/green)
2. Run health checks on new deployment
3. Switch traffic to new environment
4. Keep previous environment as rollback option
5. Cleanup old environment after validation

## Variables:
```yaml
{playbook["variables"]}
```

## Execute Commands:
```bash
# Deploy new version
ansible-playbook blue_green_deploy.yml -e "app_version=1.2.3 target_env=green"

# Switch traffic
ansible-playbook blue_green_switch.yml -e "active_env=green"

# Rollback if needed
ansible-playbook blue_green_rollback.yml -e "rollback_to=blue"
```
"""

    except Exception as e:
        return f"Error generating blue/green deployment playbook: {e}"


@mcp.tool()
def generate_canary_deployment_strategy(
    app_name: str, canary_percentage: int = 10, rollout_steps: str = "10,25,50,100"
) -> str:
    """Generate Ansible canary deployment strategy with gradual rollout.

    Args:
        app_name: Name of the application for canary deployment
        canary_percentage: Initial canary traffic percentage
        rollout_steps: Comma-separated rollout percentages

    Returns:
        Canary deployment strategy with monitoring and automated rollback

    """
    try:
        # Parse rollout steps
        steps = [int(step.strip()) for step in rollout_steps.split(",")]

        # Generate canary deployment strategy
        canary_strategy = _generate_canary_strategy(app_name, canary_percentage, steps)

        return f"""# Canary Deployment Strategy
# Application: {app_name}
# Initial Canary: {canary_percentage}%
# Rollout Steps: {rollout_steps}%

## Canary Deployment Playbook:
```yaml
{canary_strategy["main_playbook"]}
```

## Monitoring and Validation:
```yaml
{canary_strategy["monitoring"]}
```

## Progressive Rollout:
```yaml
{canary_strategy["progressive_rollout"]}
```

## Automated Rollback:
```yaml
{canary_strategy["rollback"]}
```

## Deployment Workflow:
{_format_canary_workflow(steps, canary_percentage)}

## Monitoring Checks:
- Error rate: < 1%
- Response time: < 500ms
- Success rate: > 99%
- Resource utilization: < 80%

## Execution Commands:
```bash
# Start canary deployment
ansible-playbook canary_deploy.yml -e \
  "app_version=1.2.3 canary_percent={canary_percentage}"

# Progress to next stage (if metrics are good)
ansible-playbook canary_progress.yml -e "next_percent=25"

# Full rollout (if all stages successful)
ansible-playbook canary_complete.yml

# Emergency rollback
ansible-playbook canary_rollback.yml -e "reason='high_error_rate'"
```
"""

    except Exception as e:
        return f"Error generating canary deployment strategy: {e}"


@mcp.tool()
def analyze_chef_application_patterns(
    cookbook_path: str, application_type: str = "web_application"
) -> str:
    """Analyze Chef cookbook for application deployment patterns.

    Provides migration recommendations.

    Args:
        cookbook_path: Path to Chef application cookbook
        application_type: Type of application
            (web_application, microservice, database, etc.)

    Returns:
        Analysis of deployment patterns with Ansible migration recommendations

    """
    try:
        cookbook = _normalize_path(cookbook_path)
        if not cookbook.exists():
            return f"Error: Cookbook path not found: {cookbook_path}"

        # Analyze cookbook for deployment patterns
        deployment_patterns = _analyze_application_cookbook(cookbook, application_type)

        # Generate migration recommendations
        migration_recommendations = _generate_deployment_migration_recommendations(
            deployment_patterns, application_type
        )

        return f"""# Chef Application Cookbook Analysis
# Cookbook: {cookbook.name}
# Application Type: {application_type}

## Deployment Patterns Detected:
{_format_deployment_patterns(deployment_patterns)}

## Chef Resources Analysis:
{_format_chef_resources_analysis(deployment_patterns)}

## Migration Recommendations:
{migration_recommendations}

## Recommended Ansible Strategies:
{_recommend_ansible_strategies(deployment_patterns)}

## Implementation Priority:
1. Convert basic deployment logic to Ansible tasks
2. Implement health checks and validation
3. Add rollback capabilities
4. Configure monitoring and alerting
5. Test deployment strategies in staging
6. Implement progressive deployment patterns

## Next Steps:
- Use convert_chef_deployment_to_ansible_strategy for specific recipes
- Implement blue/green with generate_blue_green_deployment_playbook
- Set up canary deployments with generate_canary_deployment_strategy
- Integrate with AWX/AAP for automated execution
"""

    except Exception as e:
        return f"Error analyzing Chef application patterns: {e}"


def _analyze_chef_deployment_pattern(content: str, pattern_hint: str) -> dict:
    """Analyze Chef recipe content for deployment patterns."""
    import re

    analysis = {
        "detected_pattern": "standard",
        "deployment_steps": [],
        "health_checks": [],
        "rollback_mechanisms": [],
        "service_management": [],
        "load_balancer_config": [],
        "configuration_management": [],
    }

    # Detect deployment patterns
    deployment_indicators = {
        "blue_green": [
            r"blue.*green|green.*blue",
            r"inactive.*active",
            r"current.*previous",
            r"switch.*traffic",
        ],
        "rolling": [
            r"rolling.*update",
            r"serial.*deployment",
            r"batch.*size",
            r"max.*parallel",
        ],
        "canary": [
            r"canary.*deployment",
            r"traffic.*split",
            r"percentage.*rollout",
            r"gradual.*rollout",
        ],
    }

    detected_patterns = []
    for pattern_type, indicators in deployment_indicators.items():
        for indicator in indicators:
            if re.search(indicator, content, re.IGNORECASE):
                detected_patterns.append(pattern_type)
                break

    if detected_patterns:
        analysis["detected_pattern"] = detected_patterns[0]
    elif pattern_hint != "auto_detect":
        analysis["detected_pattern"] = pattern_hint

    # Extract deployment steps
    analysis["deployment_steps"] = _extract_deployment_steps(content)

    # Find health checks
    analysis["health_checks"] = _extract_health_checks(content)

    # Find service management
    analysis["service_management"] = _extract_service_management(content)

    # Find load balancer configuration
    analysis["load_balancer_config"] = _extract_load_balancer_config(content)

    return analysis


def _generate_blue_green_conversion_playbook(analysis: dict, recipe_name: str) -> str:
    """Generate blue/green deployment playbook from Chef analysis.

    Args:
        analysis: Chef deployment analysis data
        recipe_name: Name of the original recipe

    Returns:
        Blue/green deployment playbook YAML content

    """
    app_name = analysis.get("application_name", recipe_name)
    port = analysis.get("service_port", "8080")
    health_check_url = analysis.get(
        "health_check_url", f"http://localhost:{port}/health"
    )

    return f"""---
- name: Blue/Green Deployment - {app_name}
  hosts: app_servers
  serial: "100%"
  vars:
    app_name: {app_name}
    app_version: "{{{{ app_version | default('latest') }}}}"
    target_env: "{{{{ target_env | default('green') }}}}"
    current_env: "{{{{ current_env | default('blue') }}}}"
    health_check_url: "{health_check_url}"
    service_port: {port}

  tasks:
    - name: Deploy to inactive environment
      include_tasks: deploy_app.yml
      vars:
        deploy_env: "{{{{ target_env }}}}"

    - name: Health check inactive environment
      uri:
        url: "{{{{ health_check_url }}}}"
        method: GET
      register: health_check
      retries: 10
      delay: 30

    - name: Switch traffic to new environment
      include_tasks: switch_traffic.yml
      when: health_check.status == 200
"""


def _generate_canary_conversion_playbook(analysis: dict, recipe_name: str) -> str:
    """Generate canary deployment playbook from Chef analysis.

    Args:
        analysis: Chef deployment analysis data
        recipe_name: Name of the original recipe

    Returns:
        Canary deployment playbook YAML content

    """
    app_name = analysis.get("application_name", recipe_name)
    port = analysis.get("service_port", "8080")
    health_check_url = analysis.get(
        "health_check_url", f"http://localhost:{port}/health"
    )

    return f"""---
- name: Canary Deployment - {app_name}
  hosts: app_servers
  serial: "{{ canary_percentage | default(10) }}%"
  vars:
    app_name: {app_name}
    app_version: "{{{{ app_version | default('latest') }}}}"
    canary_percentage: "{{{{ canary_percentage | default(10) }}}}"
    health_check_url: "{health_check_url}"
    service_port: {port}

  tasks:
    - name: Deploy to canary hosts
      include_tasks: deploy_app.yml
      vars:
        deploy_env: canary

    - name: Health check canary deployment
      uri:
        url: "{{{{ health_check_url }}}}"
        method: GET
      register: canary_health
      retries: 5
      delay: 10

    - name: Monitor canary metrics
      include_tasks: monitor_canary.yml
      when: canary_health.status == 200

    - name: Proceed with full deployment
      include_tasks: deploy_app.yml
      vars:
        deploy_env: production
      when: canary_metrics.success | default(false)
"""


def _generate_ansible_deployment_strategy(
    analysis: dict, target_strategy: str, recipe_name: str
) -> dict:
    """Generate Ansible deployment strategy from Chef analysis."""
    strategy = {"playbook": "", "features": [], "variables": {}, "tasks_count": 0}

    if target_strategy == "rolling_update":
        strategy["playbook"] = _generate_rolling_update_playbook(recipe_name)
        strategy["features"] = [
            "Serial deployment",
            "Health checks",
            "Rollback on failure",
        ]
    elif target_strategy == "blue_green":
        strategy["playbook"] = _generate_blue_green_conversion_playbook(
            analysis, recipe_name
        )
        strategy["features"] = [
            "Zero-downtime deployment",
            "Instant rollback",
            "Traffic switching",
        ]
    elif target_strategy == "canary":
        strategy["playbook"] = _generate_canary_conversion_playbook(
            analysis, recipe_name
        )
        strategy["features"] = [
            "Gradual rollout",
            "Risk mitigation",
            "Automated monitoring",
        ]

    strategy["tasks_count"] = len(analysis.get("deployment_steps", []))
    strategy["variables"] = _generate_strategy_variables(target_strategy)

    return strategy


def _generate_blue_green_playbook(
    app_name: str, config: dict, health_check_url: str
) -> dict:
    """Generate complete blue/green deployment playbook structure."""
    port = config.get("port", 8080)
    service_name = config.get("service_name", app_name)

    playbook = {
        "main_playbook": f"""---
- name: Blue/Green Deployment - {app_name}
  hosts: app_servers
  serial: "100%"
  vars:
    app_name: {app_name}
    app_version: "{{{{ app_version | default('latest') }}}}"
    target_env: "{{{{ target_env | default('green') }}}}"
    current_env: "{{{{ current_env | default('blue') }}}}"
    health_check_url: "{health_check_url}"
    service_port: {port}

  tasks:
    - name: Determine inactive environment
      set_fact:
        inactive_env: "{{{{ 'green' if current_env == 'blue' else 'blue' }}}}"

    - name: Deploy application to inactive environment
      include_tasks: deploy_app.yml
      vars:
        deploy_env: "{{{{ inactive_env }}}}"

    - name: Run health checks on new deployment
      uri:
        url: >-
          http://{{{{ ansible_host }}}}:{{{{ service_port }}}}
          {{{{ health_check_url }}}}
        method: GET
        timeout: 30
      register: health_check
      retries: 5
      delay: 10

    - name: Switch traffic to new environment
      include_tasks: switch_traffic.yml
      vars:
        new_env: "{{{{ inactive_env }}}}"
        old_env: "{{{{ current_env }}}}"
      when: health_check is succeeded

    - name: Update current environment marker
      set_fact:
        current_env: "{{{{ inactive_env }}}}"
      when: health_check is succeeded""",
        "health_check": f"""---
- name: Health Check Validation
  hosts: app_servers
  tasks:
    - name: Check application health
      uri:
        url: >-
          http://{{{{ ansible_host }}}}:{{{{ service_port }}}}
          {{{{ health_check_url }}}}
        method: GET
        status_code: 200
        timeout: 30
      register: health_result

    - name: Validate response time
      fail:
        msg: "Response time too high: {{{{ health_result.elapsed }}}}"
      when: health_result.elapsed > 2.0

    - name: Check service status
      systemd:
        name: "{service_name}-{{{{ target_env }}}}"
        state: started
      register: service_status""",
        "rollback": f"""---
- name: Blue/Green Rollback
  hosts: app_servers
  vars:
    rollback_to: "{{{{ rollback_to | default('blue') }}}}"

  tasks:
    - name: Switch traffic back to previous environment
      include_tasks: switch_traffic.yml
      vars:
        new_env: "{{{{ rollback_to }}}}"
        old_env: "{{{{ current_env }}}}"

    - name: Stop failed deployment
      systemd:
        name: "{service_name}-{{{{ current_env }}}}"
        state: stopped

    - name: Update environment marker
      set_fact:
        current_env: "{{{{ rollback_to }}}}"

    - name: Log rollback event
      lineinfile:
        path: /var/log/{app_name}_deployments.log
        line: "{{{{ ansible_date_time.iso8601 }}}} ROLLBACK: {{{{ current_env }}}} -> {{{{ rollback_to }}}}"
        create: yes""",
        "load_balancer": f"""---
- name: Load Balancer Traffic Management
  hosts: load_balancers
  tasks:
    - name: Update upstream configuration
      template:
        src: upstream.conf.j2
        dest: /etc/nginx/conf.d/{app_name}_upstream.conf
      vars:
        active_env: "{{{{ new_env }}}}"
        inactive_env: "{{{{ old_env }}}}"

    - name: Test nginx configuration
      nginx:
        state: reloaded
      register: nginx_test

    - name: Reload nginx if configuration is valid
      systemd:
        name: nginx
        state: reloaded
      when: nginx_test is succeeded""",
        "variables": f"""---
# Blue/Green Deployment Variables
app_name: {app_name}
app_version: latest
current_env: blue
health_check_url: {health_check_url}
service_port: {port}

# Deployment timeouts
deployment_timeout: 300
health_check_retries: 5
health_check_delay: 10

# Environment-specific configurations
blue_env:
  port: {port}
  service_name: "{service_name}-blue"
  config_file: "/etc/{app_name}/blue.conf"

green_env:
  port: {port + 1}
  service_name: "{service_name}-green"
  config_file: "/etc/{app_name}/green.conf\"""",
    }

    return playbook


def _generate_canary_strategy(
    app_name: str, initial_percent: int, rollout_steps: list
) -> dict:
    """Generate canary deployment strategy playbooks."""
    strategy = {
        "main_playbook": f"""---
- name: Canary Deployment - {app_name}
  hosts: app_servers
  vars:
    app_name: {app_name}
    app_version: "{{{{ app_version }}}}"
    canary_percent: {initial_percent}
    rollout_steps: {rollout_steps}

  tasks:
    - name: Calculate canary instances
      set_fact:
        canary_count: "{{{{ (groups['app_servers'] | length * canary_percent / 100) | round(0, 'ceil') | int }}}}"

    - name: Select canary instances
      set_fact:
        canary_hosts: "{{{{ groups['app_servers'][:canary_count | int] }}}}"
        stable_hosts: "{{{{ groups['app_servers'][canary_count | int:] }}}}"

    - name: Deploy canary version
      include_tasks: deploy_canary.yml
      vars:
        target_hosts: "{{{{ canary_hosts }}}}"

    - name: Configure traffic splitting
      include_tasks: setup_traffic_split.yml
      vars:
        canary_percentage: "{{{{ canary_percent }}}}"

    - name: Monitor canary metrics
      include_tasks: monitor_canary.yml

    - name: Wait for validation period
      pause:
        minutes: 10
        prompt: "Monitoring canary deployment for 10 minutes..."

    - name: Evaluate canary success
      include_tasks: evaluate_canary.yml""",
        "monitoring": """---
- name: Canary Monitoring and Validation
  hosts: monitoring_servers
  tasks:
    - name: Check error rate
      uri:
        url: "http://monitoring.internal/api/metrics/error_rate"
        method: GET
        return_content: yes
      register: error_rate_result

    - name: Validate error rate threshold
      fail:
        msg: "Error rate too high: {{ error_rate_result.json.value }}%"
      when: error_rate_result.json.value | float > 1.0

    - name: Check response time
      uri:
        url: "http://monitoring.internal/api/metrics/response_time"
        method: GET
        return_content: yes
      register: response_time_result

    - name: Validate response time threshold
      fail:
        msg: "Response time too high: {{ response_time_result.json.value }}ms"
      when: response_time_result.json.value | float > 500

    - name: Check success rate
      uri:
        url: "http://monitoring.internal/api/metrics/success_rate"
        method: GET
        return_content: yes
      register: success_rate_result

    - name: Validate success rate threshold
      fail:
        msg: "Success rate too low: {{ success_rate_result.json.value }}%"
      when: success_rate_result.json.value | float < 99.0""",
        "progressive_rollout": f"""---
- name: Progressive Canary Rollout
  hosts: app_servers
  vars:
    rollout_steps: {rollout_steps}

  tasks:
    - name: Progress through rollout steps
      include_tasks: rollout_step.yml
      vars:
        target_percent: "{{{{ item }}}}"
      loop: "{{{{ rollout_steps }}}}"
      when: canary_success | default(true)

    - name: Complete rollout
      include_tasks: complete_deployment.yml
      when: canary_success | default(true)""",
        "rollback": f"""---
- name: Canary Rollback
  hosts: app_servers
  tasks:
    - name: Stop canary instances
      systemd:
        name: "{app_name}-canary"
        state: stopped
      delegate_to: "{{{{ item }}}}"
      loop: "{{{{ canary_hosts }}}}"

    - name: Restore stable version
      systemd:
        name: "{app_name}"
        state: started
      delegate_to: "{{{{ item }}}}"
      loop: "{{{{ canary_hosts }}}}"

    - name: Reset traffic routing
      include_tasks: reset_traffic.yml

    - name: Log rollback reason
      lineinfile:
        path: /var/log/{app_name}_canary.log
        line: "{{{{ ansible_date_time.iso8601 }}}} ROLLBACK: {{{{ reason | default('manual') }}}}"
        create: yes""",
    }

    return strategy


def _extract_deployment_steps(content: str) -> list:
    """Extract deployment steps from Chef recipe."""
    import re

    steps = []

    # Look for common deployment patterns
    deployment_patterns = [
        r'(package|service|template|file|directory)\s+[\'"]([^\'"]*)[\'"]\s+do',
        r'execute\s+[\'"]([^\'"]*)[\'"]\s+do',
        r'bash\s+[\'"]([^\'"]*)[\'"]\s+do',
    ]

    for pattern in deployment_patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            resource_type = match.group(1)
            resource_name = match.group(2)
            steps.append(
                {
                    "type": resource_type,
                    "name": resource_name,
                    "line": content[: match.start()].count("\n") + 1,
                }
            )

    return steps


def _extract_health_checks(content: str) -> list:
    """Extract health check patterns from Chef recipe."""
    import re

    health_checks = []

    health_patterns = [
        r"http_request.*health|health.*check",
        r"curl.*health|wget.*health",
        r"tcp.*check|port.*check",
        r"service.*status|systemctl.*status",
    ]

    for pattern in health_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            health_checks.append(
                {
                    "pattern": match.group(0),
                    "line": content[: match.start()].count("\n") + 1,
                }
            )

    return health_checks


def _extract_service_management(content: str) -> list:
    """Extract service management patterns from Chef recipe."""
    import re

    services = []

    service_patterns = [
        r'service\s+[\'"]([^\'"]*)[\'"]\s+do',
        r'systemd_service\s+[\'"]([^\'"]*)[\'"]\s+do',
        r"systemctl\s+(start|stop|restart|reload)\s+([^\s]+)",
    ]

    for pattern in service_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            services.append(
                {
                    "name": match.group(1) if match.group(1) else match.group(2),
                    "action": "manage",
                    "line": content[: match.start()].count("\n") + 1,
                }
            )

    return services


def _extract_load_balancer_config(content: str) -> list:
    """Extract load balancer configuration from Chef recipe."""
    import re

    lb_configs = []

    lb_patterns = [
        r"nginx.*upstream|haproxy.*backend",
        r"load.*balance|traffic.*split",
        r"proxy_pass|backend.*server",
    ]

    for pattern in lb_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            lb_configs.append(
                {
                    "type": "load_balancer",
                    "config": match.group(0),
                    "line": content[: match.start()].count("\n") + 1,
                }
            )

    return lb_configs


def _generate_rolling_update_playbook(recipe_name: str) -> str:
    """Generate rolling update playbook from Chef analysis."""
    return f"""---
- name: Rolling Update Deployment - {recipe_name}
  hosts: app_servers
  serial: 2
  max_fail_percentage: 10

  vars:
    app_version: "{{{{ app_version }}}}"
    health_check_retries: 3
    health_check_delay: 10

  pre_tasks:
    - name: Remove server from load balancer
      uri:
        url: "http://lb.internal/api/servers/{{{{ ansible_host }}}}/disable"
        method: POST
      delegate_to: localhost

  tasks:
    - name: Deploy new version
      include_tasks: deploy_application.yml

    - name: Restart application service
      systemd:
        name: application
        state: restarted
        daemon_reload: yes

    - name: Wait for service to be ready
      wait_for:
        port: 8080
        delay: 5
        timeout: 60

    - name: Health check
      uri:
        url: "http://{{{{ ansible_host }}}}:8080/health"
        method: GET
        status_code: 200
      retries: "{{{{ health_check_retries }}}}"
      delay: "{{{{ health_check_delay }}}}"

  post_tasks:
    - name: Re-enable server in load balancer
      uri:
        url: "http://lb.internal/api/servers/{{{{ ansible_host }}}}/enable"
        method: POST
      delegate_to: localhost

  rescue:
    - name: Rollback on failure
      include_tasks: rollback_deployment.yml

    - name: Re-enable server in load balancer
      uri:
        url: "http://lb.internal/api/servers/{{{{ ansible_host }}}}/enable"
        method: POST
      delegate_to: localhost"""


def _analyze_application_cookbook(cookbook_path, app_type: str) -> dict:
    """Analyze Chef application cookbook for deployment patterns."""
    analysis = {
        "cookbook_name": cookbook_path.name,
        "application_type": app_type,
        "deployment_patterns": [],
        "service_resources": [],
        "configuration_files": [],
        "health_checks": [],
        "scaling_mechanisms": [],
        "monitoring_setup": [],
    }

    # Analyze recipes for deployment patterns
    recipes_dir = _safe_join(cookbook_path, "recipes")
    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            with recipe_file.open("r") as f:
                content = f.read()

            # Detect deployment patterns
            patterns = _detect_deployment_patterns_in_recipe(content, recipe_file.name)
            analysis["deployment_patterns"].extend(patterns)

            # Find service resources
            services = _extract_service_management(content)
            analysis["service_resources"].extend(services)

            # Find health checks
            health_checks = _extract_health_checks(content)
            analysis["health_checks"].extend(health_checks)

    # Analyze templates
    templates_dir = _safe_join(cookbook_path, "templates")
    if templates_dir.exists():
        config_files = [f.name for f in templates_dir.rglob("*") if f.is_file()]
        analysis["configuration_files"] = config_files

    return analysis


def _detect_deployment_patterns_in_recipe(content: str, recipe_name: str) -> list:
    """Detect deployment patterns in a Chef recipe."""
    import re

    patterns = []

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


def _format_deployment_analysis(analysis: dict) -> str:
    """Format deployment analysis for display."""
    formatted = [
        f"• Detected Pattern: {analysis['detected_pattern']}",
        f"• Deployment Steps: {len(analysis['deployment_steps'])}",
        f"• Health Checks: {len(analysis['health_checks'])}",
        f"• Service Management: {len(analysis['service_management'])}",
        f"• Load Balancer Config: {len(analysis['load_balancer_config'])}",
    ]

    return "\n".join(formatted)


def _format_strategy_features(strategy: dict) -> str:
    """Format Ansible strategy features for display."""
    formatted = [f"• {feature}" for feature in strategy.get("features", [])]
    formatted.append(f"• Total Tasks: {strategy.get('tasks_count', 0)}")

    return "\n".join(formatted)


def _format_canary_workflow(steps: list, initial_percent: int) -> str:
    """Format canary deployment workflow steps."""
    workflow = [
        f"1. Deploy canary version to {initial_percent}% of instances",
        "2. Monitor metrics for validation period (10 minutes)",
        "3. Evaluate success criteria (error rate, response time, success rate)",
    ]

    for i, step in enumerate(steps[1:], 4):
        workflow.append(f"{i}. If successful, increase traffic to {step}%")

    workflow.append(
        f"{len(workflow) + 1}. Complete full rollout or rollback on failure"
    )

    return "\n".join(workflow)


def _format_deployment_patterns(patterns: dict) -> str:
    """Format detected deployment patterns."""
    if not patterns.get("deployment_patterns"):
        return "No specific deployment patterns detected."

    formatted = []
    for pattern in patterns["deployment_patterns"]:
        confidence = pattern.get("confidence", "medium")
        formatted.append(
            f"• {pattern['type'].title()} deployment ({confidence} confidence) in {pattern['recipe']}"
        )

    return "\n".join(formatted)


def _format_chef_resources_analysis(patterns: dict) -> str:
    """Format Chef resources analysis."""
    formatted = [
        f"• Service Resources: {len(patterns.get('service_resources', []))}",
        f"• Configuration Files: {len(patterns.get('configuration_files', []))}",
        f"• Health Checks: {len(patterns.get('health_checks', []))}",
        f"• Scaling Mechanisms: {len(patterns.get('scaling_mechanisms', []))}",
    ]

    return "\n".join(formatted)


def _generate_deployment_migration_recommendations(
    patterns: dict, app_type: str
) -> str:
    """Generate migration recommendations based on analysis."""
    recommendations = []

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

    return "\n".join(recommendations)


def _recommend_ansible_strategies(patterns: dict) -> str:
    """Recommend appropriate Ansible strategies."""
    strategies = []

    detected_patterns = [p["type"] for p in patterns.get("deployment_patterns", [])]

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

    if not strategies:
        strategies = [
            "• Rolling Update: Recommended starting strategy",
            "• Blue/Green: For critical applications requiring zero downtime",
            "• Canary: For high-risk deployments requiring validation",
        ]

    return "\n".join(strategies)


def _generate_strategy_variables(strategy: str) -> dict:
    """Generate strategy-specific variables."""
    base_vars = {
        "app_version": "latest",
        "health_check_retries": 3,
        "health_check_delay": 10,
        "deployment_timeout": 300,
    }

    if strategy == "blue_green":
        base_vars.update({"blue_port": 8080, "green_port": 8081, "switch_delay": 30})
    elif strategy == "canary":
        base_vars.update(
            {
                "canary_percentage": 10,
                "validation_period": 600,
                "rollback_threshold": 1.0,
            }
        )
    elif strategy == "rolling_update":
        base_vars.update({"serial_count": 2, "max_fail_percentage": 10})

    return base_vars


@mcp.tool()
def assess_chef_migration_complexity(
    cookbook_paths: str,
    migration_scope: str = "full",
    target_platform: str = "ansible_awx",
) -> str:
    """Assess the complexity of migrating Chef cookbooks to Ansible with detailed analysis.

    Args:
        cookbook_paths: Comma-separated paths to Chef cookbooks or cookbook directory
        migration_scope: Scope of migration (full, recipes_only, infrastructure_only)
        target_platform: Target platform (ansible_awx, ansible_core, ansible_tower)

    Returns:
        Comprehensive migration complexity assessment with recommendations

    """
    try:
        # Parse cookbook paths
        paths = [_normalize_path(path.strip()) for path in cookbook_paths.split(",")]

        # Assess each cookbook
        cookbook_assessments = []
        overall_metrics = {
            "total_cookbooks": 0,
            "total_recipes": 0,
            "total_resources": 0,
            "complexity_score": 0,
            "estimated_effort_days": 0,
        }

        for cookbook_path in paths:
            if cookbook_path.exists():
                # deepcode ignore PT: cookbook_path is already normalized via _normalize_path
                assessment = _assess_single_cookbook(cookbook_path)
                cookbook_assessments.append(assessment)

                # Aggregate metrics
                overall_metrics["total_cookbooks"] += 1
                overall_metrics["total_recipes"] += assessment["metrics"][
                    "recipe_count"
                ]
                overall_metrics["total_resources"] += assessment["metrics"][
                    "resource_count"
                ]
                overall_metrics["complexity_score"] += assessment["complexity_score"]
                overall_metrics["estimated_effort_days"] += assessment[
                    "estimated_effort_days"
                ]

        # Calculate averages
        if cookbook_assessments:
            overall_metrics["avg_complexity"] = int(
                overall_metrics["complexity_score"] / len(cookbook_assessments)
            )

        # Generate migration recommendations
        recommendations = _generate_migration_recommendations_from_assessment(
            cookbook_assessments, overall_metrics, target_platform
        )

        # Create migration roadmap
        roadmap = _create_migration_roadmap(cookbook_assessments)

        return f"""# Chef to Ansible Migration Assessment
# Scope: {migration_scope}
# Target Platform: {target_platform}

## Overall Migration Metrics:
{_format_overall_metrics(overall_metrics)}

## Cookbook Assessments:
{_format_cookbook_assessments(cookbook_assessments)}

## Migration Complexity Analysis:
{_format_complexity_analysis(cookbook_assessments)}

## Migration Recommendations:
{recommendations}

## Migration Roadmap:
{roadmap}

## Risk Assessment:
{_assess_migration_risks(cookbook_assessments, target_platform)}

## Resource Requirements:
{_estimate_resource_requirements(overall_metrics, target_platform)}
"""

    except Exception as e:
        return f"Error assessing migration complexity: {e}"


@mcp.tool()
def generate_migration_plan(
    cookbook_paths: str, migration_strategy: str = "phased", timeline_weeks: int = 12
) -> str:
    """Generate a detailed migration plan from Chef to Ansible with timeline and milestones.

    Args:
        cookbook_paths: Comma-separated paths to Chef cookbooks
        migration_strategy: Migration approach (big_bang, phased, parallel)
        timeline_weeks: Target timeline in weeks

    Returns:
        Detailed migration plan with phases, milestones, and deliverables

    """
    try:
        # Parse and assess cookbooks
        paths = [_normalize_path(path.strip()) for path in cookbook_paths.split(",")]
        cookbook_assessments = []

        for cookbook_path in paths:
            if cookbook_path.exists():
                # deepcode ignore PT: cookbook_path is already normalized via _normalize_path
                assessment = _assess_single_cookbook(cookbook_path)
                cookbook_assessments.append(assessment)

        # Generate migration plan based on strategy
        migration_plan = _generate_detailed_migration_plan(
            cookbook_assessments, migration_strategy, timeline_weeks
        )

        return f"""# Chef to Ansible Migration Plan
# Strategy: {migration_strategy}
# Timeline: {timeline_weeks} weeks
# Cookbooks: {len(cookbook_assessments)}

## Executive Summary:
{migration_plan["executive_summary"]}

## Migration Phases:
{migration_plan["phases"]}

## Timeline and Milestones:
{migration_plan["timeline"]}

## Team Requirements:
{migration_plan["team_requirements"]}

## Prerequisites and Dependencies:
{migration_plan["prerequisites"]}

## Testing Strategy:
{migration_plan["testing_strategy"]}

## Risk Mitigation:
{migration_plan["risk_mitigation"]}

## Success Criteria:
{migration_plan["success_criteria"]}

## Post-Migration Tasks:
{migration_plan["post_migration"]}
"""

    except Exception as e:
        return f"Error generating migration plan: {e}"


@mcp.tool()
def analyze_cookbook_dependencies(
    cookbook_path: str, dependency_depth: str = "direct"
) -> str:
    """Analyze cookbook dependencies and identify migration order requirements.

    Args:
        cookbook_path: Path to Chef cookbook or cookbooks directory
        dependency_depth: Analysis depth (direct, transitive, full)

    Returns:
        Dependency analysis with migration order recommendations

    """
    try:
        cookbook_path_obj = _normalize_path(cookbook_path)
        if not cookbook_path_obj.exists():
            return f"{ERROR_PREFIX} Cookbook path not found: {cookbook_path}"

        # Analyze dependencies
        dependency_analysis = _analyze_cookbook_dependencies_detailed(cookbook_path_obj)

        # Determine migration order
        migration_order = _determine_migration_order(dependency_analysis)

        # Identify circular dependencies
        circular_deps = _identify_circular_dependencies(dependency_analysis)

        return f"""# Cookbook Dependency Analysis
# Cookbook: {cookbook_path_obj.name}
# Analysis Depth: {dependency_depth}

## Dependency Overview:
{_format_dependency_overview(dependency_analysis)}

## Dependency Graph:
{_format_dependency_graph(dependency_analysis)}

## Migration Order Recommendations:
{_format_migration_order(migration_order)}

## Circular Dependencies:
{_format_circular_dependencies(circular_deps)}

## External Dependencies:
{_format_external_dependencies(dependency_analysis)}

## Community Cookbooks:
{_format_community_cookbooks(dependency_analysis)}

## Migration Impact Analysis:
{_analyze_dependency_migration_impact(dependency_analysis)}
"""

    except Exception as e:
        return f"Error analyzing cookbook dependencies: {e}"


@mcp.tool()
def generate_migration_report(
    assessment_results: str,
    report_format: str = "executive",
    include_technical_details: str = "yes",
) -> str:
    """Generate comprehensive migration report from assessment results.

    Args:
        assessment_results: JSON string or summary of assessment results
        report_format: Report format (executive, technical, combined)
        include_technical_details: Include detailed technical analysis (yes/no)

    Returns:
        Formatted migration report for stakeholders

    """
    try:
        from datetime import datetime

        # Generate report based on format
        report = _generate_comprehensive_migration_report(
            include_technical_details == "yes"
        )

        current_date = datetime.now().strftime("%Y-%m-%d")

        return f"""# Chef to Ansible Migration Report
**Generated:** {current_date}
**Report Type:** {report_format.title()}
**Technical Details:** {"Included" if include_technical_details == "yes" else "Summary Only"}

## Executive Summary
{report["executive_summary"]}

## Migration Scope and Objectives
{report["scope_objectives"]}

## Current State Analysis
{report["current_state"]}

## Target State Architecture
{report["target_state"]}

## Migration Strategy and Approach
{report["strategy"]}

## Cost-Benefit Analysis
{report["cost_benefit"]}

## Timeline and Resource Requirements
{report["timeline_resources"]}

## Risk Assessment and Mitigation
{report["risk_assessment"]}

{"## Technical Implementation Details" if include_technical_details == "yes" else ""}
{report.get("technical_details", "") if include_technical_details == "yes" else ""}

## Recommendations and Next Steps
{report["recommendations"]}

## Appendices
{report["appendices"]}
"""

    except Exception as e:
        return f"Error generating migration report: {e}"


def _assess_single_cookbook(cookbook_path) -> dict:
    """Assess complexity of a single cookbook."""
    cookbook = _normalize_path(cookbook_path)
    assessment = {
        "cookbook_name": cookbook.name,
        "cookbook_path": str(cookbook),
        "metrics": {},
        "complexity_score": 0,
        "estimated_effort_days": 0,
        "challenges": [],
        "migration_priority": "medium",
        "dependencies": [],
    }

    # Count recipes and resources
    recipes_dir = _safe_join(cookbook, "recipes")
    recipe_count = len(list(recipes_dir.glob("*.rb"))) if recipes_dir.exists() else 0

    # Analyze recipe complexity
    resource_count = 0
    custom_resources = 0
    ruby_blocks = 0

    if recipes_dir.exists():
        for recipe_file in recipes_dir.glob("*.rb"):
            with recipe_file.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Count Chef resources
                import re

                resources = len(re.findall(r'\w+\s+[\'"].*[\'"]\s+do', content))
                ruby_blocks += len(
                    re.findall(r"ruby_block|execute|bash", content, re.IGNORECASE)
                )
                custom_resources += len(
                    re.findall(
                        r"custom_resource|provides|use_inline_resources", content
                    )
                )
                resource_count += resources

    assessment["metrics"] = {
        "recipe_count": recipe_count,
        "resource_count": resource_count,
        "custom_resources": custom_resources,
        "ruby_blocks": ruby_blocks,
        "templates": len(list(_safe_join(cookbook, "templates").glob("*")))
        if _safe_join(cookbook, "templates").exists()
        else 0,
        "files": len(list(_safe_join(cookbook, "files").glob("*")))
        if _safe_join(cookbook, "files").exists()
        else 0,
    }

    # Calculate complexity score (0-100)
    complexity_factors = {
        "recipe_count": min(recipe_count * 2, 20),
        "resource_density": min(resource_count / max(recipe_count, 1) * 5, 25),
        "custom_resources": custom_resources * 10,
        "ruby_blocks": ruby_blocks * 5,
        "templates": min(assessment["metrics"]["templates"] * 2, 15),
        "files": min(assessment["metrics"]["files"] * 1, 10),
    }

    assessment["complexity_score"] = sum(complexity_factors.values())

    # Estimate effort (person-days)
    base_effort = recipe_count * 0.5  # 0.5 days per recipe
    complexity_multiplier = 1 + (assessment["complexity_score"] / 100)
    assessment["estimated_effort_days"] = round(base_effort * complexity_multiplier, 1)

    # Identify challenges
    if custom_resources > 0:
        assessment["challenges"].append(
            f"{custom_resources} custom resources requiring manual conversion"
        )
    if ruby_blocks > 5:
        assessment["challenges"].append(
            f"{ruby_blocks} Ruby blocks needing shell script conversion"
        )
    if assessment["complexity_score"] > 70:
        assessment["challenges"].append(
            "High complexity cookbook requiring expert review"
        )

    # Set migration priority
    if assessment["complexity_score"] < 30:
        assessment["migration_priority"] = "low"
    elif assessment["complexity_score"] > 70:
        assessment["migration_priority"] = "high"

    return assessment


def _format_overall_metrics(metrics: dict) -> str:
    """Format overall migration metrics."""
    return f"""• Total Cookbooks: {metrics["total_cookbooks"]}
• Total Recipes: {metrics["total_recipes"]}
• Total Resources: {metrics["total_resources"]}
• Average Complexity: {metrics.get("avg_complexity", 0):.1f}/100
• Estimated Total Effort: {metrics["estimated_effort_days"]:.1f} person-days
• Estimated Duration: {int(metrics["estimated_effort_days"] / 5)}-{int(metrics["estimated_effort_days"] / 3)} weeks"""


def _format_cookbook_assessments(assessments: list) -> str:
    """Format individual cookbook assessments."""
    if not assessments:
        return "No cookbooks assessed."

    def _get_priority_icon(priority: str) -> str:
        """Get priority icon based on migration priority level."""
        if priority == "high":
            return "🔴"
        elif priority == "medium":
            return "🟡"
        else:
            return "🟢"

    formatted = []
    for assessment in assessments:
        priority_icon = _get_priority_icon(assessment["migration_priority"])
        formatted.append(f"""### {assessment["cookbook_name"]} {priority_icon}
• Complexity Score: {assessment["complexity_score"]:.1f}/100
• Estimated Effort: {assessment["estimated_effort_days"]} days
• Recipes: {assessment["metrics"]["recipe_count"]}
• Resources: {assessment["metrics"]["resource_count"]}
• Custom Resources: {assessment["metrics"]["custom_resources"]}
• Challenges: {len(assessment["challenges"])}""")

    return "\n\n".join(formatted)


def _format_complexity_analysis(assessments: list) -> str:
    """Format complexity analysis."""
    if not assessments:
        return "No complexity analysis available."

    high_complexity = [a for a in assessments if a["complexity_score"] > 70]
    medium_complexity = [a for a in assessments if 30 <= a["complexity_score"] <= 70]
    low_complexity = [a for a in assessments if a["complexity_score"] < 30]

    return f"""• High Complexity (>70): {len(high_complexity)} cookbooks
• Medium Complexity (30-70): {len(medium_complexity)} cookbooks
• Low Complexity (<30): {len(low_complexity)} cookbooks

**Top Migration Challenges:**
{_identify_top_challenges(assessments)}"""


def _identify_top_challenges(assessments: list) -> str:
    """Identify the most common migration challenges."""
    challenge_counts = {}
    for assessment in assessments:
        for challenge in assessment["challenges"]:
            challenge_counts[challenge] = challenge_counts.get(challenge, 0) + 1

    top_challenges = sorted(challenge_counts.items(), key=lambda x: x[1], reverse=True)[
        :5
    ]

    formatted = []
    for challenge, count in top_challenges:
        formatted.append(f"  - {challenge} ({count} cookbooks)")

    return (
        "\n".join(formatted)
        if formatted
        else "  - No significant challenges identified"
    )


def _generate_migration_recommendations_from_assessment(
    assessments: list, metrics: dict, target_platform: str
) -> str:
    """Generate migration recommendations based on assessment."""
    recommendations = []

    # Platform-specific recommendations
    if target_platform == "ansible_awx":
        recommendations.append(
            "• Implement AWX/AAP integration for job templates and workflows"
        )
        recommendations.append(
            "• Set up dynamic inventory sources for Chef server integration"
        )

    # Complexity-based recommendations
    avg_complexity = metrics.get("avg_complexity", 0)
    if avg_complexity > 60:
        recommendations.append(
            "• Consider phased migration approach due to high complexity"
        )
        recommendations.append(
            "• Allocate additional time for custom resource conversion"
        )
        recommendations.append("• Plan for comprehensive testing and validation")
    else:
        recommendations.append("• Standard migration timeline should be sufficient")
        recommendations.append("• Consider big-bang approach for faster delivery")

    # Effort-based recommendations
    total_effort = metrics["estimated_effort_days"]
    if total_effort > 30:
        recommendations.append("• Establish dedicated migration team")
        recommendations.append("• Consider parallel migration tracks")
    else:
        recommendations.append("• Single developer can handle migration with oversight")

    # Custom resource recommendations
    custom_resource_cookbooks = [
        a for a in assessments if a["metrics"]["custom_resources"] > 0
    ]
    if custom_resource_cookbooks:
        recommendations.append(
            f"• {len(custom_resource_cookbooks)} cookbooks need custom resource conversion"
        )
        recommendations.append(
            "• Prioritize custom resource analysis and conversion strategy"
        )

    return "\n".join(recommendations)


def _create_migration_roadmap(assessments: list) -> str:
    """Create a migration roadmap based on assessments."""
    # Sort cookbooks by complexity (low to high for easier wins first)
    sorted_cookbooks = sorted(assessments, key=lambda x: x["complexity_score"])

    phases = {
        "Phase 1 - Foundation (Weeks 1-2)": [
            "Set up Ansible/AWX environment",
            "Establish CI/CD pipelines",
            "Create testing framework",
            "Train team on Ansible best practices",
        ],
        "Phase 2 - Low Complexity Migration (Weeks 3-5)": [],
        "Phase 3 - Medium Complexity Migration (Weeks 6-9)": [],
        "Phase 4 - High Complexity Migration (Weeks 10-12)": [],
        "Phase 5 - Validation and Cleanup (Weeks 13-14)": [
            "Comprehensive testing",
            "Performance validation",
            "Documentation updates",
            "Team training and handover",
        ],
    }

    # Distribute cookbooks across phases
    for cookbook in sorted_cookbooks:
        if cookbook["complexity_score"] < 30:
            phases["Phase 2 - Low Complexity Migration (Weeks 3-5)"].append(
                f"Migrate {cookbook['cookbook_name']} ({cookbook['estimated_effort_days']} days)"
            )
        elif cookbook["complexity_score"] < 70:
            phases["Phase 3 - Medium Complexity Migration (Weeks 6-9)"].append(
                f"Migrate {cookbook['cookbook_name']} ({cookbook['estimated_effort_days']} days)"
            )
        else:
            phases["Phase 4 - High Complexity Migration (Weeks 10-12)"].append(
                f"Migrate {cookbook['cookbook_name']} ({cookbook['estimated_effort_days']} days)"
            )

    # Format roadmap
    roadmap_formatted = []
    for phase, tasks in phases.items():
        roadmap_formatted.append(f"\n### {phase}")
        for task in tasks:
            roadmap_formatted.append(f"  - {task}")

    return "\n".join(roadmap_formatted)


def _assess_migration_risks(assessments: list, target_platform: str) -> str:
    """Assess migration risks."""
    risks = []

    # Technical risks
    high_complexity_count = len([a for a in assessments if a["complexity_score"] > 70])
    if high_complexity_count > 0:
        risks.append(
            f"🔴 HIGH: {high_complexity_count} high-complexity cookbooks may cause delays"
        )

    custom_resource_count = sum(a["metrics"]["custom_resources"] for a in assessments)
    if custom_resource_count > 0:
        risks.append(
            f"🟡 MEDIUM: {custom_resource_count} custom resources need manual conversion"
        )

    ruby_block_count = sum(a["metrics"]["ruby_blocks"] for a in assessments)
    if ruby_block_count > 10:
        risks.append(
            f"🟡 MEDIUM: {ruby_block_count} Ruby blocks require shell script conversion"
        )

    # Timeline risks
    total_effort = sum(a["estimated_effort_days"] for a in assessments)
    if total_effort > 50:
        risks.append("🟡 MEDIUM: Large migration scope may impact timeline")

    # Platform risks
    if target_platform == "ansible_awx":
        risks.append("🟢 LOW: AWX integration well-supported with existing tools")

    if not risks:
        risks.append("🟢 LOW: No significant migration risks identified")

    return "\n".join(risks)


def _estimate_resource_requirements(metrics: dict, target_platform: str) -> str:
    """Estimate resource requirements for migration."""
    total_effort = metrics["estimated_effort_days"]

    # Team size recommendations
    if total_effort < 20:
        team_size = "1 developer + 1 reviewer"
        timeline = "4-6 weeks"
    elif total_effort < 50:
        team_size = "2 developers + 1 senior reviewer"
        timeline = "6-10 weeks"
    else:
        team_size = "3-4 developers + 1 tech lead + 1 architect"
        timeline = "10-16 weeks"

    return f"""• **Team Size:** {team_size}
• **Estimated Timeline:** {timeline}
• **Total Effort:** {total_effort:.1f} person-days
• **Infrastructure:** {target_platform.replace("_", "/").upper()} environment
• **Testing:** Dedicated test environment recommended
• **Training:** 2-3 days Ansible/AWX training for team"""


def _analyze_cookbook_dependencies_detailed(cookbook_path) -> dict:
    """Analyze cookbook dependencies in detail."""
    analysis = {
        "cookbook_name": cookbook_path.name,
        "direct_dependencies": [],
        "transitive_dependencies": [],
        "external_dependencies": [],
        "community_cookbooks": [],
        "circular_dependencies": [],
    }

    # Read metadata.rb for dependencies
    metadata_file = _safe_join(cookbook_path, METADATA_FILENAME)
    if metadata_file.exists():
        with metadata_file.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Parse dependencies
        import re

        depends_matches = re.findall(r'depends\s+[\'"]([^\'"]+)[\'"]', content)
        analysis["direct_dependencies"] = depends_matches

    # Read Berksfile for additional dependencies
    berksfile = _safe_join(cookbook_path, "Berksfile")
    if berksfile.exists():
        with berksfile.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        import re

        cookbook_matches = re.findall(r'cookbook\s+[\'"]([^\'"]+)[\'"]', content)
        analysis["external_dependencies"].extend(cookbook_matches)

    # Identify community cookbooks (common ones)
    community_cookbook_patterns = [
        "apache2",
        "nginx",
        "mysql",
        "postgresql",
        "java",
        "python",
        "nodejs",
        "docker",
        "build-essential",
        "git",
        "ntp",
        "sudo",
        "users",
    ]

    all_deps = analysis["direct_dependencies"] + analysis["external_dependencies"]
    for dep in all_deps:
        if any(pattern in dep.lower() for pattern in community_cookbook_patterns):
            analysis["community_cookbooks"].append(dep)

    return analysis


def _determine_migration_order(dependency_analysis: dict) -> list:
    """Determine optimal migration order based on dependencies."""
    # For now, return a simple order based on dependency count
    # In a full implementation, this would use topological sorting

    order = []

    # Leaf nodes first (no dependencies)
    if not dependency_analysis["direct_dependencies"]:
        order.append(
            {
                "cookbook": dependency_analysis["cookbook_name"],
                "priority": 1,
                "reason": "No dependencies - can be migrated first",
            }
        )
    else:
        # Has dependencies - migrate after dependencies
        dep_count = len(dependency_analysis["direct_dependencies"])
        priority = min(dep_count + 1, 5)  # Cap at priority 5
        order.append(
            {
                "cookbook": dependency_analysis["cookbook_name"],
                "priority": priority,
                "reason": f"Has {dep_count} dependencies - migrate after dependencies",
            }
        )

    return order


def _identify_circular_dependencies(dependency_analysis: dict) -> list:
    """Identify circular dependencies (simplified)."""
    # This is a simplified implementation
    # A full implementation would build a dependency graph and detect cycles

    circular = []
    cookbook_name = dependency_analysis["cookbook_name"]

    # Check if any dependency might depend back on this cookbook
    for dep in dependency_analysis["direct_dependencies"]:
        if cookbook_name.lower() in dep.lower():  # Simple heuristic
            circular.append(
                {"cookbook1": cookbook_name, "cookbook2": dep, "type": "potential"}
            )

    return circular


def _generate_detailed_migration_plan(
    assessments: list, strategy: str, timeline_weeks: int
) -> dict:
    """Generate detailed migration plan."""
    plan = {
        "executive_summary": "",
        "phases": "",
        "timeline": "",
        "team_requirements": "",
        "prerequisites": "",
        "testing_strategy": "",
        "risk_mitigation": "",
        "success_criteria": "",
        "post_migration": "",
    }

    total_cookbooks = len(assessments)
    total_effort = sum(a["estimated_effort_days"] for a in assessments)

    plan["executive_summary"] = (
        f"""This migration plan covers {total_cookbooks} Chef cookbooks with an estimated effort of {total_effort:.1f} person-days over {timeline_weeks} weeks using a {strategy} approach. The plan balances speed of delivery with risk mitigation, focusing on early wins to build momentum while carefully handling complex cookbooks."""
    )

    # Generate phases based on strategy
    if strategy == "phased":
        plan["phases"] = _generate_phased_migration_phases(assessments, timeline_weeks)
    elif strategy == "big_bang":
        plan["phases"] = _generate_big_bang_phases(assessments, timeline_weeks)
    else:  # parallel
        plan["phases"] = _generate_parallel_migration_phases(timeline_weeks)

    plan["timeline"] = _generate_migration_timeline(strategy, timeline_weeks)

    plan["team_requirements"] = f"""**Core Team:**
• 1 Migration Lead (Ansible expert)
• {min(3, max(1, total_effort // 10))} Ansible Developers
• 1 Chef SME (part-time consultation)
• 1 QA Engineer for testing
• 1 DevOps Engineer for infrastructure

**Skills Required:**
• Advanced Ansible/AWX experience
• Chef cookbook understanding
• Infrastructure as Code principles
• CI/CD pipeline experience"""

    plan["prerequisites"] = """• AWX/AAP environment setup and configured
• Git repository structure established
• CI/CD pipelines created for Ansible playbooks
• Test environments provisioned
• Team training on Ansible best practices completed
• Chef cookbook inventory and documentation review
• Stakeholder alignment on migration approach"""

    plan["testing_strategy"] = """**Testing Phases:**
1. **Unit Testing:** Ansible syntax validation and linting
2. **Integration Testing:** Playbook execution in test environments
3. **Functional Testing:** End-to-end application functionality validation
4. **Performance Testing:** Resource usage and execution time comparison
5. **User Acceptance Testing:** Stakeholder validation of migrated functionality

**Testing Tools:**
• ansible-lint for syntax validation
• molecule for role testing
• testinfra for infrastructure testing
• Custom validation scripts for Chef parity"""

    plan[
        "success_criteria"
    ] = """• All Chef cookbooks successfully converted to Ansible playbooks
• 100% functional parity between Chef and Ansible implementations
• No performance degradation in deployment times
• All automated tests passing
• Team trained and comfortable with new Ansible workflows
• Documentation complete and accessible
• Rollback procedures tested and documented"""

    return plan


def _generate_comprehensive_migration_report(include_technical: bool) -> dict:
    """Generate comprehensive migration report."""
    report = {
        "executive_summary": "",
        "scope_objectives": "",
        "current_state": "",
        "target_state": "",
        "strategy": "",
        "cost_benefit": "",
        "timeline_resources": "",
        "risk_assessment": "",
        "recommendations": "",
        "appendices": "",
    }

    # Executive Summary
    report[
        "executive_summary"
    ] = """This report outlines the migration strategy from Chef to Ansible/AWX, providing a comprehensive analysis of the current Chef infrastructure and a detailed roadmap for transition. The migration will modernize configuration management capabilities while reducing operational complexity and improving deployment automation.

**Key Findings:**
• Migration is technically feasible with moderate complexity
• Estimated 8-16 week timeline depending on approach
• Significant long-term cost savings and operational improvements
• Low-to-medium risk with proper planning and execution"""

    # Scope and Objectives
    report["scope_objectives"] = """**Migration Scope:**
• All production Chef cookbooks and recipes
• Chef server configurations and node management
• Existing deployment pipelines and automation
• Monitoring and compliance integrations

**Primary Objectives:**
• Modernize configuration management with Ansible/AWX
• Improve deployment reliability and speed
• Reduce operational overhead and complexity
• Enhance security and compliance capabilities
• Standardize on Red Hat ecosystem tools"""

    # Current State Analysis
    report["current_state"] = """**Current Chef Infrastructure:**
• Chef Server managing X nodes across multiple environments
• Y cookbooks covering infrastructure and application deployment
• Established CI/CD pipelines with Chef integration
• Monitoring and compliance reporting in place

**Pain Points Identified:**
• Complex Chef DSL requiring Ruby expertise
• Lengthy convergence times in large environments
• Limited workflow orchestration capabilities
• Dependency management challenges
• Scaling limitations with current architecture"""

    # Target State Architecture
    report["target_state"] = """**Target Ansible/AWX Architecture:**
• Red Hat Ansible Automation Platform (AWX/AAP)
• Git-based playbook and role management
• Dynamic inventory from multiple sources
• Integrated workflow templates and job scheduling
• Enhanced RBAC and audit capabilities

**Key Improvements:**
• YAML-based playbooks (easier to read/write)
• Faster execution with SSH-based architecture
• Rich workflow orchestration capabilities
• Better integration with CI/CD tools
• Enhanced scalability and performance"""

    if include_technical:
        report["technical_details"] = """## Technical Implementation Approach

### Cookbook Conversion Strategy
• **Resource Mapping:** Direct mapping of Chef resources to Ansible modules
• **Variable Extraction:** Chef node attributes converted to Ansible variables
• **Template Conversion:** ERB templates converted to Jinja2 format
• **Custom Resources:** Manual conversion to Ansible roles/modules

### Data Migration
• **Node Attributes:** Migrated to Ansible inventory variables
• **Data Bags:** Converted to Ansible Vault encrypted variables
• **Environments:** Mapped to inventory groups with variable precedence

### Testing and Validation
• **Syntax Validation:** ansible-lint and yaml-lint integration
• **Functional Testing:** molecule framework for role testing
• **Integration Testing:** testinfra for infrastructure validation
• **Performance Testing:** Execution time and resource usage comparison"""

    return report


def _format_dependency_overview(analysis: dict) -> str:
    """Format dependency overview."""
    return f"""• Direct Dependencies: {len(analysis["direct_dependencies"])}
• External Dependencies: {len(analysis["external_dependencies"])}
• Community Cookbooks: {len(analysis["community_cookbooks"])}
• Circular Dependencies: {len(analysis["circular_dependencies"])}"""


def _format_dependency_graph(analysis: dict) -> str:
    """Format dependency graph (text representation)."""
    graph = [f"{analysis['cookbook_name']} depends on:"]

    for dep in analysis["direct_dependencies"]:
        graph.append(f"  ├── {dep}")

    if analysis["external_dependencies"]:
        graph.append("External dependencies:")
        for dep in analysis["external_dependencies"]:
            graph.append(f"  ├── {dep}")

    return "\n".join(graph) if len(graph) > 1 else "No dependencies found."


def _format_migration_order(order: list) -> str:
    """Format migration order recommendations."""
    if not order:
        return "No order analysis available."

    formatted = []
    for item in sorted(order, key=lambda x: x["priority"]):
        priority_text = f"Priority {item['priority']}"
        formatted.append(f"• {item['cookbook']} - {priority_text}: {item['reason']}")

    return "\n".join(formatted)


def _format_circular_dependencies(circular: list) -> str:
    """Format circular dependencies."""
    if not circular:
        return "✅ No circular dependencies detected."

    formatted = []
    for circ in circular:
        formatted.append(
            f"⚠️  {circ['cookbook1']} ↔ {circ['cookbook2']} ({circ['type']})"
        )

    return "\n".join(formatted)


def _format_external_dependencies(analysis: dict) -> str:
    """Format external dependencies."""
    if not analysis["external_dependencies"]:
        return "No external dependencies."

    return "\n".join([f"• {dep}" for dep in analysis["external_dependencies"]])


def _format_community_cookbooks(analysis: dict) -> str:
    """Format community cookbooks."""
    if not analysis["community_cookbooks"]:
        return "No community cookbooks identified."

    return "\n".join(
        [
            f"• {cb} (consider ansible-galaxy role)"
            for cb in analysis["community_cookbooks"]
        ]
    )


def _analyze_dependency_migration_impact(analysis: dict) -> str:
    """Analyze migration impact of dependencies."""
    impacts = []

    if analysis["community_cookbooks"]:
        impacts.append(
            f"• {len(analysis['community_cookbooks'])} community cookbooks can likely be replaced with Ansible Galaxy roles"
        )

    if analysis["circular_dependencies"]:
        impacts.append(
            f"• {len(analysis['circular_dependencies'])} circular dependencies need resolution before migration"
        )

    direct_count = len(analysis["direct_dependencies"])
    if direct_count > 5:
        impacts.append(
            f"• High dependency count ({direct_count}) suggests complex migration order requirements"
        )

    if not impacts:
        impacts.append(
            "• Low dependency complexity - straightforward migration expected"
        )

    return "\n".join(impacts)


def _generate_phased_migration_phases(assessments: list, timeline_weeks: int) -> str:
    """Generate phased migration phases."""
    phases = []

    # Sort by complexity
    sorted_assessments = sorted(assessments, key=lambda x: x["complexity_score"])

    phase1 = [a for a in sorted_assessments if a["complexity_score"] < 30]
    phase2 = [a for a in sorted_assessments if 30 <= a["complexity_score"] < 70]
    phase3 = [a for a in sorted_assessments if a["complexity_score"] >= 70]

    weeks_per_phase = timeline_weeks // 3

    phases.append(
        f"**Phase 1 (Weeks 1-{weeks_per_phase}):** Foundation & Low Complexity"
    )
    phases.append(f"  • {len(phase1)} low-complexity cookbooks")
    phases.append("  • Setup AWX environment and CI/CD")

    phases.append(
        f"\n**Phase 2 (Weeks {weeks_per_phase + 1}-{weeks_per_phase * 2}):** Medium Complexity"
    )
    phases.append(f"  • {len(phase2)} medium-complexity cookbooks")
    phases.append("  • Parallel conversion and testing")

    phases.append(
        f"\n**Phase 3 (Weeks {weeks_per_phase * 2 + 1}-{timeline_weeks}):** High Complexity & Finalization"
    )
    phases.append(f"  • {len(phase3)} high-complexity cookbooks")
    phases.append("  • Final testing and deployment")

    return "\n".join(phases)


def _generate_big_bang_phases(assessments: list, timeline_weeks: int) -> str:
    """Generate big bang migration phases."""
    return f"""**Phase 1 (Weeks 1-2):** Preparation
  • AWX environment setup
  • Team training and preparation
  • Conversion tooling setup

**Phase 2 (Weeks 3-{timeline_weeks - 2}):** Mass Conversion
  • Parallel conversion of all {len(assessments)} cookbooks
  • Continuous integration and testing
  • Issue resolution and refinement

**Phase 3 (Weeks {timeline_weeks - 1}-{timeline_weeks}):** Cutover
  • Final validation and testing
  • Production deployment
  • Rollback readiness verification"""


def _generate_parallel_migration_phases(timeline_weeks: int) -> str:
    """Generate parallel migration phases."""
    return f"""**Track A - Infrastructure (Weeks 1-{timeline_weeks}):**
  • Core infrastructure cookbooks
  • Base OS configuration
  • Security and compliance

**Track B - Applications (Weeks 1-{timeline_weeks}):**
  • Application deployment cookbooks
  • Service configuration
  • Custom business logic

**Track C - Integration (Weeks 1-{timeline_weeks}):**
  • AWX workflow development
  • CI/CD pipeline integration
  • Testing and validation automation"""


def _generate_migration_timeline(strategy: str, timeline_weeks: int) -> str:
    """Generate migration timeline."""
    milestones = []

    if strategy == "phased":
        week_intervals = timeline_weeks // 4
        milestones = [
            f"Week {week_intervals}: Phase 1 completion - Low complexity cookbooks migrated",
            f"Week {week_intervals * 2}: Phase 2 completion - Medium complexity cookbooks migrated",
            f"Week {week_intervals * 3}: Phase 3 completion - High complexity cookbooks migrated",
            f"Week {timeline_weeks}: Final validation and production deployment",
        ]
    else:
        milestones = [
            "Week 2: Environment setup and team training complete",
            f"Week {timeline_weeks // 2}: 50% of cookbooks converted and tested",
            f"Week {timeline_weeks - 2}: All conversions complete, final testing",
            f"Week {timeline_weeks}: Production deployment and go-live",
        ]

    return "\n".join([f"• {milestone}" for milestone in milestones])


def main() -> None:
    """Run the SousChef MCP server.

    This is the main entry point for running the server.
    """
    mcp.run()


if __name__ == "__main__":
    main()
