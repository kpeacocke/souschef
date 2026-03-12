"""
PowerShell to Ansible converter.

Converts parsed PowerShell scripts into Ansible task YAML targeting
Windows hosts, with full Ansible Automation Platform (AAP) integration
support including execution environments and Windows credential types.

Cmdlet mapping:

- ``Install-WindowsFeature`` → ``ansible.windows.win_feature``
- ``Set-Service`` / ``Start-Service`` → ``ansible.windows.win_service``
- ``New-Item`` / ``Copy-Item`` → ``ansible.windows.win_file`` /
  ``ansible.windows.win_copy``
- ``Set-ItemProperty`` / ``New-ItemProperty`` → ``ansible.windows.win_regedit``
- ``New-LocalUser`` → ``ansible.windows.win_user``
- ``New-NetFirewallRule`` → ``community.windows.win_firewall_rule``
- ``Register-ScheduledTask`` → ``community.windows.win_scheduled_task``
- ``Install-Package`` → ``ansible.windows.win_package``
- ``Invoke-Expression`` / ``Start-Process`` → ``ansible.windows.win_shell``
- Others → ``ansible.windows.win_shell`` with a comment

AI-Assisted Conversion
----------------------
For scripts with unsupported constructs (.NET P/Invoke, WMI, COM objects,
DSC Configuration blocks, etc.), the ``*_with_ai`` variants use a
configurable LLM to produce best-effort Ansible equivalents.  These functions
accept the same ``ai_provider``, ``api_key``, ``model``, ``temperature``,
``max_tokens``, ``project_id``, and ``base_url`` parameters as the Chef
recipe AI-assisted converters in :mod:`souschef.converters.playbook`.

Enterprise / AAP
----------------
The :func:`generate_windows_ee_definition` and
:func:`generate_aap_windows_credential_vars` helpers produce the ancillary
artefacts needed for an enterprise Windows AAP deployment:

- Execution Environment definition (``execution-environment.yml``)
- WinRM credential variable stubs
- Windows host inventory template
"""

import re
from pathlib import Path
from typing import Any

import yaml

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
from souschef.parsers.powershell import (
    CMDLET_MODULE_MAP,
    _parse_script_content,
    parse_powershell_script,
)

# Error prefix used for error detection in callers
_ERROR_PREFIX = "Error:"

# Maximum content length (bytes) sent to the LLM
_AI_MAX_CONTENT_CHARS = 40_000

# Maximum raw script content for safe processing
MAX_CONTENT_LENGTH = 2_000_000

# ---------------------------------------------------------------------------
# Cmdlet → Ansible task builder registry
# ---------------------------------------------------------------------------

# Maps lower-cased cmdlet name → builder function.
# Each builder accepts (title: str, params: dict) → task dict.
# The registry is populated after the builder functions are defined.
_CMDLET_BUILDERS: dict[str, Any] = {}


def _build_windows_play_header(script_name: str) -> dict[str, Any]:
    """
    Build a standard Ansible play header for Windows targets.

    Args:
        script_name: Name of the source script (used in the play name).

    Returns:
        Play-level dictionary ready to be serialised to YAML.

    """
    return {
        "name": f"Converted from PowerShell: {script_name}",
        "hosts": "windows",
        "gather_facts": True,
        "vars": {
            "ansible_connection": "winrm",
            "ansible_winrm_transport": "ntlm",
        },
        "tasks": [],
    }


# ---------------------------------------------------------------------------
# Per-cmdlet task builders
# ---------------------------------------------------------------------------


def _build_win_feature_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_feature task from cmdlet parameters."""
    name = (
        params.get("name")
        or params.get("featurename")
        or title
        or "FEATURE_NAME"
    )
    remove = title.lower() in ("uninstall-windowsfeature", "remove-windowsfeature")
    return {
        "name": f"{'Remove' if remove else 'Install'} Windows feature: {name}",
        "ansible.windows.win_feature": {
            "name": name,
            "state": "absent" if remove else "present",
            "include_management_tools": True,
        },
    }


def _build_win_service_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_service task."""
    svc_name = params.get("name") or title or "SERVICE_NAME"
    state_map = {
        "start-service": "started",
        "stop-service": "stopped",
        "restart-service": "restarted",
        "new-service": "started",
        "remove-service": "absent",
    }
    state = state_map.get(title.lower(), "started")
    task: dict[str, Any] = {
        "name": f"Manage service: {svc_name}",
        "ansible.windows.win_service": {
            "name": svc_name,
            "state": state,
        },
    }
    if "startuptype" in params:
        start = params["startuptype"].lower()
        start_map = {
            "automatic": "auto",
            "manual": "manual",
            "disabled": "disabled",
            "automaticdelayedstart": "delayed",
        }
        task["ansible.windows.win_service"]["start_mode"] = start_map.get(start, start)
    return task


