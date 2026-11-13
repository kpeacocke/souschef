"""SaltStack SLS to Ansible playbook converter."""

import json
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
    safe_exists,
    safe_is_dir,
    safe_mkdir,
    safe_read_text,
    safe_write_text,
)
from souschef.parsers.salt import (
    SALT_PKG_FUNCTIONS,
    SALT_SERVICE_FUNCTIONS,
    _extract_pillars,
    _parse_sls_states,
)

# Module name constants to avoid duplicate literals (S1192)
_MOD_PACKAGE = "ansible.builtin.package"
_MOD_FILE = "ansible.builtin.file"
_MOD_LINEINFILE = "ansible.builtin.lineinfile"
_MOD_BLOCKINFILE = "ansible.builtin.blockinfile"
_MOD_SERVICE = "ansible.builtin.service"
_MOD_COMMAND = "ansible.builtin.command"
_MOD_COPY = "ansible.builtin.copy"
_SALT_URL_PREFIX = "salt://"
_SALT_FILES_PREFIX = "files/"
_SALT_TEMPLATES_PREFIX = "templates/"
_TOP_SLS = "top.sls"
_MAIN_YML = "main.yml"

# Ansible module mappings for Salt state categories
_ANSIBLE_MODULE_MAP: dict[str, str] = {
    "package": _MOD_PACKAGE,
    "file_managed": "ansible.builtin.template",
    "file_directory": _MOD_FILE,
    "file_absent": _MOD_FILE,
    "file_symlink": _MOD_FILE,
    "file_recurse": _MOD_COPY,
    "file_touch": _MOD_FILE,
    "file_replace": _MOD_LINEINFILE,
    "file_line": _MOD_LINEINFILE,
    "file_copy": _MOD_COPY,
    "file_append": _MOD_BLOCKINFILE,
    "file_prepend": _MOD_BLOCKINFILE,
    "file_patch": "ansible.builtin.patch",
    "service": _MOD_SERVICE,
    "command": _MOD_COMMAND,
    "user": "ansible.builtin.user",
    "group": "ansible.builtin.group",
    "git": "ansible.builtin.git",
    "pip": "ansible.builtin.pip",
    "cron": "ansible.builtin.cron",
    "mount": "ansible.posix.mount",
    "archive": "ansible.builtin.unarchive",
    "sysctl": "ansible.posix.sysctl",
    "host": _MOD_LINEINFILE,
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
        _MOD_PACKAGE: {"state": pkg_state},
    }

    if pkgs and isinstance(pkgs, list):
        task[_MOD_PACKAGE]["name"] = pkgs
    elif isinstance(name, list):
        task[_MOD_PACKAGE]["name"] = name
    else:
        task[_MOD_PACKAGE]["name"] = str(name)

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
    dest = args.get("name", state_id)

    if func == "managed":
        return _build_managed_file_task(state_id, dest, args)
    if func == "recurse":
        return _build_recurse_file_task(state_id, dest, args)
    if func in {"directory", "absent", "symlink"}:
        return _build_simple_file_task(func, state_id, dest, args)
    if func in {"replace", "line", "append", "prepend"}:
        return _build_line_file_task(func, state_id, dest, args)

    module = _ANSIBLE_MODULE_MAP.get(f"file_{func}", _MOD_FILE)
    return _named_file_task(state_id, module, {"dest": str(dest)})


