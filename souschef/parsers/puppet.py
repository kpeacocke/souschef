"""
Puppet manifest parser.

Parses Puppet manifests (``.pp`` files) and module directories to extract
resources, variables, classes, and facts into a structured format suitable
for conversion to Ansible playbooks.

Supports Puppet resource types: package, file, service, user, group, exec.
Warns about unsupported constructs (Hiera lookups, complex DSL expressions).
"""

import re
from pathlib import Path
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_NOT_A_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import (
    _get_workspace_root,
    _normalize_path,
    _resolve_path_under_base,
    safe_read_text,
)

# Backward-compatible alias for tests patching this symbol at use-site.
_ensure_within_base_path = _resolve_path_under_base

# Maximum manifest content length to prevent resource exhaustion
MAX_MANIFEST_LENGTH = 2_000_000

# Maximum number of resources to parse from a single manifest
MAX_RESOURCES = 10_000

# Supported Puppet resource types and their Ansible equivalents
PUPPET_RESOURCE_TYPES = frozenset(
    [
        "package",
        "file",
        "service",
        "user",
        "group",
        "exec",
        "cron",
        "host",
        "mount",
        "notify",
        "augeas",
        "ssh_authorized_key",
        "tidy",
        "filebucket",
    ]
)

# Constructs that require manual review / are not auto-convertible
UNSUPPORTED_CONSTRUCTS = [
    (re.compile(r"\bhiera\s*\("), "Hiera lookup"),
    (re.compile(r"\blookup\s*\("), "Hiera lookup (lookup function)"),
    (re.compile(r"\bcreate_resources\s*\("), "create_resources function"),
    (re.compile(r"\bgenerate\s*\("), "generate function"),
    (re.compile(r"\binline_template\s*\("), "inline_template function"),
    (re.compile(r"\bdefined\s*\("), "defined() function"),
    (re.compile(r"\bvirtual\b"), "Virtual resource declaration"),
    (re.compile(r"\brealize\b"), "Virtual resource realization"),
    (re.compile(r"\bcollect\b.*<\|"), "Resource collection expression"),
    (re.compile(r"@@\w+\s*\{"), "Exported resource"),
]


def parse_puppet_manifest(path: str) -> str:
    """
    Parse a Puppet manifest file (``.pp``) and extract resources.

    Identifies Puppet resources (package, file, service, user, group, exec,
    etc.), class definitions, variables, and unsupported constructs.

    Args:
        path: Path to the Puppet manifest (``.pp``) file.

    Returns:
        Formatted string listing all discovered resources, variables,
        class definitions, and unsupported constructs with source locations.

    """
    try:
        file_path = _normalize_path(path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(file_path, workspace_root)
        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        if len(content) > MAX_MANIFEST_LENGTH:
            return f"Error: Manifest too large to parse safely ({len(content)} bytes)"

        results = _parse_manifest_content(content, path)
        return _format_manifest_results(results, path)

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=path)
    except Exception as e:
        return f"An error occurred: {e}"


