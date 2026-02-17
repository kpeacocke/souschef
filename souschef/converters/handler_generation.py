"""
V2.2: Enhanced Chef handler to Ansible handler conversion.

Converts Chef handler classes (in libraries/) to Ansible error handlers and
notification routing. Supports custom handlers, exception handlers, and
callbacks.

This module provides comprehensive handler pattern detection and conversion,
going beyond simple notification mapping to handle complex handler scenarios.
"""

import re
from typing import Any

# Regex patterns for handler parsing
CLASS_PATTERN = r"class\s+(\w+)\s*<\s*(\S+)"
METHOD_PATTERN = r"def\s+(\w+)\s*(?:\([^)]*\))?\s*(?:;)?\s*(?:#.*)?"
ATTR_PATTERN = r"attr_(?:reader|writer|accessor)\s+:(\w+)"
RESCUE_PATTERN = r"rescue\s+(\w+)\s*(?:=>|,)?\s*(\w+)?"


def _extract_handler_class_info(handler_content: str) -> tuple[str, str]:
    """Extract handler class name and parent class."""
    class_match = re.search(CLASS_PATTERN, handler_content)
    if class_match:
        return class_match.group(1), class_match.group(2)
    return "", ""


def _determine_handler_type(parent_class: str) -> str:
    """Determine handler type based on parent class."""
    if "Chef::Handler" in parent_class:
        return "exception_handler"
    if "Chef::Report::Handler" in parent_class:
        return "report_handler"
    if "Chef::Event::Handler" in parent_class:
        return "event_handler"
    return "unknown"


def _extract_methods_and_callbacks(
    handler_content: str,
) -> tuple[list[str], list[str]]:
    """Extract method names and categorise callbacks."""
    methods: list[str] = []
    callbacks: list[str] = []

    for match in re.finditer(METHOD_PATTERN, handler_content, re.MULTILINE):
        method_name = match.group(1)
        methods.append(method_name)

        # Categorise methods by name
        if method_name in ["report", "report_run"]:
            callbacks.append("end_of_converge")
        elif method_name in ["exception", "exception_encountered"]:
            callbacks.append("converge_failed")

    return methods, callbacks


def _extract_attributes(handler_content: str) -> list[str]:
    """Extract attributed from handler class."""
    attributes: list[str] = []
    for match in re.finditer(ATTR_PATTERN, handler_content):
        attributes.append(match.group(1))
    return attributes


def _extract_exceptions(handler_content: str) -> list[str]:
    """Extract exception handling patterns."""
    exceptions: list[str] = []
    for match in re.finditer(RESCUE_PATTERN, handler_content):
        exception_type = match.group(1)
        if exception_type not in ["=>", ",:"]:
            exceptions.append(exception_type)
    return exceptions


def parse_chef_handler_class(handler_content: str) -> dict[str, Any]:
    """
    Parse Chef handler class definition.

    Extracts handler name, parent class, and methods from Chef handler code.

    Args:
        handler_content: The handler class code (Ruby).

    Returns:
        Dictionary with handler metadata (name, type, methods, attributes).

    """
    handler_name, parent_class = _extract_handler_class_info(handler_content)
    methods, callbacks = _extract_methods_and_callbacks(handler_content)
    attributes = _extract_attributes(handler_content)
    exceptions = _extract_exceptions(handler_content)

    handler_info: dict[str, Any] = {
        "name": handler_name,
        "type": _determine_handler_type(parent_class),
        "parent_class": parent_class,
        "methods": methods,
        "attributes": attributes,
        "exceptions_handled": exceptions,
        "callbacks": callbacks,
    }

    return handler_info