def _build_win_file_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_file task."""
    path = (
        params.get("path")
        or params.get("literalpath")
        or params.get("destination")
        or "ITEM_PATH"
    )
    item_type = params.get("itemtype", "file").lower()
    if title.lower() == "remove-item":
        state = "absent"
    elif item_type in ("directory", "dir"):
        state = "directory"
    else:
        state = "present"
    return {
        "name": f"Manage file/directory: {path}",
        "ansible.windows.win_file": {
            "path": path,
            "state": state,
        },
    }


def _build_win_copy_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_copy task."""
    src = params.get("path") or params.get("literalpath") or "SOURCE"
    dest = params.get("destination") or params.get("dest") or "DESTINATION"
    return {
        "name": f"Copy file: {src} → {dest}",
        "ansible.windows.win_copy": {
            "src": src,
            "dest": dest,
        },
    }


def _build_win_regedit_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_regedit task."""
    path = params.get("path") or params.get("literalpath") or "HKLM:\\\\SOFTWARE"
    name = params.get("name") or "PROPERTY_NAME"
    value = params.get("value") or ""
    remove = title.lower() in ("remove-itemproperty",)
    task: dict[str, Any] = {
        "name": f"{'Remove' if remove else 'Set'} registry value: {path}\\{name}",
        "ansible.windows.win_regedit": {
            "path": path,
            "name": name,
            "state": "absent" if remove else "present",
        },
    }
    if value and not remove:
        task["ansible.windows.win_regedit"]["data"] = value
    return task


def _build_win_user_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_user task."""
    user = params.get("name") or "USERNAME"
    remove = title.lower() == "remove-localuser"
    task: dict[str, Any] = {
        "name": f"{'Remove' if remove else 'Manage'} local user: {user}",
        "ansible.windows.win_user": {
            "name": user,
            "state": "absent" if remove else "present",
        },
    }
    if "password" in params and not remove:
        task["ansible.windows.win_user"]["password"] = params["password"]
    if "description" in params:
        task["ansible.windows.win_user"]["description"] = params["description"]
    return task


def _build_win_group_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_group task."""
    group = params.get("name") or "GROUPNAME"
    remove = title.lower() == "remove-localgroup"
    return {
        "name": f"{'Remove' if remove else 'Manage'} local group: {group}",
        "ansible.windows.win_group": {
            "name": group,
            "state": "absent" if remove else "present",
        },
    }


def _build_win_firewall_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build a community.windows.win_firewall_rule task."""
    name = params.get("name") or "RULE_NAME"
    direction = params.get("direction", "Inbound").capitalize()
    action = params.get("action", "Allow").lower()
    protocol = params.get("protocol", "TCP").upper()
    local_port = params.get("localport") or params.get("port") or ""
    disabled = title.lower() in ("disable-netfirewallrule",)
    remove = title.lower() == "remove-netfirewallrule"
    task: dict[str, Any] = {
        "name": f"Manage firewall rule: {name}",
        "community.windows.win_firewall_rule": {
            "name": name,
            "direction": direction,
            "action": action,
            "protocol": protocol,
            "state": "absent" if remove else "present",
            "enabled": not disabled,
        },
    }
    if local_port:
        task["community.windows.win_firewall_rule"]["localport"] = local_port
    return task


def _build_win_scheduled_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build a community.windows.win_scheduled_task task."""
    name = params.get("taskname") or params.get("name") or "TASK_NAME"
    path = params.get("taskpath", "\\")
    remove = title.lower() == "unregister-scheduledtask"
    disabled = title.lower() == "disable-scheduledtask"
    task: dict[str, Any] = {
        "name": f"Manage scheduled task: {name}",
        "community.windows.win_scheduled_task": {
            "name": name,
            "path": path,
            "state": "absent" if remove else "present",
            "enabled": not disabled,
        },
    }
    return task


def _build_win_package_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_package task."""
    name = params.get("name") or params.get("path") or "PACKAGE"
    remove = title.lower() in ("uninstall-package",)
    return {
        "name": f"{'Remove' if remove else 'Install'} package: {name}",
        "ansible.windows.win_package": {
            "name": name,
            "state": "absent" if remove else "present",
        },
    }


def _build_win_updates_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_updates task."""
    return {
        "name": "Apply Windows updates",
        "ansible.windows.win_updates": {
            "category_names": ["SecurityUpdates", "CriticalUpdates"],
            "reboot": False,
        },
    }


def _build_win_reboot_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_reboot task."""
    return {
        "name": "Reboot Windows host",
        "ansible.windows.win_reboot": {
            "reboot_timeout": 600,
        },
    }