def _accumulate_manifests(
    manifests: list[Path],
    workspace_root: Path,
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    """
    Parse a list of manifest paths and accumulate results.

    Args:
        manifests: Sorted list of Path objects pointing to ``.pp`` files.
        workspace_root: Trusted workspace root for path containment checks.

    Returns:
        A tuple of (combined_data_dict, skipped_file_warnings).

    """
    all_resources: list[dict[str, Any]] = []
    all_classes: list[dict[str, Any]] = []
    all_variables: list[dict[str, Any]] = []
    all_facts: list[dict[str, Any]] = []
    all_templates: list[dict[str, Any]] = []
    all_unsupported: list[dict[str, Any]] = []
    skipped_files: list[str] = []

    for manifest_path in manifests:
        try:
            content = safe_read_text(manifest_path, workspace_root, encoding="utf-8")
            rel_path = str(manifest_path.relative_to(workspace_root))
            parsed = _parse_manifest_content(content, rel_path)
            all_resources.extend(parsed.get("resources", []))
            all_classes.extend(parsed.get("classes", []))
            all_variables.extend(parsed.get("variables", []))
            all_facts.extend(parsed.get("facts", []))
            all_templates.extend(parsed.get("templates", []))
            all_unsupported.extend(parsed.get("unsupported", []))
        except (OSError, ValueError) as exc:
            skipped_files.append(f"{manifest_path.name}: {exc}")

    combined: dict[str, list[dict[str, Any]]] = {
        "resources": all_resources,
        "classes": all_classes,
        "variables": all_variables,
        "facts": all_facts,
        "templates": all_templates,
        "unsupported": all_unsupported,
    }
    return combined, skipped_files


def parse_puppet_module(module_path: str) -> str:
    """
    Parse a Puppet module directory and extract all resources from manifests.

    Recursively finds all ``.pp`` files in the given directory and parses
    each one, producing a combined report of resources, classes, variables,
    and unsupported constructs with file-level provenance.

    Args:
        module_path: Path to the Puppet module directory.

    Returns:
        Formatted string summarising all resources across all manifests,
        including an unsupported constructs list with file paths and line numbers.

    """
    try:
        dir_path = _normalize_path(module_path)
        workspace_root = _get_workspace_root()
        safe_dir = _ensure_within_base_path(dir_path, workspace_root)

        if not safe_dir.exists():  # NOSONAR
            return ERROR_FILE_NOT_FOUND.format(path=module_path)
        if not safe_dir.is_dir():
            return ERROR_NOT_A_DIRECTORY.format(path=module_path)

        manifests = sorted(safe_dir.rglob("*.pp"))
        if not manifests:
            return f"Warning: No Puppet manifests (.pp files) found in {module_path}"

        combined, skipped_files = _accumulate_manifests(manifests, workspace_root)
        report = _format_manifest_results(combined, module_path)
        if skipped_files:
            warning_lines = "\n".join(f"  - {w}" for w in skipped_files)
            skip_count = len(skipped_files)
            report += f"\n\nWarnings (skipped {skip_count} file(s)):\n{warning_lines}"
        return report

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=module_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=module_path)
    except Exception as e:
        return f"An error occurred: {e}"


def _parse_manifest_content(content: str, source_path: str) -> dict[str, Any]:
    """
    Parse Puppet manifest content and return structured data.

    Args:
        content: Raw Puppet manifest content.
        source_path: Source file path (used for provenance in results).

    Returns:
        Dictionary with keys: resources, classes, variables, unsupported.

    """
    resources = _extract_puppet_resources(content, source_path)
    classes = _extract_puppet_classes(content, source_path)
    variables = _extract_puppet_variables(content, source_path)
    facts = _extract_puppet_facts(content, source_path)
    templates = _extract_puppet_templates(content, source_path)
    unsupported = _detect_unsupported_constructs(content, source_path)
    return {
        "resources": resources,
        "classes": classes,
        "variables": variables,
        "facts": facts,
        "templates": templates,
        "unsupported": unsupported,
    }


def _extract_puppet_resources(content: str, source_path: str) -> list[dict[str, Any]]:
    """
    Extract Puppet resource declarations from manifest content.

    Handles both single-resource and title-array forms::

        package { 'nginx': ensure => installed }
        package { ['nginx', 'curl']: ensure => installed }

    Args:
        content: Puppet manifest content.
        source_path: Source file path for provenance.

    Returns:
        List of resource dictionaries with type, title, attributes, and location.

    """
    resources: list[dict[str, Any]] = []

    # Pattern: resource_type { 'title': attributes }
    # Also handles arrays: resource_type { ['a', 'b']: ... }
    resource_pattern = re.compile(
        r"(\w+)\s*\{[\s\n]*"  # resource_type {
        r"((?:\'[^\']*\'|\"[^\"]*\"|\[[^\]]*\]))"  # 'title' or ['t1', 't2']
        r"\s*:\s*"  # :
        r"([^}]*)",  # attributes: all content up to the closing brace
        re.DOTALL,
    )

    line_starts = _build_line_index(content)

    for match in resource_pattern.finditer(content):
        resource_type = match.group(1).lower()
        if resource_type not in PUPPET_RESOURCE_TYPES:
            continue

        title_raw = match.group(2).strip()
        attrs_raw = match.group(3)
        line_num = _get_line_number(match.start(), line_starts)

        titles = _parse_resource_titles(title_raw)
        attrs = _parse_puppet_attributes(attrs_raw)

        for title in titles:
            resources.append(
                {
                    "type": resource_type,
                    "title": title,
                    "attributes": attrs,
                    "source_file": source_path,
                    "line": line_num,
                }
            )
            if len(resources) >= MAX_RESOURCES:
                return resources

    return resources


