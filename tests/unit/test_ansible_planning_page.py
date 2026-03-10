"""Comprehensive tests for ansible_planning UI page to achieve 100% coverage."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, Mock, patch

from souschef.ansible_upgrade import UpgradePath, UpgradePlan


class SessionState(dict):
    """Session state helper that supports attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value

    def __delattr__(self, name: str):
        if name in self:
            del self[name]
        else:
            raise AttributeError(name)


def _ctx() -> MagicMock:
    """Create a context manager mock for Streamlit columns/expanders/etc."""
    mock = MagicMock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    return mock


class TestDisplayPlanningIntro:
    """Test planning page intro display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_intro(self, mock_st):
        """Test that intro title and markdown are displayed."""
        from souschef.ui.pages.ansible_planning import _display_planning_intro

        _display_planning_intro()

        mock_st.title.assert_called_once_with("Ansible Upgrade Planning")
        mock_st.markdown.assert_called_once()


class TestRenderPlanningInputs:
    """Test planning inputs rendering."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_render_inputs(self, mock_st):
        """Test input rendering and button state."""
        from souschef.ui.pages.ansible_planning import _render_planning_inputs

        col1, col2, col3 = _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3)

        # Mock selectbox to return versions
        with (
            patch.object(col1, "__enter__", return_value=col1),
            patch.object(col1, "__exit__", return_value=False),
            patch.object(col2, "__enter__", return_value=col2),
            patch.object(col2, "__exit__", return_value=False),
            patch.object(col3, "__enter__", return_value=col3),
            patch.object(col3, "__exit__", return_value=False),
        ):
            mock_st.selectbox.side_effect = ["2.14", "2.15"]
            mock_st.button.return_value = True

            current, target, plan_btn = _render_planning_inputs()

            assert current == "2.14"
            assert target == "2.15"
            assert plan_btn is True

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_render_inputs_button_false(self, mock_st):
        """Test with button not pressed."""
        from souschef.ui.pages.ansible_planning import _render_planning_inputs

        col1, col2, col3 = _ctx(), _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2, col3)
        mock_st.selectbox.side_effect = ["2.13", "2.14"]
        mock_st.button.return_value = False

        current, target, plan_btn = _render_planning_inputs()

        assert current == "2.13"
        assert target == "2.14"
        assert plan_btn is False


class TestVersionKey:
    """Test version key generation."""

    def test_version_key(self):
        """Test stable key generation from version pair."""
        from souschef.ui.pages.ansible_planning import _version_key

        key = _version_key("2.14", "2.15")
        assert key == "2.14->2.15"

    def test_version_key_consistent(self):
        """Test that key generation is consistent."""
        from souschef.ui.pages.ansible_planning import _version_key

        key1 = _version_key("2.10", "2.12")
        key2 = _version_key("2.10", "2.12")
        assert key1 == key2


class TestShouldGeneratePlan:
    """Test plan generation decision logic."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_should_generate_when_button_pressed(self, mock_st):
        """Test that plan generates when button is pressed."""
        from souschef.ui.pages.ansible_planning import _should_generate_plan

        mock_st.session_state = SessionState()

        result = _should_generate_plan(True, "2.14", "2.15")
        assert result is True

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_should_not_generate_when_button_not_pressed(self, mock_st):
        """Test no generation when button not pressed and no cached plan."""
        from souschef.ui.pages.ansible_planning import _should_generate_plan

        mock_st.session_state = SessionState()

        result = _should_generate_plan(False, "2.14", "2.15")
        assert result is False

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_reuse_cached_plan_same_version(self, mock_st):
        """Test reusing cached plan with same version pair."""
        from souschef.ui.pages.ansible_planning import _should_generate_plan

        plan = {"upgrade_path": {"from_version": "2.14"}}
        mock_st.session_state = SessionState(
            {
                "ansible_upgrade_plan": plan,
                "plan_version": "2.14->2.15",
            }
        )

        result = _should_generate_plan(False, "2.14", "2.15")
        assert result is True

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_regenerate_on_version_change(self, mock_st):
        """Test that version change triggers regeneration."""
        from souschef.ui.pages.ansible_planning import _should_generate_plan

        plan = {"upgrade_path": {"from_version": "2.14"}}
        mock_st.session_state = SessionState(
            {
                "ansible_upgrade_plan": plan,
                "plan_version": "2.14->2.15",
            }
        )

        result = _should_generate_plan(False, "2.13", "2.15")
        assert result is False


class TestDisplayUpgradePath:
    """Test upgrade path section display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_path_direct(self, mock_st):
        """Test displaying direct upgrade path without intermediates."""
        from souschef.ui.pages.ansible_planning import _display_upgrade_path_section

        upgrade_path = cast(
            UpgradePath,
            {
                "from_version": "2.14",
                "to_version": "2.15",
                "intermediate_versions": [],
            },
        )

        _display_upgrade_path_section(upgrade_path)

        mock_st.subheader.assert_called_once_with("Upgrade Path")
        assert mock_st.write.call_count == 1

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_path_with_intermediates(self, mock_st):
        """Test displaying path with intermediate versions."""
        from souschef.ui.pages.ansible_planning import _display_upgrade_path_section

        upgrade_path = cast(
            UpgradePath,
            {
                "from_version": "2.13",
                "to_version": "2.15",
                "intermediate_versions": ["2.14"],
            },
        )

        _display_upgrade_path_section(upgrade_path)

        # Should display path and intermediate count
        assert mock_st.write.call_count == 1
        assert mock_st.caption.call_count == 1

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_path_missing_keys(self, mock_st):
        """Test handling of missing path keys."""
        from souschef.ui.pages.ansible_planning import _display_upgrade_path_section

        upgrade_path = cast(UpgradePath, {})

        _display_upgrade_path_section(upgrade_path)

        # Should still display with default values
        assert mock_st.subheader.called


