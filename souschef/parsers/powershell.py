"""
PowerShell script parser for Chef-to-Ansible migration.

Parses PowerShell provisioning scripts and extracts structured actions
(Windows features, services, registry operations, file operations,
MSI installs, Chocolatey installs, user management, firewall rules,
scheduled tasks, environment variables, certificates, WinRM, IIS, DNS,
and ACL operations) that can be converted to Ansible tasks.

Actions with recognised patterns produce structured IR entries; unrecognised
fragments are preserved as raw ``win_shell`` fallbacks with source locations
and confidence warnings.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from souschef.core.constants import ERROR_FILE_NOT_FOUND, ERROR_PERMISSION_DENIED
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
    safe_read_text,
)

# ---------------------------------------------------------------------------
# Regex patterns for PowerShell provisioning actions
# ---------------------------------------------------------------------------

# Windows Features (Install-WindowsFeature / Enable-WindowsOptionalFeature)
_RE_INSTALL_WINDOWS_FEATURE = re.compile(
    r"(?<!\w)(?:Install-WindowsFeature|Add-WindowsFeature)"
    r"\s+(?:-Name\s+)?[\"']?(?P<feature>[\w\-]+)[\"']?"
    r"(?:.*?-IncludeManagementTools)?",
    re.IGNORECASE,
)
_RE_ENABLE_OPTIONAL_FEATURE = re.compile(
    r"Enable-WindowsOptionalFeature\s+(?:-Online\s+)?(?:-FeatureName\s+)?[\"']?(?P<feature>[\w\-]+)[\"']?",
    re.IGNORECASE,
)
_RE_REMOVE_WINDOWS_FEATURE = re.compile(
    r"(?:Remove-WindowsFeature|Uninstall-WindowsFeature)\s+(?:-Name\s+)?[\"']?(?P<feature>[\w\-]+)[\"']?",
    re.IGNORECASE,
)
_RE_DISABLE_OPTIONAL_FEATURE = re.compile(
    r"Disable-WindowsOptionalFeature\s+(?:-Online\s+)?(?:-FeatureName\s+)?[\"']?(?P<feature>[\w\-]+)[\"']?",
    re.IGNORECASE,
)

# Windows Services (Start-Service / Stop-Service / Set-Service)
_RE_START_SERVICE = re.compile(
    r"Start-Service\s+(?:-Name\s+)?[\"']?(?P<service>[\w\-\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_STOP_SERVICE = re.compile(
    r"Stop-Service\s+(?:-Name\s+)?[\"']?(?P<service>[\w\-\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_SET_SERVICE = re.compile(
    r"Set-Service\s+(?:-Name\s+)?[\"']?(?P<service>[\w\-\.]+)[\"']?"
    r".*?-StartupType\s+(?P<startup>Automatic|Manual|Disabled)",
    re.IGNORECASE,
)
_RE_NEW_SERVICE = re.compile(
    r"New-Service\s+(?:-Name\s+)?[\"']?(?P<service>[\w\-\.]+)[\"']?"
    r"(?:.*?-BinaryPathName\s+[\"']?(?P<path>[^\"'\s;]+)[\"']?)?",
    re.IGNORECASE,
)

# Registry operations (Set-ItemProperty, New-Item, Remove-Item on HKLM/HKCU)
_RE_SET_REG_PROPERTY = re.compile(
    r"Set-ItemProperty\s+(?:-Path\s+)?[\"']?(?P<key>(?:HKLM|HKCU|HKEY_[A-Z_]+)[:\\][^\"'\s;,]+)[\"']?"
    r"\s+(?:-Name\s+)?[\"']?(?P<name>[\w\-\s]+)[\"']?"
    r"\s+(?:-Value\s+)?[\"']?(?P<value>[^\"'\n;]+)[\"']?",
    re.IGNORECASE,
)
_RE_NEW_REG_KEY = re.compile(
    r"New-Item\s+(?:-Path\s+)?[\"']?(?P<key>(?:HKLM|HKCU|HKEY_[A-Z_]+)[:\\][^\"'\s;,]+)[\"']?",
    re.IGNORECASE,
)
_RE_REMOVE_REG_KEY = re.compile(
    r"Remove-Item\s+(?:-Path\s+)?[\"']?(?P<key>(?:HKLM|HKCU|HKEY_[A-Z_]+)[:\\][^\"'\s;,]+)[\"']?",
    re.IGNORECASE,
)

# File operations
_RE_COPY_ITEM = re.compile(
    r"Copy-Item\s+(?:-Path\s+)?[\"']?(?P<src>[^\"'\s;,]+)[\"']?"
    r"\s+(?:-Destination\s+)?[\"']?(?P<dest>[^\"'\s;,]+)[\"']?",
    re.IGNORECASE,
)
_RE_NEW_ITEM_DIR = re.compile(
    r"New-Item\s+(?:-Path\s+)?[\"']?(?P<path>[^\"'\s;,]+)[\"']?"
    r".*?-ItemType\s+(?:Directory|Folder)",
    re.IGNORECASE,
)
_RE_REMOVE_ITEM = re.compile(
    r"Remove-Item\s+(?:-Path\s+)?[\"']?(?P<path>[^\"'\s;,]+(?:\.[a-z0-9]+)?)[\"']?",
    re.IGNORECASE,
)
_RE_SET_CONTENT = re.compile(
    r"Set-Content\s+(?:-Path\s+)?[\"']?(?P<path>[^\"'\s;,]+)[\"']?"
    r"\s+(?:-Value\s+)?[\"']?(?P<content>[^\"'\n]+)[\"']?",
    re.IGNORECASE,
)

# MSI installs via Start-Process / msiexec
_RE_MSI_INSTALL = re.compile(
    r"(?:Start-Process\s+msiexec|msiexec\.exe?)\s+.*?(?:/i|/package)\s+[\"']?(?P<path>[^\"'\s;]+)[\"']?",
    re.IGNORECASE,
)

# Chocolatey installs
_RE_CHOCO_INSTALL = re.compile(
    r"(?:choco(?:latey)?(?:\.exe?)?\s+)?Install-Package\s+[\"']?(?P<package>[\w\.\-]+)[\"']?"
    r"|choco(?:latey)?(?:\.exe?)?\s+install\s+[\"']?(?P<choco_package>[\w\.\-]+)[\"']?",
    re.IGNORECASE,
)
_RE_CHOCO_UNINSTALL = re.compile(
    r"choco(?:latey)?(?:\.exe?)?\s+uninstall\s+[\"']?(?P<package>[\w\.\-]+)[\"']?",
    re.IGNORECASE,
)

# User management
_RE_NEW_LOCAL_USER = re.compile(
    r"New-LocalUser\s+(?:-Name\s+)?[\"']?(?P<username>[\w\-\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_SET_LOCAL_USER = re.compile(
    r"Set-LocalUser\s+(?:-Name\s+)?[\"']?(?P<username>[\w\-\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_REMOVE_LOCAL_USER = re.compile(
    r"Remove-LocalUser\s+(?:-Name\s+)?[\"']?(?P<username>[\w\-\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_ADD_LOCAL_GROUP_MEMBER = re.compile(
    r"Add-LocalGroupMember\s+(?:-Group\s+)?[\"']?(?P<group>[\w\-\s]+?)[\"']?"
    r"\s+-Member\s+[\"']?(?P<member>[\w\-\.\\]+)[\"']?",
    re.IGNORECASE,
)
_RE_REMOVE_LOCAL_GROUP_MEMBER = re.compile(
    r"Remove-LocalGroupMember\s+(?:-Group\s+)?[\"']?(?P<group>[\w\-\s]+?)[\"']?"
    r"\s+-Member\s+[\"']?(?P<member>[\w\-\.\\]+)[\"']?",
    re.IGNORECASE,
)

# Firewall rules
_RE_NEW_FIREWALL_RULE = re.compile(
    r"New-NetFirewallRule\s+(?:-DisplayName\s+|-Name\s+)?[\"']?(?P<name>[\w\-\s\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_ENABLE_FIREWALL_RULE = re.compile(
    r"Enable-NetFirewallRule\s+(?:-DisplayName\s+|-Name\s+)?[\"']?(?P<name>[\w\-\s\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_DISABLE_FIREWALL_RULE = re.compile(
    r"Disable-NetFirewallRule\s+(?:-DisplayName\s+|-Name\s+)?[\"']?(?P<name>[\w\-\s\.]+)[\"']?",
    re.IGNORECASE,
)
_RE_REMOVE_FIREWALL_RULE = re.compile(
    r"Remove-NetFirewallRule\s+(?:-DisplayName\s+|-Name\s+)?[\"']?(?P<name>[\w\-\s\.]+)[\"']?",
    re.IGNORECASE,
)

# Scheduled tasks
_RE_REGISTER_SCHEDULED_TASK = re.compile(
    r"(?<!Un)Register-ScheduledTask\s+(?:-TaskName\s+)?[\"']?(?P<taskname>[\w\-\s\.\\]+)[\"']?",
    re.IGNORECASE,
)
_RE_UNREGISTER_SCHEDULED_TASK = re.compile(
    r"Unregister-ScheduledTask\s+(?:-TaskName\s+)?[\"']?(?P<taskname>[\w\-\s\.\\]+)[\"']?",
    re.IGNORECASE,
)

# Environment variables
_RE_SET_ENV_VAR = re.compile(
    r"\[(?:System\.)?Environment\]::SetEnvironmentVariable\s*\([\"'](?P<varname>[\w\-\.]+)[\"']\s*,\s*[\"']?(?P<value>[^\"',)]+)[\"']?",
    re.IGNORECASE,
)
_RE_SET_ENV_ITEM = re.compile(
    r"Set-Item\s+Env:(?P<varname>[\w\-\.]+)\s+[\"']?(?P<value>[^\"'\s;]+)[\"']?",
    re.IGNORECASE,
)

# PowerShell modules
_RE_INSTALL_MODULE = re.compile(
    r"Install-Module\s+(?:-Name\s+)?[\"']?(?P<module>[\w\-\.]+)[\"']?",
    re.IGNORECASE,
)

# Certificates
_RE_IMPORT_CERTIFICATE = re.compile(
    r"(?:Import-Certificate|Import-PfxCertificate)\s+.*?(?:-FilePath\s+)?[\"']?(?P<path>[^\"'\s;,]+\.(?:cer|pfx|p12|crt))[\"']?",
    re.IGNORECASE,
)

# WinRM / remoting
_RE_ENABLE_PSREMOTING = re.compile(
    r"(?:Enable-PSRemoting|winrm\s+(?:quickconfig|set|create))",
    re.IGNORECASE,
)

# IIS
_RE_NEW_WEBSITE = re.compile(
    r"New-WebSite\s+(?:-Name\s+)?[\"']?(?P<sitename>[\w\-\s\.]+)[\"']?",
    re.IGNORECASE,
)

# DNS client
_RE_SET_DNS_CLIENT = re.compile(
    r"Set-DnsClientServerAddress\s+.*?-ServerAddresses\s+[\"']?(?P<addresses>[0-9a-f\.:,\s\[\]]+)(?=\s*(?:-|$))",
    re.IGNORECASE,
)

# ACL
_RE_SET_ACL = re.compile(
    r"(?:Set-Acl|icacls\.exe?)\s+[\"']?(?P<path>[^\"'\s;]+)[\"']?",
    re.IGNORECASE,
)

# Elevation requirement: commands that need admin
_ELEVATION_PATTERNS = re.compile(
    r"Install-WindowsFeature|Enable-WindowsOptionalFeature|New-Service|"
    r"Set-Service|msiexec|New-Item\s+.*HKLM|Set-ItemProperty\s+.*HKLM|"
    r"New-LocalUser|Remove-LocalUser|Add-LocalGroupMember|Remove-LocalGroupMember|"
    r"New-NetFirewallRule|Enable-NetFirewallRule|Disable-NetFirewallRule|"
    r"Remove-NetFirewallRule|Register-ScheduledTask|Unregister-ScheduledTask|"
    r"Enable-PSRemoting|winrm\s+quickconfig|Import-Certificate|Import-PfxCertificate|"
    r"New-WebSite|Set-Acl|icacls|Install-Module",
    re.IGNORECASE,
)

# Comment / blank lines to skip
_RE_COMMENT = re.compile(r"^\s*#")
_RE_BLANK = re.compile(r"^\s*$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_powershell_script(script_path: str) -> str:
    """
    Parse a PowerShell provisioning script and extract structured actions.

    Analyses the script line by line using pattern matching to identify
    common Windows provisioning operations.  Each recognised action is
    returned as a structured entry in the intermediate representation (IR).
    Unrecognised lines are captured as raw ``win_shell`` fallbacks.

    Args:
        script_path: Path to the ``.ps1`` PowerShell script file.

    Returns:
        JSON string containing the parsed IR with the following top-level
        keys:

        - ``source``: absolute path of the parsed file.
        - ``actions``: list of structured action dicts.
        - ``warnings``: list of warning messages (e.g. unrecognised lines).
        - ``metrics``: summary counts per action type.

    """
    try:
        normalized_path = _normalize_path(script_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)
        if not safe_path.exists():  # NOSONAR
            return ERROR_FILE_NOT_FOUND.format(path=safe_path)
        if safe_path.is_dir():
            return f"Error: Path is a directory, expected a .ps1 file: {safe_path}"

        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")
        result = _parse_powershell_content(content, str(safe_path))
        return json.dumps(result, indent=2)

    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=script_path)
    except Exception as e:
        return f"Error parsing PowerShell script: {e}"


def parse_powershell_content(content: str, source: str = "<inline>") -> str:
    """
    Parse PowerShell script content (string) and extract structured actions.

    Useful when the script content is already in memory rather than on disk.

    Args:
        content: PowerShell script text to parse.
        source: Optional label for the source (shown in IR output).

    Returns:
        JSON string with the same schema as :func:`parse_powershell_script`.

    """
    result = _parse_powershell_content(content, source)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_POWERSHELL_AST_QUERY = (
    "$content=[Console]::In.ReadToEnd();"
    "$tokens=$null;"
    "$errors=$null;"
    "$ast=[System.Management.Automation.Language.Parser]::ParseInput("
    "$content,[ref]$tokens,[ref]$errors);"
    "$commands=$ast.FindAll({param($n)"
    "$n -is [System.Management.Automation.Language.CommandAst]},$true)"
    "| ForEach-Object {"
    "[pscustomobject]@{"
    "text=$_.Extent.Text;"
    "line=[int]$_.Extent.StartLineNumber"
    "}"
    "};"
    "$commands | ConvertTo-Json -Compress -Depth 5"
)


def _extract_commands_with_ast(content: str) -> list[tuple[str, int]] | None:
    """Extract PowerShell command texts and source lines using PowerShell AST."""
    pwsh_path = shutil.which("pwsh")
    if not pwsh_path:
        return None

    result = subprocess.run(
        [
            pwsh_path,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _POWERSHELL_AST_QUERY,
        ],
        input=content,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return None

    commands: list[tuple[str, int]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        line = item.get("line")
        if isinstance(text, str) and isinstance(line, int):
            normalised = " ".join(text.splitlines()).strip()
            if normalised:
                commands.append((normalised, line))
    return commands


def _append_classified_or_fallback_action(
    actions: list[dict[str, Any]],
    warnings: list[str],
    metrics: dict[str, int],
    line: str,
    lineno: int,
) -> None:
    """Append a classified action or a win_shell fallback for one command."""
    action = _classify_line(line, lineno)
    if action is None:
        msg = (
            f"Line {lineno}: Unrecognised pattern – falling back to"
            f" win_shell: {line[:80]}"
        )
        warnings.append(msg)
        actions.append(_make_win_shell_fallback(line, lineno))
        metrics["win_shell_fallback"] += 1
        return

    actions.append(action)
    _increment_metric(metrics, action["action_type"])


def _parse_powershell_content(content: str, source: str) -> dict[str, Any]:
    """Parse PowerShell content and return the IR dict."""
    actions: list[dict[str, Any]] = []
    warnings: list[str] = []
    metrics: dict[str, int] = {
        "windows_feature": 0,
        "windows_service": 0,
        "registry": 0,
        "file": 0,
        "package": 0,
        "user": 0,
        "firewall": 0,
        "scheduled_task": 0,
        "environment": 0,
        "certificate": 0,
        "other_enterprise": 0,
        "win_shell_fallback": 0,
        "total_lines": 0,
        "skipped_lines": 0,
    }

    lines = content.splitlines()
    metrics["total_lines"] = len(lines)

    for raw_line in lines:
        stripped = raw_line.strip()
        if _RE_BLANK.match(stripped) or _RE_COMMENT.match(stripped):
            metrics["skipped_lines"] += 1

    parsed_with_ast = False
    ast_commands = _extract_commands_with_ast(content)

    command_stream: list[tuple[str, int]]
    if ast_commands is not None:
        parsed_with_ast = True
        command_stream = ast_commands
    else:
        command_stream = []
        for lineno, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if _RE_BLANK.match(line) or _RE_COMMENT.match(line):
                continue
            command_stream.append((line, lineno))

    for line, lineno in command_stream:
        _append_classified_or_fallback_action(
            actions,
            warnings,
            metrics,
            line,
            lineno,
        )

    return {
        "source": source,
        "actions": actions,
        "warnings": warnings,
        "metrics": metrics,
        "parser_backend": "ast" if parsed_with_ast else "regex",
    }


def _increment_metric(metrics: dict[str, int], action_type: str) -> None:
    """Increment the metric counter for a given action type."""
    category_map = {
        "windows_feature_install": "windows_feature",
        "windows_feature_remove": "windows_feature",
        "windows_optional_feature_enable": "windows_feature",
        "windows_optional_feature_disable": "windows_feature",
        "windows_service_start": "windows_service",
        "windows_service_stop": "windows_service",
        "windows_service_configure": "windows_service",
        "windows_service_create": "windows_service",
        "registry_set": "registry",
        "registry_create_key": "registry",
        "registry_remove_key": "registry",
        "file_copy": "file",
        "directory_create": "file",
        "file_remove": "file",
        "file_write": "file",
        "msi_install": "package",
        "chocolatey_install": "package",
        "chocolatey_uninstall": "package",
        "user_create": "user",
        "user_modify": "user",
        "user_remove": "user",
        "group_member_add": "user",
        "group_member_remove": "user",
        "firewall_rule_create": "firewall",
        "firewall_rule_enable": "firewall",
        "firewall_rule_disable": "firewall",
        "firewall_rule_remove": "firewall",
        "scheduled_task_register": "scheduled_task",
        "scheduled_task_unregister": "scheduled_task",
        "environment_set": "environment",
        "psmodule_install": "other_enterprise",
        "certificate_import": "certificate",
        "winrm_enable": "other_enterprise",
        "iis_website_create": "other_enterprise",
        "dns_client_set": "other_enterprise",
        "acl_set": "other_enterprise",
        "win_shell": "win_shell_fallback",
    }
    category = category_map.get(action_type, "win_shell_fallback")
    metrics[category] = metrics.get(category, 0) + 1


def _requires_elevation(line: str) -> bool:
    """Return True if the command typically requires elevated privileges."""
    return bool(_ELEVATION_PATTERNS.search(line))


def _classify_line(line: str, lineno: int) -> dict[str, Any] | None:
    """
    Attempt to classify a single PowerShell line as a known action.

    Returns an action dict if a pattern matches, or ``None`` if the line
    is not recognised.

    Args:
        line: Stripped script line.
        lineno: 1-based line number for source location metadata.

    Returns:
        Action dict or ``None``.

    """
    return (
        _classify_feature_line(line, lineno)
        or _classify_service_line(line, lineno)
        or _classify_registry_line(line, lineno)
        or _classify_file_line(line, lineno)
        or _classify_package_line(line, lineno)
        or _classify_user_line(line, lineno)
        or _classify_firewall_line(line, lineno)
        or _classify_enterprise_line(line, lineno)
    )


def _classify_feature_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify Windows feature installation/removal lines."""
    m = _RE_INSTALL_WINDOWS_FEATURE.search(line)
    if m:
        return _make_action(
            "windows_feature_install",
            {"feature_name": m.group("feature")},
            line,
            lineno,
        )

    m = _RE_ENABLE_OPTIONAL_FEATURE.search(line)
    if m:
        return _make_action(
            "windows_optional_feature_enable",
            {"feature_name": m.group("feature")},
            line,
            lineno,
        )

    m = _RE_REMOVE_WINDOWS_FEATURE.search(line)
    if m:
        return _make_action(
            "windows_feature_remove",
            {"feature_name": m.group("feature")},
            line,
            lineno,
        )

    m = _RE_DISABLE_OPTIONAL_FEATURE.search(line)
    if m:
        return _make_action(
            "windows_optional_feature_disable",
            {"feature_name": m.group("feature")},
            line,
            lineno,
        )

    return None


