"""Comprehensive tests for souschef/ui/pages/history.py."""

from __future__ import annotations

import json
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, Mock, patch


class SessionState(dict):
    """Session-state helper with attribute and dict access."""

    def __getattr__(self, name: str):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value):
        self[name] = value


class TestImportFallbacks:
    """Test import fallback handling."""

    def test_module_imports_successfully(self):
        """Test that module imports successfully."""
        from souschef.ui.pages import history

        assert history is not None
        assert hasattr(history, "show_history_page")


class TestFormatDatetime:
    """Test datetime formatting utility."""

    def test_format_datetime_valid_iso_format(self):
        """Test formatting valid ISO format datetime string."""
        from souschef.ui.pages.history import _format_datetime

        iso_string = "2026-03-09T10:30:45"
        result = _format_datetime(iso_string)
        assert "2026-03-09" in result
        assert "10:30" in result

    def test_format_datetime_invalid_format(self):
        """Test formatting invalid datetime string."""
        from souschef.ui.pages.history import _format_datetime

        invalid_string = "not-a-date"
        result = _format_datetime(invalid_string)
        assert result == invalid_string

    def test_format_datetime_none_value(self):
        """Test formatting None value."""
        from souschef.ui.pages.history import _format_datetime

        result = _format_datetime(cast(str, None))
        assert result is None


class TestArchiveDetection:
    """Test archive format detection."""

    def test_detect_zip_archive(self, tmp_path):
        """Test ZIP archive detection."""
        from souschef.ui.pages.history import _detect_archive_format

        zip_file = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_file, "w") as zf:
            zf.writestr("test.txt", "content")

        result = _detect_archive_format(zip_file)
        assert result == "zip"

    def test_detect_tar_gz_archive(self, tmp_path):
        """Test TAR.GZ archive detection."""
        from souschef.ui.pages.history import _detect_archive_format

        tar_file = tmp_path / "test.tar.gz"
        with tarfile.open(tar_file, "w:gz"):
            assert tar_file.exists()

        result = _detect_archive_format(tar_file)
        assert result == "tar.gz"

    def test_detect_tar_bz2_archive(self, tmp_path):
        """Test TAR.BZ2 archive detection."""
        from souschef.ui.pages.history import _detect_archive_format

        tar_file = tmp_path / "test.tar.bz2"
        with tarfile.open(tar_file, "w:bz2"):
            assert tar_file.exists()

        result = _detect_archive_format(tar_file)
        assert result == "tar.bz2"

    def test_detect_tar_xz_archive(self, tmp_path):
        """Test TAR.XZ archive detection."""
        from souschef.ui.pages.history import _detect_archive_format

        tar_file = tmp_path / "test.tar.xz"
        with tarfile.open(tar_file, "w:xz"):
            assert tar_file.exists()

        result = _detect_archive_format(tar_file)
        assert result == "tar.xz"

    def test_detect_plain_tar_archive(self, tmp_path):
        """Test plain TAR archive detection."""
        from souschef.ui.pages.history import _detect_archive_format

        tar_file = tmp_path / "test.tar"
        with tarfile.open(tar_file, "w"):
            assert tar_file.exists()

        result = _detect_archive_format(tar_file)
        assert result == "tar"

    def test_detect_unknown_archive(self, tmp_path):
        """Test unknown archive format returns None."""
        from souschef.ui.pages.history import _detect_archive_format

        unknown_file = tmp_path / "test.unknown"
        unknown_file.write_bytes(b"not an archive")

        result = _detect_archive_format(unknown_file)
        assert result is None

    def test_detect_archive_oversized(self, tmp_path):
        """Test archive size validation in detection."""
        from souschef.ui.pages.history import _detect_archive_format

        # Create a file larger than the detection limit
        large_file = tmp_path / "huge.zip"
        # Don't actually create a huge file, just mock it
        large_file.write_bytes(b"x" * (2 * 1024 * 1024 * 1024))  # 2GB

        result = _detect_archive_format(large_file)
        assert result is None


