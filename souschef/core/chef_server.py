"""
Chef Server integration utilities.

Provides authenticated Chef Server access, connection validation, and
metadata discovery for nodes, roles, environments, cookbooks, and policies.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode, urlparse, urlunparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from souschef.core.path_utils import _normalize_path
from souschef.core.url_validation import validate_user_provided_url

if TYPE_CHECKING:
    import requests as requests_module
    from requests.exceptions import Timeout
else:
    try:
        import requests as requests_module
        from requests.exceptions import ConnectionError, Timeout  # noqa: A004
    except ImportError:
        requests_module = None  # type: ignore[assignment]
        ConnectionError = Exception  # type: ignore[assignment,misc]  # noqa: A004, A001
        Timeout = Exception  # type: ignore[assignment,misc]

# Constants
AUTH_CHUNK_SIZE = 60
JSON_CONTENT_TYPE = "application/json"
REDACTED_PLACEHOLDER = "***REDACTED***"


def _redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive information from text.

    Redacts PEM-encoded keys (RSA, EC, DSA), passwords, tokens, and other
    sensitive values before logging or displaying to prevent credential leaks.

    Args:
        text: Text potentially containing sensitive data.

    Returns:
        Text with sensitive data replaced by placeholder.

    """
    import re

    # Redact PEM-encoded keys (comprehensive pattern)
    text = re.sub(
        r"-----BEGIN[A-Z\s]+PRIVATE KEY-----[\s\S]+?-----END[A-Z\s]+PRIVATE KEY-----",
        REDACTED_PLACEHOLDER,
        text,
        flags=re.IGNORECASE,
    )

    # Redact potential key content patterns (base64-like multi-line blocks)
    text = re.sub(
        r"(?:^|\n)([A-Za-z0-9+/=]{40,}\n)+",
        f"\n{REDACTED_PLACEHOLDER}\n",
        text,
    )

    # Redact common secret variable assignments (more precise pattern)
    # Matches: password=value, token:value, secret="value", KEY='value'
    text = re.sub(
        r"\b(password|token|secret|key|credential)[\s]*[=:][\s]*['\"]?([^\s'\";,]+)['\"]?",
        rf"\1={REDACTED_PLACEHOLDER}",
        text,
        flags=re.IGNORECASE,
    )

    return text


@dataclass(frozen=True)
class ChefServerConfig:
    """
    Chef Server configuration settings.

    Args:
        server_url: Base URL of the Chef Server.
        organisation: Chef organisation (e.g., "default").
        client_name: Client or user name for authentication.
        client_key: PEM-encoded RSA private key.
        timeout: Request timeout in seconds.

    """

    server_url: str
    organisation: str
    client_name: str
    client_key: str
    timeout: int = 10


def _load_client_key(client_key_path: str | None, client_key: str | None) -> str:
    """
    Load a Chef client key from path or inline content.

    Args:
        client_key_path: Path to the PEM-encoded key file.
        client_key: PEM-encoded key content.

    Returns:
        PEM-encoded key content.

    Raises:
        ValueError: If no key is provided or key cannot be read.

    """
    if client_key:
        return client_key.strip()

    if not client_key_path:
        raise ValueError("Client key is required for Chef Server authentication")

    key_path = _normalize_path(client_key_path)
    if not key_path.exists():
        raise ValueError("Client key path does not exist")
    if not key_path.is_file():
        raise ValueError("Client key path must be a file")

    return key_path.read_text(encoding="utf-8").strip()


def _utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO-8601 format.

    Returns:
        Timestamp string compatible with Chef Server auth.

    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_bytes(data: bytes) -> str:
    """
    Hash bytes using SHA1 and return Base64 string.

    Args:
        data: Input bytes to hash.

    Returns:
        Base64-encoded SHA1 digest.

    """
    # S4790: Chef Server API requires SHA1 for request signing
    digest = hashes.Hash(hashes.SHA1())  # NOSONAR
    digest.update(data)
    return base64.b64encode(digest.finalize()).decode("utf-8")


def _normalise_server_url(server_url: str, organisation: str) -> str:
    """
    Normalise Chef Server URL to include organisation path.

    Args:
        server_url: Base Chef Server URL.
        organisation: Chef organisation name.

    Returns:
        Normalised URL with organisation path.

    Raises:
        ValueError: If inputs are invalid or inconsistent.

    """
    if not organisation:
        raise ValueError("Organisation is required")

    normalised = validate_user_provided_url(server_url)
    parsed = urlparse(normalised)
    path = parsed.path.rstrip("/")

    if "/organizations/" in path:
        expected = f"/organizations/{organisation}"
        if not path.endswith(expected):
            raise ValueError("Server URL organisation does not match configuration")
        return normalised

    if path:
        org_path = f"{path}/organizations/{organisation}"
    else:
        org_path = f"/organizations/{organisation}"

    return urlunparse(parsed._replace(path=org_path)).rstrip("/")


