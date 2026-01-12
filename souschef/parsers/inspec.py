"""InSpec profile parser and converter."""

import json
import re
from pathlib import Path
from typing import Any

from souschef.core.constants import ERROR_PREFIX, INSPEC_END_INDENT, INSPEC_SHOULD_EXIST
from souschef.core.path_utils import _normalize_path, _safe_join

# Regex patterns used across converters
_VERSION_PATTERN = r"match\s+/([^/]+)/"
_MODE_PATTERN = r"cmp\s+'([^']+)'"
_OWNER_PATTERN = r"eq\s+['\"]([^'\"]+)['\"]"

# ServerSpec formatting constants
_SERVERSPEC_END = "  end"


def parse_inspec_profile(path: str) -> str:
    """
    Parse an InSpec profile and extract controls.

    Args:
        path: Path to InSpec profile directory or control file (.rb).

    Returns:
        JSON string with parsed controls, or error message.

    """
    try:
        # Validate input
        if not path or not path.strip():
            return (
                "Error: Path cannot be empty\n\n"
                "Suggestion: Provide a path to an InSpec profile directory "
                "or control file"
            )

        profile_path = _normalize_path(path)

        if not profile_path.exists():
            return (
                f"Error: Path does not exist: {path}\n\n"
                "Suggestion: Check that the path is correct and the InSpec "
                "profile exists"
            )

        if profile_path.is_dir():
            controls = _parse_controls_from_directory(profile_path)
        elif profile_path.is_file():
            controls = _parse_controls_from_file(profile_path)
        else:
            return (
                f"Error: Invalid path type: {path}\n\n"
                "Suggestion: Provide a directory or file path, not a special file type"
            )

        return json.dumps(
            {
                "profile_path": str(profile_path),
                "controls_count": len(controls),
                "controls": controls,
            },
            indent=2,
        )

    except (FileNotFoundError, RuntimeError) as e:
        return f"Error: {e}\n\nSuggestion: Verify the path exists and is accessible"
    except Exception as e:
        return f"An error occurred while parsing InSpec profile: {e}"


