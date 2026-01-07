"""
Habitat plan to Docker/Compose conversion.

This module provides tools to convert Chef Habitat plans to Dockerfiles
and Docker Compose configurations.
"""

import json
import re
import shlex
from pathlib import Path
from typing import Any

from souschef.core.constants import ERROR_PREFIX
from souschef.core.path_utils import _normalize_path
from souschef.parsers.habitat import parse_habitat_plan


def convert_habitat_to_dockerfile(
    plan_path: str, base_image: str = "ubuntu:22.04"
) -> str:
    """
    Convert a Chef Habitat plan to a Dockerfile.

    Creates a Dockerfile that replicates Habitat plan configuration.

    Security Warning: This tool processes shell commands from Habitat plans
    and includes them in the generated Dockerfile. Only use with trusted
    Habitat plans from known sources. Review generated Dockerfiles before
    building images, especially if the plan source is untrusted.

    Args:
        plan_path: Path to the plan.sh file.
        base_image: Base Docker image (default: ubuntu:22.04).

    Returns:
        Dockerfile content as a string.

    """
    try:
        # Validate and normalize path to prevent path traversal
        try:
            normalized_path = _normalize_path(plan_path)
            validated_path = str(normalized_path)
        except ValueError as e:
            return f"Invalid path {plan_path}: {e}"

        plan_json: str = parse_habitat_plan(validated_path)
        if plan_json.startswith(ERROR_PREFIX):
            return plan_json
        plan: dict[str, Any] = json.loads(plan_json)
        lines = _build_dockerfile_header(plan, validated_path, base_image)
        _add_dockerfile_deps(lines, plan)
        _add_dockerfile_build(lines, plan)
        _add_dockerfile_runtime(lines, plan)
        return "\n".join(lines)
    except Exception as e:
        return f"Error converting Habitat plan to Dockerfile: {e}"


def generate_compose_from_habitat(
    plan_paths: str, network_name: str = "habitat_net"
) -> str:
    """
    Generate docker-compose.yml from Habitat plans.

    Creates Docker Compose configuration for multiple services.

    Args:
        plan_paths: Comma-separated paths to plan.sh files.
        network_name: Docker network name.

    Returns:
        docker-compose.yml content.

    """
    try:
        # Validate network_name to prevent YAML injection
        if not _validate_docker_network_name(network_name):
            return (
                f"Invalid Docker network name: {network_name}. "
                "Expected format: alphanumeric with hyphens, underscores, or dots"
            )

        paths = [p.strip() for p in plan_paths.split(",")]
        # Validate and normalize all paths to prevent path traversal
        validated_paths = []
        for path_str in paths:
            try:
                normalized = _normalize_path(path_str)
                validated_paths.append(str(normalized))
            except ValueError as e:
                return f"Invalid path {path_str}: {e}"

        services: dict[str, Any] = {}
        for plan_path in validated_paths:
            plan_json = parse_habitat_plan(plan_path)
            if plan_json.startswith(ERROR_PREFIX):
                return f"Error parsing {plan_path}: {plan_json}"
            plan: dict[str, Any] = json.loads(plan_json)
            pkg_name = plan["package"].get("name", "unknown")
            service = _build_compose_service(plan, pkg_name)
            service["networks"] = [network_name]
            services[pkg_name] = service
        return _format_compose_yaml(services, network_name)
    except Exception as e:
        return f"Error generating docker-compose.yml: {e}"


# Dependency mapping