def _named_file_task(
    state_id: str, module: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Wrap file module parameters in a consistently named task."""
    return {"name": f"Manage file: {state_id}", module: params}


def _build_managed_file_task(
    state_id: str, dest: Any, args: dict[str, Any]
) -> dict[str, Any]:
    """Build a Salt file.managed template task."""
    params: dict[str, Any] = {"dest": str(dest)}
    source = str(args.get("source", ""))
    if source.startswith(_SALT_URL_PREFIX):
        source = source[len(_SALT_URL_PREFIX) :]
    for prefix in (_SALT_TEMPLATES_PREFIX, _SALT_FILES_PREFIX):
        if source.startswith(prefix):
            source = source[len(prefix) :]
            break
    if source and ".." not in source:
        params["src"] = source
    _apply_file_ownership(params, args)
    return _named_file_task(state_id, _ANSIBLE_MODULE_MAP["file_managed"], params)


def _build_recurse_file_task(
    state_id: str, dest: Any, args: dict[str, Any]
) -> dict[str, Any]:
    """Build a Salt file.recurse copy task."""
    params: dict[str, Any] = {
        "dest": str(dest),
        "directory_mode": str(args.get("dir_mode", "0755")),
    }
    source = str(args.get("source", ""))
    if source.startswith(_SALT_URL_PREFIX):
        source = source[len(_SALT_URL_PREFIX) :]
    if source.startswith(_SALT_FILES_PREFIX):
        source = source[len(_SALT_FILES_PREFIX) :]
    if source and ".." not in source:
        params["src"] = source
    if args.get("file_mode"):
        params["mode"] = str(args["file_mode"])
    _apply_file_ownership(params, args)
    return _named_file_task(state_id, _MOD_COPY, params)


def _build_simple_file_task(
    func: str, state_id: str, dest: Any, args: dict[str, Any]
) -> dict[str, Any]:
    """Build directory, absent, or symlink state tasks."""
    params: dict[str, Any] = {"path": str(dest)}
    if func == "directory":
        params["state"] = "directory"
        _apply_file_ownership(params, args)
    elif func == "absent":
        params["state"] = "absent"
    else:
        params["src"] = str(args.get("target", ""))
        params["state"] = "link"
    return _named_file_task(state_id, _MOD_FILE, params)


def _build_line_file_task(
    func: str, state_id: str, dest: Any, args: dict[str, Any]
) -> dict[str, Any]:
    """Build line and block editing tasks for Salt file states."""
    if func in {"replace", "line"}:
        params = {
            "path": str(dest),
            "regexp": str(args.get("pattern", "")),
            "line": str(args.get("repl", "")),
        }
        return _named_file_task(state_id, _MOD_LINEINFILE, params)
    params = {
        "path": str(dest),
        "block": str(args.get("text", args.get("content", ""))),
    }
    return _named_file_task(state_id, _MOD_BLOCKINFILE, params)


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
        _MOD_SERVICE: params,
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

    ansible_module = "ansible.builtin.shell" if func == "script" else _MOD_COMMAND

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


def _build_pkgrepo_task(state: dict[str, Any]) -> dict[str, Any]:
    """Build an APT repository task from a Salt managed repository."""
    args = state.get("args", {})
    state_id = state.get("id", "repository")
    params: dict[str, Any] = {
        "repo": str(args.get("name", state_id)),
        "state": "present",
    }
    key_url = args.get("key_url")
    if key_url:
        params["key"] = str(key_url)
    return {
        "name": f"Manage package repository: {state_id}",
        "ansible.builtin.apt_repository": params,
    }


def _build_virtualenv_task(state: dict[str, Any]) -> dict[str, Any]:
    """Build an idempotent Python virtual environment creation task."""
    args = state.get("args", {})
    path = str(state.get("id", "venv"))
    python = str(args.get("python", "python3"))
    task: dict[str, Any] = {
        "name": f"Create Python virtual environment: {path}",
        _MOD_COMMAND: {
            "argv": [python, "-m", "venv", path],
            "creates": f"{path}/bin/activate",
        },
    }
    user = args.get("user")
    if user:
        task["become_user"] = str(user)
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


def _salt_manual_review_warnings(
    content: str, include_asset_warning: bool = True
) -> list[str]:
    """Report Salt constructs that are not preserved by conversion."""
    warnings: list[str] = []
    if re.search(r"(?m)^\s*include\s*:", content):
        warnings.append(
            "Salt include directives are not translated into role dependencies"
        )
    if re.search(r"(?m)^\s*-\s*(?:require|watch|require_in|watch_in)\s*:", content):
        warnings.append(
            "Salt requisites and watch relationships require manual ordering or handlers"
        )
    if re.search(r"{%\s*(?:if|elif|else|for)\b", content):
        warnings.append(
            "Salt Jinja conditionals or loops are not translated into Ansible task conditions"
        )
    if re.search(r"{%\s*set\b", content):
        warnings.append(
            "Salt Jinja set variables are removed; define equivalent Ansible variables"
        )
    if include_asset_warning and _SALT_URL_PREFIX in content:
        warnings.append(
            "Salt file and template assets are referenced but not copied into the Ansible role"
        )
    return warnings


def _copy_salt_role_assets(
    rel_paths: list[str],
    safe_salt: Any,
    role_dir: Any,
    workspace_root: Any,
    warnings: list[str],
) -> None:
    """Copy Salt file/template sources into their Ansible role directories."""
    references = _collect_salt_asset_references(
        rel_paths, safe_salt, workspace_root, warnings
    )
    for reference in sorted(references):
        _copy_salt_asset(reference, safe_salt, role_dir, workspace_root, warnings)


def _collect_salt_asset_references(
    rel_paths: list[str], safe_salt: Any, workspace_root: Any, warnings: list[str]
) -> set[str]:
    """Collect salt:// references from the role's source SLS files."""
    references: set[str] = set()
    for rel_path in rel_paths:
        try:
            content = safe_read_text(
                safe_salt / rel_path, workspace_root, encoding="utf-8"
            )
        except OSError as exc:
            warnings.append(f"Could not inspect assets in {rel_path}: {exc}")
            continue
        references.update(re.findall(r"salt://([^\s'\"]+)", content))
    return references


def _copy_salt_asset(
    reference: str,
    safe_salt: Any,
    role_dir: Any,
    workspace_root: Any,
    warnings: list[str],
) -> None:
    """Validate and stage one Salt asset reference."""
    asset_path = Path(reference)
    if asset_path.is_absolute() or ".." in asset_path.parts:
        warnings.append(f"Unsafe Salt asset path was not copied: {reference}")
        return

    asset_type = asset_path.parts[0] if asset_path.parts else ""
    if asset_type not in {"files", "templates"} or len(asset_path.parts) < 2:
        warnings.append(f"Unsupported Salt asset source was not copied: {reference}")
        return

    source = _find_salt_asset_source(asset_path, safe_salt)
    if source is None:
        warnings.append(f"Salt asset source was not found: {reference}")
        return

    try:
        safe_source = _ensure_within_base_path(source, workspace_root)
        source_rel = Path(*asset_path.parts[1:])
        destination_root = role_dir / asset_type
        _copy_salt_asset_files(
            safe_source,
            source_rel,
            destination_root,
            workspace_root,
        )
    except (OSError, ValueError) as exc:
        warnings.append(f"Could not copy Salt asset {reference}: {exc}")


def _find_salt_asset_source(asset_path: Path, safe_salt: Any) -> Path | None:
    """Find an asset under the Salt root or its sibling assets directory."""
    candidates = (safe_salt / asset_path, safe_salt.parent / asset_path)
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _copy_salt_asset_files(
    safe_source: Path,
    source_rel: Path,
    destination_root: Any,
    workspace_root: Any,
) -> None:
    """Copy one file or a directory tree under a role's asset root."""
    safe_mkdir(destination_root, workspace_root, parents=True, exist_ok=True)
    source_files = (
        [safe_source]
        if safe_source.is_file()
        else sorted(path for path in safe_source.rglob("*") if path.is_file())
    )
    for source_file in source_files:
        safe_file = _ensure_within_base_path(source_file, workspace_root)
        relative_file = (
            Path(source_file.name)
            if safe_source.is_file()
            else source_file.relative_to(safe_source)
        )
        destination_rel = (
            source_rel if safe_source.is_file() else source_rel / relative_file
        )
        destination = destination_root / destination_rel
        safe_destination = _ensure_within_base_path(destination, workspace_root)
        safe_mkdir(safe_destination.parent, workspace_root, parents=True, exist_ok=True)
        safe_destination.write_bytes(safe_file.read_bytes())


def _order_roles_from_top(
    roles_created: list[str],
    safe_salt: Any,
    workspace_root: Any,
    warnings: list[str],
    parse_sls_yaml: Any,
    parse_top_environments: Any,
) -> list[str]:
    """Order generated roles using state order declared in top.sls."""
    top_file = safe_salt / _TOP_SLS
    if not safe_exists(top_file, workspace_root):
        return roles_created

    try:
        content = safe_read_text(top_file, workspace_root, encoding="utf-8")
        environments = parse_top_environments(parse_sls_yaml(content))
    except (OSError, ValueError) as exc:
        warnings.append(f"Could not order roles from top.sls: {exc}")
        return roles_created

    ordered: list[str] = []
    for targets in environments.values():
        for state_names in targets.values():
            for state_name in state_names:
                role_name = state_name.split(".", 1)[0].split("/", 1)[0]
                if role_name in roles_created and role_name not in ordered:
                    ordered.append(role_name)
    ordered.extend(role for role in roles_created if role not in ordered)
    return ordered


_TASK_BUILDERS = {
    "pkg": _build_pkg_task,
    "file": _build_file_task,
    "service": _build_service_task,
    "cmd": _build_cmd_task,
    "user": _build_user_task,
    "group": _build_group_task,
    "git": _build_git_task,
    "pip": _build_pip_task,
    "pkgrepo": _build_pkgrepo_task,
    "virtualenv": _build_virtualenv_task,
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

        if not safe_exists(safe_path, workspace_root):
            return json.dumps({"error": ERROR_FILE_NOT_FOUND.format(path=safe_path)})
        if safe_is_dir(safe_path, workspace_root):
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
    warnings.extend(_salt_manual_review_warnings(content))

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


def _render_var_line(var_name: str, var_value: Any) -> str:
    """
    Render a single Ansible variable definition as a YAML line.

    Args:
        var_name: Variable name.
        var_value: Variable value.

    Returns:
        YAML line string.

    """
    if var_value is None:
        return f"    {var_name}: null"
    if isinstance(var_value, str) and "{{" in var_value:
        return f"    {var_name}: {var_value}"
    if isinstance(var_value, str):
        return f"    {var_name}: '{var_value}'"
    return f"    {var_name}: {var_value}"


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
    play: dict[str, Any] = {
        "name": f"Converted from Salt: {name}",
        "hosts": "all",
        "become": True,
    }
    if ansible_vars:
        play["vars"] = ansible_vars
    if tasks:
        play["tasks"] = _normalise_task_metadata(tasks)

    return "---\n" + yaml.safe_dump(
        [play], default_flow_style=False, sort_keys=False, allow_unicode=True
    )


def _normalise_task_metadata(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalise scalar task tags to Ansible's list form."""
    normalised: list[dict[str, Any]] = []
    for task in tasks:
        normalised_task = dict(task)
        tags = normalised_task.get("tags")
        if tags and not isinstance(tags, list):
            normalised_task["tags"] = [tags]
        normalised.append(normalised_task)
    return normalised


def _render_role_task_list(tasks: list[dict[str, Any]]) -> str:
    """Render task mappings as a valid Ansible role task file."""
    return "---\n" + yaml.safe_dump(
        tasks, default_flow_style=False, sort_keys=False, allow_unicode=True
    )


def _render_param_value(lines: list[str], pk: str, pv: Any) -> None:
    """
    Render a single task parameter key-value pair as YAML lines.

    Args:
        lines: Output line list to append to.
        pk: Parameter key name.
        pv: Parameter value.

    """
    match pv:
        case list():
            lines.append(f"        {pk}:")
            for item in pv:
                lines.append(f"          - {item}")
        case None:
            lines.append(f"        {pk}:")
        case bool():
            lines.append(f"        {pk}: {str(pv).lower()}")
        case int() | float():
            lines.append(f"        {pk}: {pv}")
        case _:
            lines.append(f"        {pk}: {pv}")


def _render_task_body(lines: list[str], task: dict[str, Any]) -> None:
    """Render task module body lines excluding task metadata keys."""
    for key, val in task.items():
        if key in ("name", "when", "tags"):
            continue
        if isinstance(val, dict):
            lines.append(f"      {key}:")
            for pk, pv in val.items():
                _render_param_value(lines, pk, pv)
        else:
            lines.append(f"      {key}: {val}")


def _render_task_metadata(lines: list[str], task: dict[str, Any]) -> None:
    """Render optional task metadata fields such as when/tags."""
    when = task.get("when")
    if when:
        lines.append(f"      when: {when}")

    tags = task.get("tags")
    if not tags:
        return
    if isinstance(tags, list):
        lines.append("      tags:")
        for tag in tags:
            lines.append(f"        - {tag}")
        return
    lines.append(f"      tags: [{tags}]")


def _render_task_lines(lines: list[str], task: dict[str, Any]) -> None:
    """
    Render a single Ansible task as YAML lines.

    Args:
        lines: Output line list to append to.
        task: Ansible task dict.

    """
    task_name = task.get("name", "Unnamed task")
    lines.append(f"    - name: {task_name}")
    _render_task_body(lines, task)
    _render_task_metadata(lines, task)


def _extract_group_name_from_grain(target: str) -> str | None:
    """Extract normalised group name from a grain target expression."""
    if not target.startswith("G@"):
        return None
    grain_expr = target[2:]
    if ":" not in grain_expr:
        return None
    key, val = grain_expr.split(":", 1)
    return f"{key}_{val}".replace("-", "_").replace(".", "_")


def _append_inventory_target_lines(lines: list[str], targets: dict[str, Any]) -> None:
    """Append inventory target lines for a single top.sls environment."""
    for target in targets:
        group_name = _extract_group_name_from_grain(target)
        if group_name is not None:
            lines.append(f"# grain target: {target}")
            lines.append(f"# group: [{group_name}]")
            continue
        if target.startswith("G@"):
            lines.append(f"# grain target: {target}")
            continue
        if "*" in target or "?" in target:
            lines.append(f"# glob target: {target}")
            continue
        lines.append(target)


def _append_inventory_grain_groups(lines: list[str], targets: dict[str, Any]) -> None:
    """Append inventory group stubs derived from grain target expressions."""
    for target in targets:
        group_name = _extract_group_name_from_grain(target)
        if group_name is None:
            continue
        lines.append(f"[{group_name}]")
        lines.append(f"# Add hosts matching grain {target} here")
        lines.append("")


def _extract_watch_handlers(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extract Ansible handlers from Salt service watch/listen states.

    Translates Salt's watch/listen dependency mechanism to Ansible
    notify/handlers pattern. Any service state becomes a potential handler.

    Args:
        states: List of Salt state dicts.

    Returns:
        List of Ansible handler dicts with name and service module params.

    """
    handlers: list[dict[str, Any]] = []
    seen: set[str] = set()

    for state in states:
        if state.get("module") != "service":
            continue
        args = state.get("args", {})
        state_id = state.get("id", "service")
        service_name = args.get("name", state_id)
        handler_name = f"Restart {service_name}"
        if handler_name in seen:
            continue
        seen.add(handler_name)
        handlers.append(
            {
                "name": handler_name,
                _MOD_SERVICE: {
                    "name": str(service_name),
                    "state": "restarted",
                },
            }
        )

    return handlers


def _top_to_ansible_inventory(top_data: dict[str, Any]) -> str:
    """
    Convert parsed top.sls data to Ansible INI inventory format.

    Maps Salt targeting patterns to Ansible inventory groups. Each Salt
    environment becomes an ``[env_<name>]`` group header. Grain-based targets
    (``G@key:value``) are mapped to ``[<key>_<value>]`` groups.

    Args:
        top_data: Parsed top.sls dict from ``parse_salt_top`` (JSON parsed).
            Has an ``"environments"`` key with env -> target -> states mapping.

    Returns:
        Ansible INI inventory string.

    """
    environments = top_data.get("environments", {})
    lines: list[str] = ["# Ansible inventory generated from SaltStack top.sls", ""]

    for env_name, targets in environments.items():
        if not isinstance(targets, dict):
            continue
        lines.append(f"[env_{env_name}]")
        _append_inventory_target_lines(lines, targets)
        lines.append("")
        _append_inventory_grain_groups(lines, targets)

    return "\n".join(lines)


def top_to_ansible_inventory(top_data: dict[str, Any]) -> str:
    """Public wrapper to convert Salt top data to an Ansible inventory."""
    return _top_to_ansible_inventory(top_data)


def _render_nested_yaml_value(val: Any, indent: int) -> list[str]:
    """
    Render a nested dict value as YAML lines with given indentation.

    Args:
        val: Value to render (expected to be a dict).
        indent: Indentation level in spaces.

    Returns:
        List of YAML lines.

    """
    pad = " " * indent
    rendered: list[str] = []
    if not isinstance(val, dict):
        return rendered
    for k, v in val.items():
        if isinstance(v, dict):
            rendered.append(f"{pad}{k}:")
            rendered.extend(_render_nested_yaml_value(v, indent + 2))
        elif isinstance(v, list):
            rendered.append(f"{pad}{k}:")
            for item in v:
                rendered.append(f"{pad}  - {item}")
        elif isinstance(v, bool):
            rendered.append(f"{pad}{k}: {str(v).lower()}")
        elif v is None:
            rendered.append(f"{pad}{k}:")
        elif isinstance(v, (int, float)):
            rendered.append(f"{pad}{k}: {v}")
        else:
            rendered.append(f"{pad}{k}: '{v}'")
    return rendered


def _render_pillar_var_line(var_name: str, value: Any, lines: list[str]) -> None:
    """
    Append the YAML representation of a pillar variable to ``lines``.

    Args:
        var_name: Ansible variable name (may include a prefix).
        value: Pillar value to render.
        lines: Output line list to append to.

    """
    if isinstance(value, dict):
        lines.append(f"{var_name}:")
        lines.extend(_render_nested_yaml_value(value, 2))
    elif isinstance(value, list):
        lines.append(f"{var_name}:")
        for item in value:
            lines.append(f"  - {item}")
    elif isinstance(value, bool):
        lines.append(f"{var_name}: {str(value).lower()}")
    elif value is None:
        lines.append(f"{var_name}:")
    elif isinstance(value, (int, float)):
        lines.append(f"{var_name}: {value}")
    else:
        lines.append(f"{var_name}: '{value}'")


def _pillar_to_vault_vars(pillar_vars: dict[str, Any], prefix: str = "") -> str:
    """
    Convert pillar variable dict to Ansible vars file YAML.

    Produces an Ansible vars file with all pillar keys available as Ansible
    variables. Nested dicts are preserved. Adds a comment header explaining
    this was converted from Salt pillars.

    Args:
        pillar_vars: Dict of pillar variables (may be nested).
        prefix: Optional variable name prefix.

    Returns:
        YAML string suitable for use as an Ansible vars_file or group_vars file.

    """
    lines: list[str] = [
        "---",
        "# Converted from SaltStack pillar",
        "# Review and encrypt sensitive values with ansible-vault",
        "",
    ]

    for key, value in pillar_vars.items():
        var_name = f"{prefix}_{key}" if prefix else key
        _render_pillar_var_line(var_name, value, lines)

    return "\n".join(lines) + "\n"


def convert_salt_pillar_to_vars(pillar_path: str, output_format: str = "yaml") -> str:
    """
    Convert a SaltStack pillar file to Ansible variable definitions.

    Transforms Salt pillar data into Ansible vars files suitable for use as
    group_vars, host_vars, or Ansible Vault-encrypted variable files.

    Args:
        pillar_path: Path to pillar SLS file.
        output_format: ``"yaml"`` for plain vars file, ``"vault"`` for
            vault-annotated format.

    Returns:
        JSON string with ``"vars_file"`` (YAML content), ``"variable_count"``,
        and ``"format"``.

    """
    try:
        normalized_path = _normalize_path(pillar_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_exists(safe_path, workspace_root):
            return json.dumps({"error": ERROR_FILE_NOT_FOUND.format(path=safe_path)})
        if safe_is_dir(safe_path, workspace_root):
            return json.dumps({"error": ERROR_IS_DIRECTORY.format(path=safe_path)})

        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

    except PermissionError:
        return json.dumps({"error": ERROR_PERMISSION_DENIED.format(path=pillar_path)})
    except ValueError as e:
        return json.dumps({"error": str(e)})

    from souschef.parsers.salt import _parse_sls_yaml

    data = _parse_sls_yaml(content)

    vars_yaml = _pillar_to_vault_vars(data, prefix="")

    if output_format == "vault":
        # Add vault annotation hints
        vault_lines = [
            "---",
            "# Ansible Vault annotated vars file",
            "# Run: ansible-vault encrypt_string '<value>' --name '<key>'",
            "",
        ]
        for line in vars_yaml.splitlines()[4:]:
            vault_lines.append(line)
        vars_yaml = "\n".join(vault_lines) + "\n"

    result: dict[str, Any] = {
        "vars_file": vars_yaml,
        "variable_count": len(data),
        "format": output_format,
    }
    return json.dumps(result, indent=2)


def _collect_role_data(
    rel_paths: list[str],
    safe_salt: Any,
    workspace_root: Any,
    warnings: list[str],
    parse_sls_states: Any,
    extract_pillars: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """
    Collect all tasks, handlers and defaults for a single Ansible role.

    Reads each SLS file belonging to the role, converts states to tasks,
    extracts handlers, and accumulates pillar-derived defaults.

    Args:
        rel_paths: List of SLS file paths relative to ``safe_salt``.
        safe_salt: Validated, absolute Path to the Salt states root.
        workspace_root: Workspace root Path for path-safety checks.
        warnings: Mutable list to append warning messages to.
        parse_sls_states: Callable that parses SLS content into state dicts.
        extract_pillars: Callable that extracts pillar references from content.

    Returns:
        Tuple of ``(all_tasks, all_handlers, all_defaults)``.

    """
    all_tasks: list[dict[str, Any]] = []
    all_handlers: list[dict[str, Any]] = []
    all_defaults: dict[str, Any] = {}

    for rel_path in rel_paths:
        file_path = safe_salt / rel_path
        try:
            content = safe_read_text(file_path, workspace_root, encoding="utf-8")
        except OSError as exc:
            warnings.append(f"Could not read {rel_path}: {exc}")
            continue

        states = parse_sls_states(content)
        warnings.extend(
            _salt_manual_review_warnings(content, include_asset_warning=False)
        )
        handlers = _extract_watch_handlers(states)
        pillars = extract_pillars(content)

        for state in states:
            all_tasks.append(_convert_state_to_task(state))

        all_handlers.extend(handlers)

        for key in pillars:
            var_name = key.replace(".", "_").replace("-", "_").replace(":", "_")
            if var_name not in all_defaults:
                all_defaults[var_name] = f"{{{{ {var_name} | default('') }}}}"

    return all_tasks, all_handlers, all_defaults


def _write_role_files(
    role_name: str,
    role_dir: Any,
    safe_out: Any,
    workspace_root: Any,
    all_tasks: list[dict[str, Any]],
    all_handlers: list[dict[str, Any]],
    all_defaults: dict[str, Any],
    files_written: list[str],
    warnings: list[str],
) -> list[str] | None:
    """
    Write all files for a single Ansible role to the output directory.

    Creates the ``tasks/``, ``handlers/``, ``defaults/``, and ``meta/``
    subdirectories and their ``main.yml`` files.

    Args:
        role_name: Name of the role.
        role_dir: Absolute Path to the role directory.
        safe_out: Absolute Path to the output root.
        workspace_root: Workspace root Path for path-safety checks.
        all_tasks: List of Ansible task dicts.
        all_handlers: List of Ansible handler dicts.
        all_defaults: Dict of default variable definitions.
        files_written: Mutable list to append written file paths to.
        warnings: Mutable list to append warning messages to.

    Returns:
        List of four relative path strings (tasks, handlers, defaults, meta)
        if successful, or ``None`` if the role directories could not be created.

    """
    try:
        role_tasks_dir = role_dir / "tasks"
        safe_mkdir(role_tasks_dir, workspace_root, parents=True, exist_ok=True)
        role_handlers_dir = role_dir / "handlers"
        safe_mkdir(role_handlers_dir, workspace_root, parents=True, exist_ok=True)
        role_defaults_dir = role_dir / "defaults"
        safe_mkdir(role_defaults_dir, workspace_root, parents=True, exist_ok=True)
        role_meta_dir = role_dir / "meta"
        safe_mkdir(role_meta_dir, workspace_root, parents=True, exist_ok=True)
    except PermissionError as exc:
        warnings.append(f"Cannot create role directory for {role_name}: {exc}")
        return None

    tasks_file = role_tasks_dir / _MAIN_YML
    safe_write_text(
        tasks_file,
        workspace_root,
        _render_role_task_list(all_tasks),
        encoding="utf-8",
    )
    tasks_rel = str(tasks_file.relative_to(safe_out))
    files_written.append(tasks_rel)

    handlers_file = role_handlers_dir / _MAIN_YML
    handlers_yaml = _render_role_task_list(all_handlers)
    safe_write_text(handlers_file, workspace_root, handlers_yaml, encoding="utf-8")
    handlers_rel = str(handlers_file.relative_to(safe_out))
    files_written.append(handlers_rel)

    defaults_file = role_defaults_dir / _MAIN_YML
    safe_write_text(
        defaults_file,
        workspace_root,
        _pillar_to_vault_vars(all_defaults),
        encoding="utf-8",
    )
    defaults_rel = str(defaults_file.relative_to(safe_out))
    files_written.append(defaults_rel)

    meta_file = role_meta_dir / _MAIN_YML
    meta_content = (
        "---\ngalaxy_info:\n"
        f"  role_name: {role_name}\n"
        "  author: souschef\n"
        "  description: Converted from SaltStack\n"
        "  min_ansible_version: '2.9'\n"
        "dependencies: []\n"
    )
    safe_write_text(meta_file, workspace_root, meta_content, encoding="utf-8")
    meta_rel = str(meta_file.relative_to(safe_out))
    files_written.append(meta_rel)

    return [tasks_rel, handlers_rel, defaults_rel, meta_rel]


def _write_site_yml(
    safe_out: Any,
    workspace_root: Any,
    roles_created: list[str],
    files_written: list[str],
    warnings: list[str],
) -> None:
    """
    Write the ``site.yml`` master playbook for all converted roles.

    Args:
        safe_out: Absolute Path to the output root.
        workspace_root: Workspace root Path for path-safety checks.
        roles_created: List of role names to include in the playbook.
        files_written: Mutable list to append written file paths to.
        warnings: Mutable list to append warning messages to.

    """
    site_lines = ["---"]
    for role_name in roles_created:
        site_lines.extend(
            [
                f"- name: Apply {role_name} role",
                "  hosts: all",
                "  become: true",
                "  roles:",
                f"    - {role_name}",
            ]
        )
    try:
        safe_mkdir(safe_out, workspace_root, parents=True, exist_ok=True)
        safe_write_text(
            safe_out / "site.yml",
            workspace_root,
            "\n".join(site_lines) + "\n",
            encoding="utf-8",
        )
        files_written.append("site.yml")
    except PermissionError as exc:
        warnings.append(f"Could not write site.yml: {exc}")


def _write_inventory_from_top(
    safe_salt: Any,
    safe_out: Any,
    workspace_root: Any,
    files_written: list[str],
    warnings: list[str],
    parse_sls_yaml: Any,
    parse_top_environments: Any,
) -> None:
    """
    Generate ``inventory/hosts`` from ``top.sls`` if it exists.

    Args:
        safe_salt: Absolute Path to the Salt states root.
        safe_out: Absolute Path to the output root.
        workspace_root: Workspace root Path for path-safety checks.
        files_written: Mutable list to append written file paths to.
        warnings: Mutable list to append warning messages to.
        parse_sls_yaml: Callable that parses SLS YAML content.
        parse_top_environments: Callable that extracts environments from top data.

    """
    candidate = safe_salt / _TOP_SLS
    if not safe_exists(candidate, workspace_root):
        return
    try:
        top_content = safe_read_text(candidate, workspace_root, encoding="utf-8")
        top_data = parse_sls_yaml(top_content)
        environments = parse_top_environments(top_data)
        inventory_str = _top_to_ansible_inventory({"environments": environments})
        inv_dir = safe_out / "inventory"
        safe_mkdir(inv_dir, workspace_root, parents=True, exist_ok=True)
        safe_write_text(
            inv_dir / "hosts", workspace_root, inventory_str, encoding="utf-8"
        )
        files_written.append("inventory/hosts")
    except OSError as exc:
        warnings.append(f"Could not generate inventory: {exc}")


def convert_salt_directory_to_roles(salt_dir: str, output_dir: str) -> str:
    """
    Convert an entire Salt states directory to Ansible roles structure.

    Creates one Ansible role per top-level SLS module. Each role gets:

    - ``roles/<rolename>/tasks/main.yml`` - converted tasks
    - ``roles/<rolename>/handlers/main.yml`` - watch/listen handlers
    - ``roles/<rolename>/defaults/main.yml`` - pillar-derived defaults
    - ``roles/<rolename>/meta/main.yml`` - metadata

    Also generates:

    - ``site.yml`` - master playbook importing all roles
    - ``inventory/hosts`` - inventory from top.sls if present

    Args:
        salt_dir: Path to the Salt states root directory.
        output_dir: Path where Ansible roles should be written.

    Returns:
        JSON string with ``"roles_created"``, ``"files_written"``,
        ``"warnings"``, and ``"structure"``.

    """
    from souschef.core.constants import ERROR_PERMISSION_DENIED
    from souschef.parsers.salt import (
        _extract_pillars,
        _list_sls_files,
        _parse_sls_states,
        _parse_sls_yaml,
        _parse_top_environments,
    )

    try:
        normalized_salt = _normalize_path(salt_dir)
        workspace_root = _get_workspace_root()
        safe_salt = _ensure_within_base_path(normalized_salt, workspace_root)

        if not safe_exists(safe_salt, workspace_root):
            return json.dumps({"error": f"Salt directory not found: {salt_dir}"})
        if not safe_is_dir(safe_salt, workspace_root):
            return json.dumps({"error": f"Path is not a directory: {salt_dir}"})

        normalized_out = _normalize_path(output_dir)
        safe_out = _ensure_within_base_path(normalized_out, workspace_root)

    except PermissionError:
        return json.dumps({"error": ERROR_PERMISSION_DENIED.format(path=salt_dir)})
    except ValueError as e:
        return json.dumps({"error": str(e)})

    roles_created: list[str] = []
    files_written: list[str] = []
    warnings: list[str] = []
    structure: dict[str, list[str]] = {}

    sls_files = _list_sls_files(safe_salt, workspace_root)

    # Group files by top-level directory (role name)
    role_files: dict[str, list[str]] = {}
    for rel_path in sls_files:
        if rel_path == _TOP_SLS:
            continue
        parts = rel_path.split("/")
        role_name = parts[0].replace(".sls", "") if len(parts) == 1 else parts[0]
        role_files.setdefault(role_name, []).append(rel_path)

    for role_name, rel_paths in role_files.items():
        all_tasks, all_handlers, all_defaults = _collect_role_data(
            rel_paths,
            safe_salt,
            workspace_root,
            warnings,
            _parse_sls_states,
            _extract_pillars,
        )
        role_dir = safe_out / "roles" / role_name
        file_rels = _write_role_files(
            role_name,
            role_dir,
            safe_out,
            workspace_root,
            all_tasks,
            all_handlers,
            all_defaults,
            files_written,
            warnings,
        )
        if file_rels is not None:
            _copy_salt_role_assets(
                rel_paths,
                safe_salt,
                role_dir,
                workspace_root,
                warnings,
            )
            roles_created.append(role_name)
            structure[role_name] = file_rels

    roles_created[:] = _order_roles_from_top(
        roles_created,
        safe_salt,
        workspace_root,
        warnings,
        _parse_sls_yaml,
        _parse_top_environments,
    )
    _write_site_yml(safe_out, workspace_root, roles_created, files_written, warnings)
    _write_inventory_from_top(
        safe_salt,
        safe_out,
        workspace_root,
        files_written,
        warnings,
        _parse_sls_yaml,
        _parse_top_environments,
    )

    return json.dumps(
        {
            "roles_created": roles_created,
            "files_written": files_written,
            "warnings": warnings,
            "structure": structure,
        },
        indent=2,
    )
