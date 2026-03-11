"""Salt Migration Page for SousChef UI."""

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # pragma: no cover

from souschef.converters.salt import convert_salt_sls_to_ansible
from souschef.parsers.salt import (
    parse_salt_directory,
    parse_salt_pillar,
    parse_salt_sls,
)


def _display_intro() -> None:
    """Render the Salt migration page title and introduction."""
    st.title("Salt Migration")
    st.markdown(
        """
    Convert SaltStack SLS state files and pillars into Ansible playbooks.

    **Supported features:**
    - Parse SLS state files (pkg, file, service, cmd, user, group, git, pip)
    - Extract pillar variable provenance mappings
    - Convert SLS states to Ansible tasks
    - Scan Salt state directory structures
    - Parse pillar and top files
    """
    )


def _render_sls_parse_section() -> None:
    """Render the SLS file parsing section."""
    st.subheader("Parse SLS State File")

    col1, col2 = st.columns([3, 1])

    with col1:
        sls_path = st.text_input(
            "SLS File Path",
            value="",
            placeholder="/srv/salt/states/webserver/init.sls",
            help="Absolute path to a SaltStack SLS state file.",
            key="salt_sls_path",
        )

    with col2:
        parse_btn = st.button(
            "Parse SLS", use_container_width=True, key="salt_parse_btn"
        )

    if parse_btn:
        if not sls_path:
            st.error("Please enter a path to an SLS file.")
            return

        with st.spinner("Parsing SLS file..."):
            result_str = parse_salt_sls(sls_path)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Parse error: {result_str}")
            return

        if "Error" in result_str and "states" not in result:
            st.error(result_str)
            return

        st.session_state["salt_parse_result"] = result
        total = result.get("summary", {}).get("total_states", 0)
        st.success(f"Parsed {total} states from {sls_path}")

    if "salt_parse_result" in st.session_state:
        _display_parse_results(st.session_state["salt_parse_result"])


def _display_parse_results(result: dict[str, Any]) -> None:
    """
    Display parsed SLS state results.

    Args:
        result: Parsed SLS result dict.

    """
    summary = result.get("summary", {})
    by_category = summary.get("by_category", {})

    if by_category:
        st.subheader("State Summary")
        cols = st.columns(min(len(by_category), 4))
        for idx, (cat, count) in enumerate(by_category.items()):
            with cols[idx % len(cols)]:
                st.metric(cat.capitalize(), count)

    states = result.get("states", [])
    if states:
        st.subheader("States")
        with st.expander("View extracted states", expanded=False):
            for state in states:
                mod_func = f"`{state.get('module')}.{state.get('function')}`"
                cat = state.get("category", "unknown")
                st.markdown(f"**{state.get('id')}** — {mod_func} ({cat})")

    pillar_keys = summary.get("pillar_keys", [])
    if pillar_keys:
        st.subheader("Pillar References")
        st.info(
            f"Found {len(pillar_keys)} pillar variable reference(s): "
            + ", ".join(f"`{k}`" for k in pillar_keys)
        )

    grain_keys = summary.get("grain_keys", [])
    if grain_keys:
        st.subheader("Grain References")
        st.info(
            f"Found {len(grain_keys)} grain reference(s): "
            + ", ".join(f"`{k}`" for k in grain_keys)
        )

    st.subheader("Raw JSON")
    with st.expander("View raw output", expanded=False):
        st.json(result)


def _render_convert_section() -> None:
    """Render the SLS to Ansible conversion section."""
    st.subheader("Convert SLS to Ansible Playbook")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        sls_path = st.text_input(
            "SLS File Path",
            value="",
            placeholder="/srv/salt/states/webserver/init.sls",
            help="Path to the SLS state file to convert.",
            key="salt_convert_sls_path",
        )

    with col2:
        playbook_name = st.text_input(
            "Playbook Name (optional)",
            value="",
            placeholder="webserver",
            help="Optional name for the generated playbook.",
            key="salt_playbook_name",
        )

    with col3:
        convert_btn = st.button(
            "Convert", use_container_width=True, key="salt_convert_btn"
        )

    if convert_btn:
        if not sls_path:
            st.error("Please enter a path to an SLS file.")
            return

        with st.spinner("Converting SLS to Ansible..."):
            result_str = convert_salt_sls_to_ansible(sls_path, playbook_name)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Conversion error: {result_str}")
            return

        if "error" in result:
            st.error(result["error"])
            return

        st.session_state["salt_convert_result"] = result
        converted = result.get("tasks_converted", 0)
        unconverted = result.get("tasks_unconverted", 0)
        st.success(
            f"Conversion complete: {converted} task(s) converted, "
            f"{unconverted} task(s) require manual review."
        )

    if "salt_convert_result" in st.session_state:
        _display_conversion_results(st.session_state["salt_convert_result"])