def _build_win_get_url_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_get_url task."""
    url = params.get("uri") or params.get("url") or "URL"
    dest = params.get("outfile") or params.get("dest") or "DEST_PATH"
    return {
        "name": f"Download file: {url}",
        "ansible.windows.win_get_url": {
            "url": url,
            "dest": dest,
        },
    }


def _build_win_shell_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_shell task (fallback)."""
    cmd = params.get("filepath") or params.get("command") or title
    return {
        "name": f"Run shell command: {title}",
        "ansible.windows.win_shell": cmd,
    }


def _build_win_dsc_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.windows.win_dsc task."""
    resource = params.get("name") or params.get("resourcename") or "DSC_RESOURCE"
    module = params.get("modulename", "PSDesiredStateConfiguration")
    return {
        "name": f"Apply DSC resource: {resource}",
        "ansible.windows.win_dsc": {
            "resource_name": resource,
            "module_version": "latest",
            "module_name": module,
        },
        "vars": {"ansible_become": False},
    }


def _build_debug_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.builtin.debug task for Write-* cmdlets."""
    msg = params.get("object") or params.get("message") or ""
    return {
        "name": f"Debug message from {title}",
        "ansible.builtin.debug": {
            "msg": msg or f"(output from {title})",
        },
    }


def _build_fail_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build an ansible.builtin.fail task for Write-Error / throw."""
    msg = params.get("message") or params.get("object") or "Script error"
    return {
        "name": f"Fail from {title}",
        "ansible.builtin.fail": {
            "msg": msg,
        },
    }


def _build_unsupported_task(title: str, params: dict[str, str]) -> dict[str, Any]:
    """Build a debug task with a WARNING marker for unsupported cmdlets."""
    return {
        "name": f"WARNING: {title} requires manual conversion",
        "ansible.windows.win_shell": (
            f"# TODO: Convert {title} to equivalent Ansible task"
        ),
    }


# Populate the cmdlet builder registry
_CMDLET_BUILDERS = {
    "install-windowsfeature": _build_win_feature_task,
    "uninstall-windowsfeature": _build_win_feature_task,
    "add-windowsfeature": _build_win_feature_task,
    "remove-windowsfeature": _build_win_feature_task,
    "start-service": _build_win_service_task,
    "stop-service": _build_win_service_task,
    "restart-service": _build_win_service_task,
    "set-service": _build_win_service_task,
    "new-service": _build_win_service_task,
    "remove-service": _build_win_service_task,
    "new-item": _build_win_file_task,
    "remove-item": _build_win_file_task,
    "rename-item": _build_win_file_task,
    "copy-item": _build_win_copy_task,
    "move-item": _build_win_copy_task,
    "set-content": _build_win_copy_task,
    "get-content": _build_win_copy_task,
    "new-itemproperty": _build_win_regedit_task,
    "set-itemproperty": _build_win_regedit_task,
    "remove-itemproperty": _build_win_regedit_task,
    "new-localuser": _build_win_user_task,
    "set-localuser": _build_win_user_task,
    "remove-localuser": _build_win_user_task,
    "new-localgroup": _build_win_group_task,
    "remove-localgroup": _build_win_group_task,
    "new-netfirewallrule": _build_win_firewall_task,
    "set-netfirewallrule": _build_win_firewall_task,
    "remove-netfirewallrule": _build_win_firewall_task,
    "enable-netfirewallrule": _build_win_firewall_task,
    "disable-netfirewallrule": _build_win_firewall_task,
    "register-scheduledtask": _build_win_scheduled_task,
    "unregister-scheduledtask": _build_win_scheduled_task,
    "enable-scheduledtask": _build_win_scheduled_task,
    "disable-scheduledtask": _build_win_scheduled_task,
    "install-package": _build_win_package_task,
    "uninstall-package": _build_win_package_task,
    "install-windowsupdate": _build_win_updates_task,
    "get-windowsupdate": _build_win_updates_task,
    "restart-computer": _build_win_reboot_task,
    "invoke-webrequest": _build_win_get_url_task,
    "start-bitstransfer": _build_win_get_url_task,
    "invoke-expression": _build_win_shell_task,
    "invoke-command": _build_win_shell_task,
    "start-process": _build_win_shell_task,
    "invoke-dscresource": _build_win_dsc_task,
    "write-host": _build_debug_task,
    "write-output": _build_debug_task,
    "write-verbose": _build_debug_task,
    "write-warning": _build_debug_task,
    "write-error": _build_fail_task,
    "throw": _build_fail_task,
}


# ---------------------------------------------------------------------------
# Parameter parser
# ---------------------------------------------------------------------------


def _parse_cmdlet_parameters(params_raw: str) -> dict[str, str]:
    """
    Parse a raw PowerShell cmdlet parameter string into a dictionary.

    Handles named parameters (``-Name Value``, ``-Name "Value"``,
    ``-Name 'Value'``).

    Args:
        params_raw: Raw parameter string extracted from the script.

    Returns:
        Dictionary mapping parameter names (lower-case) to values.

    """
    params: dict[str, str] = {}
    # Match -ParamName optionally followed by a value
    pattern = re.compile(
        r"-([A-Za-z][A-Za-z0-9]*)(?:\s+"
        r"(?:['\"]([^'\"]*)['\"]|([^\s\-][^\s]*)))?",
        re.IGNORECASE,
    )
    for match in pattern.finditer(params_raw):
        key = match.group(1).lower()
        value = match.group(2) or match.group(3) or ""
        params[key] = value
    return params


# ---------------------------------------------------------------------------
# Playbook generator
# ---------------------------------------------------------------------------


def _convert_cmdlet_to_task(
    cmdlet: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert a single parsed cmdlet dict to an Ansible task dict.

    Args:
        cmdlet: Cmdlet dictionary from the parser.

    Returns:
        Ansible task dictionary.

    """
    name = cmdlet.get("name", "")
    params_raw = cmdlet.get("parameters_raw", "")
    params = _parse_cmdlet_parameters(params_raw)

    builder = _CMDLET_BUILDERS.get(name.lower(), _build_unsupported_task)
    result: dict[str, Any] = builder(name, params)
    return result