def _classify_service_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify Windows service management lines."""
    # New-Service must be checked before Set-Service to avoid partial match
    m = _RE_NEW_SERVICE.search(line)
    if m:
        params: dict[str, Any] = {"service_name": m.group("service")}
        if m.group("path"):
            params["binary_path"] = m.group("path")
        return _make_action("windows_service_create", params, line, lineno)

    m = _RE_SET_SERVICE.search(line)
    if m:
        return _make_action(
            "windows_service_configure",
            {
                "service_name": m.group("service"),
                "startup_type": m.group("startup").lower(),
            },
            line,
            lineno,
        )

    m = _RE_START_SERVICE.search(line)
    if m:
        return _make_action(
            "windows_service_start",
            {"service_name": m.group("service")},
            line,
            lineno,
        )

    m = _RE_STOP_SERVICE.search(line)
    if m:
        return _make_action(
            "windows_service_stop",
            {"service_name": m.group("service")},
            line,
            lineno,
        )

    return None


def _classify_registry_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify Windows registry operation lines."""
    m = _RE_SET_REG_PROPERTY.search(line)
    if m:
        return _make_action(
            "registry_set",
            {
                "key": m.group("key"),
                "name": m.group("name").strip(),
                "value": m.group("value").strip(),
            },
            line,
            lineno,
        )

    m = _RE_REMOVE_REG_KEY.search(line)
    if m and _is_registry_path(m.group("key")):
        return _make_action(
            "registry_remove_key",
            {"key": m.group("key")},
            line,
            lineno,
        )

    m = _RE_NEW_REG_KEY.search(line)
    if m and _is_registry_path(m.group("key")):
        return _make_action(
            "registry_create_key",
            {"key": m.group("key")},
            line,
            lineno,
        )

    return None


