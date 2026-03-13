"""
Puppet Migration Page for SousChef UI.

Provides a Streamlit interface for converting Puppet manifests and modules
to Ansible playbooks. Supports:
- Single manifest file upload or path input
- Module directory analysis
- Resource listing with unsupported construct warnings
- Playbook download
- AI-assisted conversion for unsupported constructs
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # type: ignore[assignment]  # pragma: no cover

from souschef.converters.puppet_to_ansible import (
    convert_puppet_manifest_to_ansible,
    convert_puppet_manifest_to_ansible_with_ai,
    convert_puppet_module_to_ansible,
    convert_puppet_module_to_ansible_with_ai,
    get_puppet_ansible_module_map,
)
from souschef.core.path_utils import (
    _get_workspace_root,
)
from souschef.parsers.puppet import (
    parse_puppet_manifest,
    parse_puppet_module,
)

INPUT_METHOD_FILE_PATH = "Manifest File Path"
INPUT_METHOD_MODULE_PATH = "Module Directory Path"
INPUT_METHODS = [INPUT_METHOD_FILE_PATH, INPUT_METHOD_MODULE_PATH]

MIME_TEXT_YAML = "text/yaml"
MIME_TEXT_PLAIN = "text/plain"

# AI provider display names
_AI_PROVIDERS = ["anthropic", "openai", "watson", "lightspeed"]
_DEFAULT_PROVIDER = "anthropic"
_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


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


def show_puppet_migration_page() -> None:
    """Render the Puppet Migration page in the Streamlit UI."""
    if st is None:
        return  # pragma: no cover

    st.header("Puppet Migration")
    st.markdown(
        "Convert Puppet manifests and modules to Ansible playbooks. "
        "Supports package, file, service, user, group, exec, cron, and more. "
        "Use **Convert with AI** to handle advanced constructs such as Hiera "
        "lookups, ``create_resources``, and exported resources."
    )

    # Input method selection
    input_method = st.radio(
        "Input method",
        INPUT_METHODS,
        horizontal=True,
        key="puppet_input_method",
    )

    if input_method == INPUT_METHOD_FILE_PATH:
        _show_manifest_file_section()
    else:
        _show_module_directory_section()

    st.divider()
    _show_resource_type_reference()


def _get_ai_settings() -> dict[str, str | float | int]:
    """
    Retrieve AI settings from the inline expander controls.

    Returns:
        Dictionary with ``provider``, ``api_key``, ``model``, ``temperature``,
        ``max_tokens``, ``project_id``, and ``base_url`` keys.

    """
    if st is None:  # pragma: no cover
        return {}  # pragma: no cover

    with st.expander("AI Settings (required for Convert with AI)"):
        provider = st.selectbox(
            "AI Provider",
            _AI_PROVIDERS,
            key="puppet_ai_provider",
        )
        api_key = st.text_input(
            "API Key",
            type="password",
            key="puppet_ai_api_key",
            help="API key for the selected AI provider.",
        )
        model = st.text_input(
            "Model",
            value=_DEFAULT_MODEL,
            key="puppet_ai_model",
            help="Model identifier (e.g. claude-3-5-sonnet-20241022, gpt-4o).",
        )
        col_t, col_m = st.columns(2)
        with col_t:
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.05,
                key="puppet_ai_temperature",
            )
        with col_m:
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=500,
                max_value=8000,
                value=4000,
                step=500,
                key="puppet_ai_max_tokens",
            )
        project_id = st.text_input(
            "Project ID (IBM Watsonx only)",
            key="puppet_ai_project_id",
        )
        base_url = st.text_input(
            "Base URL (optional override)",
            key="puppet_ai_base_url",
        )

    return {
        "provider": provider or _DEFAULT_PROVIDER,
        "api_key": api_key or "",
        "model": model or _DEFAULT_MODEL,
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "project_id": project_id or "",
        "base_url": base_url or "",
    }


def _show_manifest_file_section() -> None:
    """Render the manifest file input and analysis section."""
    if st is None:
        return  # pragma: no cover

    st.subheader("Analyse Puppet Manifest")
    manifest_path = st.text_input(
        "Manifest path (.pp file)",
        key="puppet_manifest_path",
        placeholder="/path/to/manifest.pp",
        help="Enter the path to a Puppet manifest file (.pp)",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        analyse_clicked = st.button(
            "Analyse Manifest",
            key="puppet_analyse_manifest",
            type="secondary",
        )

    with col2:
        convert_clicked = st.button(
            "Convert to Ansible",
            key="puppet_convert_manifest",
            type="primary",
        )

    with col3:
        ai_clicked = st.button(
            "Convert with AI",
            key="puppet_ai_manifest",
            type="primary",
            help=(
                "Use an LLM to convert unsupported constructs "
                "(Hiera, create_resources, exported resources, etc.)"
            ),
        )

    if not manifest_path:
        if analyse_clicked or convert_clicked or ai_clicked:
            st.warning("Please enter a manifest path.")
        return

    ai_cfg = _get_ai_settings() if ai_clicked else {}

    if analyse_clicked:
        _run_manifest_analysis(manifest_path)

    if convert_clicked:
        _run_manifest_conversion(manifest_path)

    if ai_clicked:
        _run_manifest_ai_conversion(manifest_path, ai_cfg)


def _show_module_directory_section() -> None:
    """Render the module directory input and analysis section."""
    if st is None:
        return  # pragma: no cover

    st.subheader("Analyse Puppet Module")
    module_path = st.text_input(
        "Module directory path",
        key="puppet_module_path",
        placeholder="/path/to/puppet/module",
        help="Enter the path to a Puppet module directory containing .pp files",
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        analyse_clicked = st.button(
            "Analyse Module",
            key="puppet_analyse_module",
            type="secondary",
        )

    with col2:
        convert_clicked = st.button(
            "Convert to Ansible",
            key="puppet_convert_module",
            type="primary",
        )

    with col3:
        ai_clicked = st.button(
            "Convert with AI",
            key="puppet_ai_module",
            type="primary",
            help=(
                "Use an LLM to convert unsupported constructs "
                "(Hiera, create_resources, exported resources, etc.)"
            ),
        )

    if not module_path:
        if analyse_clicked or convert_clicked or ai_clicked:
            st.warning("Please enter a module directory path.")
        return

    ai_cfg = _get_ai_settings() if ai_clicked else {}

    if analyse_clicked:
        _run_module_analysis(module_path)

    if convert_clicked:
        _run_module_conversion(module_path)

    if ai_clicked:
        _run_module_ai_conversion(module_path, ai_cfg)


def _run_manifest_analysis(manifest_path: str) -> None:
    """Execute manifest analysis and display results."""
    if st is None:
        return  # pragma: no cover

    safe = _validate_ui_path(manifest_path)
    if safe is None:
        st.error(f"Invalid or unsafe path: {manifest_path!r}")
        return

    with st.spinner("Analysing Puppet manifest..."):
        result = parse_puppet_manifest(safe)

    _display_analysis_result(result, "manifest")


def _run_module_analysis(module_path: str) -> None:
    """Execute module analysis and display results."""
    if st is None:
        return  # pragma: no cover

    safe = _validate_ui_path(module_path)
    if safe is None:
        st.error(f"Invalid or unsafe path: {module_path!r}")
        return

    with st.spinner("Analysing Puppet module..."):
        result = parse_puppet_module(safe)

    _display_analysis_result(result, "module")


def _run_manifest_conversion(manifest_path: str) -> None:
    """Execute manifest conversion and display playbook."""
    if st is None:
        return  # pragma: no cover

    safe = _validate_ui_path(manifest_path)
    if safe is None:
        st.error(f"Invalid or unsafe path: {manifest_path!r}")
        return

    with st.spinner("Converting Puppet manifest to Ansible..."):
        playbook = convert_puppet_manifest_to_ansible(safe)

    _display_conversion_result(playbook, safe)


def _run_module_conversion(module_path: str) -> None:
    """Execute module conversion and display playbook."""
    if st is None:
        return  # pragma: no cover

    safe = _validate_ui_path(module_path)
    if safe is None:
        st.error(f"Invalid or unsafe path: {module_path!r}")
        return

    with st.spinner("Converting Puppet module to Ansible..."):
        playbook = convert_puppet_module_to_ansible(safe)

    _display_conversion_result(playbook, safe)


def _run_manifest_ai_conversion(
    manifest_path: str, ai_cfg: dict[str, str | float | int]
) -> None:
    """Execute AI-assisted manifest conversion and display the playbook."""
    if st is None:
        return  # pragma: no cover

    if not ai_cfg.get("api_key"):
        st.warning(
            "An API key is required for AI-assisted conversion. "
            "Expand the AI Settings panel above and enter your key."
        )
        return

    safe = _validate_ui_path(manifest_path)
    if safe is None:
        st.error(f"Invalid or unsafe path: {manifest_path!r}")
        return

    with st.spinner("Converting Puppet manifest to Ansible with AI..."):
        playbook = convert_puppet_manifest_to_ansible_with_ai(
            safe,
            ai_provider=str(ai_cfg.get("provider", _DEFAULT_PROVIDER)),
            api_key=str(ai_cfg.get("api_key", "")),
            model=str(ai_cfg.get("model", _DEFAULT_MODEL)),
            temperature=float(ai_cfg.get("temperature", 0.3)),
            max_tokens=int(ai_cfg.get("max_tokens", 4000)),
            project_id=str(ai_cfg.get("project_id", "")),
            base_url=str(ai_cfg.get("base_url", "")),
        )

    _display_conversion_result(playbook, safe, ai_enhanced=True)


def _run_module_ai_conversion(
    module_path: str, ai_cfg: dict[str, str | float | int]
) -> None:
    """Execute AI-assisted module conversion and display the playbook."""
    if st is None:
        return  # pragma: no cover

    if not ai_cfg.get("api_key"):
        st.warning(
            "An API key is required for AI-assisted conversion. "
            "Expand the AI Settings panel above and enter your key."
        )
        return

    safe = _validate_ui_path(module_path)
    if safe is None:
        st.error(f"Invalid or unsafe path: {module_path!r}")
        return

    with st.spinner("Converting Puppet module to Ansible with AI..."):
        playbook = convert_puppet_module_to_ansible_with_ai(
            safe,
            ai_provider=str(ai_cfg.get("provider", _DEFAULT_PROVIDER)),
            api_key=str(ai_cfg.get("api_key", "")),
            model=str(ai_cfg.get("model", _DEFAULT_MODEL)),
            temperature=float(ai_cfg.get("temperature", 0.3)),
            max_tokens=int(ai_cfg.get("max_tokens", 4000)),
            project_id=str(ai_cfg.get("project_id", "")),
            base_url=str(ai_cfg.get("base_url", "")),
        )

    _display_conversion_result(playbook, safe, ai_enhanced=True)


def _display_analysis_result(result: str, source_type: str) -> None:
    """Display analysis results with appropriate formatting."""
    if st is None:
        return  # pragma: no cover

    if result.startswith("Error:") or result.startswith("An error occurred:"):
        st.error(result)
        return

    if result.startswith("Warning:"):
        st.warning(result)
        return

    st.success(f"Puppet {source_type} analysis complete.")

    # Check for unsupported constructs
    if "Unsupported Constructs (" in result and "none detected" not in result:
        st.warning(
            "Unsupported constructs detected. Review the report before migration."
        )

    st.text_area(
        "Analysis Report",
        value=result,
        height=400,
        key=f"puppet_analysis_result_{source_type}",
    )

    st.download_button(
        "Download Analysis Report",
        data=result,
        file_name=f"puppet_{source_type}_analysis.txt",
        mime=MIME_TEXT_PLAIN,
        key=f"puppet_download_analysis_{source_type}",
    )


def _display_conversion_result(
    playbook: str, source_path: str, *, ai_enhanced: bool = False
) -> None:
    """Display converted Ansible playbook with download option."""
    if st is None:
        return  # pragma: no cover

    if playbook.startswith("Error:") or playbook.startswith("An error occurred:"):
        st.error(playbook)
        return

    if playbook.startswith("Warning:"):
        st.warning(playbook)
        return

    if ai_enhanced:
        st.success("Puppet manifest converted to Ansible playbook with AI assistance.")
        st.info(
            "The AI-generated playbook may include best-effort conversions for "
            "unsupported constructs. Review carefully before use in production."
        )
    else:
        st.success("Puppet manifest converted to Ansible playbook successfully.")

    # Warn if debug tasks present (unsupported constructs, non-AI path)
    if not ai_enhanced and (
        "WARNING:" in playbook or "manual review" in playbook.lower()
    ):
        st.warning(
            "Some resources require manual review. Check tasks labelled WARNING "
            "in the playbook. Use **Convert with AI** to attempt automatic "
            "conversion of these constructs."
        )

    st.code(playbook, language="yaml")

    # Generate a safe filename from source path
    safe_name = Path(source_path).stem.replace(" ", "_")
    suffix = "_ai" if ai_enhanced else ""
    filename = f"{safe_name}{suffix}_ansible_playbook.yml"

    st.download_button(
        "Download Ansible Playbook",
        data=playbook,
        file_name=filename,
        mime=MIME_TEXT_YAML,
        key=f"puppet_download_playbook{'_ai' if ai_enhanced else ''}",
    )


def _show_resource_type_reference() -> None:
    """Display a reference table of supported Puppet resource types."""
    if st is None:
        return  # pragma: no cover

    with st.expander("Supported Puppet Resource Types"):
        module_map = get_puppet_ansible_module_map()
        rows: list[dict[str, str]] = [
            {"Puppet Resource Type": puppet_type, "Ansible Module": ansible_module}
            for puppet_type, ansible_module in sorted(module_map.items())
        ]
        st.markdown("| Puppet Resource Type | Ansible Module |")
        st.markdown("|---|---|")
        for row in rows:
            ptype = row["Puppet Resource Type"]
            amod = row["Ansible Module"]
            st.markdown(f"| `{ptype}` | `{amod}` |")

        st.markdown("")
        st.markdown(
            "Resource types not listed above will generate a `debug` warning task "
            "requiring manual migration."
        )
