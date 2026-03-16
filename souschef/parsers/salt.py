"""SaltStack SLS file parser."""

import importlib
import json
import os
import re
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
    safe_exists,
    safe_is_dir,
    safe_read_text,
)

# Supported Salt state module types mapped to semantic categories
SALT_STATE_MODULES = {
    "pkg": "package",
    "file": "file",
    "service": "service",
    "cmd": "command",
    "user": "user",
    "group": "group",
    "git": "git",
    "pip": "pip",
    "npm": "npm",
    "gem": "gem",
    "cron": "cron",
    "mount": "mount",
    "firewall": "firewall",
    "sysctl": "sysctl",
    "timezone": "timezone",
    "locale": "locale",
    "host": "host",
    "archive": "archive",
}

# Salt pkg.installed state functions mapped to Ansible equivalents
SALT_PKG_FUNCTIONS = {
    "installed": "present",
    "removed": "absent",
    "purged": "absent",
    "latest": "latest",
    "uptodate": "latest",
}

# Salt service state functions mapped to Ansible state/enabled
SALT_SERVICE_FUNCTIONS: dict[str, dict[str, Any | None]] = {
    "running": {"state": "started", "enabled": True},
    "enabled": {"state": None, "enabled": True},
    "disabled": {"state": None, "enabled": False},
    "dead": {"state": "stopped", "enabled": None},
    "reload": {"state": "reloaded", "enabled": None},
    "restart": {"state": "restarted", "enabled": None},
}

# Salt file state functions
SALT_FILE_FUNCTIONS = {
    "managed": "template",
    "directory": "directory",
    "absent": "absent",
    "symlink": "link",
    "recurse": "copy",
    "touch": "touch",
    "replace": "lineinfile",
    "line": "lineinfile",
    "comment": "replace",
    "uncomment": "replace",
    "append": "blockinfile",
    "prepend": "blockinfile",
    "contains": "stat",
    "copy": "copy",
    "rename": "command",
    "accumulated": "blockinfile",
    "serialize": "template",
    "patch": "patch",
    "exists": "stat",
}


def _parse_sls_yaml(content: str) -> dict[str, Any]:
    """
    Parse SLS file content as YAML.

    SLS files are YAML-based with optional Jinja2 templating. This parser
    handles common patterns while treating Jinja2 expressions as opaque strings.

    Args:
        content: Raw SLS file content.

    Returns:
        Parsed YAML data as a dictionary.

    """
    try:
        yaml_module = importlib.import_module("yaml")

        # Strip Jinja2 blocks and expressions for basic parsing
        # Replace {%...%} blocks with comments
        clean = re.sub(r"\{%-?\s*.*?-?%\}", "", content, flags=re.DOTALL)
        # Replace {{...}} expressions with placeholder string
        clean = re.sub(r"\{\{.*?\}\}", "'__JINJA2__'", clean)
        result = yaml_module.safe_load(clean)
        if isinstance(result, dict):
            return result
        return {}
    except Exception:  # noqa: BLE001
        return {}


def _extract_args_from_value(value: Any) -> dict[str, Any]:
    """
    Extract args dict from a Salt state value (list or dict).

    Args:
        value: The value part of a ``module.function: value`` mapping.

    Returns:
        Dict of argument names to values.

    """
    args: dict[str, Any] = {}
    if isinstance(value, list):
        for arg in value:
            if isinstance(arg, dict):
                args.update(arg)
    elif isinstance(value, dict):
        args = value
    return args


def _build_state_entry(
    state_id: str, module: str, func: str, value: Any
) -> dict[str, Any]:
    """
    Build a state entry dict from parsed module/function/value data.

    Args:
        state_id: The Salt state identifier string.
        module: The Salt module name (e.g. ``pkg``).
        func: The Salt function name (e.g. ``installed``).
        value: The raw value from the SLS YAML.

    Returns:
        State entry dict.

    """
    return {
        "id": state_id,
        "module": module,
        "function": func,
        "args": _extract_args_from_value(value),
        "category": SALT_STATE_MODULES.get(module, "unknown"),
    }