class TestDisplayRiskLevel:
    """Test risk level display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_low_risk(self, mock_st):
        """Test low risk level display."""
        from souschef.ui.pages.ansible_planning import _display_risk_level

        _display_risk_level("Low")

        mock_st.info.assert_called_once_with("Risk Level: Low")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_medium_risk(self, mock_st):
        """Test medium risk level display."""
        from souschef.ui.pages.ansible_planning import _display_risk_level

        _display_risk_level("Medium")

        mock_st.warning.assert_called_once_with("Risk Level: Medium")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_high_risk(self, mock_st):
        """Test high risk level display."""
        from souschef.ui.pages.ansible_planning import _display_risk_level

        _display_risk_level("High")

        mock_st.error.assert_called_once_with("Risk Level: High")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_unknown_risk(self, mock_st):
        """Test unknown risk level (no specific handling)."""
        from souschef.ui.pages.ansible_planning import _display_risk_level

        _display_risk_level("Unknown")

        # Should not call any display method for unknown risk
        assert not mock_st.info.called
        assert not mock_st.warning.called
        assert not mock_st.error.called


class TestDisplayPlanOverviewTab:
    """Test overview tab content."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_upgrade_path_section")
    @patch("souschef.ui.pages.ansible_planning._display_risk_level")
    def test_display_overview_with_plan(self, mock_risk, mock_path, mock_st):
        """Test overview tab with complete plan."""
        from souschef.ui.pages.ansible_planning import _display_plan_overview_tab

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)

        plan = cast(
            UpgradePlan,
            {
                "upgrade_path": {
                    "from_version": "2.14",
                    "to_version": "2.15",
                    "estimated_effort_days": 3,
                    "risk_level": "Low",
                }
            },
        )

        _display_plan_overview_tab(plan)

        mock_path.assert_called_once()
        mock_risk.assert_called_once_with("Low")
        assert mock_st.metric.called

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_overview_empty_plan(self, mock_st):
        """Test overview tab with empty plan."""
        from souschef.ui.pages.ansible_planning import _display_plan_overview_tab

        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)

        plan = cast(UpgradePlan, {})

        _display_plan_overview_tab(plan)

        # Should not crash, columns still created
        assert mock_st.columns.called


class TestTruncateText:
    """Test text truncation utility."""

    def test_truncate_long_text(self):
        """Test truncation of text longer than max length."""
        from souschef.ui.pages.ansible_planning import _truncate_text

        text = "This is a very long text that should be truncated"
        result = _truncate_text(text, max_length=10)

        assert len(result) == 13  # 10 chars + "..."
        assert result.endswith("...")

    def test_truncate_short_text(self):
        """Test that short text is not truncated."""
        from souschef.ui.pages.ansible_planning import _truncate_text

        text = "Short"
        result = _truncate_text(text, max_length=10)

        assert result == "Short"
        assert not result.endswith("...")

    def test_truncate_exact_length(self):
        """Test text exactly at max length."""
        from souschef.ui.pages.ansible_planning import _truncate_text

        text = "Exact text"
        result = _truncate_text(text, max_length=10)

        assert result == "Exact text"


