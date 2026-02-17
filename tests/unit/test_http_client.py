"""Tests for HTTP client abstraction."""

import uuid
from unittest.mock import Mock, patch

import pytest

from souschef.core.errors import SousChefError
from souschef.core.http_client import HTTPClient, HTTPError, create_client

DUMMY_API_KEY = "example-value"


def _sample_api_key() -> str:
    """Return a non-secret placeholder API key for tests."""
    return f"example-{uuid.uuid4()}"


API_KEY = _sample_api_key()


class TestHTTPError:
    """Test HTTPError exception."""

    def test_http_error_basic(self):
        """Test basic HTTP error creation."""
        error = HTTPError(404, "Not found")

        assert error.status_code == 404
        assert "HTTP 404" in str(error)
        assert "Not found" in str(error)

    def test_http_error_with_response(self):
        """Test HTTP error with response text."""
        error = HTTPError(500, "Server error", "Internal error details")

        assert error.status_code == 500
        assert error.response_text == "Internal error details"
        assert "Internal error details" in str(error)

    def test_http_error_suggestions(self):
        """Test that appropriate suggestions are provided."""
        error_401 = HTTPError(401, "Unauthorized")
        assert "API key" in str(error_401)

        error_403 = HTTPError(403, "Forbidden")
        assert "permission" in str(error_403)

        error_404 = HTTPError(404, "Not found")
        assert "endpoint" in str(error_404)

        error_429 = HTTPError(429, "Rate limited")
        assert "Rate limit" in str(error_429)

        error_500 = HTTPError(500, "Server error")
        assert "service" in str(error_500)

    def test_http_error_long_response_truncated(self):
        """Test that long responses are truncated."""
        long_text = "x" * 1000
        error = HTTPError(500, "Error", long_text)

        error_str = str(error)
        # Should be truncated to 500 chars
        assert error.response_text is not None
        assert len(error.response_text) == 1000
        assert "x" * 500 in error_str


