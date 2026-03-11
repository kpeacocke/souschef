"""SaltStack SLS to Ansible playbook converter."""

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
from souschef.parsers.salt import (
    SALT_PKG_FUNCTIONS,
    SALT_SERVICE_FUNCTIONS,
    _extract_pillars,
    _parse_sls_states,
)

# Ansible module mappings for Salt state categories
_ANSIBLE_MODULE_MAP: dict[str, str] = {
    "package": "ansible.builtin.package",
    "file_managed": "ansible.builtin.template",
    "file_directory": "ansible.builtin.file",
    "file_absent": "ansible.builtin.file",
    "file_symlink": "ansible.builtin.file",
    "file_recurse": "ansible.builtin.copy",
    "file_touch": "ansible.builtin.file",
    "file_replace": "ansible.builtin.lineinfile",
    "file_line": "ansible.builtin.lineinfile",
    "file_copy": "ansible.builtin.copy",
    "file_append": "ansible.builtin.blockinfile",
    "file_prepend": "ansible.builtin.blockinfile",
    "file_patch": "ansible.builtin.patch",
    "service": "ansible.builtin.service",
    "command": "ansible.builtin.command",
    "user": "ansible.builtin.user",
    "group": "ansible.builtin.group",
    "git": "ansible.builtin.git",
    "pip": "ansible.builtin.pip",
    "cron": "ansible.builtin.cron",
    "mount": "ansible.posix.mount",
    "archive": "ansible.builtin.unarchive",
    "sysctl": "ansible.posix.sysctl",
    "host": "ansible.builtin.lineinfile",
}


def _build_pkg_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible package task from a Salt pkg state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "installed")
    args = state.get("args", {})
    state_id = state.get("id", "package")

    pkg_state = SALT_PKG_FUNCTIONS.get(func, "present")
    name = args.get("name", state_id)
    pkgs = args.get("pkgs")

    task: dict[str, Any] = {
        "name": f"Manage package: {state_id}",
        "ansible.builtin.package": {"state": pkg_state},
    }

    if pkgs and isinstance(pkgs, list):
        task["ansible.builtin.package"]["name"] = pkgs
    elif isinstance(name, list):
        task["ansible.builtin.package"]["name"] = name
    else:
        task["ansible.builtin.package"]["name"] = str(name)

    return task


def _apply_file_ownership(params: dict[str, Any], args: dict[str, Any]) -> None:
    """
    Apply owner/group/mode params from Salt args to Ansible task params.

    Args:
        params: Ansible task params dict to update in-place.
        args: Salt state args dict.

    """
    owner = args.get("user")
    group = args.get("group")
    mode = args.get("mode")
    if owner:
        params["owner"] = str(owner)
    if group:
        params["group"] = str(group)
    if mode:
        params["mode"] = str(mode)


def _build_file_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible file/template/copy task from a Salt file state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "managed")
    args = state.get("args", {})
    state_id = state.get("id", "file")

    module_key = f"file_{func}"
    ansible_module = _ANSIBLE_MODULE_MAP.get(module_key, "ansible.builtin.file")

    task: dict[str, Any] = {"name": f"Manage file: {state_id}"}
    params: dict[str, Any] = {}

    dest = args.get("name", state_id)
    params["dest"] = str(dest)

    if func == "managed":
        source = args.get("source", "")
        if source:
            # Strip the salt:// prefix safely - only remove the scheme prefix
            src_str = str(source)
            if src_str.startswith("salt://"):
                src_str = src_str[len("salt://"):]
            # Reject path traversal attempts
            if ".." not in src_str:
                params["src"] = src_str
        _apply_file_ownership(params, args)
    elif func == "directory":
        params["path"] = params.pop("dest")
        params["state"] = "directory"
        _apply_file_ownership(params, args)
        ansible_module = "ansible.builtin.file"
    elif func == "absent":
        params["path"] = params.pop("dest")
        params["state"] = "absent"
        ansible_module = "ansible.builtin.file"
    elif func == "symlink":
        params["path"] = params.pop("dest")
        params["src"] = str(args.get("target", ""))
        params["state"] = "link"
        ansible_module = "ansible.builtin.file"
    elif func in ("replace", "line"):
        params.pop("dest", None)
        params["path"] = str(dest)
        params["regexp"] = str(args.get("pattern", ""))
        params["line"] = str(args.get("repl", ""))
        ansible_module = "ansible.builtin.lineinfile"
    elif func in ("append", "prepend"):
        params.pop("dest", None)
        params["path"] = str(dest)
        params["block"] = str(args.get("text", args.get("content", "")))
        ansible_module = "ansible.builtin.blockinfile"

    task[ansible_module] = params
    return task


