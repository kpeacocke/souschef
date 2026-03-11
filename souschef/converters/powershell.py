"""
PowerShell to Ansible Windows module converter.

Converts structured PowerShell provisioning actions (produced by
:mod:`souschef.parsers.powershell`) into equivalent Ansible tasks targeting
Windows managed nodes.  Uses ``ansible.windows.*`` collection modules where
available to ensure idempotency; falls back to ``ansible.windows.win_shell``
for unrecognised fragments with warnings.

Mapping decisions follow the acceptance criteria from GitHub issue #206:

- Uses ``ansible.windows`` modules when available
- Ensures idempotency for registry / service / feature cases
- Unknown fragments fall back to ``win_shell`` with warnings + source locations
"""

from __future__ import annotations

import json
from typing import Any

import yaml

from souschef.parsers.powershell import (
    _parse_powershell_content,
    parse_powershell_script,
)

# ---------------------------------------------------------------------------
# Windows module mappings
# ---------------------------------------------------------------------------

#: Maps parsed action types to ansible.windows module names
_MODULE_MAP: dict[str, str] = {
    "windows_feature_install": "ansible.windows.win_feature",
    "windows_feature_remove": "ansible.windows.win_feature",
    "windows_optional_feature_enable": "ansible.windows.win_optional_feature",
    "windows_optional_feature_disable": "ansible.windows.win_optional_feature",
    "windows_service_start": "ansible.windows.win_service",
    "windows_service_stop": "ansible.windows.win_service",
    "windows_service_configure": "ansible.windows.win_service",
    "windows_service_create": "ansible.windows.win_service",
    "registry_set": "ansible.windows.win_regedit",
    "registry_create_key": "ansible.windows.win_regedit",
    "registry_remove_key": "ansible.windows.win_regedit",
    "file_copy": "ansible.windows.win_copy",
    "directory_create": "ansible.windows.win_file",
    "file_remove": "ansible.windows.win_file",
    "file_write": "ansible.windows.win_copy",
    "msi_install": "ansible.windows.win_package",
    "chocolatey_install": "chocolatey.chocolatey.win_chocolatey",
    "chocolatey_uninstall": "chocolatey.chocolatey.win_chocolatey",
    "win_shell": "ansible.windows.win_shell",
}

#: Startup type mapping from PowerShell to Ansible
_STARTUP_TYPE_MAP: dict[str, str] = {
    "automatic": "auto",
    "manual": "manual",
    "disabled": "disabled",
    "delayed": "delayed",
}

