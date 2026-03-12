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
import textwrap
from pathlib import Path
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
        return json.dumps({"error": f"{ERROR_IS_DIRECTORY}: {path}", "status": "error"})
    except PermissionError:
        return json.dumps(
            {"error": f"{ERROR_PERMISSION_DENIED}: {path}", "status": "error"}
        )
    except (ValueError, OSError) as exc:
        return json.dumps({"error": f"Error reading file: {exc}", "status": "error"})

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
        ``idempotency_report``, ``aap_hints``, ``quality_score``,
        and ``status``.

    """
    ir = _parse_bash_content(content)
    tasks = _build_tasks(ir)
    warnings = _collect_warnings(ir)
    idempotency_report = _build_idempotency_report(ir)
    playbook_yaml = _render_playbook(tasks, script_path)
    aap_hints = _build_aap_hints(ir, script_path)
    quality_score = _build_quality_score(ir, tasks)

    return json.dumps(
        {
            "status": "success",
            "script_path": script_path,
            "playbook_yaml": playbook_yaml,
            "tasks": tasks,
            "warnings": warnings,
            "idempotency_report": idempotency_report,
            "aap_hints": aap_hints,
            "quality_score": quality_score,
        },
        indent=2,
    )


def generate_ansible_role_from_bash(
    content: str,
    role_name: str = "bash_converted",
    script_path: str = "script.sh",
) -> str:
    """
    Generate an Ansible role directory structure from Bash script content.

    Parses the script, builds tasks split across role task files, generates
    handlers, defaults, vars, meta, and a README.  Returns a JSON envelope
    containing all file contents keyed by their relative path within the
    role directory.

    Args:
        content: Raw Bash script text.
        role_name: Name for the generated Ansible role.
        script_path: Original script path label used in comments.

    Returns:
        JSON string with keys ``status``, ``role_name``, ``files``
        (dict of relative path → content), ``quality_score``, and
        ``aap_hints``.

    """
    ir = _parse_bash_content(content)
    tasks = _build_tasks(ir)
    aap_hints = _build_aap_hints(ir, script_path)
    quality_score = _build_quality_score(ir, tasks)

    files: dict[str, str] = {
        "tasks/main.yml": _render_role_tasks_main(role_name),
        "tasks/packages.yml": _render_role_task_file(
            _package_tasks(ir.get("packages", [])),
            f"Package install tasks — converted from {script_path}",
        ),
        "tasks/services.yml": _render_role_task_file(
            _service_tasks(ir.get("services", [])),
            f"Service management tasks — converted from {script_path}",
        ),
        "tasks/users.yml": _render_role_task_file(
            _user_tasks(ir.get("users", [])) + _group_tasks(ir.get("groups", [])),
            f"User and group management tasks — converted from {script_path}",
        ),
        "tasks/files.yml": _render_role_task_file(
            _file_write_tasks(ir.get("file_writes", []))
            + _file_perm_tasks(ir.get("file_perms", [])),
            f"File write and permission tasks — converted from {script_path}",
        ),
        "tasks/misc.yml": _render_role_task_file(
            _git_tasks(ir.get("git_ops", []))
            + _archive_tasks(ir.get("archives", []))
            + _sed_tasks(ir.get("sed_ops", []))
            + _cron_tasks(ir.get("cron_jobs", []))
            + _firewall_tasks(ir.get("firewall_rules", []))
            + _hostname_tasks(ir.get("hostname_ops", []))
            + _download_tasks(ir.get("downloads", []))
            + _shell_fallback_tasks(ir.get("shell_fallbacks", [])),
            f"Miscellaneous tasks — converted from {script_path}",
        ),
        "handlers/main.yml": _render_role_handlers(ir),
        "defaults/main.yml": _render_role_defaults(ir),
        "vars/main.yml": _render_role_vars(),
        "meta/main.yml": _render_role_meta(role_name),
        "README.md": _render_role_readme(role_name, ir, quality_score, script_path),
    }

    return json.dumps(
        {
            "status": "success",
            "role_name": role_name,
            "files": files,
            "quality_score": quality_score,
            "aap_hints": aap_hints,
        },
        indent=2,
    )


def generate_ansible_role_from_bash_file(
    path: str,
    role_name: str = "bash_converted",
) -> str:
    """
    Generate an Ansible role from a Bash script file.

    Reads the script at *path* and delegates to
    :func:`generate_ansible_role_from_bash`.

    Args:
        path: Path to the Bash script file.
        role_name: Name for the generated Ansible role.

    Returns:
        JSON string — see :func:`generate_ansible_role_from_bash` for
        the structure.  Returns a JSON error object on failure.

    """
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
        return json.dumps({"error": f"{ERROR_IS_DIRECTORY}: {path}", "status": "error"})
    except PermissionError:
        return json.dumps(
            {"error": f"{ERROR_PERMISSION_DENIED}: {path}", "status": "error"}
        )
    except (ValueError, OSError) as exc:
        return json.dumps({"error": f"Error reading file: {exc}", "status": "error"})

    return generate_ansible_role_from_bash(
        content, role_name=role_name, script_path=path
    )


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
    tasks.extend(_user_tasks(ir.get("users", [])))
    tasks.extend(_group_tasks(ir.get("groups", [])))
    tasks.extend(_file_perm_tasks(ir.get("file_perms", [])))
    tasks.extend(_git_tasks(ir.get("git_ops", [])))
    tasks.extend(_archive_tasks(ir.get("archives", [])))
    tasks.extend(_sed_tasks(ir.get("sed_ops", [])))
    tasks.extend(_cron_tasks(ir.get("cron_jobs", [])))
    tasks.extend(_firewall_tasks(ir.get("firewall_rules", [])))
    tasks.extend(_hostname_tasks(ir.get("hostname_ops", [])))
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
                    "dest": "{{ download_dest_dir | default('/opt/downloads') }}"
                     f"/{dest_name}",
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


def _user_tasks(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert user-management IR entries to Ansible task dicts.

    Args:
        users: List of user IR entries.

    Returns:
        List of Ansible task dictionaries using ``ansible.builtin.user``.

    """
    _state_map = {"create": "present", "modify": "present", "remove": "absent"}
    tasks = []
    for entry in users:
        state = _state_map.get(entry["action"], "present")
        # Try to extract the username from the raw command (last non-flag token)
        tokens = [t for t in entry["raw"].split() if not t.startswith("-")]
        name = tokens[-1] if len(tokens) > 1 else "UNKNOWN_USER"
        task: dict[str, Any] = {
            "name": f"Manage user {name}",
            "ansible.builtin.user": {
                "name": name,
                "state": state,
            },
            "_metadata": {
                "source_line": entry["line"],
                "confidence": entry["confidence"],
                "idempotent": True,
            },
        }
        tasks.append(task)
    return tasks