class TestDisplayBreakingChangesList:
    """Test breaking changes list display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_breaking_changes(self, mock_st):
        """Test displaying breaking changes list."""
        from souschef.ui.pages.ansible_planning import _display_breaking_changes_list

        breaking = ["Change 1", "Change 2", "Change 3"]
        mock_st.expander.return_value = _ctx()

        _display_breaking_changes_list(breaking)

        mock_st.subheader.assert_called_once_with("Breaking Changes (3)")
        assert mock_st.expander.call_count == 3

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_breaking_changes_truncation(self, mock_st):
        """Test that long change text is truncated in expander labels."""
        from souschef.ui.pages.ansible_planning import _display_breaking_changes_list

        breaking = ["A" * 100]
        mock_st.expander.return_value = _ctx()

        _display_breaking_changes_list(breaking)

        # Check that truncation happened in expander label
        call_args = mock_st.expander.call_args
        assert "..." in call_args[0][0]

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_breaking_changes_non_string(self, mock_st):
        """Test displaying non-string breaking changes."""
        from souschef.ui.pages.ansible_planning import _display_breaking_changes_list

        breaking = [{"type": "change", "desc": "something"}]
        mock_st.expander.return_value = _ctx()

        _display_breaking_changes_list(breaking)

        assert mock_st.expander.called


class TestDisplayPlanBreakingTab:
    """Test breaking changes tab."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_breaking_changes_list")
    def test_display_breaking_with_changes(self, mock_list, mock_st):
        """Test breaking tab with actual changes."""
        from souschef.ui.pages.ansible_planning import _display_plan_breaking_tab

        plan = cast(UpgradePlan, {"breaking_changes": ["Change 1", "Change 2"]})

        _display_plan_breaking_tab(plan)

        mock_list.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_breaking_no_changes(self, mock_st):
        """Test breaking tab with no changes."""
        from souschef.ui.pages.ansible_planning import _display_plan_breaking_tab

        plan = cast(UpgradePlan, {})

        _display_plan_breaking_tab(plan)

        mock_st.info.assert_called_once_with("No breaking changes detected")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_breaking_empty_list(self, mock_st):
        """Test breaking tab with empty list."""
        from souschef.ui.pages.ansible_planning import _display_plan_breaking_tab

        plan = cast(UpgradePlan, {"breaking_changes": []})

        _display_plan_breaking_tab(plan)

        mock_st.info.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_breaking_non_list(self, mock_st):
        """Test breaking tab with non-list value."""
        from souschef.ui.pages.ansible_planning import _display_plan_breaking_tab

        plan = cast(UpgradePlan, {"breaking_changes": "not a list"})

        _display_plan_breaking_tab(plan)

        mock_st.info.assert_called_once()


class TestDisplayDeprecatedFeaturesList:
    """Test deprecated features list display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_deprecated_features(self, mock_st):
        """Test displaying deprecated features list."""
        from souschef.ui.pages.ansible_planning import (
            _display_deprecated_features_list,
        )

        deprecated = ["Feature 1", "Feature 2"]
        mock_st.expander.return_value = _ctx()

        _display_deprecated_features_list(deprecated)

        mock_st.subheader.assert_called_once_with("Deprecated Features (2)")
        assert mock_st.expander.call_count == 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_deprecated_non_string(self, mock_st):
        """Test displaying non-string deprecated features."""
        from souschef.ui.pages.ansible_planning import (
            _display_deprecated_features_list,
        )

        deprecated = [123, {"feature": "test"}]
        mock_st.expander.return_value = _ctx()

        _display_deprecated_features_list(deprecated)

        assert mock_st.expander.call_count == 2


class TestDisplayPlanDeprecatedTab:
    """Test deprecated features tab."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_deprecated_features_list")
    def test_display_deprecated_with_features(self, mock_list, mock_st):
        """Test deprecated tab with actual features."""
        from souschef.ui.pages.ansible_planning import (
            _display_plan_deprecated_tab,
        )

        plan = cast(UpgradePlan, {"deprecated_features": ["Feature 1", "Feature 2"]})

        _display_plan_deprecated_tab(plan)

        mock_list.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_deprecated_no_features(self, mock_st):
        """Test deprecated tab with no features."""
        from souschef.ui.pages.ansible_planning import (
            _display_plan_deprecated_tab,
        )

        plan = cast(UpgradePlan, {})

        _display_plan_deprecated_tab(plan)

        mock_st.info.assert_called_once_with("No deprecated features detected")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_deprecated_empty_list(self, mock_st):
        """Test deprecated tab with empty list."""
        from souschef.ui.pages.ansible_planning import (
            _display_plan_deprecated_tab,
        )

        plan = cast(UpgradePlan, {"deprecated_features": []})

        _display_plan_deprecated_tab(plan)

        mock_st.info.assert_called_once()