def _map_habitat_deps_to_apt(habitat_deps: list[str]) -> list[str]:
    """
    Map Habitat package dependencies to apt package names.

    Args:
        habitat_deps: List of Habitat package identifiers
            (e.g., 'core/gcc', 'custom/org/package').

    Returns:
        List of apt package names. Unknown dependencies are included with
        basic validation.

    """
    dep_mapping = {
        "core/gcc": "gcc",
        "core/make": "make",
        "core/openssl": "libssl-dev",
        "core/pcre": "libpcre3-dev",
        "core/zlib": "zlib1g-dev",
        "core/glibc": "libc6-dev",
        "core/readline": "libreadline-dev",
        "core/curl": "curl",
        "core/wget": "wget",
        "core/git": "git",
        "core/python": "python3",
        "core/ruby": "ruby",
        "core/perl": "perl",
    }
    apt_packages = []
    for dep in habitat_deps:
        if not dep or not dep.strip():
            continue

        dep = dep.strip()

        # Check known mappings first
        if dep in dep_mapping:
            apt_packages.append(dep_mapping[dep])
        elif "/" in dep:
            # Extract package name from Habitat identifier
            # (e.g., 'core/gcc' -> 'gcc')
            # For multi-segment paths like 'custom/org/package',
            # take the last component
            pkg_name = dep.split("/")[-1]

            # Basic validation: package name should be alphanumeric with
            # hyphens/underscores
            if pkg_name and re.match(
                r"^[a-z0-9][a-z0-9._+-]*$", pkg_name, re.IGNORECASE
            ):
                apt_packages.append(pkg_name)
            # If invalid, skip but don't fail - let apt handle the error later
        else:
            # Dependency without slash - might be a direct apt package name
            # Validate it looks like a package name before including
            if re.match(r"^[a-z0-9][a-z0-9._+-]*$", dep, re.IGNORECASE):
                apt_packages.append(dep)

    return apt_packages


def _extract_default_port(port_name: str) -> str:
    """Extract default port number based on common port names."""
    port_defaults = {
        "http": "80",
        "https": "443",
        "port": "8080",
        "ssl-port": "443",
        "postgresql": "5432",
        "mysql": "3306",
        "redis": "6379",
        "mongodb": "27017",
    }
    if port_name in port_defaults:
        return port_defaults[port_name]
    for key, value in port_defaults.items():
        if key in port_name.lower():
            return value
    return ""


# Validation functions


def _validate_docker_network_name(network_name: str) -> bool:
    """
    Validate Docker network name format.

    Validates that network_name matches expected Docker naming patterns to
    prevent YAML injection or malformed compose files.

    Args:
        network_name: Docker network name to validate.

    Returns:
        True if valid, False otherwise.

    """
    if not network_name or not isinstance(network_name, str):
        return False

    # Docker network names must:
    # - Start with alphanumeric character
    # - Contain only alphanumeric, hyphens, underscores, or dots
    # - Not contain spaces or special characters that could break YAML

    # Pattern: starts with alphanumeric, followed by
    # alphanumeric/hyphen/underscore/dot
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$"

    if not re.match(pattern, network_name):
        return False

    # Reject dangerous characters that could break YAML structure
    dangerous_chars = [
        "\n",
        "\r",
        ":",
        "[",
        "]",
        "{",
        "}",
        "#",
        "|",
        ">",
        "&",
        "*",
        "!",
        "%",
        "@",
    ]
    if any(char in network_name for char in dangerous_chars):
        return False

    # Validate reasonable length (Docker network names should be < 64 chars)
    return len(network_name) <= 63


def _validate_docker_image_name(base_image: str) -> bool:
    """
    Validate Docker image name format.

    Validates that base_image matches expected Docker image format to prevent
    Dockerfile injection or malformed content.

    Args:
        base_image: Docker image name to validate.

    Returns:
        True if valid, False otherwise.

    """
    if not base_image or not isinstance(base_image, str):
        return False

    # Docker image format: [registry/][namespace/]repository[:tag|@digest]
    # Examples: ubuntu:22.04, docker.io/library/nginx:latest,
    # myregistry.com:5000/myimage:v1
    # Allow alphanumeric, hyphens, underscores, dots, colons
    # (only in specific positions), slashes, and @ for digests.
    # Reject shell metacharacters.

    # Pattern breakdown:
    # - Optional registry (with optional port), must be followed by a slash:
    #   [hostname[:port]/]
    #   - Hostname allows dots: "myregistry.com", "registry.local"
    # - One or more repository path components (may include namespaces):
    #   [namespace/]*repository
    #   - Path components do not contain colons
    # - Optional tag or digest at the end: [:tag] or [@sha256:digest]
    pattern = (
        r"^"
        # Optional registry (with optional port), must be followed by a slash.
        r"(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9_-]*[a-zA-Z0-9])?"
        r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9_-]*[a-zA-Z0-9])?)*"
        r"(?::\d+)?)/)?"
        # Repository path components (one or more), no colons here.
        r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?"
        r"(?:/[a-zA-Z0-9](?:[a-zA-Z0-9._-]*[a-zA-Z0-9])?)*)"
        # Optional tag or digest at the end.
        r"(?::[a-zA-Z0-9._-]+|@sha256:[a-fA-F0-9]{64})?"
        r"$"
    )

    if not re.match(pattern, base_image):
        return False

    # Additional safety checks: reject dangerous characters
    dangerous_chars = ["\n", "\r", ";", "|", "&", "$", "`", "(", ")", "<", ">", "\\"]
    if any(char in base_image for char in dangerous_chars):
        return False

    # Validate reasonable length (Docker image names are typically < 256 chars)
    return len(base_image) <= 256