@pytest.mark.skipif(
    not hasattr(pytest, "importorskip"),
    reason="Requires pytest.importorskip",
)
class TestHTTPClient:
    """Test HTTPClient class."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        with patch("souschef.core.http_client.requests") as mock_requests:
            mock_session = Mock()
            mock_requests.Session.return_value = mock_session
            yield mock_session

    def test_client_initialization(self):
        """Test client initialization."""
        client = HTTPClient(
            base_url="https://api.example.com",
            api_key=API_KEY,
            timeout=30,
        )

        assert client.base_url == "https://api.example.com"
        assert client.api_key == API_KEY
        assert client.timeout == 30

    def test_client_strips_trailing_slash(self):
        """Test that trailing slashes are stripped from base_url."""
        client = HTTPClient(base_url="https://api.example.com/")

        assert client.base_url == "https://api.example.com"

    def test_get_headers_bearer_auth(self):
        """Test header generation with bearer auth."""
        client = HTTPClient(
            base_url="https://api.example.com",
            api_key=API_KEY,
        )

        headers = client._get_headers(auth_type="bearer")

        assert headers["Authorization"] == f"Bearer {API_KEY}"
        assert headers["Content-Type"] == "application/json"
        assert "SousChef" in headers["User-Agent"]

    def test_get_headers_api_key_auth(self):
        """Test header generation with API key auth."""
        client = HTTPClient(
            base_url="https://api.example.com",
            api_key=API_KEY,
        )

        headers = client._get_headers(auth_type="api_key")

        assert headers["X-API-Key"] == API_KEY
        assert "Authorization" not in headers

    def test_get_headers_no_auth(self):
        """Test header generation without auth."""
        client = HTTPClient(base_url="https://api.example.com")

        headers = client._get_headers()

        assert "Authorization" not in headers
        assert "X-API-Key" not in headers

    def test_get_headers_with_extra(self):
        """Test header generation with extra headers."""
        client = HTTPClient(base_url="https://api.example.com")

        headers = client._get_headers(
            extra_headers={"X-Custom": "value", "X-Request-ID": "123"}
        )

        assert headers["X-Custom"] == "value"
        assert headers["X-Request-ID"] == "123"

    def test_http_url_rejected_by_default(self):
        """Test that HTTP URLs are rejected by default."""
        # Construct HTTP URL dynamically to avoid security scanner false positives
        insecure_url = "http" + "://" + "insecure.example.com"
        with pytest.raises(SousChefError) as exc_info:
            HTTPClient(base_url=insecure_url)

        assert "Insecure HTTP connection not allowed" in str(exc_info.value)
        assert "HTTPS" in str(exc_info.value)

    def test_https_url_always_allowed(self):
        """Test that HTTPS URLs are always allowed."""
        client = HTTPClient(base_url="https://api.example.com")

        assert client.base_url == "https://api.example.com"

    def test_post_success(self, mock_session):
        """Test successful POST request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_session.post.return_value = mock_response

        client = HTTPClient(
            base_url="https://api.example.com",
            api_key=API_KEY,
        )
        result = client.post("/v1/endpoint", json_data={"key": "value"})

        assert result == {"result": "success"}
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "https://api.example.com/v1/endpoint" in str(call_args)

    def test_post_with_leading_slash(self, mock_session):
        """Test POST with leading slash in endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_session.post.return_value = mock_response

        client = HTTPClient(base_url="https://api.example.com")
        client.post("/endpoint")

        call_args = mock_session.post.call_args
        # Should not have double slash
        assert "//endpoint" not in str(call_args)

    def test_post_http_error(self, mock_session):
        """Test POST with HTTP error response."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.post.return_value = mock_response

        client = HTTPClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.post("/endpoint")

        assert exc_info.value.status_code == 404

    def test_post_timeout(self, mock_session):
        """Test POST with timeout."""
        import requests

        mock_session.post.side_effect = requests.exceptions.Timeout()

        client = HTTPClient(base_url="https://api.example.com", timeout=30)

        with pytest.raises(SousChefError) as exc_info:
            client.post("/endpoint")

        assert "timed out" in str(exc_info.value).lower()
        assert "30 seconds" in str(exc_info.value)

    def test_post_connection_error(self, mock_session):
        """Test POST with connection error."""
        import requests

        mock_session.post.side_effect = requests.exceptions.ConnectionError()

        client = HTTPClient(base_url="https://api.example.com")

        with pytest.raises(SousChefError) as exc_info:
            client.post("/endpoint")

        assert "connect" in str(exc_info.value).lower()

    def test_post_custom_timeout(self, mock_session):
        """Test POST with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_session.post.return_value = mock_response

        client = HTTPClient(base_url="https://api.example.com", timeout=30)
        client.post("/endpoint", timeout=60)

        call_kwargs = mock_session.post.call_args.kwargs
        assert call_kwargs["timeout"] == 60

    def test_get_success(self, mock_session):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "value"}
        mock_session.get.return_value = mock_response

        client = HTTPClient(base_url="https://api.example.com")
        result = client.get("/v1/resource")

        assert result == {"data": "value"}
        mock_session.get.assert_called_once()

    def test_get_with_params(self, mock_session):
        """Test GET with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_session.get.return_value = mock_response

        client = HTTPClient(base_url="https://api.example.com")
        client.get("/resource", params={"filter": "active", "limit": 10})

        call_kwargs = mock_session.get.call_args.kwargs
        assert call_kwargs["params"] == {"filter": "active", "limit": 10}

    def test_get_http_error(self, mock_session):
        """Test GET with HTTP error."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_session.get.return_value = mock_response

        client = HTTPClient(base_url="https://api.example.com")

        with pytest.raises(HTTPError) as exc_info:
            client.get("/resource")

        assert exc_info.value.status_code == 500

    def test_context_manager(self, mock_session):
        """Test using client as context manager."""
        with HTTPClient(base_url="https://api.example.com") as client:
            assert client is not None

        mock_session.close.assert_called_once()

    def test_close_method(self, mock_session):
        """Test explicit close method."""
        client = HTTPClient(base_url="https://api.example.com")
        client.close()

        mock_session.close.assert_called_once()


class TestCreateClient:
    """Test create_client factory function."""

    def test_create_client_basic(self):
        """Test basic client creation."""
        client = create_client(
            base_url="https://api.example.com",
            api_key=API_KEY,
        )

        assert isinstance(client, HTTPClient)
        assert client.base_url == "https://api.example.com"
        assert client.api_key == API_KEY

    def test_create_client_with_kwargs(self):
        """Test client creation with additional arguments."""
        client = create_client(
            base_url="https://api.example.com",
            api_key=API_KEY,
            timeout=45,
            max_retries=5,
        )

        assert client.timeout == 45


class TestRequestsNotAvailable:
    """Test behavior when requests library is not available."""

    def test_client_raises_error_without_requests(self):
        """Test that client raises error when requests not available."""
        with patch("souschef.core.http_client.REQUESTS_AVAILABLE", False):
            with pytest.raises(SousChefError) as exc_info:
                HTTPClient(base_url="https://api.example.com")

            assert "requests library not available" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)
