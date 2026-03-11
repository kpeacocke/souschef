"""
Bash Script Migration page for the SousChef UI.

Provides an interactive interface for parsing Bash provisioning scripts
and converting them to Ansible playbooks.
"""

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

# Ensure the souschef package is importable from the UI context
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.converters.bash_to_ansible import convert_bash_content_to_ansible
from souschef.parsers.bash import parse_bash_script_content

# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def show_bash_migration_page() -> None:
    """Render the Bash Script Migration page."""
    st.title("Bash Script Migration")
    st.markdown(
        """
        Convert common provisioning-style Bash scripts into structured
        Ansible playbooks.  High-confidence patterns are mapped to
        dedicated Ansible modules; low-confidence sections fall back to
        ``ansible.builtin.shell`` with idempotency hints.
        """
    )

    _render_input_section()


# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------


def _render_input_section() -> None:
    """Render the script input area and action buttons."""
    tab_paste, tab_file = st.tabs(["Paste Script", "Upload File"])

    with tab_paste:
        _render_paste_tab()

    with tab_file:
        _render_upload_tab()


def _render_paste_tab() -> None:
    """Render the paste-script tab."""
    script_content = st.text_area(
        "Bash Script Content",
        height=300,
        placeholder="#!/bin/bash\napt-get install -y nginx\nsystemctl enable nginx\n",
        help="Paste your Bash script here.",
    )

    col_parse, col_convert = st.columns(2)
    with col_parse:
        do_parse = st.button("Analyse Script", use_container_width=True)
    with col_convert:
        do_convert = st.button("Convert to Ansible", use_container_width=True)

    if do_parse and script_content:
        _display_parse_results(script_content)
    elif do_convert and script_content:
        _display_conversion_results(script_content)
    elif (do_parse or do_convert) and not script_content:
        st.warning("Please enter a Bash script first.")


def _render_upload_tab() -> None:
    """Render the file-upload tab."""
    uploaded = st.file_uploader(
        "Upload Bash Script",
        type=["sh", "bash", "txt"],
        help="Upload a Bash script file (.sh, .bash, or .txt).",
    )

    if uploaded is not None:
        script_content = uploaded.read().decode("utf-8", errors="replace")
        st.code(script_content, language="bash")

        col_parse, col_convert = st.columns(2)
        with col_parse:
            do_parse = st.button("Analyse Uploaded Script", use_container_width=True)
        with col_convert:
            do_convert = st.button(
                "Convert Uploaded Script to Ansible", use_container_width=True
            )

        if do_parse:
            _display_parse_results(script_content)
        elif do_convert:
            _display_conversion_results(script_content, script_path=uploaded.name)


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------


def _display_parse_results(content: str) -> None:
    """Parse *content* and render the IR results."""
    ir = parse_bash_script_content(content)

    st.subheader("Analysis Results")

    _render_summary_metrics(ir)
    _render_packages(ir)
    _render_services(ir)
    _render_file_writes(ir)
    _render_downloads(ir)
    _render_idempotency_risks(ir)
    _render_shell_fallbacks(ir)


