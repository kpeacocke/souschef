"""Chef Habitat plan parser."""

import json
import re
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import _normalize_path

# Maximum length for variable values in Habitat plan parsing
# Prevents ReDoS attacks from extremely long variable assignments
MAX_PLAN_VALUE_LENGTH = 10000


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
    try:
        normalized_path = _normalize_path(plan_path)
        if not normalized_path.exists():
            return ERROR_FILE_NOT_FOUND.format(path=normalized_path)
        if normalized_path.is_dir():
            return ERROR_IS_DIRECTORY.format(path=normalized_path)

        content = normalized_path.read_text(encoding="utf-8")
        metadata: dict[str, Any] = {
            "package": {},
            "dependencies": {"build": [], "runtime": []},
            "ports": [],
            "binds": [],
            "service": {},
            "callbacks": {},
        }

        # Extract package info
        metadata["package"]["name"] = _extract_plan_var(content, "pkg_name")
        metadata["package"]["origin"] = _extract_plan_var(content, "pkg_origin")
        metadata["package"]["version"] = _extract_plan_var(content, "pkg_version")
        metadata["package"]["maintainer"] = _extract_plan_var(content, "pkg_maintainer")
        metadata["package"]["license"] = _extract_plan_array(content, "pkg_license")
        metadata["package"]["description"] = _extract_plan_var(
            content, "pkg_description"
        )
        metadata["package"]["upstream_url"] = _extract_plan_var(
            content, "pkg_upstream_url"
        )
        metadata["package"]["source"] = _extract_plan_var(content, "pkg_source")

        # Extract dependencies
        metadata["dependencies"]["build"] = _extract_plan_array(
            content, "pkg_build_deps"
        )
        metadata["dependencies"]["runtime"] = _extract_plan_array(content, "pkg_deps")

        # Extract ports and bindings
        metadata["ports"] = _extract_plan_exports(content, "pkg_exports")
        metadata["binds"] = _extract_plan_exports(content, "pkg_binds_optional")

        # Extract service config
        metadata["service"]["run"] = _extract_plan_var(content, "pkg_svc_run")
        metadata["service"]["user"] = _extract_plan_var(content, "pkg_svc_user")
        metadata["service"]["group"] = _extract_plan_var(content, "pkg_svc_group")

        # Extract callbacks
        for callback in ["do_build", "do_install", "do_init", "do_setup_environment"]:
            callback_content = _extract_plan_function(content, callback)
            if callback_content:
                metadata["callbacks"][callback] = callback_content

        return json.dumps(metadata, indent=2)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=plan_path)
    except Exception as e:
        return f"Error parsing Habitat plan: {e}"