class TestSafeZipExtraction:
    """Test safe ZIP extraction."""

    def test_extract_zip_safely_valid_files(self, tmp_path):
        """Test extracting valid ZIP files."""
        from souschef.ui.pages.history import _extract_zip_safely

        # Create a valid ZIP file
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("subdir/file2.txt", "content2")

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        _extract_zip_safely(
            zip_path, extract_dir, 100 * 1024 * 1024, 500 * 1024 * 1024, 10000
        )

        assert (extract_dir / "file1.txt").exists()
        assert (extract_dir / "subdir" / "file2.txt").exists()

    def test_extract_zip_path_traversal_blocked(self, tmp_path):
        """Test that path traversal attacks in ZIP are blocked."""
        from souschef.ui.pages.history import _filter_safe_zip_members

        # Create ZIP with path traversal attempt
        zip_path = tmp_path / "malicious.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "fake content")

        with zipfile.ZipFile(zip_path, "r") as zf:
            safe_members = _filter_safe_zip_members(
                zf, 10000, 100 * 1024 * 1024, 500 * 1024 * 1024
            )
            # Malicious file should be filtered out
            assert len(safe_members) == 0

    def test_extract_zip_absolute_path_blocked(self, tmp_path):
        """Test that absolute paths in ZIP are blocked."""
        from souschef.ui.pages.history import _filter_safe_zip_members

        # Create ZIP with absolute path
        zip_path = tmp_path / "absolute.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/passwd", "fake content")

        with zipfile.ZipFile(zip_path, "r") as zf:
            safe_members = _filter_safe_zip_members(
                zf, 10000, 100 * 1024 * 1024, 500 * 1024 * 1024
            )
            # Absolute path should be fi ltered out
            assert len(safe_members) == 0

    def test_extract_zip_file_count_limit(self, tmp_path):
        """Test ZIP extraction respects file count limit."""
        from souschef.ui.pages.history import _filter_safe_zip_members

        # Create ZIP with many files
        zip_path = tmp_path / "many.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(20):
                zf.writestr(f"file{i}.txt", f"content{i}")

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Set limit to 10 files
            safe_members = _filter_safe_zip_members(
                zf, 10, 100 * 1024 * 1024, 500 * 1024 * 1024
            )
            # Should stop at 10 files
            assert len(safe_members) == 10

    def test_extract_zip_size_limit(self, tmp_path):
        """Test ZIP extraction respects file size limit."""
        from souschef.ui.pages.history import _filter_safe_zip_members

        # Create ZIP with large files
        zip_path = tmp_path / "large.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("small.txt", "x" * 1000)
            zf.writestr("large.txt", "x" * (50 * 1024 * 1024))  # 50MB

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Set limit to 10MB per file
            safe_members = _filter_safe_zip_members(
                zf, 10000, 10 * 1024 * 1024, 500 * 1024 * 1024
            )
            # Large file should be skipped
            assert len(safe_members) == 1
            assert safe_members[0].filename == "small.txt"

    def test_extract_zip_total_size_limit(self, tmp_path):
        """Test ZIP extraction respects total size limit."""
        from souschef.ui.pages.history import _filter_safe_zip_members

        # Create ZIP exceeding total size
        zip_path = tmp_path / "exceeds_total.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "x" * (400 * 1024 * 1024))  # 400MB
            zf.writestr("file2.txt", "x" * (200 * 1024 * 1024))  # 200MB

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Set total limit to 500MB
            safe_members = _filter_safe_zip_members(
                zf, 10000, 1024 * 1024 * 1024, 500 * 1024 * 1024
            )
            # Second file should cause total to exceed limit
            assert len(safe_members) == 1

    def test_extract_single_zip_member(self, tmp_path):
        """Test extracting a single ZIP member."""
        from souschef.ui.pages.history import _extract_single_zip_member

        # Create ZIP file
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("subdir/file.txt", "content")

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Extract the member
        with zipfile.ZipFile(zip_path, "r") as zf:
            info = zf.filelist[0]
            _extract_single_zip_member(zf, info, extract_dir)

        assert (extract_dir / "subdir" / "file.txt").exists()
        assert (extract_dir / "subdir" / "file.txt").read_text() == "content"

    def test_extract_directory_member(self, tmp_path):
        """Test extracting directory members from ZIP."""
        from souschef.ui.pages.history import _extract_single_zip_member

        # Create ZIP with directory entry
        zip_path = tmp_path / "with_dir.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("mydir/", "")
            zf.writestr("mydir/file.txt", "content")

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        # Extract directory entry
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.filelist:
                _extract_single_zip_member(zf, info, extract_dir)

        assert (extract_dir / "mydir").is_dir()
        assert (extract_dir / "mydir" / "file.txt").exists()


