"""
Bash Script Migration page for the SousChef UI.

Provides an interactive interface for parsing Bash provisioning scripts
and converting them to Ansible playbooks.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # pragma: no cover

from souschef.converters.bash_to_ansible import (
    convert_bash_content_to_ansible,
    generate_ansible_role_from_bash,
)
from souschef.parsers.bash import parse_bash_script_content

SHELL_FALLBACKS_LABEL = "Shell Fallbacks"

# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


def show_bash_migration_page() -> None:
    """Render the Bash Script Migration page."""
    if st is None:  # pragma: no cover
        return
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

    col_parse, col_convert, col_role = st.columns(3)
    with col_parse:
        do_parse = st.button("Analyse Script", use_container_width=True)
    with col_convert:
        do_convert = st.button("Convert to Ansible", use_container_width=True)
    with col_role:
        do_role = st.button("Generate Ansible Role", use_container_width=True)

    if do_parse and script_content:
        _display_parse_results(script_content)
    elif do_convert and script_content:
        _display_conversion_results(script_content)
    elif do_role and script_content:
        _display_role_results(script_content)
    elif (do_parse or do_convert or do_role) and not script_content:
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

        col_parse, col_convert, col_role = st.columns(3)
        with col_parse:
            do_parse = st.button("Analyse Uploaded Script", use_container_width=True)
        with col_convert:
            do_convert = st.button(
                "Convert Uploaded Script to Ansible", use_container_width=True
            )
        with col_role:
            do_role = st.button(
                "Generate Role from Uploaded Script", use_container_width=True
            )

        if do_parse:
            _display_parse_results(script_content)
        elif do_convert:
            _display_conversion_results(script_content, script_path=uploaded.name)
        elif do_role:
            _display_role_results(script_content, script_path=uploaded.name)


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------


def _display_parse_results(content: str) -> None:
    """Parse *content* and render the IR results."""
    ir = parse_bash_script_content(content)

    st.subheader("Analysis Results")

    _render_cm_escapes(ir)
    _render_sensitive_data(ir)
    _render_summary_metrics(ir)
    _render_packages(ir)
    _render_services(ir)
    _render_file_writes(ir)
    _render_downloads(ir)
    _render_users(ir)
    _render_groups(ir)
    _render_file_perms(ir)
    _render_git_ops(ir)
    _render_archives(ir)
    _render_sed_ops(ir)
    _render_cron_jobs(ir)
    _render_firewall_rules(ir)
    _render_hostname_ops(ir)
    _render_env_vars(ir)
    _render_idempotency_risks(ir)
    _render_shell_fallbacks(ir)


def _render_summary_metrics(ir: dict[str, Any]) -> None:
    """Render high-level metric cards in two rows."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Packages", len(ir.get("packages", [])))
    with col2:
        st.metric("Services", len(ir.get("services", [])))
    with col3:
        st.metric("File Writes", len(ir.get("file_writes", [])))

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Downloads", len(ir.get("downloads", [])))
    with col5:
        users_groups = len(ir.get("users", [])) + len(ir.get("groups", []))
        st.metric("Users & Groups", users_groups)
    with col6:
        security_risks = len(ir.get("sensitive_data", [])) + len(
            ir.get("cm_escapes", [])
        )
        st.metric("Security Risks", security_risks)


def _render_packages(ir: dict[str, Any]) -> None:
    """Render detected package install operations."""
    packages = ir.get("packages", [])
    if not packages:
        return
    st.subheader("Package Installs")
    for pkg in packages:
        pkg_display = ", ".join(pkg["packages"]) or pkg["raw"][:60]
        with st.expander(f"Line {pkg['line']}: {pkg['manager']} — {pkg_display}"):
            st.write(f"**Ansible module:** `{pkg['ansible_module']}`")
            st.write(f"**Confidence:** {pkg['confidence']:.0%}")
            st.code(pkg["raw"], language="bash")


def _render_services(ir: dict[str, Any]) -> None:
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


def _render_file_writes(ir: dict[str, Any]) -> None:
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


def _render_downloads(ir: dict[str, Any]) -> None:
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


def _render_idempotency_risks(ir: dict[str, Any]) -> None:
    """Render idempotency risk warnings."""
    risks = ir.get("idempotency_risks", [])
    if not risks:
        return
    st.subheader("Idempotency Risks")
    for risk in risks:
        st.warning(f"**Line {risk['line']} [{risk['type']}]:** {risk['suggestion']}")


def _render_shell_fallbacks(ir: dict[str, Any]) -> None:
    """Render lines that will fall back to ansible.builtin.shell."""
    fallbacks = ir.get("shell_fallbacks", [])
    if not fallbacks:
        return
    st.subheader(SHELL_FALLBACKS_LABEL)
    st.info(
        f"{len(fallbacks)} line(s) will use `ansible.builtin.shell` as no "
        "direct module mapping was found."
    )
    for fb in fallbacks:
        with st.expander(f"Line {fb['line']}: {fb['raw'][:60]}"):
            st.code(fb["raw"], language="bash")
            st.warning(fb["warning"])


