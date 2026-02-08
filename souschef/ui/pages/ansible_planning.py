"""Ansible Upgrade Planning Page for SousChef UI."""

import json
import sys
from pathlib import Path
from typing import Any

import streamlit as st

# Add the parent directory to the path so we can import souschef modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from souschef.ansible_upgrade import generate_upgrade_plan
from souschef.core.ansible_versions import ANSIBLE_VERSIONS


def _display_planning_intro() -> None:
    """Render the planning page title and introduction."""
    st.title("Ansible Upgrade Planning")
    st.markdown(
        """
    Plan your Ansible upgrade by selecting source and target versions.
    View breaking changes, deprecated features, and estimated effort.
    """
    )


def _render_planning_inputs() -> tuple[str, str, bool]:
    """Render version inputs and return selections plus button state."""
    col1, col2, col3 = st.columns(3)

    with col1:
        current_version = st.selectbox(
            "Current Ansible Version",
            options=sorted(ANSIBLE_VERSIONS.keys(), reverse=True),
            help="Your current Ansible version",
        )

    with col2:
        target_version = st.selectbox(
            "Target Ansible Version",
            options=sorted(ANSIBLE_VERSIONS.keys(), reverse=True),
            help="Target Ansible version for upgrade",
        )

    with col3:
        plan_btn = st.button("Generate Plan", use_container_width=True)

    return current_version, target_version, plan_btn


def _version_key(current_version: str, target_version: str) -> str:
    """Build a stable session state key for the version pair."""
    return f"{current_version}->{target_version}"


def _should_generate_plan(
    plan_btn: bool, current_version: str, target_version: str
) -> bool:
    """Decide whether to generate or reuse a stored plan."""
    if plan_btn:
        return True

    stored_plan = st.session_state.get("ansible_upgrade_plan")
    stored_version = st.session_state.get("plan_version")
    return bool(stored_plan) and stored_version == _version_key(
        current_version, target_version
    )


def _display_upgrade_path_section(upgrade_path: dict[str, Any]) -> None:
    """Display the upgrade path details."""
    st.subheader("Upgrade Path")
    from_ver = upgrade_path.get("from_version", "?")
    to_ver = upgrade_path.get("to_version", "?")
    intermediate = upgrade_path.get("intermediate_versions", [])

    if isinstance(intermediate, list) and intermediate:
        path_str = f"{from_ver} → {' → '.join(intermediate)} → {to_ver}"
    else:
        path_str = f"{from_ver} → {to_ver}"

    st.write(path_str)
    if isinstance(intermediate, list):
        st.caption(f"Upgrade steps: {len(intermediate) + 1}")


def _display_risk_level(risk: str) -> None:
    """Display the risk level with appropriate styling."""
    if risk == "Low":
        st.info("Risk Level: Low")
    elif risk == "Medium":
        st.warning("Risk Level: Medium")
    elif risk == "High":
        st.error("Risk Level: High")


def _display_plan_overview_tab(plan: dict[str, Any]) -> None:
    """Render the overview tab content."""
    col1, col2 = st.columns(2)

    with col1:
        if "upgrade_path" in plan:
            upgrade_path = plan["upgrade_path"]
            if isinstance(upgrade_path, dict):
                _display_upgrade_path_section(upgrade_path)

    with col2:
        if "estimated_effort_days" in plan:
            effort = plan["estimated_effort_days"]
            st.metric("Estimated Effort", f"{effort} days")
        if "upgrade_path" in plan and isinstance(plan["upgrade_path"], dict):
            risk = plan["upgrade_path"].get("risk_level", "unknown")
            _display_risk_level(risk)


def _truncate_text(text: str, max_length: int = 60) -> str:
    """Truncate text to max_length with ellipsis if needed."""
    return text[:max_length] + ("..." if len(text) > max_length else "")


def _display_breaking_changes_list(breaking: list[Any]) -> None:
    """Display list of breaking changes in expanders."""
    st.subheader(f"Breaking Changes ({len(breaking)})")
    for idx, change in enumerate(breaking, 1):
        display_text = _truncate_text(
            str(change) if not isinstance(change, str) else change
        )
        with st.expander(f"{idx}. {display_text}"):
            st.write(change)


def _display_plan_breaking_tab(plan: dict[str, Any]) -> None:
    """Render breaking change details."""
    breaking = plan.get("breaking_changes", [])
    if not isinstance(breaking, list) or not breaking:
        st.info("No breaking changes detected")
        return

    _display_breaking_changes_list(breaking)


def _display_deprecated_features_list(deprecated: list[Any]) -> None:
    """Display list of deprecated features in expanders."""
    st.subheader(f"Deprecated Features ({len(deprecated)})")
    for idx, feature in enumerate(deprecated, 1):
        if isinstance(feature, str):
            display_text = feature[:60] + ("..." if len(feature) > 60 else "")
        else:
            display_text = str(feature)[:60]
        with st.expander(f"{idx}. {display_text}"):
            st.write(feature)


def _display_plan_deprecated_tab(plan: dict[str, Any]) -> None:
    """Render deprecated feature details."""
    deprecated = plan.get("deprecated_features", [])
    if not isinstance(deprecated, list) or not deprecated:
        st.info("No deprecated features identified")
        return

    _display_deprecated_features_list(deprecated)


def _get_collection_list(impacts: dict[str, Any], key: str) -> list[Any]:
    """Extract and validate a collection list from impacts."""
    items = impacts.get(key, [])
    return items if isinstance(items, list) else []