class TestTarValidation:
    """Test TAR member validation."""

    def test_validate_tar_member_safe(self, tmp_path):
        """Test validation of safe TAR member."""
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.size = 1000
        member.name = "safe_file.txt"
        member.issym = MagicMock(return_value=False)
        member.islnk = MagicMock(return_value=False)

        result = _validate_tar_member(
            member, tmp_path, 0, 0, 100 * 1024 * 1024, 500 * 1024 * 1024, 10000
        )

        assert result["is_safe"] is True
        assert result["should_stop"] is False
        assert result["warning"] is None

    def test_validate_tar_member_file_count_exceeded(self, tmp_path):
        """Test validation fails when file count exceeds limit."""
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.size = 1000
        member.name = "file.txt"

        result = _validate_tar_member(
            member,
            tmp_path,
            10000,
            0,
            100 * 1024 * 1024,
            500 * 1024 * 1024,
            100,
        )

        assert result["is_safe"] is False
        assert result["should_stop"] is True
        assert "more than" in result["warning"]

    def test_validate_tar_member_oversized(self, tmp_path):
        """Test validation fails for oversized file."""
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.size = 200 * 1024 * 1024  # 200MB
        member.name = "huge.tar"

        result = _validate_tar_member(
            member, tmp_path, 0, 0, 100 * 1024 * 1024, 500 * 1024 * 1024, 10000
        )

        assert result["is_safe"] is False
        assert "exceeds" in result["warning"]

    def test_validate_tar_member_total_size_exceeded(self, tmp_path):
        """Test validation fails when total size exceeds limit."""
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.size = 200 * 1024 * 1024  # 200MB
        member.name = "file.tar"

        result = _validate_tar_member(
            member,
            tmp_path,
            0,
            400 * 1024 * 1024,
            1024 * 1024 * 1024,
            500 * 1024 * 1024,
            10000,
        )

        assert result["is_safe"] is False
        assert result["should_stop"] is True

    def test_validate_tar_member_path_traversal(self, tmp_path):
        """Test validation detects path traversal."""
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.size = 1000
        member.name = "../../../etc/passwd"
        member.issym = MagicMock(return_value=False)
        member.islnk = MagicMock(return_value=False)

        result = _validate_tar_member(
            member, tmp_path, 0, 0, 100 * 1024 * 1024, 500 * 1024 * 1024, 10000
        )

        assert result["is_safe"] is False
        assert "unsafe" in result["warning"].lower()

    def test_validate_tar_member_symlink(self, tmp_path):
        """Test validation detects symlinks."""
        from souschef.ui.pages.history import _validate_tar_member

        member = MagicMock()
        member.size = 100
        member.name = "link.txt"
        member.issym = MagicMock(return_value=True)
        member.islnk = MagicMock(return_value=False)
        member.linkname = "/etc/passwd"

        result = _validate_tar_member(
            member, tmp_path, 0, 0, 100 * 1024 * 1024, 500 * 1024 * 1024, 10000
        )

        assert result["is_safe"] is False
        assert "symlink" in result["warning"].lower()


