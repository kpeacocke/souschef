"""Unit tests for Puppet Server connector workflows."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from souschef.webhooks import requests


def _ctx() -> MagicMock:
    """Create a simple context-manager mock."""
    ctx = MagicMock()
    ctx.__enter__.return_value = ctx
    ctx.__exit__.return_value = False
    return ctx


class TestPuppetServerClient:
    """Tests for the Puppet Server HTTP client."""

    def test_initialises_certificate_authentication(self) -> None:
        """Certificate, key, and CA settings are applied to the session."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient(
            server_url="https://puppet.example.test:8140/",
            cert_path="certs/client.pem",
            key_path="certs/client.key",
            ca_path="certs/ca.pem",
            timeout=15,
        )

        assert client.server_url == "https://puppet.example.test:8140"
        assert client.timeout == 15
        assert client.session.cert == ("certs/client.pem", "certs/client.key")
        assert client.session.verify == "certs/ca.pem"

    def test_request_json_returns_supported_payload(self) -> None:
        """JSON objects and lists are returned unchanged."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        response = MagicMock()
        response.json.return_value = [{"name": "web01"}]
        client.session.get = MagicMock(return_value=response)

        result = client._request_json("/puppet/v3/nodes")

        assert result == [{"name": "web01"}]
        client.session.get.assert_called_once_with(
            "https://puppet.example.test/puppet/v3/nodes",
            params=None,
            timeout=30,
        )

    def test_request_json_wraps_request_failures(self) -> None:
        """HTTP errors are raised as runtime errors."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        client.session.get = MagicMock(
            side_effect=requests.RequestException("request failed")
        )

        with pytest.raises(RuntimeError, match="request failed"):
            client._request_json("/puppet/v3/nodes")

    def test_request_json_wraps_invalid_json(self) -> None:
        """Invalid JSON bodies are rejected."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        response = MagicMock()
        response.json.side_effect = ValueError("invalid")
        client.session.get = MagicMock(return_value=response)

        with pytest.raises(RuntimeError, match="invalid JSON"):
            client._request_json("/puppet/v3/nodes")

    def test_request_json_rejects_scalar_payloads(self) -> None:
        """Scalar JSON payloads are rejected."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        response = MagicMock()
        response.json.return_value = "scalar"
        client.session.get = MagicMock(return_value=response)

        with pytest.raises(RuntimeError, match="unsupported JSON payload"):
            client._request_json("/puppet/v3/nodes")

    def test_list_nodes_filters_non_dict_items(self) -> None:
        """Node listing keeps only dictionary entries."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        with patch.object(
            client,
            "_request_json",
            return_value=[{"name": "web01"}, "skip", {"name": "web02"}],
        ):
            result = client.list_nodes(environment="prod")

        assert result == [{"name": "web01"}, {"name": "web02"}]

    def test_list_nodes_requires_list_payload(self) -> None:
        """Node listing rejects non-list payloads."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        with (
            patch.object(
                client,
                "_request_json",
                return_value={"name": "web01"},
            ),
            pytest.raises(RuntimeError, match="must be a list"),
        ):
            client.list_nodes()

    def test_get_catalog_quotes_node_name(self) -> None:
        """Catalog fetches URL-encode node names."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        with patch.object(
            client,
            "_request_json",
            return_value={"resources": []},
        ) as mock_request:
            result = client.get_catalog("web 01/example", environment="prod")

        assert result == {"resources": []}
        mock_request.assert_called_once_with(
            "/puppet/v3/catalog/web%2001%2Fexample",
            params={"environment": "prod"},
        )

    def test_get_catalog_requires_object_payload(self) -> None:
        """Catalog fetches reject non-object payloads."""
        from souschef.api_clients import PuppetServerClient

        client = PuppetServerClient("https://puppet.example.test", "cert", "key")
        with (
            patch.object(
                client,
                "_request_json",
                return_value=[],
            ),
            pytest.raises(RuntimeError, match="JSON object"),
        ):
            client.get_catalog("web01")


class TestPuppetOrchestratorConnector:
    """Tests for Puppet Server orchestration helpers."""

    @patch("souschef.orchestrators.puppet.PuppetServerClient")
    def test_list_puppet_server_nodes_sorts_names(
        self,
        mock_client_cls: MagicMock,
    ) -> None:
        """Node listings are sorted and counted."""
        mock_client = mock_client_cls.return_value
        mock_client.list_nodes.return_value = [
            {"name": "web02"},
            {"name": "web01"},
            {"title": "ignored"},
        ]

        from souschef.orchestrators.puppet import list_puppet_server_nodes

        result = list_puppet_server_nodes(
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            environment="prod",
            ca_path="ca.pem",
        )

        assert result == {
            "status": "success",
            "environment": "prod",
            "count": 2,
            "nodes": ["web01", "web02"],
        }
        mock_client.list_nodes.assert_called_once_with(environment="prod")

    @patch("souschef.orchestrators.puppet.PuppetServerClient")
    def test_import_puppet_catalog_to_ir_builds_graph(
        self,
        mock_client_cls: MagicMock,
    ) -> None:
        """Catalog imports are mapped into the shared IR and fidelity report."""
        mock_client = mock_client_cls.return_value
        mock_client.get_catalog.return_value = {
            "resources": [
                {
                    "type": "Package",
                    "title": "nginx",
                    "file": "site.pp",
                    "line": 10,
                    "parameters": {"ensure": "installed"},
                },
                {
                    "type": "Custom",
                    "title": "review-me",
                    "file": "site.pp",
                    "line": 20,
                    "parameters": {"enabled": True},
                },
            ],
            "edges": [{"source": "Package[nginx]", "target": "Custom[review-me]"}],
        }

        from souschef.orchestrators.puppet import import_puppet_catalog_to_ir

        result = import_puppet_catalog_to_ir(
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            "web01",
            environment="prod",
        )

        assert result["status"] == "success"
        assert result["node"] == "web01"
        assert result["environment"] == "prod"
        assert result["fidelity_report"] == {
            "total_resources": 2,
            "mapped_resources": 1,
            "review_required": 1,
            "coverage_percent": 50.0,
            "resource_types": {"package": 1, "custom": 1},
        }
        assert len(result["ir"]["nodes"]) == 2
        assert len(result["ir"]["edges"]) == 1


class TestPuppetServerTools:
    """Tests for MCP wrappers around Puppet Server helpers."""

    def test_list_puppet_server_nodes_tool_returns_json(self) -> None:
        """Server tool normalises paths and returns JSON."""
        from souschef.server import list_puppet_server_nodes

        with (
            patch(
                "souschef.server._normalise_workspace_path",
                side_effect=[Path("/workspace/cert.pem"), Path("/workspace/key.pem")],
            ) as mock_normalise,
            patch(
                "souschef.server._list_puppet_server_nodes",
                return_value={"status": "success", "nodes": ["web01"]},
            ) as mock_list_nodes,
        ):
            result = list_puppet_server_nodes(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
            )

        assert json.loads(result) == {"status": "success", "nodes": ["web01"]}
        assert mock_normalise.call_count == 2
        mock_list_nodes.assert_called_once_with(
            server_url="https://puppet.example.test",
            cert_path="/workspace/cert.pem",
            key_path="/workspace/key.pem",
            environment="",
            ca_path="",
        )

    def test_list_puppet_server_nodes_tool_returns_error_json(self) -> None:
        """Server tool wraps exceptions as JSON errors."""
        from souschef.server import list_puppet_server_nodes

        with patch(
            "souschef.server._normalise_workspace_path",
            side_effect=ValueError("bad path"),
        ):
            result = list_puppet_server_nodes(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
            )

        assert json.loads(result) == {"status": "error", "error": "bad path"}

    def test_import_puppet_catalog_to_ir_tool_returns_json(self) -> None:
        """Catalog import tool returns the orchestrator result as JSON."""
        from souschef.server import import_puppet_catalog_to_ir

        with (
            patch(
                "souschef.server._normalise_workspace_path",
                side_effect=[
                    Path("/workspace/cert.pem"),
                    Path("/workspace/key.pem"),
                    Path("/workspace/ca.pem"),
                ],
            ) as mock_normalise,
            patch(
                "souschef.server._import_puppet_catalog_to_ir",
                return_value={"status": "success", "node": "web01"},
            ) as mock_import,
        ):
            result = import_puppet_catalog_to_ir(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
                "web01",
                ca_path="ca.pem",
            )

        assert json.loads(result) == {"status": "success", "node": "web01"}
        assert mock_normalise.call_count == 3
        mock_import.assert_called_once_with(
            server_url="https://puppet.example.test",
            cert_path="/workspace/cert.pem",
            key_path="/workspace/key.pem",
            node_name="web01",
            environment="",
            ca_path="/workspace/ca.pem",
        )


@pytest.fixture(autouse=True)
def mock_streamlit() -> Generator[MagicMock, None, None]:
    """Mock Streamlit for Puppet migration UI tests."""
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.spinner.return_value = _ctx()
    mock_st.expander.return_value = _ctx()
    mock_st.columns.side_effect = lambda n: [_ctx() for _ in range(n)]

    with patch("souschef.ui.pages.puppet_migration.st", mock_st):
        yield mock_st


from souschef.ui.pages.puppet_migration import (  # noqa: E402
    INPUT_METHOD_PUPPET_SERVER,
    _run_puppet_server_catalog_import,
    _run_puppet_server_node_listing,
    _show_puppet_server_section,
    show_puppet_migration_page,
)


class TestPuppetMigrationUiConnector:
    """Tests for the Puppet Server mode in the Streamlit page."""

    def test_show_page_routes_to_puppet_server_section(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Selecting the Puppet Server mode renders that section."""
        mock_streamlit.radio.return_value = INPUT_METHOD_PUPPET_SERVER

        with patch(
            "souschef.ui.pages.puppet_migration._show_puppet_server_section"
        ) as mock_section:
            show_puppet_migration_page()

        mock_section.assert_called_once_with()

    def test_show_puppet_server_section_requires_connection_fields(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """List or import actions require the connection settings."""
        mock_streamlit.text_input.side_effect = ["", "", "", "", ""]
        mock_streamlit.button.side_effect = [True, False]

        _show_puppet_server_section()

        mock_streamlit.warning.assert_called_once()

    def test_show_puppet_server_section_lists_nodes(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """List nodes triggers the connector helper."""
        mock_streamlit.text_input.side_effect = [
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            "ca.pem",
            "prod",
            "web01",
        ]
        mock_streamlit.button.side_effect = [True, False]

        with patch(
            "souschef.ui.pages.puppet_migration._run_puppet_server_node_listing"
        ) as mock_list:
            _show_puppet_server_section()

        mock_list.assert_called_once_with(
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            "prod",
            "ca.pem",
        )

    def test_show_puppet_server_section_imports_selected_node(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Import uses the selected node when nodes were preloaded."""
        mock_streamlit.session_state["puppet_server_nodes"] = ["web01", "web02"]
        mock_streamlit.text_input.side_effect = [
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            "ca.pem",
            "prod",
        ]
        mock_streamlit.button.side_effect = [False, True]
        mock_streamlit.selectbox.return_value = "web02"

        with patch(
            "souschef.ui.pages.puppet_migration._run_puppet_server_catalog_import"
        ) as mock_import:
            _show_puppet_server_section()

        mock_import.assert_called_once_with(
            "https://puppet.example.test",
            "cert.pem",
            "key.pem",
            "web02",
            "prod",
            "ca.pem",
        )

    def test_run_puppet_server_node_listing_success(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Successful node listings populate session state."""
        with patch(
            "souschef.ui.pages.puppet_migration.list_puppet_server_nodes",
            return_value={
                "status": "success",
                "count": 2,
                "nodes": ["web01", "web02"],
            },
        ):
            _run_puppet_server_node_listing(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
                "prod",
                "ca.pem",
            )

        assert mock_streamlit.session_state["puppet_server_nodes"] == ["web01", "web02"]
        mock_streamlit.success.assert_called_once_with("Loaded 2 Puppet node(s).")

    def test_run_puppet_server_node_listing_error(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Listing failures are surfaced in the UI."""
        with patch(
            "souschef.ui.pages.puppet_migration.list_puppet_server_nodes",
            return_value={"status": "error", "error": "connection failed"},
        ):
            _run_puppet_server_node_listing(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
                "prod",
                "ca.pem",
            )

        mock_streamlit.error.assert_called_once_with("connection failed")

    def test_run_puppet_server_catalog_import_success(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Successful catalog imports render fidelity and IR JSON."""
        with patch(
            "souschef.ui.pages.puppet_migration.import_puppet_catalog_to_ir",
            return_value={
                "status": "success",
                "fidelity_report": {"coverage_percent": 100.0},
                "ir": {"nodes": []},
            },
        ):
            _run_puppet_server_catalog_import(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
                "web01",
                "prod",
                "ca.pem",
            )

        mock_streamlit.success.assert_called_once_with(
            "Puppet catalog imported successfully."
        )
        assert mock_streamlit.json.call_count == 2

    def test_run_puppet_server_catalog_import_error(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Catalog import failures are surfaced in the UI."""
        with patch(
            "souschef.ui.pages.puppet_migration.import_puppet_catalog_to_ir",
            return_value={"status": "error", "error": "import failed"},
        ):
            _run_puppet_server_catalog_import(
                "https://puppet.example.test",
                "cert.pem",
                "key.pem",
                "web01",
                "prod",
                "ca.pem",
            )

        mock_streamlit.error.assert_called_once_with("import failed")