class TestDisplayCollectionMetrics:
    """Test collection metrics display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collection_metrics(self, mock_st):
        """Test displaying collection metrics."""
        from souschef.ui.pages.ansible_planning import _display_collection_metrics

        collections = {"collection1": "1.0", "collection2": "2.0"}
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)

        _display_collection_metrics(collections)

        assert mock_st.metric.call_count == 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collection_metrics_empty(self, mock_st):
        """Test displaying empty collection metrics."""
        from souschef.ui.pages.ansible_planning import _display_collection_metrics

        collections = {}
        col1, col2 = _ctx(), _ctx()
        mock_st.columns.return_value = (col1, col2)

        _display_collection_metrics(collections)

        # Should still call metric with 0
        assert mock_st.metric.called


class TestDisplayCollectionSection:
    """Test collection section display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collection_section_with_items(self, mock_st):
        """Test displaying collection section with items."""
        from souschef.ui.pages.ansible_planning import _display_collection_section

        collections = ["col1", "col2", "col3"]

        _display_collection_section("Test Section", "🎯", collections)

        mock_st.subheader.assert_called_once()
        assert mock_st.write.call_count == 3

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collection_section_empty(self, mock_st):
        """Test that empty section is not displayed."""
        from souschef.ui.pages.ansible_planning import _display_collection_section

        collections = []

        _display_collection_section("Test Section", "🎯", collections)

        # Should not display anything for empty collection
        assert not mock_st.subheader.called

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collection_section_many_items(self, mock_st):
        """Test displaying many collection items with overflow."""
        from souschef.ui.pages.ansible_planning import _display_collection_section

        collections = [f"col{i}" for i in range(20)]

        _display_collection_section("Test Section", "🎯", collections)

        # Should display subheader, 10 items, and info about remaining
        assert mock_st.subheader.called
        assert mock_st.write.call_count == 10
        assert mock_st.info.called


class TestDisplayPlanCollectionsTab:
    """Test collections tab."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_collection_metrics")
    @patch("souschef.ui.pages.ansible_planning._display_collection_section")
    def test_display_collections_with_updates(
        self, mock_section, mock_metrics, mock_st
    ):
        """Test collections tab with updates."""
        from souschef.ui.pages.ansible_planning import _display_plan_collections_tab

        plan = cast(
            UpgradePlan,
            {
                "upgrade_path": {
                    "collection_updates_needed": {"col1": "1.0", "col2": "2.0"}
                }
            },
        )

        _display_plan_collections_tab(plan)

        mock_metrics.assert_called_once()
        mock_section.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collections_no_updates(self, mock_st):
        """Test collections tab with no updates."""
        from souschef.ui.pages.ansible_planning import _display_plan_collections_tab

        plan = cast(UpgradePlan, {"upgrade_path": {"collection_updates_needed": {}}})

        _display_plan_collections_tab(plan)

        mock_st.info.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_collections_no_upgrade_path(self, mock_st):
        """Test collections tab without upgrade path."""
        from souschef.ui.pages.ansible_planning import _display_plan_collections_tab

        plan = cast(UpgradePlan, {})

        _display_plan_collections_tab(plan)

        # Should handle gracefully
        assert not mock_st.info.called


class TestDisplayPreUpgradeChecklist:
    """Test pre-upgrade checklist display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_checklist(self, mock_st):
        """Test displaying pre-upgrade checklist."""
        from souschef.ui.pages.ansible_planning import _display_pre_upgrade_checklist

        checklist = ["Check 1", "Check 2", "Check 3"]
        mock_st.expander.return_value = _ctx()

        _display_pre_upgrade_checklist(checklist)

        mock_st.expander.assert_called_once_with("Pre-Upgrade Checklist")
        assert mock_st.write.call_count == 3

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_checklist_non_list(self, mock_st):
        """Test with non-list checklist."""
        from souschef.ui.pages.ansible_planning import _display_pre_upgrade_checklist

        checklist = "not a list"

        _display_pre_upgrade_checklist(checklist)

        # Should not do anything
        assert not mock_st.expander.called