def _extract_state_id_and_module(state_id: str, state_def: Any) -> list[dict[str, Any]]:
    """
    Extract Salt state entries from a single state ID definition.

    A state ID may contain multiple state module calls (e.g., pkg.installed
    and service.running in the same ID block).

    Salt supports two equivalent SLS YAML formats:

    Simple format (dict value, most common):

    .. code-block:: yaml

        nginx:
          pkg.installed:
            - name: nginx

    Multi-state format (list of dicts):

    .. code-block:: yaml

        nginx:
          - pkg.installed:
            - name: nginx

    Args:
        state_id: The Salt state identifier string.
        state_def: The value associated with that state ID (list or dict).

    Returns:
        List of state entry dicts with keys: id, module, function, args.

    """
    entries: list[dict[str, Any]] = []

    # Handle the simple dict format: {module.function: [args...]}
    if isinstance(state_def, dict):
        for key, value in state_def.items():
            if "." in key:
                module, func = key.split(".", 1)
                entries.append(_build_state_entry(state_id, module, func, value))
        return entries

    # Handle the list format: [{module.function: [args...]}, ...]
    if not isinstance(state_def, list):
        return entries

    for item in state_def:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if "." in key:
                module, func = key.split(".", 1)
                entries.append(_build_state_entry(state_id, module, func, value))
    return entries


def _extract_pillars(content: str) -> dict[str, Any]:
    """
    Extract pillar variable references from SLS content.

    Detects ``pillar['key']``, ``pillar.get('key', default)``, and
    ``salt['pillar.get']('key', default)`` patterns.

    Args:
        content: Raw SLS file content.

    Returns:
        Dictionary mapping pillar key names to provenance metadata.

    """
    pillars: dict[str, Any] = {}

    # Pattern: pillar['key'] or pillar["key"]
    for m in re.finditer(r"pillar\[(['\"])(\w[\w.:-]*)\1\]", content):
        key = m.group(2)
        pillars[key] = {"source": "pillar", "access": "direct", "default": None}

    # Pattern: pillar.get('key') or pillar.get('key', 'default')
    for m in re.finditer(
        r"pillar\.get\(\s*(['\"])(\w[\w.:-]*)\1(?:\s*,\s*([^)]+))?\s*\)",
        content,
    ):
        key = m.group(2)
        default = m.group(3).strip().strip("'\"") if m.group(3) else None
        pillars[key] = {"source": "pillar", "access": "get", "default": default}

    # Pattern: salt['pillar.get']('key') or salt['pillar.get']('key', 'default')
    for m in re.finditer(
        r"salt\[['\"]pillar\.get['\"]\]\(\s*(['\"])(\w[\w.:-]*)\1(?:\s*,\s*([^)]+))?\s*\)",
        content,
    ):
        key = m.group(2)
        default = m.group(3).strip().strip("'\"") if m.group(3) else None
        pillars[key] = {
            "source": "salt_pillar_get",
            "access": "salt_call",
            "default": default,
        }

    return pillars


def _extract_grains(content: str) -> list[str]:
    """
    Extract grain references from SLS content.

    Detects ``grains['key']`` and ``grains.get('key')`` patterns.

    Args:
        content: Raw SLS file content.

    Returns:
        List of grain key names referenced in the SLS file.

    """
    grains: list[str] = []
    for m in re.finditer(r"grains\[(['\"])(\w[\w.:-]*)\1\]", content):
        grains.append(m.group(2))
    for m in re.finditer(r"grains\.get\(\s*(['\"])(\w[\w.:-]*)\1", content):
        key = m.group(2)
        if key not in grains:
            grains.append(key)
    return grains


def _parse_sls_states(content: str) -> list[dict[str, Any]]:
    """
    Parse all state definitions from SLS content.

    Args:
        content: Raw SLS file content.

    Returns:
        List of normalised state entry dicts.

    """
    data = _parse_sls_yaml(content)
    states: list[dict[str, Any]] = []

    for state_id, state_def in data.items():
        # Skip YAML top-level keys that are not state definitions
        if state_id in ("include", "extend"):
            continue
        entries = _extract_state_id_and_module(state_id, state_def)
        states.extend(entries)

    return states


