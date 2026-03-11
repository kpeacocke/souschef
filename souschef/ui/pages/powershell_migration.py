"""PowerShell Migration Page for SousChef UI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # pragma: no cover

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.converters.powershell import convert_powershell_content_to_ansible
from souschef.parsers.powershell import parse_powershell_content

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PLACEHOLDER_SCRIPT = """\
# Example PowerShell provisioning script
Install-WindowsFeature -Name Web-Server -IncludeManagementTools
Start-Service -Name W3SVC
Set-ItemProperty -Path 'HKLM:\\SOFTWARE\\MyApp' -Name 'Version' -Value '1.0'
New-Item -Path 'C:\\MyApp\\Logs' -ItemType Directory
choco install notepadplusplus
"""

_LABEL_SCRIPT_INPUT = "PowerShell Script"
_LABEL_PLAYBOOK_NAME = "Playbook Name"
_LABEL_HOSTS = "Target Hosts"
_LABEL_PARSE_BTN = "Parse Script"
_LABEL_CONVERT_BTN = "Convert to Ansible"
_LABEL_ACTIONS_TAB = "Parsed Actions"
_LABEL_PLAYBOOK_TAB = "Ansible Playbook"
_LABEL_WARNINGS_TAB = "Warnings"


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def show_powershell_migration_page() -> None:
    """Render the PowerShell Migration page."""
    _display_intro()
    script_content, playbook_name, hosts = _render_inputs()
    _render_action_buttons(script_content, playbook_name, hosts)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def _display_intro() -> None:
    """Render the page title and introduction."""
    st.title("PowerShell to Ansible Migration")
    st.markdown(
        """
        Convert PowerShell provisioning scripts to idiomatic Ansible playbooks
        targeting Windows managed nodes.

        **Supported actions:**
        - Windows Features (`Install-WindowsFeature`, `Enable-WindowsOptionalFeature`)
        - Windows Services (`Start-Service`, `Stop-Service`, `Set-Service`,
          `New-Service`)
        - Registry edits (`Set-ItemProperty`, `New-Item`, `Remove-Item`
          on HKLM/HKCU)
        - File operations (`Copy-Item`, `New-Item -ItemType Directory`,
          `Set-Content`, `Remove-Item`)
        - MSI installs (`msiexec`, `Start-Process msiexec`)
        - Chocolatey packages (`choco install` / `choco uninstall`)

        Unrecognised commands fall back to `ansible.windows.win_shell` with warnings.
        """
    )


def _render_inputs() -> tuple[str, str, str]:
    """Render script input area and options; return (content, playbook_name, hosts)."""
    script_content: str = st.text_area(
        _LABEL_SCRIPT_INPUT,
        value=_PLACEHOLDER_SCRIPT,
        height=250,
        help="Paste your PowerShell provisioning script here.",
        key="ps_script_content",
    )

    col1, col2 = st.columns(2)
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

    return script_content, playbook_name, hosts


def _render_action_buttons(
    script_content: str, playbook_name: str, hosts: str
) -> None:
    """Render Parse and Convert buttons and display results."""
    col_parse, col_convert = st.columns(2)

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

    if parse_clicked:
        _handle_parse(script_content)

    if convert_clicked:
        _handle_convert(script_content, playbook_name, hosts)

    # Persist results across reruns using session state
    if not parse_clicked and not convert_clicked:
        _display_stored_results()


# ---------------------------------------------------------------------------
# Result handlers
# ---------------------------------------------------------------------------


def _handle_parse(script_content: str) -> None:
    """Parse the script and display structured actions."""
    if not script_content.strip():
        st.warning("Please enter a PowerShell script to parse.")
        return

    with st.spinner("Parsing PowerShell script..."):
        result_json = parse_powershell_content(script_content)

    result = json.loads(result_json)
    st.session_state["ps_parse_result"] = result
    st.session_state["ps_convert_result"] = None
    _display_parse_result(result)


def _handle_convert(script_content: str, playbook_name: str, hosts: str) -> None:
    """Convert the script and display the Ansible playbook."""
    if not script_content.strip():
        st.warning("Please enter a PowerShell script to convert.")
        return

    with st.spinner("Converting to Ansible playbook..."):
        result_json = convert_powershell_content_to_ansible(
            script_content,
            playbook_name=playbook_name,
            hosts=hosts,
        )

    result = json.loads(result_json)
    st.session_state["ps_convert_result"] = result
    st.session_state["ps_parse_result"] = None
    _display_convert_result(result)


def _display_stored_results() -> None:
    """Re-display previously computed results from session state."""
    parse_result = st.session_state.get("ps_parse_result")
    convert_result = st.session_state.get("ps_convert_result")

    if parse_result:
        _display_parse_result(parse_result)
    elif convert_result:
        _display_convert_result(convert_result)


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
            mime="text/yaml",
            key="ps_download_playbook",
        )

    with tab_warnings:
        _render_warnings(warnings)
