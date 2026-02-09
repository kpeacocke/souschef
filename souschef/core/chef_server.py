"""
Chef Server validation utilities.

Provides functions to validate Chef Server connections without UI dependencies.
"""

from typing import TYPE_CHECKING

from souschef.core.url_validation import validate_user_provided_url

if TYPE_CHECKING:
    import requests as requests_module
    from requests.exceptions import (
        Timeout,
    )
else:
    try:
        import requests as requests_module
        from requests.exceptions import (
            ConnectionError,  # noqa: A004
            Timeout,
        )
    except ImportError:
        requests_module = None  # type: ignore[assignment]
        ConnectionError = Exception  # type: ignore[assignment,misc]  # noqa: A004, A001
        Timeout = Exception  # type: ignore[assignment,misc]

# Constants
JSON_CONTENT_TYPE = "application/json"


def _handle_chef_server_response(
    response: "requests_module.Response", server_url: str
) -> tuple[bool, str]:
    """
    Handle Chef Server search response.

    Args:
        response: HTTP response from Chef Server
        server_url: The Chef Server URL that was queried

    Returns:
        Tuple of (success: bool, message: str)

    """
    if response.status_code == 200:
        return True, f"✅ Successfully connected to Chef Server at {server_url}"
    if response.status_code == 401:
        return (
            False,
            "❌ Authentication failed - check your Chef Server credentials",
        )
    if response.status_code == 404:
        return False, "❌ Chef Server search endpoint not found"
    return (
        False,
        f"❌ Connection failed with status code {response.status_code}",
    )


def _validate_chef_server_connection(
    server_url: str, node_name: str
) -> tuple[bool, str]:
    """
    Validate Chef Server connection by testing the search endpoint.

    Args:
        server_url: Base URL of the Chef Server
        node_name: Chef node name for authentication

    Returns:
        Tuple of (success: bool, message: str)

    """
    if not requests_module:
        return False, "requests library not installed"

    if not server_url:
        return False, "Server URL is required"

    try:
        server_url = validate_user_provided_url(server_url)
    except ValueError as exc:
        return False, f"Invalid server URL: {exc}"

    if not node_name:
        return False, "Node name is required for authentication"

    # Test the search endpoint
    try:
        search_url = f"{server_url.rstrip('/')}/search/node"
        response = requests_module.get(
            search_url,
            params={"q": "*:*"},
            timeout=5,
            headers={"Accept": JSON_CONTENT_TYPE},
        )
        return _handle_chef_server_response(response, server_url)

    except Timeout:
        return False, f"❌ Connection timeout - could not reach {server_url}"
    except ConnectionError:
        return False, f"❌ Connection error - Chef Server not reachable at {server_url}"
    except Exception as e:
        return False, f"❌ Unexpected error: {e}"
