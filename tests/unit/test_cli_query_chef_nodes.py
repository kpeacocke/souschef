"""CLI tests for query-chef-nodes command."""

from unittest.mock import patch

from click.testing import CliRunner

from souschef.cli import cli


def test_query_chef_nodes_success_json(monkeypatch) -> None:
    """query-chef-nodes returns JSON output when nodes exist."""
    runner = CliRunner()
    monkeypatch.setenv("CHEF_SERVER_URL", "https://chef.example")
    monkeypatch.setenv("CHEF_CLIENT_NAME", "client")
    monkeypatch.setenv("CHEF_CLIENT_KEY_PATH", "/tmp/key.pem")

    with patch("souschef.core.chef_server.get_chef_nodes") as mock_get:
        mock_get.return_value = [
            {"name": "node1", "environment": "prod", "platform": "ubuntu"}
        ]
        result = runner.invoke(cli, ["query-chef-nodes", "--json"])

    assert result.exit_code == 0
    assert "node1" in result.output
    assert "environment" in result.output


def test_query_chef_nodes_no_nodes(monkeypatch) -> None:
    """query-chef-nodes handles empty results."""
    runner = CliRunner()
    monkeypatch.setenv("CHEF_SERVER_URL", "https://chef.example")
    monkeypatch.setenv("CHEF_CLIENT_NAME", "client")
    monkeypatch.setenv("CHEF_CLIENT_KEY_PATH", "/tmp/key.pem")

    with patch("souschef.core.chef_server.get_chef_nodes", return_value=[]):
        result = runner.invoke(cli, ["query-chef-nodes"])

    assert result.exit_code == 0
    assert "No nodes found" in result.output


def test_query_chef_nodes_error(monkeypatch) -> None:
    """query-chef-nodes exits on errors from Chef server."""
    runner = CliRunner()
    monkeypatch.setenv("CHEF_SERVER_URL", "https://chef.example")
    monkeypatch.setenv("CHEF_CLIENT_NAME", "client")
    monkeypatch.setenv("CHEF_CLIENT_KEY_PATH", "/tmp/key.pem")

    with patch(
        "souschef.core.chef_server.get_chef_nodes",
        side_effect=RuntimeError("boom"),
    ):
        result = runner.invoke(cli, ["query-chef-nodes"])

    assert result.exit_code != 0
    assert "Error querying Chef Server" in result.output
