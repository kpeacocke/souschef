"""
HTTP client abstraction for SousChef.

Provides a unified interface for making HTTP requests with consistent
error handling, authentication, and retry logic.
"""

# mypy: disable-error-code="import-untyped,misc,assignment"

from typing import Any, Literal

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.exceptions import (
        ConnectionError as RequestsConnectionError,
    )
    from requests.exceptions import (
        HTTPError as RequestsHTTPError,
    )
    from requests.exceptions import (
        RequestException,
    )
    from requests.exceptions import (
        Timeout as RequestsTimeout,
    )
    from urllib3.util.retry import Retry

    REQUESTS_AVAILABLE = True
except ImportError:  # pragma: no cover
    requests = None
    HTTPAdapter = None
    Retry = None
    RequestsHTTPError = Exception
    RequestsTimeout = Exception
    RequestsConnectionError = Exception
    RequestException = Exception
    REQUESTS_AVAILABLE = False

from souschef.core.errors import SousChefError


class HTTPError(SousChefError):
    """Raised when an HTTP request fails."""

    def __init__(
        self,
        status_code: int,
        message: str,
        response_text: str | None = None,
    ):
        """
        Initialise HTTP error.

        Args:
            status_code: HTTP status code.
            message: Error message.
            response_text: Optional response body text.

        """
        self.status_code = status_code
        self.response_text = response_text

        full_message = f"HTTP {status_code}: {message}"
        if response_text:
            full_message += f"\nResponse: {response_text[:500]}"

        suggestion = self._get_suggestion(status_code)
        super().__init__(full_message, suggestion)

    @staticmethod
    def _get_suggestion(status_code: int) -> str:
        """Get helpful suggestion based on status code."""
        if status_code == 401:
            return "Check that your API key is valid and properly configured."
        elif status_code == 403:
            return (
                "Your API key doesn't have permission for this operation. "
                "Verify the key has the required scopes."
            )
        elif status_code == 404:
            return "The requested API endpoint was not found. Check the base URL."
        elif status_code == 429:
            return "Rate limit exceeded. Wait a moment and try again."
        elif 500 <= status_code < 600:
            return "The API service is experiencing issues. Try again later."
        else:
            return "Check the API documentation for this error code."


class HTTPClient:
    """
    HTTP client with authentication and error handling.

    Provides a simple interface for making authenticated HTTP requests
    with automatic retries and consistent error handling.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 60,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        user_agent: str = "SousChef/1.0",
    ):
        """
        Initialise HTTP client.

        Args:
            base_url: Base URL for API requests.
            api_key: Optional API key for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            backoff_factor: Exponential backoff multiplier for retries.
            user_agent: User-Agent header value.

        """
        if not REQUESTS_AVAILABLE:
            raise SousChefError(
                "requests library not available",
                "Install with: pip install requests",
            )

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.user_agent = user_agent

        # Create session with retry configuration
        self.session = requests.Session()

        # Configure retries for transient errors
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _get_headers(
        self,
        auth_type: Literal["bearer", "api_key"] = "bearer",
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """
        Build request headers with authentication.

        Args:
            auth_type: Authentication type ("bearer" or "api_key").
            extra_headers: Additional headers to include.

        Returns:
            Complete headers dictionary.

        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }

        if self.api_key:
            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.api_key}"
            elif auth_type == "api_key":
                headers["X-API-Key"] = self.api_key

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        auth_type: Literal["bearer", "api_key"] = "bearer",
        extra_headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint (relative to base_url).
            json_data: JSON request body.
            auth_type: Authentication type.
            extra_headers: Additional headers.
            timeout: Request timeout (overrides default).

        Returns:
            JSON response data.

        Raises:
            HTTPError: If request fails.

        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(auth_type, extra_headers)
        timeout_value = timeout if timeout is not None else self.timeout

        response = None
        try:
            response = self.session.post(
                url,
                json=json_data,
                headers=headers,
                timeout=timeout_value,
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except RequestsHTTPError as e:
            if response is not None:
                raise HTTPError(
                    response.status_code,
                    str(e),
                    response.text,
                ) from e
            else:
                raise SousChefError(
                    f"HTTP request failed: {e}",
                    "Check the API endpoint and your network connection.",
                ) from e
        except RequestsTimeout as e:
            raise SousChefError(
                f"Request timed out after {timeout_value} seconds",
                "The API service may be slow or unresponsive. Try increasing "
                "the timeout value or try again later.",
            ) from e
        except RequestsConnectionError as e:
            raise SousChefError(
                f"Failed to connect to {url}",
                "Check your network connection and verify the base URL is correct.",
            ) from e
        except RequestException as e:
            raise SousChefError(
                f"Request failed: {e}",
                "Check the API documentation and your request parameters.",
            ) from e

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        auth_type: Literal["bearer", "api_key"] = "bearer",
        extra_headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint (relative to base_url).
            params: Query parameters.
            auth_type: Authentication type.
            extra_headers: Additional headers.
            timeout: Request timeout (overrides default).

        Returns:
            JSON response data.

        Raises:
            HTTPError: If request fails.

        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(auth_type, extra_headers)
        timeout_value = timeout if timeout is not None else self.timeout

        response = None
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout_value,
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except RequestsHTTPError as e:
            if response is not None:
                raise HTTPError(
                    response.status_code,
                    str(e),
                    response.text,
                ) from e
            else:
                raise SousChefError(
                    f"HTTP request failed: {e}",
                    "Check the API endpoint and your network connection.",
                ) from e
        except RequestsTimeout as e:
            raise SousChefError(
                f"Request timed out after {timeout_value} seconds",
                "The API service may be slow or unresponsive. Try increasing "
                "the timeout value or try again later.",
            ) from e
        except RequestsConnectionError as e:
            raise SousChefError(
                f"Failed to connect to {url}",
                "Check your network connection and verify the base URL is correct.",
            ) from e
        except RequestException as e:
            raise SousChefError(
                f"Request failed: {e}",
                "Check the API documentation and your request parameters.",
            ) from e

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "HTTPClient":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and close session."""
        self.close()


def create_client(
    base_url: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> HTTPClient:
    """
    Create an HTTP client with default settings.

    Args:
        base_url: Base URL for API requests.
        api_key: Optional API key for authentication.
        **kwargs: Additional HTTPClient arguments.

    Returns:
        Configured HTTP client.

    """
    return HTTPClient(base_url=base_url, api_key=api_key, **kwargs)