def _group_tasks(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert group-management IR entries to Ansible task dicts.

    Args:
        groups: List of group IR entries.

    Returns:
        List of Ansible task dictionaries using ``ansible.builtin.group``.

    """
    _state_map = {"create": "present", "modify": "present", "remove": "absent"}
    tasks = []
    for entry in groups:
        state = _state_map.get(entry["action"], "present")
        tokens = [t for t in entry["raw"].split() if not t.startswith("-")]
        name = tokens[-1] if len(tokens) > 1 else "UNKNOWN_GROUP"
        task: dict[str, Any] = {
            "name": f"Manage group {name}",
            "ansible.builtin.group": {
                "name": name,
                "state": state,
            },
            "_metadata": {
                "source_line": entry["line"],
                "confidence": entry["confidence"],
                "idempotent": True,
            },
        }
        tasks.append(task)
    return tasks


def _file_perm_tasks(file_perms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert file-permission IR entries to Ansible task dicts.

    Args:
        file_perms: List of file permission IR entries.

    Returns:
        List of Ansible task dictionaries using ``ansible.builtin.file``.

    """
    tasks = []
    for entry in file_perms:
        module_args: dict[str, Any] = {"path": entry["path"]}
        if entry["op"] == "chmod" and entry["mode"]:
            module_args["mode"] = entry["mode"]
        if entry["op"] == "chown" and entry["owner"]:
            parts = entry["owner"].split(":")
            module_args["owner"] = parts[0]
            if len(parts) > 1:
                module_args["group"] = parts[1]
        if entry["recursive"]:
            module_args["recurse"] = True
        task: dict[str, Any] = {
            "name": f"Set {entry['op']} on {entry['path']}",
            "ansible.builtin.file": module_args,
            "_metadata": {
                "source_line": entry["line"],
                "confidence": entry["confidence"],
                "idempotent": True,
            },
        }
        tasks.append(task)
    return tasks


def _git_tasks(git_ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert git operation IR entries to Ansible task dicts.

    Args:
        git_ops: List of git operation IR entries.

    Returns:
        List of Ansible task dictionaries using ``ansible.builtin.git``.

    """
    tasks = []
    for entry in git_ops:
        if entry["action"] == "clone" and entry.get("repo"):
            dest = (
                entry.get("dest") or "/opt/" + entry["repo"].rstrip("/").split("/")[-1]
            )
            task: dict[str, Any] = {
                "name": f"Git clone {entry['repo']}",
                "ansible.builtin.git": {
                    "repo": entry["repo"],
                    "dest": dest,
                    "version": "HEAD",
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
                idempotency_hint="Consider ansible.builtin.git for git operations",
            )
        tasks.append(task)
    return tasks


def _archive_tasks(archives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert archive extraction IR entries to Ansible task dicts.

    Args:
        archives: List of archive IR entries.

    Returns:
        List of Ansible task dictionaries using ``ansible.builtin.unarchive``.

    """
    tasks = []
    for entry in archives:
        src = entry.get("source", "UNKNOWN_ARCHIVE")
        # Derive destination directory from source path; fall back to a
        # configurable variable so users can set an appropriate location.
        if "/" in src:
            dest = str(Path(src).parent)
        else:
            dest = "{{ archive_dest_dir | default('/opt/archives') }}"
        task: dict[str, Any] = {
            "name": f"Extract archive {src}",
            "ansible.builtin.unarchive": {
                "src": src,
                "dest": dest,
                "remote_src": True,
            },
            "_metadata": {
                "source_line": entry["line"],
                "confidence": entry["confidence"],
                "idempotent": False,
                "idempotency_hint": "Add 'creates' parameter to avoid re-extraction",
            },
        }
        tasks.append(task)
    return tasks


def _sed_tasks(sed_ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert sed in-place IR entries to shell task dicts with a hint.

    sed operations are complex to auto-convert; they fall back to shell
    with a recommendation to use ``ansible.builtin.lineinfile`` or
    ``ansible.builtin.replace``.

    Args:
        sed_ops: List of sed operation IR entries.

    Returns:
        List of Ansible shell task dictionaries.

    """
    return [
        _shell_task(
            entry["raw"],
            entry["line"],
            entry["confidence"],
            idempotency_hint=(
                "Replace with ansible.builtin.lineinfile or ansible.builtin.replace"
            ),
        )
        for entry in sed_ops
    ]


def _cron_tasks(cron_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert cron job IR entries to shell task dicts with a hint.

    Cron jobs are complex to auto-convert; they fall back to shell with
    a recommendation to use ``ansible.builtin.cron``.

    Args:
        cron_jobs: List of cron job IR entries.

    Returns:
        List of Ansible shell task dictionaries.

    """
    return [
        _shell_task(
            entry["raw"],
            entry["line"],
            entry["confidence"],
            idempotency_hint="Replace with ansible.builtin.cron task",
        )
        for entry in cron_jobs
    ]


def _firewall_tasks(firewall_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert firewall rule IR entries to Ansible task dicts.

    The Ansible module is chosen based on the detected tool
    (ufw → ``community.general.ufw``, firewalld → ``ansible.posix.firewalld``,
    iptables → ``ansible.builtin.iptables``).

    Args:
        firewall_rules: List of firewall rule IR entries.

    Returns:
        List of Ansible task dictionaries.

    """
    tasks = []
    for entry in firewall_rules:
        module = entry.get("ansible_module", "ansible.builtin.shell")
        if entry["confidence"] >= _CONFIDENCE_THRESHOLD:
            task: dict[str, Any] = {
                "name": (f"Configure {entry['tool']} rule (line {entry['line']})"),
                module: {
                    "rule": entry["raw"],
                    "state": "present",
                },
                "_metadata": {
                    "source_line": entry["line"],
                    "confidence": entry["confidence"],
                    "idempotent": True,
                    "idempotency_hint": (f"Review and adjust {module} parameters"),
                },
            }
        else:
            task = _shell_task(
                entry["raw"],
                entry["line"],
                entry["confidence"],
                idempotency_hint=f"Consider using {module}",
            )
        tasks.append(task)
    return tasks


def _hostname_tasks(hostname_ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Convert hostname operation IR entries to Ansible task dicts.

    Args:
        hostname_ops: List of hostname operation IR entries.

    Returns:
        List of Ansible task dictionaries using ``ansible.builtin.hostname``.

    """
    tasks = []
    for entry in hostname_ops:
        hostname = entry.get("hostname") or "UNKNOWN_HOSTNAME"
        task: dict[str, Any] = {
            "name": f"Set hostname to {hostname}",
            "ansible.builtin.hostname": {
                "name": hostname,
            },
            "_metadata": {
                "source_line": entry["line"],
                "confidence": entry["confidence"],
                "idempotent": True,
            },
        }
        tasks.append(task)
    return tasks


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
    special = set(":{}[]|>&*!,'#\"")
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


def _build_aap_hints(ir: dict[str, Any], script_path: str) -> dict[str, Any]:
    """
    Build Ansible Automation Platform (AAP) deployment hints from the IR.

    Produces suggested execution environment, credential types, survey
    variables, and advisory notes to aid in configuring an AAP job template.

    Args:
        ir: Intermediate representation from the Bash parser.
        script_path: Original script path label used in notes.

    Returns:
        Dictionary with ``suggested_ee``, ``suggested_credentials``,
        ``become_enabled``, ``timeout``, ``survey_variables``, and
        ``notes`` keys.

    """
    notes: list[str] = []
    if ir.get("sensitive_data"):
        notes.append("Script contains hardcoded credentials — use ansible-vault")
    if ir.get("cm_escapes"):
        tools = {c["tool"] for c in ir["cm_escapes"]}
        notes.append(
            "Script contains "
            + "/".join(sorted(tools))
            + " calls — review for native Ansible equivalents"
        )
    if ir.get("firewall_rules"):
        notes.append(
            "Firewall rules detected — ensure required collections are installed"
        )
    if ir.get("git_ops"):
        notes.append(
            "Git operations detected — ensure git is available on target hosts"
        )

    survey_vars = [
        {
            "name": var["name"],
            "description": f"{var['name']} variable from script",
            "type": "text",
            "default": "" if var["is_sensitive"] else var["value"],
            "required": var["is_sensitive"],
        }
        for var in ir.get("env_vars", [])
        if not var["is_sensitive"]
    ][:10]

    return {
        "suggested_ee": (
            "registry.redhat.io/ansible-automation-platform/ee-supported-rhel8:latest"
        ),
        "suggested_credentials": ["Machine"],
        "become_enabled": True,
        "timeout": 3600,
        "survey_variables": survey_vars,
        "notes": notes,
    }


def _build_quality_score(
    ir: dict[str, Any], tasks: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Compute a quality score for the conversion.

    Grades the playbook from A to F based on the proportion of structured
    (idempotent) tasks versus shell fallbacks, with a penalty for detected
    sensitive data.

    Args:
        ir: Intermediate representation from the Bash parser.
        tasks: List of Ansible task dictionaries produced by
            :func:`_build_tasks`.

    Returns:
        Dictionary with ``grade``, ``total_operations``,
        ``structured_operations``, ``shell_fallbacks``,
        ``coverage_pct``, ``idempotency_score``, and ``improvements``
        keys.

    """
    total = len(tasks)
    if total == 0:
        return {
            "grade": "N/A",
            "coverage_pct": 0,
            "total_operations": 0,
            "structured_operations": 0,
            "shell_fallbacks": 0,
            "idempotency_score": 0,
            "improvements": [],
        }

    structured = sum(
        1 for t in tasks if t.get("_metadata", {}).get("idempotent", False)
    )
    shell_count = total - structured
    coverage_pct = int(structured / total * 100)
    sensitive_penalty = min(20, len(ir.get("sensitive_data", [])) * 5)
    idempotency_score = max(0, coverage_pct - sensitive_penalty)

    if idempotency_score >= 90:
        grade = "A"
    elif idempotency_score >= 75:
        grade = "B"
    elif idempotency_score >= 60:
        grade = "C"
    elif idempotency_score >= 40:
        grade = "D"
    else:
        grade = "F"

    improvements: list[str] = []
    if ir.get("sensitive_data"):
        improvements.append("Encrypt secrets with ansible-vault")
    if ir.get("sed_ops"):
        improvements.append(
            "Replace sed -i with ansible.builtin.lineinfile or ansible.builtin.replace"
        )
    if ir.get("cron_jobs"):
        improvements.append("Replace crontab calls with ansible.builtin.cron tasks")
    if ir.get("cm_escapes"):
        improvements.append("Replace CM tool calls with native Ansible modules")

    return {
        "grade": grade,
        "total_operations": total,
        "structured_operations": structured,
        "shell_fallbacks": shell_count,
        "coverage_pct": coverage_pct,
        "idempotency_score": idempotency_score,
        "improvements": improvements,
    }


# ---------------------------------------------------------------------------
# Role structure renderers
# ---------------------------------------------------------------------------


def _render_role_tasks_main(role_name: str) -> str:
    """
    Render the role ``tasks/main.yml`` file that includes sub-task files.

    Args:
        role_name: Name of the role.

    Returns:
        YAML string for the tasks/main.yml file.

    """
    return textwrap.dedent(
        f"""\
        # tasks/main.yml — generated by SousChef for role '{role_name}'
        ---
        - name: Install packages
          ansible.builtin.import_tasks: packages.yml

        - name: Manage services
          ansible.builtin.import_tasks: services.yml

        - name: Manage users and groups
          ansible.builtin.import_tasks: users.yml

        - name: Manage files and permissions
          ansible.builtin.import_tasks: files.yml

        - name: Miscellaneous tasks
          ansible.builtin.import_tasks: misc.yml
        """
    )


def _render_role_task_file(tasks: list[dict[str, Any]], comment: str) -> str:
    """
    Render a role task YAML file from a list of task dicts.

    Args:
        tasks: List of Ansible task dictionaries.
        comment: Comment line placed at the top of the file.

    Returns:
        YAML string for the task file.

    """
    lines = [f"# {comment}", "---"]
    if not tasks:
        lines.append("# No tasks detected for this category.")
        lines.append("[]")
        return "\n".join(lines) + "\n"
    for task in tasks:
        clean_task = {k: v for k, v in task.items() if k != "_metadata"}
        lines.append("")
        lines.extend(_render_task(clean_task))
    return "\n".join(lines) + "\n"


def _render_role_handlers(ir: dict[str, Any]) -> str:
    """
    Render the role ``handlers/main.yml`` with service restart handlers.

    A handler is generated for each unique service detected in the IR.

    Args:
        ir: Intermediate representation from the Bash parser.

    Returns:
        YAML string for the handlers/main.yml file.

    """
    services = ir.get("services", [])
    seen: set[str] = set()
    lines = ["# handlers/main.yml — generated by SousChef", "---"]
    for svc in services:
        name = svc["name"]
        if name in seen:
            continue
        seen.add(name)
        lines.append("")
        lines.append(f"- name: Restart {name}")
        lines.append("  ansible.builtin.service:")
        lines.append(f"    name: {name}")
        lines.append("    state: restarted")
    if not seen:
        lines.append("# No service handlers generated.")
        lines.append("[]")
    return "\n".join(lines) + "\n"


def _render_role_defaults(ir: dict[str, Any]) -> str:
    """
    Render the role ``defaults/main.yml`` from detected env vars.

    Sensitive variables are given an empty default and a vault comment.
    Non-sensitive variables use the detected value as the default.

    Args:
        ir: Intermediate representation from the Bash parser.

    Returns:
        YAML string for the defaults/main.yml file.

    """
    lines = ["# defaults/main.yml — generated by SousChef", "---"]
    env_vars = ir.get("env_vars", [])
    if not env_vars:
        lines.append("# No environment variables detected.")
    for var in env_vars:
        if var["is_sensitive"]:
            lines.append(f"# {var['name']}: ''  # TODO: set via ansible-vault")
        else:
            value = var["value"]
            lines.append(f"{var['name'].lower()}: {_yaml_str(value)}")
    return "\n".join(lines) + "\n"


def _render_role_vars() -> str:
    """
    Render an empty role ``vars/main.yml`` file.

    Returns:
        YAML string for the vars/main.yml file.

    """
    return "# vars/main.yml — generated by SousChef\n---\n"


def _render_role_meta(role_name: str) -> str:
    """
    Render the role ``meta/main.yml`` with basic metadata.

    Args:
        role_name: Name of the role.

    Returns:
        YAML string for the meta/main.yml file.

    """
    return textwrap.dedent(
        f"""\
        # meta/main.yml — generated by SousChef
        ---
        galaxy_info:
          role_name: {role_name}
          description: >
            Auto-generated role converted from a Bash script by SousChef.
          min_ansible_version: "2.9"
          platforms:
            - name: EL
              versions:
                - "8"
                - "9"
            - name: Ubuntu
              versions:
                - focal
                - jammy
        dependencies: []
        """
    )


def _render_role_readme(
    role_name: str,
    ir: dict[str, Any],
    quality_score: dict[str, Any],
    script_path: str,
) -> str:
    """
    Render an auto-generated README.md for the role.

    Args:
        role_name: Name of the role.
        ir: Intermediate representation from the Bash parser.
        quality_score: Quality score dictionary from :func:`_build_quality_score`.
        script_path: Original script path label.

    Returns:
        Markdown string for the role README.

    """
    grade = quality_score.get("grade", "N/A")
    coverage = quality_score.get("coverage_pct", 0)
    improvements = quality_score.get("improvements", [])

    improvements_md = (
        "\n".join(f"- {i}" for i in improvements)
        if improvements
        else "_No improvements required._"
    )

    env_vars = ir.get("env_vars", [])
    vars_md = ""
    if env_vars:
        rows = "\n".join(
            f"| `{v['name']}` | `{'' if v['is_sensitive'] else v['value']}` "
            f"| {'Yes (vault)' if v['is_sensitive'] else 'No'} |"
            for v in env_vars
        )
        vars_md = (
            "\n## Role Variables\n\n"
            "| Variable | Default | Sensitive |\n"
            "| --- | --- | --- |\n" + rows + "\n"
        )

    return textwrap.dedent(
        f"""\
        # {role_name}

        Auto-generated Ansible role converted from `{script_path}` by
        [SousChef](https://github.com/your-org/souschef).

        ## Quality Score

        | Metric | Value |
        | --- | --- |
        | Grade | **{grade}** |
        | Coverage | {coverage}% |
        | Total operations | {quality_score.get("total_operations", 0)} |
        | Structured operations | {quality_score.get("structured_operations", 0)} |
        | Shell fallbacks | {quality_score.get("shell_fallbacks", 0)} |

        ## Suggested Improvements

        {improvements_md}
        {vars_md}
        ## Example Playbook

        ```yaml
        - hosts: servers
          roles:
            - role: {role_name}
        ```

        ## Licence

        MIT
        """
    )