def _generate_powershell_playbook(
    parsed: dict[str, Any],
    source_path: str,
) -> str:
    """
    Generate an Ansible playbook YAML from parsed PowerShell data.

    Args:
        parsed: Parsed script data (from ``_parse_script_content``).
        source_path: Source script path for the play name.

    Returns:
        YAML string of the complete Ansible playbook.

    """
    script_name = Path(source_path).name
    play = _build_windows_play_header(script_name)

    for cmdlet in parsed.get("cmdlets", []):
        task = _convert_cmdlet_to_task(cmdlet)
        play["tasks"].append(task)

    if not play["tasks"]:
        play["tasks"].append(
            {
                "name": "No convertible cmdlets found",
                "ansible.builtin.debug": {
                    "msg": (
                        "The source script contained no cmdlets that could be "
                        "automatically converted. Review manually or use "
                        "Convert with AI."
                    ),
                },
            }
        )

    playbook = [play]
    return yaml.dump(
        playbook, default_flow_style=False, sort_keys=False, allow_unicode=True
    )


# ---------------------------------------------------------------------------
# Public conversion entry points
# ---------------------------------------------------------------------------


def convert_powershell_script_to_ansible(script_path: str) -> str:
    """
    Convert a PowerShell script to an Ansible playbook.

    Parses the script and produces a Windows-targeted Ansible playbook.
    Unsupported cmdlets are emitted as ``ansible.windows.win_shell`` stubs
    with a WARNING comment.

    Args:
        script_path: Path to the PowerShell script (``.ps1``/``.psm1``).

    Returns:
        Ansible playbook YAML string, or an error message prefixed with
        ``"Error:"`` if the script cannot be read.

    """
    try:
        file_path = _normalize_path(script_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(file_path, workspace_root)
        raw_content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        if len(raw_content) > MAX_CONTENT_LENGTH:
            return (
                f"Error: Script too large to convert safely "
                f"({len(raw_content)} bytes)"
            )

        parsed = _parse_script_content(raw_content, script_path)
        return _generate_powershell_playbook(parsed, script_path)

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=script_path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=script_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=script_path)
    except Exception as e:
        return f"An error occurred: {e}"


def _convert_scripts_to_plays(
    scripts: list[Any],
    workspace_root: Any,
) -> list[dict[str, Any]]:
    """
    Convert a list of script Paths into Ansible play dictionaries.

    Args:
        scripts: List of ``pathlib.Path`` script files.
        workspace_root: Workspace root for path containment.

    Returns:
        List of Ansible play dictionaries (only non-empty plays included).

    """
    all_plays: list[dict[str, Any]] = []
    for script_path in scripts:
        try:
            content = safe_read_text(
                script_path, workspace_root, encoding="utf-8"
            )
            rel_path = str(script_path.relative_to(workspace_root))
            parsed = _parse_script_content(content, rel_path)
            play = _build_windows_play_header(script_path.name)
            for cmdlet in parsed.get("cmdlets", []):
                play["tasks"].append(_convert_cmdlet_to_task(cmdlet))
            if play["tasks"]:
                all_plays.append(play)
        except (OSError, ValueError):
            continue
    return all_plays


