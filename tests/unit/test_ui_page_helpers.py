"""Additional helper-focused tests for UI page modules."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, Mock, patch


class SessionState(dict):
    """Session state helper that supports attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    """Create a mock context manager object."""
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


class TestAnsibleAssessmentHelpers:
    """Tests for ansible assessment page helpers."""

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_collections(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_collections

        mock_st.columns.return_value = [_ctx(), _ctx()]
        assessment = {
            "collections": {"community.general": "9.0.0", "ansible.posix": "1.5.4"}
        }

        _display_assessment_collections(cast(dict[str, object], assessment))

        mock_st.subheader.assert_called_once()
        assert mock_st.text.call_count == 2

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_warnings(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_warnings

        _display_assessment_warnings({"compatibility_issues": ["Issue A", "Issue B"]})

        mock_st.warning.assert_called_once()
        assert mock_st.write.call_count == 2

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_details(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_details

        mock_st.columns.return_value = [_ctx(), _ctx()]
        assessment = {
            "current_version_full": "2.15.0",
            "eol_status": {"status": "Supported", "security_risk": "Low"},
            "playbooks_scanned": 12,
        }

        _display_assessment_details(assessment)

        assert mock_st.write.call_count >= 3

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_show_ansible_assessment_page_error(self, mock_st):
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        mock_st.session_state = SessionState()
        with (
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=(".", True),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.assess_ansible_environment",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.st.spinner", return_value=_ctx()
            ),
        ):
            show_ansible_assessment_page()

        mock_st.error.assert_called()
        mock_st.exception.assert_called()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_show_ansible_assessment_page_success(self, mock_st):
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        mock_st.session_state = SessionState()
        with (
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=(".", True),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.assess_ansible_environment",
                return_value={
                    "current_version": "2.15",
                    "python_version": "3.11",
                    "eol_status": {"eol_date": "2027-01-01"},
                    "collections": {"community.general": "9.0.0"},
                },
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.st.spinner", return_value=_ctx()
            ),
        ):
            show_ansible_assessment_page()

        mock_st.subheader.assert_called()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_assessment_intro_help_and_export(self, mock_st):
        from souschef.ui.pages.ansible_assessment import (
            _display_assessment_export,
            _display_assessment_help,
            _display_assessment_intro,
        )

        mock_st.expander.return_value = _ctx()

        _display_assessment_intro()
        _display_assessment_help()
        _display_assessment_export({"a": 1})

        mock_st.title.assert_called_once()
        assert mock_st.markdown.called
        mock_st.download_button.assert_called_once()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_render_assessment_inputs(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _render_assessment_inputs

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.text_input.return_value = "/tmp/env"
        mock_st.button.return_value = True

        path, clicked = _render_assessment_inputs()
        assert path == "/tmp/env"
        assert clicked

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_show_ansible_assessment_page_from_session_state(self, mock_st):
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        mock_st.session_state = SessionState({"ansible_assessment_results": {"x": 1}})

        with (
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=(".", False),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.assess_ansible_environment",
                return_value={"current_version": "2.15"},
            ),
            patch(
                "souschef.ui.pages.ansible_assessment.st.spinner", return_value=_ctx()
            ),
        ):
            show_ansible_assessment_page()

        mock_st.divider.assert_called()


class TestAnsiblePlanningHelpers:
    """Tests for ansible planning page helpers."""

    def test_version_key_and_truncate(self):
        from souschef.ui.pages.ansible_planning import _truncate_text, _version_key

        assert _version_key("2.14", "2.16") == "2.14->2.16"
        assert _truncate_text("short", 10) == "short"
        assert _truncate_text("x" * 80, 10).endswith("...")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_should_generate_plan_states(self, mock_st):
        from souschef.ui.pages.ansible_planning import _should_generate_plan

        mock_st.session_state = SessionState(
            {"ansible_upgrade_plan": {"a": 1}, "plan_version": "2.14->2.15"}
        )

        assert _should_generate_plan(True, "2.14", "2.15")
        assert _should_generate_plan(False, "2.14", "2.15")
        assert not _should_generate_plan(False, "2.14", "2.16")

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_risk_level(self, mock_st):
        from souschef.ui.pages.ansible_planning import _display_risk_level

        _display_risk_level("Low")
        _display_risk_level("Medium")
        _display_risk_level("High")

        mock_st.info.assert_called_once()
        mock_st.warning.assert_called_once()
        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_plan_collections_tab(self, mock_st):
        from souschef.ansible_upgrade import UpgradePlan
        from souschef.ui.pages.ansible_planning import _display_plan_collections_tab

        mock_st.columns.return_value = [_ctx(), _ctx()]

        plan = {
            "upgrade_path": {
                "collection_updates_needed": {
                    "community.general": "9.0.0",
                    "ansible.posix": "1.5.4",
                }
            }
        }
        _display_plan_collections_tab(cast(UpgradePlan, plan))

        assert mock_st.metric.call_count == 2
        assert mock_st.write.call_count >= 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_plan_testing_tab(self, mock_st):
        from souschef.ansible_upgrade import UpgradePlan
        from souschef.ui.pages.ansible_planning import _display_plan_testing_tab

        mock_st.expander.return_value = _ctx()
        plan = {
            "pre_upgrade_checklist": ["Backup", "Freeze changes"],
            "testing_plan": {
                "phases": [{"phase": "Phase 1", "steps": ["Run smoke tests"]}],
                "success_criteria": ["No failures"],
            },
            "post_upgrade_validation": ["Run full suite"],
        }

        _display_plan_testing_tab(cast(UpgradePlan, plan))

        assert mock_st.expander.call_count >= 3

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_show_ansible_planning_page_success(self, mock_st):
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        with (
            patch(
                "souschef.ui.pages.ansible_planning._render_planning_inputs",
                return_value=("2.14", "2.15", True),
            ),
            patch(
                "souschef.ui.pages.ansible_planning.generate_upgrade_plan",
                return_value={
                    "upgrade_path": {"risk_level": "Low", "estimated_effort_days": 2}
                },
            ),
            patch("souschef.ui.pages.ansible_planning.st.spinner", return_value=_ctx()),
            patch("souschef.ui.pages.ansible_planning._display_plan_tabs"),
            patch("souschef.ui.pages.ansible_planning._display_plan_export"),
            patch("souschef.ui.pages.ansible_planning._display_planning_help"),
        ):
            show_ansible_planning_page()

        mock_st.subheader.assert_called()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_collections_non_dict(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_collections

        _display_assessment_collections({"collections": "bad"})
        mock_st.subheader.assert_not_called()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_collections_dict(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_collections

        mock_st.columns.return_value = [_ctx(), _ctx()]
        _display_assessment_collections(
            {"collections": {"community.general": "8.0.0", "ansible.posix": "1.5.4"}}
        )
        mock_st.subheader.assert_called_once()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_warnings_non_list(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_warnings

        _display_assessment_warnings({"compatibility_issues": "bad"})
        mock_st.warning.assert_not_called()

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_display_assessment_results_non_dict_eol(self, mock_st):
        from souschef.ui.pages.ansible_assessment import _display_assessment_results

        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
        with (
            patch(
                "souschef.ui.pages.ansible_assessment._display_assessment_collections"
            ),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_warnings"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_details"),
            patch("souschef.ui.pages.ansible_assessment._display_assessment_export"),
        ):
            _display_assessment_results(
                {
                    "current_version": "2.15",
                    "python_version": "3.12",
                    "eol_status": "n/a",
                }
            )

        assert mock_st.metric.call_count == 3

    @patch("souschef.ui.pages.ansible_assessment.st")
    def test_show_ansible_assessment_page_button_not_clicked(self, mock_st):
        from souschef.ui.pages.ansible_assessment import show_ansible_assessment_page

        mock_st.session_state = SessionState()
        with (
            patch(
                "souschef.ui.pages.ansible_assessment._render_assessment_inputs",
                return_value=("", False),
            ),
            patch(
                "souschef.ui.pages.ansible_assessment._display_assessment_help"
            ) as help_fn,
        ):
            show_ansible_assessment_page()

        help_fn.assert_called_once()


class TestAnsibleValidationHelpers:
    """Tests for ansible validation page helpers."""

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_validation_metrics(self, mock_st):
        from souschef.ui.pages.ansible_validation import _display_validation_metrics

        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx(), _ctx()]
        categories = _display_validation_metrics(
            {
                "compatible": [{"collection": "a"}],
                "incompatible": [],
                "updates_needed": [{"collection": "b"}],
                "warnings": ["w1"],
            }
        )

        assert categories["compatible"]
        assert categories["updates_needed"]
        assert mock_st.metric.call_count == 4

    def test_save_uploaded_file(self):
        from souschef.ui.pages.ansible_validation import _save_uploaded_file

        class Upload:
            def getbuffer(self):
                return memoryview(b"collections:\n  - name: community.general\n")

        path = _save_uploaded_file(Upload())
        assert path.endswith("requirements.yml")
        assert Path(path).exists()

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_display_validation_tabs(self, mock_st):
        from souschef.ui.pages.ansible_validation import _display_validation_tabs

        mock_st.tabs.return_value = [_ctx(), _ctx(), _ctx(), _ctx(), _ctx()]
        mock_st.columns.side_effect = lambda n: [_ctx() for _ in range(n)]

        _display_validation_tabs(
            {},
            [{"collection": "ok"}],
            [{"collection": "bad", "version": "*"}],
            [{"collection": "up", "current": "1", "required": "2"}],
            ["warn"],
        )

        assert mock_st.tabs.call_count == 1

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_show_ansible_validation_page_no_file(self, mock_st):
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        with (
            patch(
                "souschef.ui.pages.ansible_validation._render_validation_inputs",
                return_value=(None, "2.15", True),
            ),
            patch("souschef.ui.pages.ansible_validation._display_validation_help"),
        ):
            show_ansible_validation_page()

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_show_ansible_validation_page_success(self, mock_st):
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        upload = MagicMock()
        upload.getbuffer.return_value = memoryview(
            b"collections:\n  - name: community.general\n"
        )

        mock_st.spinner.return_value = _ctx()
        mock_st.tabs.return_value = [_ctx(), _ctx(), _ctx(), _ctx(), _ctx()]
        mock_st.columns.side_effect = lambda n: [_ctx() for _ in range(n)]
        mock_st.expander.return_value = _ctx()

        with (
            patch(
                "souschef.ui.pages.ansible_validation._render_validation_inputs",
                return_value=(upload, "2.15", True),
            ),
            patch(
                "souschef.ui.pages.ansible_validation._save_uploaded_file",
                return_value="/tmp/requirements.yml",
            ),
            patch(
                "souschef.ui.pages.ansible_validation.parse_requirements_yml",
                return_value=[{"name": "community.general", "version": "*"}],
            ),
            patch(
                "souschef.ui.pages.ansible_validation.validate_collection_compatibility",
                return_value={
                    "compatible": [{"collection": "community.general", "version": "*"}],
                    "incompatible": [],
                    "updates_needed": [],
                    "warnings": [],
                },
            ),
            patch("souschef.ui.pages.ansible_validation.shutil.rmtree"),
            patch("souschef.ui.pages.ansible_validation._display_validation_help"),
        ):
            show_ansible_validation_page()

        mock_st.subheader.assert_called()

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_validation_tabs_empty_states(self, mock_st):
        from souschef.ui.pages.ansible_validation import (
            _display_validation_compatible_tab,
            _display_validation_incompatible_tab,
            _display_validation_requires_tab,
            _display_validation_warnings_tab,
        )

        _display_validation_compatible_tab([])
        _display_validation_incompatible_tab([])
        _display_validation_requires_tab([])
        _display_validation_warnings_tab([])

        assert mock_st.info.call_count >= 3
        mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_validation_tabs_non_empty_states(self, mock_st):
        from souschef.ui.pages.ansible_validation import (
            _display_validation_compatible_tab,
            _display_validation_incompatible_tab,
            _display_validation_requires_tab,
            _display_validation_warnings_tab,
        )

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.expander.return_value = _ctx()

        _display_validation_compatible_tab(
            [{"collection": "community.general", "version": "9.0.0"}]
        )
        _display_validation_incompatible_tab(
            [{"collection": "bad.coll", "version": "1.0"}]
        )
        _display_validation_requires_tab(
            [{"collection": "needs.update", "current": "1", "required": "2"}]
        )
        _display_validation_warnings_tab(["warn 1"])

        assert mock_st.write.called
        assert mock_st.error.called
        assert mock_st.warning.called

    @patch("souschef.ui.pages.ansible_validation.st")
    def test_show_ansible_validation_page_exception(self, mock_st):
        from souschef.ui.pages.ansible_validation import show_ansible_validation_page

        upload = MagicMock()
        upload.getbuffer.return_value = memoryview(b"collections: []")
        mock_st.spinner.return_value = _ctx()

        with (
            patch(
                "souschef.ui.pages.ansible_validation._render_validation_inputs",
                return_value=(upload, "2.15", True),
            ),
            patch(
                "souschef.ui.pages.ansible_validation._save_uploaded_file",
                side_effect=RuntimeError("boom"),
            ),
            patch("souschef.ui.pages.ansible_validation._display_validation_help"),
        ):
            show_ansible_validation_page()

        mock_st.error.assert_called()
        mock_st.exception.assert_called_once()


class TestValidationReportsHelpers:
    """Tests for validation reports helpers."""

    def test_parse_ansible_lint_output(self):
        from souschef.ui.pages.validation_reports import _parse_ansible_lint_output

        parsed = _parse_ansible_lint_output("warning: x\nerror: y\ninfo: z\n")
        assert parsed["warnings"] == 1
        assert parsed["errors"] == 1
        assert parsed["info"] == 1
        assert len(parsed["details"]) == 3

    def test_generate_validation_report(self):
        from souschef.ui.pages.validation_reports import _generate_validation_report

        report = _generate_validation_report(
            {
                "site.yml": (True, "ok"),
                "db.yml": (False, "failed"),
            }
        )

        assert "ANSIBLE PLAYBOOK VALIDATION REPORT" in report
        assert "site.yml" in report
        assert "db.yml" in report
        assert "Passed: 1" in report
        assert "Failed: 1" in report

    def test_validate_playbooks_in_directory(self, tmp_path):
        from souschef.ui.pages.validation_reports import (
            _validate_playbooks_in_directory,
        )

        (tmp_path / "site.yml").write_text("- hosts: all\n")
        (tmp_path / "db.yaml").write_text("- hosts: db\n")

        with patch(
            "souschef.ui.pages.validation_reports._run_ansible_lint",
            return_value=(True, "ok"),
        ):
            results = _validate_playbooks_in_directory(str(tmp_path))

        assert "site.yml" in results
        assert "db.yaml" in results

    def test_run_ansible_lint_success_and_timeout(self):
        import subprocess

        from souschef.ui.pages.validation_reports import _run_ansible_lint

        success_process = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch(
            "souschef.ui.pages.validation_reports.subprocess.run",
            return_value=success_process,
        ):
            ok, out = _run_ansible_lint("/tmp/site.yml")
        assert ok
        assert "ok" in out

        with patch(
            "souschef.ui.pages.validation_reports.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="x", timeout=30),
        ):
            ok2, out2 = _run_ansible_lint("/tmp/site.yml")
        assert not ok2
        assert "timeout" in out2.lower()

    @patch("souschef.ui.pages.validation_reports.st")
    def test_show_validation_reports_page_no_converted_path(self, mock_st):
        from souschef.ui.pages.validation_reports import show_validation_reports_page

        mock_st.session_state = SessionState()
        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]

        show_validation_reports_page()

        mock_st.info.assert_called()

    @patch("souschef.ui.pages.validation_reports.st")
    def test_show_validation_reports_page_single_result(self, mock_st, tmp_path):
        from souschef.ui.pages.validation_reports import show_validation_reports_page

        mock_st.session_state = SessionState(
            {"converted_playbooks_path": str(tmp_path)}
        )
        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.spinner.return_value = _ctx()
        mock_st.expander.return_value = _ctx()
        mock_st.button.return_value = False

        with patch(
            "souschef.ui.pages.validation_reports._validate_playbooks_in_directory",
            return_value={"site.yml": (True, "ok")},
        ):
            show_validation_reports_page()

        mock_st.metric.assert_called()

    @patch("souschef.ui.pages.validation_reports.st")
    def test_display_validation_result(self, mock_st):
        from souschef.ui.pages.validation_reports import _display_validation_result

        mock_st.expander.return_value = _ctx()
        _display_validation_result("site.yml", True, "ok")
        _display_validation_result("db.yml", False, "bad")

        assert mock_st.success.called
        assert mock_st.error.called


class TestMigrationConfigHelpers:
    """Tests for migration config helpers."""

    def test_generate_markdown_report(self):
        from souschef.ui.pages.migration_config import _generate_markdown_report

        report = _generate_markdown_report(
            {
                "summary": {
                    "total_manual_hours": 100,
                    "total_ai_assisted_hours": 60,
                    "time_saved_hours": 40,
                    "efficiency_gain_percent": 40,
                    "timeline_weeks": 8,
                },
                "activities": [
                    {
                        "name": "Parse recipes",
                        "count": 10,
                        "description": "Convert recipes",
                        "manual_hours": 20,
                        "ai_assisted_hours": 12,
                        "time_saved": 8,
                        "efficiency_gain_percent": 40,
                    }
                ],
            }
        )

        assert "Migration Activity Breakdown Report" in report
        assert "Parse recipes" in report
        assert "Time Saved" in report

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_activity_table_empty(self, mock_st):
        from souschef.ui.pages.migration_config import _display_activity_table

        _display_activity_table({"activities": []})
        mock_st.info.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_breakdown_metrics(self, mock_st):
        from souschef.ui.pages.migration_config import _display_breakdown_metrics

        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx(), _ctx()]
        _display_breakdown_metrics(
            {
                "summary": {
                    "total_manual_hours": 100,
                    "total_ai_assisted_hours": 60,
                    "time_saved_hours": 40,
                    "efficiency_gain_percent": 40,
                    "timeline_weeks": 8,
                }
            }
        )

        assert mock_st.metric.call_count == 4

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_activity_summary_and_table(self, mock_st):
        from souschef.ui.pages.migration_config import (
            _display_activity_summary,
            _display_activity_table,
        )

        breakdown = {
            "activities": [
                {
                    "name": "Convert recipes",
                    "count": 10,
                    "description": "Recipe migration",
                    "manual_hours": 20,
                    "ai_assisted_hours": 10,
                    "time_saved": 10,
                    "efficiency_gain_percent": 50,
                }
            ]
        }

        _display_activity_summary(breakdown)
        _display_activity_table(breakdown)

        mock_st.markdown.assert_called()
        mock_st.table.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_time_savings_chart(self, mock_st):
        from souschef.ui.pages.migration_config import _display_time_savings_chart

        breakdown = {
            "activities": [
                {
                    "name": "Convert templates",
                    "manual_hours": 12,
                    "ai_assisted_hours": 6,
                }
            ]
        }

        _display_time_savings_chart(breakdown)
        mock_st.bar_chart.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_display_breakdown_export_options(self, mock_st):
        from souschef.ui.pages.migration_config import _display_breakdown_export_options

        mock_st.columns.return_value = [_ctx(), _ctx()]

        _display_breakdown_export_options(
            {
                "summary": {
                    "total_manual_hours": 10,
                    "total_ai_assisted_hours": 5,
                    "time_saved_hours": 5,
                    "efficiency_gain_percent": 50,
                    "timeline_weeks": 1,
                },
                "activities": [],
            }
        )

        assert mock_st.download_button.call_count == 2

    @patch("souschef.ui.pages.migration_config.st")
    def test_generate_and_display_breakdown_success_and_error(self, mock_st):
        from souschef.ui.pages.migration_config import _generate_and_display_breakdown

        mock_st.spinner.return_value = _ctx()
        mock_st.session_state = SessionState()

        with (
            patch(
                "souschef.ui.pages.migration_config.calculate_activity_breakdown",
                return_value={"summary": {}, "activities": []},
            ),
            patch(
                "souschef.ui.pages.migration_config._display_activity_breakdown"
            ) as disp,
        ):
            _generate_and_display_breakdown("/tmp/cookbook", "phased")
            disp.assert_called_once()

        with patch(
            "souschef.ui.pages.migration_config.calculate_activity_breakdown",
            return_value={"error": "bad input"},
        ):
            _generate_and_display_breakdown("/tmp/cookbook", "phased")
            mock_st.error.assert_called()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_activity_visualisation_empty_path(self, mock_st):
        from souschef.ui.pages.migration_config import _show_activity_visualisation

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.text_input.return_value = ""
        mock_st.selectbox.return_value = "phased"
        mock_st.button.return_value = True
        mock_st.session_state = SessionState()

        _show_activity_visualisation()
        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_migration_config_page_without_config(self, mock_st):
        from souschef.ui.pages.migration_config import show_migration_config_page

        mock_st.session_state = SessionState()
        with (
            patch(
                "souschef.ui.pages.migration_config._show_configuration_section"
            ) as cfg,
            patch(
                "souschef.ui.pages.migration_config._show_activity_visualisation"
            ) as viz,
        ):
            show_migration_config_page()

        cfg.assert_called_once()
        viz.assert_not_called()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_migration_config_page_with_config(self, mock_st):
        from souschef.ui.pages.migration_config import show_migration_config_page

        mock_st.session_state = SessionState({"migration_config": MagicMock()})
        with (
            patch(
                "souschef.ui.pages.migration_config._show_configuration_section"
            ) as cfg,
            patch(
                "souschef.ui.pages.migration_config._show_activity_visualisation"
            ) as viz,
        ):
            show_migration_config_page()

        cfg.assert_called_once()
        viz.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_configuration_section_existing_config(self, mock_st):
        from souschef.ui.pages.migration_config import _show_configuration_section

        mock_st.session_state = SessionState({"migration_config": MagicMock()})
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.side_effect = [False, False]

        with (
            patch("souschef.ui.pages.migration_config._display_current_config") as disp,
            patch("souschef.ui.pages.migration_config._export_configuration") as exp,
        ):
            _show_configuration_section()

        disp.assert_called_once()
        exp.assert_not_called()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_configuration_section_new_config_form(self, mock_st):
        from souschef.ui.pages.migration_config import _show_configuration_section

        mock_st.session_state = SessionState()
        with patch(
            "souschef.ui.pages.migration_config._show_configuration_form"
        ) as form:
            _show_configuration_section()
        form.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_export_configuration(self, mock_st):
        from souschef.ui.pages.migration_config import _export_configuration

        cfg = MagicMock()
        cfg.to_dict.return_value = {"a": 1}
        mock_st.session_state = SessionState({"migration_config": cfg})

        _export_configuration()
        mock_st.download_button.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_configuration_form_save_success(self, mock_st):
        from souschef.ui.pages.migration_config import _show_configuration_form

        mock_st.session_state = SessionState()
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.selectbox.side_effect = [
            "awx",
            "standard",
            "3.10",
        ]
        mock_st.multiselect.return_value = ["ansible-lint"]
        mock_st.text_input.side_effect = ["hosts.ini", "2.15+"]
        mock_st.button.return_value = True

        _show_configuration_form()

        assert "migration_config" in mock_st.session_state
        mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.migration_config.st")
    def test_show_configuration_form_save_failure(self, mock_st):
        from souschef.ui.pages.migration_config import _show_configuration_form

        mock_st.session_state = SessionState()
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.selectbox.side_effect = ["awx", "redhat-best-practice", "3.10"]
        mock_st.multiselect.return_value = ["invalid-tool"]
        mock_st.text_input.side_effect = ["hosts.ini", "2.15+"]
        mock_st.button.return_value = True

        _show_configuration_form()
        mock_st.error.assert_called_once()


