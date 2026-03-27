"""PowerShell Migration Page for SousChef UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # pragma: no cover

from souschef.orchestrators.powershell import (
    analyze_powershell_migration_fidelity,
    convert_powershell_content_to_ansible,
    generate_ansible_requirements,
    generate_powershell_awx_job_template,
    generate_powershell_role_structure,
    generate_windows_group_vars,
    generate_windows_inventory,
    parse_powershell_content,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PLACEHOLDER_SCRIPT = """\
# Example PowerShell provisioning script
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
Start-Service -Name W3SVC
Set-Service -Name W3SVC -StartupType Automatic
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\MyApp' -Name 'Version' -Value '1.0'
New-Item -Path 'C:\\MyApp\\Logs' -ItemType Directory
New-LocalUser -Name 'svc_myapp'
New-NetFirewallRule -DisplayName 'MyApp HTTP' -Direction Inbound -Port 80
Register-ScheduledTask -TaskName 'MyApp Backup'
[System.Environment]::SetEnvironmentVariable('APP_HOME', 'C:\\MyApp', 'Machine')
choco install notepadplusplus
"""

_LABEL_SCRIPT_INPUT = "PowerShell Script"
_LABEL_PLAYBOOK_NAME = "Playbook Name"
_LABEL_HOSTS = "Target Hosts"
_LABEL_ROLE_NAME = "Role Name"
_LABEL_PARSE_BTN = "Parse Script"
_LABEL_CONVERT_BTN = "Convert to Ansible"
_LABEL_ENTERPRISE_BTN = "Generate Enterprise Artefacts"
_LABEL_ACTIONS_TAB = "Parsed Actions"
_LABEL_PLAYBOOK_TAB = "Ansible Playbook"
_LABEL_WARNINGS_TAB = "Warnings"
_LABEL_ROLE_TAB = "Ansible Role"
_LABEL_INVENTORY_TAB = "Inventory"
_LABEL_REQUIREMENTS_TAB = "requirements.yml"
_LABEL_JOB_TEMPLATE_TAB = "AWX Job Template"
_LABEL_FIDELITY_TAB = "Migration Fidelity"
_MIME_YAML = "text/yaml"


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def show_powershell_migration_page() -> None:
    """Render the PowerShell Migration page."""
    if st is None:
        return  # pragma: no cover

    _display_intro()
    script_content, playbook_name, hosts, role_name = _render_inputs()
    _render_action_buttons(script_content, playbook_name, hosts, role_name)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _display_intro() -> None:
    """Render the page title and introduction."""
    if st is None:
        return  # pragma: no cover

    st.title("PowerShell to Ansible Migration")
    st.markdown(
        """
        Convert PowerShell provisioning scripts to idiomatic Ansible playbooks and
        complete enterprise automation artefacts targeting Windows managed nodes on
        **Ansible Automation Platform (AAP) / AWX**.

        **Supported actions:**
        Windows Features · Services · Registry · Files · MSI/Chocolatey ·
        Users & Groups · Firewall Rules · Scheduled Tasks · Environment Variables ·
        Certificates · WinRM · IIS · DNS · ACL

        Unrecognised commands fall back to `ansible.windows.win_shell` with warnings.
        """
    )


def _render_inputs() -> tuple[str, str, str, str]:
    """
    Render script input area and options.

    Returns:
        Tuple of (script_content, playbook_name, hosts, role_name).

    """
    if st is None:
        return "", "", "", ""  # pragma: no cover

    script_content: str = st.text_area(
        _LABEL_SCRIPT_INPUT,
        value=_PLACEHOLDER_SCRIPT,
        height=250,
        help="Paste your PowerShell provisioning script here.",
        key="ps_script_content",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        playbook_name: str = st.text_input(
            _LABEL_PLAYBOOK_NAME,
            value="powershell_migration",
            help="Name for the generated Ansible play.",
            key="ps_playbook_name",
        )
    with col2:
        hosts: str = st.text_input(
            _LABEL_HOSTS,
            value="windows",
            help="Ansible inventory group or host pattern.",
            key="ps_hosts",
        )
    with col3:
        role_name: str = st.text_input(
            _LABEL_ROLE_NAME,
            value="windows_provisioning",
            help="Name for the generated Ansible role.",
            key="ps_role_name",
        )

    return script_content, playbook_name, hosts, role_name


def _render_action_buttons(
    script_content: str, playbook_name: str, hosts: str, role_name: str
) -> None:
    """Render Parse, Convert, and Enterprise buttons and display results."""
    if st is None:
        return  # pragma: no cover

    col_parse, col_convert, col_enterprise = st.columns(3)

    with col_parse:
        parse_clicked = st.button(
            _LABEL_PARSE_BTN, use_container_width=True, key="ps_parse_btn"
        )

    with col_convert:
        convert_clicked = st.button(
            _LABEL_CONVERT_BTN,
            use_container_width=True,
            type="primary",
            key="ps_convert_btn",
        )

    with col_enterprise:
        enterprise_clicked = st.button(
            _LABEL_ENTERPRISE_BTN,
            use_container_width=True,
            key="ps_enterprise_btn",
        )

    if parse_clicked:
        _handle_parse(script_content)

    if convert_clicked:
        _handle_convert(script_content, playbook_name, hosts)

    if enterprise_clicked:
        _handle_enterprise(script_content, playbook_name, hosts, role_name)

    # Persist results across reruns using session state
    if not parse_clicked and not convert_clicked and not enterprise_clicked:
        _display_stored_results()


# ---------------------------------------------------------------------------
# Result handlers
# ---------------------------------------------------------------------------


def _load_json_payload(raw_json: str, operation: str) -> dict[str, Any] | None:
    """Parse a JSON payload and surface UI-friendly errors when malformed."""
    if st is None:
        return None  # pragma: no cover

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        st.error(f"{operation} returned invalid JSON output.")
        st.text(raw_json)
        return None

    if not isinstance(payload, dict):
        st.error(f"{operation} returned an unexpected response shape.")
        return None

    return payload


def _handle_parse(script_content: str) -> None:
    """Parse the script and display structured actions."""
    if st is None:
        return  # pragma: no cover

    if not script_content.strip():
        st.warning("Please enter a PowerShell script to parse.")
        return

    with st.spinner("Parsing PowerShell script..."):
        result_json = parse_powershell_content(script_content)

    result = _load_json_payload(result_json, "Parse")
    if result is None:
        return

    st.session_state["ps_parse_result"] = result
    st.session_state["ps_convert_result"] = None
    st.session_state["ps_enterprise_result"] = None
    _display_parse_result(result)


def _handle_convert(script_content: str, playbook_name: str, hosts: str) -> None:
    """Convert the script and display the Ansible playbook."""
    if st is None:
        return  # pragma: no cover

    if not script_content.strip():
        st.warning("Please enter a PowerShell script to convert.")
        return

    with st.spinner("Converting to Ansible playbook..."):
        result_json = convert_powershell_content_to_ansible(
            script_content,
            playbook_name=playbook_name,
            hosts=hosts,
        )

    result = _load_json_payload(result_json, "Convert")
    if result is None:
        return

    st.session_state["ps_convert_result"] = result
    st.session_state["ps_parse_result"] = None
    st.session_state["ps_enterprise_result"] = None
    _display_convert_result(result)


def _handle_enterprise(
    script_content: str, playbook_name: str, hosts: str, role_name: str
) -> None:
    """Generate enterprise artefacts and display them."""
    if st is None:
        return  # pragma: no cover

    if not script_content.strip():
        st.warning("Please enter a PowerShell script.")
        return

    with st.spinner("Generating enterprise Ansible artefacts..."):
        parsed_raw = parse_powershell_content(script_content, "<inline>")
        parsed_ir = _load_json_payload(parsed_raw, "Parse")
        if parsed_ir is None:
            return

        fidelity_raw = analyze_powershell_migration_fidelity(parsed_ir)
        fidelity = _load_json_payload(fidelity_raw, "Fidelity analysis")
        if fidelity is None:
            return

        enterprise_result = {
            "parsed_ir": parsed_ir,
            "inventory": generate_windows_inventory(),
            "group_vars": generate_windows_group_vars(),
            "requirements": generate_ansible_requirements(parsed_ir),
            "role_files": generate_powershell_role_structure(
                parsed_ir,
                role_name=role_name,
                playbook_name=playbook_name,
                hosts=hosts,
            ),
            "job_template": generate_powershell_awx_job_template(
                parsed_ir,
                job_template_name=f"Windows: {playbook_name}",
                playbook=f"{playbook_name}.yml",
            ),
            "fidelity": fidelity,
        }

    st.session_state["ps_enterprise_result"] = enterprise_result
    st.session_state["ps_parse_result"] = None
    st.session_state["ps_convert_result"] = None
    _display_enterprise_result(enterprise_result)


def _display_stored_results() -> None:
    """Re-display previously computed results from session state."""
    if st is None:
        return  # pragma: no cover

    parse_result = st.session_state.get("ps_parse_result")
    convert_result = st.session_state.get("ps_convert_result")
    enterprise_result = st.session_state.get("ps_enterprise_result")

    if parse_result:
        _display_parse_result(parse_result)
    elif convert_result:
        _display_convert_result(convert_result)
    elif enterprise_result:
        _display_enterprise_result(enterprise_result)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def _display_parse_result(result: dict) -> None:
    """Display parsed actions and metrics."""
    metrics = result.get("metrics", {})
    actions = result.get("actions", [])
    warnings = result.get("warnings", [])

    _render_metrics_summary(metrics)

    tab_actions, tab_warnings = st.tabs([_LABEL_ACTIONS_TAB, _LABEL_WARNINGS_TAB])

    with tab_actions:
        _render_actions_table(actions)

    with tab_warnings:
        _render_warnings(warnings)


def _render_metrics_summary(metrics: dict) -> None:
    """Display a summary row of parsed action counts."""
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Windows Features", metrics.get("windows_feature", 0))
    col2.metric("Services", metrics.get("windows_service", 0))
    col3.metric("Registry", metrics.get("registry", 0))
    col4.metric("Files", metrics.get("file", 0))
    col5.metric("Packages", metrics.get("package", 0))
    col6.metric("Fallbacks", metrics.get("win_shell_fallback", 0))

    # Show enterprise metrics if present
    enterprise_keys = [
        "user",
        "firewall",
        "scheduled_task",
        "environment",
        "certificate",
        "other_enterprise",
    ]
    enterprise_vals = {
        k: metrics.get(k, 0) for k in enterprise_keys if metrics.get(k, 0) > 0
    }
    if enterprise_vals:
        cols = st.columns(len(enterprise_vals))
        for col, (key, val) in zip(cols, enterprise_vals.items(), strict=False):
            col.metric(key.replace("_", " ").title(), val)


def _render_actions_table(actions: list) -> None:
    """Render the parsed actions as expandable entries."""
    if not actions:
        st.info("No actions found in the script.")
        return

    for action in actions:
        action_type = action.get("action_type", "unknown")
        src_line = action.get("source_line", "?")
        confidence = action.get("confidence", "?")
        params = action.get("params", {})
        requires_elevation = action.get("requires_elevation", False)

        badge = "high" if confidence == "high" else "low"
        elevation_note = " (requires elevation)" if requires_elevation else ""

        with st.expander(
            f"Line {src_line}: {action_type}{elevation_note} [{badge} confidence]"
        ):
            st.json(params)
            st.caption(f"Raw: `{action.get('raw', '')}`")


def _render_warnings(warnings: list) -> None:
    """Render parsing warnings."""
    if not warnings:
        st.success("No warnings.")
        return

    for w in warnings:
        st.warning(w)


def _display_convert_result(result: dict) -> None:
    """Display converted Ansible playbook and statistics."""
    status = result.get("status", "error")
    if status == "error":
        st.error(f"Conversion failed: {result.get('error', 'Unknown error')}")
        return

    tasks_total = result.get("tasks_generated", 0)
    fallbacks = result.get("win_shell_fallbacks", 0)
    warnings = result.get("warnings", [])
    playbook_yaml = result.get("playbook_yaml", "")

    col1, col2, col3 = st.columns(3)
    col1.metric("Tasks Generated", tasks_total)
    col2.metric("win_shell Fallbacks", fallbacks)
    col3.metric("Warnings", len(warnings))

    tab_playbook, tab_warnings = st.tabs([_LABEL_PLAYBOOK_TAB, _LABEL_WARNINGS_TAB])

    with tab_playbook:
        st.code(playbook_yaml, language="yaml")
        st.download_button(
            "Download Playbook",
            data=playbook_yaml,
            file_name="playbook.yml",
            mime=_MIME_YAML,
            key="ps_download_playbook",
        )

    with tab_warnings:
        _render_warnings(warnings)


def _display_enterprise_result(enterprise_result: dict) -> None:
    """Display all enterprise artefacts across tabs."""
    fidelity = enterprise_result.get("fidelity", {})
    score = fidelity.get("fidelity_score", 0)
    total = fidelity.get("total_actions", 0)
    automated = fidelity.get("automated_actions", 0)
    fallbacks = fidelity.get("fallback_actions", 0)
    role_files = enterprise_result.get("role_files", {})

    # Top-level fidelity metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fidelity Score", f"{score}%")
    col2.metric("Total Actions", total)
    col3.metric("Automated", automated)
    col4.metric("Fallbacks", fallbacks)

    (
        tab_fidelity,
        tab_role,
        tab_inventory,
        tab_requirements,
        tab_job_template,
    ) = st.tabs(
        [
            _LABEL_FIDELITY_TAB,
            _LABEL_ROLE_TAB,
            _LABEL_INVENTORY_TAB,
            _LABEL_REQUIREMENTS_TAB,
            _LABEL_JOB_TEMPLATE_TAB,
        ]
    )

    with tab_fidelity:
        _render_fidelity_report(fidelity)

    with tab_role:
        _render_role_files(role_files)

    with tab_inventory:
        inventory = enterprise_result.get("inventory", "")
        group_vars = enterprise_result.get("group_vars", "")
        st.subheader("inventory/hosts")
        st.code(inventory, language="ini")
        st.download_button(
            "Download inventory/hosts",
            data=inventory,
            file_name="hosts",
            mime="text/plain",
            key="ps_download_inventory",
        )
        st.subheader("group_vars/windows.yml")
        st.code(group_vars, language="yaml")
        st.download_button(
            "Download group_vars/windows.yml",
            data=group_vars,
            file_name="windows.yml",
            mime=_MIME_YAML,
            key="ps_download_group_vars",
        )

    with tab_requirements:
        requirements = enterprise_result.get("requirements", "")
        st.code(requirements, language="yaml")
        st.download_button(
            "Download requirements.yml",
            data=requirements,
            file_name="requirements.yml",
            mime=_MIME_YAML,
            key="ps_download_requirements",
        )

    with tab_job_template:
        job_template = enterprise_result.get("job_template", "")
        st.code(job_template, language="markdown")
        st.download_button(
            "Download Job Template",
            data=job_template,
            file_name="job_template.md",
            mime="text/markdown",
            key="ps_download_job_template",
        )


def _render_fidelity_report(fidelity: dict) -> None:
    """Render the migration fidelity analysis."""
    st.markdown(f"**{fidelity.get('summary', '')}**")

    recommendations = fidelity.get("recommendations", [])
    if recommendations:
        st.subheader("Recommendations")
        for rec in recommendations:
            st.info(rec)

    review_required = fidelity.get("review_required", [])
    if review_required:
        st.subheader("Actions Requiring Manual Review")
        for item in review_required:
            with st.expander(
                f"Line {item.get('source_line', '?')}: {item.get('action_type', '?')}"
            ):
                st.warning(item.get("reason", ""))
                st.caption(f"Raw: `{item.get('raw', '')}`")


def _render_role_files(role_files: dict) -> None:
    """Render role file structure with code viewers and download buttons."""
    if not role_files:
        st.info("No role files generated.")
        return

    st.caption(f"Generated {len(role_files)} files for the Ansible role.")

    for rel_path, content in role_files.items():
        lang = "yaml"
        if rel_path.endswith(".md"):
            lang = "markdown"
        elif rel_path.endswith("hosts"):
            lang = "ini"

        with st.expander(rel_path):
            st.code(content, language=lang)
            st.download_button(
                f"Download {Path(rel_path).name}",
                data=content,
                file_name=Path(rel_path).name,
                mime="text/plain",
                key=f"ps_download_{rel_path.replace('/', '_').replace('.', '_')}",
            )