def convert_powershell_directory_to_ansible(directory_path: str) -> str:
    """
    Convert all PowerShell scripts in a directory to a combined Ansible playbook.

    Combines plays from every ``.ps1``/``.psm1`` file found in the directory
    into a single multi-play playbook.

    Args:
        directory_path: Path to the directory containing PowerShell scripts.

    Returns:
        Combined Ansible playbook YAML string, or an error message.

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
            list(safe_dir.rglob("*.ps1")) + list(safe_dir.rglob("*.psm1"))
        )
        if not scripts:
            return (
                f"Warning: No PowerShell scripts (.ps1/.psm1) found in "
                f"{directory_path}"
            )

        all_plays = _convert_scripts_to_plays(scripts, workspace_root)
        if not all_plays:
            return (
                "Warning: No convertible cmdlets found across all scripts in "
                + directory_path
            )

        return yaml.dump(
            all_plays, default_flow_style=False, sort_keys=False, allow_unicode=True
        )

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=directory_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=directory_path)
    except Exception as e:
        return f"An error occurred: {e}"


# ---------------------------------------------------------------------------
# AI-Assisted Conversion
# ---------------------------------------------------------------------------


def convert_powershell_script_to_ansible_with_ai(
    script_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """
    Convert a PowerShell script to an Ansible playbook using AI.

    When unsupported constructs are detected, delegates to a LLM for
    best-effort conversion.  Falls back to the deterministic converter
    if no unsupported constructs exist.

    Args:
        script_path: Path to the PowerShell script (``.ps1``/``.psm1``).
        ai_provider: AI provider (``'anthropic'``, ``'openai'``,
            ``'watson'``, ``'lightspeed'``).
        api_key: API key for the chosen provider.
        model: Model identifier.
        temperature: Sampling temperature; defaults to ``0.3``.
        max_tokens: Maximum tokens in the LLM response.
        project_id: Project ID for IBM Watsonx.
        base_url: Custom provider endpoint URL.

    Returns:
        Ansible playbook YAML string, or an error message string.

    """
    try:
        file_path = _normalize_path(script_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(file_path, workspace_root)
        raw_content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        if len(raw_content) > MAX_CONTENT_LENGTH:
            return (
                f"Error: Script too large to convert safely "
                f"({len(raw_content)} bytes)"
            )

        parsed = _parse_script_content(raw_content, script_path)
        unsupported = parsed.get("unsupported", [])

        if not unsupported:
            return _generate_powershell_playbook(parsed, script_path)

        parsed_analysis = parse_powershell_script(script_path)
        return _convert_ps_with_ai(
            raw_content,
            parsed_analysis,
            unsupported,
            safe_path.name,
            ai_provider,
            api_key,
            model,
            temperature,
            max_tokens,
            project_id,
            base_url,
        )

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=script_path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=script_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=script_path)
    except Exception as e:
        return f"An error occurred: {e}"


def convert_powershell_directory_to_ansible_with_ai(
    directory_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """
    Convert a directory of PowerShell scripts to Ansible using AI.

    Args:
        directory_path: Path to the directory containing PowerShell scripts.
        ai_provider: AI provider identifier.
        api_key: API key for the chosen provider.
        model: Model identifier.
        temperature: Sampling temperature; defaults to ``0.3``.
        max_tokens: Maximum tokens in the LLM response.
        project_id: Project ID for IBM Watsonx.
        base_url: Custom provider endpoint URL.

    Returns:
        Combined Ansible playbook YAML string, or an error message string.

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
            list(safe_dir.rglob("*.ps1")) + list(safe_dir.rglob("*.psm1"))
        )
        if not scripts:
            return (
                f"Warning: No PowerShell scripts (.ps1/.psm1) found in "
                f"{directory_path}"
            )

        collected = _collect_directory_scripts(scripts, workspace_root)
        all_unsupported = collected["unsupported"]
        combined_raw = "\n\n".join(collected["content_parts"])

        if not all_unsupported:
            combined_parsed: dict[str, Any] = {
                "cmdlets": collected["cmdlets"],
                "functions": [],
                "variables": [],
                "modules": [],
                "unsupported": [],
            }
            return _generate_powershell_playbook(combined_parsed, directory_path)

        analysis = _format_directory_analysis(collected, directory_path)
        return _convert_ps_with_ai(
            combined_raw,
            analysis,
            all_unsupported,
            directory_path,
            ai_provider,
            api_key,
            model,
            temperature,
            max_tokens,
            project_id,
            base_url,
        )

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=directory_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=directory_path)
    except Exception as e:
        return f"An error occurred: {e}"


def _collect_directory_scripts(
    scripts: list[Any],
    workspace_root: Any,
) -> dict[str, Any]:
    """
    Read and parse all scripts, aggregating cmdlets and unsupported constructs.

    Args:
        scripts: Sorted list of ``pathlib.Path`` script files.
        workspace_root: Workspace root for safe-path containment.

    Returns:
        Dictionary with keys ``'cmdlets'``, ``'unsupported'``,
        ``'content_parts'``.

    """
    all_cmdlets: list[dict[str, Any]] = []
    all_unsupported: list[dict[str, Any]] = []
    content_parts: list[str] = []

    for script_path in scripts:
        try:
            content = safe_read_text(
                script_path, workspace_root, encoding="utf-8"
            )
            rel_path = str(script_path.relative_to(workspace_root))
            parsed = _parse_script_content(content, rel_path)
            all_cmdlets.extend(parsed.get("cmdlets", []))
            all_unsupported.extend(parsed.get("unsupported", []))
            content_parts.append(f"# === {rel_path} ===\n{content}")
        except (OSError, ValueError):
            continue

    return {
        "cmdlets": all_cmdlets,
        "unsupported": all_unsupported,
        "content_parts": content_parts,
    }


