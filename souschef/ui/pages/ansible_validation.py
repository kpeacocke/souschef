"""Ansible Collection Validation Page for SousChef UI."""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.ansible_upgrade import validate_collection_compatibility
from souschef.core.ansible_versions import ANSIBLE_VERSIONS
from souschef.parsers.ansible_inventory import parse_requirements_yml


def _display_validation_intro() -> None:
    """Render the validation page title and introduction."""
    st.title("Ansible Collection Validation")
    st.markdown(
        """
    Validate that your Ansible collections are compatible with
    a target Ansible version.
    """
    )


def _render_validation_inputs() -> tuple[Any, str, bool]:
    """Render inputs and return the uploaded file, version, and button."""
    col1, col2 = st.columns(2)

    with col1:
        collections_file = st.file_uploader(
            "Upload Requirements File (requirements.yml or requirements.txt)",
            type=["yml", "yaml", "txt"],
            help="Your Ansible requirements file with collections",
        )

    with col2:
        target_version = st.selectbox(
            "Target Ansible Version",
            options=sorted(ANSIBLE_VERSIONS.keys(), reverse=True),
            help="Target Ansible version to validate against",
        )

    validate_btn = st.button("Validate Collections", use_container_width=True)
    return collections_file, target_version, validate_btn


def _save_uploaded_file(collections_file: Any) -> str:
    """
    Persist the uploaded file and return its temporary path.

    Saves the file as requirements.yml in a temporary directory to satisfy
    parse_requirements_yml() filename validation.

    Returns:
        Path to the saved requirements.yml file.

    """
    tmp_dir = tempfile.mkdtemp()
    requirements_path = Path(tmp_dir) / "requirements.yml"
    requirements_path.write_bytes(collections_file.getbuffer().tobytes())
    return str(requirements_path)


def _display_validation_metrics(validation: dict[str, Any]) -> dict[str, Any]:
    """Render summary metrics and return the category lists."""
    col1, col2, col3, col4 = st.columns(4)

    compatible = validation.get("compatible", [])
    incompatible = validation.get("incompatible", [])
    updates_needed = validation.get("updates_needed", [])

    # Cast to proper types since they come from dict[str, Any]
    if not isinstance(compatible, list):
        compatible = []
    if not isinstance(incompatible, list):
        incompatible = []
    if not isinstance(updates_needed, list):
        updates_needed = []

    with col1:
        st.metric("Compatible", len(compatible))

    with col2:
        st.metric("Incompatible", len(incompatible))

    with col3:
        st.metric("Updates Needed", len(updates_needed))

    with col4:
        warnings = validation.get("warnings", [])
        warning_count = len(warnings) if isinstance(warnings, list) else 0
        st.metric("Warnings", warning_count)

    return {
        "compatible": compatible,
        "incompatible": incompatible,
        "updates_needed": updates_needed,
        "warnings": warnings if isinstance(warnings, list) else [],
    }


def _display_validation_summary(
    compatible: list[dict[str, str]],
    incompatible: list[dict[str, str]],
    updates_needed: list[dict[str, str]],
    warnings: list[str],
) -> None:
    """Render the summary tab."""
    st.subheader("Summary")

    total = len(compatible) + len(incompatible) + len(updates_needed)
    if total > 0:
        compat_pct = (len(compatible) / total) * 100
        st.progress(
            min(compat_pct / 100, 1.0),
            text=f"{compat_pct:.1f}% Compatible",
        )

    st.write(f"**Total Collections:** {total}")
    if total > 0:
        st.write(
            f"**Compatible:** {len(compatible)} ({len(compatible) / total * 100:.1f}%)"
        )
        st.write(
            f"**Incompatible:** {len(incompatible)} "
            f"({len(incompatible) / total * 100:.1f}%)"
        )
        st.write(
            f"**Updates Needed:** {len(updates_needed)} "
            f"({len(updates_needed) / total * 100:.1f}%)"
        )
    if warnings:
        st.write(f"**Warnings:** {len(warnings)}")


def _display_validation_compatible_tab(compatible: list[dict[str, str]]) -> None:
    """Render compatible collection details."""
    if compatible:
        st.subheader("Compatible Collections")
        col1, col2 = st.columns(2)
        for idx, item in enumerate(compatible):
            with col1 if idx % 2 == 0 else col2:
                collection = item.get("collection", "Unknown")
                version = item.get("version", "*")
                st.write(f"• {collection} ({version})")
    else:
        st.info("No fully compatible collections")


