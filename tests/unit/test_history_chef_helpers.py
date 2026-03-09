"""Helper tests for history and chef_server_settings UI pages."""

from __future__ import annotations

import json
import tarfile
import zipfile
from unittest.mock import MagicMock, Mock, patch

import pytest


class SessionState(dict):
    """Session-state helper with attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


def _ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.__enter__ = Mock(return_value=ctx)
    ctx.__exit__ = Mock(return_value=None)
    return ctx


class TestHistoryHelpers:
    """Tests for history.py helper functions."""

    def test_validate_archive_size_ok(self, tmp_path):
        from souschef.ui.pages.history import _validate_archive_size

        archive = tmp_path / "small.tar"
        archive.write_bytes(b"x" * 100)

        assert _validate_archive_size(archive, 1024)

    def test_validate_archive_size_too_large(self, tmp_path):
        from souschef.ui.pages.history import _validate_archive_size

        archive = tmp_path / "big.tar"
        archive.write_bytes(b"x" * 2048)

        try:
            _validate_archive_size(archive, 1024)
            raise AssertionError("Expected ValueError")
        except ValueError as exc:
            assert "too large" in str(exc)

    def test_detect_archive_format_zip(self, tmp_path):
        from souschef.ui.pages.history import _detect_archive_format

        zip_path = tmp_path / "data.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("a.txt", "hello")

        assert _detect_archive_format(zip_path) == "zip"

    def test_detect_archive_format_tar(self, tmp_path):
        from souschef.ui.pages.history import _detect_archive_format

        tar_path = tmp_path / "data.tar"
        file_path = tmp_path / "a.txt"
        file_path.write_text("hello")
        with tarfile.open(tar_path, "w") as tf:
            tf.add(file_path, arcname="a.txt")

        assert _detect_archive_format(tar_path) == "tar"

    @patch("souschef.ui.pages.history.st")
    def test_filter_safe_zip_members(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _filter_safe_zip_members

        zip_path = tmp_path / "safe.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("ok.txt", "ok")
            zf.writestr("../bad.txt", "bad")

        with zipfile.ZipFile(zip_path, "r") as zf:
            members = _filter_safe_zip_members(
                zf,
                max_files=10,
                max_file_size=1024 * 1024,
                max_total_size=2 * 1024 * 1024,
            )

        assert any(m.filename == "ok.txt" for m in members)
        assert all(".." not in m.filename for m in members)

    @patch("souschef.ui.pages.history.st")
    def test_extract_single_zip_member(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _extract_single_zip_member

        zip_path = tmp_path / "extract.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("dir/file.txt", "content")

        extract_dir = tmp_path / "out"
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zf:
            info = zf.getinfo("dir/file.txt")
            _extract_single_zip_member(zf, info, extract_dir)

        assert (extract_dir / "dir" / "file.txt").exists()

    @patch("souschef.ui.pages.history.st")
    def test_validate_tar_member_limits(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.name = "file.txt"
        member.size = 100

        result = _validate_tar_member(
            member,
            tmp_path,
            file_count=0,
            total_size=0,
            max_file_size=1024,
            max_total_size=2048,
            max_files=10,
        )

        assert result["is_safe"]
        assert not result["should_stop"]

    def test_filter_conversions_by_status(self):
        from souschef.ui.pages.history import _filter_conversions_by_status

        c1 = MagicMock(status="success")
        c2 = MagicMock(status="failed")
        conversions = [c1, c2]

        assert len(_filter_conversions_by_status(conversions, "All")) == 2
        assert _filter_conversions_by_status(conversions, "success") == [c1]

    def test_parse_conversion_blob_keys(self):
        from souschef.ui.pages.history import _parse_conversion_blob_keys

        conversion = MagicMock()
        conversion.conversion_data = json.dumps(
            {"roles_blob_key": "r1", "repo_blob_key": "r2"}
        )
        conversion.blob_storage_key = "fallback"

        roles, repo = _parse_conversion_blob_keys(conversion)
        assert roles == "r1"
        assert repo == "r2"

    @patch("souschef.ui.pages.history.st")
    def test_create_and_display_zip_download(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _create_and_display_zip_download

        source = tmp_path / "source"
        source.mkdir()
        (source / "a.txt").write_text("content")

        _create_and_display_zip_download(source, "out.zip", "Download", "k1")

        mock_st.download_button.assert_called_once()

    def test_format_datetime(self):
        from souschef.ui.pages.history import _format_datetime

        assert _format_datetime("2025-01-01T10:30:00") == "2025-01-01 10:30"
        assert _format_datetime("not-a-date") == "not-a-date"

    @patch("souschef.ui.pages.history.st")
    def test_show_statistics(self, mock_st):
        from souschef.ui.pages.history import _show_statistics

        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
        storage = MagicMock()
        storage.get_statistics.return_value = {
            "total_analyses": 4,
            "unique_cookbooks_analysed": 3,
            "total_conversions": 2,
            "successful_conversions": 1,
            "total_files_generated": 10,
            "avg_manual_hours": 16.0,
            "avg_ai_hours": 8.0,
        }

        _show_statistics(storage)

        assert mock_st.metric.call_count >= 8

    @patch("souschef.ui.pages.history.st")
    @patch("souschef.ui.pages.history.pd")
    def test_display_conversion_table(self, mock_pd, mock_st):
        from souschef.ui.pages.history import _display_conversion_table

        conv = MagicMock()
        conv.status = "success"
        conv.cookbook_name = "nginx"
        conv.output_type = "playbook"
        conv.files_generated = 3
        conv.blob_storage_key = "key"
        conv.created_at = "2025-01-01T10:00:00"
        conv.id = 1

        _display_conversion_table([conv])

        mock_st.dataframe.assert_called_once()

    def test_get_conversion_history(self):
        from souschef.ui.pages.history import _get_conversion_history

        storage = MagicMock()
        storage.get_conversion_history.return_value = [1, 2]

        _get_conversion_history(storage, "", 10)
        storage.get_conversion_history.assert_called_with(limit=10)

        _get_conversion_history(storage, "nginx", 10)
        storage.get_conversion_history.assert_called_with(
            cookbook_name="nginx", limit=10
        )

    @patch("souschef.ui.pages.history.st")
    def test_show_history_page(self, mock_st):
        from souschef.ui.pages.history import show_history_page

        mock_st.tabs.return_value = [_ctx(), _ctx(), _ctx()]
        storage = MagicMock()
        blob = MagicMock()

        with (
            patch(
                "souschef.ui.pages.history.get_storage_manager", return_value=storage
            ),
            patch("souschef.ui.pages.history.get_blob_storage", return_value=blob),
            patch("souschef.ui.pages.history._show_analysis_history") as a,
            patch("souschef.ui.pages.history._show_conversion_history") as c,
            patch("souschef.ui.pages.history._show_statistics") as s,
        ):
            show_history_page()

        a.assert_called_once_with(storage)
        c.assert_called_once_with(storage, blob)
        s.assert_called_once_with(storage)

    @patch("souschef.ui.pages.history.st")
    def test_show_analysis_history_no_results(self, mock_st):
        from souschef.ui.pages.history import _show_analysis_history

        storage = MagicMock()
        storage.get_analysis_history.return_value = []
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.text_input.return_value = ""
        mock_st.selectbox.return_value = 25

        _show_analysis_history(storage)
        mock_st.info.assert_called()

    @patch("souschef.ui.pages.history.st")
    @patch("souschef.ui.pages.history.pd")
    def test_show_analysis_history_with_results(self, mock_pd, mock_st):
        from souschef.ui.pages.history import _show_analysis_history

        analysis = MagicMock()
        analysis.id = 1
        analysis.cookbook_name = "nginx"
        analysis.cookbook_version = "1.0.0"
        analysis.complexity = "Low"
        analysis.estimated_hours = 10.0
        analysis.estimated_hours_with_souschef = 5.0
        analysis.ai_provider = "anthropic"
        analysis.created_at = "2025-01-01T00:00:00"

        storage = MagicMock()
        storage.get_analysis_history.return_value = [analysis]
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.text_input.return_value = ""
        mock_st.selectbox.side_effect = [25, 1]

        with patch("souschef.ui.pages.history._display_analysis_details") as details:
            _show_analysis_history(storage)

        mock_st.dataframe.assert_called_once()
        details.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_details_with_conversions(self, mock_st):
        from souschef.ui.pages.history import _display_analysis_details

        analysis = MagicMock()
        analysis.id = 7
        analysis.complexity = "Medium"
        analysis.estimated_hours = 12.0
        analysis.estimated_hours_with_souschef = 6.0
        analysis.analysis_data = (
            '{"activity_breakdown": [{"activity_type": "Parse", "count": 1}]}'
        )
        analysis.recommendations = "Do the thing"

        storage = MagicMock()
        storage.get_conversions_by_analysis_id.return_value = [MagicMock()]
        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.expander.return_value = _ctx()
        mock_st.button.return_value = False

        with (
            patch(
                "souschef.ui.pages.history.get_blob_storage", return_value=MagicMock()
            ),
            patch(
                "souschef.ui.pages.history._display_conversion_actions"
            ) as conv_actions,
        ):
            _display_analysis_details(analysis, storage)

        conv_actions.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_details_without_conversions(self, mock_st):
        from souschef.ui.pages.history import _display_analysis_details

        analysis = MagicMock()
        analysis.id = 8
        analysis.complexity = "Low"
        analysis.estimated_hours = 8.0
        analysis.estimated_hours_with_souschef = 4.0
        analysis.analysis_data = "{}"
        analysis.recommendations = "ok"

        storage = MagicMock()
        storage.get_conversions_by_analysis_id.return_value = []
        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.expander.return_value = _ctx()
        mock_st.button.return_value = False

        with (
            patch(
                "souschef.ui.pages.history.get_blob_storage", return_value=MagicMock()
            ),
            patch("souschef.ui.pages.history._display_convert_button") as convert_btn,
        ):
            _display_analysis_details(analysis, storage)

        convert_btn.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_details_activity_divider_branch(self, mock_st):
        from souschef.ui.pages.history import _display_analysis_details

        analysis = MagicMock()
        analysis.id = 78
        analysis.complexity = "Low"
        analysis.estimated_hours = 4.0
        analysis.estimated_hours_with_souschef = 2.0
        analysis.analysis_data = (
            '{"activity_breakdown": [{"activity_type": "Parse", "count": 1}]}'
        )
        analysis.recommendations = "ok"

        storage = MagicMock()
        storage.get_conversions_by_analysis_id.return_value = []
        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.expander.return_value = _ctx()
        mock_st.button.return_value = False

        with (
            patch(
                "souschef.ui.pages.history.get_blob_storage", return_value=MagicMock()
            ),
            patch("souschef.ui.pages.history._display_analysis_activity_breakdown"),
        ):
            _display_analysis_details(analysis, storage)

        # Activity section adds an extra divider after rendering breakdown.
        assert mock_st.divider.call_count >= 2

    @patch("souschef.ui.pages.history.st")
    def test_display_conversion_downloads_no_selection(self, mock_st):
        from souschef.ui.pages.history import _display_conversion_downloads

        c1 = MagicMock()
        c1.id = 1
        c1.cookbook_name = "nginx"
        c1.created_at = "2025-01-01T00:00:00"
        c1.blob_storage_key = "blob"

        mock_st.selectbox.return_value = None

        _display_conversion_downloads(MagicMock(), MagicMock(), [c1])

        mock_st.subheader.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_conversion_deletion(self, mock_st):
        from souschef.ui.pages.history import _display_conversion_deletion

        storage = MagicMock()
        storage.delete_conversion.return_value = True
        selected = MagicMock()
        selected.id = 11

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.return_value = True

        _display_conversion_deletion(storage, selected)

        storage.delete_conversion.assert_called_once_with(11)
        mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_extract_zip_safely(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _extract_zip_safely

        archive = tmp_path / "sample.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("x.yml", "- hosts: all\n")

        out = tmp_path / "out"
        out.mkdir()

        _extract_zip_safely(
            archive,
            out,
            max_file_size=1024 * 1024,
            max_total_size=10 * 1024 * 1024,
            max_files=100,
        )

        assert (out / "x.yml").exists()

    @patch("souschef.ui.pages.history.st")
    def test_filter_safe_tar_members(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _filter_safe_tar_members

        tar = MagicMock()
        m1 = MagicMock()
        m2 = MagicMock()
        tar.getmembers.return_value = [m1, m2]

        with patch(
            "souschef.ui.pages.history._validate_tar_member",
            side_effect=[
                {
                    "warning": None,
                    "should_stop": False,
                    "is_safe": True,
                    "new_total_size": 10,
                },
                {
                    "warning": "skip",
                    "should_stop": False,
                    "is_safe": False,
                    "new_total_size": 10,
                },
            ],
        ):
            safe = _filter_safe_tar_members(
                tar,
                tmp_path,
                max_file_size=100,
                max_total_size=1000,
                max_files=10,
            )

        assert safe == [m1]

    def test_safe_tar_extractall_rejects_bad_member(self, tmp_path):
        from souschef.ui.pages.history import _safe_tar_extractall

        tar = MagicMock()
        bad_member = MagicMock()
        bad_member.name = "../evil"

        try:
            _safe_tar_extractall(tar, tmp_path, [bad_member])
            raise AssertionError("Expected ValueError")
        except ValueError as exc:
            assert "path traversal" in str(exc).lower()

    def test_safe_tar_extractall_rejects_absolute_member(self, tmp_path):
        from souschef.ui.pages.history import _safe_tar_extractall

        tar = MagicMock()
        abs_member = MagicMock()
        abs_member.name = "/etc/passwd"

        try:
            _safe_tar_extractall(tar, tmp_path, [abs_member])
            raise AssertionError("Expected ValueError")
        except ValueError as exc:
            assert "absolute path" in str(exc).lower()

    def test_safe_tar_extractall_extracts_valid_member(self, tmp_path):
        from souschef.ui.pages.history import _safe_tar_extractall

        tar = MagicMock()
        ok_member = MagicMock()
        ok_member.name = "cookbook/metadata.rb"

        _safe_tar_extractall(tar, tmp_path, [ok_member])
        tar.extract.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_download_conversion_artefacts(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _download_conversion_artefacts

        mock_st.spinner.return_value = _ctx()
        conversion = MagicMock()
        conversion.id = 1
        blob = MagicMock()

        with (
            patch(
                "souschef.ui.pages.history._parse_conversion_blob_keys",
                return_value=("roles_key", "repo_key"),
            ),
            patch("souschef.ui.pages.history._display_roles_download"),
            patch("souschef.ui.pages.history._display_repo_download"),
        ):
            _download_conversion_artefacts(conversion, blob)

        mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_trigger_conversion_download_failure(self, mock_st):
        from souschef.ui.pages.history import _trigger_conversion

        mock_st.spinner.return_value = _ctx()
        analysis = MagicMock()
        analysis.cookbook_blob_key = "blob"
        analysis.cookbook_name = "nginx"
        analysis.id = 1

        blob = MagicMock()
        blob.download.return_value = None

        _trigger_conversion(analysis, blob)
        mock_st.error.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_trigger_conversion_unknown_archive_format(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _trigger_conversion

        mock_st.spinner.return_value = _ctx()
        analysis = MagicMock()
        analysis.cookbook_blob_key = "blob"
        analysis.cookbook_name = "nginx"
        analysis.id = 2

        archive = tmp_path / "archive.bin"
        archive.write_bytes(b"x")
        blob = MagicMock()
        blob.download.return_value = archive

        with patch(
            "souschef.ui.pages.history._detect_archive_format",
            return_value=None,
        ):
            _trigger_conversion(analysis, blob)

        mock_st.error.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_trigger_conversion_no_cookbook_directory(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _trigger_conversion

        mock_st.spinner.return_value = _ctx()
        analysis = MagicMock()
        analysis.cookbook_blob_key = "blob"
        analysis.cookbook_name = "nginx"
        analysis.id = 3

        archive = tmp_path / "archive.zip"
        archive.write_bytes(b"x")
        blob = MagicMock()
        blob.download.return_value = archive

        with (
            patch(
                "souschef.ui.pages.history._detect_archive_format",
                return_value="zip",
            ),
            patch("souschef.ui.pages.history._validate_archive_size"),
            patch("souschef.ui.pages.history._extract_zip_safely"),
            patch("pathlib.Path.iterdir", return_value=[]),
        ):
            _trigger_conversion(analysis, blob)

        mock_st.error.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_trigger_conversion_success_path(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _trigger_conversion

        mock_st.spinner.return_value = _ctx()
        mock_st.session_state = SessionState()

        analysis = MagicMock()
        analysis.cookbook_blob_key = "blob"
        analysis.cookbook_name = "nginx"
        analysis.id = 4

        archive = tmp_path / "archive.zip"
        archive.write_bytes(b"x")
        blob = MagicMock()
        blob.download.return_value = archive

        cookbook_dir = tmp_path / "extracted" / "cookbook"
        cookbook_dir.mkdir(parents=True)

        with (
            patch(
                "souschef.ui.pages.history._detect_archive_format",
                return_value="zip",
            ),
            patch("souschef.ui.pages.history._validate_archive_size"),
            patch("souschef.ui.pages.history._extract_zip_safely"),
            patch("pathlib.Path.iterdir", return_value=[cookbook_dir]),
        ):
            _trigger_conversion(analysis, blob)

        assert "history_convert_path" in mock_st.session_state
        mock_st.success.assert_called()

    def test_import_streamlit_fallback_branch(self):
        import builtins
        import importlib

        import souschef.ui.pages.history as history

        real_import = builtins.__import__

        def fake_import(
            name, module_globals=None, module_locals=None, fromlist=(), level=0
        ):
            if name == "streamlit":
                raise ImportError("streamlit missing")
            return real_import(name, module_globals, module_locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            reloaded = importlib.reload(history)
            assert hasattr(reloaded, "st")

        # Restore clean module state for following tests.
        importlib.reload(history)

    def test_validate_archive_size_missing_file_branch(self, tmp_path):
        from souschef.ui.pages.history import _validate_archive_size

        missing = tmp_path / "missing.tar"
        with pytest.raises(ValueError, match="Archive file not found"):
            _validate_archive_size(missing, 100)

    def test_safe_tar_extractall_skips_empty_member_name(self, tmp_path):
        from souschef.ui.pages.history import _safe_tar_extractall

        tar = MagicMock()
        member = MagicMock()
        member.name = ""

        _safe_tar_extractall(tar, tmp_path, [member])
        tar.extract.assert_not_called()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_details_delete_analysis_success(self, mock_st):
        from souschef.ui.pages.history import _display_analysis_details

        analysis = MagicMock()
        analysis.id = 99
        analysis.complexity = "Low"
        analysis.estimated_hours = 4.0
        analysis.estimated_hours_with_souschef = 2.0
        analysis.analysis_data = (
            '{"activity_breakdown": [{"activity_type": "Parse", "count": 1}]}'
        )
        analysis.recommendations = "ok"

        storage = MagicMock()
        storage.get_conversions_by_analysis_id.return_value = []
        storage.delete_analysis.return_value = True

        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.expander.return_value = _ctx()
        # First buttons for conversion area False, delete button True.
        mock_st.button.side_effect = [False, True]

        with patch(
            "souschef.ui.pages.history.get_blob_storage", return_value=MagicMock()
        ):
            _display_analysis_details(analysis, storage)

        storage.delete_analysis.assert_called_once_with(99)
        mock_st.success.assert_called()
        mock_st.rerun.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_details_delete_analysis_failure(self, mock_st):
        from souschef.ui.pages.history import _display_analysis_details

        analysis = MagicMock()
        analysis.id = 100
        analysis.complexity = "Low"
        analysis.estimated_hours = 4.0
        analysis.estimated_hours_with_souschef = 2.0
        analysis.analysis_data = "{}"
        analysis.recommendations = "ok"

        storage = MagicMock()
        storage.get_conversions_by_analysis_id.return_value = []
        storage.delete_analysis.return_value = False

        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.expander.return_value = _ctx()
        mock_st.button.side_effect = [False, True]

        with patch(
            "souschef.ui.pages.history.get_blob_storage", return_value=MagicMock()
        ):
            _display_analysis_details(analysis, storage)

        mock_st.error.assert_called_with("Failed to delete analysis.")

    @patch("souschef.ui.pages.history.st")
    def test_display_convert_button_with_blob_key_triggers(self, mock_st):
        from souschef.ui.pages.history import _display_convert_button

        analysis = MagicMock()
        analysis.id = 101
        analysis.cookbook_name = "nginx"
        analysis.cookbook_version = "1.0"
        analysis.cookbook_blob_key = "blob-key"

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.return_value = True

        with patch("souschef.ui.pages.history._trigger_conversion") as trigger:
            _display_convert_button(analysis, MagicMock())

        trigger.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_trigger_conversion_tar_format_branches(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _trigger_conversion

        mock_st.spinner.return_value = _ctx()
        mock_st.session_state = SessionState()

        analysis = MagicMock()
        analysis.cookbook_blob_key = "blob"
        analysis.cookbook_name = "nginx"
        analysis.id = 55

        archive = tmp_path / "archive.bin"
        archive.write_bytes(b"x")
        cookbook_dir = tmp_path / "extracted" / "cookbook"
        cookbook_dir.mkdir(parents=True)

        blob = MagicMock()
        blob.download.return_value = archive

        for fmt, mode in [
            ("tar.gz", "r:gz"),
            ("tar.bz2", "r:bz2"),
            ("tar.xz", "r:xz"),
            ("tar", "r"),
        ]:
            tar_ctx = MagicMock()
            tar_ctx.__enter__.return_value = tar_ctx
            tar_ctx.__exit__.return_value = None

            with (
                patch(
                    "souschef.ui.pages.history._detect_archive_format", return_value=fmt
                ),
                patch("souschef.ui.pages.history._validate_archive_size"),
                patch("tarfile.open", return_value=tar_ctx) as tar_open,
                patch(
                    "souschef.ui.pages.history._filter_safe_tar_members",
                    return_value=[],
                ),
                patch("souschef.ui.pages.history._safe_tar_extractall") as safe_extract,
                patch("pathlib.Path.iterdir", return_value=[cookbook_dir]),
            ):
                _trigger_conversion(analysis, blob)

            tar_open.assert_called_with(archive, mode)
            safe_extract.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_trigger_conversion_exception_branch(self, mock_st):
        from souschef.ui.pages.history import _trigger_conversion

        mock_st.spinner.return_value = _ctx()
        analysis = MagicMock()
        analysis.cookbook_blob_key = "blob"
        analysis.cookbook_name = "nginx"

        blob = MagicMock()
        blob.download.side_effect = RuntimeError("download failed")

        _trigger_conversion(analysis, blob)
        assert mock_st.error.call_count >= 1

    @patch("souschef.ui.pages.history.st")
    def test_filter_safe_tar_members_break_branch(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _filter_safe_tar_members

        tar = MagicMock()
        m1 = MagicMock()
        m2 = MagicMock()
        tar.getmembers.return_value = [m1, m2]

        with patch(
            "souschef.ui.pages.history._validate_tar_member",
            side_effect=[
                {
                    "warning": "stop",
                    "should_stop": True,
                    "is_safe": False,
                    "new_total_size": 0,
                },
                {
                    "warning": None,
                    "should_stop": False,
                    "is_safe": True,
                    "new_total_size": 10,
                },
            ],
        ):
            safe = _filter_safe_tar_members(
                tar,
                tmp_path,
                max_file_size=100,
                max_total_size=1000,
                max_files=10,
            )

        assert safe == []
        mock_st.warning.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_extract_zip_members_exception_branch(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _extract_zip_members

        info = MagicMock()
        info.filename = "bad.txt"

        with patch(
            "souschef.ui.pages.history._extract_single_zip_member",
            side_effect=RuntimeError("boom"),
        ):
            _extract_zip_members(MagicMock(), tmp_path, [info])

        mock_st.warning.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_extract_single_zip_member_outside_dir_branch(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _extract_single_zip_member

        zip_ref = MagicMock()
        info = MagicMock()
        info.filename = "../outside.txt"

        _extract_single_zip_member(zip_ref, info, tmp_path)
        mock_st.warning.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_conversion_downloads_full_action_branch(self, mock_st):
        from souschef.ui.pages.history import _display_conversion_downloads

        c1 = MagicMock()
        c1.id = 1
        c1.cookbook_name = "nginx"
        c1.output_type = "playbook"
        c1.files_generated = 3
        c1.created_at = "2025-01-01T00:00:00"
        c1.blob_storage_key = "blob"

        mock_st.selectbox.return_value = 1
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.return_value = True

        with (
            patch("souschef.ui.pages.history._download_conversion_artefacts") as dl,
            patch("souschef.ui.pages.history._display_conversion_deletion") as del_ui,
        ):
            _display_conversion_downloads(MagicMock(), MagicMock(), [c1])

        dl.assert_called_once()
        del_ui.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_download_conversion_artefacts_exception_branch(self, mock_st):
        from souschef.ui.pages.history import _download_conversion_artefacts

        mock_st.spinner.return_value = _ctx()
        with patch(
            "souschef.ui.pages.history._parse_conversion_blob_keys",
            side_effect=RuntimeError("parse failed"),
        ):
            _download_conversion_artefacts(MagicMock(), MagicMock())

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_roles_download_missing_and_directory_branches(
        self, mock_st, tmp_path
    ):
        from souschef.ui.pages.history import _display_roles_download

        conversion = MagicMock(cookbook_name="test", id=1)
        blob = MagicMock()

        missing = MagicMock()
        missing.exists.return_value = False

        directory = MagicMock()
        directory.exists.return_value = True
        directory.is_file.return_value = False

        blob.download.side_effect = [missing, directory]

        with patch(
            "souschef.ui.pages.history._create_and_display_zip_download"
        ) as zip_dl:
            _display_roles_download(conversion, blob, "roles", tmp_path)
            _display_roles_download(conversion, blob, "roles", tmp_path)

        zip_dl.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_repo_download_file_and_directory_branches(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _display_repo_download

        conversion = MagicMock(cookbook_name="test", id=2)
        blob = MagicMock()

        file_obj = MagicMock()
        file_obj.exists.return_value = True
        file_obj.is_file.return_value = True
        file_obj.open.return_value.__enter__.return_value.read.return_value = b"x"

        directory = MagicMock()
        directory.exists.return_value = True
        directory.is_file.return_value = False

        blob.download.side_effect = [file_obj, directory]

        with patch(
            "souschef.ui.pages.history._create_and_display_zip_download"
        ) as zip_dl:
            _display_repo_download(conversion, blob, "repo", tmp_path)
            _display_repo_download(conversion, blob, "repo", tmp_path)

        mock_st.download_button.assert_called_once()
        zip_dl.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_repo_download_missing_path_branch(self, mock_st, tmp_path):
        from souschef.ui.pages.history import _display_repo_download

        conversion = MagicMock(cookbook_name="test", id=3)
        blob = MagicMock()

        missing = MagicMock()
        missing.exists.return_value = False
        blob.download.return_value = missing

        _display_repo_download(conversion, blob, "repo", tmp_path)

        mock_st.download_button.assert_not_called()


class TestChefServerSettingsHelpers:
    """Tests for chef_server_settings.py helper functions."""

    def test_estimate_operation_time(self):
        from souschef.ui.pages.chef_server_settings import _estimate_operation_time

        assert _estimate_operation_time(3, "assess") == pytest.approx(15.0)
        assert _estimate_operation_time(3, "convert") == pytest.approx(30.0)

    def test_format_time_estimate(self):
        from souschef.ui.pages.chef_server_settings import _format_time_estimate

        assert _format_time_estimate(30) == "30 seconds"
        assert _format_time_estimate(120) == "2 minutes"
        assert "hour" in _format_time_estimate(3700)

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_confirm_bulk_operation(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _confirm_bulk_operation

        assert _confirm_bulk_operation(30, "assess")

        mock_st.checkbox.return_value = True
        assert _confirm_bulk_operation(120, "assess")

    def test_download_cookbook_rejects_invalid_names(self, tmp_path):
        from souschef.ui.pages.chef_server_settings import _download_cookbook

        result = _download_cookbook(
            server_url="https://chef.example.com",
            organisation="default",
            client_name="client",
            client_key_path="",
            cookbook_name="../bad",
            version="1.0.0",
            target_dir=tmp_path,
        )

        assert result is None

    def test_download_cookbook_success(self, tmp_path):
        from souschef.ui.pages.chef_server_settings import _download_cookbook

        with patch(
            "souschef.core.chef_server.get_chef_cookbook_version",
            return_value={"name": "nginx", "version": "1.0.0"},
        ):
            result = _download_cookbook(
                server_url="https://chef.example.com",
                organisation="default",
                client_name="client",
                client_key_path="",
                cookbook_name="nginx",
                version="1.0.0",
                target_dir=tmp_path,
            )

        assert result is not None
        assert (result / "metadata.rb").exists()

    def test_get_chef_cookbooks_handles_exception(self):
        from souschef.ui.pages.chef_server_settings import _get_chef_cookbooks

        with patch(
            "souschef.core.chef_server.list_chef_cookbooks",
            side_effect=RuntimeError("boom"),
        ):
            result = _get_chef_cookbooks("url", "org", "client", "")

        assert result == []

    def test_assess_single_cookbook_cache_hit(self, tmp_path):
        from souschef.ui.pages.chef_server_settings import _assess_single_cookbook

        storage = MagicMock()
        storage.get_cached_analysis.return_value = {"cached": True}
        cookbook = {"name": "nginx", "versions": ["1.0.0"]}

        with patch(
            "souschef.ui.pages.chef_server_settings._download_cookbook",
            return_value=tmp_path / "nginx",
        ):
            success = _assess_single_cookbook(
                storage,
                "url",
                "org",
                "client",
                "",
                tmp_path,
                cookbook,
                "anthropic",
                "key",
                "model",
            )

        assert success
        storage.save_analysis.assert_not_called()

    def test_assess_single_cookbook_rule_based(self, tmp_path):
        from souschef.ui.pages.chef_server_settings import _assess_single_cookbook

        storage = MagicMock()
        storage.get_cached_analysis.return_value = None
        cookbook_dir = tmp_path / "nginx"
        cookbook_dir.mkdir()
        cookbook = {"name": "nginx", "versions": ["1.0.0"]}

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._download_cookbook",
                return_value=cookbook_dir,
            ),
            patch(
                "souschef.assessment.parse_chef_migration_assessment",
                return_value={
                    "complexity": "Medium",
                    "estimated_hours": 8.0,
                    "recommendations": "ok",
                },
            ),
        ):
            success = _assess_single_cookbook(
                storage,
                "url",
                "org",
                "client",
                "",
                tmp_path,
                cookbook,
                "anthropic",
                "",
                "model",
            )

        assert success
        storage.save_analysis.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_run_bulk_assessment_no_cookbooks(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        mock_st.spinner.return_value = _ctx()
        with patch(
            "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
            return_value=[],
        ):
            _run_bulk_assessment("url", "org", "client", "")

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_run_bulk_conversion_no_cookbooks(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        mock_st.spinner.return_value = _ctx()
        with patch(
            "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
            return_value=[],
        ):
            _run_bulk_conversion("url", "org", "client", "")

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_run_bulk_assessment_success(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _run_bulk_assessment

        mock_st.spinner.return_value = _ctx()
        mock_st.progress.return_value = MagicMock()
        mock_st.empty.return_value = MagicMock()
        mock_st.container.return_value = _ctx()
        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]

        cookbooks = [{"name": "nginx", "versions": ["1.0.0"]}]
        storage = MagicMock()

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=cookbooks,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._confirm_bulk_operation",
                return_value=True,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._assess_single_cookbook",
                return_value=True,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings.get_storage_manager",
                return_value=storage,
            ),
        ):
            _run_bulk_assessment("url", "org", "client", "")

        mock_st.success.assert_called()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_run_bulk_conversion_success(self, mock_st, tmp_path):
        from souschef.ui.pages.chef_server_settings import _run_bulk_conversion

        mock_st.spinner.return_value = _ctx()
        mock_st.progress.return_value = MagicMock()
        mock_st.empty.return_value = MagicMock()
        mock_st.container.return_value = _ctx()
        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
        mock_st.checkbox.return_value = True
        mock_st.text_input.return_value = "./test-output/bulk-conversion-out"
        mock_st.button.return_value = True

        cookbooks = [{"name": "nginx", "versions": ["1.0.0"]}]
        storage = MagicMock()
        cookbook_dir = tmp_path / "nginx"
        cookbook_dir.mkdir()

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._get_chef_cookbooks",
                return_value=cookbooks,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._download_cookbook",
                return_value=cookbook_dir,
            ),
            patch(
                "souschef.ui.pages.chef_server_settings.get_storage_manager",
                return_value=storage,
            ),
        ):
            _run_bulk_conversion("url", "org", "client", "")

        storage.save_conversion.assert_called()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_current_configuration(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _render_current_configuration

        mock_st.session_state = SessionState(
            {
                "chef_server_url": "https://chef.local",
                "chef_org": "default",
                "chef_client_name": "me",
                "chef_client_key_path": "/tmp/key.pem",
            }
        )

        _render_current_configuration()

        mock_st.info.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_save_settings_section(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _render_save_settings_section

        mock_st.session_state = SessionState()
        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.return_value = True

        _render_save_settings_section("url", "org", "client", "/tmp/key.pem")

        assert mock_st.session_state.chef_server_url == "url"
        mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_show_chef_server_settings_page_smoke(self, mock_st):
        from souschef.ui.pages.chef_server_settings import (
            show_chef_server_settings_page,
        )

        mock_st.session_state = SessionState()

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._render_current_configuration"
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_chef_server_configuration",
                return_value=("", "default", "", ""),
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_test_connection_button"
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_save_settings_section"
            ),
            patch("souschef.ui.pages.chef_server_settings._render_usage_examples"),
            patch("souschef.ui.pages.chef_server_settings._render_bulk_operations"),
        ):
            show_chef_server_settings_page()

        mock_st.title.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_test_connection_button_success(self, mock_st):
        from souschef.ui.pages.chef_server_settings import (
            _render_test_connection_button,
        )

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.spinner.return_value = _ctx()
        mock_st.button.return_value = True

        with patch(
            "souschef.ui.pages.chef_server_settings._validate_chef_server_connection",
            return_value=(True, "ok"),
        ):
            _render_test_connection_button("url", "org", "client", "")

        mock_st.success.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_test_connection_button_failure(self, mock_st):
        from souschef.ui.pages.chef_server_settings import (
            _render_test_connection_button,
        )

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.spinner.return_value = _ctx()
        mock_st.button.return_value = True

        with patch(
            "souschef.ui.pages.chef_server_settings._validate_chef_server_connection",
            return_value=(False, "bad"),
        ):
            _render_test_connection_button("url", "org", "client", "")

        mock_st.error.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_bulk_operations_button_paths(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _render_bulk_operations

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.side_effect = [True, True, True]

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._run_bulk_assessment"
            ) as assess,
            patch(
                "souschef.ui.pages.chef_server_settings._run_bulk_conversion"
            ) as convert,
        ):
            _render_bulk_operations("url", "org", "client", "")

        assess.assert_called_once()
        convert.assert_called_once()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_show_chef_server_settings_page_without_server_url(self, mock_st):
        from souschef.ui.pages.chef_server_settings import (
            show_chef_server_settings_page,
        )

        with (
            patch(
                "souschef.ui.pages.chef_server_settings._render_current_configuration"
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_chef_server_configuration",
                return_value=("", "default", "", ""),
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_test_connection_button"
            ),
            patch(
                "souschef.ui.pages.chef_server_settings._render_save_settings_section"
            ),
            patch("souschef.ui.pages.chef_server_settings._render_usage_examples"),
            patch(
                "souschef.ui.pages.chef_server_settings._render_bulk_operations"
            ) as bulk,
        ):
            show_chef_server_settings_page()

        bulk.assert_not_called()

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_chef_server_configuration(self, mock_st):
        from souschef.ui.pages.chef_server_settings import (
            _render_chef_server_configuration,
        )

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.text_input.side_effect = [
            "https://chef.example.com",
            "default",
            "client",
            "/tmp/key.pem",
        ]

        server_url, organisation, client_name, client_key_path = (
            _render_chef_server_configuration()
        )

        assert server_url == "https://chef.example.com"
        assert organisation == "default"
        assert client_name == "client"
        assert client_key_path == "/tmp/key.pem"

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_render_usage_examples(self, mock_st):
        from souschef.ui.pages.chef_server_settings import _render_usage_examples

        mock_st.expander.return_value = _ctx()
        _render_usage_examples()

        assert mock_st.expander.call_count == 2

    def test_get_chef_cookbooks_success(self):
        from souschef.ui.pages.chef_server_settings import _get_chef_cookbooks

        with patch(
            "souschef.core.chef_server.list_chef_cookbooks",
            return_value=[{"name": "nginx", "versions": ["1.0.0"]}],
        ):
            result = _get_chef_cookbooks("url", "org", "client", "")

        assert result == [{"name": "nginx", "versions": ["1.0.0"]}]

    @patch("souschef.ui.pages.history.st")
    def test_display_conversion_actions_multiple(self, mock_st):
        from souschef.ui.pages.history import _display_conversion_actions

        analysis = MagicMock()
        analysis.id = 1

        c1 = MagicMock()
        c1.id = 10
        c1.status = "success"
        c1.output_type = "roles"
        c1.files_generated = 3
        c1.created_at = "2026-01-01T00:00:00"
        c1.blob_storage_key = "blob-1"

        c2 = MagicMock()
        c2.id = 11
        c2.status = "success"
        c2.output_type = "repo"
        c2.files_generated = 5
        c2.created_at = "2026-01-02T00:00:00"
        c2.blob_storage_key = "blob-2"

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.expander.return_value = _ctx()
        mock_st.button.side_effect = [True, True, True]

        with patch("souschef.ui.pages.history._download_conversion_artefacts") as dl:
            _display_conversion_actions(analysis, [c1, c2], MagicMock())

        assert dl.call_count == 3

    @patch("souschef.ui.pages.history.st")
    def test_display_convert_button_no_blob_key(self, mock_st):
        from souschef.ui.pages.history import _display_convert_button

        analysis = MagicMock()
        analysis.id = 3
        analysis.cookbook_name = "nginx"
        analysis.cookbook_version = "1.0.0"
        analysis.cookbook_blob_key = None

        mock_st.columns.return_value = [_ctx(), _ctx()]
        _display_convert_button(analysis, MagicMock())

        mock_st.caption.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_show_conversion_history_with_results(self, mock_st):
        from souschef.ui.pages.history import _show_conversion_history

        conversion = MagicMock()
        conversion.id = 1
        conversion.status = "success"
        conversion.cookbook_name = "nginx"
        conversion.blob_storage_key = "blob"

        storage = MagicMock()
        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
        mock_st.text_input.return_value = ""
        mock_st.selectbox.side_effect = ["All", 25]

        with (
            patch(
                "souschef.ui.pages.history._get_conversion_history",
                return_value=[conversion],
            ),
            patch("souschef.ui.pages.history._display_conversion_table") as table,
            patch(
                "souschef.ui.pages.history._display_conversion_downloads"
            ) as downloads,
        ):
            _show_conversion_history(storage, MagicMock())

        table.assert_called_once()
        downloads.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_get_conversion_filters(self, mock_st):
        from souschef.ui.pages.history import _get_conversion_filters

        mock_st.columns.return_value = [_ctx(), _ctx(), _ctx()]
        mock_st.text_input.return_value = "nginx"
        mock_st.selectbox.side_effect = ["success", 50]

        cookbook, status, limit = _get_conversion_filters()
        assert cookbook == "nginx"
        assert status == "success"
        assert limit == 50

    @patch("souschef.ui.pages.history.st")
    def test_display_conversion_downloads_selected_without_blob(self, mock_st):
        from souschef.ui.pages.history import _display_conversion_downloads

        c1 = MagicMock()
        c1.id = 1
        c1.cookbook_name = "nginx"
        c1.created_at = "2026-01-01T00:00:00"
        c1.blob_storage_key = "blob"

        selected = MagicMock()
        selected.id = 1
        selected.blob_storage_key = None

        mock_st.selectbox.return_value = 1
        with patch("builtins.next", return_value=selected):
            _display_conversion_downloads(MagicMock(), MagicMock(), [c1])

        mock_st.subheader.assert_called_once()

    @patch("souschef.ui.pages.history.st")
    def test_display_conversion_deletion_failure(self, mock_st):
        from souschef.ui.pages.history import _display_conversion_deletion

        storage = MagicMock()
        storage.delete_conversion.return_value = False
        selected = MagicMock()
        selected.id = 12

        mock_st.columns.return_value = [_ctx(), _ctx()]
        mock_st.button.return_value = True

        _display_conversion_deletion(storage, selected)

        mock_st.success.assert_not_called()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_details_malformed_json(self, mock_st):
        from souschef.ui.pages.history import _display_analysis_details

        analysis = MagicMock()
        analysis.id = 13
        analysis.complexity = "Low"
        analysis.estimated_hours = 8.0
        analysis.estimated_hours_with_souschef = 4.0
        analysis.analysis_data = "not-json"
        analysis.recommendations = "ok"

        storage = MagicMock()
        storage.get_conversions_by_analysis_id.return_value = []
        mock_st.columns.side_effect = lambda spec: [
            _ctx() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        mock_st.expander.return_value = _ctx()
        mock_st.button.return_value = False

        with (
            patch(
                "souschef.ui.pages.history.get_blob_storage", return_value=MagicMock()
            ),
            patch("souschef.ui.pages.history._display_convert_button") as convert_btn,
        ):
            _display_analysis_details(analysis, storage)

        convert_btn.assert_called_once()
