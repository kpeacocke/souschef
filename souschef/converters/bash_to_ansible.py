"""
Bash script to Ansible playbook converter.

Converts a parsed Bash script intermediate representation (IR) into an
Ansible playbook YAML string.  High-confidence patterns are converted to
dedicated Ansible modules (``ansible.builtin.package``,
``ansible.builtin.service``, ``ansible.builtin.copy``,
``ansible.builtin.get_url``).  Low-confidence and unrecognised lines
fall back to ``ansible.builtin.shell`` with idempotency hints
(``creates``, ``changed_when``, ``failed_when``).
"""

from __future__ import annotations

import json
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
from souschef.parsers.bash import _parse_bash_content

# Threshold below which a match is considered low-confidence and should
# fall back to ansible.builtin.shell rather than a structured module.
_CONFIDENCE_THRESHOLD = 0.8

# YAML indentation used when building task blocks
_INDENT = "  "


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert_bash_to_ansible(path: str) -> str:
    """
    Convert a Bash script file to an Ansible playbook.

    Reads the script at *path*, parses it into an IR, converts each
    detected pattern to an appropriate Ansible task, and returns the
    resulting playbook as a JSON string (for consistency with other
    MCP tool responses).

    Args:
        path: Path to the Bash script.

    Returns:
        JSON string with ``playbook_yaml``, ``tasks``, ``warnings``,
        and ``idempotency_report`` keys.  Returns a JSON error object
        on failure.

    """
    from pathlib import Path

    try:
        workspace = _get_workspace_root()
        normalised = _normalize_path(path)
        safe_path = _ensure_within_base_path(Path(normalised), workspace)
        content = safe_read_text(safe_path, workspace)
    except FileNotFoundError:
        return json.dumps(
            {"error": f"{ERROR_FILE_NOT_FOUND}: {path}", "status": "error"}
        )
    except IsADirectoryError:
        return json.dumps(
            {"error": f"{ERROR_IS_DIRECTORY}: {path}", "status": "error"}
        )
    except PermissionError:
        return json.dumps(
            {"error": f"{ERROR_PERMISSION_DENIED}: {path}", "status": "error"}
        )
    except (ValueError, OSError) as exc:
        return json.dumps(
            {"error": f"Error reading file: {exc}", "status": "error"}
        )

    return convert_bash_content_to_ansible(content, script_path=path)