def detect_handler_patterns(recipe_content: str) -> list[dict[str, Any]]:
    """
    Detect handler patterns in recipe content.

    Identifies where handlers are registered or used in recipes.

    Args:
        recipe_content: The recipe code.

    Returns:
        List of handler usage patterns.

    """
    patterns: list[dict[str, Any]] = []

    # Pattern 1: run_context.exception_handlers.register(HandlerClass.new)
    register_pattern = (
        r"run_context\.exception_handlers\.register\s*\(\s*(\w+)\.new\s*\)"
    )
    for match in re.finditer(register_pattern, recipe_content):
        patterns.append(
            {
                "pattern": "exception_handler_registration",
                "handler_class": match.group(1),
                "location": match.start(),
            }
        )

    # Pattern 2: notifies with delayed/immediately timing
    notifies_pattern = r"notifies\s+:(\w+),\s*['\"]([^[]+)\[([^\]]+)\]['\"],\s*:(\w+)"
    for match in re.finditer(notifies_pattern, recipe_content):
        patterns.append(
            {
                "pattern": "notification_handler",
                "action": match.group(1),
                "resource_type": match.group(2),
                "resource_name": match.group(3),
                "timing": match.group(4),
                "location": match.start(),
            }
        )

    # Pattern 3: rescue blocks handling exceptions
    rescue_pattern = r"rescue\s+(\w+)\s*(?:=>|,)?\s*(\w+)?"
    for match in re.finditer(rescue_pattern, recipe_content):
        patterns.append(
            {
                "pattern": "rescue_handler",
                "exception_type": match.group(1),
                "variable": match.group(2),
                "location": match.start(),
            }
        )

    # Pattern 4: log with level (info, warn, error)
    log_pattern = r"Chef::Log\.(\w+)\s*\(\s*['\"](.+?)['\"]"
    for match in re.finditer(log_pattern, recipe_content):
        patterns.append(
            {
                "pattern": "log_handler",
                "level": match.group(1),
                "message": match.group(2),
                "location": match.start(),
            }
        )

    return patterns


def generate_ansible_handler_from_chef(
    handler_info: dict[str, Any],
) -> str:
    """
    Generate Ansible handler configuration from Chef handler metadata.

    Creates Ansible handler blocks that replicate Chef handler behaviour.

    Args:
        handler_info: Chef handler metadata from parse_chef_handler_class.

    Returns:
        YAML string with Ansible handler definition.

    """
    handler_name = handler_info.get("name", "unknown")
    handler_type = handler_info.get("type", "unknown")
    callbacks = handler_info.get("callbacks", [])

    yaml_output = f"# Chef handler '{handler_name}' (type: {handler_type})\n"
    yaml_output += "# Converted from Chef to Ansible\n"
    yaml_output += "handlers:\n"
    yaml_output += f"  - name: {handler_name}_handler\n"
    yaml_output += "    listen: "

    # Map Chef callbacks to Ansible handler listen events
    if callbacks:
        yaml_output += f"'{', '.join(callbacks)}'\n"
    else:
        yaml_output += "'default_handler'\n"

    # Add handler block
    yaml_output += "    # Handler implementation\n"
    yaml_output += "    block:\n"
    yaml_output += f"      - name: Execute {handler_name}\n"
    yaml_output += "        debug:\n"
    yaml_output += f"          msg: 'Handler {handler_name} triggered'\n"

    # Add exception handling if present
    if handler_info.get("exceptions_handled"):
        yaml_output += "      rescue:\n"
        yaml_output += f"      - name: Handle exception in {handler_name}\n"
        yaml_output += "        debug:\n"
        yaml_output += f"          msg: 'Exception occurred in {handler_name}'\n"

    return yaml_output


