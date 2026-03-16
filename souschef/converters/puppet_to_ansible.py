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

AI-Assisted Conversion
----------------------
For manifests with unsupported constructs (Hiera lookups, create_resources,
exported/virtual resources, etc.), the ``*_with_ai`` variants use a
configurable LLM to produce best-effort Ansible equivalents.  These functions
accept the same ``ai_provider``, ``api_key``, ``model``, ``temperature``,
``max_tokens``, ``project_id``, and ``base_url`` parameters as the Chef
recipe AI-assisted converters in :mod:`souschef.converters.playbook`.
"""

import importlib
import re
from typing import Any

from souschef.core.constants import (
    ERROR_FILE_NOT_FOUND,
    ERROR_IS_DIRECTORY,
    ERROR_PERMISSION_DENIED,
)
from souschef.core.path_utils import (
    _get_workspace_root,
    _normalize_path,
    _resolve_path_under_base,
    safe_read_text,
)
from souschef.parsers.puppet import (
    _parse_manifest_content,
    parse_puppet_manifest,
)

# Error prefix used for error detection in callers
_ERROR_PREFIX = "Error:"

# Shared Ansible module names
_ANSIBLE_DEBUG_MODULE = "ansible.builtin.debug"

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
        safe_path = _resolve_path_under_base(file_path, workspace_root)
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
        safe_dir = _resolve_path_under_base(dir_path, workspace_root)

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
                    f"WARNING: Unsupported construct '{item['construct']}' at {loc}"
                ),
                _ANSIBLE_DEBUG_MODULE: {
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
                _ANSIBLE_DEBUG_MODULE: {
                    "msg": f"No Puppet resources were found in {source}"
                },
            }
        ]

    playbook = [play]
    yaml_module = importlib.import_module("yaml")
    result: str = yaml_module.dump(
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
        _ANSIBLE_DEBUG_MODULE: {
            "msg": (
                f"Puppet host '{title}' has no IP address; review /etc/hosts manually"
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


# Dispatch table for resource type converters — defined after all _convert_* functions
_RESOURCE_CONVERTERS = {
    "package": _convert_package,
    "service": _convert_service,
    "file": _convert_file,
    "user": _convert_user,
    "group": _convert_group,
    "exec": _convert_exec,
    "cron": _convert_cron,
    "host": _convert_host,
    "mount": _convert_mount,
    "ssh_authorized_key": _convert_ssh_authorized_key,
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
        _ANSIBLE_DEBUG_MODULE: {
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


# ---------------------------------------------------------------------------
# AI-Assisted Conversion
# ---------------------------------------------------------------------------

# Maximum manifest content length sent to the LLM (trim beyond this)
_AI_MAX_CONTENT_CHARS = 40_000


def convert_puppet_manifest_to_ansible_with_ai(
    manifest_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """
    Convert a Puppet manifest to an Ansible playbook using an LLM.

    Uses a configurable AI provider to convert the *entire* manifest,
    with particular focus on unsupported constructs such as Hiera lookups,
    ``create_resources`` calls, exported/virtual resources, etc. that the
    deterministic converter cannot handle.

    If no unsupported constructs are detected the function falls back to the
    standard deterministic :func:`convert_puppet_manifest_to_ansible`.

    Args:
        manifest_path: Path to the Puppet manifest (``.pp``) file.
        ai_provider: AI provider to use (``'anthropic'``, ``'openai'``,
            ``'watson'``, ``'lightspeed'``).
        api_key: API key for the chosen provider.
        model: Model identifier (e.g. ``'claude-3-5-sonnet-20241022'``).
        temperature: Sampling temperature (0.0 – 1.0). Lower values produce
            more deterministic output; defaults to ``0.3`` for code generation.
        max_tokens: Maximum tokens in the LLM response.
        project_id: Project ID (required for IBM Watsonx).
        base_url: Custom base URL override for the provider endpoint.

    Returns:
        Ansible playbook YAML string, or an error message string prefixed
        with ``"Error:"`` if conversion fails.

    """
    try:
        file_path = _normalize_path(manifest_path)
        workspace_root = _get_workspace_root()
        safe_path = _resolve_path_under_base(file_path, workspace_root)
        raw_content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

        if len(raw_content) > MAX_CONTENT_LENGTH:
            return (
                f"Error: Manifest too large to convert safely "
                f"({len(raw_content)} bytes)"
            )

        parsed = _parse_manifest_content(raw_content, manifest_path)
        unsupported = parsed.get("unsupported", [])

        if not unsupported:
            # Nothing the LLM needs to help with — use fast deterministic path
            return _generate_puppet_playbook(parsed, manifest_path)

        # Build the analysis text for context
        parsed_analysis = parse_puppet_manifest(manifest_path)

        return _convert_manifest_with_ai(
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
        return ERROR_FILE_NOT_FOUND.format(path=manifest_path)
    except IsADirectoryError:
        return ERROR_IS_DIRECTORY.format(path=manifest_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=manifest_path)
    except Exception as e:
        return f"An error occurred: {e}"


def convert_puppet_module_to_ansible_with_ai(
    module_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """
    Convert a Puppet module directory to an Ansible playbook using an LLM.

    Combines all ``.pp`` files in the module, then applies AI-assisted
    conversion for any unsupported constructs found.  Falls back to the
    standard deterministic converter when no unsupported constructs exist.

    Args:
        module_path: Path to the Puppet module directory.
        ai_provider: AI provider (``'anthropic'``, ``'openai'``, ``'watson'``,
            ``'lightspeed'``).
        api_key: API key for the chosen provider.
        model: Model identifier.
        temperature: Sampling temperature; defaults to ``0.3``.
        max_tokens: Maximum tokens in the LLM response.
        project_id: Project ID for IBM Watsonx.
        base_url: Custom provider endpoint URL.

    Returns:
        Ansible playbook YAML string, or an error message string prefixed
        with ``"Error:"`` if conversion fails.

    """
    try:
        dir_path = _normalize_path(module_path)
        workspace_root = _get_workspace_root()
        safe_dir = _resolve_path_under_base(dir_path, workspace_root)

        if not safe_dir.exists():  # NOSONAR
            return ERROR_FILE_NOT_FOUND.format(path=module_path)
        if not safe_dir.is_dir():
            return ERROR_IS_DIRECTORY.format(path=module_path)

        manifests = sorted(safe_dir.rglob("*.pp"))
        if not manifests:
            return f"Warning: No Puppet manifests (.pp files) found in {module_path}"

        parsed_data = _collect_module_manifests(manifests, workspace_root)
        all_resources = parsed_data["resources"]
        all_unsupported = parsed_data["unsupported"]
        combined_content_parts = parsed_data["content_parts"]

        combined: dict[str, Any] = {
            "resources": all_resources,
            "classes": [],
            "variables": [],
            "unsupported": all_unsupported,
        }

        if not all_unsupported:
            return _generate_puppet_playbook(combined, module_path)

        # Build combined manifest text for context
        combined_raw = "\n\n".join(combined_content_parts)
        parsed_analysis = _format_module_analysis(
            all_resources, all_unsupported, module_path
        )

        return _convert_manifest_with_ai(
            combined_raw,
            parsed_analysis,
            all_unsupported,
            module_path,
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
        return ERROR_FILE_NOT_FOUND.format(path=module_path)
    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=module_path)
    except Exception as e:
        return f"An error occurred: {e}"


def _collect_module_manifests(
    manifests: list[Any],
    workspace_root: Any,
) -> dict[str, Any]:
    """
    Read and parse all ``.pp`` files in a module, collecting resources and content.

    Args:
        manifests: Sorted list of ``pathlib.Path`` objects pointing to ``.pp`` files.
        workspace_root: Workspace root path used for safe-path containment checks.

    Returns:
        Dictionary with keys ``'resources'``, ``'unsupported'``, and
        ``'content_parts'``.

    """
    all_resources: list[dict[str, Any]] = []
    all_unsupported: list[dict[str, Any]] = []
    combined_content_parts: list[str] = []

    for manifest_path in manifests:
        try:
            content = safe_read_text(manifest_path, workspace_root, encoding="utf-8")
            rel_path = str(manifest_path.relative_to(workspace_root))
            parsed = _parse_manifest_content(content, rel_path)
            all_resources.extend(parsed.get("resources", []))
            all_unsupported.extend(parsed.get("unsupported", []))
            combined_content_parts.append(f"# === {rel_path} ===\n{content}")
        except (OSError, ValueError):
            continue

    return {
        "resources": all_resources,
        "unsupported": all_unsupported,
        "content_parts": combined_content_parts,
    }


def _format_module_analysis(
    resources: list[dict[str, Any]],
    unsupported: list[dict[str, Any]],
    module_path: str,
) -> str:
    """
    Produce a concise analysis summary for a multi-file Puppet module.

    Args:
        resources: Aggregated list of parsed resources across all manifests.
        unsupported: Aggregated list of unsupported construct dicts.
        module_path: Path to the module root (used in heading).

    Returns:
        Formatted analysis string.

    """
    lines: list[str] = [
        f"Puppet Module Analysis: {module_path}",
        "",
        f"Total resources: {len(resources)}",
        f"Unsupported constructs: {len(unsupported)}",
    ]
    if unsupported:
        lines.append("")
        lines.append("Unsupported constructs requiring AI conversion:")
        for item in unsupported:
            loc = f"{item['source_file']}:{item['line']}"
            lines.append(f"  [{item['construct']}] at {loc} — {item['text']!r}")
    return "\n".join(lines)


def _convert_manifest_with_ai(
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
    Core AI-assisted conversion routine shared by manifest and module variants.

    Initialises the AI client, builds the conversion prompt, calls the LLM,
    and cleans the response.

    Args:
        raw_content: Full Puppet manifest text (may be multi-file concatenation).
        parsed_analysis: Human-readable analysis string for context.
        unsupported: List of unsupported construct dicts.
        source_name: File or directory name used in error messages.
        ai_provider: AI provider identifier.
        api_key: Provider API key.
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.
        project_id: Watsonx project ID.
        base_url: Custom provider URL.

    Returns:
        Cleaned Ansible playbook YAML string, or an error message string.

    """
    # Lazy import to avoid loading AI libraries unless needed
    from souschef.converters.playbook import (
        _call_ai_api,
        _initialize_ai_client,
    )

    client = _initialize_ai_client(ai_provider, api_key, project_id, base_url)
    if isinstance(client, str):
        # _initialize_ai_client returns an error string on failure
        return client

    prompt = _create_puppet_ai_prompt(
        raw_content, parsed_analysis, unsupported, source_name
    )
    ai_response = _call_ai_api(
        client, ai_provider, prompt, model, temperature, max_tokens
    )
    return _clean_puppet_ai_response(ai_response)


