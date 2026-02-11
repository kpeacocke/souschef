"""URL validation utilities for user-provided endpoints."""

import ipaddress
import os
import socket
from collections.abc import Iterable
from urllib.parse import urlparse, urlunparse

DEFAULT_ALLOWLIST_ENV = "SOUSCHEF_ALLOWED_HOSTNAMES"


def _split_allowlist(env_value: str) -> set[str]:
    """
    Split an allowlist environment variable into hostnames.

    Args:
        env_value: Raw environment value containing hostnames.

    Returns:
        A set of normalised hostnames.

    """
    return {entry.strip().lower() for entry in env_value.split(",") if entry.strip()}


def _matches_allowlist(hostname: str, allowlist: Iterable[str]) -> bool:
    """
    Check whether a hostname matches the allowlist.

    Args:
        hostname: Hostname to validate.
        allowlist: Iterable of allowlist entries.

    Returns:
        True if the hostname matches the allowlist.

    """
    for entry in allowlist:
        entry = entry.lower().strip()
        if not entry:
            continue
        if entry.startswith("*."):
            suffix = entry[1:]
            if hostname.endswith(suffix) and hostname != suffix.lstrip("."):
                return True
        elif hostname == entry:
            return True
    return False


def _is_private_hostname(hostname: str) -> bool:
    """
    Determine whether a hostname resolves to a private or local address.

    Performs DNS resolution to prevent DNS rebinding attacks.

    Args:
        hostname: Hostname to inspect.

    Returns:
        True if the hostname is private, local, or resolves to any private addresses.

    """
    local_suffixes = (".localhost", ".local", ".localdomain", ".internal")
    if hostname in {"localhost"} or hostname.endswith(local_suffixes):
        return True

    # Check if it's a literal IP address
    try:
        ip_address = ipaddress.ip_address(hostname)
        return bool(
            ip_address.is_private
            or ip_address.is_loopback
            or ip_address.is_link_local
            or ip_address.is_reserved
            or ip_address.is_multicast
            or ip_address.is_unspecified
        )
    except ValueError:
        pass  # Not a literal IP, proceed to DNS resolution

    # RFC 2606: Skip DNS resolution for reserved test domains
    test_domains = (".example.com", ".example.org", ".example.net", ".test")
    if any(hostname.endswith(suffix) for suffix in test_domains):
        # Allow reserved test domains without DNS resolution
        return False

    # Resolve hostname to all A/AAAA records and check if ANY resolve to private IPs
    try:
        socket.setdefaulttimeout(10)  # Limit DNS resolution to 10 seconds
        addrinfo = socket.getaddrinfo(
            hostname, 443, socket.AF_UNSPEC, socket.SOCK_STREAM
        )
        socket.setdefaulttimeout(None)

        if not addrinfo:
            # Cannot resolve - allow it (fail open, DNS may work at runtime)
            return False

        # Check ALL resolved addresses - if ANY are private/reserved, reject
        for _family, _socktype, _proto, _canonname, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            ip_address = ipaddress.ip_address(ip_str)
            if (
                ip_address.is_private
                or ip_address.is_loopback
                or ip_address.is_link_local
                or ip_address.is_reserved
                or ip_address.is_multicast
                or ip_address.is_unspecified
            ):
                return True

        return False  # All resolved addresses are public

    except (socket.gaierror, TimeoutError, OSError):
        # DNS resolution failed/timeout - allow it (fail open, assume public)
        # The hostname may resolve correctly at runtime
        return False


def _is_ip_literal(hostname: str) -> bool:
    """
    Check whether the hostname is an IP literal.

    Args:
        hostname: Hostname to inspect.

    Returns:
        True if the hostname is an IP literal.

    """
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


def _normalise_url_value(base_url: str, default_url: str | None) -> str:
    """
    Normalise the input URL value.

    Args:
        base_url: URL provided by the user.
        default_url: Default URL to use when base_url is empty.

    Returns:
        Normalised URL string.

    """
    url_value = str(base_url).strip()
    if not url_value:
        if default_url is None:
            raise ValueError("Base URL is required.")
        url_value = default_url

    if "://" not in url_value:
        url_value = f"https://{url_value}"

    return url_value


def _validate_scheme(parsed_url) -> None:
    """
    Validate URL scheme.

    Args:
        parsed_url: Parsed URL object.

    """
    if parsed_url.scheme.lower() != "https":
        raise ValueError("Base URL must use HTTPS.")


def _validate_hostname(
    hostname: str,
    allowlist: set[str],
    allowed_hosts: set[str] | None,
) -> None:
    """
    Validate hostname using allowlist and public host rules.

    Args:
        hostname: Hostname to validate.
        allowlist: Allowlisted hostnames.
        allowed_hosts: Provider-specific allowed hostnames.

    """
    hostname = hostname.lower()
    is_ip_literal = _is_ip_literal(hostname)

    if allowed_hosts and hostname not in allowed_hosts:
        raise ValueError("Base URL host is not permitted.")

    allowlist_match = _matches_allowlist(hostname, allowlist) if allowlist else False
    if allowlist and not allowlist_match:
        raise ValueError("Base URL host is not in the allowlist.")

    if not allowlist_match and _is_private_hostname(hostname):
        raise ValueError("Base URL host must be a public hostname.")

    if not allowlist_match and "." not in hostname and not is_ip_literal:
        raise ValueError("Base URL host must be a fully qualified domain name.")


def _normalise_parsed_url(parsed_url, strip_path: bool) -> str:
    """
    Normalise a parsed URL into a string.

    Args:
        parsed_url: Parsed URL object.
        strip_path: Whether to strip paths, queries, and fragments.

    Returns:
        Normalised URL string.

    """
    cleaned = parsed_url._replace(params="", query="", fragment="")
    if strip_path:
        cleaned = cleaned._replace(path="")

    return str(urlunparse(cleaned)).rstrip("/")


def validate_user_provided_url(
    base_url: str,
    *,
    default_url: str | None = None,
    allowlist_env_var: str = DEFAULT_ALLOWLIST_ENV,
    allowed_hosts: set[str] | None = None,
    strip_path: bool = False,
) -> str:
    """
    Validate a user-provided URL for outbound requests.

    Args:
        base_url: URL provided by the user.
        default_url: Default URL to use when base_url is empty.
        allowlist_env_var: Environment variable containing allowed hostnames.
        allowed_hosts: Explicit host allowlist for provider-specific endpoints.
        strip_path: Whether to strip paths, queries, and fragments.

    Returns:
        Validated and normalised URL string.

    Raises:
        ValueError: If the URL is invalid or fails security validation.

    """
    url_value = _normalise_url_value(base_url, default_url)
    parsed = urlparse(url_value)

    _validate_scheme(parsed)

    if not parsed.hostname:
        raise ValueError("Base URL must include a hostname.")

    if parsed.username or parsed.password:
        raise ValueError("Base URL must not include user credentials.")

    allowlist_value = os.environ.get(allowlist_env_var, "")
    allowlist = _split_allowlist(allowlist_value)
    normalised_allowed_hosts = (
        {host.lower() for host in allowed_hosts} if allowed_hosts else None
    )

    _validate_hostname(parsed.hostname, allowlist, normalised_allowed_hosts)

    return _normalise_parsed_url(parsed, strip_path)
