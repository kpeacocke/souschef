"""
Puppet Migration Page for SousChef UI.

Provides a Streamlit interface for converting Puppet manifests and modules
to Ansible playbooks. Supports:
- Single manifest file upload or path input
- Module directory analysis
- Resource listing with unsupported construct warnings
- Playbook download
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

if TYPE_CHECKING:
    import streamlit as st
else:
    try:
        import streamlit as st
    except ImportError:  # pragma: no cover
        st = None  # type: ignore[assignment]  # pragma: no cover

from souschef.converters.puppet_to_ansible import (
    convert_puppet_manifest_to_ansible,
    convert_puppet_module_to_ansible,
    get_puppet_ansible_module_map,
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


def show_puppet_migration_page() -> None:
    """Render the Puppet Migration page in the Streamlit UI."""
    if st is None:
        return  # pragma: no cover

    st.header("Puppet Migration")
    st.markdown(
        "Convert Puppet manifests and modules to Ansible playbooks. "
        "Supports package, file, service, user, group, exec, cron, and more."
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

    col1, col2 = st.columns(2)

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

    if not manifest_path:
        if analyse_clicked or convert_clicked:
            st.warning("Please enter a manifest path.")
        return

    if analyse_clicked:
        _run_manifest_analysis(manifest_path)

    if convert_clicked:
        _run_manifest_conversion(manifest_path)


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

    col1, col2 = st.columns(2)

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

    if not module_path:
        if analyse_clicked or convert_clicked:
            st.warning("Please enter a module directory path.")
        return

    if analyse_clicked:
        _run_module_analysis(module_path)

    if convert_clicked:
        _run_module_conversion(module_path)


def _run_manifest_analysis(manifest_path: str) -> None:
    """Execute manifest analysis and display results."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Analysing Puppet manifest..."):
        result = parse_puppet_manifest(manifest_path)

    _display_analysis_result(result, "manifest")


def _run_module_analysis(module_path: str) -> None:
    """Execute module analysis and display results."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Analysing Puppet module..."):
        result = parse_puppet_module(module_path)

    _display_analysis_result(result, "module")


def _run_manifest_conversion(manifest_path: str) -> None:
    """Execute manifest conversion and display playbook."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Converting Puppet manifest to Ansible..."):
        playbook = convert_puppet_manifest_to_ansible(manifest_path)

    _display_conversion_result(playbook, manifest_path)


def _run_module_conversion(module_path: str) -> None:
    """Execute module conversion and display playbook."""
    if st is None:
        return  # pragma: no cover

    with st.spinner("Converting Puppet module to Ansible..."):
        playbook = convert_puppet_module_to_ansible(module_path)

    _display_conversion_result(playbook, module_path)


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


def _display_conversion_result(playbook: str, source_path: str) -> None:
    """Display converted Ansible playbook with download option."""
    if st is None:
        return  # pragma: no cover

    if playbook.startswith("Error:") or playbook.startswith("An error occurred:"):
        st.error(playbook)
        return

    if playbook.startswith("Warning:"):
        st.warning(playbook)
        return

    st.success("Puppet manifest converted to Ansible playbook successfully.")

    # Warn if debug tasks present (unsupported constructs)
    if "WARNING:" in playbook or "manual review" in playbook.lower():
        st.warning(
            "Some resources require manual review. Check tasks labelled WARNING "
            "in the playbook."
        )

    st.code(playbook, language="yaml")

    # Generate a safe filename from source path
    safe_name = Path(source_path).stem.replace(" ", "_")
    filename = f"{safe_name}_ansible_playbook.yml"

    st.download_button(
        "Download Ansible Playbook",
        data=playbook,
        file_name=filename,
        mime=MIME_TEXT_YAML,
        key="puppet_download_playbook",
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