def _extract_puppet_classes(content: str, source_path: str) -> list[dict[str, Any]]:
    """
    Extract Puppet class definitions from manifest content.

    Args:
        content: Puppet manifest content.
        source_path: Source file path for provenance.

    Returns:
        List of class dictionaries with name, parameters, and location.

    """
    classes = []
    # Pattern: class classname (optional params) { ... }
    class_pattern = re.compile(
        r"\bclass\s+(\w[\w:]*)\s*"  # class name
        r"(?:\(([^)]{0,2000})\))?"  # optional (params)
        r"\s*(?:inherits\s+[\w:]+\s*)?"  # optional inherits
        r"\{",
        re.DOTALL,
    )
    line_starts = _build_line_index(content)

    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        params_raw = match.group(2) or ""
        params = _parse_class_params(params_raw)
        line_num = _get_line_number(match.start(), line_starts)
        classes.append(
            {
                "name": class_name,
                "parameters": params,
                "source_file": source_path,
                "line": line_num,
            }
        )
    return classes


def _extract_puppet_variables(content: str, source_path: str) -> list[dict[str, Any]]:
    """
    Extract Puppet variable assignments from manifest content.

    Args:
        content: Puppet manifest content.
        source_path: Source file path for provenance.

    Returns:
        List of variable dictionaries with name, value, and location.

    """
    variables = []
    # Pattern: $variable = value
    var_pattern = re.compile(
        r"\$(\w+)\s*=\s*([^\n]{0,500})",
    )
    line_starts = _build_line_index(content)

    for match in var_pattern.finditer(content):
        var_name = match.group(1)
        var_value = match.group(2).strip().rstrip(",;")
        line_num = _get_line_number(match.start(), line_starts)
        variables.append(
            {
                "name": var_name,
                "value": var_value,
                "source_file": source_path,
                "line": line_num,
            }
        )
    return variables


def _extract_puppet_facts(content: str, source_path: str) -> list[dict[str, Any]]:
    """Extract Puppet fact references from manifest content."""
    facts: list[dict[str, Any]] = []
    line_starts = _build_line_index(content)

    legacy_pattern = re.compile(r"\$::([a-zA-Z_][\w]*)")
    modern_pattern = re.compile(
        r"\$facts\s*\[\s*['\"](?P<first>[\w\-]+)['\"]\s*\]"
        r"(?:\s*\[\s*['\"](?P<second>[\w\-]+)['\"]\s*\])?"
    )

    seen: set[tuple[str, int]] = set()

    for match in legacy_pattern.finditer(content):
        name = match.group(1)
        line_num = _get_line_number(match.start(), line_starts)
        dedupe_key = (name, line_num)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        facts.append(
            {
                "name": name,
                "notation": "legacy",
                "source_file": source_path,
                "line": line_num,
            }
        )

    for match in modern_pattern.finditer(content):
        first = match.group("first")
        second = match.group("second")
        name = f"{first}.{second}" if second else first
        line_num = _get_line_number(match.start(), line_starts)
        dedupe_key = (name, line_num)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        facts.append(
            {
                "name": name,
                "notation": "facts_hash",
                "source_file": source_path,
                "line": line_num,
            }
        )

    return facts


def _extract_puppet_templates(content: str, source_path: str) -> list[dict[str, Any]]:
    """Extract Puppet template references from manifest content."""
    templates: list[dict[str, Any]] = []
    line_starts = _build_line_index(content)

    pattern = re.compile(
        r"\b(?P<func>template|epp|inline_template|inline_epp)\s*\(\s*"
        r"['\"](?P<path>[^'\"]+)['\"]"
    )

    for match in pattern.finditer(content):
        line_num = _get_line_number(match.start(), line_starts)
        templates.append(
            {
                "function": match.group("func"),
                "path": match.group("path"),
                "source_file": source_path,
                "line": line_num,
            }
        )

    return templates


