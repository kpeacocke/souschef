"""Tests for Salt MCP tools in souschef/server.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.server import (
    convert_salt_to_ansible,
    parse_salt_directory,
    parse_salt_pillar,
    parse_salt_sls,
    parse_salt_top,
    query_salt_master,
)


# ---------------------------------------------------------------------------
# parse_salt_sls MCP tool
# ---------------------------------------------------------------------------


def test_server_parse_salt_sls_delegates_to_parser(tmp_path: Path) -> None:
    """parse_salt_sls MCP tool delegates to the parser module."""
    expected = json.dumps({"summary": {"total_states": 1}})

    with patch(
        "souschef.server.parse_salt_sls.__wrapped__",
        return_value=expected,
        create=True,
    ):
        with patch(
            "souschef.parsers.salt.parse_salt_sls", return_value=expected
        ) as mock_parser:
            # Call via the server tool which validates path first
            with patch("souschef.server._validate_path_length"):
                result = parse_salt_sls(str(tmp_path / "init.sls"))

    assert isinstance(result, str)


def test_server_parse_salt_sls_path_too_long() -> None:
    """parse_salt_sls rejects paths exceeding max length."""
    long_path = "x" * 5000
    result = parse_salt_sls(long_path)
    assert "Error" in result or "error" in result.lower() or "exceeds" in result


def test_server_parse_salt_sls_calls_parser() -> None:
    """parse_salt_sls MCP tool calls the underlying parser."""
    expected = json.dumps({"summary": {"total_states": 0}, "states": []})
    with patch("souschef.server._parse_salt_sls", return_value=expected) as mock:
        result = parse_salt_sls("/some/path.sls")
    mock.assert_called_once_with("/some/path.sls")
    assert result == expected


# ---------------------------------------------------------------------------
# parse_salt_pillar MCP tool
# ---------------------------------------------------------------------------


def test_server_parse_salt_pillar_path_too_long() -> None:
    """parse_salt_pillar rejects paths exceeding max length."""
    long_path = "x" * 5000
    result = parse_salt_pillar(long_path)
    assert "Error" in result or "error" in result.lower() or "exceeds" in result


def test_server_parse_salt_pillar_calls_parser() -> None:
    """parse_salt_pillar MCP tool calls the underlying parser."""
    expected = json.dumps({"flattened": {}, "summary": {"total_keys": 0}})
    with patch(
        "souschef.server._parse_salt_pillar", return_value=expected
    ) as mock:
        result = parse_salt_pillar("/some/pillar.sls")
    mock.assert_called_once_with("/some/pillar.sls")
    assert result == expected


# ---------------------------------------------------------------------------
# parse_salt_top MCP tool
# ---------------------------------------------------------------------------


def test_server_parse_salt_top_path_too_long() -> None:
    """parse_salt_top rejects paths exceeding max length."""
    long_path = "x" * 5000
    result = parse_salt_top(long_path)
    assert "Error" in result or "error" in result.lower() or "exceeds" in result


def test_server_parse_salt_top_calls_parser() -> None:
    """parse_salt_top MCP tool calls the underlying parser."""
    expected = json.dumps({"environments": {}, "summary": {}})
    with patch("souschef.server._parse_salt_top", return_value=expected) as mock:
        result = parse_salt_top("/some/top.sls")
    mock.assert_called_once_with("/some/top.sls")
    assert result == expected


# ---------------------------------------------------------------------------
# parse_salt_directory MCP tool
# ---------------------------------------------------------------------------


def test_server_parse_salt_directory_path_too_long() -> None:
    """parse_salt_directory rejects paths exceeding max length."""
    long_path = "x" * 5000
    result = parse_salt_directory(long_path)
    assert "Error" in result or "error" in result.lower() or "exceeds" in result


def test_server_parse_salt_directory_calls_parser() -> None:
    """parse_salt_directory MCP tool calls the underlying parser."""
    expected = json.dumps({"summary": {"total_files": 0}})
    with patch(
        "souschef.server._parse_salt_directory", return_value=expected
    ) as mock:
        result = parse_salt_directory("/srv/salt")
    mock.assert_called_once_with("/srv/salt")
    assert result == expected


# ---------------------------------------------------------------------------
# convert_salt_to_ansible MCP tool
# ---------------------------------------------------------------------------


def test_server_convert_salt_to_ansible_path_too_long() -> None:
    """convert_salt_to_ansible rejects paths exceeding max length."""
    long_path = "x" * 5000
    result = convert_salt_to_ansible(long_path)
    assert "Error" in result or "error" in result.lower() or "exceeds" in result


def test_server_convert_salt_to_ansible_calls_converter() -> None:
    """convert_salt_to_ansible MCP tool calls the underlying converter."""
    expected = json.dumps(
        {
            "playbook": "---\n- name: test",
            "tasks_converted": 1,
            "tasks_unconverted": 0,
            "ansible_vars": {},
            "warnings": [],
        }
    )
    with patch(
        "souschef.server._convert_salt_sls_to_ansible", return_value=expected
    ) as mock:
        result = convert_salt_to_ansible("/some/path.sls", "myplay")
    mock.assert_called_once_with("/some/path.sls", "myplay")
    assert result == expected


def test_server_convert_salt_to_ansible_default_playbook_name() -> None:
    """convert_salt_to_ansible uses empty string as default playbook name."""
    expected = json.dumps({"playbook": "---"})
    with patch(
        "souschef.server._convert_salt_sls_to_ansible", return_value=expected
    ) as mock:
        result = convert_salt_to_ansible("/some/path.sls")
    mock.assert_called_once_with("/some/path.sls", "")


# ---------------------------------------------------------------------------
# query_salt_master MCP tool
# ---------------------------------------------------------------------------


def test_server_query_salt_master_url_too_long() -> None:
    """query_salt_master rejects URLs exceeding max length."""
    long_url = "https://salt-master/" + "x" * 5000
    result = query_salt_master(long_url, "user", "pass")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error"
    assert "exceeds" in result_dict["error"]


def test_server_query_salt_master_invalid_query_type() -> None:
    """query_salt_master rejects invalid query_type values."""
    result = query_salt_master(
        "https://salt-master:8080", "user", "pass", query_type="invalid"
    )
    result_dict = json.loads(result)
    assert result_dict["status"] == "error"
    assert "Invalid query_type" in result_dict["error"]


def test_server_query_salt_master_connection_error() -> None:
    """Connection errors are returned as JSON error."""
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        result = query_salt_master(
            "https://salt-master:8080", "user", "pass"
        )
    result_dict = json.loads(result)
    assert result_dict["status"] == "error"
    assert "Connection error" in result_dict["error"]


def test_server_query_salt_master_http_error() -> None:
    """HTTP errors are returned as JSON error."""
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            "https://salt-master:8080/login", 401, "Unauthorized", {}, None
        ),
    ):
        result = query_salt_master(
            "https://salt-master:8080", "user", "pass"
        )
    result_dict = json.loads(result)
    assert result_dict["status"] == "error"
    assert "401" in result_dict["error"]


def test_server_query_salt_master_auth_no_token() -> None:
    """Missing token in login response returns error."""
    mock_response = MagicMock()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_response.read.return_value = json.dumps({"return": [{}]}).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=mock_response):
        result = query_salt_master(
            "https://salt-master:8080", "user", "pass"
        )
    result_dict = json.loads(result)
    assert result_dict["status"] == "error"
    assert "Authentication failed" in result_dict["error"]


def test_server_query_salt_master_top_success() -> None:
    """Successful top query returns structured result."""
    login_response = MagicMock()
    login_response.__enter__ = MagicMock(return_value=login_response)
    login_response.__exit__ = MagicMock(return_value=False)
    login_response.read.return_value = json.dumps(
        {"return": [{"token": "abc123"}]}
    ).encode("utf-8")

    query_response = MagicMock()
    query_response.__enter__ = MagicMock(return_value=query_response)
    query_response.__exit__ = MagicMock(return_value=False)
    query_response.read.return_value = json.dumps(
        {"return": [{"minion1": {"base": ["common", "webserver"]}}]}
    ).encode("utf-8")

    with patch(
        "urllib.request.urlopen", side_effect=[login_response, query_response]
    ):
        result = query_salt_master(
            "https://salt-master:8080", "user", "pass", target="*", query_type="top"
        )

    result_dict = json.loads(result)
    assert result_dict["status"] == "success"
    assert result_dict["query_type"] == "top"
    assert result_dict["target"] == "*"


def test_server_query_salt_master_states_query() -> None:
    """States query uses state.show_highstate function."""
    login_response = MagicMock()
    login_response.__enter__ = MagicMock(return_value=login_response)
    login_response.__exit__ = MagicMock(return_value=False)
    login_response.read.return_value = json.dumps(
        {"return": [{"token": "tok"}]}
    ).encode("utf-8")

    query_response = MagicMock()
    query_response.__enter__ = MagicMock(return_value=query_response)
    query_response.__exit__ = MagicMock(return_value=False)
    query_response.read.return_value = json.dumps({"return": [{}]}).encode("utf-8")

    with patch(
        "urllib.request.urlopen", side_effect=[login_response, query_response]
    ):
        result = query_salt_master(
            "https://salt-master:8080",
            "user",
            "pass",
            query_type="states",
        )

    result_dict = json.loads(result)
    assert result_dict["status"] == "success"
    assert result_dict["query_type"] == "states"


def test_server_query_salt_master_pillar_query() -> None:
    """Pillar query uses pillar.items function."""
    login_response = MagicMock()
    login_response.__enter__ = MagicMock(return_value=login_response)
    login_response.__exit__ = MagicMock(return_value=False)
    login_response.read.return_value = json.dumps(
        {"return": [{"token": "tok"}]}
    ).encode("utf-8")

    query_response = MagicMock()
    query_response.__enter__ = MagicMock(return_value=query_response)
    query_response.__exit__ = MagicMock(return_value=False)
    query_response.read.return_value = json.dumps({"return": [{}]}).encode("utf-8")

    with patch(
        "urllib.request.urlopen", side_effect=[login_response, query_response]
    ):
        result = query_salt_master(
            "https://salt-master:8080",
            "user",
            "pass",
            query_type="pillar",
        )

    result_dict = json.loads(result)
    assert result_dict["status"] == "success"
    assert result_dict["query_type"] == "pillar"


def test_server_query_salt_master_generic_exception() -> None:
    """Generic exceptions are handled as JSON error."""
    with patch(
        "urllib.request.urlopen",
        side_effect=RuntimeError("unexpected failure"),
    ):
        result = query_salt_master(
            "https://salt-master:8080", "user", "pass"
        )
    result_dict = json.loads(result)
    assert result_dict["status"] == "error"
    assert "unexpected failure" in result_dict["error"]