def _render_users(ir: dict[str, Any]) -> None:
    """Render detected user management operations."""
    users = ir.get("users", [])
    if not users:
        return
    st.subheader("User Management")
    for u in users:
        with st.expander(f"Line {u['line']}: [{u['action']}] {u['raw'][:60]}"):
            st.write("**Ansible module:** `ansible.builtin.user`")
            st.write(f"**Confidence:** {u['confidence']:.0%}")
            st.code(u["raw"], language="bash")


def _render_groups(ir: dict[str, Any]) -> None:
    """Render detected group management operations."""
    groups = ir.get("groups", [])
    if not groups:
        return
    st.subheader("Group Management")
    for g in groups:
        with st.expander(f"Line {g['line']}: [{g['action']}] {g['raw'][:60]}"):
            st.write("**Ansible module:** `ansible.builtin.group`")
            st.write(f"**Confidence:** {g['confidence']:.0%}")
            st.code(g["raw"], language="bash")


def _render_file_perms(ir: dict[str, Any]) -> None:
    """Render detected file permission operations."""
    file_perms = ir.get("file_perms", [])
    if not file_perms:
        return
    st.subheader("File Permissions")
    for fp in file_perms:
        detail = fp["mode"] if fp["op"] == "chmod" else fp["owner"]
        with st.expander(f"Line {fp['line']}: {fp['op']} {detail} {fp['path']}"):
            st.write("**Ansible module:** `ansible.builtin.file`")
            st.write(f"**Confidence:** {fp['confidence']:.0%}")
            st.write(f"**Recursive:** {fp['recursive']}")
            st.code(fp["raw"], language="bash")


def _render_git_ops(ir: dict[str, Any]) -> None:
    """Render detected git operations."""
    git_ops = ir.get("git_ops", [])
    if not git_ops:
        return
    st.subheader("Git Operations")
    for g in git_ops:
        detail = g.get("repo") or g.get("dest") or g["raw"][:40]
        with st.expander(f"Line {g['line']}: [{g['action']}] {detail}"):
            st.write("**Ansible module:** `ansible.builtin.git`")
            st.write(f"**Confidence:** {g['confidence']:.0%}")
            st.code(g["raw"], language="bash")


def _render_archives(ir: dict[str, Any]) -> None:
    """Render detected archive extraction operations."""
    archives = ir.get("archives", [])
    if not archives:
        return
    st.subheader("Archive Extractions")
    for a in archives:
        with st.expander(f"Line {a['line']}: [{a['tool']}] {a['source']}"):
            st.write("**Ansible module:** `ansible.builtin.unarchive`")
            st.write(f"**Confidence:** {a['confidence']:.0%}")
            st.code(a["raw"], language="bash")


def _render_sed_ops(ir: dict[str, Any]) -> None:
    """Render detected sed in-place operations."""
    sed_ops = ir.get("sed_ops", [])
    if not sed_ops:
        return
    st.subheader("sed In-place Operations")
    for s in sed_ops:
        with st.expander(f"Line {s['line']}: {s['raw'][:60]}"):
            st.write(
                f"**Suggested module:** `{s['ansible_module']}`"
                " or `ansible.builtin.replace`"
            )
            st.write(f"**Confidence:** {s['confidence']:.0%}")
            st.code(s["raw"], language="bash")


def _render_cron_jobs(ir: dict[str, Any]) -> None:
    """Render detected cron job operations."""
    cron_jobs = ir.get("cron_jobs", [])
    if not cron_jobs:
        return
    st.subheader("Cron Jobs")
    for c in cron_jobs:
        with st.expander(f"Line {c['line']}: {c['raw'][:60]}"):
            st.write("**Suggested module:** `ansible.builtin.cron`")
            st.write(f"**Confidence:** {c['confidence']:.0%}")
            st.code(c["raw"], language="bash")


def _render_firewall_rules(ir: dict[str, Any]) -> None:
    """Render detected firewall rule operations."""
    firewall_rules = ir.get("firewall_rules", [])
    if not firewall_rules:
        return
    st.subheader("Firewall Rules")
    for fw in firewall_rules:
        with st.expander(f"Line {fw['line']}: [{fw['tool']}] {fw['raw'][:60]}"):
            st.write(f"**Ansible module:** `{fw['ansible_module']}`")
            st.write(f"**Confidence:** {fw['confidence']:.0%}")
            st.code(fw["raw"], language="bash")


def _render_hostname_ops(ir: dict[str, Any]) -> None:
    """Render detected hostname operations."""
    hostname_ops = ir.get("hostname_ops", [])
    if not hostname_ops:
        return
    st.subheader("Hostname Operations")
    for h in hostname_ops:
        with st.expander(f"Line {h['line']}: set hostname to {h['hostname']}"):
            st.write("**Ansible module:** `ansible.builtin.hostname`")
            st.write(f"**Confidence:** {h['confidence']:.0%}")
            st.code(h["raw"], language="bash")