class TestAnsiblePlanningAdditionalHelpers:
    """Additional branch tests for ansible planning helpers."""

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_plan_breaking_and_deprecated_tabs_empty(self, mock_st):
        from souschef.ansible_upgrade import UpgradePlan
        from souschef.ui.pages.ansible_planning import (
            _display_plan_breaking_tab,
            _display_plan_deprecated_tab,
        )

        _display_plan_breaking_tab(cast(UpgradePlan, {"breaking_changes": []}))
        _display_plan_deprecated_tab(cast(UpgradePlan, {"deprecated_features": []}))

        assert mock_st.info.call_count >= 2

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_display_plan_tabs(self, mock_st):
        from souschef.ansible_upgrade import UpgradePlan
        from souschef.ui.pages.ansible_planning import _display_plan_tabs

        mock_st.tabs.return_value = [_ctx(), _ctx(), _ctx(), _ctx(), _ctx()]
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.expander.return_value = _ctx()

        plan = {
            "upgrade_path": {
                "from_version": "2.14",
                "to_version": "2.15",
                "intermediate_versions": [],
                "estimated_effort_days": 2,
                "risk_level": "Low",
                "collection_updates_needed": {"community.general": "9.0.0"},
            },
            "breaking_changes": ["Change A"],
            "deprecated_features": ["Feature B"],
            "pre_upgrade_checklist": ["Backup"],
            "testing_plan": {
                "phases": [{"phase": "P1", "steps": ["Run tests"]}],
                "success_criteria": ["No failures"],
            },
            "post_upgrade_validation": ["Verify hosts"],
        }

        _display_plan_tabs(cast(UpgradePlan, plan))
        mock_st.tabs.assert_called_once()

    @patch("souschef.ui.pages.ansible_planning.st")
    def test_show_ansible_planning_same_versions_warning(self, mock_st):
        from souschef.ui.pages.ansible_planning import show_ansible_planning_page

        mock_st.session_state = SessionState()
        with (
            patch(
                "souschef.ui.pages.ansible_planning._render_planning_inputs",
                return_value=("2.15", "2.15", True),
            ),
            patch("souschef.ui.pages.ansible_planning._display_planning_help"),
        ):
            show_ansible_planning_page()

        mock_st.warning.assert_called_once()