# Dockerfile generation


def _add_dockerfile_label(
    lines: list[str], label_name: str, label_value: str | None
) -> None:
    """
    Add a LABEL to Dockerfile lines with validation.

    Args:
        lines: List of Dockerfile lines to append to.
        label_name: Name of the label (e.g., 'maintainer', 'version').
        label_value: Value for the label, or None if not present.

    """
    if not label_value:
        return

    # Validate no newlines that would break Dockerfile syntax
    if "\n" in label_value or "\r" in label_value:
        lines.append(
            f"# WARNING: {label_name.title()} field contains newlines, omitting LABEL"
        )
    else:
        # Use json.dumps to properly escape quotes and special characters
        escaped_value = json.dumps(label_value)
        lines.append(f"LABEL {label_name}={escaped_value}")


def _build_dockerfile_header(
    plan: dict[str, Any], plan_path: str, base_image: str
) -> list[str]:
    """
    Build Dockerfile header with metadata.

    Args:
        plan: Parsed Habitat plan dictionary.
        plan_path: Path to the plan.sh file.
        base_image: Base Docker image name (validated).

    Returns:
        List of Dockerfile header lines.

    Raises:
        ValueError: If base_image format is invalid.

    """
    # Validate base_image to prevent Dockerfile injection
    if not _validate_docker_image_name(base_image):
        raise ValueError(
            f"Invalid Docker image name: {base_image}. "
            "Expected format: [registry/]repository[:tag]"
        )

    lines = [
        "# Dockerfile generated from Habitat plan",
        f"# Original plan: {Path(plan_path).name}",
        (
            f"# Package: {plan['package'].get('origin', 'unknown')}/"
            f"{plan['package'].get('name', 'unknown')}"
        ),
        f"# Version: {plan['package'].get('version', 'unknown')}",
        "",
        f"FROM {base_image}",
        "",
    ]
    _add_dockerfile_label(lines, "maintainer", plan["package"].get("maintainer"))
    _add_dockerfile_label(lines, "version", plan["package"].get("version"))
    _add_dockerfile_label(lines, "description", plan["package"].get("description"))
    if lines[-1].startswith("LABEL"):
        lines.append("")
    return lines


def _add_dockerfile_deps(lines: list[str], plan: dict[str, Any]) -> None:
    """Add dependency installation to Dockerfile."""
    if plan["dependencies"]["build"] or plan["dependencies"]["runtime"]:
        lines.append("# Install dependencies")
        all_deps = set(plan["dependencies"]["build"] + plan["dependencies"]["runtime"])
        apt_packages = _map_habitat_deps_to_apt(list(all_deps))
        if apt_packages:
            safe_apt_packages = [shlex.quote(pkg) for pkg in apt_packages]
            lines.append("RUN apt-get update && \\")
            lines.append(f"    apt-get install -y {' '.join(safe_apt_packages)} && \\")
            lines.append("    rm -rf /var/lib/apt/lists/*")
            lines.append("")