def _render_summary_metrics(ir: dict) -> None:  # type: ignore[type-arg]
    """Render high-level metric cards."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Packages", len(ir.get("packages", [])))
    with col2:
        st.metric("Services", len(ir.get("services", [])))
    with col3:
        st.metric("File Writes", len(ir.get("file_writes", [])))
    with col4:
        st.metric("Downloads", len(ir.get("downloads", [])))


def _render_packages(ir: dict) -> None:  # type: ignore[type-arg]
    """Render detected package install operations."""
    packages = ir.get("packages", [])
    if not packages:
        return
    st.subheader("Package Installs")
    for pkg in packages:
        pkg_display = ", ".join(pkg["packages"]) or pkg["raw"][:60]
        with st.expander(
            f"Line {pkg['line']}: {pkg['manager']} — {pkg_display}"
        ):
            st.write(f"**Ansible module:** `{pkg['ansible_module']}`")
            st.write(f"**Confidence:** {pkg['confidence']:.0%}")
            st.code(pkg["raw"], language="bash")


def _render_services(ir: dict) -> None:  # type: ignore[type-arg]
    """Render detected service control operations."""
    services = ir.get("services", [])
    if not services:
        return
    st.subheader("Service Control")
    for svc in services:
        with st.expander(
            f"Line {svc['line']}: {svc['manager']} {svc['action']} {svc['name']}"
        ):
            st.write("**Ansible module:** `ansible.builtin.service`")
            st.write(f"**Confidence:** {svc['confidence']:.0%}")
            st.code(svc["raw"], language="bash")


def _render_file_writes(ir: dict) -> None:  # type: ignore[type-arg]
    """Render detected file write operations."""
    file_writes = ir.get("file_writes", [])
    if not file_writes:
        return
    st.subheader("File Writes")
    for fw in file_writes:
        with st.expander(f"Line {fw['line']}: write to {fw['destination']}"):
            st.write("**Ansible module:** `ansible.builtin.copy`")
            st.write(f"**Confidence:** {fw['confidence']:.0%}")
            st.code(fw["raw"], language="bash")


def _render_downloads(ir: dict) -> None:  # type: ignore[type-arg]
    """Render detected download operations."""
    downloads = ir.get("downloads", [])
    if not downloads:
        return
    st.subheader("Downloads")
    for dl in downloads:
        with st.expander(
            f"Line {dl['line']}: {dl['tool']} {dl.get('url') or '(url not parsed)'}"
        ):
            st.write("**Ansible module:** `ansible.builtin.get_url`")
            st.write(f"**Confidence:** {dl['confidence']:.0%}")
            st.code(dl["raw"], language="bash")


def _render_idempotency_risks(ir: dict) -> None:  # type: ignore[type-arg]
    """Render idempotency risk warnings."""
    risks = ir.get("idempotency_risks", [])
    if not risks:
        return
    st.subheader("Idempotency Risks")
    for risk in risks:
        st.warning(
            f"**Line {risk['line']} [{risk['type']}]:** {risk['suggestion']}"
        )


def _render_shell_fallbacks(ir: dict) -> None:  # type: ignore[type-arg]
    """Render lines that will fall back to ansible.builtin.shell."""
    fallbacks = ir.get("shell_fallbacks", [])
    if not fallbacks:
        return
    st.subheader("Shell Fallbacks")
    st.info(
        f"{len(fallbacks)} line(s) will use `ansible.builtin.shell` as no "
        "direct module mapping was found."
    )
    for fb in fallbacks:
        with st.expander(f"Line {fb['line']}: {fb['raw'][:60]}"):
            st.code(fb["raw"], language="bash")
            st.warning(fb["warning"])


def _display_conversion_results(
    content: str,
    script_path: str = "script.sh",
) -> None:
    """Convert *content* and render the playbook output."""
    raw = convert_bash_content_to_ansible(content, script_path=script_path)
    data = json.loads(raw)

    if data.get("status") == "error":
        st.error(f"Conversion error: {data.get('error')}")
        return

    st.subheader("Generated Playbook")

    playbook_yaml = data.get("playbook_yaml", "")
    st.code(playbook_yaml, language="yaml")

    st.download_button(
        "Download Playbook",
        data=playbook_yaml,
        file_name="converted_playbook.yml",
        mime="text/yaml",
    )

    warnings = data.get("warnings", [])
    if warnings:
        st.subheader("Warnings")
        for w in warnings:
            st.warning(w)

    report = data.get("idempotency_report", {})
    total_risks = report.get("total_risks", 0)
    if total_risks:
        st.subheader("Idempotency Report")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Idempotency Risks", total_risks)
        with col2:
            st.metric("Shell Fallbacks", report.get("non_idempotent_tasks", 0))

        suggestions = report.get("suggestions", [])
        if suggestions:
            st.write("**Suggestions:**")
            for suggestion in suggestions:
                st.info(suggestion)
