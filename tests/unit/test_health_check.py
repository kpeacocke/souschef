"""Tests for health_check.py."""

from __future__ import annotations

import json
from unittest.mock import patch


def test_health_check_success():
    """Test health check success path."""
    from souschef.ui.health_check import main

    with (
        patch("souschef.ui.health_check.sys.exit") as mock_exit,
        patch("souschef.ui.health_check.sys.stdout.write") as mock_write,
    ):
        main()
        mock_exit.assert_called_once_with(0)
        assert mock_write.called


def test_health_check_failure():
    """Test health check failure path when import fails."""
    from souschef.ui.health_check import main

    with (
        patch("builtins.__import__", side_effect=ImportError("Module not found")),
        patch("souschef.ui.health_check.sys.exit") as mock_exit,
        patch("souschef.ui.health_check.sys.stdout.write") as mock_write,
    ):
        main()
        mock_exit.assert_called_once_with(1)
        assert mock_write.called


def test_health_check_output_format_success():
    """Test that health check produces valid JSON on success."""
    from souschef.ui.health_check import main

    with (
        patch("souschef.ui.health_check.sys.exit"),
        patch("souschef.ui.health_check.sys.stdout.write") as mock_write,
    ):
        main()

        # Get the JSON string that was written
        call_args = mock_write.call_args[0][0]
        result = json.loads(call_args)

        assert result["status"] == "healthy"
        assert result["service"] == "souschef-ui"


def test_health_check_output_format_failure():
    """Test that health check produces valid JSON on failure."""
    from souschef.ui.health_check import main

    with (
        patch("builtins.__import__", side_effect=Exception("Test error")),
        patch("souschef.ui.health_check.sys.exit"),
        patch("souschef.ui.health_check.sys.stdout.write") as mock_write,
    ):
        main()

        call_args = mock_write.call_args[0][0]
        result = json.loads(call_args)

        assert result["status"] == "unhealthy"
        assert result["service"] == "souschef-ui"
        assert "error" in result
