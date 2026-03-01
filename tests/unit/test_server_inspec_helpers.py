"""Tests for InSpec control parsing helpers in server module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from souschef.server import _parse_controls_from_directory, _parse_controls_from_file


def test_parse_controls_from_directory_missing_dir(tmp_path: Path) -> None:
    """Missing controls directory raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        _parse_controls_from_directory(tmp_path)


def test_parse_controls_from_directory_read_error(tmp_path: Path) -> None:
    """Read errors in control files raise RuntimeError."""
    controls_dir = tmp_path / "controls"
    controls_dir.mkdir()
    control_file = controls_dir / "default.rb"
    control_file.write_text("control 'x' do end")

    with (
        patch(
            "souschef.parsers.inspec.safe_read_text", side_effect=OSError("read failed")
        ),
        pytest.raises(RuntimeError),
    ):
        _parse_controls_from_directory(tmp_path)


def test_parse_controls_from_directory_success(tmp_path: Path) -> None:
    """Parse controls directory and include file metadata."""
    controls_dir = tmp_path / "controls"
    controls_dir.mkdir()
    control_file = controls_dir / "default.rb"
    control_file.write_text("control 'x' do end")

    with (
        patch(
            "souschef.server.safe_read_text",
            return_value="control 'x' do end",
        ),
        patch(
            "souschef.server._parse_inspec_control",
            return_value=[{"id": "x"}],
        ),
    ):
        controls = _parse_controls_from_directory(tmp_path)

    assert controls[0]["file"] == "controls/default.rb"


def test_parse_controls_from_file_success(tmp_path: Path) -> None:
    """Parse control file and inject file name."""
    control_file = tmp_path / "control.rb"
    control_file.write_text("control 'x' do end")

    with (
        patch(
            "souschef.server.safe_read_text",
            return_value="control 'x' do end",
        ),
        patch(
            "souschef.server._parse_inspec_control",
            return_value=[{"id": "x"}],
        ),
    ):
        controls = _parse_controls_from_file(control_file)

    assert controls[0]["file"] == "control.rb"


def test_parse_controls_from_file_error(tmp_path: Path) -> None:
    """Parse control file errors raise RuntimeError."""
    control_file = tmp_path / "control.rb"
    control_file.write_text("control 'x' do end")

    with (
        patch("pathlib.Path.read_text", side_effect=OSError("read failed")),
        pytest.raises(RuntimeError),
    ):
        _parse_controls_from_file(control_file)