def convert_inspec_to_test(inspec_path: str, output_format: str = "testinfra") -> str:  # noqa: C901
    """
    Convert InSpec controls to test framework format.

    Args:
        inspec_path: Path to InSpec profile or control file.
        output_format: Output format ('testinfra', 'ansible_assert',
            'serverspec', or 'goss').

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

        elif output_format == "serverspec":
            converted_tests.append("# frozen_string_literal: true")
            converted_tests.append("")
            converted_tests.append("require 'serverspec'")
            converted_tests.append("")
            converted_tests.append("set :backend, :exec")
            converted_tests.append("")
            for control in controls:
                serverspec_code = _convert_inspec_to_serverspec(control)
                converted_tests.append(serverspec_code)

        elif output_format == "goss":
            # Goss uses a single YAML spec for all tests
            return _convert_inspec_to_goss(controls)

        else:
            error_msg = (
                f"Error: Unsupported format '{output_format}'. "
                "Use 'testinfra', 'ansible_assert', 'serverspec', or 'goss'"
            )
            return error_msg

        return "\n".join(converted_tests)

    except json.JSONDecodeError as e:
        return f"Error parsing InSpec result: {e}"
    except Exception as e:
        return f"An error occurred during conversion: {e}"


def generate_inspec_from_chef(
    resource_type: str, resource_name: str, properties: dict[str, Any]
) -> str:
    """
    Generate InSpec control from Chef resource.

    Args:
        resource_type: Type of Chef resource.
        resource_name: Name of the resource.
        properties: Resource properties.

    Returns:
        InSpec control code.

    """
    return _generate_inspec_from_resource(resource_type, resource_name, properties)


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


def _extract_control_metadata(control_body: str) -> dict[str, Any]:
    """
    Extract title, description, and impact from control body.

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
    """
    Parse InSpec control blocks from content.

    Args:
        content: InSpec profile content.

    Returns:
        List of parsed control dictionaries with id, title, desc, impact, tests.

    """
    controls = []
    lines = content.split("\n")
    lines_len = len(lines)

    i = 0
    while i < lines_len:
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
    """
    Find the end of a nested Ruby block (do...end).

    Args:
        lines: All lines of content.
        start_index: Starting line index (after the 'do' line).

    Returns:
        Tuple of (body_lines, ending_index).

    """
    nesting_level = 0
    body_lines = []
    lines_len = len(lines)
    i = start_index

    while i < lines_len:
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
    """
    Extract 'it { should ... }' expectations from describe block.

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
    """
    Extract 'its(...) { should ... }' expectations from describe block.

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
    """
    Extract InSpec describe blocks and their matchers.

    Args:
        content: Content to parse for describe blocks.

    Returns:
        List of test dictionaries with resource type, name, and expectations.

    """
    tests = []
    lines = content.split("\n")
    lines_len = len(lines)

    i = 0
    while i < lines_len:
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
    """
    Convert package resource to Testinfra assertions.

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
            version_match = re.search(_VERSION_PATTERN, exp["matcher"])
            if version_match:
                version = version_match.group(1)
                lines.append(f'    assert pkg.version.startswith("{version}")')


def _convert_service_to_testinfra(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """
    Convert service resource to Testinfra assertions.

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
    """
    Convert file resource to Testinfra assertions.

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
    """
    Convert port resource to Testinfra assertions.

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
    """
    Convert InSpec control to Testinfra test.

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


def _convert_package_to_serverspec(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """
    Convert package resource to ServerSpec expectations.

    Args:
        lines: List to append test lines to.
        resource_name: Name of the package.
        expectations: List of InSpec expectations.

    """
    lines.append(f"  describe package('{resource_name}') do")
    for exp in expectations:
        if "be_installed" in exp["matcher"]:
            lines.append("    it { should be_installed }")
        elif exp["type"] == "its" and exp["property"] == "version":
            version_match = re.search(_VERSION_PATTERN, exp["matcher"])
            if version_match:
                version = version_match.group(1)
                lines.append(f"    its('version') {{ should match /{version}/ }}")
    lines.append(_SERVERSPEC_END)


def _convert_service_to_serverspec(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """
    Convert service resource to ServerSpec expectations.

    Args:
        lines: List to append test lines to.
        resource_name: Name of the service.
        expectations: List of InSpec expectations.

    """
    lines.append(f"  describe service('{resource_name}') do")
    for exp in expectations:
        if "be_running" in exp["matcher"]:
            lines.append("    it { should be_running }")
        elif "be_enabled" in exp["matcher"]:
            lines.append("    it { should be_enabled }")
    lines.append(_SERVERSPEC_END)


def _convert_file_to_serverspec(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """
    Convert file resource to ServerSpec expectations.

    Args:
        lines: List to append test lines to.
        resource_name: Path to the file.
        expectations: List of InSpec expectations.

    """
    lines.append(f"  describe file('{resource_name}') do")
    for exp in expectations:
        if "exist" in exp["matcher"]:
            lines.append("    it { should exist }")
        elif exp["type"] == "its" and exp["property"] == "mode":
            mode_match = re.search(_MODE_PATTERN, exp["matcher"])
            if mode_match:
                mode = mode_match.group(1)
                lines.append(f"    its('mode') {{ should cmp '{mode}' }}")
        elif exp["type"] == "its" and exp["property"] == "owner":
            owner_match = re.search(_OWNER_PATTERN, exp["matcher"])
            if owner_match:
                owner = owner_match.group(1)
                lines.append(f"    its('owner') {{ should eq '{owner}' }}")
    lines.append(_SERVERSPEC_END)


def _convert_port_to_serverspec(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """
    Convert port resource to ServerSpec expectations.

    Args:
        lines: List to append test lines to.
        resource_name: Port number or address.
        expectations: List of InSpec expectations.

    """
    lines.append(f"  describe port({resource_name}) do")
    for exp in expectations:
        if "be_listening" in exp["matcher"]:
            lines.append("    it { should be_listening }")
    lines.append(_SERVERSPEC_END)


def _convert_inspec_to_serverspec(control: dict[str, Any]) -> str:
    """
    Convert InSpec control to ServerSpec test.

    Args:
        control: Parsed InSpec control dictionary.

    Returns:
        ServerSpec test code as string.

    """
    lines = []

    # Add describe block for the control
    lines.append(f"describe '{control.get('title') or control['id']}' do")

    # Convert each test within the control
    for test in control["tests"]:
        resource_type = test["resource_type"]
        resource_name = test["resource_name"]
        expectations = test["expectations"]

        # Map InSpec resources to ServerSpec using dedicated converters
        if resource_type == "package":
            _convert_package_to_serverspec(lines, resource_name, expectations)
        elif resource_type == "service":
            _convert_service_to_serverspec(lines, resource_name, expectations)
        elif resource_type == "file":
            _convert_file_to_serverspec(lines, resource_name, expectations)
        elif resource_type == "port":
            _convert_port_to_serverspec(lines, resource_name, expectations)

    lines.append("end")
    lines.append("")
    return "\n".join(lines)


def _convert_package_to_goss(expectations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert package resource to Goss specification.

    Args:
        expectations: List of InSpec expectations.

    Returns:
        Goss package specification dictionary.

    """
    spec: dict[str, Any] = {}
    for exp in expectations:
        if "be_installed" in exp["matcher"]:
            spec["installed"] = True
        elif exp["type"] == "its" and exp["property"] == "version":
            version_match = re.search(_VERSION_PATTERN, exp["matcher"])
            if version_match:
                spec["versions"] = [version_match.group(1)]
    return spec