class TestDisplayTestingPhases:
    """Test testing phases display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_testing_phases(self, mock_st):
        """Test displaying testing phases."""
        from souschef.ui.pages.ansible_planning import _display_testing_phases

        phases = [
            {"phase": "Phase 1", "steps": ["Step 1", "Step 2"]},
            {"phase": "Phase 2", "steps": ["Step 3"]},
        ]
        mock_st.expander.return_value = _ctx()

        _display_testing_phases(phases)

        assert mock_st.expander.call_count == 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_testing_phases_non_list(self, mock_st):
        """Test with non-list phases."""
        from souschef.ui.pages.ansible_planning import _display_testing_phases

        phases = "not a list"

        _display_testing_phases(phases)

        assert not mock_st.expander.called

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_testing_phases_invalid_item(self, mock_st):
        """Test with invalid phase items."""
        from souschef.ui.pages.ansible_planning import _display_testing_phases

        phases = [
            {"phase": "Phase 1", "steps": "not a list"},  # Invalid - will skip
            {"phase": "Phase 2"},  # Missing steps - gets default []
        ]
        mock_st.expander.return_value = _ctx()

        _display_testing_phases(phases)

        # Phase 1 should be skipped (steps not a list), Phase 2 should display
        assert mock_st.expander.call_count == 1

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_testing_phases_non_dict_phase(self, mock_st):
        """Test with non-dict phase items in list."""
        from souschef.ui.pages.ansible_planning import _display_testing_phases

        phases = [
            "not a dict",  # Should be skipped
            123,  # Should be skipped
            {"phase": "Valid Phase", "steps": ["Step 1"]},  # Should display
        ]
        mock_st.expander.return_value = _ctx()

        _display_testing_phases(phases)

        # Only valid dict phase should display
        assert mock_st.expander.call_count == 1


class TestDisplaySuccessCriteria:
    """Test success criteria display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_success_criteria(self, mock_st):
        """Test displaying success criteria."""
        from souschef.ui.pages.ansible_planning import _display_success_criteria

        success = ["Criteria 1", "Criteria 2"]
        mock_st.expander.return_value = _ctx()

        _display_success_criteria(success)

        mock_st.expander.assert_called_once_with("Success Criteria")
        assert mock_st.write.call_count == 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_success_criteria_non_list(self, mock_st):
        """Test with non-list success criteria."""
        from souschef.ui.pages.ansible_planning import _display_success_criteria

        success = "not a list"

        _display_success_criteria(success)

        assert not mock_st.expander.called

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_success_criteria_empty(self, mock_st):
        """Test with empty success criteria."""
        from souschef.ui.pages.ansible_planning import _display_success_criteria

        success = []

        _display_success_criteria(success)

        assert not mock_st.expander.called


class TestDisplayTestingStrategy:
    """Test testing strategy display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_testing_phases")
    @patch("souschef.ui.pages.ansible_planning._display_success_criteria")
    def test_display_testing_strategy(self, mock_criteria, mock_phases, mock_st):
        """Test displaying testing strategy."""
        from souschef.ui.pages.ansible_planning import _display_testing_strategy

        testing = {
            "phases": [{"phase": "Phase 1", "steps": ["Step 1"]}],
            "success_criteria": ["Criteria 1"],
        }

        _display_testing_strategy(testing)

        mock_phases.assert_called_once()
        mock_criteria.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_testing_phases")
    @patch("souschef.ui.pages.ansible_planning._display_success_criteria")
    def test_display_testing_strategy_empty(self, mock_criteria, mock_phases, mock_st):
        """Test with empty testing strategy."""
        from souschef.ui.pages.ansible_planning import _display_testing_strategy

        testing = {}

        _display_testing_strategy(testing)

        # Should still call with empty data
        mock_phases.assert_called_once()
        mock_criteria.assert_called_once()


class TestDisplayPostUpgradeValidation:
    """Test post-upgrade validation display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_validation_list(self, mock_st):
        """Test displaying validation checks."""
        from souschef.ui.pages.ansible_planning import (
            _display_post_upgrade_validation,
        )

        validation = ["Check 1", "Check 2"]
        mock_st.expander.return_value = _ctx()

        _display_post_upgrade_validation(validation)

        mock_st.expander.assert_called_once_with("Post-Upgrade Validation")
        assert mock_st.write.call_count == 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_validation_non_list(self, mock_st):
        """Test with non-list validation."""
        from souschef.ui.pages.ansible_planning import (
            _display_post_upgrade_validation,
        )

        validation = "not a list"

        _display_post_upgrade_validation(validation)

        assert not mock_st.expander.called