def _detect_unsupported_constructs(
    content: str, source_path: str
) -> list[dict[str, Any]]:
    """
    Detect Puppet constructs that cannot be automatically converted.

    Identifies constructs such as Hiera lookups, virtual resources,
    exported resources, create_resources calls, etc. that require
    manual review during migration to Ansible.

    Args:
        content: Puppet manifest content.
        source_path: Source file path for provenance.

    Returns:
        List of unsupported construct dictionaries with construct type,
        matched text, and source location.

    """
    unsupported = []
    line_starts = _build_line_index(content)

    for pattern, construct_name in UNSUPPORTED_CONSTRUCTS:
        for match in pattern.finditer(content):
            line_num = _get_line_number(match.start(), line_starts)
            unsupported.append(
                {
                    "construct": construct_name,
                    "text": match.group(0)[:80],
                    "source_file": source_path,
                    "line": line_num,
                }
            )
    return unsupported


def _parse_resource_titles(title_raw: str) -> list[str]:
    """
    Parse one or more resource titles from a Puppet resource declaration.

    Handles single titles (``'nginx'``) and array titles
    (``['nginx', 'curl']``).

    Args:
        title_raw: Raw title string from manifest.

    Returns:
        List of individual title strings.

    """
    # Array form: ['title1', 'title2']
    if title_raw.startswith("["):
        inner = title_raw.strip("[]")
        return [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
    # Single form: 'title' or "title"
    return [title_raw.strip().strip("'\"")]


def _parse_puppet_attributes(attrs_raw: str) -> dict[str, str]:
    """
    Parse Puppet resource attribute key-value pairs.

    Handles attribute syntax like::

        ensure => installed,
        owner  => 'root',
        mode   => '0644',

    Args:
        attrs_raw: Raw attribute string from resource body.

    Returns:
        Dictionary of attribute names to values.

    """
    attrs: dict[str, str] = {}
    # Pattern: key => value,
    attr_pattern = re.compile(
        r"(\w+)\s*=>\s*"  # key =>
        r"((?:\'[^\']{0,500}\'|\"[^\"]{0,500}\"|[\w:.\-\/]+))",  # value
    )
    for match in attr_pattern.finditer(attrs_raw):
        key = match.group(1)
        value = match.group(2).strip().strip("'\"")
        attrs[key] = value
    return attrs


def _parse_class_params(params_raw: str) -> list[dict[str, str]]:
    """
    Parse Puppet class parameter definitions.

    Handles both typed and untyped parameters with optional defaults::

        String $name = 'default',
        $port = 80,

    Args:
        params_raw: Raw parameter string from class definition.

    Returns:
        List of parameter dictionaries with name, type, and default.

    """
    params: list[dict[str, str]] = []
    if not params_raw.strip():
        return params

    # Pattern: Optional[Type] $name = default_value
    param_pattern = re.compile(
        r"(?:([\w\[\]]+)\s+)?"  # optional type
        r"\$(\w+)"  # $param_name
        r"(?:\s*=\s*([^\n,)]{0,200}))?"
    )
    for match in param_pattern.finditer(params_raw):
        param_type = (match.group(1) or "").strip()
        param_name = match.group(2)
        param_default = (match.group(3) or "").strip().rstrip(",")
        params.append(
            {
                "name": param_name,
                "type": param_type,
                "default": param_default,
            }
        )
    return params


def _build_line_index(content: str) -> list[int]:
    """
    Build an index mapping character offsets to line start positions.

    Args:
        content: File content string.

    Returns:
        List where index ``i`` is the character offset of line ``i+1``.

    """
    starts = [0]
    for i, ch in enumerate(content):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _get_line_number(offset: int, line_starts: list[int]) -> int:
    """
    Return the 1-based line number for a given character offset.

    Args:
        offset: Character offset in the content.
        line_starts: Line start index from :func:`_build_line_index`.

    Returns:
        1-based line number.

    """
    # Binary search for the line containing this offset
    lo, hi = 0, len(line_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def _format_resources_section(
    parts: list[str], resources: list[dict[str, Any]]
) -> None:
    """Append the resources section to the report parts list."""
    if resources:
        parts.append(f"Resources ({len(resources)}):")
        for res in resources:
            parts.append(f"  {res['type']} {{ '{res['title']}' }} [line {res['line']}]")
            for attr_key, attr_val in res.get("attributes", {}).items():
                parts.append(f"    {attr_key}: {attr_val}")
        parts.append("")
    else:
        parts.append("Resources: none found")
        parts.append("")


def _format_classes_section(parts: list[str], classes: list[dict[str, Any]]) -> None:
    """Append the classes section to the report parts list."""
    if classes:
        parts.append(f"Classes ({len(classes)}):")
        for cls in classes:
            param_names = [p["name"] for p in cls.get("parameters", [])]
            param_str = ", ".join(f"${n}" for n in param_names) if param_names else ""
            parts.append(f"  class {cls['name']}({param_str}) [line {cls['line']}]")
        parts.append("")


def _format_variables_section(
    parts: list[str], variables: list[dict[str, Any]]
) -> None:
    """Append the variables section (first 20) to the report parts list."""
    if variables:
        parts.append(f"Variables ({len(variables)}):")
        for var in variables[:20]:  # Show first 20 to avoid overwhelming output
            parts.append(f"  ${var['name']} = {var['value']} [line {var['line']}]")
        if len(variables) > 20:
            parts.append(f"  ... and {len(variables) - 20} more")
        parts.append("")


def _format_facts_section(parts: list[str], facts: list[dict[str, Any]]) -> None:
    """Append the facts section to the report parts list."""
    if facts:
        parts.append(f"Facts Referenced ({len(facts)}):")
        for fact in facts[:20]:
            parts.append(f"  {fact['name']} ({fact['notation']}) [line {fact['line']}]")
        if len(facts) > 20:
            parts.append(f"  ... and {len(facts) - 20} more")
        parts.append("")


def _format_templates_section(
    parts: list[str], templates: list[dict[str, Any]]
) -> None:
    """Append the template references section to the report parts list."""
    if templates:
        parts.append(f"Templates Referenced ({len(templates)}):")
        for template in templates:
            parts.append(
                f"  {template['function']}('{template['path']}')"
                f" [line {template['line']}]"
            )
        parts.append("")


def _format_unsupported_section(
    parts: list[str], unsupported: list[dict[str, Any]]
) -> None:
    """Append the unsupported constructs section to the report parts list."""
    if unsupported:
        count = len(unsupported)
        parts.append(f"Unsupported Constructs ({count}) - require manual review:")
        for item in unsupported:
            parts.append(
                f"  [{item['construct']}] at"
                f" {item['source_file']}:{item['line']}"
                f" — {item['text']!r}"
            )
        parts.append("")
    else:
        parts.append("Unsupported Constructs: none detected")
        parts.append("")


def _format_manifest_results(results: dict[str, Any], source: str) -> str:
    """
    Format parsed manifest results as a human-readable report string.

    Args:
        results: Parsed manifest data (resources, classes, variables, unsupported).
        source: Source path displayed in the report header.

    Returns:
        Formatted report string suitable for display or further processing.

    """
    parts: list[str] = [f"Puppet Manifest Analysis: {source}", ""]

    resources = results.get("resources", [])
    classes = results.get("classes", [])
    variables = results.get("variables", [])
    facts = results.get("facts", [])
    templates = results.get("templates", [])
    unsupported = results.get("unsupported", [])

    _format_resources_section(parts, resources)
    _format_classes_section(parts, classes)
    _format_variables_section(parts, variables)
    _format_facts_section(parts, facts)
    _format_templates_section(parts, templates)
    _format_unsupported_section(parts, unsupported)

    # Summary
    parts.append("Summary:")
    parts.append(f"  Total resources: {len(resources)}")
    parts.append(f"  Total classes: {len(classes)}")
    parts.append(f"  Total variables: {len(variables)}")
    parts.append(f"  Total facts referenced: {len(facts)}")
    parts.append(f"  Total templates referenced: {len(templates)}")
    parts.append(f"  Unsupported constructs: {len(unsupported)}")
    if unsupported:
        parts.append("  NOTE: Review unsupported constructs before migration.")

    return "\n".join(parts)


def get_puppet_resource_types() -> list[str]:
    """
    Return the list of supported Puppet resource types.

    Returns:
        Sorted list of supported resource type names.

    """
    return sorted(PUPPET_RESOURCE_TYPES)
