"""
Enterprise-grade Ansible artefact generators for PowerShell migration.

Produces the full set of files required for a production-ready Windows
automation project on Ansible Automation Platform (AAP) / AWX:

- Windows inventory template (WinRM-ready ``[windows]`` INI file)
- ``group_vars/windows.yml`` with WinRM connection variables
- ``requirements.yml`` listing required Ansible collections
- Complete Ansible Role directory structure
- AWX / AAP Windows job template JSON (importable via ``awx-cli``)
- Migration fidelity analysis report

All generators accept the parsed IR (as returned by
:func:`souschef.parsers.powershell.parse_powershell_content`) so that
output can be tailored to the actual actions found in each script.
"""

from __future__ import annotations

import importlib
import json
import re
from typing import Any, cast

yaml = cast(Any, importlib.import_module("yaml"))

_COMMUNITY_WINDOWS_NAME = "community.windows"
_COMMUNITY_WINDOWS_VERSION = ">=2.2.0"
_UNKNOWN_SOURCE = "<unknown>"
_REBOOT_HANDLER_NAME = "Reboot if required"
_DEFAULT_WINRM_CREDENTIAL_NAME = "windows-winrm-credential"

# ---------------------------------------------------------------------------
# Collections required for Windows automation
# ---------------------------------------------------------------------------

#: Always-required Ansible collections for Windows automation
_REQUIRED_COLLECTIONS: list[dict[str, str]] = [
    {"name": "ansible.windows", "version": ">=2.4.0"},
    {"name": _COMMUNITY_WINDOWS_NAME, "version": _COMMUNITY_WINDOWS_VERSION},
]

#: Additional collections triggered by specific action types
_CONDITIONAL_COLLECTIONS: dict[str, dict[str, str]] = {
    "chocolatey_install": {"name": "chocolatey.chocolatey", "version": ">=1.5.0"},
    "chocolatey_uninstall": {"name": "chocolatey.chocolatey", "version": ">=1.5.0"},
    "psmodule_install": {
        "name": _COMMUNITY_WINDOWS_NAME,
        "version": _COMMUNITY_WINDOWS_VERSION,
    },
    "scheduled_task_register": {
        "name": _COMMUNITY_WINDOWS_NAME,
        "version": _COMMUNITY_WINDOWS_VERSION,
    },
    "scheduled_task_unregister": {
        "name": _COMMUNITY_WINDOWS_NAME,
        "version": _COMMUNITY_WINDOWS_VERSION,
    },
    "iis_website_create": {
        "name": _COMMUNITY_WINDOWS_NAME,
        "version": _COMMUNITY_WINDOWS_VERSION,
    },
    "dns_client_set": {
        "name": _COMMUNITY_WINDOWS_NAME,
        "version": _COMMUNITY_WINDOWS_VERSION,
    },
    "certificate_import": {
        "name": _COMMUNITY_WINDOWS_NAME,
        "version": _COMMUNITY_WINDOWS_VERSION,
    },
}

#: Action types that map to enterprise tiers (for fidelity report)
_HIGH_FIDELITY_TYPES: frozenset[str] = frozenset(
    {
        "windows_feature_install",
        "windows_feature_remove",
        "windows_optional_feature_enable",
        "windows_optional_feature_disable",
        "windows_service_start",
        "windows_service_stop",
        "windows_service_configure",
        "windows_service_create",
        "registry_set",
        "registry_create_key",
        "registry_remove_key",
        "file_copy",
        "directory_create",
        "file_remove",
        "file_write",
        "msi_install",
        "chocolatey_install",
        "chocolatey_uninstall",
        "user_create",
        "user_modify",
        "user_remove",
        "group_member_add",
        "group_member_remove",
        "firewall_rule_create",
        "firewall_rule_enable",
        "firewall_rule_disable",
        "firewall_rule_remove",
        "scheduled_task_register",
        "scheduled_task_unregister",
        "environment_set",
        "psmodule_install",
        "certificate_import",
        "winrm_enable",
        "iis_website_create",
        "dns_client_set",
        "acl_set",
    }
)

