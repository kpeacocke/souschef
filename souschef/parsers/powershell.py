"""
PowerShell script parser.

Parses PowerShell scripts (``.ps1``, ``.psm1``, ``.psd1`` files) and
module directories to extract cmdlet invocations, function definitions,
variables, and module imports into a structured format suitable for
conversion to Ansible playbooks targeting Windows hosts via AAP/AWX.

Cmdlet coverage includes the most common Windows Server administration
commands (package management, file system, services, registry, users,
network, IIS, scheduled tasks, etc.) as well as Windows-specific Desired
State Configuration (DSC) resources.

Constructs that cannot be converted automatically (COM objects, .NET P/Invoke,
WMI queries, complex remoting, etc.) are flagged for manual review or
AI-assisted conversion.
"""

import re
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
    safe_read_text,
)

# Maximum script content length to prevent resource exhaustion
MAX_SCRIPT_LENGTH = 2_000_000

# Maximum number of cmdlet invocations to extract per file
MAX_CMDLETS = 10_000

# ---------------------------------------------------------------------------
# Supported cmdlet → Ansible module mapping
# ---------------------------------------------------------------------------

# Registry of PowerShell cmdlets that have a direct Ansible equivalent.
# Maps cmdlet name (lower-case) → Ansible module name.
CMDLET_MODULE_MAP: dict[str, str] = {
    # Package management
    "install-windowsfeature": "ansible.windows.win_feature",
    "uninstall-windowsfeature": "ansible.windows.win_feature",
    "add-windowsfeature": "ansible.windows.win_feature",
    "remove-windowsfeature": "ansible.windows.win_feature",
    "install-package": "ansible.windows.win_package",
    "uninstall-package": "ansible.windows.win_package",
    "install-module": "community.windows.win_psmodule",
    "uninstall-module": "community.windows.win_psmodule",
    # File system
    "new-item": "ansible.windows.win_file",
    "remove-item": "ansible.windows.win_file",
    "copy-item": "ansible.windows.win_copy",
    "move-item": "ansible.windows.win_copy",
    "get-content": "ansible.windows.win_copy",
    "set-content": "ansible.windows.win_copy",
    "add-content": "ansible.windows.win_lineinfile",
    "test-path": "ansible.windows.win_stat",
    "rename-item": "ansible.windows.win_file",
    # Services
    "start-service": "ansible.windows.win_service",
    "stop-service": "ansible.windows.win_service",
    "restart-service": "ansible.windows.win_service",
    "set-service": "ansible.windows.win_service",
    "new-service": "ansible.windows.win_service",
    "remove-service": "ansible.windows.win_service",
    # Registry
    "new-itemproperty": "ansible.windows.win_regedit",
    "set-itemproperty": "ansible.windows.win_regedit",
    "remove-itemproperty": "ansible.windows.win_regedit",
    "new-item-registry": "ansible.windows.win_regedit",
    "remove-item-registry": "ansible.windows.win_regedit",
    # Users and groups
    "new-localuser": "ansible.windows.win_user",
    "set-localuser": "ansible.windows.win_user",
    "remove-localuser": "ansible.windows.win_user",
    "add-localgroupmember": "ansible.windows.win_group_membership",
    "remove-localgroupmember": "ansible.windows.win_group_membership",
    "new-localgroup": "ansible.windows.win_group",
    "remove-localgroup": "ansible.windows.win_group",
    # ACL / permissions
    "set-acl": "ansible.windows.win_acl",
    "get-acl": "ansible.windows.win_acl",
    # Network
    "new-netfirewallrule": "community.windows.win_firewall_rule",
    "set-netfirewallrule": "community.windows.win_firewall_rule",
    "remove-netfirewallrule": "community.windows.win_firewall_rule",
    "enable-netfirewallrule": "community.windows.win_firewall_rule",
    "disable-netfirewallrule": "community.windows.win_firewall_rule",
    "set-dnsserversearchorder": "community.windows.win_dns_client",
    # Scheduled tasks
    "register-scheduledtask": "community.windows.win_scheduled_task",
    "unregister-scheduledtask": "community.windows.win_scheduled_task",
    "enable-scheduledtask": "community.windows.win_scheduled_task",
    "disable-scheduledtask": "community.windows.win_scheduled_task",
    # Environment variables
    "set-environmentvariable": "ansible.windows.win_environment",
    "[environment]::setenvironmentvariable": "ansible.windows.win_environment",
    # IIS (requires IIS Administration module / win_iis_*)
    "new-website": "community.windows.win_iis_website",
    "start-website": "community.windows.win_iis_website",
    "stop-website": "community.windows.win_iis_website",
    "remove-website": "community.windows.win_iis_website",
    "new-webapplication": "community.windows.win_iis_webapplication",
    "new-webvirtualdirectory": "community.windows.win_iis_virtualdirectory",
    "new-webbinding": "community.windows.win_iis_webbinding",
    # DSC resources (map to win_dsc)
    "invoke-dscresource": "ansible.windows.win_dsc",
    # General shell / command execution
    "invoke-expression": "ansible.windows.win_shell",
    "invoke-command": "ansible.windows.win_shell",
    "start-process": "ansible.windows.win_shell",
    "cmd": "ansible.windows.win_command",
    # Certificates
    "import-certificate": "community.windows.win_certificate_store",
    "remove-item-certificate": "community.windows.win_certificate_store",
    # Chocolatey (common on Windows)
    "choco": "chocolatey.chocolatey.win_chocolatey",
    # Downloads
    "invoke-webrequest": "ansible.windows.win_get_url",
    "start-bitstransfer": "ansible.windows.win_get_url",
    # Reboot / wait
    "restart-computer": "ansible.windows.win_reboot",
    # Zip / archive
    "expand-archive": "community.windows.win_unzip",
    "compress-archive": "community.windows.win_zip",
    # Windows Updates
    "install-windowsupdate": "ansible.windows.win_updates",
    "get-windowsupdate": "ansible.windows.win_updates",
    # MSI / installer
    "start-msiexec": "ansible.windows.win_package",
    # Output / debug
    "write-host": "ansible.builtin.debug",
    "write-output": "ansible.builtin.debug",
    "write-verbose": "ansible.builtin.debug",
    "write-warning": "ansible.builtin.debug",
    "write-error": "ansible.builtin.fail",
    "throw": "ansible.builtin.fail",
}