def _convert_service_to_goss(expectations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert service resource to Goss specification.

    Args:
        expectations: List of InSpec expectations.

    Returns:
        Goss service specification dictionary.

    """
    spec: dict[str, Any] = {}
    for exp in expectations:
        if "be_running" in exp["matcher"]:
            spec["running"] = True
        elif "be_enabled" in exp["matcher"]:
            spec["enabled"] = True
    return spec


def _convert_file_to_goss(expectations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert file resource to Goss specification.

    Args:
        expectations: List of InSpec expectations.

    Returns:
        Goss file specification dictionary.

    """
    spec: dict[str, Any] = {}
    for exp in expectations:
        if "exist" in exp["matcher"]:
            spec["exists"] = True
        elif exp["type"] == "its" and exp["property"] == "mode":
            mode_match = re.search(_MODE_PATTERN, exp["matcher"])
            if mode_match:
                spec["mode"] = mode_match.group(1)
        elif exp["type"] == "its" and exp["property"] == "owner":
            owner_match = re.search(_OWNER_PATTERN, exp["matcher"])
            if owner_match:
                spec["owner"] = owner_match.group(1)
    return spec


def _convert_port_to_goss(expectations: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Convert port resource to Goss specification.

    Args:
        expectations: List of InSpec expectations.

    Returns:
        Goss port specification dictionary.

    """
    spec: dict[str, Any] = {}
    for exp in expectations:
        if "be_listening" in exp["matcher"]:
            spec["listening"] = True
    return spec


def _convert_inspec_to_goss(controls: list[dict[str, Any]]) -> str:
    """
    Convert InSpec controls to Goss YAML specification.

    Args:
        controls: List of parsed InSpec control dictionaries.

    Returns:
        Goss specification as YAML string.

    """
    goss_spec: dict[str, dict[str, Any]] = {
        "package": {},
        "service": {},
        "file": {},
        "port": {},
    }

    # Process all controls and group by resource type
    for control in controls:
        for test in control["tests"]:
            resource_type = test["resource_type"]
            resource_name = test["resource_name"]
            expectations = test["expectations"]

            if resource_type == "package":
                spec = _convert_package_to_goss(expectations)
                goss_spec["package"][resource_name] = spec
            elif resource_type == "service":
                spec = _convert_service_to_goss(expectations)
                goss_spec["service"][resource_name] = spec
            elif resource_type == "file":
                spec = _convert_file_to_goss(expectations)
                goss_spec["file"][resource_name] = spec
            elif resource_type == "port":
                # Goss uses string format for ports
                port_key = f"tcp://{resource_name}"
                spec = _convert_port_to_goss(expectations)
                goss_spec["port"][port_key] = spec

    # Remove empty sections
    goss_spec = {k: v for k, v in goss_spec.items() if v}

    # Convert to YAML (using JSON for now, will need PyYAML for proper YAML)
    try:
        import yaml

        return yaml.dump(goss_spec, default_flow_style=False, sort_keys=False)
    except ImportError:
        # Fallback to JSON if PyYAML not available
        return json.dumps(goss_spec, indent=2)


def _convert_package_to_ansible_assert(
    lines: list[str], resource_name: str, expectations: list[dict[str, Any]]
) -> None:
    """
    Convert package expectations to Ansible assert conditions.

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
    """
    Convert service expectations to Ansible assert conditions.

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
    """
    Convert file expectations to Ansible assert conditions.

    Args:
        lines: List to append assertion lines to.
        expectations: List of InSpec expectations.

    """
    for exp in expectations:
        if "exist" in exp["matcher"]:
            lines.append("      - stat_result.stat.exists")


def _convert_inspec_to_ansible_assert(control: dict[str, Any]) -> str:
    """
    Convert InSpec control to Ansible assert task.

    Args:
        control: Parsed InSpec control dictionary.

    Returns:
        Ansible assert task in YAML format.

    """
    lines = [
        f"- name: Verify {control.get('title') or control['id']}",
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
    """
    Generate InSpec checks for package resource.

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
    lines.append(INSPEC_END_INDENT)
    return lines


def _generate_inspec_resource_checks(
    resource_type: str,
    resource_name: str,
    properties: dict[str, Any] | None = None,
    custom_checks: list[str] | None = None,
) -> list[str]:
    """
    Generate InSpec checks for a resource using a generic pattern.

    Args:
        resource_type: InSpec resource type (e.g., 'file', 'user', 'service').
        resource_name: Name/path of the resource.
        properties: Optional resource properties to check.
        custom_checks: Optional list of custom check lines.

    Returns:
        List of InSpec check lines.

    """
    lines = [f"  describe {resource_type}('{resource_name}') do"]

    # Add custom checks if provided
    if custom_checks:
        lines.extend(custom_checks)
    else:
        # Default: should exist
        lines.append(INSPEC_SHOULD_EXIST)

    # Add property checks
    if properties:
        property_map = {
            "mode": lambda v: f"    its('mode') {{ should cmp '{v}' }}",
            "owner": lambda v: f"    its('owner') {{ should eq '{v}' }}",
            "group": lambda v: f"    its('group') {{ should eq '{v}' }}",
            "shell": lambda v: f"    its('shell') {{ should eq '{v}' }}",
        }
        for prop, value in properties.items():
            if prop in property_map:
                lines.append(property_map[prop](value))

    lines.append(INSPEC_END_INDENT)
    return lines


def _generate_inspec_service_checks(resource_name: str) -> list[str]:
    """
    Generate InSpec checks for service resource.

    Args:
        resource_name: Name of the service.

    Returns:
        List of InSpec check lines.

    """
    return _generate_inspec_resource_checks(
        "service",
        resource_name,
        custom_checks=[
            "    it { should be_running }",
            "    it { should be_enabled }",
        ],
    )


def _generate_inspec_file_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """
    Generate InSpec checks for file/template resource.

    Args:
        resource_name: Name/path of the file.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    return _generate_inspec_resource_checks(
        "file",
        resource_name,
        properties=properties,
    )


def _generate_inspec_directory_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """
    Generate InSpec checks for directory resource.

    Args:
        resource_name: Path of the directory.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    return _generate_inspec_resource_checks(
        "file",
        resource_name,
        properties=properties,
        custom_checks=[
            INSPEC_SHOULD_EXIST,
            "    it { should be_directory }",
        ],
    )


def _generate_inspec_user_checks(
    resource_name: str, properties: dict[str, Any]
) -> list[str]:
    """
    Generate InSpec checks for user resource.

    Args:
        resource_name: Username.
        properties: Resource properties.

    Returns:
        List of InSpec check lines.

    """
    return _generate_inspec_resource_checks(
        "user",
        resource_name,
        properties=properties,
    )


def _generate_inspec_group_checks(resource_name: str) -> list[str]:
    """
    Generate InSpec checks for group resource.

    Args:
        resource_name: Group name.

    Returns:
        List of InSpec check lines.

    """
    return _generate_inspec_resource_checks("group", resource_name)


def _generate_inspec_from_resource(
    resource_type: str, resource_name: str, properties: dict[str, Any]
) -> str:
    """
    Generate InSpec control from Chef resource.

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