def _load_private_key(key_pem: str) -> rsa.RSAPrivateKey:
    """
    Load an RSA private key from PEM content.

    Args:
        key_pem: PEM-encoded private key.

    Returns:
        RSA private key instance.

    Raises:
        ValueError: If key cannot be parsed or is not RSA.

    """
    try:
        key = serialization.load_pem_private_key(key_pem.encode("utf-8"), password=None)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid client key format") from exc

    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("Client key must be an RSA private key")

    return key


def _sign_request(canonical: str, key_pem: str) -> str:
    """
    Sign a canonical request string with a private key.

    Args:
        canonical: Canonical request string.
        key_pem: PEM-encoded private key.

    Returns:
        Base64-encoded signature.

    Raises:
        ValueError: If signing fails.

    """
    key = _load_private_key(key_pem)
    try:
        # S4790: Chef Server API requires SHA1 for signing
        signature = key.sign(
            canonical.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA1(),  # NOSONAR
        )
    except Exception as exc:
        raise ValueError("Failed to sign Chef Server request") from exc

    return base64.b64encode(signature).decode("utf-8")


def _split_signature(signature: str) -> dict[str, str]:
    """
    Split a signature into Chef Server authorization headers.

    Args:
        signature: Base64 signature string.

    Returns:
        Dictionary of X-Ops-Authorization headers.

    """
    chunks = [
        signature[i : i + AUTH_CHUNK_SIZE]
        for i in range(0, len(signature), AUTH_CHUNK_SIZE)
    ]
    return {
        f"X-Ops-Authorization-{index + 1}": chunk for index, chunk in enumerate(chunks)
    }


def _build_auth_headers(
    method: str,
    path_with_query: str,
    body: bytes,
    client_name: str,
    timestamp: str,
    key_pem: str,
) -> dict[str, str]:
    """
    Build Chef Server authentication headers.

    Args:
        method: HTTP method.
        path_with_query: Path including query string.
        body: Request body bytes.
        client_name: Client/user name.
        timestamp: ISO timestamp.
        key_pem: PEM-encoded key.

    Returns:
        Header dictionary.

    """
    content_hash = _hash_bytes(body)
    hashed_path = _hash_bytes(path_with_query.encode("utf-8"))
    canonical = "\n".join(
        [
            f"Method:{method.upper()}",
            f"Hashed Path:{hashed_path}",
            f"X-Ops-Content-Hash:{content_hash}",
            f"X-Ops-Timestamp:{timestamp}",
            f"X-Ops-UserId:{client_name}",
        ]
    )

    signature = _sign_request(canonical, key_pem)
    auth_headers = _split_signature(signature)
    headers = {
        "Accept": JSON_CONTENT_TYPE,
        "Content-Type": JSON_CONTENT_TYPE,
        "X-Ops-Sign": "algorithm=sha1;version=1.0",
        "X-Ops-Userid": client_name,
        "X-Ops-Timestamp": timestamp,
        "X-Ops-Content-Hash": content_hash,
        "User-Agent": "souschef/chef-server-client",
    }
    headers.update(auth_headers)
    return headers


def _handle_chef_server_response(
    response: requests_module.Response, server_url: str
) -> tuple[bool, str]:
    """
    Handle Chef Server response status codes.

    Args:
        response: HTTP response from Chef Server.
        server_url: The Chef Server URL that was queried.

    Returns:
        Tuple of (success: bool, message: str).

    """
    if response.status_code == 200:
        return True, f"Successfully connected to Chef Server at {server_url}"
    if response.status_code == 401:
        return False, "Authentication failed - check your Chef Server credentials"
    if response.status_code == 403:
        return False, "Authorisation failed - access denied by Chef Server"
    if response.status_code == 404:
        return False, "Chef Server endpoint not found"
    return False, f"Connection failed with status code {response.status_code}"