class TestParseConversionBlobKeys:
    """Test parsing conversion blob keys."""

    def test_parse_conversion_blob_keys_with_both_keys(self):
        """Test parsing conversion with both roles and repo blob keys."""
        from souschef.ui.pages.history import _parse_conversion_blob_keys

        conversion = MagicMock()
        conversion.blob_storage_key = "default_key"
        conversion.conversion_data = json.dumps(
            {"roles_blob_key": "roles_key", "repo_blob_key": "repo_key"}
        )

        roles_key, repo_key = _parse_conversion_blob_keys(conversion)
        assert roles_key == "roles_key"
        assert repo_key == "repo_key"

    def test_parse_conversion_blob_keys_missing_conversion_data(self):
        """Test parsing conversion with missing conversion_data."""
        from souschef.ui.pages.history import _parse_conversion_blob_keys

        conversion = MagicMock()
        conversion.blob_storage_key = "default_key"
        conversion.conversion_data = "{invalid json"

        roles_key, repo_key = _parse_conversion_blob_keys(conversion)
        assert roles_key == "default_key"
        assert repo_key is None

    def test_parse_conversion_blob_keys_no_repo_key(self):
        """Test parsing conversion without repo_blob_key."""
        from souschef.ui.pages.history import _parse_conversion_blob_keys

        conversion = MagicMock()
        conversion.blob_storage_key = "default_key"
        conversion.conversion_data = json.dumps({"roles_blob_key": "custom_roles_key"})

        roles_key, repo_key = _parse_conversion_blob_keys(conversion)
        assert roles_key == "custom_roles_key"
        assert repo_key is None


class TestHistoryPageUI:
    """Test main history page UI functions."""

    @patch("souschef.ui.pages.history.get_storage_manager")
    @patch("souschef.ui.pages.history.get_blob_storage")
    @patch("souschef.ui.pages.history.st")
    def test_show_history_page(self, mock_st, mock_blob_storage, mock_storage_manager):
        """Test main history page display."""
        from souschef.ui.pages.history import show_history_page

        # Setup mocks for tabs
        mock_tab1 = MagicMock()
        mock_tab2 = MagicMock()
        mock_tab3 = MagicMock()
        mock_st.tabs.return_value = (mock_tab1, mock_tab2, mock_tab3)
        mock_tab1.__enter__ = Mock(return_value=mock_tab1)
        mock_tab1.__exit__ = Mock(return_value=None)
        mock_tab2.__enter__ = Mock(return_value=mock_tab2)
        mock_tab2.__exit__ = Mock(return_value=None)
        mock_tab3.__enter__ = Mock(return_value=mock_tab3)
        mock_tab3.__exit__ = Mock(return_value=None)

        # Setup columns mock to handle different numbers of columns
        def create_columns(num_cols):
            if isinstance(num_cols, list):
                num_cols = len(num_cols)
            cols = tuple(MagicMock() for _ in range(num_cols))
            for col in cols:
                col.__enter__ = Mock(return_value=col)
                col.__exit__ = Mock(return_value=None)
            return cols

        mock_st.columns.side_effect = create_columns

        # Mock storage manager methods to return empty lists
        mock_storage = MagicMock()
        mock_storage.get_analysis_history.return_value = []
        mock_storage.get_conversion_history.return_value = []
        mock_storage.get_statistics.return_value = {
            "total_analyses": 0,
            "unique_cookbooks_analysed": 0,
            "total_conversions": 0,
            "successful_conversions": 0,
            "total_files_generated": 0,
            "avg_manual_hours": 0.0,
            "avg_ai_hours": 0.0,
        }
        mock_storage_manager.return_value = mock_storage

        show_history_page()

        mock_st.header.assert_called()
        mock_st.markdown.assert_called()
        mock_st.tabs.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_show_analysis_history_no_results(self, mock_st):
        """Test analysis history with no results."""
        from souschef.ui.pages.history import _show_analysis_history

        # Setup columns mock
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = (mock_col1, mock_col2)
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)

        mock_storage = MagicMock()
        mock_storage.get_analysis_history.return_value = []

        _show_analysis_history(mock_storage)

        mock_st.info.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_show_analysis_history_empty(self, mock_st):
        """Test filtered analysis history with no results."""
        from souschef.ui.pages.history import _show_analysis_history

        # Setup columns mock
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = (mock_col1, mock_col2)
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)

        mock_st.text_input.return_value = "nginx"
        mock_st.selectbox.return_value = 25

        mock_storage = MagicMock()
        mock_storage.get_analysis_history.return_value = []

        _show_analysis_history(mock_storage)

        mock_st.info.assert_called()
        mock_storage.get_analysis_history.assert_called_with(
            cookbook_name="nginx", limit=25
        )

    @patch("souschef.ui.pages.history.st")
    def test_show_analysis_history_with_filter(self, mock_st):
        """Test analysis history calls storage manager correctly."""
        from souschef.ui.pages.history import _show_analysis_history

        # Setup columns mock
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = (mock_col1, mock_col2)
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)

        mock_st.text_input.return_value = ""
        mock_st.selectbox.return_value = 25

        mock_storage = MagicMock()
        mock_storage.get_analysis_history.return_value = []

        _show_analysis_history(mock_storage)

        # Verify the function was called with correct parameters
        assert mock_storage.get_analysis_history.called