# ---------------------------------------------------------------------------
# Constructs that require manual review or AI-assisted conversion
# ---------------------------------------------------------------------------

UNSUPPORTED_CONSTRUCTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\[.*::.*\]", re.IGNORECASE), ".NET static method call"),
    (re.compile(r"New-Object\s+", re.IGNORECASE), "COM/CLR object instantiation"),
    (re.compile(r"Add-Type\s+", re.IGNORECASE), "Inline .NET type compilation"),
    (re.compile(r"Get-WmiObject\s+", re.IGNORECASE), "WMI query"),
    (re.compile(r"Get-CimInstance\s+", re.IGNORECASE), "CIM/WMI query"),
    (re.compile(r"Invoke-WmiMethod\s+", re.IGNORECASE), "WMI method invocation"),
    (
        re.compile(r"Enter-PSSession\s+|New-PSSession\s+", re.IGNORECASE),
        "PS remoting session",
    ),
    (re.compile(r"\$using:", re.IGNORECASE), "Cross-scope variable ($using:)"),
    (re.compile(r"Register-ObjectEvent\s+", re.IGNORECASE), "Event subscription"),
    (re.compile(r"#Requires\s+-", re.IGNORECASE), "#Requires directive"),
    (
        re.compile(r"Import-Module\s+\w+\s+-UseWindowsPowerShell", re.IGNORECASE),
        "Windows PowerShell compatibility mode",
    ),
    (re.compile(r"Configuration\s+\w+\s*\{", re.IGNORECASE), "DSC Configuration block"),
]

# ---------------------------------------------------------------------------
# Regex patterns for extraction
# ---------------------------------------------------------------------------

# Match a PowerShell function definition
_RE_FUNCTION = re.compile(
    r"(?:^|\n)\s*function\s+([A-Za-z_][A-Za-z0-9_\-]*)\s*"
    r"(?:\(([^)]*)\))?\s*\{",
    re.IGNORECASE,
)

# Match a variable assignment  $VarName = value  (or  $VarName = "value")
_RE_VARIABLE = re.compile(
    r"(?m)^\s*\$([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.{0,120})",
    re.IGNORECASE,
)

# Match #Requires -Modules <name>
_RE_REQUIRES_MODULE = re.compile(
    r"#Requires\s+-Modules?\s+([A-Za-z0-9_\.,\s]+)", re.IGNORECASE
)

# Match Import-Module <name>
_RE_IMPORT_MODULE = re.compile(
    r"Import-Module\s+['\"]?([A-Za-z0-9_\.\-]+)['\"]?", re.IGNORECASE
)

# Match param() block parameters
_RE_PARAM = re.compile(
    r"\[Parameter[^\]]*\]\s*\$([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE
)