def _build_service_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible service task from a Salt service state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "running")
    args = state.get("args", {})
    state_id = state.get("id", "service")

    svc_map: dict[str, Any] = SALT_SERVICE_FUNCTIONS.get(
        func, {"state": "started", "enabled": None}
    )
    name = args.get("name", state_id)

    params: dict[str, Any] = {"name": str(name)}
    state_val = svc_map.get("state")
    enabled_val = svc_map.get("enabled")
    if state_val is not None:
        params["state"] = state_val
    if enabled_val is not None:
        params["enabled"] = enabled_val

    task: dict[str, Any] = {
        "name": f"Manage service: {state_id}",
        "ansible.builtin.service": params,
    }
    return task


def _build_cmd_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible command/shell task from a Salt cmd state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "run")
    args = state.get("args", {})
    state_id = state.get("id", "command")

    cmd = args.get("name", state_id)
    cwd = args.get("cwd")
    creates = args.get("creates")
    unless = args.get("unless")

    params: dict[str, Any] = {"cmd": str(cmd)}
    if cwd:
        params["chdir"] = str(cwd)
    if creates:
        params["creates"] = str(creates)

    if func == "script":
        ansible_module = "ansible.builtin.shell"
    else:
        ansible_module = "ansible.builtin.command"

    task: dict[str, Any] = {
        "name": f"Run command: {state_id}",
        ansible_module: params,
    }

    if unless:
        task["when"] = f"not ({unless})"

    return task


def _build_user_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible user task from a Salt user state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "present")
    args = state.get("args", {})
    state_id = state.get("id", "user")

    name = args.get("name", state_id)
    params: dict[str, Any] = {
        "name": str(name),
        "state": "present" if func == "present" else "absent",
    }

    if func == "present":
        for key in ("uid", "gid", "home", "shell", "comment", "groups"):
            val = args.get(key)
            if val is not None:
                params[key] = val

    task: dict[str, Any] = {
        "name": f"Manage user: {state_id}",
        "ansible.builtin.user": params,
    }
    return task


def _build_group_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible group task from a Salt group state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "present")
    args = state.get("args", {})
    state_id = state.get("id", "group")

    name = args.get("name", state_id)
    params: dict[str, Any] = {
        "name": str(name),
        "state": "present" if func == "present" else "absent",
    }
    gid = args.get("gid")
    if gid is not None:
        params["gid"] = gid

    task: dict[str, Any] = {
        "name": f"Manage group: {state_id}",
        "ansible.builtin.group": params,
    }
    return task


def _build_git_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible git task from a Salt git state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    args = state.get("args", {})
    state_id = state.get("id", "git")

    repo = args.get("name", args.get("address", state_id))
    dest = args.get("target", f"/opt/{state_id}")
    rev = args.get("rev", "HEAD")

    task: dict[str, Any] = {
        "name": f"Clone git repo: {state_id}",
        "ansible.builtin.git": {
            "repo": str(repo),
            "dest": str(dest),
            "version": str(rev),
        },
    }
    return task