#: Action types that require manual review after conversion
_REVIEW_REQUIRED_TYPES: frozenset[str] = frozenset(
    {
        "firewall_rule_create",  # Direction/protocol/port need manual completion
        "acl_set",  # ACE entries need manual completion
        "certificate_import",  # Store location may need adjustment
        "winrm_enable",  # Already configured if using Ansible
        "iis_website_create",  # Bindings / app pool need manual completion
        "scheduled_task_register",  # Action/trigger need manual completion
    }
)


# ---------------------------------------------------------------------------
# Public generators
# ---------------------------------------------------------------------------


def generate_windows_inventory(
    hosts: list[str] | None = None,
    winrm_port: int = 5986,
    use_ssl: bool = True,
    validate_certs: bool = False,
    winrm_transport: str = "ntlm",
) -> str:
    """
    Generate a WinRM-ready Ansible inventory file for Windows targets.

    Produces an INI-format inventory with ``[windows]`` group and matching
    ``[windows:vars]`` section containing the WinRM connection settings
    required by ``ansible.windows``.

    Args:
        hosts: Optional list of Windows host names or IPs to include in the
            inventory.  When omitted a placeholder host is added.
        winrm_port: WinRM listener port (5986 for HTTPS, 5985 for HTTP).
        use_ssl: Whether to use HTTPS (WinRM over SSL).  Set to ``False`` for
            HTTP (port ``5985``) in isolated lab environments.
        validate_certs: Whether Ansible should validate the WinRM SSL
            certificate.  Typically ``False`` for self-signed certs.
        winrm_transport: WinRM authentication transport method.  Valid values
            are ``ntlm`` (default), ``kerberos``, ``basic``, ``credssp``, or
            ``certificate``.  ``ssl`` is not a valid transport—use ``use_ssl``
            to control the connection scheme instead.

    Returns:
        INI-formatted inventory string ready to save as ``inventory/hosts``.

    """
    host_list = hosts or ["windows-host1.example.com"]
    scheme = "https" if use_ssl else "http"

    lines = ["[windows]"]
    for h in host_list:
        lines.append(h)

    lines += [
        "",
        "[windows:vars]",
        "ansible_connection=winrm",
        f"ansible_port={winrm_port}",
        f"ansible_winrm_scheme={scheme}",
        f"ansible_winrm_transport={winrm_transport}",
        "ansible_winrm_server_cert_validation="
        + ("validate" if validate_certs else "ignore"),
        "ansible_winrm_operation_timeout_sec=60",
        "ansible_winrm_read_timeout_sec=70",
        "# ansible_user=Administrator",
        "# ansible_password={{ vault_windows_password }}",
    ]

    return "\n".join(lines) + "\n"