def _extract_plan_var(content: str, var_name: str) -> str:
    """
    Extract a variable value from a Habitat plan.

    This helper supports both quoted and unquoted assignments and allows
    escaped quotes within quoted values. If the variable is not found,
    an empty string is returned.

    Args:
        content: Full text of the Habitat plan.
        var_name: Name of the variable to extract.

    Returns:
        The extracted variable value, or an empty string if not present.

    """
    # First, try to match a quoted value (single or double quotes), allowing
    # escaped characters (e.g. \" or \') inside the value. We anchor at the
    # start of the line to avoid partial matches elsewhere.
    # Use a bounded, non-greedy quantifier to prevent ReDoS on malformed input.
    quoted_pattern = (
        rf'^{re.escape(var_name)}=(["\'])'
        rf"(?P<value>(?:\\.|(?!\1).){{0,{MAX_PLAN_VALUE_LENGTH}}}?)\1"
    )
    match = re.search(quoted_pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group("value").strip()

    # Fallback: match an unquoted value up to the end of the line or a comment.
    unquoted_pattern = rf"^{re.escape(var_name)}=([^\n#]+)"
    match = re.search(unquoted_pattern, content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_plan_array(content: str, var_name: str) -> list[str]:
    """Extract an array variable from a Habitat plan."""
    # Find the start of the array declaration
    pattern = rf"{var_name}=\("
    match = re.search(pattern, content)
    if not match:
        return []

    # Manually parse to handle nested parentheses correctly
    start_pos = match.end()
    paren_count = 1
    end_pos = start_pos

    # Find the matching closing parenthesis
    while end_pos < len(content) and paren_count > 0:
        if content[end_pos] == "(":
            paren_count += 1
        elif content[end_pos] == ")":
            paren_count -= 1
        end_pos += 1

    if paren_count != 0:
        # Unmatched parentheses
        return []

    # Extract the content between parentheses (excluding the final closing paren)
    array_content = content[start_pos : end_pos - 1]

    # Split by newlines and process each line
    elements = []
    for line in array_content.strip().split("\n"):
        # Remove inline comments
        line = line.split("#")[0].strip()
        if not line:
            continue

        # Remove quotes and whitespace
        line = line.strip("\"'").strip()
        if line:
            elements.append(line)

    return elements


def _extract_plan_exports(content: str, var_name: str) -> list[dict[str, str]]:
    """Extract port exports or bindings from a Habitat plan."""
    # Find the start of the array declaration
    pattern = rf"{var_name}=\("
    match = re.search(pattern, content)
    if not match:
        return []

    # Manually parse to handle nested parentheses correctly
    start_pos = match.end()
    paren_count = 1
    end_pos = start_pos

    # Find the matching closing parenthesis
    while end_pos < len(content) and paren_count > 0:
        if content[end_pos] == "(":
            paren_count += 1
        elif content[end_pos] == ")":
            paren_count -= 1
        end_pos += 1

    if paren_count != 0:
        # Unmatched parentheses
        return []

    # Extract the content between parentheses (excluding the final closing paren)
    exports_content = content[start_pos : end_pos - 1]

    exports = []
    for line in exports_content.strip().split("\n"):
        export_match = re.search(r"\[([^\]]+)\]=([^\s]+)", line)
        if export_match:
            exports.append(
                {"name": export_match.group(1), "value": export_match.group(2)}
            )
    return exports


def _update_quote_state(
    ch: str,
    in_single_quote: bool,
    in_double_quote: bool,
    in_backtick: bool,
    escape_next: bool,
) -> tuple[bool, bool, bool, bool]:
    """Update quote tracking state for shell script parsing."""
    if escape_next:
        return in_single_quote, in_double_quote, in_backtick, False

    if ch == "\\":
        return in_single_quote, in_double_quote, in_backtick, True

    if ch == "'" and not in_double_quote and not in_backtick:
        return not in_single_quote, in_double_quote, in_backtick, False
    if ch == '"' and not in_single_quote and not in_backtick:
        return in_single_quote, not in_double_quote, in_backtick, False
    if ch == "`" and not in_single_quote and not in_double_quote:
        return in_single_quote, in_double_quote, not in_backtick, False

    return in_single_quote, in_double_quote, in_backtick, False


def _extract_plan_function(content: str, func_name: str) -> str:
    """
    Extract a shell function body from a Habitat plan.

    Uses brace counting to handle nested braces in conditionals and loops.

    Args:
        content: Full text of the Habitat plan.
        func_name: Name of the function to extract.

    Returns:
        The function body as a string, or an empty string if the function
        is not found or is malformed.

    """
    # Find the start of the function definition: func_name() {
    func_def_pattern = rf"{re.escape(func_name)}\s*\(\)\s*{{"
    match = re.search(func_def_pattern, content)
    if not match:
        return ""

    start_index = match.end()
    brace_count = 1
    i = start_index

    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    escape_next = False

    while i < len(content):
        ch = content[i]

        # Update quote/escape state
        (
            in_single_quote,
            in_double_quote,
            in_backtick,
            escape_next,
        ) = _update_quote_state(
            ch, in_single_quote, in_double_quote, in_backtick, escape_next
        )

        # Count braces only when not inside quotes
        if not (in_single_quote or in_double_quote or in_backtick):
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    body = content[start_index:i]
                    return body.strip("\n").strip()

        i += 1

    # Unbalanced braces or malformed definition
    return ""