def _format_directory_analysis(
    collected: dict[str, Any], directory_path: str
) -> str:
    """
    Build a human-readable analysis summary for a script directory.

    Args:
        collected: Output of :func:`_collect_directory_scripts`.
        directory_path: Path to the directory (for the heading).

    Returns:
        Formatted analysis string.

    """
    lines = [
        f"PowerShell Directory Analysis: {directory_path}",
        "",
        f"Total cmdlets:       {len(collected['cmdlets'])}",
        f"Unsupported constructs: {len(collected['unsupported'])}",
    ]
    if collected["unsupported"]:
        lines.append("")
        lines.append("Unsupported constructs requiring AI conversion:")
        for item in collected["unsupported"]:
            loc = f"{item['source_file']}:{item['line']}"
            lines.append(f"  [{item['construct']}] at {loc} — {item['text']!r}")
    return "\n".join(lines)


def _convert_ps_with_ai(
    raw_content: str,
    parsed_analysis: str,
    unsupported: list[dict[str, Any]],
    source_name: str,
    ai_provider: str,
    api_key: str,
    model: str,
    temperature: float,
    max_tokens: int,
    project_id: str,
    base_url: str,
) -> str:
    """
    Core AI-assisted conversion routine for PowerShell scripts.

    Args:
        raw_content: Full PowerShell script text.
        parsed_analysis: Human-readable analysis string.
        unsupported: List of unsupported construct dicts.
        source_name: Script or directory name used in error messages.
        ai_provider: AI provider identifier.
        api_key: Provider API key.
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.
        project_id: Watsonx project ID.
        base_url: Custom provider URL.

    Returns:
        Cleaned Ansible playbook YAML string, or an error message.

    """
    from souschef.converters.playbook import (
        _call_ai_api,
        _initialize_ai_client,
    )

    client = _initialize_ai_client(ai_provider, api_key, project_id, base_url)
    if isinstance(client, str):
        return client

    prompt = _create_ps_ai_prompt(
        raw_content, parsed_analysis, unsupported, source_name
    )
    ai_response = _call_ai_api(
        client, ai_provider, prompt, model, temperature, max_tokens
    )
    return _clean_ps_ai_response(ai_response)


def _create_ps_ai_prompt(
    raw_content: str,
    parsed_analysis: str,
    unsupported: list[dict[str, Any]],
    script_name: str,
) -> str:
    """
    Build the LLM prompt for PowerShell → Ansible conversion.

    Args:
        raw_content: Raw PowerShell script text (truncated if very long).
        parsed_analysis: Pre-formatted analysis string from the parser.
        unsupported: List of unsupported construct dictionaries.
        script_name: Script file or directory name.

    Returns:
        Prompt string ready to send to the LLM.

    """
    if len(raw_content) > _AI_MAX_CONTENT_CHARS:
        raw_content = raw_content[:_AI_MAX_CONTENT_CHARS] + "\n# [truncated]"

    unsupported_lines = _format_unsupported_for_prompt(unsupported)
    guidance_lines = _build_construct_guidance(unsupported)

    parts = [
        "You are an expert PowerShell-to-Ansible migration engineer targeting",
        "Windows hosts managed via Ansible Automation Platform (AAP).",
        "Convert the PowerShell script below into a complete, production-ready",
        "Ansible playbook for Windows.",
        "",
        "POWERSHELL SCRIPT CONTENT:",
        raw_content,
        "",
        "PARSED POWERSHELL ANALYSIS (for context):",
        parsed_analysis,
        "",
        "UNSUPPORTED CONSTRUCTS REQUIRING AI CONVERSION:",
        unsupported_lines,
        "",
        "CONVERSION GUIDANCE:",
        guidance_lines,
        "",
        "GENERAL REQUIREMENTS:",
        "- All tasks must be idempotent.",
        "- Use fully-qualified Ansible module names (ansible.windows.*, "
        "community.windows.*, ansible.builtin.*).",
        "- Set `hosts: windows` and `gather_facts: true`.",
        "- Include WinRM connection vars: ansible_connection: winrm, "
        "ansible_winrm_transport: ntlm.",
        "- Name the play: 'Converted from PowerShell: " + script_name + "'",
        "- Use ansible.windows.win_shell for any commands not mappable to a "
        "dedicated module.",
        "",
        "OUTPUT FORMAT:",
        "Return ONLY valid YAML for a single Ansible playbook. "
        "Do NOT include markdown code fences, explanations, "
        "or any text outside the YAML.",
    ]
    return "\n".join(parts)