def _process_callback_lines(
    callback_content: str, replace_vars: bool = False
) -> list[str]:
    """
    Process callback lines for Dockerfile.

    Security Note: This function processes shell commands from Habitat plans
    and embeds them directly into Dockerfile RUN commands. Only use this
    with trusted Habitat plans from known sources. Malicious commands in
    untrusted plans will be executed during Docker image builds.

    Args:
        callback_content: Raw callback content to process.
        replace_vars: Whether to replace Habitat variables with paths.

    Returns:
        List of processed RUN commands.

    """
    processed = []
    # Patterns that might indicate malicious or dangerous commands
    dangerous_patterns = [
        r"curl.*\|.*sh",  # Piping curl to shell
        r"wget.*\|.*sh",  # Piping wget to shell
        r"eval",  # eval commands
        r"\$\(curl",  # Command substitution with curl
        r"\$\(wget",  # Command substitution with wget
    ]

    for line in callback_content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Perform variable replacement BEFORE validation
            if replace_vars:
                line = (
                    line.replace("$pkg_prefix", "/usr/local")
                    .replace("$pkg_svc_config_path", "/etc/app")
                    .replace("$pkg_svc_data_path", "/var/lib/app")
                    .replace("$pkg_svc_var_path", "/var/run/app")
                )

            # Check for potentially dangerous patterns AFTER replacement
            for pattern in dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Add a warning comment but still include the command
                    # Users should review their Dockerfiles before building
                    processed.append(
                        "# WARNING: Potentially dangerous command pattern detected"
                    )
                    break

            processed.append(f"RUN {line}")
    return processed


def _add_dockerfile_build(lines: list[str], plan: dict[str, Any]) -> None:
    """Add build and install steps to Dockerfile."""
    if "do_build" in plan["callbacks"]:
        lines.append("# Build steps")
        lines.extend(
            _process_callback_lines(plan["callbacks"]["do_build"], replace_vars=True)
        )
        lines.append("")
    if "do_install" in plan["callbacks"]:
        lines.append("# Install steps")
        lines.extend(
            _process_callback_lines(plan["callbacks"]["do_install"], replace_vars=True)
        )
        lines.append("")
    if "do_init" in plan["callbacks"]:
        lines.append("# Initialization steps")
        lines.extend(
            _process_callback_lines(plan["callbacks"]["do_init"], replace_vars=True)
        )
        lines.append("")


def _add_dockerfile_runtime(lines: list[str], plan: dict[str, Any]) -> None:
    """Add runtime configuration to Dockerfile."""
    if plan["ports"]:
        lines.append("# Expose ports")
        for port in plan["ports"]:
            port_num = _extract_default_port(port["name"])
            if port_num:
                lines.append(f"EXPOSE {port_num}")
        lines.append("")
    if plan["service"].get("user") and plan["service"]["user"] != "root":
        lines.append(f"USER {plan['service']['user']}")
        lines.append("")
    lines.append("WORKDIR /usr/local")
    lines.append("")
    if plan["service"].get("run"):
        run_cmd = plan["service"]["run"]
        cmd_parts = shlex.split(run_cmd)
        if cmd_parts:
            lines.append(f"CMD {json.dumps(cmd_parts)}")


# Docker Compose generation


def _needs_data_volume(plan: dict[str, Any]) -> bool:
    """
    Detect if a service needs a data volume.

    Checks for data-related patterns in callbacks (like do_init creating
    directories with mkdir) rather than relying on fragile keyword matching
    in run commands.

    Args:
        plan: Parsed Habitat plan dictionary.

    Returns:
        True if the service needs a data volume.

    """
    # Check if do_init callback creates data directories
    if "do_init" in plan["callbacks"]:
        init_code = plan["callbacks"]["do_init"]
        # Look for mkdir commands creating data directories
        if "mkdir" in init_code and ("data" in init_code or "pgdata" in init_code):
            return True

    # Check for database-related package names (common use case)
    pkg_name = plan["package"].get("name", "")
    return pkg_name in ["postgresql", "mysql", "mongodb", "redis"]


