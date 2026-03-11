"""
Puppet to Ansible converter.

Converts parsed Puppet resources into Ansible task YAML, producing
playbooks from Puppet manifests and module directories.

Resource mapping:

- ``package`` → ``ansible.builtin.package``
- ``service`` → ``ansible.builtin.service``
- ``file`` → ``ansible.builtin.file`` / ``ansible.builtin.copy``
  / ``ansible.builtin.template``
- ``user`` → ``ansible.builtin.user``
- ``group`` → ``ansible.builtin.group``
- ``exec`` → ``ansible.builtin.command`` (with idempotency warnings)
- ``cron`` → ``ansible.builtin.cron``
- ``host`` → ``ansible.builtin.lineinfile`` (with warning)
- ``mount`` → ``ansible.posix.mount``
- Others → ``ansible.builtin.debug`` warning task
"""

import re
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
from souschef.parsers.puppet import (
    _parse_manifest_content,
)

# Maximum content length for safe processing
MAX_CONTENT_LENGTH = 2_000_000

# Mapping from Puppet ensure values to Ansible state values
ENSURE_TO_STATE: dict[str, str] = {
    "present": "present",
    "absent": "absent",
    "installed": "present",
    "latest": "latest",
    "purged": "absent",
    "running": "started",
    "stopped": "stopped",
    "enabled": "started",
    "disabled": "stopped",
    "directory": "directory",
    "link": "link",
    "file": "file",
}

# Puppet resource type → Ansible module mapping
RESOURCE_MODULE_MAP: dict[str, str] = {
    "package": "ansible.builtin.package",
    "service": "ansible.builtin.service",
    "file": "ansible.builtin.file",
    "user": "ansible.builtin.user",
    "group": "ansible.builtin.group",
    "exec": "ansible.builtin.command",
    "cron": "ansible.builtin.cron",
    "host": "ansible.builtin.lineinfile",
    "mount": "ansible.posix.mount",
    "ssh_authorized_key": "ansible.posix.authorized_key",
}

# Puppet file attributes → Ansible file module parameters
FILE_ATTR_MAP: dict[str, str] = {
    "owner": "owner",
    "group": "group",
    "mode": "mode",
}

# Puppet user attributes → Ansible user module parameters
USER_ATTR_MAP: dict[str, str] = {
    "uid": "uid",
    "gid": "group",
    "home": "home",
    "shell": "shell",
    "comment": "comment",
    "password": "password",
    "groups": "groups",
    "managehome": "create_home",
}

# Puppet cron attributes → Ansible cron module parameters
CRON_ATTR_MAP: dict[str, str] = {
    "command": "job",
    "hour": "hour",
    "minute": "minute",
    "weekday": "weekday",
    "month": "month",
    "monthday": "day",
    "user": "user",
}


def convert_puppet_manifest_to_ansible(manifest_path: str) -> str:
    """
    Convert a Puppet manifest file to an Ansible playbook.

    Parses the Puppet manifest at ``manifest_path`` and generates a
    corresponding Ansible playbook with tasks mapped from Puppet resources.
    Unsupported constructs are included as ``debug`` warning tasks.

    Args:
        manifest_path: Path to the Puppet manifest (``.pp``) file.

    Returns:
        Ansible playbook in YAML format as a string, or an error message
        if the file cannot be read or converted.

    """
    try:
        file_path = _normalize_path(manifest_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(file_path, workspace_root)
        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        if len(content) > MAX_CONTENT_LENGTH:
            return f"Error: Manifest too large to convert safely ({len(content)} bytes)"

        parsed = _parse_manifest_content(content, manifest_path)
        return _generate_puppet_playbook(parsed, manifest_path)

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=manifest_path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=manifest_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=manifest_path)
    except Exception as e:
        return f"An error occurred: {e}"