class ChefServerClient:
    """
    Authenticated Chef Server client.

    Handles signed requests to Chef Server endpoints using key-based
    authentication and provides helper methods for core resources.
    """

    def __init__(self, config: ChefServerConfig) -> None:
        """
        Initialise the Chef Server client.

        Args:
            config: Chef Server configuration.

        """
        self._config = config
        self._base_url = _normalise_server_url(config.server_url, config.organisation)

    @property
    def base_url(self) -> str:
        """
        Return the normalised base URL.

        Returns:
            Base URL including organisation path.

        """
        return self._base_url

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> requests_module.Response:
        """
        Issue an authenticated request to Chef Server.

        Args:
            method: HTTP method.
            endpoint: Endpoint path (e.g., "/nodes").
            params: Optional query parameters.
            body: Optional JSON body.

        Returns:
            HTTP response object.

        Raises:
            RuntimeError: If requests is unavailable.

        """
        if not requests_module:
            raise RuntimeError("requests library not installed")

        endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        query = urlencode(params or {})
        path_with_query = f"{endpoint_path}?{query}" if query else endpoint_path
        url = f"{self._base_url}{path_with_query}"

        payload = (
            json.dumps(body, separators=(",", ":")).encode("utf-8") if body else b""
        )
        timestamp = _utc_timestamp()
        headers = _build_auth_headers(
            method,
            path_with_query,
            payload,
            self._config.client_name,
            timestamp,
            self._config.client_key,
        )

        return requests_module.request(
            method=method.upper(),
            url=url,
            data=payload if payload else None,
            headers=headers,
            timeout=self._config.timeout,
            verify=True,
        )

    def test_connection(self) -> tuple[bool, str]:
        """
        Validate connection by querying the search endpoint.

        Returns:
            Tuple of (success, message).

        """
        response = self._request("GET", "/search/node", params={"q": "*:*"})
        return _handle_chef_server_response(response, self._base_url)

    def search_nodes(self, search_query: str) -> list[dict[str, Any]]:
        """
        Search for nodes using Chef Server search API.

        Args:
            search_query: Chef search query.

        Returns:
            List of node metadata dictionaries.

        """
        response = self._request("GET", "/search/node", params={"q": search_query})
        response.raise_for_status()
        data = response.json()
        nodes = []
        for row in data.get("rows", []):
            if not isinstance(row, dict):
                continue
            nodes.append(
                {
                    "name": row.get("name", "unknown"),
                    "roles": row.get("run_list", []),
                    "environment": row.get("chef_environment", "_default"),
                    "platform": row.get("platform", "unknown"),
                    "ipaddress": row.get("ipaddress", ""),
                    "fqdn": row.get("fqdn", ""),
                    "automatic": row.get("automatic", {}),
                }
            )
        return nodes

    def list_roles(self) -> list[dict[str, Any]]:
        """
        List roles available in Chef Server.

        Returns:
            List of role summaries.

        """
        response = self._request("GET", "/roles")
        response.raise_for_status()
        data = response.json()
        return [
            {"name": name, "url": details.get("url")}
            for name, details in data.items()
            if isinstance(details, dict)
        ]

    def list_environments(self) -> list[dict[str, Any]]:
        """
        List environments available in Chef Server.

        Returns:
            List of environment summaries.

        """
        response = self._request("GET", "/environments")
        response.raise_for_status()
        data = response.json()
        return [
            {"name": name, "url": details.get("url")}
            for name, details in data.items()
            if isinstance(details, dict)
        ]

    def list_cookbooks(self) -> list[dict[str, Any]]:
        """
        List cookbooks available in Chef Server.

        Returns:
            List of cookbooks with version metadata.

        """
        response = self._request("GET", "/cookbooks")
        response.raise_for_status()
        data = response.json()
        cookbooks = []
        for name, details in data.items():
            if not isinstance(details, dict):
                continue
            cookbooks.append(
                {
                    "name": name,
                    "versions": details.get("versions", []),
                }
            )
        return cookbooks

    def get_cookbook_version(self, cookbook_name: str, version: str) -> dict[str, Any]:
        """
        Fetch cookbook details for a specific version.

        Args:
            cookbook_name: Cookbook name.
            version: Cookbook version string.

        Returns:
            Cookbook metadata payload.

        """
        response = self._request(
            "GET",
            f"/cookbooks/{cookbook_name}/{version}",
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}

    def list_policies(self) -> list[dict[str, Any]]:
        """
        List policies available in Chef Server.

        Returns:
            List of policy summaries.

        """
        response = self._request("GET", "/policies")
        response.raise_for_status()
        data = response.json()
        return [
            {"name": name, "url": details.get("url")}
            for name, details in data.items()
            if isinstance(details, dict)
        ]