def generate_windows_group_vars(
    ansible_user: str = "Administrator",
    winrm_port: int = 5986,
    use_ssl: bool = True,
    validate_certs: bool = False,
    winrm_transport: str = "ntlm",
) -> str:
    """
    Generate ``group_vars/windows.yml`` for WinRM connection settings.

    Produces a YAML file suitable for ``group_vars/windows.yml`` that
    centralises connection variables for Windows managed nodes.

    Args:
        ansible_user: Default Windows user for Ansible to connect as.
        winrm_port: WinRM port (5986 for HTTPS, 5985 for HTTP).
        use_ssl: Whether to use HTTPS WinRM transport.
        validate_certs: Whether to validate the WinRM SSL certificate.
            Typically ``False`` for self-signed certs.
        winrm_transport: WinRM authentication transport method.  Valid values
            are ``ntlm`` (default), ``kerberos``, ``basic``, ``credssp``, or
            ``certificate``.  ``ssl`` is not a valid transport—use ``use_ssl``
            to control the connection scheme instead.

    Returns:
        YAML string for ``group_vars/windows.yml``.

    """
    scheme = "https" if use_ssl else "http"
    group_vars: dict[str, Any] = {
        "ansible_connection": "winrm",
        "ansible_user": ansible_user,
        "ansible_password": "{{ vault_windows_password }}",
        "ansible_port": winrm_port,
        "ansible_winrm_scheme": scheme,
        "ansible_winrm_transport": winrm_transport,
        "ansible_winrm_server_cert_validation": (
            "validate" if validate_certs else "ignore"
        ),
        "ansible_winrm_operation_timeout_sec": 60,
        "ansible_winrm_read_timeout_sec": 70,
        "ansible_become": False,
        "ansible_become_method": "runas",
        "ansible_become_user": "SYSTEM",
    }

    header = (
        "---\n"
        "# group_vars/windows.yml\n"
        "# WinRM connection settings for all Windows managed nodes.\n"
        "# Sensitive values (passwords) should be stored in Ansible Vault.\n\n"
    )
    return header + cast(
        str,
        yaml.dump(group_vars, default_flow_style=False, allow_unicode=True),
    )


def generate_ansible_requirements(
    parsed_ir: dict[str, Any] | None = None,
) -> str:
    """
    Generate ``requirements.yml`` listing required Ansible collections.

    Examines the parsed IR to determine which collections are needed and
    produces a ``requirements.yml`` file that can be installed with
    ``ansible-galaxy collection install -r requirements.yml``.

    Args:
        parsed_ir: Optional parsed IR dict (from
            :func:`souschef.parsers.powershell.parse_powershell_content`
            internals).  When ``None``, all collections are included.

    Returns:
        YAML string for ``requirements.yml``.

    """
    action_types: set[str] = set()
    if parsed_ir:
        for action in parsed_ir.get("actions", []):
            action_types.add(action.get("action_type", ""))

    seen: set[str] = set()
    collections: list[dict[str, str]] = []

    for col in _REQUIRED_COLLECTIONS:
        name = col["name"]
        if name not in seen:
            collections.append(col.copy())
            seen.add(name)

    for action_type, col in _CONDITIONAL_COLLECTIONS.items():
        name = col["name"]
        if (parsed_ir is None or action_type in action_types) and name not in seen:
            collections.append(col.copy())
            seen.add(name)

    requirements: dict[str, Any] = {"collections": collections}
    header = (
        "---\n"
        "# requirements.yml\n"
        "# Install with: ansible-galaxy collection install -r requirements.yml\n\n"
    )
    return header + cast(
        str,
        yaml.dump(requirements, default_flow_style=False, allow_unicode=True),
    )


