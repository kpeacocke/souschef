"""Advanced filtering and saved searches for migration operations."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import streamlit as st

LOGGER = logging.getLogger(__name__)

SEARCHES_DIR = Path.home() / ".souschef" / "searches"
SAVED_SEARCHES_FILE = SEARCHES_DIR / "saved.json"


@dataclass
class FilterCriteria:
    """Filter criteria for migrations and resources."""

    tools: list[str] = field(default_factory=list)  # Chef, Puppet, etc.
    complexity: list[str] = field(default_factory=list)  # simple, medium, complex
    risk_levels: list[str] = field(default_factory=list)  # low, medium, high, critical
    status: list[str] = field(
        default_factory=list
    )  # not started, in progress, completed
    tags: list[str] = field(default_factory=list)  # user-defined tags
    has_dependencies: bool | None = None  # Filter by dependency existence
    search_text: str = ""  # Free-text search


def _ensure_searches_dir() -> None:
    """Ensure saved searches directory exists."""
    SEARCHES_DIR.mkdir(parents=True, exist_ok=True)


def _load_saved_searches() -> dict[str, FilterCriteria]:
    """
    Load all saved searches from disk.

    Returns:
        Dictionary mapping search name to FilterCriteria.

    """
    _ensure_searches_dir()

    if not SAVED_SEARCHES_FILE.exists():
        return {}

    try:
        with SAVED_SEARCHES_FILE.open() as f:
            data = json.load(f)
            return {name: FilterCriteria(**criteria) for name, criteria in data.items()}
    except (OSError, json.JSONDecodeError, TypeError) as e:
        LOGGER.warning(f"Could not load saved searches: {e}")
        return {}


def _save_searches(searches: dict[str, FilterCriteria]) -> None:
    """
    Save all searches to disk.

    Args:
        searches: Dictionary mapping search name to FilterCriteria.

    """
    _ensure_searches_dir()

    try:
        with SAVED_SEARCHES_FILE.open("w") as f:
            data = {name: asdict(criteria) for name, criteria in searches.items()}
            json.dump(data, f, indent=2)
    except OSError as e:
        LOGGER.warning(f"Could not save searches: {e}")


def save_search(search_name: str, criteria: FilterCriteria) -> None:
    """
    Save a filter criteria set with a given name.

    Args:
        search_name: Name for this saved search.
        criteria: FilterCriteria to save.

    """
    searches = _load_saved_searches()
    searches[search_name] = criteria
    _save_searches(searches)


def delete_search(search_name: str) -> None:
    """
    Delete a saved search.

    Args:
        search_name: Name of search to delete.

    """
    searches = _load_saved_searches()
    if search_name in searches:
        del searches[search_name]
        _save_searches(searches)


def get_search(search_name: str) -> FilterCriteria | None:
    """
    Get a saved search by name.

    Args:
        search_name: Name of search to retrieve.

    Returns:
        FilterCriteria or None if not found.

    """
    searches = _load_saved_searches()
    return searches.get(search_name)


def list_saved_searches() -> list[str]:
    """
    List all saved search names.

    Returns:
        List of saved search names.

    """
    searches = _load_saved_searches()
    return sorted(searches.keys())


def apply_filters(
    items: list[dict[str, Any]], criteria: FilterCriteria
) -> list[dict[str, Any]]:
    """
    Filter a list of items based on criteria.

    Args:
        items: List of item dictionaries to filter.
        criteria: FilterCriteria to apply.

    Returns:
        Filtered list of items.

    """
    filtered = items

    # Tool filter
    if criteria.tools:
        filtered = [item for item in filtered if item.get("tool") in criteria.tools]

    # Complexity filter
    if criteria.complexity:
        filtered = [
            item for item in filtered if item.get("complexity") in criteria.complexity
        ]

    # Risk level filter
    if criteria.risk_levels:
        filtered = [
            item for item in filtered if item.get("risk_level") in criteria.risk_levels
        ]

    # Status filter
    if criteria.status:
        filtered = [item for item in filtered if item.get("status") in criteria.status]

    # Tags filter
    if criteria.tags:
        filtered = [
            item
            for item in filtered
            if any(tag in item.get("tags", []) for tag in criteria.tags)
        ]

    # Dependencies filter
    if criteria.has_dependencies is not None:
        has_deps = criteria.has_dependencies
        filtered = [
            item
            for item in filtered
            if (len(item.get("dependencies", [])) > 0) == has_deps
        ]

    # Free-text search
    if criteria.search_text:
        search_lower = criteria.search_text.lower()
        filtered = [
            item
            for item in filtered
            if search_lower in (item.get("name", "").lower() or "")
            or search_lower in (item.get("description", "").lower() or "")
            or search_lower in (item.get("path", "").lower() or "")
        ]

    return filtered


def show_filter_panel() -> FilterCriteria:
    """
    Display interactive filter panel and return selected criteria.

    Returns:
        FilterCriteria based on user selections.

    """
    st.sidebar.divider()
    st.sidebar.subheader("Filters")

    # Tool filter
    tools = st.sidebar.multiselect(
        "Tool",
        ["Chef", "Puppet", "PowerShell", "Salt", "Bash"],
        help="Filter by source tool",
    )

    # Complexity filter
    complexity = st.sidebar.multiselect(
        "Complexity",
        ["Simple", "Medium", "Complex"],
        help="Filter by complexity level",
    )

    # Risk filter
    risk_levels = st.sidebar.multiselect(
        "Risk",
        ["Low", "Medium", "High", "Critical"],
        help="Filter by risk level",
    )

    # Status filter
    status = st.sidebar.multiselect(
        "Status",
        ["Not Started", "In Progress", "Completed"],
        help="Filter by migration status",
    )

    # Dependencies filter
    dep_filter = st.sidebar.radio(
        "Dependencies",
        ["All", "With Dependencies", "No Dependencies"],
        help="Filter by dependency presence",
    )
    has_dependencies = None
    if dep_filter == "With Dependencies":
        has_dependencies = True
    elif dep_filter == "No Dependencies":
        has_dependencies = False

    # Free-text search
    search_text = st.sidebar.text_input(
        "Search",
        "",
        placeholder="Search by name, path...",
        help="Free-text search across names and paths",
    )

    # Saved searches
    st.sidebar.divider()
    saved_searches = list_saved_searches()
    if saved_searches:
        st.sidebar.subheader("Saved Searches")
        selected_saved = st.sidebar.selectbox(
            "Load saved search",
            [""] + saved_searches,
            key="load_saved_search",
        )
        if selected_saved:
            criteria = get_search(selected_saved)
            if criteria:
                st.session_state.current_filter = criteria
                st.rerun()

    # Save current search
    if (
        st.sidebar.button("💾 Save Current Search")
        and "save_search_mode" not in st.session_state
    ):
        st.session_state.save_search_mode = True
        st.rerun()

    return FilterCriteria(
        tools=tools,
        complexity=[c.lower() for c in complexity],
        risk_levels=[r.lower() for r in risk_levels],
        status=[s.lower() for s in status],
        has_dependencies=has_dependencies,
        search_text=search_text,
    )


def show_save_search_dialog() -> None:
    """Show modal dialog to save current search with a name."""
    if st.session_state.get("save_search_mode"):
        with st.form("save_search_form"):
            search_name = st.text_input(
                "Search Name",
                placeholder="e.g., 'High-risk Chef conversions'",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save") and search_name:
                    criteria = FilterCriteria(
                        tools=st.session_state.get("filter_tools", []),
                        complexity=st.session_state.get("filter_complexity", []),
                        risk_levels=st.session_state.get("filter_risk", []),
                        status=st.session_state.get("filter_status", []),
                    )
                    save_search(search_name, criteria)
                    st.success(f"Saved search: {search_name}")
                    st.session_state.save_search_mode = False
                    st.rerun()
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.save_search_mode = False
                    st.rerun()
