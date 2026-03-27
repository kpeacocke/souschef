"""Unit tests for CLI API companion commands."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from souschef.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


def test_api_serve_invokes_server(runner: CliRunner) -> None:
    """The api serve command delegates to the REST server runner."""
    with patch("souschef.cli.run_api_server") as mock_run_api_server:
        result = runner.invoke(
            cli, ["api", "serve", "--host", "0.0.0.0", "--port", "9090"]
        )

    assert result.exit_code == 0
    mock_run_api_server.assert_called_once_with(host="0.0.0.0", port=9090)


def test_api_webhook_rejects_invalid_json(runner: CliRunner) -> None:
    """Invalid webhook JSON exits with an error."""
    result = runner.invoke(
        cli,
        [
            "api",
            "webhook",
            "--url",
            "https://hooks.example.test",
            "--event",
            "done",
            "--payload",
            "{",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid payload JSON" in result.output


def test_api_webhook_requires_object_payload(runner: CliRunner) -> None:
    """Webhook payloads must decode to JSON objects."""
    result = runner.invoke(
        cli,
        [
            "api",
            "webhook",
            "--url",
            "https://hooks.example.test",
            "--event",
            "done",
            "--payload",
            "[]",
        ],
    )

    assert result.exit_code == 1
    assert "must decode to a JSON object" in result.output


def test_api_webhook_success(runner: CliRunner) -> None:
    """Successful webhook CLI calls print JSON and exit cleanly."""
    with patch(
        "souschef.cli.send_webhook_notification",
        return_value={"status": "success", "status_code": 200},
    ) as mock_send:
        result = runner.invoke(
            cli,
            [
                "api",
                "webhook",
                "--url",
                "https://hooks.example.test",
                "--event",
                "done",
                "--payload",
                '{"status": "ok"}',
                "--secret",
                "shared-secret",
            ],
        )

    assert result.exit_code == 0
    assert json.loads(result.output) == {"status": "success", "status_code": 200}
    mock_send.assert_called_once_with(
        "https://hooks.example.test",
        "done",
        {"status": "ok"},
        secret="shared-secret",
    )


def test_api_webhook_failure_exits_non_zero(runner: CliRunner) -> None:
    """Failed webhook deliveries bubble up as a non-zero exit."""
    with patch(
        "souschef.cli.send_webhook_notification",
        return_value={"status": "error", "error": "bad gateway"},
    ):
        result = runner.invoke(
            cli,
            [
                "api",
                "webhook",
                "--url",
                "https://hooks.example.test",
                "--event",
                "done",
                "--payload",
                '{"status": "ok"}',
            ],
        )

    assert result.exit_code == 1
    assert json.loads(result.output) == {"status": "error", "error": "bad gateway"}
