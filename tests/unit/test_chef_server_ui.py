"""Tests for Chef Server settings UI page."""

from unittest.mock import MagicMock, patch

from souschef.core.chef_server import _validate_chef_server_connection
from souschef.ui.pages.chef_server_settings import (
    show_chef_server_settings_page,
)


class TestChefServerValidation:
    """Test Chef Server connection validation."""

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_success(self, mock_requests):
        """Test successful Chef Server validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response

        success, message = _validate_chef_server_connection(
            "https://chef.example.com", "my-node"
        )

        assert success is True
        assert "Successfully connected" in message

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_auth_failure(self, mock_requests):
        """Test authentication failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_requests.get.return_value = mock_response

        success, message = _validate_chef_server_connection(
            "https://chef.example.com", "my-node"
        )

        assert success is False
        assert "Authentication failed" in message

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_not_found(self, mock_requests):
        """Test endpoint not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        success, message = _validate_chef_server_connection(
            "https://chef.example.com", "my-node"
        )

        assert success is False
        assert "not found" in message

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_timeout(self, mock_requests):
        """Test connection timeout."""
        from requests.exceptions import Timeout

        mock_requests.get.side_effect = Timeout()

        success, message = _validate_chef_server_connection(
            "https://chef.example.com", "my-node"
        )

        assert success is False
        assert "timeout" in message.lower()

    @patch("souschef.core.chef_server.requests_module")
    def test_validate_connection_error(self, mock_requests):
        """Test connection error."""
        from requests.exceptions import ConnectionError as RequestsConnectionError

        mock_requests.get.side_effect = RequestsConnectionError()

        success, message = _validate_chef_server_connection(
            "https://chef.example.com", "my-node"
        )

        assert success is False
        assert "not reachable" in message

    def test_validate_invalid_url(self):
        """Test validation with invalid URL."""
        success, message = _validate_chef_server_connection("invalid-url", "my-node")

        assert success is False
        assert "Invalid server URL" in message

    def test_validate_missing_node_name(self):
        """Test validation with missing node name."""
        success, message = _validate_chef_server_connection(
            "https://chef.example.com", ""
        )

        assert success is False
        assert "Node name is required" in message

    def test_validate_requests_not_available(self):
        """Test validation when requests library not available."""
        with patch("souschef.core.chef_server.requests_module", None):
            success, message = _validate_chef_server_connection(
                "https://chef.example.com", "my-node"
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