def build_handler_routing_table(
    patterns: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build notification routing table from handler patterns.

    Creates a map of which handlers should respond to which events.

    Args:
        patterns: List of handler patterns from detect_handler_patterns.

    Returns:
        Routing table with event-to-handler mappings.

    """
    routing: dict[str, Any] = {
        "event_routes": {},
        "exception_routes": {},
        "notification_routes": {},
        "summary": {
            "total_patterns": len(patterns),
            "exception_handlers": 0,
            "notification_handlers": 0,
            "rescue_handlers": 0,
            "log_handlers": 0,
        },
    }

    for pattern in patterns:
        pattern_type = pattern.get("pattern")

        if pattern_type == "exception_handler_registration":
            handler_class = pattern.get("handler_class", "unknown")
            if "exception_routes" in routing:
                routing["exception_routes"][handler_class] = {
                    "event": "converge_failed",
                    "handler": handler_class,
                }
            routing["summary"]["exception_handlers"] += 1

        elif pattern_type == "notification_handler":
            resource_type = pattern.get("resource_type", "unknown")
            action = pattern.get("action", "unknown")
            timing = pattern.get("timing", "delayed")

            route_key = f"{resource_type}[{action}]"
            routing["notification_routes"][route_key] = {
                "listener": action,
                "timing": timing,
                "ansible_equivalent": "notify" if timing == "immediately" else "listen",
            }
            routing["summary"]["notification_handlers"] += 1

        elif pattern_type == "rescue_handler":
            exception_type = pattern.get("exception_type", "StandardError")
            routing["exception_routes"][exception_type] = {
                "event": "exception_caught",
                "exception": exception_type,
            }
            routing["summary"]["rescue_handlers"] += 1

        elif pattern_type == "log_handler":
            level = pattern.get("level", "info")
            routing["event_routes"][level] = {
                "listener": f"log_{level}",
                "action": "debug",
            }
            routing["summary"]["log_handlers"] += 1

    return routing


def generate_handler_conversion_report(
    handler_path: str,
    handler_info: dict[str, Any],
    routing: dict[str, Any],
) -> str:
    """
    Generate comprehensive handler conversion report.

    Provides analysis and recommendations for handler migration.

    Args:
        handler_path: Path to the original Chef handler file.
        handler_info: Handler metadata.
        routing: Handler routing table.

    Returns:
        Markdown-formatted conversion report.

    """
    report = "# Handler Conversion Report\n\n"
    report += f"**Source File**: {handler_path}\n"
    report += f"**Handler Name**: {handler_info.get('name', 'unknown')}\n"
    report += f"**Handler Type**: {handler_info.get('type', 'unknown')}\n"
    report += f"**Parent Class**: {handler_info.get('parent_class', 'unknown')}\n\n"

    # Method summary
    methods = handler_info.get("methods", [])
    report += f"## Methods ({len(methods)})\n"
    for method in methods:
        report += f"- `{method}()`\n"

    # Attributes
    attributes = handler_info.get("attributes", [])
    if attributes:
        report += f"\n## Attributes ({len(attributes)})\n"
        for attr in attributes:
            report += f"- `{attr}`\n"

    # Exceptions handled
    exceptions = handler_info.get("exceptions_handled", [])
    if exceptions:
        report += f"\n## Exceptions Handled ({len(exceptions)})\n"
        for exc in exceptions:
            report += f"- `{exc}`\n"

    # Callbacks
    callbacks = handler_info.get("callbacks", [])
    report += f"\n## Callbacks ({len(callbacks)})\n"
    if callbacks:
        for callback in callbacks:
            report += f"- {callback}\n"
    else:
        report += "- (none detected)\n"

    # Routing summary
    report += "\n## Handler Routing\n"
    summary = routing.get("summary", {})
    report += f"- Total patterns detected: {summary.get('total_patterns', 0)}\n"
    report += f"- Exception handlers: {summary.get('exception_handlers', 0)}\n"
    report += f"- Notification handlers: {summary.get('notification_handlers', 0)}\n"
    report += f"- Rescue handlers: {summary.get('rescue_handlers', 0)}\n"
    report += f"- Log handlers: {summary.get('log_handlers', 0)}\n"

    # Conversion recommendations
    report += "\n## Conversion Recommendations\n"
    if handler_info.get("type") == "exception_handler":
        report += "1. Convert to Ansible error handler block\n"
        report += "2. Use rescue/failed_when conditionals\n"
        report += "3. Map callbacks to Ansible callback plugins\n"
    elif handler_info.get("type") == "report_handler":
        report += "1. Convert to Ansible report/callback plugin\n"
        report += "2. Create custom callback plugin if needed\n"
    else:
        report += "1. Create equivalent Ansible handler block\n"
        report += "2. Register with notify/listen patterns\n"

    report += "\n## Ansible Conversion Output\n"
    report += "```yaml\n"
    report += generate_ansible_handler_from_chef(handler_info)
    report += "```\n"

    return report