def _display_validation_requires_tab(updates_needed: list[dict[str, str]]) -> None:
    """Render collections that require updates."""
    if updates_needed:
        st.subheader("Collections Requiring Update")
        for item in updates_needed:
            collection = item.get("collection", "Unknown")
            current = item.get("current", "?")
            required = item.get("required", "?")
            with st.expander(
                f"{collection} (current: {current}, required: {required})"
            ):
                msg = (
                    "This collection must be updated to a "
                    "compatible version for your target "
                    "Ansible version. Your playbooks may not "
                    "work without this update."
                )
                st.write(msg)
    else:
        st.info("No collections require mandatory updates")


def _display_validation_warnings_tab(warnings: list[str]) -> None:
    """Render validation warnings."""
    if warnings:
        st.subheader("Validation Warnings")
        for warning in warnings:
            st.warning(warning)
    else:
        st.info("No warnings")


def _display_validation_incompatible_tab(incompatible: list[dict[str, str]]) -> None:
    """Render incompatible collections."""
    if incompatible:
        st.error(f"Incompatible Collections ({len(incompatible)})")
        for item in incompatible:
            collection = item.get("collection", "Unknown")
            version = item.get("version", "*")
            st.error(f"• {collection} ({version}) - Not compatible")
        st.markdown(
            """
        **Action Required:**
        These collections cannot be used with your target Ansible
        version. You must either:
        1. Remove the collections if no longer needed
        2. Find compatible replacement collections
        3. Choose a different target Ansible version
        """
        )
    else:
        st.success("No incompatible collections detected!")


def _display_validation_tabs(
    validation: dict[str, Any],
    compatible: list[dict[str, str]],
    incompatible: list[dict[str, str]],
    updates_needed: list[dict[str, str]],
    warnings: list[str],
) -> None:
    """Render the validation results tabs."""
    tabs = st.tabs(
        [
            "Summary",
            "Compatible",
            "Incompatible",
            "Updates Needed",
            "Warnings",
        ]
    )

    with tabs[0]:
        _display_validation_summary(compatible, incompatible, updates_needed, warnings)

    with tabs[1]:
        _display_validation_compatible_tab(compatible)

    with tabs[2]:
        _display_validation_incompatible_tab(incompatible)

    with tabs[3]:
        _display_validation_requires_tab(updates_needed)

    with tabs[4]:
        _display_validation_warnings_tab(warnings)


def _display_validation_export(validation: dict[str, Any], target_version: str) -> None:
    """Provide a JSON export for validation results."""
    st.divider()
    st.subheader("Export Validation Report")

    report_json = json.dumps(validation, indent=2, default=str)
    st.download_button(
        label="Download Validation Report as JSON",
        data=report_json,
        file_name=f"ansible_collection_validation_{target_version}.json",
        mime="application/json",
    )


def _display_validation_help() -> None:
    """Render the validation help section."""
    st.divider()
    with st.expander("Validation Help"):
        st.markdown(
            """
        **Requirements File Format:**

        Your requirements file should be in Ansible Galaxy format:

        ```yaml
        collections:
          - name: community.general
            version: ">=5.0.0"
          - name: ansible.posix
            version: "7.1.0"
        ```

        **Validation Results:**

        **Compatible** - Collection works with target version
        **Requires Update** - Must update for compatibility
        **May Update** - Recommended to update
        **Incompatible** - Cannot be used at all

        **Next Steps:**

        1. Review incompatible collections
        2. Update or replace incompatible collections
        3. Test your playbooks with new versions
        4. Deploy with confidence
        """
        )


def show_ansible_validation_page() -> None:
    """
    Display the Ansible Collection Validation page.

    Validates collection compatibility for a target Ansible version,
    identifying collections that need updates or may have issues.
    """
    _display_validation_intro()
    collections_file, target_version, validate_btn = _render_validation_inputs()

    if validate_btn:
        if not collections_file:
            st.error("Please upload a requirements file")
        else:
            try:
                tmp_path = _save_uploaded_file(collections_file)

                with st.spinner(
                    f"Validating collections for Ansible {target_version}..."
                ):
                    # Parse requirements file to extract collections
                    collections = parse_requirements_yml(tmp_path)
                    # Validate the collections against target version
                    validation = validate_collection_compatibility(
                        collections, target_version
                    )

                st.divider()
                st.subheader("Validation Results")

                categories = _display_validation_metrics(validation)
                _display_validation_tabs(
                    validation,
                    categories["compatible"],
                    categories["incompatible"],
                    categories["updates_needed"],
                    categories["warnings"],
                )
                _display_validation_export(validation, target_version)

                # Clean up temporary directory
                try:
                    tmp_dir = Path(tmp_path).parent
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass

            except Exception as e:
                st.error(f"Error validating collections: {str(e)}")
                st.exception(e)

    _display_validation_help()