# Generic cmdlet / function call with optional -parameters
_RE_CMDLET_CALL = re.compile(
    r"(?m)(?:^|;|\|)\s*"
    r"([A-Za-z]+-[A-Za-z]+(?:-[A-Za-z]+)*)"  # VerbNoun cmdlet
    r"((?:\s+-[A-Za-z][A-Za-z0-9]*\s+[^-\n][^\n]*|\s+-[A-Za-z][A-Za-z0-9]*)*)",
    re.IGNORECASE,
)


def parse_powershell_script(path: str) -> str:
    """
    Parse a PowerShell script file and extract its structure.

    Identifies cmdlet invocations, function definitions, variable assignments,
    module imports, and constructs that cannot be automatically converted.

    Args:
        path: Path to a PowerShell script (``.ps1``, ``.psm1``, or ``.psd1``).

    Returns:
        Formatted analysis string summarising the script contents, or an
        error message string prefixed with ``"Error:"`` if reading fails.

    """
    try:
        file_path = _normalize_path(path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(file_path, workspace_root)
        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        if len(content) > MAX_SCRIPT_LENGTH:
            return f"Error: Script too large to parse safely ({len(content)} bytes)"

        results = _parse_script_content(content, path)
        return _format_script_results(results, path)

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


def parse_powershell_directory(directory_path: str) -> str:
    """
    Parse all PowerShell scripts in a directory.

    Recursively finds all ``.ps1``, ``.psm1``, and ``.psd1`` files and
    produces a combined analysis report across all scripts.

    Args:
        directory_path: Path to the directory containing PowerShell scripts.

    Returns:
        Formatted summary report across all scripts, or an error message.

    """
    try:
        dir_path = _normalize_path(directory_path)
        workspace_root = _get_workspace_root()
        safe_dir = _ensure_within_base_path(dir_path, workspace_root)

        if not safe_dir.exists():  # NOSONAR
            return ERROR_FILE_NOT_FOUND.format(path=directory_path)
        if not safe_dir.is_dir():
            return ERROR_IS_DIRECTORY.format(path=directory_path)

        scripts = sorted(
            list(safe_dir.rglob("*.ps1"))
            + list(safe_dir.rglob("*.psm1"))
            + list(safe_dir.rglob("*.psd1"))
        )
        if not scripts:
            return (
                f"Warning: No PowerShell scripts (.ps1/.psm1/.psd1) found "
                f"in {directory_path}"
            )

        all_cmdlets: list[dict[str, Any]] = []
        all_functions: list[dict[str, Any]] = []
        all_variables: list[dict[str, Any]] = []
        all_unsupported: list[dict[str, Any]] = []
        all_modules: list[dict[str, Any]] = []

        for script_path in scripts:
            try:
                content = safe_read_text(
                    script_path, workspace_root, encoding="utf-8"
                )
                rel_path = str(script_path.relative_to(workspace_root))
                parsed = _parse_script_content(content, rel_path)
                all_cmdlets.extend(parsed.get("cmdlets", []))
                all_functions.extend(parsed.get("functions", []))
                all_variables.extend(parsed.get("variables", []))
                all_unsupported.extend(parsed.get("unsupported", []))
                all_modules.extend(parsed.get("modules", []))
            except (OSError, ValueError):
                continue

        combined: dict[str, Any] = {
            "cmdlets": all_cmdlets,
            "functions": all_functions,
            "variables": all_variables,
            "unsupported": all_unsupported,
            "modules": all_modules,
        }
        return _format_script_results(combined, directory_path)

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=directory_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=directory_path)
    except Exception as e:
        return f"An error occurred: {e}"


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------


def _parse_script_content(content: str, source_path: str) -> dict[str, Any]:
    """
    Parse PowerShell script content and return structured data.

    Args:
        content: Raw PowerShell script text.
        source_path: Source file path (used for provenance in results).

    Returns:
        Dictionary with keys: cmdlets, functions, variables, modules,
        unsupported.

    """
    stripped = _strip_comments(content)
    cmdlets = _extract_cmdlets(stripped, source_path)
    functions = _extract_functions(stripped, source_path)
    variables = _extract_variables(stripped, source_path)
    modules = _extract_module_imports(stripped, source_path)
    unsupported = _detect_unsupported_constructs(content, source_path)

    return {
        "cmdlets": cmdlets[:MAX_CMDLETS],
        "functions": functions,
        "variables": variables,
        "modules": modules,
        "unsupported": unsupported,
    }


