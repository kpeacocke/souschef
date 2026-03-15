"""Salt Migration Page for SousChef UI."""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # pragma: no cover

from souschef.converters.salt import (
    convert_salt_directory_to_roles,
    convert_salt_sls_to_ansible,
)
from souschef.core.path_utils import _get_workspace_root
from souschef.parsers.salt import (
    assess_salt_complexity,
    parse_salt_directory,
    parse_salt_pillar,
    parse_salt_sls,
)


def _validate_ui_path(path_str: str) -> str | None:
    """
    Validate and normalise a user-provided filesystem path.

    Ensures the path stays within the workspace root to prevent directory
    traversal attacks (CWE-22).

    The implementation uses the canonical CodeQL-recognised sanitiser pattern
    for ``py/path-injection``:

    1. ``Path(trusted_base) / user_input`` + ``os.path.normpath`` — pure
       string normalisation with no filesystem I/O; collapses all ``..`` and
       repeated-separator sequences so directory-traversal sequences cannot
       survive.
    2. ``os.path.commonpath([candidate, workspace])`` — containment guard
       that CodeQL models as a barrier, preventing the taint from propagating
       past this check to any downstream filesystem operation.  ``commonpath``
       is used in preference to ``startswith`` because it handles the edge
       case of a root (``/``) workspace correctly.

    Null bytes (CWE-158) are rejected before normalisation because they can
    terminate the path string in C-based OS functions and bypass suffix checks.

    No helper function that performs filesystem I/O is called on user-controlled
    data — this keeps the guard and any subsequent use in the same scope so that
    CodeQL's inter-procedural taint analysis does not trace the taint into a
    different call frame and re-flag it against a sink there.

    Args:
        path_str: Raw path string from a UI text input.

    Returns:
        Normalised absolute path string if valid and within the workspace root,
        ``None`` if the path is unsafe, outside the workspace, or empty.

    """
    if not path_str or "\x00" in path_str:
        # Null bytes can terminate path strings in C-based OS functions (CWE-158),
        # potentially bypassing extension or suffix checks.
        return None
    try:
        workspace = _get_workspace_root()
        # workspace comes from a trusted internal source; normalise it purely
        # via normpath (no filesystem access needed here).
        workspace_str = os.path.normpath(str(workspace))
        # Pure string normalisation — no filesystem access.
        # Path(base) / user_input handles both relative and absolute inputs
        # (an absolute user_input replaces the base, which normpath then
        # makes canonical); normpath collapses all ".." sequences.
        candidate = os.path.normpath(str(Path(workspace_str) / path_str))
        # commonpath([candidate, workspace]) == workspace iff candidate is
        # within the workspace tree.  This is the CodeQL-recognised barrier:
        # any path that escapes the workspace is rejected before being passed
        # to any downstream operation.
        if os.path.commonpath([candidate, workspace_str]) != workspace_str:
            return None
        return candidate
    except (ValueError, OSError):
        return None


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

        safe_path = _validate_ui_path(sls_path)
        if safe_path is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Parsing SLS file..."):
            result_str = parse_salt_sls(safe_path)

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

        safe_path = _validate_ui_path(sls_path)
        if safe_path is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Converting SLS to Ansible..."):
            result_str = convert_salt_sls_to_ansible(safe_path, playbook_name)

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

        safe_path = _validate_ui_path(pillar_path)
        if safe_path is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Parsing pillar file..."):
            result_str = parse_salt_pillar(safe_path)

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

        safe_dir = _validate_ui_path(salt_dir)
        if safe_dir is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Scanning directory..."):
            result_str = parse_salt_directory(safe_dir)

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


def _render_assessment_section() -> None:
    """Render the complexity assessment section."""
    st.subheader("Assess Salt Migration Complexity")

    col1, col2 = st.columns([3, 1])

    with col1:
        salt_dir = st.text_input(
            "Salt States Directory",
            value="",
            placeholder="/srv/salt",
            help="Path to the Salt states root directory to assess.",
            key="salt_assess_dir",
        )

    with col2:
        assess_btn = st.button(
            "Assess", use_container_width=True, key="salt_assess_btn"
        )

    if assess_btn:
        if not salt_dir:
            st.error("Please enter a directory path.")
            return

        safe_dir = _validate_ui_path(salt_dir)
        if safe_dir is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Assessing Salt migration complexity..."):
            result_str = assess_salt_complexity(safe_dir)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Assessment error: {result_str}")
            return

        if "error" in result:
            st.error(result["error"])
            return

        st.session_state["salt_assess_result"] = result
        summary = result.get("summary", {})
        st.success(
            f"Assessment complete: {summary.get('total_files', 0)} files, "
            f"{summary.get('total_states', 0)} states, "
            f"complexity: {summary.get('complexity_level', 'unknown').upper()}"
        )

    if "salt_assess_result" in st.session_state:
        _display_assessment_results(st.session_state["salt_assess_result"])