def _display_collection_metrics(impacts: dict[str, Any]) -> None:
    """Display collection impact metrics in columns."""
    req = _get_collection_list(impacts, "requires_update")
    may = _get_collection_list(impacts, "may_require_update")
    compat = _get_collection_list(impacts, "compatible")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Requires Update", len(req))
    with col2:
        st.metric("May Require Update", len(may))
    with col3:
        st.metric("Compatible", len(compat))


def _display_collection_section(title: str, emoji: str, collections: list[Any]) -> None:
    """Display a collection section with title and list."""
    if not collections:
        return

    st.subheader(f"{emoji} {title}")
    for collection in collections[:10]:
        st.write(f"• {collection}")
    if len(collections) > 10:
        st.info(f"... and {len(collections) - 10} more collections")


def _display_plan_collections_tab(plan: dict[str, Any]) -> None:
    """Render collection impact details."""
    if "collection_impacts" not in plan:
        return

    impacts = plan["collection_impacts"]
    if not isinstance(impacts, dict):
        return

    _display_collection_metrics(impacts)
    st.divider()

    req = _get_collection_list(impacts, "requires_update")
    may = _get_collection_list(impacts, "may_require_update")

    _display_collection_section("Requires Update", "", req)
    _display_collection_section("May Require Update", "", may)


def _display_pre_upgrade_checklist(checklist: Any) -> None:
    """Display the pre-upgrade checklist in an expander."""
    if isinstance(checklist, list):
        with st.expander("Pre-Upgrade Checklist"):
            for item in checklist:
                st.write(f"☐ {item}")


def _display_testing_strategy(testing: Any) -> None:
    """Display the testing strategy in an expander."""
    if isinstance(testing, list):
        with st.expander("Testing Strategy"):
            for test in testing:
                st.write(f"• {test}")


def _display_post_upgrade_validation(validation: Any) -> None:
    """Display the post-upgrade validation in an expander."""
    if isinstance(validation, list):
        with st.expander("Post-Upgrade Validation"):
            for check in validation:
                st.write(f"• {check}")


def _display_plan_testing_tab(plan: dict[str, Any]) -> None:
    """Render testing strategy details."""
    st.subheader("Testing Strategy")

    if "pre_upgrade_checklist" in plan:
        _display_pre_upgrade_checklist(plan["pre_upgrade_checklist"])

    if "testing_strategy" in plan:
        _display_testing_strategy(plan["testing_strategy"])

    if "post_upgrade_validation" in plan:
        _display_post_upgrade_validation(plan["post_upgrade_validation"])


def _display_plan_tabs(plan: dict[str, Any]) -> None:
    """Render the plan output tabs."""
    tabs = st.tabs(
        [
            "Overview",
            "Breaking Changes",
            "Deprecated Features",
            "Collections",
            "Testing",
        ]
    )

    with tabs[0]:
        _display_plan_overview_tab(plan)

    with tabs[1]:
        _display_plan_breaking_tab(plan)

    with tabs[2]:
        _display_plan_deprecated_tab(plan)

    with tabs[3]:
        _display_plan_collections_tab(plan)

    with tabs[4]:
        _display_plan_testing_tab(plan)


def _display_plan_export(
    plan: dict[str, Any], current_version: str, target_version: str
) -> None:
    """Provide a JSON export for the upgrade plan."""
    st.divider()
    st.subheader("Export Plan")

    plan_json = json.dumps(plan, indent=2, default=str)
    st.download_button(
        label="Download Plan as JSON",
        data=plan_json,
        file_name=(f"ansible_upgrade_plan_{current_version}_to_{target_version}.json"),
        mime="application/json",
    )


def _display_planning_help() -> None:
    """Render the planning help section."""
    st.divider()
    with st.expander("Planning Help"):
        st.markdown(
            """
        **What is an upgrade plan?**

        An upgrade plan details what you need to do to move from one
        Ansible version to another. It includes:

        - **Upgrade Path**: The recommended sequence of steps
        - **Breaking Changes**: Incompatible changes between versions
        - **Deprecated Features**: Old features no longer supported
        - **Collection Updates**: Which collections need updating
        - **Risk Assessment**: Overall risk level of the upgrade

        **Breaking Changes vs Deprecated Features:**

        - **Breaking Changes** will stop your playbooks from working
        - **Deprecated Features** will warn but still work for now

        **Risk Levels:**

        - **Low**: Few changes, mostly collections working
        - **Medium**: Some breaking changes, collection updates needed
        - **High**: Major changes, extensive testing required
        """
        )


def show_ansible_planning_page() -> None:
    """
    Display the Ansible Upgrade Planning page.

    Generates and displays a detailed upgrade plan between two Ansible versions,
    including breaking changes, deprecated features, and recommended actions.
    """
    _display_planning_intro()
    current_version, target_version, plan_btn = _render_planning_inputs()

    if _should_generate_plan(plan_btn, current_version, target_version):
        if current_version == target_version:
            st.warning("Current and target versions are the same!")
        else:
            try:
                msg = (
                    f"Generating upgrade plan from {current_version} to "
                    f"{target_version}..."
                )
                with st.spinner(msg):
                    plan = generate_upgrade_plan(current_version, target_version)

                st.session_state.ansible_upgrade_plan = plan
                st.session_state.plan_version = _version_key(
                    current_version, target_version
                )

                st.divider()
                st.subheader("Upgrade Plan Generated")
                st.markdown(
                    f"Planning upgrade from **Ansible {current_version}** to "
                    f"**Ansible {target_version}**"
                )

                _display_plan_tabs(plan)
                _display_plan_export(plan, current_version, target_version)

            except Exception as e:
                st.error(f"Error generating upgrade plan: {str(e)}")
                st.exception(e)

    _display_planning_help()
