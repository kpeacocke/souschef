"""
Tests for uncovered lines in converter and chef_server modules.

Covers exception handlers, edge cases, and rarely-exercised code paths
in habitat, template, and chef_server modules.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# souschef/converters/habitat.py – uncovered lines 48-49, 95-96, 109-110,
#   147, 171-172, 193, 248, 306, 478, 713
# ---------------------------------------------------------------------------


class TestHabitatConverter:
    """Tests for Habitat-to-Docker converter edge cases."""

    def test_convert_habitat_to_dockerfile_invalid_path_traversal(self) -> None:
        """convert_habitat_to_dockerfile returns error for path traversal attempt."""
        from souschef.converters.habitat import convert_habitat_to_dockerfile

        with patch(
            "souschef.converters.habitat._normalize_path",
            side_effect=ValueError("path traversal"),
        ):
            result = convert_habitat_to_dockerfile("/fake/../evil/plan.sh")
        assert "Invalid path" in result

    def test_generate_compose_from_habitat_invalid_path_traversal(self) -> None:
        """generate_compose_from_habitat returns error for path traversal."""
        from souschef.converters.habitat import generate_compose_from_habitat

        with patch(
            "souschef.converters.habitat._normalize_path",
            side_effect=ValueError("path traversal"),
        ):
            result = generate_compose_from_habitat("../evil/plan.sh")
        assert "Invalid path" in result

    def test_generate_compose_from_habitat_exception_in_format(self) -> None:
        """generate_compose_from_habitat returns error when format raises Exception."""
        from souschef.converters.habitat import generate_compose_from_habitat

        valid_json = (
            '{"package": {"name": "myapp"}, "ports": [], "binds": [], '
            '"dependencies": {"runtime": []}}'
        )

        with (
            patch("souschef.converters.habitat.parse_habitat_plan", return_value=valid_json),
            patch(
                "souschef.converters.habitat._format_compose_yaml",
                side_effect=Exception("yaml error"),
            ),
        ):
            result = generate_compose_from_habitat("plan.sh")
        assert "Error" in result

    def test_map_habitat_deps_skips_blank_entries(self) -> None:
        """_map_habitat_deps_to_apt skips empty and whitespace-only entries."""
        from souschef.converters.habitat import _map_habitat_deps_to_apt

        result = _map_habitat_deps_to_apt(["", "  ", "core/gcc"])
        assert "gcc" in result
        assert "" not in result

    def test_map_habitat_deps_dep_without_slash_added_directly(self) -> None:
        """_map_habitat_deps_to_apt adds valid deps without slash as apt packages."""
        from souschef.converters.habitat import _map_habitat_deps_to_apt

        result = _map_habitat_deps_to_apt(["openssl"])
        assert "openssl" in result

    def test_extract_default_port_keyword_substring(self) -> None:
        """_extract_default_port returns '80' for port name containing 'http'."""
        from souschef.converters.habitat import _extract_default_port

        assert _extract_default_port("app-http-port") == "80"

    def test_validate_docker_network_name_dangerous_chars(self) -> None:
        """_validate_docker_network_name returns False for dangerous characters."""
        from souschef.converters.habitat import _validate_docker_network_name

        assert _validate_docker_network_name("bad;net") is False
        assert _validate_docker_network_name("net:name") is False

    def test_validate_docker_image_name_dangerous_chars(self) -> None:
        """_validate_docker_image_name returns False for dangerous characters."""
        from souschef.converters.habitat import _validate_docker_image_name

        assert _validate_docker_image_name("ubuntu;rm -rf /") is False

    def test_process_callback_lines_skips_blank_and_comment_lines(self) -> None:
        """_process_callback_lines skips blank lines and comment-only lines."""
        from souschef.converters.habitat import _process_callback_lines

        content = "\n# This is a comment\n\necho hello\n"
        result = _process_callback_lines(content, replace_vars=False)
        run_commands = [line for line in result if not line.startswith("#")]
        assert any("echo hello" in cmd for cmd in run_commands)

    def test_format_compose_yaml_raises_for_invalid_network_name(self) -> None:
        """_format_compose_yaml raises ValueError for an invalid network name."""
        from souschef.converters.habitat import _format_compose_yaml

        with pytest.raises(ValueError, match="Invalid Docker network name"):
            _format_compose_yaml({}, "bad;network!")


# ---------------------------------------------------------------------------
# souschef/converters/template.py – uncovered lines 49-50, 73-74, 132, 141-142
# ---------------------------------------------------------------------------


class TestTemplateConverter:
    """Tests for ERB template converter edge cases."""

    def test_convert_template_file_unicode_decode_error(self, tmp_path: Path) -> None:
        """convert_template_file returns failure dict for UnicodeDecodeError."""
        from souschef.converters.template import convert_template_file

        erb_file = tmp_path / "test.erb"
        erb_file.write_bytes(b"\xff\xfe invalid utf8")

        result = convert_template_file(str(erb_file))
        assert result["success"] is False
        assert "UTF-8" in result.get("error", "")

    def test_convert_template_file_generic_exception(self, tmp_path: Path) -> None:
        """convert_template_file returns failure dict for unexpected exceptions."""
        from souschef.converters.template import convert_template_file

        erb_file = tmp_path / "test.erb"
        erb_file.write_text("<% @name %>")

        with patch(
            "souschef.converters.template._extract_template_variables",
            side_effect=RuntimeError("unexpected error"),
        ):
            result = convert_template_file(str(erb_file))
        assert result["success"] is False
        assert "Conversion failed" in result.get("error", "")

    def test_convert_cookbook_templates_counts_failed_templates(
        self, tmp_path: Path
    ) -> None:
        """convert_cookbook_templates increments templates_failed for failed conversions."""
        from souschef.converters.template import convert_cookbook_templates

        tmpl_dir = tmp_path / "templates" / "default"
        tmpl_dir.mkdir(parents=True)
        erb_file = tmpl_dir / "config.erb"
        # Write invalid UTF-8 bytes so the file conversion fails
        erb_file.write_bytes(b"\xff\xfe invalid utf8")

        result = convert_cookbook_templates(str(tmp_path))
        assert result["templates_failed"] >= 1

    def test_convert_cookbook_templates_generic_exception(
        self, tmp_path: Path
    ) -> None:
        """convert_cookbook_templates returns failure dict when glob raises exception."""
        from souschef.converters.template import convert_cookbook_templates

        with patch.object(Path, "glob", side_effect=RuntimeError("glob failed")):
            result = convert_cookbook_templates(str(tmp_path))
        assert result["success"] is False
        assert "Failed to convert" in result.get("error", "")


# ---------------------------------------------------------------------------
# souschef/core/chef_server.py – uncovered lines 193, 220, 248-249, 546, 561,
#   602-605, 618-621, 635-640, 662-663, 782, 830, 920-927, 951-958,
#   986-993, 1017-1024
# ---------------------------------------------------------------------------


class TestChefServer:
    """Tests for Chef server client edge cases."""

    def _make_client_with_base_url(self, base_url: str = "https://chef.example.com"):
        """Create a mock ChefServerClient with _base_url set correctly."""
        from souschef.core.chef_server import ChefServerClient, ChefServerConfig

        config = ChefServerConfig(
            server_url=base_url,
            organisation="myorg",
            client_name="admin",
            client_key="",
        )
        client = ChefServerClient.__new__(ChefServerClient)
        client._config = config
        client._timeout = 10
        return client

    def test_normalise_server_url_preserves_existing_path(self) -> None:
        """_normalise_server_url adds org path when URL has an existing path."""
        from souschef.core.chef_server import _normalise_server_url

        result = _normalise_server_url("https://chef.example.com/custom-path", "myorg")
        assert "myorg" in result

    def test_load_private_key_non_rsa_key_raises_value_error(self) -> None:
        """_load_private_key raises ValueError for invalid PEM content."""
        from souschef.core.chef_server import _load_private_key

        not_valid_pem = "this is not a pem at all"
        with pytest.raises(ValueError):
            _load_private_key(not_valid_pem)

    def test_sign_request_key_sign_failure_raises_value_error(self) -> None:
        """_sign_request raises ValueError when key.sign raises an exception."""
        from souschef.core.chef_server import _sign_request

        # Use a well-formed but throwaway RSA key to hit the signing failure branch
        # We'll mock _load_private_key to return a key whose sign() raises
        mock_key = MagicMock()
        mock_key.sign.side_effect = Exception("signing error")

        with (
            patch("souschef.core.chef_server._load_private_key", return_value=mock_key),
            pytest.raises(ValueError, match="Failed to sign"),
        ):
            _sign_request("GET\n/api\n", "fake_key_pem")

    def test_extract_version_strings_versions_not_a_list(self) -> None:
        """_extract_version_strings returns [] when versions field is not a list."""
        from souschef.core.chef_server import ChefServerClient

        client = ChefServerClient.__new__(ChefServerClient)
        result = client._extract_version_strings({"name": "myapp", "versions": "bad"})
        assert result == []

    def test_get_node_non_dict_json_returns_empty(self) -> None:
        """get_node returns {} when response JSON is not a dict."""
        from souschef.core.chef_server import ChefServerClient, ChefServerConfig

        config = ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="myorg",
            client_name="admin",
            client_key="",
        )
        client = ChefServerClient.__new__(ChefServerClient)
        client._config = config
        client._timeout = 10

        mock_response = MagicMock()
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_response.raise_for_status.return_value = None

        with patch.object(client, "_request", return_value=mock_response):
            result = client.get_node("mynode")
        assert result == {}

    def test_get_policy_non_dict_json_returns_empty(self) -> None:
        """get_policy returns {} when response JSON is not a dict."""
        from souschef.core.chef_server import ChefServerClient, ChefServerConfig

        config = ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="myorg",
            client_name="admin",
            client_key="",
        )
        client = ChefServerClient.__new__(ChefServerClient)
        client._config = config
        client._timeout = 10

        mock_response = MagicMock()
        mock_response.json.return_value = [1, 2, 3]
        mock_response.raise_for_status.return_value = None

        with patch.object(client, "_request", return_value=mock_response):
            result = client.get_policy("mypolicy")
        assert result == {}

    def test_get_policy_revision_non_dict_json_returns_empty(self) -> None:
        """get_policy_revision returns {} when response JSON is not a dict."""
        from souschef.core.chef_server import ChefServerClient, ChefServerConfig

        config = ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="myorg",
            client_name="admin",
            client_key="",
        )
        client = ChefServerClient.__new__(ChefServerClient)
        client._config = config
        client._timeout = 10

        mock_response = MagicMock()
        mock_response.json.return_value = "not a dict"
        mock_response.raise_for_status.return_value = None

        with patch.object(client, "_request", return_value=mock_response):
            result = client.get_policy_revision("mypolicy", "abc123")
        assert result == {}

    def test_download_url_plain_endpoint(self) -> None:
        """download_url uses the plain endpoint (no ://) directly as the request path."""
        from souschef.core.chef_server import ChefServerClient, ChefServerConfig

        config = ChefServerConfig(
            server_url="https://chef.example.com",
            organisation="myorg",
            client_name="admin",
            client_key="",
        )
        client = ChefServerClient.__new__(ChefServerClient)
        client._config = config
        client._timeout = 10

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b"file bytes"

        with patch.object(client, "_request", return_value=mock_response):
            result = client.download_url("cookbooks/myapp/1.0.0/download")
        assert result == b"file bytes"

    def test_build_chef_server_client_returns_instance(self) -> None:
        """build_chef_server_client delegates to _build_client_from_env."""
        from souschef.core.chef_server import build_chef_server_client

        mock_client = MagicMock()
        with patch(
            "souschef.core.chef_server._build_client_from_env",
            return_value=mock_client,
        ) as mock_build:
            result = build_chef_server_client(
                server_url="https://chef.example.com",
                organisation="myorg",
                client_name="admin",
            )
        mock_build.assert_called_once()
        assert result is mock_client

    def test_validate_chef_server_connection_timeout(self) -> None:
        """_validate_chef_server_connection returns failure on Timeout."""
        from souschef.core.chef_server import Timeout, _validate_chef_server_connection

        with patch(
            "souschef.core.chef_server._build_client_from_env",
            side_effect=Timeout("timed out"),
        ):
            ok, msg = _validate_chef_server_connection(
                "https://chef.example.com",
                "admin",
            )
        assert ok is False
        assert "timeout" in msg.lower() or "Connection" in msg

    def test_list_chef_environments_wrapper(self) -> None:
        """list_chef_environments delegates to _build_client_from_env."""
        from souschef.core.chef_server import list_chef_environments

        mock_client = MagicMock()
        mock_client.list_environments.return_value = [{"name": "production"}]

        with patch(
            "souschef.core.chef_server._build_client_from_env",
            return_value=mock_client,
        ):
            result = list_chef_environments()
        assert isinstance(result, list)

    def test_list_chef_cookbooks_wrapper(self) -> None:
        """list_chef_cookbooks delegates to _build_client_from_env."""
        from souschef.core.chef_server import list_chef_cookbooks

        mock_client = MagicMock()
        mock_client.list_cookbooks.return_value = [{"name": "myapp"}]

        with patch(
            "souschef.core.chef_server._build_client_from_env",
            return_value=mock_client,
        ):
            result = list_chef_cookbooks()
        assert isinstance(result, list)

    def test_get_chef_cookbook_version_wrapper(self) -> None:
        """get_chef_cookbook_version delegates to _build_client_from_env."""
        from souschef.core.chef_server import get_chef_cookbook_version

        mock_client = MagicMock()
        mock_client.get_cookbook_version.return_value = {"name": "myapp", "version": "1.0.0"}

        with patch(
            "souschef.core.chef_server._build_client_from_env",
            return_value=mock_client,
        ):
            result = get_chef_cookbook_version("myapp", "1.0.0")
        assert isinstance(result, dict)
        assert result["name"] == "myapp"

    def test_list_chef_policies_wrapper(self) -> None:
        """list_chef_policies delegates to _build_client_from_env."""
        from souschef.core.chef_server import list_chef_policies

        mock_client = MagicMock()
        mock_client.list_policies.return_value = [{"name": "mypolicy"}]

        with patch(
            "souschef.core.chef_server._build_client_from_env",
            return_value=mock_client,
        ):
            result = list_chef_policies()
        assert isinstance(result, list)