def _build_client_config(
    server_url: str,
    organisation: str,
    client_name: str,
    client_key_path: str | None,
    client_key: str | None,
    timeout: int = 10,
) -> ChefServerConfig:
    """
    Build Chef Server configuration from inputs.

    Args:
        server_url: Base Chef Server URL.
        organisation: Chef organisation name.
        client_name: Client or user name.
        client_key_path: Path to key file.
        client_key: Inline key content.
        timeout: Request timeout.

    Returns:
        ChefServerConfig instance.

    """
    if not server_url:
        raise ValueError("Server URL is required")
    if not client_name:
        raise ValueError("Client name is required for authentication")

    key_content = _load_client_key(client_key_path, client_key)
    return ChefServerConfig(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key=key_content,
        timeout=timeout,
    )


def _build_client_from_env(
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
    timeout: int = 10,
) -> ChefServerClient:
    """
    Build a Chef Server client from inputs or environment variables.

    Args:
        server_url: Chef Server URL override.
        organisation: Organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.
        timeout: Request timeout.

    Returns:
        ChefServerClient instance.

    """
    config = _build_client_config(
        server_url or os.environ.get("CHEF_SERVER_URL", ""),
        organisation or os.environ.get("CHEF_ORG", "default"),
        client_name or os.environ.get("CHEF_CLIENT_NAME", ""),
        client_key_path or os.environ.get("CHEF_CLIENT_KEY_PATH"),
        client_key or os.environ.get("CHEF_CLIENT_KEY"),
        timeout=timeout,
    )
    return ChefServerClient(config)


def _validate_chef_server_connection(
    server_url: str,
    client_name: str,
    organisation: str = "default",
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> tuple[bool, str]:
    """
    Validate Chef Server connection by testing the search endpoint.

    Args:
        server_url: Base URL of the Chef Server.
        client_name: Client or user name for authentication.
        organisation: Chef organisation name.
        client_key_path: Path to client key file.
        client_key: Inline client key content.

    Returns:
        Tuple of (success: bool, message: str).

    """
    if not requests_module:
        return False, "requests library not installed"

    try:
        client = _build_client_from_env(
            server_url=server_url,
            organisation=organisation,
            client_name=client_name,
            client_key_path=client_key_path,
            client_key=client_key,
        )
        return client.test_connection()
    except ValueError as exc:
        return False, _redact_sensitive_data(str(exc))
    except Timeout:
        return False, f"Connection timeout - could not reach {server_url}"
    except ConnectionError:
        return False, f"Connection error - Chef Server not reachable at {server_url}"
    except Exception as exc:
        return False, _redact_sensitive_data(f"Unexpected error: {exc}")


def get_chef_nodes(
    search_query: str,
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query Chef Server for nodes matching search criteria.

    Args:
        search_query: Chef search query string.
        server_url: Chef Server URL override.
        organisation: Chef organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.

    Returns:
        List of node metadata.

    """
    client = _build_client_from_env(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )
    return client.search_nodes(search_query)


def list_chef_roles(
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    List roles from Chef Server.

    Args:
        server_url: Chef Server URL override.
        organisation: Chef organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.

    Returns:
        List of role summaries.

    """
    client = _build_client_from_env(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )
    return client.list_roles()


def list_chef_environments(
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    List environments from Chef Server.

    Args:
        server_url: Chef Server URL override.
        organisation: Chef organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.

    Returns:
        List of environment summaries.

    """
    client = _build_client_from_env(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )
    return client.list_environments()


def list_chef_cookbooks(
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    List cookbooks from Chef Server.

    Args:
        server_url: Chef Server URL override.
        organisation: Chef organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.

    Returns:
        List of cookbooks with version metadata.

    """
    client = _build_client_from_env(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )
    return client.list_cookbooks()


def get_chef_cookbook_version(
    cookbook_name: str,
    version: str,
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> dict[str, Any]:
    """
    Fetch cookbook metadata for a specific version.

    Args:
        cookbook_name: Cookbook name.
        version: Cookbook version string.
        server_url: Chef Server URL override.
        organisation: Chef organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.

    Returns:
        Cookbook metadata payload.

    """
    client = _build_client_from_env(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )
    return client.get_cookbook_version(cookbook_name, version)


def list_chef_policies(
    server_url: str | None = None,
    organisation: str | None = None,
    client_name: str | None = None,
    client_key_path: str | None = None,
    client_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    List policies from Chef Server.

    Args:
        server_url: Chef Server URL override.
        organisation: Chef organisation override.
        client_name: Client name override.
        client_key_path: Client key path override.
        client_key: Client key content override.

    Returns:
        List of policy summaries.

    """
    client = _build_client_from_env(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )
    return client.list_policies()
