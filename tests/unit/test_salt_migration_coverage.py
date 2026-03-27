"""Additional coverage tests for souschef/ui/pages/salt_migration.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_st() -> MagicMock:
    """Return a mock streamlit module with dynamic columns support."""
    mock = MagicMock()
    mock.session_state = {}

    def _columns(spec):
        """Return the right number of mock columns based on spec."""
        if isinstance(spec, (list, tuple)):
            n = len(spec)
        elif isinstance(spec, int):
            n = spec
        else:
            n = 3
        cols = []
        for _ in range(n):
            col = MagicMock()
            col.__enter__ = MagicMock(return_value=MagicMock())
            col.__exit__ = MagicMock(return_value=False)
            cols.append(col)
        return cols

    mock.columns.side_effect = _columns
    mock.spinner.return_value = MagicMock(
        __enter__=MagicMock(return_value=None),
        __exit__=MagicMock(return_value=False),
    )
    mock.expander.return_value = MagicMock(
        __enter__=MagicMock(return_value=MagicMock()),
        __exit__=MagicMock(return_value=False),
    )
    return mock


class TestValidateUiPath:
    """Tests for _validate_ui_path function covering missing lines."""

    def test_validate_ui_path_returns_none_for_empty_string(
        self, mock_st: MagicMock
    ) -> None:
        """Empty string returns None (line 75)."""
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _validate_ui_path

            result = _validate_ui_path("")
        assert result is None

    def test_validate_ui_path_returns_none_for_null_byte(
        self, mock_st: MagicMock
    ) -> None:
        """Path with null byte returns None."""
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _validate_ui_path

            result = _validate_ui_path("/valid/path\x00injection")
        assert result is None

    def test_validate_ui_path_returns_none_for_traversal(
        self, mock_st: MagicMock
    ) -> None:
        """
        Path traversal outside workspace returns None (line 91).

        In tests, SOUSCHEF_WORKSPACE_ROOT is set to '/' by conftest.py so
        any path would be within it.  We patch _get_workspace_root to a
        restricted workspace so the traversal guard triggers.
        """
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._get_workspace_root",
                return_value="/workspaces/souschef",
            ),
        ):
            from souschef.ui.pages.salt_migration import _validate_ui_path

            result = _validate_ui_path("/tmp/outside_workspace")
        assert result is None

    def test_validate_ui_path_returns_none_on_os_error(
        self, mock_st: MagicMock
    ) -> None:
        """OSError during path resolution returns None (lines 93-94)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._get_workspace_root",
                side_effect=OSError("disk error"),
            ),
        ):
            from souschef.ui.pages.salt_migration import _validate_ui_path

            result = _validate_ui_path("/srv/salt")
        assert result is None


class TestRenderSlsParseSectionInvalidPath:
    """Additional tests for _render_sls_parse_section - invalid path branch."""

    def test_render_sls_parse_section_invalid_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid/unsafe path shows error message (lines 141-142)."""
        mock_st.text_input.return_value = "/srv/salt/init.sls"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        mock_st.error.assert_called()


class TestRenderConvertSectionInvalidPath:
    """Additional tests for _render_convert_section - invalid path branch."""

    def test_render_convert_section_invalid_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid/unsafe path shows error message (lines 249-250)."""
        mock_st.text_input.side_effect = ["/srv/salt/init.sls", ""]
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.error.assert_called()