def _strip_comments(content: str) -> str:
    """
    Remove single-line (#) and block (<# ... #>) PowerShell comments.

    Args:
        content: Raw PowerShell text.

    Returns:
        Text with comments replaced by whitespace to preserve line numbers.

    """
    # Remove block comments <# ... #>
    content = re.sub(
        r"<#.*?#>",
        lambda m: "\n" * m.group(0).count("\n"),
        content,
        flags=re.DOTALL,
    )
    # Remove single-line comments
    content = re.sub(r"#[^\n]*", "", content)
    return content


def _build_line_index(content: str) -> list[int]:
    """
    Build an index of character offsets for the start of each line.

    Args:
        content: Script text.

    Returns:
        Sorted list of character offsets at which each line starts.

    """
    offsets = [0]
    for i, ch in enumerate(content):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _get_line_number(offset: int, line_starts: list[int]) -> int:
    """
    Return the 1-based line number for a given character offset.

    Args:
        offset: Character offset within the script.
        line_starts: Sorted list of line-start offsets from
            :func:`_build_line_index`.

    Returns:
        1-based line number.

    """
    lo, hi = 0, len(line_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def _extract_cmdlets(
    content: str, source_path: str
) -> list[dict[str, Any]]:
    """
    Extract PowerShell cmdlet invocations from script content.

    Args:
        content: Comment-stripped PowerShell text.
        source_path: Source file path for provenance.

    Returns:
        List of cmdlet dictionaries with ``name``, ``ansible_module``,
        ``parameters``, ``source_file``, and ``line`` keys.

    """
    line_starts = _build_line_index(content)
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    for match in _RE_CMDLET_CALL.finditer(content):
        name = match.group(1)
        params_raw = (match.group(2) or "").strip()
        line_num = _get_line_number(match.start(), line_starts)
        key = (name.lower(), line_num)
        if key in seen:
            continue
        seen.add(key)

        ansible_module = CMDLET_MODULE_MAP.get(name.lower())
        found.append(
            {
                "name": name,
                "ansible_module": ansible_module or "ansible.windows.win_shell",
                "supported": ansible_module is not None,
                "parameters_raw": params_raw[:200],
                "source_file": source_path,
                "line": line_num,
            }
        )
    return found


def _extract_functions(
    content: str, source_path: str
) -> list[dict[str, Any]]:
    """
    Extract PowerShell function definitions.

    Args:
        content: Comment-stripped PowerShell text.
        source_path: Source file path for provenance.

    Returns:
        List of function definition dictionaries.

    """
    line_starts = _build_line_index(content)
    functions = []
    for match in _RE_FUNCTION.finditer(content):
        functions.append(
            {
                "name": match.group(1),
                "params": match.group(2) or "",
                "source_file": source_path,
                "line": _get_line_number(match.start(), line_starts),
            }
        )
    return functions


def _extract_variables(
    content: str, source_path: str
) -> list[dict[str, Any]]:
    """
    Extract top-level variable assignments from script content.

    Args:
        content: Comment-stripped PowerShell text.
        source_path: Source file path for provenance.

    Returns:
        List of variable dictionaries.

    """
    line_starts = _build_line_index(content)
    seen_names: set[str] = set()
    variables = []
    for match in _RE_VARIABLE.finditer(content):
        name = match.group(1)
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        variables.append(
            {
                "name": f"${name}",
                "value_snippet": match.group(2).strip()[:100],
                "source_file": source_path,
                "line": _get_line_number(match.start(), line_starts),
            }
        )
    return variables


def _extract_module_imports(
    content: str, source_path: str
) -> list[dict[str, Any]]:
    """
    Extract PowerShell module imports (Import-Module and #Requires).

    Args:
        content: Comment-stripped PowerShell text.
        source_path: Source file path for provenance.

    Returns:
        List of module import dictionaries.

    """
    line_starts = _build_line_index(content)
    modules: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pattern, import_type in [
        (_RE_IMPORT_MODULE, "Import-Module"),
        (_RE_REQUIRES_MODULE, "#Requires"),
    ]:
        for match in pattern.finditer(content):
            name = match.group(1).strip().rstrip(",")
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            modules.append(
                {
                    "name": name,
                    "import_type": import_type,
                    "source_file": source_path,
                    "line": _get_line_number(match.start(), line_starts),
                }
            )
    return modules


def _detect_unsupported_constructs(
    content: str, source_path: str
) -> list[dict[str, Any]]:
    """
    Detect PowerShell constructs that cannot be automatically converted.

    Args:
        content: Raw PowerShell script text (including comments, for context).
        source_path: Source file path for provenance.

    Returns:
        List of unsupported construct dictionaries.

    """
    line_starts = _build_line_index(content)
    unsupported = []
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


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------


def _format_cmdlets_section(
    parts: list[str], cmdlets: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Append the cmdlets section to *parts* and return (supported, unsupported) lists.

    Args:
        parts: Mutable list of strings to append to.
        cmdlets: List of parsed cmdlet dictionaries.

    Returns:
        Tuple of (supported_cmdlets, unsupported_cmdlets) lists.

    """
    supported = [c for c in cmdlets if c.get("supported")]
    unsupported_cmdlets = [c for c in cmdlets if not c.get("supported")]

    parts.append(
        f"Cmdlet Invocations ({len(cmdlets)} total, "
        f"{len(supported)} directly mappable):"
    )
    if cmdlets:
        for c in cmdlets[:50]:
            tag = "" if c.get("supported") else " [needs manual review]"
            parts.append(
                f"  {c['name']} → {c['ansible_module']}"
                f"  [line {c['line']}]{tag}"
            )
        if len(cmdlets) > 50:
            parts.append(f"  ... and {len(cmdlets) - 50} more")
    else:
        parts.append("  (none detected)")

    return supported, unsupported_cmdlets


def _format_script_results(results: dict[str, Any], source_path: str) -> str:
    """
    Format parsed script results as a human-readable report string.

    Args:
        results: Parsed data dictionary from :func:`_parse_script_content`.
        source_path: Source file or directory path (used in heading).

    Returns:
        Formatted multi-line string report.

    """
    cmdlets = results.get("cmdlets", [])
    functions = results.get("functions", [])
    variables = results.get("variables", [])
    modules = results.get("modules", [])
    unsupported = results.get("unsupported", [])

    parts: list[str] = [
        f"PowerShell Script Analysis: {source_path}",
        "=" * 60,
        "",
    ]

    supported, unsupported_cmdlets = _format_cmdlets_section(parts, cmdlets)

    # Functions
    parts.append("")
    parts.append(f"Function Definitions ({len(functions)}):")
    if functions:
        for f in functions:
            parts.append(f"  {f['name']}()  [line {f['line']}]")
    else:
        parts.append("  (none detected)")

    # Modules
    parts.append("")
    parts.append(f"Module Imports ({len(modules)}):")
    if modules:
        for m in modules:
            parts.append(f"  {m['import_type']}: {m['name']}  [line {m['line']}]")
    else:
        parts.append("  (none detected)")

    # Variables
    parts.append("")
    parts.append(f"Variables ({len(variables)}):")
    if variables:
        for v in variables[:20]:
            parts.append(f"  {v['name']} = {v['value_snippet']}  [line {v['line']}]")
        if len(variables) > 20:
            parts.append(f"  ... and {len(variables) - 20} more")
    else:
        parts.append("  (none detected)")

    # Unsupported constructs
    parts.append("")
    _format_unsupported_section(parts, unsupported)

    # Summary
    parts.extend(
        [
            "",
            "Summary:",
            f"  Cmdlets:              {len(cmdlets)}",
            f"  Directly mappable:    {len(supported)}",
            f"  Needs manual review:  {len(unsupported_cmdlets)}",
            f"  Functions:            {len(functions)}",
            f"  Module imports:       {len(modules)}",
            f"  Unsupported constructs: {len(unsupported)}",
        ]
    )
    if unsupported:
        parts.append("  NOTE: Review unsupported constructs before migration.")

    return "\n".join(parts)


def _format_unsupported_section(
    parts: list[str], unsupported: list[dict[str, Any]]
) -> None:
    """
    Append the unsupported constructs section to the report parts list.

    Args:
        parts: Mutable list of string parts to append to.
        unsupported: List of unsupported construct dicts.

    """
    count = len(unsupported)
    parts.append(f"Unsupported Constructs ({count}):")
    if unsupported:
        for item in unsupported:
            parts.append(
                f"  [{item['construct']}] at {item['source_file']}:{item['line']}"
                f" — {item['text']!r}"
            )
    else:
        parts.append("  none detected")


def get_powershell_ansible_module_map() -> dict[str, str]:
    """
    Return the mapping of PowerShell cmdlets to Ansible modules.

    Returns:
        Dictionary mapping PowerShell cmdlet names to Ansible module names.

    """
    return dict(CMDLET_MODULE_MAP)


def get_supported_powershell_cmdlets() -> list[str]:
    """
    Return the sorted list of cmdlets that map directly to Ansible modules.

    Returns:
        Sorted list of supported PowerShell cmdlet names.

    """
    return sorted(CMDLET_MODULE_MAP.keys())