#: Registry hive normalisation (short -> win_regedit hive)
_REG_HIVE_MAP: dict[str, str] = {
    "HKLM": "HKLM",
    "HKCU": "HKCU",
    "HKEY_LOCAL_MACHINE": "HKLM",
    "HKEY_CURRENT_USER": "HKCU",
    "HKEY_CLASSES_ROOT": "HKCR",
    "HKEY_USERS": "HKU",
    "HKEY_CURRENT_CONFIG": "HKCC",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert_powershell_to_ansible(
    script_path: str,
    playbook_name: str = "powershell_migration",
    hosts: str = "windows",
) -> str:
    """
    Convert a PowerShell provisioning script to an Ansible playbook.

    Parses the script, maps each recognised action to an appropriate
    ``ansible.windows`` module task, and serialises the result as a YAML
    Ansible playbook.

    Args:
        script_path: Path to the ``.ps1`` PowerShell script file.
        playbook_name: Name to use for the generated playbook (used in the
            ``name`` field of the play).
        hosts: Ansible inventory group / host pattern for the play.

    Returns:
        JSON string with keys:

        - ``status``: ``"success"`` or ``"error"``.
        - ``playbook_yaml``: the generated Ansible playbook as YAML text.
        - ``tasks_generated``: number of tasks generated.
        - ``win_shell_fallbacks``: number of low-confidence win_shell tasks.
        - ``warnings``: list of warning messages.
        - ``source``: absolute path of the parsed file.

    """
    parsed_json = parse_powershell_script(script_path)
    if parsed_json.startswith("Error"):
        return json.dumps({"status": "error", "error": parsed_json}, indent=2)

    parsed = json.loads(parsed_json)
    return _build_conversion_result(parsed, playbook_name, hosts)


def convert_powershell_content_to_ansible(
    content: str,
    playbook_name: str = "powershell_migration",
    hosts: str = "windows",
    source: str = "<inline>",
) -> str:
    """
    Convert PowerShell script content (string) to an Ansible playbook.

    Useful when the script content is already in memory rather than on disk.

    Args:
        content: PowerShell script text.
        playbook_name: Name to use for the generated playbook.
        hosts: Ansible inventory group / host pattern for the play.
        source: Optional label for the source shown in the output.

    Returns:
        JSON string with the same schema as
        :func:`convert_powershell_to_ansible`.

    """
    parsed = _parse_powershell_content(content, source)
    return _build_conversion_result(parsed, playbook_name, hosts)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_conversion_result(
    parsed: dict[str, Any],
    playbook_name: str,
    hosts: str,
) -> str:
    """Build the final JSON result from parsed IR."""
    actions: list[dict[str, Any]] = parsed.get("actions", [])
    source: str = parsed.get("source", "<unknown>")
    parse_warnings: list[str] = parsed.get("warnings", [])

    tasks: list[dict[str, Any]] = []
    conversion_warnings: list[str] = list(parse_warnings)
    win_shell_count = 0

    for action in actions:
        task, warning = _action_to_task(action)
        tasks.append(task)
        if warning:
            conversion_warnings.append(warning)
        if action.get("action_type") == "win_shell":
            win_shell_count += 1

    playbook = _build_playbook(playbook_name, hosts, tasks)
    playbook_yaml = yaml.dump(playbook, default_flow_style=False, allow_unicode=True)

    return json.dumps(
        {
            "status": "success",
            "source": source,
            "playbook_yaml": playbook_yaml,
            "tasks_generated": len(tasks),
            "win_shell_fallbacks": win_shell_count,
            "warnings": conversion_warnings,
        },
        indent=2,
    )


def _build_playbook(
    name: str, hosts: str, tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Wrap tasks in an Ansible play structure."""
    return [
        {
            "name": name,
            "hosts": hosts,
            "gather_facts": False,
            "tasks": tasks,
        }
    ]


def _action_to_task(
    action: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """
    Convert a single parsed action to an Ansible task dict.

    Args:
        action: Parsed action dict from :mod:`souschef.parsers.powershell`.

    Returns:
        A tuple of (task_dict, warning_string).  ``warning_string`` is an
        empty string when no warning is needed.

    """
    action_type: str = action.get("action_type", "win_shell")
    params: dict[str, Any] = action.get("params", {})
    src_line: int = action.get("source_line", 0)
    raw: str = action.get("raw", "")

    module = _MODULE_MAP.get(action_type, "ansible.windows.win_shell")
    warning = ""

    converter = _TASK_CONVERTERS.get(action_type)
    if converter:
        task_name, module_args = converter(params, raw)
    else:
        # Unknown action type – use win_shell fallback
        task_name = f"Execute shell command (line {src_line})"
        module_args = {"cmd": raw}
        warning = (
            f"Line {src_line}: No module mapping for action type '{action_type}' "
            f"– using win_shell fallback. Review manually."
        )

    task: dict[str, Any] = {"name": task_name, module: module_args}

    if action.get("requires_elevation"):
        task["become"] = True
        task["become_method"] = "runas"
        task["become_user"] = "SYSTEM"

    if action.get("confidence") == "low" and not warning:
        warning = (
            f"Line {src_line}: Low-confidence win_shell task – review manually: "
            f"{raw[:60]}"
        )

    return task, warning


# ---------------------------------------------------------------------------
# Per-action-type converter functions
# ---------------------------------------------------------------------------


def _convert_windows_feature_install(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_feature_install to win_feature task args."""
    feature = params.get("feature_name", "unknown")
    return (
        f"Install Windows feature: {feature}",
        {"name": feature, "state": "present", "include_management_tools": True},
    )


def _convert_windows_feature_remove(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_feature_remove to win_feature task args."""
    feature = params.get("feature_name", "unknown")
    return (
        f"Remove Windows feature: {feature}",
        {"name": feature, "state": "absent"},
    )


def _convert_optional_feature_enable(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_optional_feature_enable to win_optional_feature args."""
    feature = params.get("feature_name", "unknown")
    return (
        f"Enable optional Windows feature: {feature}",
        {"name": feature, "state": "enabled"},
    )


def _convert_optional_feature_disable(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_optional_feature_disable to win_optional_feature args."""
    feature = params.get("feature_name", "unknown")
    return (
        f"Disable optional Windows feature: {feature}",
        {"name": feature, "state": "disabled"},
    )


def _convert_service_start(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_service_start to win_service task args."""
    svc = params.get("service_name", "unknown")
    return (
        f"Start service: {svc}",
        {"name": svc, "state": "started"},
    )


def _convert_service_stop(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_service_stop to win_service task args."""
    svc = params.get("service_name", "unknown")
    return (
        f"Stop service: {svc}",
        {"name": svc, "state": "stopped"},
    )


def _convert_service_configure(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_service_configure to win_service task args."""
    svc = params.get("service_name", "unknown")
    startup = _STARTUP_TYPE_MAP.get(
        params.get("startup_type", "").lower(), "auto"
    )
    return (
        f"Configure service startup: {svc}",
        {"name": svc, "start_mode": startup},
    )


def _convert_service_create(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert windows_service_create to win_service task args."""
    svc = params.get("service_name", "unknown")
    args: dict[str, Any] = {"name": svc, "state": "started"}
    if "binary_path" in params:
        args["path"] = params["binary_path"]
    return (f"Create service: {svc}", args)


def _convert_registry_set(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert registry_set to win_regedit task args."""
    key = params.get("key", "")
    name = params.get("name", "")
    value = params.get("value", "")
    hive, subkey = _split_registry_key(key)
    return (
        f"Set registry value: {key}\\{name}",
        {
            "path": f"{hive}:{subkey}",
            "name": name,
            "data": value,
            "state": "present",
        },
    )


def _convert_registry_create_key(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert registry_create_key to win_regedit task args."""
    key = params.get("key", "")
    hive, subkey = _split_registry_key(key)
    return (
        f"Create registry key: {key}",
        {"path": f"{hive}:{subkey}", "state": "present"},
    )


def _convert_registry_remove_key(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert registry_remove_key to win_regedit task args."""
    key = params.get("key", "")
    hive, subkey = _split_registry_key(key)
    return (
        f"Remove registry key: {key}",
        {"path": f"{hive}:{subkey}", "state": "absent"},
    )


def _convert_file_copy(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert file_copy to win_copy task args."""
    src = params.get("src", "")
    dest = params.get("dest", "")
    return (
        f"Copy file: {src} -> {dest}",
        {"src": src, "dest": dest},
    )


def _convert_directory_create(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert directory_create to win_file task args."""
    path = params.get("path", "")
    return (
        f"Create directory: {path}",
        {"path": path, "state": "directory"},
    )


def _convert_file_remove(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert file_remove to win_file task args."""
    path = params.get("path", "")
    return (
        f"Remove file or directory: {path}",
        {"path": path, "state": "absent"},
    )


def _convert_file_write(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert file_write to win_copy task args (inline content)."""
    path = params.get("path", "")
    content = params.get("content", "")
    return (
        f"Write file content: {path}",
        {"dest": path, "content": content},
    )


def _convert_msi_install(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert msi_install to win_package task args."""
    pkg_path = params.get("package_path", "")
    return (
        f"Install MSI package: {pkg_path}",
        {"path": pkg_path, "state": "present"},
    )


def _convert_chocolatey_install(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert chocolatey_install to win_chocolatey task args."""
    pkg = params.get("package_name", "unknown")
    return (
        f"Install Chocolatey package: {pkg}",
        {"name": pkg, "state": "present"},
    )


def _convert_chocolatey_uninstall(
    params: dict[str, Any], _raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert chocolatey_uninstall to win_chocolatey task args."""
    pkg = params.get("package_name", "unknown")
    return (
        f"Uninstall Chocolatey package: {pkg}",
        {"name": pkg, "state": "absent"},
    )


def _convert_win_shell(
    params: dict[str, Any], raw: str
) -> tuple[str, dict[str, Any]]:
    """Convert win_shell fallback to win_shell task args."""
    cmd = params.get("command", raw)
    return (
        f"Execute command: {cmd[:50]}",
        {"cmd": cmd},
    )


#: Dispatch table mapping action_type -> converter function
_TASK_CONVERTERS: dict[
    str,
    Any,
] = {
    "windows_feature_install": _convert_windows_feature_install,
    "windows_feature_remove": _convert_windows_feature_remove,
    "windows_optional_feature_enable": _convert_optional_feature_enable,
    "windows_optional_feature_disable": _convert_optional_feature_disable,
    "windows_service_start": _convert_service_start,
    "windows_service_stop": _convert_service_stop,
    "windows_service_configure": _convert_service_configure,
    "windows_service_create": _convert_service_create,
    "registry_set": _convert_registry_set,
    "registry_create_key": _convert_registry_create_key,
    "registry_remove_key": _convert_registry_remove_key,
    "file_copy": _convert_file_copy,
    "directory_create": _convert_directory_create,
    "file_remove": _convert_file_remove,
    "file_write": _convert_file_write,
    "msi_install": _convert_msi_install,
    "chocolatey_install": _convert_chocolatey_install,
    "chocolatey_uninstall": _convert_chocolatey_uninstall,
    "win_shell": _convert_win_shell,
}


# ---------------------------------------------------------------------------
# Registry key helpers
# ---------------------------------------------------------------------------


def _split_registry_key(key: str) -> tuple[str, str]:
    r"""
    Split a registry key path into (hive, subkey).

    Normalises long hive names (e.g. HKEY_LOCAL_MACHINE) to short forms
    (HKLM) and returns a tuple ``(hive, subkey)`` where *subkey* starts
    with a backslash.

    Args:
        key: Full registry key path, e.g. ``HKLM:\\SOFTWARE\\Microsoft``.

    Returns:
        Tuple of (normalised_hive, subkey_path).

    """
    # Normalise separator: replace / with \\
    normalised = key.replace("/", "\\")
    # Replace :: with \\ (HKLM::SOFTWARE style)
    normalised = normalised.replace("::", "\\")
    # Replace single colon separator
    normalised = normalised.replace(":\\", "\\")

    parts = normalised.split("\\", 1)
    raw_hive = parts[0].upper()
    hive = _REG_HIVE_MAP.get(raw_hive, raw_hive)
    subkey = f"\\{parts[1]}" if len(parts) > 1 else "\\"
    return hive, subkey