class TestRenderPillarSectionInvalidPath:
    """Additional tests for _render_pillar_section - invalid path branch."""

    def test_render_pillar_section_invalid_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid/unsafe path shows error message (lines 343-344)."""
        mock_st.text_input.return_value = "/srv/salt/pillar.sls"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.error.assert_called()


class TestRenderDirectorySectionInvalidPath:
    """Additional tests for _render_directory_section - invalid path branch."""

    def test_render_directory_section_invalid_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid/unsafe path shows error message (lines 401-402)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.error.assert_called()


class TestRenderAssessmentSection:
    """Tests for _render_assessment_section covering missing lines."""

    def test_render_assessment_section_no_button(self, mock_st: MagicMock) -> None:
        """Section renders without clicking assess button."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.subheader.assert_called()

    def test_render_assessment_section_empty_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Empty directory path shows error (lines 490-492)."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = True

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.error.assert_called()

    def test_render_assessment_section_invalid_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid path shows error (lines 494-496)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.error.assert_called()

    def test_render_assessment_section_json_error(self, mock_st: MagicMock) -> None:
        """JSON decode error shows error (lines 504-506)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.assess_salt_complexity",
                return_value="not valid json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.error.assert_called()

    def test_render_assessment_section_error_key_in_result(
        self, mock_st: MagicMock
    ) -> None:
        """Assessment returning error key shows error (lines 508-510)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.assess_salt_complexity",
                return_value=json.dumps({"error": "Directory not found"}),
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.error.assert_called_with("Directory not found")

    def test_render_assessment_section_success(self, mock_st: MagicMock) -> None:
        """Successful assessment shows success message (lines 512-521)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        assess_result = json.dumps(
            {
                "summary": {
                    "total_files": 5,
                    "total_states": 12,
                    "complexity_level": "medium",
                    "estimated_effort_days": 10,
                    "estimated_effort_days_with_souschef": 3,
                    "estimated_effort_weeks": "2-3 weeks",
                    "high_complexity_files": [],
                    "module_breakdown": {},
                },
                "files": [],
            }
        )

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.assess_salt_complexity",
                return_value=assess_result,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.success.assert_called()

    def test_render_assessment_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Cached result is shown from session state (line 521)."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_assess_result": {
                "summary": {
                    "total_files": 3,
                    "total_states": 7,
                    "complexity_level": "low",
                    "estimated_effort_days": 5,
                    "estimated_effort_days_with_souschef": 2,
                    "estimated_effort_weeks": "1 week",
                    "high_complexity_files": [],
                    "module_breakdown": {},
                },
                "files": [],
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_assessment_section

            _render_assessment_section()
        mock_st.metric.assert_called()


class TestDisplayAssessmentResults:
    """Tests for _display_assessment_results covering missing lines."""

    def test_display_assessment_results_basic(self, mock_st: MagicMock) -> None:
        """Assessment results display basic metrics (lines 532-543)."""
        result = {
            "summary": {
                "total_files": 5,
                "total_states": 10,
                "complexity_level": "medium",
                "estimated_effort_days": 8,
                "estimated_effort_days_with_souschef": 3,
                "estimated_effort_weeks": "2 weeks",
                "high_complexity_files": [],
                "module_breakdown": {},
            },
            "files": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_assessment_results

            _display_assessment_results(result)
        mock_st.metric.assert_called()

    def test_display_assessment_results_with_high_complexity_files(
        self, mock_st: MagicMock
    ) -> None:
        """High complexity files section is displayed (lines 554-558)."""
        result = {
            "summary": {
                "total_files": 5,
                "total_states": 10,
                "complexity_level": "high",
                "estimated_effort_days": 20,
                "estimated_effort_days_with_souschef": 7,
                "estimated_effort_weeks": "4-6 weeks",
                "high_complexity_files": ["complex.sls", "massive.sls"],
                "module_breakdown": {},
            },
            "files": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_assessment_results

            _display_assessment_results(result)
        mock_st.warning.assert_called()

    def test_display_assessment_results_with_module_breakdown(
        self, mock_st: MagicMock
    ) -> None:
        """Module breakdown section is displayed (lines 560-563)."""
        result = {
            "summary": {
                "total_files": 3,
                "total_states": 6,
                "complexity_level": "low",
                "estimated_effort_days": 5,
                "estimated_effort_days_with_souschef": 2,
                "estimated_effort_weeks": "1 week",
                "high_complexity_files": [],
                "module_breakdown": {"pkg": 3, "service": 2, "file": 1},
            },
            "files": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_assessment_results

            _display_assessment_results(result)
        mock_st.json.assert_called()

    def test_display_assessment_results_per_file_complexity(
        self, mock_st: MagicMock
    ) -> None:
        """Per-file complexity section is displayed (lines 565-573)."""
        result = {
            "summary": {
                "total_files": 2,
                "total_states": 4,
                "complexity_level": "medium",
                "estimated_effort_days": 6,
                "estimated_effort_days_with_souschef": 2,
                "estimated_effort_weeks": "1-2 weeks",
                "high_complexity_files": [],
                "module_breakdown": {},
            },
            "files": [
                {
                    "file": "webserver.sls",
                    "state_count": 3,
                    "complexity_score": 8.5,
                    "complexity_level": "high",
                },
                {
                    "file": "common.sls",
                    "state_count": 1,
                    "complexity_score": 2.0,
                    "complexity_level": "low",
                },
            ],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_assessment_results

            _display_assessment_results(result)
        mock_st.subheader.assert_called()
        mock_st.markdown.assert_called()


class TestRenderMigrationPlanSection:
    """Tests for _render_migration_plan_section covering missing lines."""

    def test_render_migration_plan_section_no_button(self, mock_st: MagicMock) -> None:
        """Section renders without clicking plan button."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.number_input.return_value = 8
        mock_st.selectbox.return_value = "aap"

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _render_migration_plan_section,
            )

            _render_migration_plan_section()
        mock_st.subheader.assert_called()

    def test_render_migration_plan_section_empty_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Empty path shows error (lines 613-615)."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = True
        mock_st.number_input.return_value = 8
        mock_st.selectbox.return_value = "aap"

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _render_migration_plan_section,
            )

            _render_migration_plan_section()
        mock_st.error.assert_called()

    def test_render_migration_plan_section_invalid_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid path shows error (lines 617-619)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True
        mock_st.number_input.return_value = 8
        mock_st.selectbox.return_value = "aap"

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import (
                _render_migration_plan_section,
            )

            _render_migration_plan_section()
        mock_st.error.assert_called()

    def test_render_migration_plan_section_success(self, mock_st: MagicMock) -> None:
        """Successful plan generation shows success and download (lines 621-631)."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True
        mock_st.number_input.return_value = 8
        mock_st.selectbox.return_value = "aap"

        plan_result = "# Salt Migration Plan\n\nPhase 1: Assessment"

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.plan_salt_migration",
                return_value=plan_result,
            ),
        ):
            from souschef.ui.pages.salt_migration import (
                _render_migration_plan_section,
            )

            _render_migration_plan_section()
        mock_st.success.assert_called()

    def test_render_migration_plan_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Cached plan is shown from session state (lines 629-631)."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.number_input.return_value = 8
        mock_st.selectbox.return_value = "aap"
        mock_st.session_state = {
            "salt_plan_result": "# Phase 1: Assessment\n\n## Steps"
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _render_migration_plan_section,
            )

            _render_migration_plan_section()
        mock_st.markdown.assert_called()
        mock_st.download_button.assert_called()


class TestRunBatchConversion:
    """Tests for _run_batch_conversion covering missing lines (642-676)."""

    def test_run_batch_conversion_empty_inputs_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Empty salt_dir or output_dir returns None (lines 643-645)."""
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _run_batch_conversion

            result = _run_batch_conversion("", "/output")
        assert result is None
        mock_st.error.assert_called()

    def test_run_batch_conversion_invalid_salt_dir_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid salt_dir path returns None (lines 647-650)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                side_effect=[None, "/output"],
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_batch_conversion

            result = _run_batch_conversion("/srv/salt", "/output")
        assert result is None
        mock_st.error.assert_called()

    def test_run_batch_conversion_invalid_output_dir_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid output_dir path returns None (lines 652-657)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                side_effect=["/srv/salt", None],
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_batch_conversion

            result = _run_batch_conversion("/srv/salt", "/output")
        assert result is None
        mock_st.error.assert_called()

    def test_run_batch_conversion_json_error_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """JSON decode error returns None (lines 661-663)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_directory_to_roles",
                return_value="not valid json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_batch_conversion

            result = _run_batch_conversion("/srv/salt", "/output")
        assert result is None
        mock_st.error.assert_called()

    def test_run_batch_conversion_error_key_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Error in result returns None (lines 665-667)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_directory_to_roles",
                return_value=json.dumps({"error": "Salt dir not found"}),
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_batch_conversion

            result = _run_batch_conversion("/srv/salt", "/output")
        assert result is None
        mock_st.error.assert_called_with("Salt dir not found")

    def test_run_batch_conversion_success_returns_result(
        self, mock_st: MagicMock
    ) -> None:
        """Successful conversion returns result dict (lines 669-676)."""
        batch_result = {
            "roles_created": ["webserver", "db"],
            "files_written": [
                "/output/webserver/tasks/main.yml",
                "/output/db/tasks/main.yml",
            ],
            "warnings": [],
        }

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_directory_to_roles",
                return_value=json.dumps(batch_result),
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_batch_conversion

            result = _run_batch_conversion("/srv/salt", "/output")
        assert result is not None
        assert result["roles_created"] == ["webserver", "db"]
        mock_st.success.assert_called()


class TestDisplayBatchConversionResults:
    """Tests for _display_batch_conversion_results covering missing lines (681-704)."""

    def test_display_batch_conversion_results_basic(self, mock_st: MagicMock) -> None:
        """Basic batch results display metrics (lines 681-692)."""
        result = {
            "roles_created": ["webserver"],
            "files_written": ["/output/webserver/tasks/main.yml"],
            "warnings": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _display_batch_conversion_results,
            )

            _display_batch_conversion_results(result)
        mock_st.metric.assert_called()

    def test_display_batch_conversion_results_with_warnings(
        self, mock_st: MagicMock
    ) -> None:
        """Warnings are displayed (lines 693-695)."""
        result = {
            "roles_created": [],
            "files_written": [],
            "warnings": ["Could not convert cmd.run state", "Manual review needed"],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _display_batch_conversion_results,
            )

            _display_batch_conversion_results(result)
        mock_st.warning.assert_called()

    def test_display_batch_conversion_results_with_roles(
        self, mock_st: MagicMock
    ) -> None:
        """Roles expander shown when roles exist (lines 697-699)."""
        result = {
            "roles_created": ["webserver", "db", "cache"],
            "files_written": [],
            "warnings": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _display_batch_conversion_results,
            )

            _display_batch_conversion_results(result)
        mock_st.expander.assert_called()

    def test_display_batch_conversion_results_with_files(
        self, mock_st: MagicMock
    ) -> None:
        """Files expander shown when files exist (lines 701-704)."""
        result = {
            "roles_created": [],
            "files_written": [
                "/output/webserver/tasks/main.yml",
                "/output/webserver/handlers/main.yml",
            ],
            "warnings": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import (
                _display_batch_conversion_results,
            )

            _display_batch_conversion_results(result)
        mock_st.expander.assert_called()


class TestRunInventoryGeneration:
    """Tests for _run_inventory_generation covering missing lines (709-736)."""

    def test_run_inventory_generation_empty_path_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Empty top_path returns None (lines 709-711)."""
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _run_inventory_generation

            result = _run_inventory_generation("")
        assert result is None
        mock_st.error.assert_called()

    def test_run_inventory_generation_invalid_path_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Invalid path returns None (lines 713-715)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration._validate_ui_path",
                return_value=None,
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_inventory_generation

            result = _run_inventory_generation("/srv/salt/top.sls")
        assert result is None
        mock_st.error.assert_called()

    def test_run_inventory_generation_json_error_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """JSON decode error returns None (lines 720-722)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.generate_salt_inventory",
                return_value="not valid json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_inventory_generation

            result = _run_inventory_generation("/srv/salt/top.sls")
        assert result is None
        mock_st.error.assert_called()

    def test_run_inventory_generation_error_key_returns_none(
        self, mock_st: MagicMock
    ) -> None:
        """Error in result returns None (lines 724-726)."""
        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.generate_salt_inventory",
                return_value=json.dumps({"error": "top.sls not found"}),
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_inventory_generation

            result = _run_inventory_generation("/srv/salt/top.sls")
        assert result is None
        mock_st.error.assert_called_with("top.sls not found")

    def test_run_inventory_generation_success_returns_result(
        self, mock_st: MagicMock
    ) -> None:
        """Successful generation returns result dict (lines 728-736)."""
        inv_result = {
            "inventory": "[webservers]\n192.168.1.10\n",
            "groups": ["webservers"],
            "hosts": ["192.168.1.10"],
        }

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.generate_salt_inventory",
                return_value=json.dumps(inv_result),
            ),
        ):
            from souschef.ui.pages.salt_migration import _run_inventory_generation

            result = _run_inventory_generation("/srv/salt/top.sls")
        assert result is not None
        assert result["groups"] == ["webservers"]
        mock_st.success.assert_called()


class TestDisplayInventoryResults:
    """Tests for _display_inventory_results covering missing lines (741-758)."""

    def test_display_inventory_results_with_inventory(self, mock_st: MagicMock) -> None:
        """Inventory content is shown as code with download button (lines 744-752)."""
        result = {
            "inventory": "[webservers]\n192.168.1.10\n",
            "groups": [],
            "hosts": ["192.168.1.10"],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_inventory_results

            _display_inventory_results(result)
        mock_st.subheader.assert_called()
        mock_st.code.assert_called()
        mock_st.download_button.assert_called_once()

    def test_display_inventory_results_with_groups(self, mock_st: MagicMock) -> None:
        """Groups expander shown when groups exist (lines 754-758)."""
        result = {
            "inventory": "",
            "groups": ["webservers", "db_servers"],
            "hosts": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_inventory_results

            _display_inventory_results(result)
        mock_st.expander.assert_called()

    def test_display_inventory_results_empty(self, mock_st: MagicMock) -> None:
        """No inventory and no groups shows nothing."""
        result = {
            "inventory": "",
            "groups": [],
            "hosts": [],
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_inventory_results

            _display_inventory_results(result)
        mock_st.download_button.assert_not_called()
        mock_st.expander.assert_not_called()


class TestRenderBatchConvertSection:
    """Tests for _render_batch_convert_section covering missing lines (788-793)."""

    def test_render_batch_convert_section_success_stores_result(
        self, mock_st: MagicMock
    ) -> None:
        """Successful conversion stores result in session state (lines 788-790)."""
        mock_st.text_input.side_effect = ["/srv/salt", "/output"]
        mock_st.button.return_value = True
        mock_st.session_state = {}

        batch_result = {
            "roles_created": ["webserver"],
            "files_written": ["/output/webserver/tasks/main.yml"],
            "warnings": [],
        }

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_directory_to_roles",
                return_value=json.dumps(batch_result),
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_batch_convert_section

            _render_batch_convert_section()
        mock_st.success.assert_called()

    def test_render_batch_convert_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Cached result is shown from session state (lines 792-793)."""
        mock_st.text_input.side_effect = ["", ""]
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_batch_result": {
                "roles_created": ["webserver"],
                "files_written": ["/output/webserver/tasks/main.yml"],
                "warnings": [],
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_batch_convert_section

            _render_batch_convert_section()
        mock_st.metric.assert_called()


class TestRenderInventorySection:
    """Tests for _render_inventory_section covering missing lines (817-822)."""

    def test_render_inventory_section_success_stores_result(
        self, mock_st: MagicMock
    ) -> None:
        """Successful inventory stores result in session state (lines 817-819)."""
        mock_st.text_input.return_value = "/srv/salt/top.sls"
        mock_st.button.return_value = True
        mock_st.session_state = {}

        inv_result = {
            "inventory": "[all]\nlocalhost\n",
            "groups": ["all"],
            "hosts": ["localhost"],
        }

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.generate_salt_inventory",
                return_value=json.dumps(inv_result),
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_inventory_section

            _render_inventory_section()
        mock_st.success.assert_called()

    def test_render_inventory_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Cached result is shown from session state (lines 821-822)."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_inv_result": {
                "inventory": "[webservers]\n192.168.1.10\n",
                "groups": ["webservers"],
                "hosts": ["192.168.1.10"],
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_inventory_section

            _render_inventory_section()
        mock_st.subheader.assert_called()
        mock_st.download_button.assert_called()