def generate_powershell_role_structure(
    parsed_ir: dict[str, Any],
    role_name: str = "windows_provisioning",
    playbook_name: str = "site",
    hosts: str = "windows",
) -> dict[str, str]:
    """
    Generate a complete Ansible Role directory structure from a parsed IR.

    Produces all files for a production-ready Ansible role including tasks,
    handlers, defaults, vars, meta and README.  Each dict entry maps a
    relative file path to its content.

    Args:
        parsed_ir: Parsed IR dict (from
            :func:`souschef.parsers.powershell.parse_powershell_content`
            internals).
        role_name: Name of the role directory (used in paths and metadata).
        playbook_name: Base name for the top-level playbook file.
        hosts: Ansible inventory host/group pattern.

    Returns:
        Ordered dict mapping relative path → file content for the following
        files::

            roles/<role_name>/tasks/main.yml
            roles/<role_name>/handlers/main.yml
            roles/<role_name>/defaults/main.yml
            roles/<role_name>/vars/main.yml
            roles/<role_name>/meta/main.yml
            roles/<role_name>/README.md
            <playbook_name>.yml
            inventory/hosts
            group_vars/windows.yml
            requirements.yml

    """
    from souschef.converters.powershell import _action_to_task

    actions = parsed_ir.get("actions", [])
    source = parsed_ir.get("source", _UNKNOWN_SOURCE)

    tasks: list[dict[str, Any]] = []
    handlers: list[dict[str, Any]] = []
    handler_names: set[str] = set()
    warnings: list[str] = []
    default_vars: dict[str, Any] = {}

    for action in actions:
        task, warning = _action_to_task(action)
        if warning:
            warnings.append(warning)
        _apply_role_handlers_for_action(action, task, handlers, handler_names)

        tasks.append(task)

    tasks_yaml = yaml.dump(tasks, default_flow_style=False, allow_unicode=True)
    handlers_yaml = yaml.dump(
        handlers or [{"name": _REBOOT_HANDLER_NAME, "ansible.windows.win_reboot": {}}],
        default_flow_style=False,
        allow_unicode=True,
    )
    defaults_yaml = yaml.dump(
        default_vars or {"# role_variable": "default_value"},
        default_flow_style=False,
        allow_unicode=True,
    )
    vars_yaml = "---\n# vars/main.yml\n# Define sensitive variables in Ansible Vault.\n"

    meta_data: dict[str, Any] = {
        "galaxy_info": {
            "role_name": role_name,
            "author": "souschef",
            "description": f"Migrated from PowerShell: {source}",
            "min_ansible_version": "2.14",
            "platforms": [{"name": "Windows", "versions": ["all"]}],
            "galaxy_tags": ["windows", "migration", "powershell"],
        },
        "dependencies": [],
    }
    meta_yaml = yaml.dump(meta_data, default_flow_style=False, allow_unicode=True)

    readme = _build_role_readme(role_name, source, actions, warnings)

    top_playbook = yaml.dump(
        [
            {
                "name": f"Windows provisioning from PowerShell: {source}",
                "hosts": hosts,
                "gather_facts": False,
                "roles": [role_name],
            }
        ],
        default_flow_style=False,
        allow_unicode=True,
    )

    inventory = generate_windows_inventory()
    group_vars = generate_windows_group_vars()
    requirements = generate_ansible_requirements(parsed_ir)

    rp = f"roles/{role_name}"
    return {
        f"{rp}/tasks/main.yml": f"---\n{tasks_yaml}",
        f"{rp}/handlers/main.yml": f"---\n{handlers_yaml}",
        f"{rp}/defaults/main.yml": f"---\n{defaults_yaml}",
        f"{rp}/vars/main.yml": vars_yaml,
        f"{rp}/meta/main.yml": f"---\n{meta_yaml}",
        f"{rp}/README.md": readme,
        f"{playbook_name}.yml": top_playbook,
        "inventory/hosts": inventory,
        "group_vars/windows.yml": group_vars,
        "requirements.yml": requirements,
    }