def _build_compose_service(plan: dict[str, Any], pkg_name: str) -> dict[str, Any]:
    """Build a docker-compose service definition."""
    service: dict[str, Any] = {
        "build": {"context": ".", "dockerfile": f"Dockerfile.{pkg_name}"},
        "container_name": pkg_name,
        "networks": [],
    }
    if plan["ports"]:
        service["ports"] = []
        for port in plan["ports"]:
            port_num = _extract_default_port(port["name"])
            if port_num:
                service["ports"].append(f"{port_num}:{port_num}")
    if _needs_data_volume(plan):
        service["volumes"] = [f"{pkg_name}_data:/var/lib/app"]
    service["environment"] = []
    for port in plan["ports"]:
        port_num = _extract_default_port(port["name"])
        if port_num:
            service["environment"].append(f"{port['name'].upper()}={port_num}")
    if plan["binds"]:
        service["depends_on"] = [bind["name"] for bind in plan["binds"]]
    return service


def _add_service_build(lines: list[str], service: dict[str, Any]) -> None:
    """
    Add build configuration to service lines.

    Args:
        lines: List of YAML lines to append to.
        service: Service dictionary containing optional 'build' configuration.

    """
    if "build" in service:
        lines.append("    build:")
        lines.append(f"      context: {service['build']['context']}")
        lines.append(f"      dockerfile: {service['build']['dockerfile']}")


def _add_service_ports(lines: list[str], service: dict[str, Any]) -> None:
    """
    Add ports configuration to service lines.

    Args:
        lines: List of YAML lines to append to.
        service: Service dictionary containing optional 'ports' configuration.

    """
    if "ports" in service:
        lines.append("    ports:")
        for port in service["ports"]:
            lines.append(f'      - "{port}"')


def _add_service_volumes(
    lines: list[str], service: dict[str, Any], volumes_used: set[str]
) -> None:
    """
    Add volumes configuration to service lines.

    Args:
        lines: List of YAML lines to append to.
        service: Service dictionary containing optional 'volumes' configuration.
        volumes_used: Set to track volume names for top-level volumes section.

    """
    if "volumes" in service:
        lines.append("    volumes:")
        for volume in service["volumes"]:
            lines.append(f"      - {volume}")
            volumes_used.add(volume.split(":")[0])


def _add_service_environment(lines: list[str], service: dict[str, Any]) -> None:
    """
    Add environment configuration to service lines.

    Args:
        lines: List of YAML lines to append to.
        service: Service dictionary containing optional 'environment'
            configuration.

    """
    if "environment" in service:
        lines.append("    environment:")
        for env in service["environment"]:
            lines.append(f"      - {env}")


def _add_service_dependencies(lines: list[str], service: dict[str, Any]) -> None:
    """
    Add depends_on and networks configuration to service lines.

    Args:
        lines: List of YAML lines to append to.
        service: Service dictionary containing optional 'depends_on' and
            'networks' configuration.

    """
    if "depends_on" in service:
        lines.append("    depends_on:")
        for dep in service["depends_on"]:
            lines.append(f"      - {dep}")
    if "networks" in service:
        lines.append("    networks:")
        for net in service["networks"]:
            lines.append(f"      - {net}")


def _format_compose_yaml(services: dict[str, Any], network_name: str) -> str:
    """
    Format services as docker-compose YAML.

    Args:
        services: Dictionary of service configurations.
        network_name: Docker network name (validated).

    Returns:
        docker-compose.yml content as string.

    Raises:
        ValueError: If network_name format is invalid.

    """
    # Validate network_name to prevent YAML injection
    if not _validate_docker_network_name(network_name):
        raise ValueError(
            f"Invalid Docker network name: {network_name}. "
            "Expected format: alphanumeric with hyphens, underscores, or dots"
        )

    lines = ["version: '3.8'", "", "services:"]
    volumes_used: set[str] = set()
    for name, service in services.items():
        lines.append(f"  {name}:")
        if "container_name" in service:
            lines.append(f"    container_name: {service['container_name']}")
        _add_service_build(lines, service)
        _add_service_ports(lines, service)
        _add_service_volumes(lines, service, volumes_used)
        _add_service_environment(lines, service)
        _add_service_dependencies(lines, service)
        lines.append("")
    lines.extend(["networks:", f"  {network_name}:", "    driver: bridge"])
    if volumes_used:
        lines.extend(["", "volumes:"])
        for vol in sorted(volumes_used):
            lines.append(f"  {vol}:")
    return "\n".join(lines)