def convert_puppet_module_to_ansible(module_path: str) -> str:
    """
    Convert a Puppet module directory to a collection of Ansible playbooks.

    Recursively processes all ``.pp`` files in the module directory and
    generates a combined Ansible playbook.

    Args:
        module_path: Path to the Puppet module directory.

    Returns:
        Combined Ansible playbook in YAML format, or an error message.

    """
    try:
        dir_path = _normalize_path(module_path)
        workspace_root = _get_workspace_root()
        safe_dir = _ensure_within_base_path(dir_path, workspace_root)

        if not safe_dir.exists():  # NOSONAR
            return ERROR_FILE_NOT_FOUND.format(path=module_path)
        if not safe_dir.is_dir():
            return ERROR_IS_DIRECTORY.format(path=module_path)

        manifests = sorted(safe_dir.rglob("*.pp"))
        if not manifests:
            return f"Warning: No Puppet manifests (.pp files) found in {module_path}"

        all_resources: list[dict[str, Any]] = []
        all_unsupported: list[dict[str, Any]] = []

        for manifest_path in manifests:
            try:
                content = safe_read_text(
                    manifest_path, workspace_root, encoding="utf-8"
                )
                rel_path = str(manifest_path.relative_to(workspace_root))
                parsed = _parse_manifest_content(content, rel_path)
                all_resources.extend(parsed.get("resources", []))
                all_unsupported.extend(parsed.get("unsupported", []))
            except (OSError, ValueError):
                continue

        combined: dict[str, Any] = {
            "resources": all_resources,
            "classes": [],
            "variables": [],
            "unsupported": all_unsupported,
        }
        return _generate_puppet_playbook(combined, module_path)

    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return ERROR_FILE_NOT_FOUND.format(path=module_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=module_path)
    except Exception as e:
        return f"An error occurred: {e}"


# Dispatch table for resource type converters
_RESOURCE_CONVERTERS = {
    "package": lambda title, attrs: _convert_package(title, attrs),
    "service": lambda title, attrs: _convert_service(title, attrs),
    "file": lambda title, attrs: _convert_file(title, attrs),
    "user": lambda title, attrs: _convert_user(title, attrs),
    "group": lambda title, attrs: _convert_group(title, attrs),
    "exec": lambda title, attrs: _convert_exec(title, attrs),
    "cron": lambda title, attrs: _convert_cron(title, attrs),
    "host": lambda title, attrs: _convert_host(title, attrs),
    "mount": lambda title, attrs: _convert_mount(title, attrs),
    "ssh_authorized_key": lambda title, attrs: _convert_ssh_authorized_key(
        title, attrs
    ),
}


def convert_puppet_resource_to_task(
    resource_type: str,
    title: str,
    attributes: dict[str, str],
) -> dict[str, Any]:
    """
    Convert a single Puppet resource to an Ansible task dictionary.

    Args:
        resource_type: Puppet resource type (e.g. ``'package'``, ``'service'``).
        title: Resource title / name (e.g. ``'nginx'``).
        attributes: Resource attributes dict (e.g. ``{'ensure': 'installed'}``).

    Returns:
        Ansible task dictionary ready for YAML serialisation.

    """
    rtype = resource_type.lower()
    converter = _RESOURCE_CONVERTERS.get(rtype)
    if converter is not None:
        return converter(title, attributes)
    # Fallback: unsupported resource type
    return _convert_unsupported(resource_type, title)


def _generate_puppet_playbook(parsed: dict[str, Any], source: str) -> str:
    """
    Generate an Ansible playbook YAML string from parsed manifest data.

    Args:
        parsed: Parsed manifest dictionary with resources and unsupported constructs.
        source: Source path used for the playbook name.

    Returns:
        Ansible playbook YAML string.

    """
    tasks = []
    resources = parsed.get("resources", [])
    unsupported = parsed.get("unsupported", [])

    for resource in resources:
        task = convert_puppet_resource_to_task(
            resource["type"],
            resource["title"],
            resource.get("attributes", {}),
        )
        tasks.append(task)

    # Add warning tasks for unsupported constructs
    for item in unsupported:
        loc = f"{item['source_file']}:{item['line']}"
        tasks.append(
            {
                "name": (
                    f"WARNING: Unsupported construct '{item['construct']}'"
                    f" at {loc}"
                ),
                "ansible.builtin.debug": {
                    "msg": (
                        f"Manual migration required: {item['construct']} "
                        f"— {item['text']!r}"
                    ),
                },
            }
        )

    play_name = _source_to_play_name(source)
    play: dict[str, Any] = {
        "name": play_name,
        "hosts": "all",
        "become": True,
        "tasks": tasks if tasks else [],
    }

    if not tasks:
        play["tasks"] = [
            {
                "name": "No convertible resources found",
                "ansible.builtin.debug": {
                    "msg": f"No Puppet resources were found in {source}"
                },
            }
        ]

    playbook = [play]
    result: str = yaml.dump(
        playbook, default_flow_style=False, sort_keys=False, allow_unicode=True
    )
    return result