class TestHistoryPageSimple:
    """Simple tests for history page functions without complex mocking."""

    @patch("souschef.ui.pages.history.st")
    @patch("souschef.ui.pages.history.pd")
    def test_display_analysis_activity_breakdown(self, mock_pd, mock_st):
        """Test displaying activity breakdown."""
        from souschef.ui.pages.history import _display_analysis_activity_breakdown

        # Setup columns mock
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = (mock_col1, mock_col2)
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)

        activities = [
            {
                "activity_type": "Package Installation",
                "count": 5,
                "description": "Install packages",
                "manual_hours": 2.0,
                "ai_assisted_hours": 1.0,
                "time_saved_hours": 1.0,
                "efficiency_gain_percent": 50,
            }
        ]

        _display_analysis_activity_breakdown(activities)

        mock_st.markdown.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_display_analysis_activity_breakdown_empty(self, mock_st):
        """Test displaying empty activity breakdown."""
        from souschef.ui.pages.history import _display_analysis_activity_breakdown

        _display_analysis_activity_breakdown([])

        # Should return early without errors
        mock_st.markdown.assert_not_called()

    """Test conversion history functions."""

    def test_get_conversion_filters(self):
        """Test getting conversion filter values."""
        from souschef.ui.pages.history import _get_conversion_filters

        with patch("souschef.ui.pages.history.st") as mock_st:
            # Setup columns mock
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_col3 = MagicMock()
            mock_st.columns.return_value = (mock_col1, mock_col2, mock_col3)
            mock_col1.__enter__ = Mock(return_value=mock_col1)
            mock_col1.__exit__ = Mock(return_value=None)
            mock_col2.__enter__ = Mock(return_value=mock_col2)
            mock_col2.__exit__ = Mock(return_value=None)
            mock_col3.__enter__ = Mock(return_value=mock_col3)
            mock_col3.__exit__ = Mock(return_value=None)

            mock_st.text_input.return_value = "test-cookbook"
            mock_st.selectbox.side_effect = ["success", 25]

            cookbook_filter, status_filter, limit = _get_conversion_filters()

            assert cookbook_filter == "test-cookbook"
            assert status_filter == "success"
            assert limit == 25

    def test_filter_conversions_by_status_all(self):
        """Test filtering conversions with 'All' status."""
        from souschef.ui.pages.history import _filter_conversions_by_status

        conversions = [
            MagicMock(status="success"),
            MagicMock(status="failed"),
            MagicMock(status="partial"),
        ]

        result = _filter_conversions_by_status(conversions, "All")
        assert len(result) == 3

    def test_filter_conversions_by_status_success(self):
        """Test filtering conversions by success status."""
        from souschef.ui.pages.history import _filter_conversions_by_status

        conversions = [
            MagicMock(status="success"),
            MagicMock(status="failed"),
            MagicMock(status="success"),
        ]

        result = _filter_conversions_by_status(conversions, "success")
        assert len(result) == 2
        assert all(c.status == "success" for c in result)

    @patch("souschef.ui.pages.history.st")
    @patch("souschef.ui.pages.history.pd")
    def test_display_conversion_table(self, mock_pd, mock_st):
        """Test displaying conversion history table."""
        from souschef.ui.pages.history import _display_conversion_table

        conversions = [
            MagicMock(
                status="success",
                cookbook_name="cookbook1",
                output_type="ansible",
                files_generated=5,
                blob_storage_key="key1",
                created_at="2026-03-09T10:00:00",
                id="conv-1",
            )
        ]

        _display_conversion_table(conversions)

        mock_st.write.assert_called()
        mock_st.dataframe.assert_called()