class TestDisplayPlanTestingTab:
    """Test testing tab display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_pre_upgrade_checklist")
    @patch("souschef.ui.pages.ansible_planning._display_testing_strategy")
    @patch("souschef.ui.pages.ansible_planning._display_post_upgrade_validation")
    def test_display_testing_tab_full(
        self, mock_validation, mock_strategy, mock_checklist, mock_st
    ):
        """Test testing tab with all sections."""
        from souschef.ui.pages.ansible_planning import _display_plan_testing_tab

        plan = cast(
            UpgradePlan,
            {
                "pre_upgrade_checklist": ["Check 1"],
                "testing_plan": {"phases": [], "success_criteria": []},
                "post_upgrade_validation": ["Validation 1"],
            },
        )

        _display_plan_testing_tab(plan)

        mock_st.subheader.assert_called_once_with("Testing Strategy")
        mock_checklist.assert_called_once()
        mock_strategy.assert_called_once()
        mock_validation.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_pre_upgrade_checklist")
    @patch("souschef.ui.pages.ansible_planning._display_testing_strategy")
    @patch("souschef.ui.pages.ansible_planning._display_post_upgrade_validation")
    def test_display_testing_tab_partial(
        self, mock_validation, mock_strategy, mock_checklist, mock_st
    ):
        """Test testing tab with only some sections."""
        from souschef.ui.pages.ansible_planning import _display_plan_testing_tab

        plan = cast(UpgradePlan, {"pre_upgrade_checklist": ["Check 1"]})

        _display_plan_testing_tab(plan)

        mock_checklist.assert_called_once()
        mock_strategy.assert_not_called()
        mock_validation.assert_not_called()


class TestDisplayPlanTabs:
    """Test plan tabs display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_plan_overview_tab")
    @patch("souschef.ui.pages.ansible_planning._display_plan_breaking_tab")
    @patch("souschef.ui.pages.ansible_planning._display_plan_deprecated_tab")
    @patch("souschef.ui.pages.ansible_planning._display_plan_collections_tab")
    @patch("souschef.ui.pages.ansible_planning._display_plan_testing_tab")
    def test_display_tabs(
        self,
        mock_testing,
        mock_collections,
        mock_deprecated,
        mock_breaking,
        mock_overview,
        mock_st,
    ):
        """Test that all tabs are displayed."""
        from souschef.ui.pages.ansible_planning import _display_plan_tabs

        # Create mock tabs
        tab_mocks = [_ctx(), _ctx(), _ctx(), _ctx(), _ctx()]
        mock_st.tabs.return_value = tab_mocks

        plan = cast(UpgradePlan, {})

        _display_plan_tabs(plan)

        mock_st.tabs.assert_called_once()
        assert mock_overview.called
        assert mock_breaking.called
        assert mock_deprecated.called
        assert mock_collections.called
        assert mock_testing.called


class TestDisplayPlanExport:
    """Test plan export display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_export(self, mock_st):
        """Test that export button is displayed."""
        from souschef.ui.pages.ansible_planning import _display_plan_export

        plan = cast(UpgradePlan, {"upgrade_path": {"from_version": "2.14"}})

        _display_plan_export(plan, "2.14", "2.15")

        mock_st.divider.assert_called_once()
        mock_st.subheader.assert_called_once_with("Export Plan")
        mock_st.download_button.assert_called_once()

        # Verify download button parameters
        call_args = mock_st.download_button.call_args
        assert "Download Plan as JSON" in call_args[1]["label"]
        assert "ansible_upgrade_plan_2.14_to_2.15.json" in call_args[1]["file_name"]


class TestDisplayPlanningHelp:
    """Test planning help section display."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_help(self, mock_st):
        """Test that help section is displayed."""
        from souschef.ui.pages.ansible_planning import _display_planning_help

        mock_st.expander.return_value = _ctx()

        _display_planning_help()

        mock_st.divider.assert_called_once()
        mock_st.expander.assert_called_once_with("Planning Help")
        mock_st.markdown.assert_called_once()


