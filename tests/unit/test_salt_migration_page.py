"""Tests for souschef/ui/pages/salt_migration.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_st() -> MagicMock:
    """Return a mock streamlit module."""
    mock = MagicMock()
    mock.session_state = {}
    mock.tabs.return_value = [
        MagicMock(
            __enter__=MagicMock(return_value=MagicMock()),
            __exit__=MagicMock(return_value=False),
        ),
        MagicMock(
            __enter__=MagicMock(return_value=MagicMock()),
            __exit__=MagicMock(return_value=False),
        ),
        MagicMock(
            __enter__=MagicMock(return_value=MagicMock()),
            __exit__=MagicMock(return_value=False),
        ),
        MagicMock(
            __enter__=MagicMock(return_value=MagicMock()),
            __exit__=MagicMock(return_value=False),
        ),
    ]

    def _columns(spec):
        """Return the right number of mock columns based on spec."""
        if isinstance(spec, (list, tuple)):
            n = len(spec)
        elif isinstance(spec, int):
            n = spec
        else:
            n = 3
        return [MagicMock() for _ in range(n)]

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


def _import_page_module(mock_st: MagicMock):
    """Import the salt_migration module with mocked streamlit."""
    import sys

    # Patch streamlit at the module level
    with patch.dict(sys.modules, {"streamlit": mock_st}):
        if "souschef.ui.pages.salt_migration" in sys.modules:
            del sys.modules["souschef.ui.pages.salt_migration"]
        import souschef.ui.pages.salt_migration as module

        return module


class TestDisplayIntro:
    """Tests for _display_intro function."""

    def test_display_intro_renders_title(self, mock_st: MagicMock) -> None:
        """Intro renders a title."""
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_intro

            _display_intro()
        mock_st.title.assert_called_once()
        call_args = mock_st.title.call_args[0][0]
        assert "Salt" in call_args

    def test_display_intro_renders_markdown(self, mock_st: MagicMock) -> None:
        """Intro renders markdown description."""
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_intro

            _display_intro()
        mock_st.markdown.assert_called_once()


class TestDisplayParseResults:
    """Tests for _display_parse_results function."""

    def test_display_parse_results_no_states(self, mock_st: MagicMock) -> None:
        """Empty states list is handled gracefully."""
        result = {
            "summary": {"by_category": {}, "pillar_keys": [], "grain_keys": []},
            "states": [],
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_parse_results

            _display_parse_results(result)
        # Should not error

    def test_display_parse_results_with_states(self, mock_st: MagicMock) -> None:
        """States are shown in expander."""
        result = {
            "summary": {
                "by_category": {"package": 1, "service": 1},
                "pillar_keys": ["db_pass"],
                "grain_keys": ["os"],
            },
            "states": [
                {
                    "id": "nginx",
                    "module": "pkg",
                    "function": "installed",
                    "category": "package",
                }
            ],
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_parse_results

            _display_parse_results(result)
        mock_st.subheader.assert_called()

    def test_display_parse_results_pillar_info(self, mock_st: MagicMock) -> None:
        """Pillar keys are shown in info section."""
        result = {
            "summary": {
                "by_category": {},
                "pillar_keys": ["db_host", "db_port"],
                "grain_keys": [],
            },
            "states": [],
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_parse_results

            _display_parse_results(result)
        mock_st.info.assert_called()

    def test_display_parse_results_grain_info(self, mock_st: MagicMock) -> None:
        """Grain keys are shown in info section."""
        result = {
            "summary": {
                "by_category": {},
                "pillar_keys": [],
                "grain_keys": ["os_family"],
            },
            "states": [],
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_parse_results

            _display_parse_results(result)
        mock_st.info.assert_called()

    def test_display_parse_results_raw_json(self, mock_st: MagicMock) -> None:
        """Raw JSON section is displayed."""
        result = {
            "summary": {"by_category": {}, "pillar_keys": [], "grain_keys": []},
            "states": [],
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_parse_results

            _display_parse_results(result)
        mock_st.json.assert_called()


class TestDisplayConversionResults:
    """Tests for _display_conversion_results function."""

    def test_display_conversion_results_metrics(self, mock_st: MagicMock) -> None:
        """Conversion metrics are displayed."""
        result = {
            "tasks_converted": 5,
            "tasks_unconverted": 2,
            "warnings": ["Warning 1"],
            "ansible_vars": {"db_host": "localhost"},
            "playbook": "---\n- name: test",
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_conversion_results

            _display_conversion_results(result)
        mock_st.metric.assert_called()
        mock_st.warning.assert_called()

    def test_display_conversion_results_no_warnings(self, mock_st: MagicMock) -> None:
        """No warnings means no warning display."""
        result = {
            "tasks_converted": 3,
            "tasks_unconverted": 0,
            "warnings": [],
            "ansible_vars": {},
            "playbook": "---",
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_conversion_results

            _display_conversion_results(result)
        mock_st.warning.assert_not_called()

    def test_display_conversion_results_download_button(
        self, mock_st: MagicMock
    ) -> None:
        """Download button is shown when playbook exists."""
        result = {
            "tasks_converted": 1,
            "tasks_unconverted": 0,
            "warnings": [],
            "ansible_vars": {},
            "playbook": "---\n- name: myplay",
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_conversion_results

            _display_conversion_results(result)
        mock_st.download_button.assert_called_once()

    def test_display_conversion_results_no_playbook(self, mock_st: MagicMock) -> None:
        """No playbook means no download button."""
        result = {
            "tasks_converted": 0,
            "tasks_unconverted": 0,
            "warnings": [],
            "ansible_vars": {},
            "playbook": "",
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_conversion_results

            _display_conversion_results(result)
        mock_st.download_button.assert_not_called()


class TestDisplayDirectoryResults:
    """Tests for _display_directory_results function."""

    def test_display_directory_results_metrics(self, mock_st: MagicMock) -> None:
        """Directory scan metrics are displayed."""
        result = {
            "summary": {
                "total_files": 10,
                "state_files": 7,
                "pillar_files": 2,
                "top_files": 1,
            },
            "files": {
                "states": ["common.sls", "webserver.sls"],
                "top": ["top.sls"],
                "pillars": ["db.sls", "app.sls"],
            },
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_directory_results

            _display_directory_results(result)
        mock_st.metric.assert_called()

    def test_display_directory_results_empty_files(self, mock_st: MagicMock) -> None:
        """Empty file lists produce no expanders."""
        result = {
            "summary": {
                "total_files": 0,
                "state_files": 0,
                "pillar_files": 0,
                "top_files": 0,
            },
            "files": {
                "states": [],
                "top": [],
                "pillars": [],
            },
        }
        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _display_directory_results

            _display_directory_results(result)
        mock_st.expander.assert_not_called()


class TestRenderSlsParseSection:
    """Tests for _render_sls_parse_section function."""

    def test_render_sls_parse_section_no_parse_button(self, mock_st: MagicMock) -> None:
        """Section renders without clicking parse button."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        mock_st.subheader.assert_called()

    def test_render_sls_parse_section_empty_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Clicking parse with empty path shows error."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = True

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        mock_st.error.assert_called()

    def test_render_sls_parse_section_parse_success(self, mock_st: MagicMock) -> None:
        """Successful parse shows success message."""
        mock_st.text_input.return_value = "/srv/salt/init.sls"
        mock_st.button.return_value = True

        parse_result = json.dumps(
            {
                "summary": {
                    "total_states": 2,
                    "by_category": {"package": 1, "service": 1},
                    "pillar_keys": [],
                    "grain_keys": [],
                },
                "states": [],
            }
        )

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_sls",
                return_value=parse_result,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        mock_st.success.assert_called()

    def test_render_sls_parse_section_parse_json_error(
        self, mock_st: MagicMock
    ) -> None:
        """JSON decode error shows error message."""
        mock_st.text_input.return_value = "/srv/salt/init.sls"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_sls",
                return_value="not valid json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        mock_st.error.assert_called()

    def test_render_sls_parse_section_file_error(self, mock_st: MagicMock) -> None:
        """Parser returning error string shows error."""
        mock_st.text_input.return_value = "/srv/salt/init.sls"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_sls",
                return_value='{"Error": "file not found"}',
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        mock_st.error.assert_called()

    def test_render_sls_parse_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Previously parsed result is shown from session state."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_parse_result": {
                "summary": {"by_category": {}, "pillar_keys": [], "grain_keys": []},
                "states": [],
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_sls_parse_section

            _render_sls_parse_section()
        # json.assert_called would prove display happened
        mock_st.json.assert_called()


class TestRenderConvertSection:
    """Tests for _render_convert_section function."""

    def test_render_convert_section_no_convert_button(self, mock_st: MagicMock) -> None:
        """Section renders without clicking convert button."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.subheader.assert_called()

    def test_render_convert_section_empty_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Clicking convert with empty path shows error."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = True

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.error.assert_called()

    def test_render_convert_section_convert_success(self, mock_st: MagicMock) -> None:
        """Successful conversion shows success message."""
        mock_st.text_input.side_effect = ["/srv/salt/init.sls", "myplay"]
        mock_st.button.return_value = True

        convert_result = json.dumps(
            {
                "playbook": "---\n- name: test",
                "tasks_converted": 2,
                "tasks_unconverted": 0,
                "ansible_vars": {},
                "warnings": [],
            }
        )

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_sls_to_ansible",
                return_value=convert_result,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.success.assert_called()

    def test_render_convert_section_json_error(self, mock_st: MagicMock) -> None:
        """JSON decode error shows error message."""
        mock_st.text_input.side_effect = ["/srv/salt/init.sls", ""]
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_sls_to_ansible",
                return_value="not json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.error.assert_called()

    def test_render_convert_section_converter_error(self, mock_st: MagicMock) -> None:
        """Converter returning error key shows error."""
        mock_st.text_input.side_effect = ["/srv/salt/init.sls", ""]
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.convert_salt_sls_to_ansible",
                return_value=json.dumps({"error": "File not found"}),
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.error.assert_called_with("File not found")

    def test_render_convert_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Previously converted result is shown from session state."""
        mock_st.text_input.side_effect = ["", ""]
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_convert_result": {
                "tasks_converted": 1,
                "tasks_unconverted": 0,
                "warnings": [],
                "ansible_vars": {},
                "playbook": "---",
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_convert_section

            _render_convert_section()
        mock_st.metric.assert_called()


class TestRenderPillarSection:
    """Tests for _render_pillar_section function."""

    def test_render_pillar_section_no_button(self, mock_st: MagicMock) -> None:
        """Section renders without clicking pillar button."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.subheader.assert_called()

    def test_render_pillar_section_empty_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Empty pillar path shows error."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = True

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.error.assert_called()

    def test_render_pillar_section_parse_success(self, mock_st: MagicMock) -> None:
        """Successful pillar parse shows success message."""
        mock_st.text_input.return_value = "/srv/salt/pillar/db.sls"
        mock_st.button.return_value = True

        parse_result = json.dumps(
            {
                "variables": {"db": {"host": "localhost"}},
                "flattened": {"db.host": "localhost"},
                "summary": {"total_keys": 1, "top_level_keys": ["db"]},
            }
        )

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_pillar",
                return_value=parse_result,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.success.assert_called()

    def test_render_pillar_section_json_error(self, mock_st: MagicMock) -> None:
        """JSON decode error shows error."""
        mock_st.text_input.return_value = "/srv/salt/pillar/db.sls"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_pillar",
                return_value="not json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.error.assert_called()

    def test_render_pillar_section_file_error(self, mock_st: MagicMock) -> None:
        """Parser returning error string shows error."""
        mock_st.text_input.return_value = "/srv/salt/pillar/db.sls"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_pillar",
                return_value='{"Error": "not found"}',
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.error.assert_called()

    def test_render_pillar_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Previously parsed result is shown from session state."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_pillar_result": {
                "flattened": {"db.host": "localhost"},
                "summary": {"total_keys": 1},
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.json.assert_called()

    def test_render_pillar_section_empty_flattened(self, mock_st: MagicMock) -> None:
        """Empty flattened dict shows info message."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_pillar_result": {
                "flattened": {},
                "summary": {"total_keys": 0},
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_pillar_section

            _render_pillar_section()
        mock_st.info.assert_called()


class TestRenderDirectorySection:
    """Tests for _render_directory_section function."""

    def test_render_directory_section_no_button(self, mock_st: MagicMock) -> None:
        """Section renders without clicking scan button."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.subheader.assert_called()

    def test_render_directory_section_empty_path_shows_error(
        self, mock_st: MagicMock
    ) -> None:
        """Empty directory path shows error."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = True

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.error.assert_called()

    def test_render_directory_section_scan_success(self, mock_st: MagicMock) -> None:
        """Successful directory scan shows success message."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        scan_result = json.dumps(
            {
                "summary": {
                    "total_files": 5,
                    "state_files": 3,
                    "pillar_files": 1,
                    "top_files": 1,
                },
                "files": {
                    "states": ["common.sls"],
                    "top": ["top.sls"],
                    "pillars": ["db.sls"],
                    "all": ["common.sls", "top.sls", "db.sls"],
                },
            }
        )

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_directory",
                return_value=scan_result,
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.success.assert_called()

    def test_render_directory_section_json_error(self, mock_st: MagicMock) -> None:
        """JSON decode error shows error."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_directory",
                return_value="not json",
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.error.assert_called()

    def test_render_directory_section_scan_error(self, mock_st: MagicMock) -> None:
        """Parser returning error shows error."""
        mock_st.text_input.return_value = "/srv/salt"
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.salt_migration.st", mock_st),
            patch(
                "souschef.ui.pages.salt_migration.parse_salt_directory",
                return_value='{"Error": "not found"}',
            ),
        ):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.error.assert_called()

    def test_render_directory_section_shows_cached_result(
        self, mock_st: MagicMock
    ) -> None:
        """Previously scanned result is shown from session state."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.session_state = {
            "salt_dir_result": {
                "summary": {
                    "total_files": 3,
                    "state_files": 2,
                    "pillar_files": 0,
                    "top_files": 1,
                },
                "files": {
                    "states": ["common.sls"],
                    "top": ["top.sls"],
                    "pillars": [],
                },
            }
        }

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import _render_directory_section

            _render_directory_section()
        mock_st.metric.assert_called()


class TestShowSaltMigrationPage:
    """Tests for show_salt_migration_page function."""

    def test_show_salt_migration_page_renders(self, mock_st: MagicMock) -> None:
        """Page renders all eight tabs."""
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.number_input.return_value = 8
        mock_st.selectbox.return_value = "aap"
        mock_st.session_state = {}

        tab_mocks = [
            MagicMock(
                __enter__=lambda s, *a, **k: MagicMock(),
                __exit__=lambda s, *a, **k: False,
            )
            for _ in range(8)
        ]
        for t in tab_mocks:
            t.__enter__ = MagicMock(return_value=MagicMock())
            t.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = tab_mocks

        with patch("souschef.ui.pages.salt_migration.st", mock_st):
            from souschef.ui.pages.salt_migration import show_salt_migration_page

            show_salt_migration_page()

        mock_st.tabs.assert_called_once_with(
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