def _source_to_play_name(source: str) -> str:
    """
    Generate a human-readable play name from the source file path.

    Args:
        source: Source file or directory path.

    Returns:
        Play name string.

    """
    stem = re.sub(r"[^\w\s\-]", " ", source).strip()
    stem = re.sub(r"\s+", " ", stem)
    return f"Converted from Puppet: {stem}"


def _map_ensure(ensure: str) -> str:
    """
    Map a Puppet ``ensure`` value to the corresponding Ansible state.

    Args:
        ensure: Puppet ensure attribute value.

    Returns:
        Ansible state string.

    """
    return ENSURE_TO_STATE.get(ensure.lower(), ensure)


def _convert_package(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``package`` resource to an Ansible package task.

    Args:
        title: Package name.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "present")
    state = _map_ensure(ensure)
    task: dict[str, Any] = {
        "name": f"Manage package: {title}",
        "ansible.builtin.package": {
            "name": title,
            "state": state,
        },
    }
    return task


def _convert_service(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``service`` resource to an Ansible service task.

    Args:
        title: Service name.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "running")
    enable = attrs.get("enable", "")
    state = _map_ensure(ensure)

    params: dict[str, Any] = {
        "name": title,
        "state": state,
    }
    if enable:
        params["enabled"] = enable.lower() in ("true", "yes", "1")

    return {
        "name": f"Manage service: {title}",
        "ansible.builtin.service": params,
    }


def _convert_file(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``file`` resource to an Ansible file/copy/template task.

    Selects the appropriate Ansible module based on resource attributes:
    - ``source`` → ``ansible.builtin.copy``
    - ``content`` containing ERB → ``ansible.builtin.template`` (with warning)
    - ``content`` plain → ``ansible.builtin.copy``
    - Otherwise → ``ansible.builtin.file``

    Args:
        title: File path.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "file")
    state = _map_ensure(ensure)

    # Build common file params
    file_params: dict[str, Any] = {"path": title}
    for puppet_key, ansible_key in FILE_ATTR_MAP.items():
        if puppet_key in attrs:
            file_params[ansible_key] = attrs[puppet_key]

    # Determine module based on attributes
    if "source" in attrs:
        file_params["src"] = attrs["source"]
        file_params.pop("path", None)
        file_params["dest"] = title
        return {
            "name": f"Copy file: {title}",
            "ansible.builtin.copy": file_params,
        }

    if "content" in attrs:
        content_val = attrs["content"]
        if "<%=" in content_val or "<%" in content_val:
            # ERB template — map to ansible template with a warning
            file_params["src"] = f"{title}.j2"
            file_params["dest"] = title
            file_params.pop("path", None)
            file_params["_puppet_note"] = "Convert ERB template to Jinja2 manually"
            return {
                "name": f"Template file (convert ERB to Jinja2): {title}",
                "ansible.builtin.template": file_params,
            }
        file_params["content"] = content_val
        file_params["dest"] = title
        file_params.pop("path", None)
        return {
            "name": f"Write file content: {title}",
            "ansible.builtin.copy": file_params,
        }

    # No source/content — manage file/directory state
    file_params["state"] = state
    return {
        "name": f"Manage file: {title}",
        "ansible.builtin.file": file_params,
    }


def _convert_user(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``user`` resource to an Ansible user task.

    Args:
        title: User name.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "present")
    state = _map_ensure(ensure)

    params: dict[str, Any] = {"name": title, "state": state}
    for puppet_key, ansible_key in USER_ATTR_MAP.items():
        if puppet_key in attrs:
            val = attrs[puppet_key]
            if puppet_key == "managehome":
                params[ansible_key] = val.lower() in ("true", "yes", "1")
            else:
                params[ansible_key] = val

    return {
        "name": f"Manage user: {title}",
        "ansible.builtin.user": params,
    }


def _convert_group(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``group`` resource to an Ansible group task.

    Args:
        title: Group name.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "present")
    state = _map_ensure(ensure)

    params: dict[str, Any] = {"name": title, "state": state}
    if "gid" in attrs:
        params["gid"] = attrs["gid"]

    return {
        "name": f"Manage group: {title}",
        "ansible.builtin.group": params,
    }