def _classify_file_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify file/directory operation lines."""
    # Directory creation before generic remove/copy
    m = _RE_NEW_ITEM_DIR.search(line)
    if m:
        return _make_action(
            "directory_create",
            {"path": m.group("path")},
            line,
            lineno,
        )

    m = _RE_COPY_ITEM.search(line)
    if m:
        return _make_action(
            "file_copy",
            {"src": m.group("src"), "dest": m.group("dest")},
            line,
            lineno,
        )

    m = _RE_SET_CONTENT.search(line)
    if m:
        return _make_action(
            "file_write",
            {"path": m.group("path"), "content": m.group("content").strip()},
            line,
            lineno,
        )

    m = _RE_REMOVE_ITEM.search(line)
    if m and not _is_registry_path(m.group("path")):
        return _make_action(
            "file_remove",
            {"path": m.group("path")},
            line,
            lineno,
        )

    return None


def _classify_package_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify package installation/removal lines (MSI, Chocolatey)."""
    m = _RE_MSI_INSTALL.search(line)
    if m:
        return _make_action(
            "msi_install",
            {"package_path": m.group("path")},
            line,
            lineno,
        )

    m = _RE_CHOCO_INSTALL.search(line)
    if m:
        pkg = m.group("package") or m.group("choco_package")
        return _make_action(
            "chocolatey_install",
            {"package_name": pkg},
            line,
            lineno,
        )

    m = _RE_CHOCO_UNINSTALL.search(line)
    if m:
        return _make_action(
            "chocolatey_uninstall",
            {"package_name": m.group("package")},
            line,
            lineno,
        )

    return None