def _create_puppet_ai_prompt(
    raw_content: str,
    parsed_analysis: str,
    unsupported: list[dict[str, Any]],
    manifest_name: str,
) -> str:
    """
    Build the LLM prompt for Puppet → Ansible conversion.

    The prompt explains the manifest content, the parsed analysis, the
    specific unsupported constructs that need AI help, and the output format
    requirements.

    Args:
        raw_content: Raw Puppet manifest text (truncated if very long).
        parsed_analysis: Pre-formatted analysis string from the parser.
        unsupported: List of unsupported construct dictionaries.
        manifest_name: Manifest file or module name (used in play name).

    Returns:
        Prompt string ready to send to the LLM.

    """
    # Truncate very long manifests to avoid exceeding context windows
    if len(raw_content) > _AI_MAX_CONTENT_CHARS:
        raw_content = raw_content[:_AI_MAX_CONTENT_CHARS] + "\n# [truncated]"

    unsupported_lines = _format_unsupported_for_prompt(unsupported)
    guidance_lines = _build_construct_guidance(unsupported)

    parts = [
        "You are an expert Puppet-to-Ansible migration engineer.",
        (
            "Convert the Puppet manifest below into a complete, production-ready "
            "Ansible playbook."
        ),
        "",
        "PUPPET MANIFEST CONTENT:",
        raw_content,
        "",
        "PARSED PUPPET ANALYSIS (for context):",
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
        "- Use fully-qualified Ansible module names (ansible.builtin.*).",
        "- Set `become: true` at the play level.",
        "- Name the play: 'Converted from Puppet: " + manifest_name + "'",
        (
            "- Preserve the logical order: install packages, then configure, "
            "then start services."
        ),
        "",
        "OUTPUT FORMAT:",
        (
            "Return ONLY valid YAML for a single Ansible playbook. "
            "Do NOT include markdown code fences, explanations, "
            "or any text outside the YAML."
        ),
    ]
    return "\n".join(parts)