def generate_powershell_awx_job_template(
    parsed_ir: dict[str, Any],
    job_template_name: str = "Windows PowerShell Migration",
    playbook: str = "site.yml",
    inventory: str = "windows-inventory",
    project: str = "windows-migration-project",
    credential_name: str = _DEFAULT_WINRM_CREDENTIAL_NAME,
    environment: str = "production",
    include_survey: bool = True,
) -> str:
    """
    Generate an AWX / AAP Windows job template configuration.

    Produces a JSON configuration importable via ``awx-cli`` or the AWX/AAP
    REST API, pre-configured for WinRM-based Windows automation.

    Args:
        parsed_ir: Parsed IR dict used to derive survey fields and extra vars.
        job_template_name: Display name for the AWX job template.
        playbook: Playbook filename relative to the project root.
        inventory: Inventory name or ID in AWX.
        project: Project name or ID in AWX.
        credential_name: Windows credential name in AWX (Machine credential with
            WinRM settings).
        environment: Target environment label (used in template description).
        include_survey: Whether to generate a survey spec from script variables.

    Returns:
        Formatted text block with the job template JSON, CLI import command,
        and a summary of detected actions.

    """
    actions = parsed_ir.get("actions", [])
    source = parsed_ir.get("source", _UNKNOWN_SOURCE)
    metrics = parsed_ir.get("metrics", {})

    extra_vars = _extract_extra_vars(actions)

    survey_spec = _build_survey_spec(extra_vars) if include_survey else {}

    job_template: dict[str, Any] = {
        "name": job_template_name,
        "description": (
            f"Windows automation migrated from PowerShell – "
            f"source: {source} – environment: {environment}"
        ),
        "job_type": "run",
        "project": project,
        "playbook": playbook,
        "inventory": inventory,
        "credential": credential_name,
        "verbosity": 1,
        "become_enabled": True,
        "ask_variables_on_launch": True,
        "ask_limit_on_launch": True,
        "ask_tags_on_launch": False,
        "ask_skip_tags_on_launch": False,
        "ask_job_type_on_launch": False,
        "ask_verbosity_on_launch": False,
        "ask_inventory_on_launch": False,
        "ask_credential_on_launch": False,
        "survey_enabled": include_survey and bool(survey_spec),
        "extra_vars": json.dumps(extra_vars, indent=2) if extra_vars else "{}",
        "survey_spec": survey_spec if include_survey else {},
        "labels": ["windows", "powershell-migration", environment],
    }

    cli_cmd = (
        f"awx-cli job_templates create \\\n"
        f'    --name "{job_template["name"]}" \\\n'
        f'    --project "{job_template["project"]}" \\\n'
        f'    --playbook "{job_template["playbook"]}" \\\n'
        f'    --inventory "{job_template["inventory"]}" \\\n'
        f'    --credential "{job_template["credential"]}" \\\n'
        f"    --job_type run \\\n"
        f"    --verbosity 1 \\\n"
        f"    --become-enabled true\n"
    )

    summary_lines = ["Action type breakdown:"]
    for category, count in metrics.items():
        if not category.startswith("total") and not category.startswith("skipped"):
            summary_lines.append(f"  {category}: {count}")

    return (
        f"# AWX/AAP Windows Job Template Configuration\n"
        f"# Generated from PowerShell: {source}\n\n"
        f"## Job Template JSON:\n"
        f"```json\n{json.dumps(job_template, indent=2)}\n```\n\n"
        f"## CLI Import Command:\n"
        f"```bash\n{cli_cmd}```\n\n"
        f"## Script Analysis Summary:\n" + "\n".join(summary_lines) + "\n"
    )