def _build_pip_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build an Ansible pip task from a Salt pip state.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    func = state.get("function", "installed")
    args = state.get("args", {})
    state_id = state.get("id", "pip")

    name = args.get("name", args.get("pkgs", state_id))
    params: dict[str, Any] = {
        "name": name,
        "state": SALT_PKG_FUNCTIONS.get(func, "present"),
    }
    venv = args.get("bin_env")
    if venv:
        params["virtualenv"] = str(venv)

    task: dict[str, Any] = {
        "name": f"Manage pip package: {state_id}",
        "ansible.builtin.pip": params,
    }
    return task


def _build_generic_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Build a generic shell task for unsupported Salt states.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict with a warning comment.

    """
    state_id = state.get("id", "unknown")
    module = state.get("module", "unknown")
    func = state.get("function", "unknown")

    msg = f"Manual conversion required for Salt state: {module}.{func} ({state_id})"
    task: dict[str, Any] = {
        "name": f"TODO: Convert Salt {module}.{func}: {state_id}",
        "ansible.builtin.debug": {"msg": msg},
        "tags": ["salt_unconverted"],
    }
    return task


_TASK_BUILDERS = {
    "pkg": _build_pkg_task,
    "file": _build_file_task,
    "service": _build_service_task,
    "cmd": _build_cmd_task,
    "user": _build_user_task,
    "group": _build_group_task,
    "git": _build_git_task,
    "pip": _build_pip_task,
}


def _convert_state_to_task(state: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a single Salt state entry to an Ansible task dict.

    Args:
        state: Salt state entry dict.

    Returns:
        Ansible task dict.

    """
    module = state.get("module", "")
    builder = _TASK_BUILDERS.get(module, _build_generic_task)
    return builder(state)


def _pillar_to_ansible_vars(pillar_provenance: dict[str, Any]) -> dict[str, Any]:
    """
    Convert pillar provenance mapping to Ansible variable definitions.

    Pillar keys are converted to Ansible variable names with their default
    values. Variable names use underscores instead of dots.

    Args:
        pillar_provenance: Dict from _extract_pillars().

    Returns:
        Dict of Ansible variable name -> default value or placeholder.

    """
    vars_dict: dict[str, Any] = {}
    for key, meta in pillar_provenance.items():
        var_name = key.replace(".", "_").replace("-", "_").replace(":", "_")
        default = meta.get("default")
        if default is not None:
            vars_dict[var_name] = default
        else:
            vars_dict[var_name] = f"{{{{ {var_name} }}}}"
    return vars_dict