def _classify_user_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify Windows local user management lines."""
    m = _RE_NEW_LOCAL_USER.search(line)
    if m:
        return _make_action(
            "user_create",
            {"username": m.group("username")},
            line,
            lineno,
        )

    m = _RE_SET_LOCAL_USER.search(line)
    if m:
        return _make_action(
            "user_modify",
            {"username": m.group("username")},
            line,
            lineno,
        )

    m = _RE_REMOVE_LOCAL_USER.search(line)
    if m:
        return _make_action(
            "user_remove",
            {"username": m.group("username")},
            line,
            lineno,
        )

    m = _RE_ADD_LOCAL_GROUP_MEMBER.search(line)
    if m:
        return _make_action(
            "group_member_add",
            {"group": m.group("group").strip(), "member": m.group("member").strip()},
            line,
            lineno,
        )

    m = _RE_REMOVE_LOCAL_GROUP_MEMBER.search(line)
    if m:
        return _make_action(
            "group_member_remove",
            {"group": m.group("group").strip(), "member": m.group("member").strip()},
            line,
            lineno,
        )

    return None


def _classify_firewall_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify Windows firewall rule lines."""
    m = _RE_NEW_FIREWALL_RULE.search(line)
    if m:
        return _make_action(
            "firewall_rule_create",
            {"rule_name": m.group("name").strip()},
            line,
            lineno,
        )

    m = _RE_ENABLE_FIREWALL_RULE.search(line)
    if m:
        return _make_action(
            "firewall_rule_enable",
            {"rule_name": m.group("name").strip()},
            line,
            lineno,
        )

    m = _RE_DISABLE_FIREWALL_RULE.search(line)
    if m:
        return _make_action(
            "firewall_rule_disable",
            {"rule_name": m.group("name").strip()},
            line,
            lineno,
        )

    m = _RE_REMOVE_FIREWALL_RULE.search(line)
    if m:
        return _make_action(
            "firewall_rule_remove",
            {"rule_name": m.group("name").strip()},
            line,
            lineno,
        )

    return None


