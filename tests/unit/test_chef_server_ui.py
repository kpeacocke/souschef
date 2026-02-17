"""Tests for Chef Server settings UI page."""

from unittest.mock import MagicMock, patch

from souschef.core.chef_server import _validate_chef_server_connection
from souschef.ui.pages.chef_server_settings import (
    show_chef_server_settings_page,
)


class TestChefServerValidation:
    """Test Chef Server connection validation."""

    def test_validate_connection_success(self):
        """Test successful Chef Server validation."""
        mock_client = MagicMock()
        mock_client.test_connection.return_value = (True, "Connection ok")

        with patch("souschef.core.chef_server._build_client_from_env") as mock_build:
            mock_build.return_value = mock_client

            success, message = _validate_chef_server_connection(
                "https://chef.example.com",
                "my-client",
                organisation="default",
                client_key_path="/tmp/client.pem",  # NOSONAR - S2083: test fixture
            )

        assert success is True
        assert "Connection ok" in message

    def test_validate_connection_auth_failure(self):
        """Test authentication failure."""
        mock_client = MagicMock()
        mock_client.test_connection.return_value = (
            False,
            "Authentication failed - check your Chef Server credentials",
        )

        with patch("souschef.core.chef_server._build_client_from_env") as mock_build:
            mock_build.return_value = mock_client

            success, message = _validate_chef_server_connection(
                "https://chef.example.com",
                "my-client",
                organisation="default",
                client_key_path="/tmp/client.pem",  # NOSONAR - S2083: test fixture
            )

        assert success is False
        assert "Authentication failed" in message

    def test_validate_connection_timeout(self):
        """Test connection timeout."""
        from requests.exceptions import Timeout

        mock_client = MagicMock()
        mock_client.test_connection.side_effect = Timeout()

        with patch("souschef.core.chef_server._build_client_from_env") as mock_build:
            mock_build.return_value = mock_client

            success, message = _validate_chef_server_connection(
                "https://chef.example.com",
                "my-client",
                organisation="default",
                client_key_path="/tmp/client.pem",  # NOSONAR - S2083: test fixture
            )

        assert success is False
        assert "timeout" in message.lower()

    def test_validate_invalid_url(self):
        """Test validation with invalid URL."""
        with patch("souschef.core.chef_server._build_client_from_env") as mock_build:
            mock_build.side_effect = ValueError("Invalid server URL: bad")

            success, message = _validate_chef_server_connection(
                "invalid-url",
                "my-client",
                organisation="default",
                client_key_path="/tmp/client.pem",  # NOSONAR - S2083: test fixture
            )

        assert success is False
        assert "Invalid server URL" in message

    def test_validate_missing_client_name(self):
        """Test validation with missing client name."""
        with patch("souschef.core.chef_server._build_client_from_env") as mock_build:
            mock_build.side_effect = ValueError("Client name is required")

            success, message = _validate_chef_server_connection(
                "https://chef.example.com",
                "",
                organisation="default",
                client_key_path="/tmp/client.pem",  # NOSONAR - S2083: test fixture
            )

        assert success is False
        assert "Client name is required" in message

    def test_validate_requests_not_available(self):
        """Test validation when requests library not available."""
        with patch("souschef.core.chef_server.requests_module", None):
            success, message = _validate_chef_server_connection(
                "https://chef.example.com",
                "my-client",
                organisation="default",
                client_key_path="/tmp/client.pem",  # NOSONAR - S2083: test fixture
            )

            assert success is False
            assert "requests library not installed" in message


class TestChefServerUIPage:
    """Test Chef Server settings UI page."""

    @patch("souschef.ui.pages.chef_server_settings.st")
    def test_page_renders_without_errors(self, mock_st):
        """Test that the page renders without errors."""
        # Mock Streamlit components
        mock_st.title = MagicMock()
        mock_st.markdown = MagicMock()
        mock_st.info = MagicMock()
        mock_st.subheader = MagicMock()
        mock_st.columns = MagicMock(return_value=(MagicMock(), MagicMock()))
        mock_st.text_input = MagicMock(return_value="")
        mock_st.button = MagicMock(return_value=False)
        mock_st.expander = MagicMock(
            return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
        )
        mock_st.session_state = MagicMock()
        mock_st.session_state.get = MagicMock(return_value="Not configured")

        # Call the page function
        show_chef_server_settings_page()

        # Verify key components were rendered
        mock_st.title.assert_called_once()
        assert mock_st.markdown.call_count >= 2
        mock_st.info.assert_called_once()