def convert_salt_sls_to_ansible(sls_path: str, playbook_name: str = "") -> str:
    """
    Convert a SaltStack SLS state file to an Ansible playbook.

    Reads a Salt SLS file, converts each state definition to the equivalent
    Ansible task, maps pillar variables to Ansible vars, and returns the
    complete playbook as YAML text with a JSON report.

    Supported Salt modules: pkg, file, service, cmd, user, group, git, pip.
    Unsupported modules generate debug tasks tagged ``salt_unconverted``.

    Args:
        sls_path: Path to the SLS state file.
        playbook_name: Optional name for the generated playbook. Defaults to
            the SLS file stem.

    Returns:
        JSON string with keys:
            - ``playbook``: YAML text of the generated Ansible playbook.
            - ``tasks_converted``: Count of successfully mapped tasks.
            - ``tasks_unconverted``: Count of tasks requiring manual review.
            - ``ansible_vars``: Ansible variable definitions from pillar keys.
            - ``warnings``: List of conversion warning messages.

    """
    try:
        normalized_path = _normalize_path(sls_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_path.exists():  # NOSONAR
            return json.dumps({"error": ERROR_FILE_NOT_FOUND.format(path=safe_path)})
        if safe_path.is_dir():
            return json.dumps({"error": ERROR_IS_DIRECTORY.format(path=safe_path)})

        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

    except PermissionError:
        return json.dumps({"error": ERROR_PERMISSION_DENIED.format(path=sls_path)})
    except ValueError as e:
        return json.dumps({"error": str(e)})

    name = playbook_name or safe_path.stem
    states = _parse_sls_states(content)
    pillars = _extract_pillars(content)
    ansible_vars = _pillar_to_ansible_vars(pillars)

    tasks = []
    tasks_converted = 0
    tasks_unconverted = 0
    warnings: list[str] = []

    for state in states:
        task = _convert_state_to_task(state)
        tasks.append(task)
        module = state.get("module", "")
        if module in _TASK_BUILDERS:
            tasks_converted += 1
        else:
            tasks_unconverted += 1
            warnings.append(
                f"Unsupported Salt module '{module}.{state.get('function')}' "
                f"for state '{state.get('id')}' - manual conversion required"
            )

    # Render playbook as YAML
    playbook_yaml = _render_playbook_yaml(name, tasks, ansible_vars)

    result: dict[str, Any] = {
        "playbook": playbook_yaml,
        "tasks_converted": tasks_converted,
        "tasks_unconverted": tasks_unconverted,
        "ansible_vars": ansible_vars,
        "warnings": warnings,
    }

    return json.dumps(result, indent=2)


def _render_playbook_yaml(
    name: str,
    tasks: list[dict[str, Any]],
    ansible_vars: dict[str, Any],
) -> str:
    """
    Render Ansible playbook as a YAML string.

    Args:
        name: Playbook/play name.
        tasks: List of Ansible task dicts.
        ansible_vars: Variable definitions for the play.

    Returns:
        YAML string representation of the playbook.

    """
    lines: list[str] = []
    lines.append("---")
    lines.append(f"- name: Converted from Salt: {name}")
    lines.append("  hosts: all")
    lines.append("  become: true")

    if ansible_vars:
        lines.append("  vars:")
        for var_name, var_value in ansible_vars.items():
            if var_value is None:
                lines.append(f"    {var_name}: null")
            elif isinstance(var_value, str) and "{{" in var_value:
                lines.append(f"    {var_name}: {var_value}")
            elif isinstance(var_value, str):
                lines.append(f"    {var_name}: '{var_value}'")
            else:
                lines.append(f"    {var_name}: {var_value}")

    if tasks:
        lines.append("  tasks:")
        for task in tasks:
            _render_task_lines(lines, task)

    return "\n".join(lines) + "\n"


def _render_param_value(lines: list[str], pk: str, pv: Any) -> None:
    """
    Render a single task parameter key-value pair as YAML lines.

    Args:
        lines: Output line list to append to.
        pk: Parameter key name.
        pv: Parameter value.

    """
    if isinstance(pv, list):
        lines.append(f"        {pk}:")
        for item in pv:
            lines.append(f"          - {item}")
    elif pv is None:
        lines.append(f"        {pk}:")
    elif isinstance(pv, bool):
        lines.append(f"        {pk}: {str(pv).lower()}")
    elif isinstance(pv, (int, float)):
        lines.append(f"        {pk}: {pv}")
    else:
        lines.append(f"        {pk}: {pv}")


def _render_task_lines(lines: list[str], task: dict[str, Any]) -> None:
    """
    Render a single Ansible task as YAML lines.

    Args:
        lines: Output line list to append to.
        task: Ansible task dict.

    """
    task_name = task.get("name", "Unnamed task")
    lines.append(f"    - name: {task_name}")

    for key, val in task.items():
        if key in ("name", "when", "tags"):
            continue
        if isinstance(val, dict):
            lines.append(f"      {key}:")
            for pk, pv in val.items():
                _render_param_value(lines, pk, pv)
        else:
            lines.append(f"      {key}: {val}")

    when = task.get("when")
    if when:
        lines.append(f"      when: {when}")

    tags = task.get("tags")
    if tags:
        if isinstance(tags, list):
            lines.append("      tags:")
            for tag in tags:
                lines.append(f"        - {tag}")
        else:
            lines.append(f"      tags: [{tags}]")
