"""Advanced filtering, saved searches, and search history for migration workflows."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import streamlit as st

LOGGER = logging.getLogger(__name__)

SEARCHES_DIR = Path.home() / ".souschef" / "searches"
SAVED_SEARCHES_FILE = SEARCHES_DIR / "saved.json"
SEARCH_HISTORY_FILE = SEARCHES_DIR / "history.json"
MAX_SEARCH_HISTORY = 50


@dataclass
class FilterCriteria:
    """Filter criteria for migrations and resources."""

    tools: list[str] = field(default_factory=list)
    complexity: list[str] = field(default_factory=list)
    risk_levels: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    has_dependencies: bool | None = None
    search_text: str = ""

    def is_empty(self) -> bool:
        """Return whether this criteria set has no active filters."""
        return not any(
            [
                self.tools,
                self.complexity,
                self.risk_levels,
                self.status,
                self.tags,
                self.has_dependencies is not None,
                self.search_text.strip(),
            ]
        )


def _ensure_searches_dir() -> None:
    """Ensure saved-search and history directory exists."""
    try:
        SEARCHES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        LOGGER.warning("Could not create %s: %s", SEARCHES_DIR, exc)


def _load_json(path: Path, fallback: Any) -> Any:
    """Load JSON from disk or return fallback when unavailable/invalid."""
    if not path.exists():
        return fallback

    try:
        with path.open(encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        LOGGER.warning("Could not load %s: %s", path, exc)
        return fallback


def _save_json(path: Path, value: Any) -> None:
    """Persist JSON value to disk, handling file errors gracefully."""
    _ensure_searches_dir()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file_obj:
            json.dump(value, file_obj, indent=2)
    except OSError as exc:
        LOGGER.warning("Could not save %s: %s", path, exc)


def _load_saved_searches() -> dict[str, FilterCriteria]:
    """Load saved searches keyed by name."""
    _ensure_searches_dir()
    raw = _load_json(SAVED_SEARCHES_FILE, {})

    if not isinstance(raw, dict):
        return {}

    saved: dict[str, FilterCriteria] = {}
    for name, criteria in raw.items():
        if isinstance(name, str) and isinstance(criteria, dict):
            try:
                saved[name] = FilterCriteria(**criteria)
            except TypeError as exc:
                LOGGER.warning("Skipping invalid saved search %s: %s", name, exc)

    return saved


def _save_searches(searches: dict[str, FilterCriteria]) -> None:
    """Save all named searches to disk."""
    data = {name: asdict(criteria) for name, criteria in searches.items()}
    _save_json(SAVED_SEARCHES_FILE, data)


def _load_search_history() -> list[dict[str, Any]]:
    """Load saved search history entries."""
    _ensure_searches_dir()
    raw = _load_json(SEARCH_HISTORY_FILE, [])

    if not isinstance(raw, list):
        return []

    history = [entry for entry in raw if isinstance(entry, dict)]
    return history[:MAX_SEARCH_HISTORY]


def _save_search_history(history: list[dict[str, Any]]) -> None:
    """Persist search history entries, capped to max history size."""
    _save_json(SEARCH_HISTORY_FILE, history[:MAX_SEARCH_HISTORY])


def save_search(search_name: str, criteria: FilterCriteria) -> None:
    """Save a named filter criteria set."""
    clean_name = search_name.strip()
    if not clean_name:
        return

    searches = _load_saved_searches()
    searches[clean_name] = criteria
    _save_searches(searches)


def delete_search(search_name: str) -> None:
    """Delete a named saved search."""
    searches = _load_saved_searches()
    if search_name in searches:
        del searches[search_name]
        _save_searches(searches)


def get_search(search_name: str) -> FilterCriteria | None:
    """Get a saved search by name."""
    return _load_saved_searches().get(search_name)


def list_saved_searches() -> list[str]:
    """List all saved-search names in alphabetical order."""
    return sorted(_load_saved_searches().keys())


def record_search(criteria: FilterCriteria, *, source: str = "manual") -> None:
    """Record a criteria set in search history for recall/audit."""
    if criteria.is_empty():
        return

    history = _load_search_history()
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "source": source,
        "criteria": asdict(criteria),
    }

    if history and history[0].get("criteria") == payload["criteria"]:
        return

    history.insert(0, payload)
    _save_search_history(history)


def list_search_history(limit: int = 10) -> list[dict[str, Any]]:
    """Return recent search history entries."""
    history = _load_search_history()
    return history[: max(0, limit)]


def clear_search_history() -> None:
    """Clear all persisted search history entries."""
    _save_search_history([])


def apply_filters(
    items: list[dict[str, Any]], criteria: FilterCriteria
) -> list[dict[str, Any]]:
    """Filter items based on tool, complexity, risk, status, tags, and text."""
    filtered = items

    if criteria.tools:
        filtered = [item for item in filtered if item.get("tool") in criteria.tools]

    if criteria.complexity:
        filtered = [
            item
            for item in filtered
            if (item.get("complexity") or "").lower() in criteria.complexity
        ]

    if criteria.risk_levels:
        filtered = [
            item
            for item in filtered
            if (item.get("risk_level") or "").lower() in criteria.risk_levels
        ]

    if criteria.status:
        filtered = [
            item
            for item in filtered
            if (item.get("status") or "").lower() in criteria.status
        ]

    if criteria.tags:
        filtered = [
            item
            for item in filtered
            if any(
                tag in [(item_tag or "").lower() for item_tag in item.get("tags", [])]
                for tag in criteria.tags
            )
        ]

    if criteria.has_dependencies is not None:
        filtered = [
            item
            for item in filtered
            if bool(item.get("dependencies")) == criteria.has_dependencies
        ]

    if criteria.search_text:
        search_lower = criteria.search_text.lower()
        filtered = [
            item
            for item in filtered
            if search_lower in (item.get("name", "") or "").lower()
            or search_lower in (item.get("description", "") or "").lower()
            or search_lower in (item.get("path", "") or "").lower()
        ]

    return filtered


def _criteria_from_session_state() -> FilterCriteria:
    """Build current criteria from streamlit session-state keys."""
    raw_tags = st.session_state.get("filter_tags", "")
    tags = [tag.strip().lower() for tag in raw_tags.split(",") if tag.strip()]

    return FilterCriteria(
        tools=st.session_state.get("filter_tools", []),
        complexity=[c.lower() for c in st.session_state.get("filter_complexity", [])],
        risk_levels=[r.lower() for r in st.session_state.get("filter_risk", [])],
        status=[s.lower() for s in st.session_state.get("filter_status", [])],
        tags=tags,
        has_dependencies=st.session_state.get("filter_has_dependencies"),
        search_text=st.session_state.get("filter_search_text", ""),
    )


def _hydrate_filter_state(criteria: FilterCriteria) -> None:
    """Write a criteria set into session state widget keys."""
    st.session_state.filter_tools = criteria.tools
    st.session_state.filter_complexity = [c.title() for c in criteria.complexity]
    st.session_state.filter_risk = [r.title() for r in criteria.risk_levels]
    st.session_state.filter_status = [s.title() for s in criteria.status]
    st.session_state.filter_tags = ", ".join(criteria.tags)
    st.session_state.filter_has_dependencies = criteria.has_dependencies
    st.session_state.filter_search_text = criteria.search_text
    st.session_state.current_filter = criteria


def show_filter_panel() -> FilterCriteria:
    """Display sidebar filters and saved-search controls."""
    current = st.session_state.get("current_filter", FilterCriteria())

    if "filter_tools" not in st.session_state:
        _hydrate_filter_state(current)

    st.sidebar.divider()
    st.sidebar.subheader("Filters")

    tools = st.sidebar.multiselect(
        "Tool",
        ["Chef", "Puppet", "PowerShell", "Salt", "Bash"],
        default=st.session_state.get("filter_tools", []),
        key="filter_tools",
        help="Filter by source tool.",
    )
    complexity = st.sidebar.multiselect(
        "Complexity",
        ["Simple", "Medium", "Complex"],
        default=st.session_state.get("filter_complexity", []),
        key="filter_complexity",
        help="Filter by complexity level.",
    )
    risk = st.sidebar.multiselect(
        "Risk",
        ["Low", "Medium", "High", "Critical"],
        default=st.session_state.get("filter_risk", []),
        key="filter_risk",
        help="Filter by risk level.",
    )
    status = st.sidebar.multiselect(
        "Status",
        ["Not Started", "In Progress", "Completed"],
        default=st.session_state.get("filter_status", []),
        key="filter_status",
        help="Filter by migration status.",
    )

    dep_index_map = {None: 0, True: 1, False: 2}
    dep_filter = st.sidebar.radio(
        "Dependencies",
        ["All", "With Dependencies", "No Dependencies"],
        index=dep_index_map[st.session_state.get("filter_has_dependencies")],
        help="Filter by dependency presence.",
    )
    st.session_state.filter_has_dependencies = {
        "All": None,
        "With Dependencies": True,
        "No Dependencies": False,
    }[dep_filter]

    tags_text = st.sidebar.text_input(
        "Tags",
        value=st.session_state.get("filter_tags", ""),
        key="filter_tags",
        placeholder="db, api, critical",
        help="Comma-separated tags.",
    )
    search_text = st.sidebar.text_input(
        "Search",
        value=st.session_state.get("filter_search_text", ""),
        key="filter_search_text",
        placeholder="Search by name, description, or path...",
        help="Free-text search across names, descriptions, and paths.",
    )

    st.session_state.filter_tools = tools
    st.session_state.filter_complexity = complexity
    st.session_state.filter_risk = risk
    st.session_state.filter_status = status
    st.session_state.filter_tags = tags_text
    st.session_state.filter_search_text = search_text

    st.sidebar.divider()
    st.sidebar.subheader("Saved Searches")
    saved_searches = list_saved_searches()
    selected_saved = st.sidebar.selectbox(
        "Load saved search",
        [""] + saved_searches,
        key="load_saved_search",
    )

    if selected_saved:
        loaded = get_search(selected_saved)
        if loaded:
            _hydrate_filter_state(loaded)
            record_search(loaded, source="saved")
            st.rerun()

    if st.sidebar.button("Save Current Search"):
        st.session_state.save_search_mode = True
        st.rerun()

    if selected_saved and st.sidebar.button("Delete Saved Search"):
        delete_search(selected_saved)
        st.success(f"Deleted saved search: {selected_saved}")
        st.session_state.load_saved_search = ""
        st.rerun()

    criteria = _criteria_from_session_state()
    st.session_state.current_filter = criteria

    previous = st.session_state.get("last_recorded_filter")
    if previous != criteria:
        record_search(criteria)
        st.session_state.last_recorded_filter = criteria

    return criteria


def show_save_search_dialog() -> None:
    """Show modal dialog for naming and saving current filters."""
    if not st.session_state.get("save_search_mode"):
        return

    with st.form("save_search_form"):
        search_name = st.text_input(
            "Search Name",
            placeholder="e.g. high-risk chef conversions",
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save") and search_name.strip():
                criteria = _criteria_from_session_state()
                save_search(search_name, criteria)
                st.success(f"Saved search: {search_name.strip()}")
                st.session_state.save_search_mode = False
                st.rerun()
        with col2:
            if st.form_submit_button("Cancel"):
                st.session_state.save_search_mode = False
                st.rerun()