def _format_unsupported_for_prompt(unsupported: list[dict[str, Any]]) -> str:
    """
    Format unsupported construct list as a human-readable prompt section.

    Args:
        unsupported: List of unsupported construct dicts from the parser.

    Returns:
        Formatted multi-line string listing each unsupported construct.

    """
    if not unsupported:
        return "(none)"
    lines = []
    for item in unsupported:
        loc = f"{item['source_file']}:{item['line']}"
        lines.append(f"  - [{item['construct']}] at {loc}: {item['text']!r}")
    return "\n".join(lines)


def _build_construct_guidance(unsupported: list[dict[str, Any]]) -> str:
    """
    Build targeted conversion guidance based on the detected construct types.

    Args:
        unsupported: List of unsupported construct dicts.

    Returns:
        Guidance string with specific instructions per construct type.

    """
    seen: set[str] = set()
    for item in unsupported:
        seen.add(item["construct"])

    guidance_map: dict[str, str] = {
        "Hiera lookup": (
            "Hiera lookup: Replace hiera('key', default) with an Ansible "
            "variable reference {{ key }}; declare variables in vars: "
            "with sensible defaults."
        ),
        "Hiera lookup (lookup function)": (
            "Hiera lookup (lookup): Replace lookup('key', ...) with an Ansible "
            "variable {{ key }} and add it to the play vars: section."
        ),
        "create_resources function": (
            "create_resources: Unroll into individual resource tasks "
            "using a loop (with_items / loop) over the hash entries."
        ),
        "generate function": (
            "generate(): Replace with ansible.builtin.command or "
            "ansible.builtin.shell with an equivalent command, "
            "guarded by a when condition for idempotency."
        ),
        "inline_template function": (
            "inline_template(): Convert ERB expressions to Jinja2 equivalents "
            "and use ansible.builtin.template or set_fact."
        ),
        "defined() function": (
            "defined(): Replace with Ansible's `is defined` test in a "
            "when: condition, e.g. `when: my_var is defined`."
        ),
        "Virtual resource declaration": (
            "Virtual resource (@Resource): Include as a regular task "
            "with a when condition to control activation."
        ),
        "Virtual resource realization": (
            "realize(): Convert to a direct task (idempotency is handled "
            "by the module itself)."
        ),
        "Resource collection expression": (
            "Resource collection (<| |>): Replace with a task loop "
            "over a host group or dynamic inventory group."
        ),
        "Exported resource": (
            "Exported resource (@@): Use ansible.builtin.add_host or "
            "group_vars to share data across hosts, then apply tasks "
            "to the target group."
        ),
    }

    lines = []
    for construct, hint in guidance_map.items():
        if construct in seen:
            lines.append(f"- {hint}")

    return (
        "\n".join(lines) if lines else ("- Follow best practices for idempotent tasks.")
    )


def _clean_puppet_ai_response(ai_response: str) -> str:
    """
    Strip markdown fences from the AI response and validate it looks like YAML.

    Args:
        ai_response: Raw string returned by the LLM.

    Returns:
        Cleaned YAML string, or an error message if the response is invalid.

    """
    if not ai_response or not ai_response.strip():
        return f"{_ERROR_PREFIX} AI returned an empty response"

    # Remove markdown code fences (```yaml ... ``` or ``` ... ```)
    cleaned = re.sub(r"```\w*\n?", "", ai_response).strip()

    # Minimal sanity check — must look like a YAML list or mapping
    if not cleaned.startswith("---") and not cleaned.startswith("- "):
        return (
            f"{_ERROR_PREFIX} AI response does not appear to be a valid "
            "Ansible playbook (expected YAML list starting with '---' or '- ')"
        )

    return cleaned