def convert_bash_content_to_ansible(
    content: str,
    script_path: str = "script.sh",
) -> str:
    """
    Convert raw Bash script content to an Ansible playbook JSON response.

    Args:
        content: Raw Bash script text.
        script_path: Optional path label used in playbook metadata.

    Returns:
        JSON string with keys ``playbook_yaml``, ``tasks``, ``warnings``,
        ``idempotency_report``, and ``status``.

    """
    ir = _parse_bash_content(content)
    tasks = _build_tasks(ir)
    warnings = _collect_warnings(ir)
    idempotency_report = _build_idempotency_report(ir)
    playbook_yaml = _render_playbook(tasks, script_path)

    return json.dumps(
        {
            "status": "success",
            "script_path": script_path,
            "playbook_yaml": playbook_yaml,
            "tasks": tasks,
            "warnings": warnings,
            "idempotency_report": idempotency_report,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Task builders
# ---------------------------------------------------------------------------


def _build_tasks(ir: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build a list of Ansible task dictionaries from *ir*.

    Args:
        ir: Intermediate representation from the Bash parser.

    Returns:
        Ordered list of Ansible task dictionaries.

    """
    tasks: list[dict[str, Any]] = []
    tasks.extend(_package_tasks(ir.get("packages", [])))
    tasks.extend(_service_tasks(ir.get("services", [])))
    tasks.extend(_file_write_tasks(ir.get("file_writes", [])))
    tasks.extend(_download_tasks(ir.get("downloads", [])))
    tasks.extend(_shell_fallback_tasks(ir.get("shell_fallbacks", [])))
    return tasks


def _package_tasks(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert package-install IR entries to Ansible task dicts.

    Args:
        packages: List of package IR entries.

    Returns:
        List of Ansible task dictionaries.

    """
    tasks = []
    for entry in packages:
        if entry["confidence"] >= _CONFIDENCE_THRESHOLD:
            pkg_list = entry["packages"] or [entry["raw"].split()[-1]]
            task: dict[str, Any] = {
                "name": f"Install packages via {entry['manager']}",
                entry["ansible_module"]: {
                    "name": pkg_list,
                    "state": "present",
                },
                "_metadata": {
                    "source_line": entry["line"],
                    "confidence": entry["confidence"],
                    "idempotent": True,
                },
            }
        else:
            task = _shell_task(
                entry["raw"],
                entry["line"],
                entry["confidence"],
                idempotency_hint=f"state=present equivalent for {entry['manager']}",
            )
        tasks.append(task)
    return tasks


def _service_tasks(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert service-control IR entries to Ansible task dicts.

    Args:
        services: List of service IR entries.

    Returns:
        List of Ansible task dictionaries.

    """
    _action_map = {
        "start": "started",
        "stop": "stopped",
        "restart": "restarted",
        "reload": "reloaded",
        "enable": "started",  # enable also implies started in most cases
        "disable": "stopped",
    }
    tasks = []
    for entry in services:
        if entry["confidence"] >= _CONFIDENCE_THRESHOLD:
            state = _action_map.get(entry["action"], entry["action"])
            enabled: bool | None = None
            if entry["action"] in {"enable", "disable"}:
                enabled = entry["action"] == "enable"
            module_args: dict[str, Any] = {
                "name": entry["name"],
                "state": state,
            }
            if enabled is not None:
                module_args["enabled"] = enabled
            task: dict[str, Any] = {
                "name": f"{entry['action'].capitalize()} service {entry['name']}",
                "ansible.builtin.service": module_args,
                "_metadata": {
                    "source_line": entry["line"],
                    "confidence": entry["confidence"],
                    "idempotent": True,
                },
            }
        else:
            task = _shell_task(entry["raw"], entry["line"], entry["confidence"])
        tasks.append(task)
    return tasks


def _file_write_tasks(file_writes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert file-write IR entries to Ansible task dicts.

    File-write operations (heredoc, echo redirect) are generally mapped
    to ``ansible.builtin.copy`` when confidence is sufficient, otherwise
    they fall back to ``ansible.builtin.shell``.

    Args:
        file_writes: List of file-write IR entries.

    Returns:
        List of Ansible task dictionaries.

    """
    tasks = []
    for entry in file_writes:
        if entry["confidence"] >= _CONFIDENCE_THRESHOLD:
            task: dict[str, Any] = {
                "name": f"Write file {entry['destination']}",
                "ansible.builtin.copy": {
                    "dest": entry["destination"],
                    "content": "# TODO: replace with actual file content",
                    "mode": "0644",
                },
                "_metadata": {
                    "source_line": entry["line"],
                    "confidence": entry["confidence"],
                    "idempotent": True,
                },
            }
        else:
            task = _shell_task(
                entry["raw"],
                entry["line"],
                entry["confidence"],
                idempotency_hint=(
                    f"Use ansible.builtin.copy with dest={entry['destination']}"
                ),
                creates=entry["destination"],
            )
        tasks.append(task)
    return tasks


def _download_tasks(downloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert download IR entries to Ansible task dicts.

    Downloads are mapped to ``ansible.builtin.get_url`` when a URL is
    present; otherwise they fall back to ``ansible.builtin.shell``.

    Args:
        downloads: List of download IR entries.

    Returns:
        List of Ansible task dictionaries.

    """
    tasks = []
    for entry in downloads:
        if entry["url"]:
            # Derive destination filename from URL
            dest_name = entry["url"].rstrip("/").split("/")[-1] or "downloaded_file"
            task: dict[str, Any] = {
                "name": f"Download {dest_name}",
                "ansible.builtin.get_url": {
                    "url": entry["url"],
                    "dest": f"/tmp/{dest_name}",  # nosec B108 – temporary placeholder
                    "mode": "0644",
                },
                "_metadata": {
                    "source_line": entry["line"],
                    "confidence": entry["confidence"],
                    "idempotent": False,
                    "idempotency_hint": (
                        "Add 'checksum' parameter to get_url for verification"
                    ),
                },
            }
        else:
            task = _shell_task(
                entry["raw"],
                entry["line"],
                entry["confidence"],
                idempotency_hint="Use ansible.builtin.get_url with checksum parameter",
            )
        tasks.append(task)
    return tasks


def _shell_fallback_tasks(fallbacks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert shell-fallback IR entries to shell task dicts.

    Args:
        fallbacks: List of shell-fallback IR entries.

    Returns:
        List of Ansible task dictionaries.

    """
    return [
        _shell_task(fb["raw"], fb["line"], 0.5, warning=fb["warning"])
        for fb in fallbacks
    ]


def _shell_task(
    raw: str,
    line: int,
    confidence: float,
    *,
    idempotency_hint: str = "",
    creates: str = "",
    warning: str = "",
) -> dict[str, Any]:
    """
    Build an ``ansible.builtin.shell`` task dictionary.

    Args:
        raw: Raw shell command string.
        line: Source line number.
        confidence: Confidence score (0.0–1.0).
        idempotency_hint: Optional human-readable idempotency suggestion.
        creates: Optional ``creates`` parameter value for idempotency.
        warning: Optional warning message to embed in task metadata.

    Returns:
        Ansible task dictionary.

    """
    module_args: dict[str, Any] = {"cmd": raw}
    if creates:
        module_args["creates"] = creates

    task: dict[str, Any] = {
        "name": f"Shell: {raw[:60]}{'...' if len(raw) > 60 else ''}",
        "ansible.builtin.shell": module_args,
        "changed_when": "false",
        "failed_when": "result.rc != 0",
        "_metadata": {
            "source_line": line,
            "confidence": confidence,
            "idempotent": False,
        },
    }
    if idempotency_hint:
        task["_metadata"]["idempotency_hint"] = idempotency_hint
    if warning:
        task["_metadata"]["warning"] = warning
    return task


# ---------------------------------------------------------------------------
# Playbook renderer
# ---------------------------------------------------------------------------


def _render_playbook(tasks: list[dict[str, Any]], script_path: str) -> str:
    """
    Render a list of task dicts as a YAML playbook string.

    Internal ``_metadata`` keys are stripped from each task before
    rendering; they are only used internally for reporting.

    Args:
        tasks: List of Ansible task dictionaries (may contain ``_metadata``).
        script_path: Path label for the playbook name/comment.

    Returns:
        YAML string representing the Ansible playbook.

    """
    script_name = script_path.split("/")[-1]
    lines: list[str] = [
        f"# Generated by SousChef from {script_name}",
        "---",
        "- name: Converted from Bash script",
        "  hosts: all",
        "  become: true",
        "  tasks:",
    ]

    for task in tasks:
        # Strip internal metadata key
        clean_task = {k: v for k, v in task.items() if k != "_metadata"}
        lines.append("")
        lines.extend(_render_task(clean_task))

    return "\n".join(lines) + "\n"


def _render_task(task: dict[str, Any]) -> list[str]:
    """
    Render a single task dict as indented YAML lines.

    Args:
        task: Ansible task dictionary (without ``_metadata``).

    Returns:
        List of YAML lines for the task.

    """
    lines: list[str] = []
    name = task.get("name", "Unnamed task")
    lines.append(f"  - name: {_yaml_str(name)}")

    for key, value in task.items():
        if key == "name":
            continue
        if isinstance(value, dict):
            lines.append(f"    {key}:")
            for sub_key, sub_val in value.items():
                if isinstance(sub_val, list):
                    lines.append(f"      {sub_key}:")
                    for item in sub_val:
                        lines.append(f"        - {_yaml_str(str(item))}")
                elif isinstance(sub_val, bool):
                    lines.append(f"      {sub_key}: {str(sub_val).lower()}")
                else:
                    lines.append(f"      {sub_key}: {_yaml_str(str(sub_val))}")
        elif isinstance(value, bool):
            lines.append(f"    {key}: {str(value).lower()}")
        else:
            lines.append(f"    {key}: {_yaml_str(str(value))}")

    return lines


def _yaml_str(value: str) -> str:
    """
    Wrap a value in YAML quotes if it contains special characters.

    Args:
        value: String value to potentially quote.

    Returns:
        Quoted or unquoted string suitable for YAML output.

    """
    special = set(':{}[]|>&*!,\'#"')
    if any(c in value for c in special) or value.lower() in {"true", "false", "null"}:
        # Use double quotes and escape internal double quotes
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


# ---------------------------------------------------------------------------
# Warning and idempotency collectors
# ---------------------------------------------------------------------------


def _collect_warnings(ir: dict[str, Any]) -> list[str]:
    """
    Collect all warning messages from the IR.

    Args:
        ir: Intermediate representation dictionary.

    Returns:
        List of warning strings.

    """
    warnings: list[str] = []
    for fb in ir.get("shell_fallbacks", []):
        warnings.append(f"Line {fb['line']}: {fb['warning']} — `{fb['raw'][:60]}`")
    for risk in ir.get("idempotency_risks", []):
        msg = (
            f"Line {risk['line']}: Idempotency risk [{risk['type']}]"
            f" — {risk['suggestion']}"
        )
        warnings.append(msg)
    return warnings


def _build_idempotency_report(ir: dict[str, Any]) -> dict[str, Any]:
    """
    Build a summary idempotency report from the IR.

    Args:
        ir: Intermediate representation dictionary.

    Returns:
        Dictionary with ``risks``, ``total_risks``,
        ``non_idempotent_tasks``, and ``suggestions`` keys.

    """
    risks = ir.get("idempotency_risks", [])
    suggestions = list({r["suggestion"] for r in risks})
    return {
        "total_risks": len(risks),
        "risks": risks,
        "non_idempotent_tasks": len(ir.get("shell_fallbacks", [])),
        "suggestions": suggestions,
    }