class TestStatistics:
    """Test statistics display."""

    @patch("souschef.ui.pages.history.st")
    def test_show_statistics(self, mock_st):
        """Test statistics display."""
        from souschef.ui.pages.history import _show_statistics

        # Setup columns mock
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        mock_st.columns.side_effect = [
            (mock_col1, mock_col2, mock_col3),  # First columns(3) call
            (mock_col1, mock_col2, mock_col3),  # Second columns(3) call
        ]
        for col in [mock_col1, mock_col2, mock_col3]:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)

        mock_storage = MagicMock()
        mock_storage.get_statistics.return_value = {
            "total_analyses": 10,
            "unique_cookbooks_analysed": 5,
            "total_conversions": 8,
            "successful_conversions": 7,
            "total_files_generated": 50,
            "avg_manual_hours": 20.5,
            "avg_ai_hours": 10.2,
        }

        _show_statistics(mock_storage)

        mock_st.subheader.assert_called()
        mock_st.metric.assert_called()
        assert mock_st.metric.call_count >= 7


class TestDownloadFunctions:
    """Test download-related functions."""

    @patch("souschef.ui.pages.history.st")
    @patch("souschef.ui.pages.history.Path")
    def test_display_roles_download_file(self, mock_path_class, mock_st):
        """Test displaying roles download for file."""
        from souschef.ui.pages.history import _display_roles_download

        conversion = MagicMock(cookbook_name="test-cookbook", id="conv-1")
        blob_storage = MagicMock()
        roles_path = MagicMock(spec=Path)
        roles_path.exists.return_value = True
        roles_path.is_file.return_value = True
        roles_path.open.return_value.__enter__.return_value.read.return_value = (
            b"content"
        )

        blob_storage.download.return_value = roles_path

        _display_roles_download(conversion, blob_storage, "roles_key", MagicMock())

        mock_st.download_button.assert_called()

    @patch("souschef.ui.pages.history.st")
    def test_display_repo_download_no_key(self, mock_st):
        """Test displaying repo download when no key provided."""
        from souschef.ui.pages.history import _display_repo_download

        conversion = MagicMock(cookbook_name="test-cookbook", id="conv-1")
        blob_storage = MagicMock()

        _display_repo_download(conversion, blob_storage, None, MagicMock())

        # Should return early without calling download
        blob_storage.download.assert_not_called()

    @patch("souschef.ui.pages.history.st")
    @patch("souschef.ui.pages.history.zipfile.ZipFile")
    def test_create_and_display_zip_download(self, mock_zipfile_class, mock_st):
        """Test creating and displaying ZIP download."""
        from souschef.ui.pages.history import _create_and_display_zip_download

        # Create a temporary source directory with real files
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = Path(tmp_dir)
            test_file = source_path / "test.txt"
            test_file.write_text("content")

            _create_and_display_zip_download(
                source_path, "archive.zip", "Download", "key1"
            )

            mock_st.download_button.assert_called()


def test_history_pandas_import_error():
    """Test that history module handles missing pandas gracefully."""
    import sys
    from unittest.mock import patch

    # Store original pandas module if it exists
    original_pandas = sys.modules.get("pandas")

    try:
        # Remove pandas from sys.modules
        if "pandas" in sys.modules:
            del sys.modules["pandas"]

        # Mock pandas import to raise ImportError
        with patch.dict("sys.modules", {"pandas": None}):
            # Remove the history module from cache to force reimport
            if "souschef.ui.pages.history" in sys.modules:
                del sys.modules["souschef.ui.pages.history"]

            # Mock streamlit to prevent other import issues
            mock_st = MagicMock()
            with patch.dict("sys.modules", {"streamlit": mock_st}):
                # Now import with builtins.__import__ patched to raise ImportError for pandas
                import builtins

                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == "pandas":
                        raise ImportError("pandas not available")
                    return original_import(name, *args, **kwargs)

                with patch.object(builtins, "__import__", side_effect=mock_import):
                    # This should trigger the except ImportError block in history.py
                    import souschef.ui.pages.history as history_module

                    # Verify that pd is set to None
                    assert history_module.pd is None

    finally:
        # Restore original pandas module
        if original_pandas is not None:
            sys.modules["pandas"] = original_pandas
        elif "pandas" in sys.modules:
            del sys.modules["pandas"]