def _convert_exec(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``exec`` resource to an Ansible command task.

    Includes idempotency hints using ``creates``, ``unless``, or
    ``onlyif`` attributes when present.

    Args:
        title: Command string or exec name.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary with optional ``when`` conditions.

    """
    command = attrs.get("command", title)
    params: dict[str, Any] = {"cmd": command}

    task: dict[str, Any] = {
        "name": f"Execute command: {title}",
        "ansible.builtin.command": params,
    }

    # Add idempotency guards
    if "creates" in attrs:
        task["args"] = {"creates": attrs["creates"]}
    if "unless" in attrs:
        task["when"] = f"not ({attrs['unless']})"
    if "onlyif" in attrs:
        task["when"] = attrs["onlyif"]
    if "cwd" in attrs:
        params["chdir"] = attrs["cwd"]

    return task


def _convert_cron(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``cron`` resource to an Ansible cron task.

    Args:
        title: Cron job name.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "present")
    state = _map_ensure(ensure)

    params: dict[str, Any] = {"name": title, "state": state}
    for puppet_key, ansible_key in CRON_ATTR_MAP.items():
        if puppet_key in attrs:
            params[ansible_key] = attrs[puppet_key]

    return {
        "name": f"Manage cron job: {title}",
        "ansible.builtin.cron": params,
    }


def _convert_host(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``host`` resource to an Ansible lineinfile task.

    Puppet ``host`` resources manage ``/etc/hosts`` entries. Since Ansible
    does not have a dedicated hosts module, this maps to ``lineinfile``.

    Args:
        title: Hostname.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ip = attrs.get("ip", "")
    ensure = attrs.get("ensure", "present")
    state = _map_ensure(ensure)

    if ip:
        line = f"{ip} {title}"
        params: dict[str, Any] = {
            "path": "/etc/hosts",
            "line": line,
            "state": state,
        }
        return {
            "name": f"Manage /etc/hosts entry: {title}",
            "ansible.builtin.lineinfile": params,
        }

    return {
        "name": f"Manage host: {title} (manual review required — no IP specified)",
        "ansible.builtin.debug": {
            "msg": (
                f"Puppet host '{title}' has no IP address;"
                " review /etc/hosts manually"
            )
        },
    }


def _convert_mount(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``mount`` resource to an Ansible posix.mount task.

    Args:
        title: Mount point path.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "mounted")
    state = _map_ensure(ensure) if ensure in ENSURE_TO_STATE else ensure

    params: dict[str, Any] = {
        "path": title,
        "state": state,
    }
    if "device" in attrs:
        params["src"] = attrs["device"]
    if "fstype" in attrs:
        params["fstype"] = attrs["fstype"]
    if "options" in attrs:
        params["opts"] = attrs["options"]

    return {
        "name": f"Manage mount: {title}",
        "ansible.posix.mount": params,
    }


def _convert_ssh_authorized_key(title: str, attrs: dict[str, str]) -> dict[str, Any]:
    """
    Convert a Puppet ``ssh_authorized_key`` resource to Ansible authorized_key.

    Args:
        title: Key name / comment.
        attrs: Resource attributes.

    Returns:
        Ansible task dictionary.

    """
    ensure = attrs.get("ensure", "present")
    state = _map_ensure(ensure)

    params: dict[str, Any] = {
        "key": attrs.get("key", ""),
        "user": attrs.get("user", "root"),
        "state": state,
    }

    return {
        "name": f"Manage SSH authorized key: {title}",
        "ansible.posix.authorized_key": params,
    }


def _convert_unsupported(resource_type: str, title: str) -> dict[str, Any]:
    """
    Generate a debug warning task for an unsupported Puppet resource type.

    Args:
        resource_type: The unsupported Puppet resource type.
        title: Resource title.

    Returns:
        Ansible debug task dictionary.

    """
    return {
        "name": f"WARNING: Unsupported Puppet resource type '{resource_type}': {title}",
        "ansible.builtin.debug": {
            "msg": (
                f"Manual migration required: Puppet resource type '{resource_type}' "
                f"has no automatic Ansible equivalent. Resource: {title!r}"
            )
        },
    }


def get_puppet_ansible_module_map() -> dict[str, str]:
    """
    Return the mapping of Puppet resource types to Ansible modules.

    Returns:
        Dictionary mapping Puppet resource type names to Ansible module names.

    """
    return dict(RESOURCE_MODULE_MAP)


def get_supported_puppet_types() -> list[str]:
    """
    Return the list of Puppet resource types that can be converted automatically.

    Returns:
        Sorted list of supported Puppet resource type names.

    """
    return sorted(RESOURCE_MODULE_MAP.keys())
