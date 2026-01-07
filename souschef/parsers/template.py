"""Chef ERB template parser and Jinja2 converter."""

import json
import re

from souschef.core.constants import (
    ERB_PATTERNS,
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
    JINJA2_VAR_REPLACEMENT,
    NODE_PREFIX,
    REGEX_ERB_OUTPUT,
    REGEX_RUBY_INTERPOLATION,
    REGEX_WORD_SYMBOLS,
)
from souschef.core.path_utils import _normalize_path

# Maximum length for variable names in ERB template parsing
MAX_VARIABLE_NAME_LENGTH = 100

# Maximum length for code block content in regex matching
MAX_CODE_BLOCK_LENGTH = 500


def parse_template(path: str) -> str:
    """
    Parse a Chef ERB template file and convert to Jinja2.

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

        return json.dumps(result, indent=2)

    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except UnicodeDecodeError:
        return f"Error: Unable to decode {path} as UTF-8 text"
    except Exception as e:
        return f"An error occurred: {e}"


def _strip_ruby_comments(content: str) -> str:
    """
    Remove Ruby comments from code.

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
    """
    Extract variables from <%= %> output tags.

    Args:
        content: Raw ERB template content.
        variables: Set to add found variables to (modified in place).

    """
    output_vars = re.findall(REGEX_ERB_OUTPUT, content)
    for var in output_vars:
        var = var.strip()
        if var.startswith(NODE_PREFIX):
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
    """
    Extract attribute path from a node reference.

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
    """
    Extract variables from Ruby string interpolation.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    interpolated = re.findall(REGEX_RUBY_INTERPOLATION, code)
    for expr in interpolated:
        var_match = re.match(REGEX_WORD_SYMBOLS, expr.strip())
        if var_match:
            variables.add(var_match.group())


def _extract_node_attributes(code: str, variables: set[str]) -> None:
    """
    Extract node attribute references from code.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    if NODE_PREFIX in code:
        node_matches = re.finditer(r"node\[.+\]", code)
        for match in node_matches:
            attr_path = _extract_node_attribute_path(match.group())
            if attr_path:
                variables.add(attr_path)


def _extract_conditional_variables(code: str, variables: set[str]) -> None:
    """
    Extract variables from conditional statements.

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
    """
    Extract variables from .each iterators.

    Args:
        code: Code block content.
        variables: Set to add found variables to (modified in place).

    """
    if ".each" in code:
        match = re.search(
            rf"(\w{{1,{MAX_VARIABLE_NAME_LENGTH}}})\.each\s+do\s+\|"
            rf"(\w{{1,{MAX_VARIABLE_NAME_LENGTH}}})\|",
            code,
        )
        if match:
            variables.add(match.group(1))  # Array variable
            variables.add(match.group(2))  # Iterator variable


def _extract_code_block_variables(content: str, variables: set[str]) -> None:
    """
    Extract variables from <% %> code blocks.

    Args:
        content: Raw ERB template content.
        variables: Set to add found variables to (modified in place).

    """
    code_blocks = re.findall(
        rf"<%\s+([^%]{{1,{MAX_CODE_BLOCK_LENGTH}}}?)\s+%>", content, re.DOTALL
    )
    for code in code_blocks:
        _extract_interpolated_variables(code, variables)
        _extract_node_attributes(code, variables)
        _extract_conditional_variables(code, variables)
        _extract_iterator_variables(code, variables)


def _extract_template_variables(content: str) -> set[str]:
    """
    Extract all variables used in an ERB template.

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
    """
    Convert ERB template syntax to Jinja2.

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
    result = re.sub(r"\{\{\s*@(\w+)\s*\}\}", JINJA2_VAR_REPLACEMENT, result)
    # Clean up @var in conditionals and other control structures
    result = re.sub(r"@(\w+)", r"\1", result)

    return result


def _extract_heredoc_strings(content: str) -> dict[str, str]:
    """
    Extract heredoc strings from Ruby code.

    Args:
        content: Ruby code content.

    Returns:
        Dictionary mapping heredoc markers to their content.

    """
    heredocs = {}
    # Match heredoc patterns: <<-MARKER or <<MARKER
    heredoc_pattern = r"<<-?(\w+)\s*\n((?:(?!^\s*\1\s*$).)*?)^\s*\1\s*$"
    for match in re.finditer(heredoc_pattern, content, re.DOTALL | re.MULTILINE):
        marker = match.group(1)
        content_text = match.group(2)
        heredocs[marker] = content_text
    return heredocs