def _render_env_vars(ir: dict[str, Any]) -> None:
    """Render detected environment variables."""
    env_vars = ir.get("env_vars", [])
    if not env_vars:
        return
    st.subheader("Environment Variables")
    for v in env_vars:
        label = f"Line {v['line']}: {v['name']}={v['value']}"
        if v["is_sensitive"]:
            label += " [SENSITIVE]"
        with st.expander(label):
            if v["is_sensitive"]:
                st.warning("This variable appears to contain sensitive data.")
            st.code(v["raw"], language="bash")


def _render_sensitive_data(ir: dict[str, Any]) -> None:
    """Render sensitive data warnings prominently with st.error."""
    sensitive_data = ir.get("sensitive_data", [])
    if not sensitive_data:
        return
    st.subheader("Sensitive Data Detected")
    for s in sensitive_data:
        st.error(f"**Line {s['line']} [{s['type']}]:** {s['suggestion']}")


def _render_cm_escapes(ir: dict[str, Any]) -> None:
    """Render CM tool escape call warnings prominently."""
    cm_escapes = ir.get("cm_escapes", [])
    if not cm_escapes:
        return
    st.subheader("Configuration Management Tool Calls Detected")
    for c in cm_escapes:
        st.warning(f"**Line {c['line']} [{c['tool']}]:** {c['suggestion']}")
        with st.expander(f"Line {c['line']}: {c['raw'][:60]}"):
            st.code(c["raw"], language="bash")


def _render_quality_score(data: dict[str, Any]) -> None:
    """
    Render the conversion quality score badge and metrics.

    Args:
        data: JSON response dict from the converter containing a
            ``quality_score`` key.

    """
    qs = data.get("quality_score", {})
    if not qs or qs.get("grade") == "N/A":
        return

    st.subheader("Quality Score")
    grade = qs.get("grade", "N/A")
    grade_colours = {
        "A": "green",
        "B": "blue",
        "C": "orange",
        "D": "orange",
        "F": "red",
    }
    colour = grade_colours.get(grade, "grey")
    st.markdown(
        f"<span style='font-size:2rem;color:{colour};font-weight:bold'>"
        f"Grade: {grade}</span>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Coverage", f"{qs.get('coverage_pct', 0)}%")
    with col2:
        st.metric("Structured Tasks", qs.get("structured_operations", 0))
    with col3:
        st.metric(SHELL_FALLBACKS_LABEL, qs.get("shell_fallbacks", 0))

    improvements = qs.get("improvements", [])
    if improvements:
        st.write("**Suggested improvements:**")
        for imp in improvements:
            st.info(imp)


def _render_aap_hints(data: dict[str, Any]) -> None:
    """
    Render Ansible Automation Platform deployment hints.

    Args:
        data: JSON response dict from the converter containing an
            ``aap_hints`` key.

    """
    hints = data.get("aap_hints", {})
    if not hints:
        return

    st.subheader("AAP Deployment Hints")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Execution Environment:** `{hints.get('suggested_ee', '')}`")
        st.write(
            f"**Credentials:** {', '.join(hints.get('suggested_credentials', []))}"
        )
    with col2:
        st.write(f"**Become enabled:** {hints.get('become_enabled', True)}")
        st.write(f"**Timeout:** {hints.get('timeout', 3600)}s")

    survey_vars = hints.get("survey_variables", [])
    if survey_vars:
        st.write("**Suggested survey variables:**")
        for sv in survey_vars:
            required_tag = " (required)" if sv.get("required") else ""
            st.info(f"`{sv['name']}`{required_tag} — {sv['description']}")

    notes = hints.get("notes", [])
    if notes:
        st.write("**Notes:**")
        for note in notes:
            st.warning(note)


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

    _render_quality_score(data)
    _render_aap_hints(data)

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
            st.metric(SHELL_FALLBACKS_LABEL, report.get("non_idempotent_tasks", 0))

        suggestions = report.get("suggestions", [])
        if suggestions:
            st.write("**Suggestions:**")
            for suggestion in suggestions:
                st.info(suggestion)


def _display_role_results(
    content: str,
    script_path: str = "script.sh",
    role_name: str = "bash_converted",
) -> None:
    """
    Generate an Ansible role from *content* and display the file tree.

    Args:
        content: Raw Bash script text.
        script_path: Original script path label.
        role_name: Name for the generated role.

    """
    raw = generate_ansible_role_from_bash(
        content, role_name=role_name, script_path=script_path
    )
    data = json.loads(raw)

    if data.get("status") == "error":
        st.error(f"Role generation error: {data.get('error')}")
        return

    st.subheader(f"Generated Role: {data.get('role_name', role_name)}")

    _render_quality_score(data)
    _render_aap_hints(data)

    files: dict[str, str] = data.get("files", {})
    st.write(f"**{len(files)} file(s) generated:**")
    for filename, file_content in files.items():
        lang = "yaml"
        if filename.endswith(".md"):
            lang = "markdown"
        with st.expander(f"{filename}"):
            st.code(file_content, language=lang)
            st.download_button(
                f"Download {filename}",
                data=file_content,
                file_name=filename.replace("/", "_"),
                mime="text/plain",
                key=f"dl_{filename}",
            )