def _display_conversion_results(result: dict[str, Any]) -> None:
    """
    Display SLS-to-Ansible conversion results.

    Args:
        result: Conversion result dict.

    """
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Tasks Converted", result.get("tasks_converted", 0))
    with col2:
        st.metric("Requires Manual Review", result.get("tasks_unconverted", 0))

    warnings = result.get("warnings", [])
    if warnings:
        st.warning(f"{len(warnings)} conversion warning(s):")
        for w in warnings:
            st.markdown(f"- {w}")

    ansible_vars = result.get("ansible_vars", {})
    if ansible_vars:
        st.subheader("Ansible Variables (from pillars)")
        with st.expander("View variable mappings", expanded=False):
            st.json(ansible_vars)

    playbook = result.get("playbook", "")
    if playbook:
        st.subheader("Generated Ansible Playbook")
        st.code(playbook, language="yaml")
        st.download_button(
            "Download Playbook",
            data=playbook,
            file_name="playbook.yml",
            mime="text/plain",
            key="salt_download_playbook",
        )


def _render_pillar_section() -> None:
    """Render the pillar file parsing section."""
    st.subheader("Parse Pillar File")

    col1, col2 = st.columns([3, 1])

    with col1:
        pillar_path = st.text_input(
            "Pillar File Path",
            value="",
            placeholder="/srv/salt/pillar/webserver.sls",
            help="Path to a SaltStack pillar SLS file.",
            key="salt_pillar_path",
        )

    with col2:
        pillar_btn = st.button(
            "Parse Pillar", use_container_width=True, key="salt_pillar_btn"
        )

    if pillar_btn:
        if not pillar_path:
            st.error("Please enter a path to a pillar file.")
            return

        with st.spinner("Parsing pillar file..."):
            result_str = parse_salt_pillar(pillar_path)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Parse error: {result_str}")
            return

        if "Error" in result_str and "variables" not in result:
            st.error(result_str)
            return

        st.session_state["salt_pillar_result"] = result
        total = result.get("summary", {}).get("total_keys", 0)
        st.success(f"Parsed {total} variable(s) from pillar file.")

    if "salt_pillar_result" in st.session_state:
        result = st.session_state["salt_pillar_result"]
        st.subheader("Pillar Variables")
        flattened = result.get("flattened", {})
        if flattened:
            with st.expander("View flattened variables", expanded=True):
                st.json(flattened)
        else:
            st.info("No pillar variables found.")


def _render_directory_section() -> None:
    """Render the Salt directory scanning section."""
    st.subheader("Scan Salt Directory")

    col1, col2 = st.columns([3, 1])

    with col1:
        salt_dir = st.text_input(
            "Salt States Directory",
            value="",
            placeholder="/srv/salt",
            help="Path to the root Salt states directory.",
            key="salt_dir_path",
        )

    with col2:
        scan_btn = st.button(
            "Scan Directory", use_container_width=True, key="salt_scan_btn"
        )

    if scan_btn:
        if not salt_dir:
            st.error("Please enter a directory path.")
            return

        with st.spinner("Scanning directory..."):
            result_str = parse_salt_directory(salt_dir)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Scan error: {result_str}")
            return

        if "Error" in result_str and "files" not in result:
            st.error(result_str)
            return

        st.session_state["salt_dir_result"] = result
        summary = result.get("summary", {})
        st.success(
            f"Found {summary.get('total_files', 0)} SLS file(s) "
            f"({summary.get('state_files', 0)} states, "
            f"{summary.get('pillar_files', 0)} pillars, "
            f"{summary.get('top_files', 0)} top files)."
        )

    if "salt_dir_result" in st.session_state:
        _display_directory_results(st.session_state["salt_dir_result"])


def _display_directory_results(result: dict[str, Any]) -> None:
    """
    Display Salt directory scan results.

    Args:
        result: Directory scan result dict.

    """
    summary = result.get("summary", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Files", summary.get("total_files", 0))
    with col2:
        st.metric("State Files", summary.get("state_files", 0))
    with col3:
        st.metric("Pillar Files", summary.get("pillar_files", 0))
    with col4:
        st.metric("Top Files", summary.get("top_files", 0))

    files = result.get("files", {})
    state_files = files.get("states", [])
    if state_files:
        with st.expander(f"State files ({len(state_files)})", expanded=False):
            for f in state_files:
                st.code(f)

    top_files = files.get("top", [])
    if top_files:
        with st.expander(f"Top files ({len(top_files)})", expanded=False):
            for f in top_files:
                st.code(f)

    pillar_files = files.get("pillars", [])
    if pillar_files:
        with st.expander(f"Pillar files ({len(pillar_files)})", expanded=False):
            for f in pillar_files:
                st.code(f)


def show_salt_migration_page() -> None:
    """Render the complete Salt Migration page."""
    _display_intro()

    tab_parse, tab_convert, tab_pillar, tab_directory = st.tabs(
        ["Parse SLS", "Convert to Ansible", "Pillar Files", "Directory Scan"]
    )

    with tab_parse:
        _render_sls_parse_section()

    with tab_convert:
        _render_convert_section()

    with tab_pillar:
        _render_pillar_section()

    with tab_directory:
        _render_directory_section()
