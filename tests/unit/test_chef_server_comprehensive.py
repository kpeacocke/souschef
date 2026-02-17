"""Comprehensive tests for Chef Server utilities."""

from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from souschef.core.chef_server import (
    _handle_chef_server_response,
    _validate_chef_server_connection,
)


def _get_test_key_pem() -> str:
    """Generate a valid test RSA key in PEM format."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


class TestHandleChefServerResponse:
    """Tests for _handle_chef_server_response function."""

    def test_handle_response_success_200(self):
        """Test handling successful 200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        server_url = "https://chef.example.com"

        success, message = _handle_chef_server_response(mock_response, server_url)

        assert success is True
        assert "Successfully connected" in message
        assert server_url in message

    def test_handle_response_unauthorized_401(self):
        """Test handling 401 unauthorized response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        server_url = "https://chef.example.com"

        success, message = _handle_chef_server_response(mock_response, server_url)

        assert success is False
        assert "Authentication failed" in message
        assert "credentials" in message

    def test_handle_response_not_found_404(self):
        """Test handling 404 not found response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        server_url = "https://chef.example.com"

        success, message = _handle_chef_server_response(mock_response, server_url)

        assert success is False
        assert "not found" in message

    def test_handle_response_server_error_500(self):
        """Test handling 500 server error response."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        server_url = "https://chef.example.com"

        success, message = _handle_chef_server_response(mock_response, server_url)

        assert success is False
        assert "Connection failed" in message
        assert "500" in message

    def test_handle_response_forbidden_403(self):
        """Test handling 403 forbidden response."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        server_url = "https://chef.example.com"

        success, message = _handle_chef_server_response(mock_response, server_url)

        assert success is False
        assert "Authorisation failed" in message


class TestValidateChefServerConnectionEdgeCases:
    """Tests for additional edge cases in _validate_chef_server_connection."""

    def test_validate_empty_server_url(self):
        """Test validation with empty server URL."""
        success, message = _validate_chef_server_connection("", "my-node")

        assert success is False
        assert "Server URL is required" in message

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_generic_exception(self, mock_requests):
        """Test handling of generic exception."""
        mock_requests.request.side_effect = RuntimeError("Unexpected error")

        success, message = _validate_chef_server_connection(
            "https://chef.example.com",
            "my-node",
            client_key=_get_test_key_pem(),
        )

        assert success is False
        assert "Unexpected error" in message

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_strips_trailing_slash(self, mock_requests):
        """Test that trailing slashes are removed from server URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.request.return_value = mock_response

        _validate_chef_server_connection(
            "https://chef.example.com/",
            "my-node",
            client_key=_get_test_key_pem(),
        )

        # Verify URL was stripped (should not have trailing slash)
        call_url = mock_requests.request.call_args.kwargs["url"]
        assert not call_url.endswith("//search")

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_with_query_params(self, mock_requests):
        """Test that search query is passed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.request.return_value = mock_response

        _validate_chef_server_connection(
            "https://chef.example.com",
            "my-node",
            client_key=_get_test_key_pem(),
        )

        # Verify query params are in URL
        call_url = mock_requests.request.call_args.kwargs["url"]
        assert "q=%2A%3A%2A" in call_url or "q=*:*" in call_url

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_with_timeout(self, mock_requests):
        """Test that timeout is set correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.request.return_value = mock_response

        _validate_chef_server_connection(
            "https://chef.example.com",
            "my-node",
            client_key=_get_test_key_pem(),
        )

        # Verify timeout (default is 10)
        call_timeout = mock_requests.request.call_args.kwargs["timeout"]
        assert call_timeout == 10

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_with_headers(self, mock_requests):
        """Test that correct headers are sent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.request.return_value = mock_response

        _validate_chef_server_connection(
            "https://chef.example.com",
            "my-node",
            client_key=_get_test_key_pem(),
        )

        # Verify headers
        call_headers = mock_requests.request.call_args.kwargs["headers"]
        assert "Accept" in call_headers
        assert "application/json" in call_headers["Accept"]
