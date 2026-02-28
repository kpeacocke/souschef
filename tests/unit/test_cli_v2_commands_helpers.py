"""Helper function tests for cli_v2_commands module."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest

from souschef.cli_v2_commands import (
    _output_result,
    _resolve_output_path,
    _safe_write_file,
    _validate_user_path,
    create_v2_group,
    register_v2_commands,
)


class TestValidateUserPath:
    """Test _validate_user_path helper function."""

    def test_validate_user_path_none_returns_cwd(self) -> None:
        """None input returns current working directory."""
        result = _validate_user_path(None)
        assert result == Path.cwd()

    def test_validate_user_path_existing_directory(self, tmp_path: Path) -> None:
        """Valid existing path is resolved and returned."""
        result = _validate_user_path(str(tmp_path))
        assert result.exists()
        assert result.is_absolute()

    def test_validate_user_path_nonexistent_raises(self) -> None:
        """Non-existent path raises ValueError."""
        with pytest.raises(ValueError, match="Path does not exist"):
            _validate_user_path("/nonexistent/path/that/does/not/exist")

    def test_validate_user_path_oserror_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OSError during path resolution raises ValueError."""

        def raise_oserror(*_args, **_kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "resolve", raise_oserror)

        with pytest.raises(ValueError, match="Invalid path"):
            _validate_user_path("/some/path")


class TestResolveOutputPath:
    """Test _resolve_output_path helper function."""

    def test_resolve_output_path_default(self, tmp_path: Path) -> None:
        """No output specified uses default path."""
        default = tmp_path / "output.json"
        with patch("souschef.cli_v2_commands._get_workspace_root") as mock_root:
            mock_root.return_value = tmp_path

            result = _resolve_output_path(None, default)

            assert result.name == "output.json"
            assert result.parent.exists()

    def test_resolve_output_path_custom_output(self, tmp_path: Path) -> None:
        """Custom output path is resolved."""
        custom_output = str(tmp_path / "custom" / "result.json")
        default = tmp_path / "output.json"

        with (
            patch("souschef.cli_v2_commands._get_workspace_root") as mock_root,
            patch("souschef.cli_v2_commands._normalize_path") as mock_norm,
            patch("souschef.cli_v2_commands._ensure_within_base_path") as mock_safe,
        ):
            mock_root.return_value = tmp_path
            mock_norm.return_value = Path(custom_output)
            mock_safe.return_value = Path(custom_output).resolve()

            result = _resolve_output_path(custom_output, default)

            assert result.parent.exists()

    def test_resolve_output_path_validation_error_raises_click_abort(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ValueError during validation raises click.Abort."""

        def raise_value_error(*_args, **_kwargs):
            raise ValueError("Invalid path")

        monkeypatch.setattr(
            "souschef.cli_v2_commands._get_workspace_root",
            raise_value_error,
        )

        with pytest.raises(click.Abort):
            _resolve_output_path(None, tmp_path / "output.json")


class TestSafeWriteFile:
    """Test _safe_write_file helper function."""

    def test_safe_write_file_creates_file(self, tmp_path: Path) -> None:
        """File is created with content at resolved path."""
        content = "Test content"
        output_path = tmp_path / "output.json"

        with patch("souschef.cli_v2_commands._resolve_output_path") as mock_resolve:
            mock_resolve.return_value = output_path

            result = _safe_write_file(content, None, tmp_path / "default.json")

            assert result == output_path
            assert output_path.exists()
            assert output_path.read_text() == content

    def test_safe_write_file_oserror_raises_click_abort(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OSError during write raises click.Abort."""

        def raise_oserror(*_args, **_kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "open", raise_oserror)

        with patch("souschef.cli_v2_commands._resolve_output_path") as mock_resolve:
            mock_resolve.return_value = tmp_path / "output.json"

            with pytest.raises(click.Abort):
                _safe_write_file("content", None, tmp_path / "default.json")


class TestOutputResult:
    """Test _output_result helper function."""

    def test_output_result_text_format(self, capsys) -> None:
        """Text format outputs content directly."""
        result = "Some text output"
        _output_result(result, "text")

        captured = capsys.readouterr()
        assert result in captured.out

    def test_output_result_json_format(self, capsys) -> None:
        """JSON format outputs properly formatted JSON."""
        result = json.dumps({"key": "value"})
        _output_result(result, "json")

        captured = capsys.readouterr()
        assert "key" in captured.out
        assert "value" in captured.out

    def test_output_result_invalid_json_exits(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        """Invalid JSON with json format exits."""
        result = "not valid json"

        def mock_exit(code):
            raise SystemExit(code)

        monkeypatch.setattr(sys, "exit", mock_exit)

        with pytest.raises(SystemExit, match="1"):
            _output_result(result, "json")

        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out


class TestCreateV2Group:
    """Test create_v2_group helper function."""

    def test_create_v2_group_returns_click_group(self) -> None:
        """Returns a Click Group object."""
        result = create_v2_group()

        assert isinstance(result, click.Group)
        assert result.name == "v2"

    def test_create_v2_group_has_commands(self) -> None:
        """Group has all v2 commands registered."""
        group = create_v2_group()

        # The group should have subcommands (they're added via add_command)
        # We can check this by inspecting the Group's commands dict
        assert group.commands is not None
        assert "migrate" in group.commands
        assert "status" in group.commands
        assert "list" in group.commands
        assert "rollback" in group.commands


class TestRegisterV2Commands:
    """Test register_v2_commands function."""

    def test_register_v2_commands_adds_to_cli(self) -> None:
        """Registers v2 group to the main CLI."""
        mock_cli = MagicMock()
        mock_cli.add_command = MagicMock()

        register_v2_commands(mock_cli)

        mock_cli.add_command.assert_called_once()
        call_args = mock_cli.add_command.call_args
        assert call_args[1]["name"] == "v2"