def _classify_enterprise_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify enterprise Windows operations."""
    return _classify_task_env_line(line, lineno) or _classify_infra_line(line, lineno)


def _classify_task_env_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify scheduled task and environment variable lines."""
    m = _RE_REGISTER_SCHEDULED_TASK.search(line)
    if m:
        return _make_action(
            "scheduled_task_register",
            {"task_name": m.group("taskname").strip()},
            line,
            lineno,
        )

    m = _RE_UNREGISTER_SCHEDULED_TASK.search(line)
    if m:
        return _make_action(
            "scheduled_task_unregister",
            {"task_name": m.group("taskname").strip()},
            line,
            lineno,
        )

    m = _RE_SET_ENV_VAR.search(line)
    if m:
        return _make_action(
            "environment_set",
            {"name": m.group("varname"), "value": m.group("value").strip()},
            line,
            lineno,
        )

    m = _RE_SET_ENV_ITEM.search(line)
    if m:
        return _make_action(
            "environment_set",
            {"name": m.group("varname"), "value": m.group("value").strip()},
            line,
            lineno,
        )

    m = _RE_INSTALL_MODULE.search(line)
    if m:
        return _make_action(
            "psmodule_install",
            {"module_name": m.group("module")},
            line,
            lineno,
        )

    return None