def _format_unsupported_for_prompt(unsupported: list[dict[str, Any]]) -> str:
    """
    Format the unsupported construct list for inclusion in the AI prompt.

    Args:
        unsupported: List of unsupported construct dicts.

    Returns:
        Formatted multi-line string.

    """
    if not unsupported:
        return "(none)"
    return "\n".join(
        f"  - [{item['construct']}] at {item['source_file']}:{item['line']}: "
        f"{item['text']!r}"
        for item in unsupported
    )


def _build_construct_guidance(unsupported: list[dict[str, Any]]) -> str:
    """
    Build targeted conversion guidance based on detected construct types.

    Args:
        unsupported: List of unsupported construct dicts.

    Returns:
        Guidance string with specific instructions per construct type.

    """
    seen: set[str] = {item["construct"] for item in unsupported}

    guidance_map: dict[str, str] = {
        ".NET static method call": (
            ".NET static method: Replace with the equivalent ansible.windows.win_shell "
            "command or a dedicated Ansible module where available."
        ),
        "COM/CLR object instantiation": (
            "New-Object: Use ansible.windows.win_shell or ansible.windows.win_dsc "
            "with the appropriate DSC resource."
        ),
        "Inline .NET type compilation": (
            "Add-Type: Replace with a pre-compiled assembly deployed via "
            "ansible.windows.win_copy, or rewrite as a PowerShell module."
        ),
        "WMI query": (
            "Get-WmiObject: Replace with the equivalent ansible.windows module "
            "(e.g. win_service, win_disk_facts) or use ansible.windows.win_shell "
            "with a filtered CIM query."
        ),
        "CIM/WMI query": (
            "Get-CimInstance: Same as WMI — use dedicated Ansible facts modules "
            "where possible; fall back to ansible.windows.win_shell."
        ),
        "WMI method invocation": (
            "Invoke-WmiMethod: Convert to the equivalent service/process Ansible "
            "module or ansible.windows.win_shell."
        ),
        "PS remoting session": (
            "Enter-PSSession/New-PSSession: Not needed with Ansible — the WinRM "
            "connection already provides remote execution. Remove and run tasks "
            "directly."
        ),
        "Cross-scope variable ($using:)": (
            "$using: variable: Convert to an Ansible variable (vars:) and reference "
            "with {{ var_name }}."
        ),
        "Event subscription": (
            "Register-ObjectEvent: Consider a scheduled task or Windows Event Log "
            "trigger via community.windows.win_scheduled_task."
        ),
        "DSC Configuration block": (
            "DSC Configuration: Convert each DSC resource invocation to an "
            "ansible.windows.win_dsc task with matching properties."
        ),
        "Windows PowerShell compatibility mode": (
            "-UseWindowsPowerShell: Ensure the Ansible EE uses a PowerShell "
            "version that supports the module natively."
        ),
    }

    lines = [
        f"- {hint}"
        for construct, hint in guidance_map.items()
        if construct in seen
    ]
    return "\n".join(lines) if lines else (
        "- Follow best practices for idempotent Windows automation."
    )


def _clean_ps_ai_response(ai_response: str) -> str:
    """
    Strip markdown fences from the AI response and validate it is YAML.

    Args:
        ai_response: Raw string returned by the LLM.

    Returns:
        Cleaned YAML string, or an error message if the response is invalid.

    """
    if not ai_response or not ai_response.strip():
        return f"{_ERROR_PREFIX} AI returned an empty response"

    import re as _re
    cleaned = _re.sub(r"```\w*\n?", "", ai_response).strip()

    if not cleaned.startswith("---") and not cleaned.startswith("- "):
        return (
            f"{_ERROR_PREFIX} AI response does not appear to be a valid "
            "Ansible playbook (expected YAML list starting with '---' or '- ')"
        )
    return cleaned


# ---------------------------------------------------------------------------
# Enterprise / AAP artefact generators
# ---------------------------------------------------------------------------

_DEFAULT_EE_BASE_IMAGE = (
    "registry.redhat.io/ansible-automation-platform-25/ee-supported-rhel9:latest"
)