def analyze_powershell_migration_fidelity(
    parsed_ir: dict[str, Any],
) -> str:
    """
    Analyse migration fidelity and produce a structured report.

    Calculates the percentage of PowerShell actions that can be automatically
    mapped to idiomatic Ansible modules (vs. ``win_shell`` fallbacks), lists
    actions needing manual review, and provides actionable next steps.

    Args:
        parsed_ir: Parsed IR dict from
            :func:`souschef.parsers.powershell.parse_powershell_content`.

    Returns:
        JSON string with the following keys:

        - ``fidelity_score``: Percentage (0-100) of actions fully automated.
        - ``total_actions``: Total number of actions.
        - ``automated_actions``: Number of high-confidence idiomatic mappings.
        - ``fallback_actions``: Number of ``win_shell`` fallbacks.
        - ``review_required``: List of action dicts needing manual review.
        - ``summary``: Human-readable summary string.
        - ``recommendations``: List of actionable recommendation strings.

    """
    actions = parsed_ir.get("actions", [])
    source = parsed_ir.get("source", _UNKNOWN_SOURCE)
    metrics = parsed_ir.get("metrics", {})

    total = len(actions)
    if total == 0:
        return json.dumps(
            {
                "fidelity_score": 100,
                "total_actions": 0,
                "automated_actions": 0,
                "fallback_actions": 0,
                "review_required": [],
                "summary": "No actions found in script.",
                "recommendations": [],
                "source": source,
            },
            indent=2,
        )

    automated = 0
    fallback = 0
    review_required: list[dict[str, Any]] = []

    for action in actions:
        atype = action.get("action_type", "win_shell")
        if atype == "win_shell":
            fallback += 1
        elif atype in _HIGH_FIDELITY_TYPES:
            automated += 1
            if atype in _REVIEW_REQUIRED_TYPES:
                review_required.append(
                    {
                        "action_type": atype,
                        "source_line": action.get("source_line"),
                        "raw": action.get("raw", ""),
                        "reason": _review_reason(atype),
                    }
                )
        else:
            fallback += 1

    fidelity = round((automated / total) * 100) if total > 0 else 0
    manual_count = fallback + len(review_required)

    recommendations = _build_recommendations(
        fidelity, fallback, review_required, metrics
    )

    summary = (
        f"Migration fidelity: {fidelity}% automated "
        f"({automated}/{total} actions use idiomatic Ansible modules). "
        f"{manual_count} actions require manual review."
    )

    return json.dumps(
        {
            "fidelity_score": fidelity,
            "total_actions": total,
            "automated_actions": automated,
            "fallback_actions": fallback,
            "review_required": review_required,
            "summary": summary,
            "recommendations": recommendations,
            "source": source,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_role_readme(
    role_name: str,
    source: str,
    actions: list[dict[str, Any]],
    warnings: list[str],
) -> str:
    """Build a README.md for the generated role."""
    action_summary = "\n".join(
        f"- Line {a.get('source_line', '?')}: `{a.get('action_type', 'unknown')}`"
        for a in actions
    )
    warnings_section = (
        "\n".join(f"- {w}" for w in warnings) if warnings else "_No warnings._"
    )

    return f"""# {role_name}

Ansible role auto-generated by **SousChef** from PowerShell provisioning script.

**Source:** `{source}`

## Actions Converted ({len(actions)})

{action_summary or "_No actions detected._"}

## Warnings

{warnings_section}

## Requirements

- Ansible >= 2.14
- `ansible.windows` >= 2.4.0
- `community.windows` >= 2.2.0
- WinRM configured on target hosts (see `group_vars/windows.yml`)

## Role Variables

See `defaults/main.yml` for tuneable variables.

## Usage

```yaml
- hosts: windows
  gather_facts: false
  roles:
    - {role_name}
```

## License

MIT
"""


def _extract_extra_vars(actions: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract candidate extra_vars from parsed actions."""
    extra: dict[str, Any] = {}
    for action in actions:
        atype = action.get("action_type", "")
        params = action.get("params", {})
        if atype in {"environment_set"}:
            name = params.get("name", "")
            if name:
                var_name = re.sub(r"\W", "_", name).lower()
                extra[var_name] = params.get("value", "")
        elif atype in {"chocolatey_install"}:
            pkg = params.get("package_name", "")
            if pkg:
                var_name = re.sub(r"^\d+", "", re.sub(r"\W", "_", pkg).lower())
                extra[f"{var_name}_version"] = "latest"
    return extra


def _apply_role_handlers_for_action(
    action: dict[str, Any],
    task: dict[str, Any],
    handlers: list[dict[str, Any]],
    handler_names: set[str],
) -> None:
    """Attach handler notifications for actions that need orchestration."""
    action_type = action.get("action_type")

    if action_type in {"windows_feature_install", "windows_feature_remove"}:
        task["notify"] = _REBOOT_HANDLER_NAME
        if _REBOOT_HANDLER_NAME not in handler_names:
            handlers.append(
                {
                    "name": _REBOOT_HANDLER_NAME,
                    "ansible.windows.win_reboot": {
                        "reboot_timeout": 300,
                        "msg": "Rebooting after Windows feature change",
                    },
                    "listen": _REBOOT_HANDLER_NAME,
                }
            )
            handler_names.add(_REBOOT_HANDLER_NAME)
        return

    if action_type != "windows_service_configure":
        return

    svc = action.get("params", {}).get("service_name", "")
    handler_name = f"Restart {svc}"
    if svc and handler_name not in handler_names:
        handlers.append(
            {
                "name": handler_name,
                "ansible.windows.win_service": {
                    "name": svc,
                    "state": "restarted",
                },
                "listen": handler_name,
            }
        )
        handler_names.add(handler_name)
    if "notify" not in task:
        task["notify"] = handler_name


def _build_survey_spec(extra_vars: dict[str, Any]) -> dict[str, Any]:
    """Build an AWX survey spec from extra_vars candidates."""
    if not extra_vars:
        return {}

    spec: list[dict[str, Any]] = []
    for idx, (key, default_val) in enumerate(extra_vars.items()):
        spec.append(
            {
                "question_name": key.replace("_", " ").title(),
                "question_description": f"Value for {key}",
                "variable": key,
                "type": "text",
                "required": False,
                "default": str(default_val),
                "min": 0,
                "max": 1024,
            }
        )
        if idx >= 9:  # limit to 10 survey fields
            break

    return {"name": "Migration Parameters", "description": "", "spec": spec}


def _review_reason(action_type: str) -> str:
    """Return a human-readable reason why an action requires review."""
    reasons: dict[str, str] = {
        "firewall_rule_create": (
            "Protocol, direction, port, and action must be "
            "manually specified in the generated task."
        ),
        "acl_set": (
            "ACE user, rights type, and propagation flags must be set manually."
        ),
        "certificate_import": (
            "Certificate store location (LocalMachine/CurrentUser) "
            "and thumbprint must be verified."
        ),
        "winrm_enable": (
            "WinRM should already be enabled if Ansible can connect; "
            "task may be redundant."
        ),
        "iis_website_create": (
            "Application pool, bindings, physical path, and "
            "authentication settings must be completed manually."
        ),
        "scheduled_task_register": (
            "Task action, trigger, principal, and schedule must be completed manually."
        ),
    }
    return reasons.get(action_type, "Manual review recommended.")


def _build_recommendations(
    fidelity: int,
    fallback: int,
    review_required: list[dict[str, Any]],
    metrics: dict[str, int],
) -> list[str]:
    """Build actionable recommendation strings based on analysis."""
    recs: list[str] = []

    if fidelity == 100:
        recs.append(
            "Excellent: all actions mapped to idiomatic Ansible modules. "
            "Run ansible-lint on the generated playbook before deploying."
        )
    elif fidelity >= 80:
        recs.append(
            f"Good fidelity ({fidelity}%). Review win_shell fallbacks and "
            "replace with idiomatic modules where possible."
        )
    elif fidelity >= 50:
        recs.append(
            f"Moderate fidelity ({fidelity}%). Many commands use win_shell "
            "fallbacks. Consider refactoring or adding custom modules."
        )
    else:
        recs.append(
            f"Low fidelity ({fidelity}%). Most commands were not recognised. "
            "Manual migration recommended for this script."
        )

    if fallback > 0:
        recs.append(
            f"{fallback} win_shell fallback(s) detected. "
            "Test each with ansible.windows.win_command where appropriate."
        )

    if review_required:
        types = {r["action_type"] for r in review_required}
        recs.append(
            "Manual completion required for: "
            + ", ".join(sorted(types))
            + ". See review_required list for details."
        )

    if metrics.get("windows_feature", 0) > 0:
        recs.append(
            "Windows feature changes may require a reboot. "
            "The generated role includes a win_reboot handler."
        )

    recs.append(
        "Run: ansible-galaxy collection install -r requirements.yml "
        "before executing the generated playbook."
    )

    return recs