def _classify_infra_line(line: str, lineno: int) -> dict[str, Any] | None:
    """Classify certificate, WinRM, IIS, DNS, and ACL lines."""
    m = _RE_IMPORT_CERTIFICATE.search(line)
    if m:
        return _make_action(
            "certificate_import",
            {"certificate_path": m.group("path")},
            line,
            lineno,
        )

    if _RE_ENABLE_PSREMOTING.search(line):
        return _make_action(
            "winrm_enable",
            {"raw_command": line},
            line,
            lineno,
        )

    m = _RE_NEW_WEBSITE.search(line)
    if m:
        return _make_action(
            "iis_website_create",
            {"site_name": m.group("sitename").strip()},
            line,
            lineno,
        )

    m = _RE_SET_DNS_CLIENT.search(line)
    if m:
        return _make_action(
            "dns_client_set",
            {"server_addresses": m.group("addresses").strip()},
            line,
            lineno,
        )

    m = _RE_SET_ACL.search(line)
    if m:
        return _make_action(
            "acl_set",
            {"path": m.group("path")},
            line,
            lineno,
        )

    return None


def _is_registry_path(path: str) -> bool:
    """Return True if *path* looks like a Windows registry path."""
    return bool(re.match(r"(?:HKLM|HKCU|HKEY_[A-Z_]+)[:\\]", path, re.IGNORECASE))


def _make_action(
    action_type: str,
    params: dict[str, Any],
    raw_line: str,
    lineno: int,
) -> dict[str, Any]:
    """Build a structured action dict."""
    return {
        "action_type": action_type,
        "params": params,
        "requires_elevation": _requires_elevation(raw_line),
        "source_line": lineno,
        "raw": raw_line,
        "confidence": "high",
    }


def _make_win_shell_fallback(line: str, lineno: int) -> dict[str, Any]:
    """Build a win_shell fallback action for unrecognised lines."""
    return {
        "action_type": "win_shell",
        "params": {"command": line},
        "requires_elevation": False,
        "source_line": lineno,
        "raw": line,
        "confidence": "low",
    }


# ---------------------------------------------------------------------------
# Convenience: parse from a Path object (internal use)
# ---------------------------------------------------------------------------


def _parse_script_from_path(path: Path) -> dict[str, Any]:
    """Parse a PowerShell script from a :class:`pathlib.Path` (internal)."""
    content = path.read_text(encoding="utf-8")
    return _parse_powershell_content(content, str(path))