def generate_windows_ee_definition(
    ee_name: str = "windows-ee",
    base_image: str = _DEFAULT_EE_BASE_IMAGE,
    python_packages: list[str] | None = None,
    galaxy_collections: list[str] | None = None,
) -> str:
    """
    Generate an Ansible Builder ``execution-environment.yml`` for Windows targets.

    The resulting EE definition includes the ``ansible.windows`` and
    ``community.windows`` collections and the ``pywinrm`` Python package
    required for WinRM connectivity.

    Args:
        ee_name: Human-readable name for the execution environment.
        base_image: Base image reference (defaults to AAP 2.5 supported EE).
        python_packages: Additional Python packages to include beyond ``pywinrm``.
        galaxy_collections: Additional Galaxy collections beyond the Windows ones.

    Returns:
        YAML string for the ``execution-environment.yml`` file.

    """
    default_py = ["pywinrm", "pywinrm[kerberos]", "requests-credssp"]
    default_collections = [
        "ansible.windows:>=2.0.0",
        "community.windows:>=2.0.0",
        "ansible.posix:>=1.5.0",
        "chocolatey.chocolatey:>=1.4.0",
    ]

    py_packages = default_py + (python_packages or [])
    collections = default_collections + (galaxy_collections or [])

    def _col_entry(col: str) -> dict[str, str]:
        if ":" in col:
            name, ver = col.split(":", 1)
            return {"name": name, "version": ver.lstrip(">=")}
        return {"name": col, "version": ""}

    ee: dict[str, Any] = {
        "version": 3,
        "build_arg_defaults": {
            "EE_BASE_IMAGE": base_image,
        },
        "dependencies": {
            "python": py_packages,
            "galaxy": {
                "collections": [_col_entry(c) for c in collections]
            },
        },
        "images": {
            "base_image": {
                "name": base_image,
            }
        },
    }

    return (
        f"# Execution Environment definition for Windows automation\n"
        f"# Name: {ee_name}\n"
        f"# Generated by SousChef PowerShell Migration\n\n"
        + yaml.dump(ee, default_flow_style=False, sort_keys=False, allow_unicode=True)
    )


def generate_aap_windows_credential_vars(
    hosts: list[str] | None = None,
    transport: str = "ntlm",
    port: int = 5985,
    validate_certs: bool = True,
) -> str:
    """
    Generate a Windows credential variable template for AAP/AWX inventories.

    Produces a ``group_vars/windows.yml`` stub with WinRM connection
    variables appropriate for an enterprise Windows inventory.

    Args:
        hosts: Optional list of host names/patterns to include.
        transport: WinRM authentication transport
            (``'ntlm'``, ``'kerberos'``, ``'certificate'``, ``'basic'``).
        port: WinRM port (5985 for HTTP, 5986 for HTTPS).
        validate_certs: Whether to validate SSL certificates.

    Returns:
        YAML string for ``group_vars/windows.yml``.

    """
    protocol = "https" if port == 5986 else "http"

    vars_block: dict[str, Any] = {
        "ansible_connection": "winrm",
        "ansible_winrm_transport": transport,
        "ansible_winrm_port": port,
        "ansible_winrm_scheme": protocol,
        "ansible_winrm_server_cert_validation": (
            "validate" if validate_certs else "ignore"
        ),
        "ansible_winrm_read_timeout_sec": 30,
        "ansible_winrm_operation_timeout_sec": 20,
        "ansible_become": False,
    }

    if transport == "kerberos":
        vars_block["ansible_winrm_kerberos_delegation"] = True

    lines = [
        "# Windows group_vars — generated by SousChef PowerShell Migration",
        "# Store ansible_user / ansible_password in AAP/AWX credential type:",
        "# Machine > Windows (uses winrm transport).",
        "#",
        "# AAP Credential Type: Machine",
        "# AAP Credential settings:",
        "#   Connection: WinRM",
        f"#   Transport: {transport}",
        f"#   Port: {port}",
        "",
    ]

    return (
        "\n".join(lines)
        + yaml.dump(
            vars_block, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
    )


def generate_windows_inventory_template(
    hosts: list[str] | None = None,
    group_name: str = "windows",
    transport: str = "ntlm",
) -> str:
    """
    Generate a Windows inventory YAML template for AAP/AWX.

    Args:
        hosts: List of Windows host names or IPs.
        group_name: Inventory group name (default ``'windows'``).
        transport: WinRM transport type.

    Returns:
        YAML inventory template string.

    """
    host_list = hosts or ["win-server-01", "win-server-02"]
    inventory: dict[str, Any] = {
        group_name: {
            "hosts": {h: {} for h in host_list},
            "vars": {
                "ansible_connection": "winrm",
                "ansible_winrm_transport": transport,
                "ansible_winrm_server_cert_validation": "validate",
            },
        }
    }
    return (
        "# Windows inventory template — generated by SousChef\n"
        "# Populate ansible_user / ansible_password via AAP Machine credentials.\n\n"
        + yaml.dump(
            inventory, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
    )


def get_powershell_ansible_module_map() -> dict[str, str]:
    """
    Return the mapping of PowerShell cmdlets to Ansible modules.

    Returns:
        Dictionary mapping lower-cased cmdlet names to Ansible module names.

    """
    return dict(CMDLET_MODULE_MAP)


def get_supported_powershell_cmdlets() -> list[str]:
    """
    Return the sorted list of PowerShell cmdlets with direct Ansible equivalents.

    Returns:
        Sorted list of supported PowerShell cmdlet names.

    """
    return sorted(CMDLET_MODULE_MAP.keys())