def _summarise_states(states: list[dict[str, Any]]) -> dict[str, int]:
    """
    Summarise extracted states by category count.

    Args:
        states: List of state entry dicts.

    Returns:
        Dictionary mapping category names to counts.

    """
    counts: dict[str, int] = {}
    for state in states:
        cat = state.get("category", "unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def parse_salt_sls(sls_path: str) -> str:
    """
    Parse a SaltStack SLS state file and extract structured state data.

    Analyses SLS files to extract state definitions, pillar variable references,
    grain references, and provides a summary suitable for Ansible conversion.

    Supported state modules: pkg, file, service, cmd, user, group, git, pip,
    npm, gem, cron, mount, firewall, sysctl, timezone, locale, host, archive.

    Args:
        sls_path: Path to the SLS state file.

    Returns:
        JSON string with parsed state metadata including states list, pillar
        provenance mapping, grain references, and summary counts.

    """
    try:
        normalized_path = _normalize_path(sls_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_exists(safe_path, workspace_root):
            return ERROR_FILE_NOT_FOUND.format(path=safe_path)
        if safe_is_dir(safe_path, workspace_root):
            return ERROR_IS_DIRECTORY.format(path=safe_path)

        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=sls_path)
    except ValueError as e:
        return f"Error: {e}"

    states = _parse_sls_states(content)
    pillars = _extract_pillars(content)
    grains = _extract_grains(content)
    summary = _summarise_states(states)

    result: dict[str, Any] = {
        "file": sls_path,
        "states": states,
        "pillar_provenance": pillars,
        "grain_references": grains,
        "summary": {
            "total_states": len(states),
            "by_category": summary,
            "pillar_keys": list(pillars.keys()),
            "grain_keys": grains,
        },
    }

    return json.dumps(result, indent=2)


def parse_salt_pillar(pillar_path: str) -> str:
    """
    Parse a SaltStack pillar file and extract variable definitions.

    Pillar files define configuration data injected into states. This parser
    extracts variable names, values, and nesting structure.

    Args:
        pillar_path: Path to the pillar SLS file.

    Returns:
        JSON string with pillar variable definitions and structure.

    """
    try:
        normalized_path = _normalize_path(pillar_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_exists(safe_path, workspace_root):
            return ERROR_FILE_NOT_FOUND.format(path=safe_path)
        if safe_is_dir(safe_path, workspace_root):
            return ERROR_IS_DIRECTORY.format(path=safe_path)

        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=pillar_path)
    except ValueError as e:
        return f"Error: {e}"

    data = _parse_sls_yaml(content)
    flattened = _flatten_dict_to_dot_notation(data)

    result: dict[str, Any] = {
        "file": pillar_path,
        "variables": data,
        "flattened": flattened,
        "summary": {
            "total_keys": len(flattened),
            "top_level_keys": list(data.keys()) if isinstance(data, dict) else [],
        },
    }

    return json.dumps(result, indent=2)


def _flatten_dict_to_dot_notation(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dictionaries into dot-notation keys."""
    flat: dict[str, Any] = {}
    if not isinstance(obj, dict):
        return flat

    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten_dict_to_dot_notation(value, full_key))
        else:
            flat[full_key] = value
    return flat


def parse_salt_top(top_path: str) -> str:
    """
    Parse a SaltStack top.sls file and extract target-to-state mappings.

    The top file maps minion targets (hostnames/globs/grains) to the SLS
    states that should be applied to them.

    Args:
        top_path: Path to the top.sls file.

    Returns:
        JSON string with target-to-state mappings per environment.

    """
    try:
        normalized_path = _normalize_path(top_path)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_exists(safe_path, workspace_root):
            return ERROR_FILE_NOT_FOUND.format(path=safe_path)
        if safe_is_dir(safe_path, workspace_root):
            return ERROR_IS_DIRECTORY.format(path=safe_path)

        content = safe_read_text(safe_path, workspace_root, encoding="utf-8")

    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=top_path)
    except ValueError as e:
        return f"Error: {e}"

    data = _parse_sls_yaml(content)
    environments = _parse_top_environments(data)

    all_states: list[str] = []
    for env_targets in environments.values():
        for states in env_targets.values():
            all_states.extend(states)
    unique_states = sorted(set(all_states))

    result: dict[str, Any] = {
        "file": top_path,
        "environments": environments,
        "summary": {
            "environments": list(environments.keys()),
            "total_targets": sum(len(t) for t in environments.values()),
            "unique_states": unique_states,
        },
    }

    return json.dumps(result, indent=2)


def _parse_top_environments(data: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    """
    Parse top.sls YAML data into environment-to-target-to-states mapping.

    Args:
        data: Parsed YAML dict from a top.sls file.

    Returns:
        Nested dict: environment -> target -> list of state names.

    """
    environments: dict[str, dict[str, list[str]]] = {}
    for env_name, env_data in data.items():
        if isinstance(env_data, dict):
            targets: dict[str, list[str]] = {}
            for target, states in env_data.items():
                if isinstance(states, list):
                    targets[target] = [str(s) for s in states]
                elif isinstance(states, str):
                    targets[target] = [states]
            environments[env_name] = targets
    return environments


def _list_sls_files(directory: Path, base_path: Path) -> list[str]:
    """
    Recursively list all SLS files in a directory.

    Args:
        directory: Root directory to search.
        base_path: Trusted base directory for path containment check.

    Returns:
        List of relative SLS file paths.

    """
    base_str = os.path.normpath(str(base_path))
    candidate_str = os.path.normpath(str(directory))
    try:
        common = os.path.commonpath([candidate_str, base_str])
    except ValueError as exc:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg) from exc
    if common != base_str:
        msg = f"Path traversal attempt: escapes {base_path}"
        raise ValueError(msg)
    validated_dir = Path(candidate_str)
    results: list[str] = []
    for p in sorted(validated_dir.rglob("*.sls")):
        try:
            rel = p.relative_to(validated_dir)
        except ValueError:
            # Skip paths that are not descendants of the validated directory
            continue
        results.append(str(rel))
    return results


def parse_salt_directory(salt_dir: str) -> str:
    """
    Parse a SaltStack state directory structure.

    Scans a Salt states directory to discover SLS files, top files,
    and pillar files, then returns a structural overview.

    Args:
        salt_dir: Path to the Salt states root directory.

    Returns:
        JSON string with directory structure overview.

    """
    try:
        normalized_path = _normalize_path(salt_dir)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_exists(safe_path, workspace_root):
            return ERROR_FILE_NOT_FOUND.format(path=safe_path)
        if not safe_is_dir(safe_path, workspace_root):
            return f"Error: Path is not a directory: {salt_dir}"

    except PermissionError:
        return ERROR_PERMISSION_DENIED.format(path=salt_dir)
    except ValueError as e:
        return f"Error: {e}"

    sls_files = _list_sls_files(safe_path, workspace_root)
    top_files = [f for f in sls_files if Path(f).name == "top.sls"]
    pillar_files = [f for f in sls_files if "pillar" in f.lower()]
    state_files = [f for f in sls_files if f not in top_files and f not in pillar_files]

    result: dict[str, Any] = {
        "directory": salt_dir,
        "files": {
            "all": sls_files,
            "top": top_files,
            "pillars": pillar_files,
            "states": state_files,
        },
        "summary": {
            "total_files": len(sls_files),
            "top_files": len(top_files),
            "pillar_files": len(pillar_files),
            "state_files": len(state_files),
        },
    }

    return json.dumps(result, indent=2)


def _score_state_complexity(state: dict[str, Any]) -> float:
    """
    Score the migration complexity of a single Salt state.

    Assigns a complexity score from 0.0 (trivial) to 1.0 (very complex) based
    on the state module type, argument count, and Jinja2 template usage.

    Args:
        state: Salt state entry dict with module, function, and args keys.

    Returns:
        Float from 0.0 (trivial) to 1.0 (very complex).

    """
    module = state.get("module", "")
    func = state.get("function", "")
    args = state.get("args", {})

    score = _base_complexity_for_module(module)
    score += _command_function_penalty(module, func)
    score += _jinja_penalty(args)
    score += _arg_count_penalty(args)

    return min(score, 1.0)


def _base_complexity_for_module(module: str) -> float:
    """Return base complexity by Salt module type."""
    complex_modules = {"cmd", "git", "archive", "mount", "firewall", "sysctl"}
    simple_modules = {"pkg", "service"}
    if module in complex_modules:
        return 0.4
    if module in simple_modules:
        return 0.1
    return 0.2


def _command_function_penalty(module: str, function: str) -> float:
    """Return additional complexity for imperative command execution."""
    if module == "cmd" and function in {"run", "script", "call"}:
        return 0.2
    return 0.0


def _count_jinja_markers(value: Any) -> int:
    """Count Jinja2 placeholders in a scalar/list argument value."""
    if isinstance(value, str):
        return 1 if "__JINJA2__" in value else 0
    if isinstance(value, list):
        return sum(
            1 for item in value if isinstance(item, str) and "__JINJA2__" in item
        )
    return 0


def _jinja_penalty(args: Any) -> float:
    """Return complexity penalty based on Jinja2 usage in arguments."""
    if not isinstance(args, dict):
        return 0.0
    jinja_count = sum(_count_jinja_markers(value) for value in args.values())
    return min(jinja_count * 0.1, 0.3)


def _arg_count_penalty(args: Any) -> float:
    """Return complexity penalty based on number of arguments."""
    if not isinstance(args, dict):
        return 0.0
    arg_count = len(args)
    if arg_count > 5:
        return 0.2
    if arg_count > 3:
        return 0.1
    return 0.0


def _detect_salt_dependencies(content: str) -> dict[str, list[str]]:
    """
    Detect state dependencies in SLS file content.

    Parses require, watch, onchanges, onfail, and listen dependency
    declarations as well as include clauses from SLS content.

    Args:
        content: Raw SLS file content string.

    Returns:
        Dict mapping state IDs to dependency strings like ``"pkg:nginx"``.
        The special ``"__include__"`` key lists included SLS module names.

    """
    data = _parse_sls_yaml(content)
    dependencies = _extract_include_dependencies(data)

    for state_id, state_def in data.items():
        if state_id in ("include", "extend"):
            continue

        arg_dicts = _extract_dependency_arg_dicts(state_def)
        state_deps = _collect_state_dependencies(arg_dicts)
        if state_deps:
            dependencies[str(state_id)] = state_deps

    return dependencies


def _extract_include_dependencies(data: dict[str, Any]) -> dict[str, list[str]]:
    """Extract dependencies introduced via the top-level include clause."""
    dependencies: dict[str, list[str]] = {}
    includes = data.get("include")
    if isinstance(includes, list):
        dependencies["__include__"] = [str(inc) for inc in includes]
    return dependencies


def _extract_dependency_arg_dicts(state_def: Any) -> list[dict[str, Any]]:
    """Extract nested argument dictionaries from Salt state definition formats."""
    arg_dicts: list[dict[str, Any]] = []
    sources: list[Any]

    if isinstance(state_def, dict):
        sources = list(state_def.values())
    elif isinstance(state_def, list):
        sources = [
            val for item in state_def if isinstance(item, dict) for val in item.values()
        ]
    else:
        return arg_dicts

    for value in sources:
        if not isinstance(value, list):
            continue
        arg_dicts.extend(item for item in value if isinstance(item, dict))

    return arg_dicts


def _collect_state_dependencies(arg_dicts: list[dict[str, Any]]) -> list[str]:
    """Collect dependency tokens from extracted argument dictionaries."""
    dep_keywords = {"require", "watch", "onchanges", "onfail", "listen"}
    dependencies: list[str] = []

    for arg_dict in arg_dicts:
        for keyword in dep_keywords:
            dep_list = arg_dict.get(keyword)
            if not isinstance(dep_list, list):
                continue
            dependencies.extend(_dependency_items_to_tokens(dep_list))

    return dependencies


def _dependency_items_to_tokens(dep_items: list[Any]) -> list[str]:
    """Convert Salt dependency item dictionaries into module:id tokens."""
    tokens: list[str] = []
    for dep_item in dep_items:
        if not isinstance(dep_item, dict):
            continue
        tokens.extend(
            f"{dep_module}:{dep_id}" for dep_module, dep_id in dep_item.items()
        )
    return tokens


def assess_salt_complexity(salt_dir: str) -> str:
    """
    Assess migration complexity of a SaltStack state directory.

    Scans all SLS files in the given directory, scores each state's migration
    complexity, and produces per-file and overall complexity reports with
    effort estimates.

    Uses ``ComplexityLevel`` and ``EffortMetrics`` from
    ``souschef.core.metrics`` for consistent effort reporting.

    Args:
        salt_dir: Path to the Salt states root directory.

    Returns:
        JSON string with:

        - ``directory``: The assessed directory path.
        - ``files``: List of per-file reports (file, state_count,
          complexity_score, complexity_level, dependencies, module_summary).
        - ``summary``: Overall complexity_score, complexity_level,
          total_files, total_states, estimated_effort_days,
          estimated_effort_days_with_souschef, estimated_effort_hours,
          estimated_effort_weeks, high_complexity_files, module_breakdown.

    """
    from souschef.core.metrics import (
        categorize_complexity,
        estimate_effort_for_complexity,
    )

    try:
        normalized_path = _normalize_path(salt_dir)
        workspace_root = _get_workspace_root()
        safe_path = _ensure_within_base_path(normalized_path, workspace_root)

        if not safe_exists(safe_path, workspace_root):
            return json.dumps({"error": f"Directory not found: {salt_dir}"})
        if not safe_is_dir(safe_path, workspace_root):
            return json.dumps({"error": f"Path is not a directory: {salt_dir}"})

    except PermissionError:
        return json.dumps({"error": f"Permission denied: {salt_dir}"})
    except ValueError as e:
        return json.dumps({"error": str(e)})

    sls_files = _list_sls_files(safe_path, workspace_root)
    file_reports: list[dict[str, Any]] = []
    total_score_sum = 0.0
    total_states = 0
    module_breakdown: dict[str, int] = {}
    high_complexity_files: list[str] = []

    for rel_path in sls_files:
        file_path = safe_path / rel_path
        try:
            content = safe_read_text(file_path, workspace_root, encoding="utf-8")
        except OSError:
            continue

        states = _parse_sls_states(content)
        deps = _detect_salt_dependencies(content)

        state_scores = [_score_state_complexity(s) for s in states]
        avg_score = (
            (sum(state_scores) / len(state_scores)) * 100 if state_scores else 0.0
        )
        complexity_level = categorize_complexity(avg_score)

        # Module summary for this file
        mod_summary: dict[str, int] = {}
        for state in states:
            mod = state.get("module", "unknown")
            mod_summary[mod] = mod_summary.get(mod, 0) + 1
            module_breakdown[mod] = module_breakdown.get(mod, 0) + 1

        total_score_sum += avg_score
        total_states += len(states)

        if complexity_level.value == "high":
            high_complexity_files.append(rel_path)

        file_reports.append(
            {
                "file": rel_path,
                "state_count": len(states),
                "complexity_score": round(avg_score, 2),
                "complexity_level": complexity_level.value,
                "dependencies": deps,
                "module_summary": mod_summary,
            }
        )

    total_files = len(sls_files)
    overall_score = (total_score_sum / total_files) if total_files > 0 else 0.0
    overall_complexity = categorize_complexity(overall_score)
    effort = estimate_effort_for_complexity(overall_score, total_states)

    result: dict[str, Any] = {
        "directory": salt_dir,
        "files": file_reports,
        "summary": {
            "complexity_score": round(overall_score, 2),
            "complexity_level": overall_complexity.value,
            "total_files": total_files,
            "total_states": total_states,
            "estimated_effort_days": effort.estimated_days,
            "estimated_effort_days_with_souschef": effort.estimated_days_with_souschef,
            "estimated_effort_hours": effort.estimated_hours,
            "estimated_effort_weeks": effort.estimated_weeks_range,
            "high_complexity_files": high_complexity_files,
            "module_breakdown": module_breakdown,
        },
    }

    return json.dumps(result, indent=2)