def _display_assessment_results(result: dict[str, Any]) -> None:
    """
    Display complexity assessment results.

    Args:
        result: Assessment result dict.

    """
    summary = result.get("summary", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Files", summary.get("total_files", 0))
    with col2:
        st.metric("Total States", summary.get("total_states", 0))
    with col3:
        st.metric("Complexity", summary.get("complexity_level", "unknown").upper())
    with col4:
        st.metric("Effort (days)", summary.get("estimated_effort_days", 0))

    col5, col6 = st.columns(2)
    with col5:
        st.metric(
            "Effort with SousChef (days)",
            summary.get("estimated_effort_days_with_souschef", 0),
        )
    with col6:
        st.metric("Timeline", summary.get("estimated_effort_weeks", "unknown"))

    high_files = summary.get("high_complexity_files", [])
    if high_files:
        st.warning(f"{len(high_files)} high-complexity file(s) require manual review:")
        with st.expander("High-complexity files", expanded=True):
            for f in high_files:
                st.code(f)

    module_breakdown = summary.get("module_breakdown", {})
    if module_breakdown:
        st.subheader("Module Breakdown")
        with st.expander("Module usage", expanded=False):
            st.json(module_breakdown)

    files = result.get("files", [])
    if files:
        st.subheader("Per-file Complexity")
        with st.expander(f"File reports ({len(files)})", expanded=False):
            for fr in sorted(
                files, key=lambda x: x.get("complexity_score", 0), reverse=True
            ):
                level = fr.get("complexity_level", "low")
                st.markdown(
                    f"**`{fr['file']}`** — {fr['state_count']} states, "
                    f"score: {fr['complexity_score']:.1f}, level: **{level.upper()}**"
                )


def _render_migration_plan_section() -> None:
    """Render the migration plan generation section."""
    st.subheader("Generate Migration Plan")

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        salt_dir = st.text_input(
            "Salt States Directory",
            value="",
            placeholder="/srv/salt",
            help="Path to the Salt states root directory.",
            key="salt_plan_dir",
        )

    with col2:
        timeline = st.number_input(
            "Timeline (weeks)",
            min_value=1,
            max_value=52,
            value=8,
            key="salt_plan_timeline",
        )

    with col3:
        platform = st.selectbox(
            "Target Platform",
            options=["aap", "awx", "ansible_core"],
            key="salt_plan_platform",
        )

    plan_btn = st.button("Generate Plan", key="salt_plan_btn")

    if plan_btn:
        if not salt_dir:
            st.error("Please enter a directory path.")
            return

        safe_dir = _validate_ui_path(salt_dir)
        if safe_dir is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Generating migration plan..."):
            from souschef.server import plan_salt_migration

            result_str = plan_salt_migration(safe_dir, int(timeline), str(platform))

        st.session_state["salt_plan_result"] = result_str
        st.success("Migration plan generated.")

    if "salt_plan_result" in st.session_state:
        plan_text = st.session_state["salt_plan_result"]
        st.markdown(plan_text)
        st.download_button(
            "Download Plan",
            data=plan_text,
            file_name="salt_migration_plan.md",
            mime="text/plain",
            key="salt_download_plan",
        )


def _render_batch_convert_section() -> None:
    """Render the batch directory conversion section."""
    st.subheader("Batch Convert Salt Directory to Ansible Roles")

    col1, col2 = st.columns(2)

    with col1:
        salt_dir = st.text_input(
            "Salt States Directory",
            value="",
            placeholder="/srv/salt",
            help="Path to the Salt states root directory.",
            key="salt_batch_dir",
        )

    with col2:
        output_dir = st.text_input(
            "Output Directory",
            value="",
            placeholder="/tmp/ansible-roles",
            help="Path where Ansible roles structure should be written.",
            key="salt_batch_output",
        )

    convert_btn = st.button("Convert Directory", key="salt_batch_btn")

    if convert_btn:
        if not salt_dir or not output_dir:
            st.error("Please enter both a Salt directory and an output directory.")
            return

        safe_salt_dir = _validate_ui_path(salt_dir)
        if safe_salt_dir is None:
            st.error("Invalid or unsafe Salt directory path. Must be within the workspace.")
            return

        safe_output_dir = _validate_ui_path(output_dir)
        if safe_output_dir is None:
            st.error("Invalid or unsafe output directory path. Must be within the workspace.")
            return

        with st.spinner("Converting Salt directory to Ansible roles..."):
            result_str = convert_salt_directory_to_roles(safe_salt_dir, safe_output_dir)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Conversion error: {result_str}")
            return

        if "error" in result:
            st.error(result["error"])
            return

        st.session_state["salt_batch_result"] = result
        roles = result.get("roles_created", [])
        files = result.get("files_written", [])
        st.success(
            f"Converted {len(roles)} role(s), wrote {len(files)} file(s) to {output_dir}"
        )

    if "salt_batch_result" in st.session_state:
        result = st.session_state["salt_batch_result"]
        roles = result.get("roles_created", [])
        files = result.get("files_written", [])
        warnings = result.get("warnings", [])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Roles Created", len(roles))
        with col2:
            st.metric("Files Written", len(files))

        if warnings:
            st.warning(f"{len(warnings)} warning(s):")
            for w in warnings:
                st.markdown(f"- {w}")

        if roles:
            with st.expander(f"Roles ({len(roles)})", expanded=True):
                for r in roles:
                    st.code(r)

        if files:
            with st.expander(f"Files written ({len(files)})", expanded=False):
                for f in files:
                    st.code(f)


def _render_inventory_section() -> None:
    """Render the inventory generation section."""
    st.subheader("Generate Ansible Inventory from top.sls")

    col1, col2 = st.columns([3, 1])

    with col1:
        top_path = st.text_input(
            "top.sls Path",
            value="",
            placeholder="/srv/salt/top.sls",
            help="Path to the SaltStack top.sls file.",
            key="salt_top_path",
        )

    with col2:
        inv_btn = st.button(
            "Generate Inventory", use_container_width=True, key="salt_inv_btn"
        )

    if inv_btn:
        if not top_path:
            st.error("Please enter a path to the top.sls file.")
            return

        safe_path = _validate_ui_path(top_path)
        if safe_path is None:
            st.error("Invalid or unsafe path. Path must be within the workspace.")
            return

        with st.spinner("Generating Ansible inventory..."):
            from souschef.server import generate_salt_inventory

            result_str = generate_salt_inventory(safe_path)

        try:
            result: dict[str, Any] = json.loads(result_str)
        except json.JSONDecodeError:
            st.error(f"Generation error: {result_str}")
            return

        if "error" in result:
            st.error(result["error"])
            return

        st.session_state["salt_inv_result"] = result
        groups = result.get("groups", [])
        hosts = result.get("hosts", [])
        st.success(
            f"Generated inventory with {len(groups)} group(s) and {len(hosts)} host(s)."
        )

    if "salt_inv_result" in st.session_state:
        result = st.session_state["salt_inv_result"]
        inventory = result.get("inventory", "")

        if inventory:
            st.subheader("Generated Ansible Inventory")
            st.code(inventory, language="ini")
            st.download_button(
                "Download Inventory",
                data=inventory,
                file_name="hosts",
                mime="text/plain",
                key="salt_download_inventory",
            )

        groups = result.get("groups", [])
        if groups:
            with st.expander(f"Groups ({len(groups)})", expanded=False):
                for g in groups:
                    st.code(g)


def show_salt_migration_page() -> None:
    """Render the complete Salt Migration page."""
    _display_intro()

    (
        tab_parse,
        tab_convert,
        tab_pillar,
        tab_directory,
        tab_assessment,
        tab_plan,
        tab_batch,
        tab_inventory,
    ) = st.tabs(
        [
            "Parse SLS",
            "Convert to Ansible",
            "Pillar Files",
            "Directory Scan",
            "Assessment",
            "Migration Plan",
            "Batch Convert",
            "Inventory",
        ]
    )

    with tab_parse:
        _render_sls_parse_section()

    with tab_convert:
        _render_convert_section()

    with tab_pillar:
        _render_pillar_section()

    with tab_directory:
        _render_directory_section()

    with tab_assessment:
        _render_assessment_section()

    with tab_plan:
        _render_migration_plan_section()

    with tab_batch:
        _render_batch_convert_section()

    with tab_inventory:
        _render_inventory_section()
