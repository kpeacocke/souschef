"""Tests for health_check.py."""

from __future__ import annotations

import importlib
import json
import sys
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


def test_health_check_adds_app_path_to_sys_path_on_reload():
    """Test import-time branch that inserts app path into sys.path."""
    import souschef.ui.health_check as health_check

    app_path = str(health_check.Path(health_check.__file__).parent.parent)
    while app_path in sys.path:
        sys.path.remove(app_path)

    reloaded = importlib.reload(health_check)

    assert app_path in reloaded.sys.path
