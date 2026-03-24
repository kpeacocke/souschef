"""Tests for Salt migration background job helpers."""

from __future__ import annotations

import json
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_streamlit_module() -> Generator[None, None, None]:
    """Ensure streamlit import is available during page module import."""
    with patch.dict("sys.modules", {"streamlit": MagicMock()}):
        yield


def test_batch_job_failure_hint_path_error() -> None:
    """Path-related failures return a concrete path remediation hint."""
    from souschef.ui.pages.salt_migration import _batch_job_failure_hint

    hint = _batch_job_failure_hint("Invalid path outside workspace")
    assert "workspace" in hint


def test_run_batch_conversion_background_job_success() -> None:
    """Background conversion job returns parsed result with progress/log calls."""
    from souschef.ui.pages.salt_migration import _run_batch_conversion_background_job

    progress_updates: list[int] = []
    log_lines: list[str] = []

    def _progress(value: int, _message: str | None = None) -> None:
        progress_updates.append(value)

    def _log(message: str) -> None:
        log_lines.append(message)

    payload = {
        "roles_created": ["web"],
        "files_written": ["/tmp/out/tasks/main.yml"],
        "warnings": [],
    }

    with (
        patch(
            "souschef.ui.pages.salt_migration._validate_ui_path",
            side_effect=["/safe/salt", "/safe/out"],
        ),
        patch(
            "souschef.ui.pages.salt_migration.convert_salt_directory_to_roles",
            return_value=json.dumps(payload),
        ),
    ):
        result = _run_batch_conversion_background_job(
            _progress,
            _log,
            "/salt",
            "/out",
        )

    assert result == payload
    assert progress_updates[-1] == 100
    assert any("Roles created" in line for line in log_lines)


def test_run_batch_conversion_background_job_invalid_path_raises() -> None:
    """Invalid source path should raise ValueError with actionable message."""
    from souschef.ui.pages.salt_migration import _run_batch_conversion_background_job

    with (
        patch(
            "souschef.ui.pages.salt_migration._validate_ui_path",
            return_value=None,
        ),
        pytest.raises(ValueError, match="Invalid or unsafe Salt directory path"),
    ):
        _run_batch_conversion_background_job(
            lambda *_args: None,
            lambda *_args: None,
            "/salt",
            "/out",
        )


def test_run_batch_conversion_background_job_converter_error_raises() -> None:
    """Converter error payload should be raised as ValueError."""
    from souschef.ui.pages.salt_migration import _run_batch_conversion_background_job

    with (
        patch(
            "souschef.ui.pages.salt_migration._validate_ui_path",
            side_effect=["/safe/salt", "/safe/out"],
        ),
        patch(
            "souschef.ui.pages.salt_migration.convert_salt_directory_to_roles",
            return_value=json.dumps({"error": "failed conversion"}),
        ),
        pytest.raises(ValueError, match="failed conversion"),
    ):
        _run_batch_conversion_background_job(
            lambda *_args: None,
            lambda *_args: None,
            "/salt",
            "/out",
        )