class TestShowAnsiblePlanningPage:
    """Test main planning page entry point."""

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_planning_intro")
    @patch("souschef.ui.pages.ansible_planning._render_planning_inputs")
    @patch("souschef.ui.pages.ansible_planning._should_generate_plan")
    @patch("souschef.ui.pages.ansible_planning._display_planning_help")
    def test_show_page_without_generation(
        self, mock_help, mock_should_gen, mock_inputs, mock_intro, mock_st
    ):
        """Test page display when plan should not be generated."""
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = ("2.14", "2.15", False)
        mock_should_gen.return_value = False

        show_ansible_planning_page()

        mock_intro.assert_called_once()
        mock_inputs.assert_called_once()
        mock_help.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_planning_intro")
    @patch("souschef.ui.pages.ansible_planning._render_planning_inputs")
    @patch("souschef.ui.pages.ansible_planning._should_generate_plan")
    @patch("souschef.ui.pages.ansible_planning.generate_upgrade_plan")
    @patch("souschef.ui.pages.ansible_planning._display_plan_tabs")
    @patch("souschef.ui.pages.ansible_planning._display_plan_export")
    @patch("souschef.ui.pages.ansible_planning._display_planning_help")
    def test_show_page_with_generation(
        self,
        mock_help,
        mock_export,
        mock_tabs,
        mock_gen_plan,
        mock_should_gen,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test page display when plan should be generated."""
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = ("2.14", "2.15", False)
        mock_should_gen.return_value = True
        mock_gen_plan.return_value = {"upgrade_path": {}}
        mock_st.spinner.return_value = _ctx()

        show_ansible_planning_page()

        mock_gen_plan.assert_called_once_with("2.14", "2.15")
        mock_tabs.assert_called_once()
        mock_export.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_planning_intro")
    @patch("souschef.ui.pages.ansible_planning._render_planning_inputs")
    @patch("souschef.ui.pages.ansible_planning._should_generate_plan")
    @patch("souschef.ui.pages.ansible_planning._display_planning_help")
    def test_show_page_same_version(
        self, mock_help, mock_should_gen, mock_inputs, mock_intro, mock_st
    ):
        """Test page when current and target versions are the same."""
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = ("2.14", "2.14", False)
        mock_should_gen.return_value = True

        show_ansible_planning_page()

        # Should show warning for same versions
        mock_st.warning.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_planning_intro")
    @patch("souschef.ui.pages.ansible_planning._render_planning_inputs")
    @patch("souschef.ui.pages.ansible_planning._should_generate_plan")
    @patch("souschef.ui.pages.ansible_planning.generate_upgrade_plan")
    @patch("souschef.ui.pages.ansible_planning._display_planning_help")
    def test_show_page_generation_error(
        self,
        mock_help,
        mock_gen_plan,
        mock_should_gen,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test page when plan generation raises an exception."""
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = ("2.14", "2.15", False)
        mock_should_gen.return_value = True
        mock_gen_plan.side_effect = ValueError("Invalid version")
        mock_st.spinner.return_value = _ctx()

        show_ansible_planning_page()

        # Should display error
        mock_st.error.assert_called_once()
        mock_st.exception.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    @patch("souschef.ui.pages.ansible_planning._display_planning_intro")
    @patch("souschef.ui.pages.ansible_planning._render_planning_inputs")
    @patch("souschef.ui.pages.ansible_planning._should_generate_plan")
    @patch("souschef.ui.pages.ansible_planning.generate_upgrade_plan")
    @patch("souschef.ui.pages.ansible_planning._display_plan_tabs")
    @patch("souschef.ui.pages.ansible_planning._display_plan_export")
    @patch("souschef.ui.pages.ansible_planning._display_planning_help")
    def test_show_page_plan_stored_in_session(
        self,
        mock_help,
        mock_export,
        mock_tabs,
        mock_gen_plan,
        mock_should_gen,
        mock_inputs,
        mock_intro,
        mock_st,
    ):
        """Test that plan is stored in session state."""
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        mock_inputs.return_value = ("2.14", "2.15", False)
        mock_should_gen.return_value = True
        mock_gen_plan.return_value = {"upgrade_path": {"from_version": "2.14"}}
        mock_st.spinner.return_value = _ctx()

        show_ansible_planning_page()

        # Check that session state was updated
        assert "ansible_upgrade_plan" in mock_st.session_state
        assert "plan_version" in mock_st.session_state
