"""Tests for URL validation utilities."""

import pytest

from souschef.core.url_validation import (
    _is_private_hostname,
    _matches_allowlist,
    validate_user_provided_url,
)


def test_https_required() -> None:
    """Test that HTTP URLs are rejected."""
    insecure_url = "http" + "://" + "api.example.com"
    with pytest.raises(ValueError, match="HTTPS"):
        validate_user_provided_url(insecure_url)


def test_public_hostname_required() -> None:
    """Test that local hostnames are rejected by default."""
    with pytest.raises(ValueError, match="public hostname"):
        validate_user_provided_url("https://localhost")


def test_private_ip_rejected() -> None:
    """Test that private IPs are rejected by default."""
    with pytest.raises(ValueError, match="public hostname"):
        validate_user_provided_url("https://127.0.0.1")


def test_allowlist_allows_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that allowlisted hosts are permitted."""
    monkeypatch.setenv("SOUSCHEF_ALLOWED_HOSTNAMES", "localhost")
    assert validate_user_provided_url("https://localhost") == "https://localhost"


def test_allowlist_ignores_empty_entries() -> None:
    """Test allowlist matching skips empty entries."""
    assert _matches_allowlist("api.example.com", {"", "api.example.com"})


def test_fully_qualified_domain_required() -> None:
    """Test that non-qualified hostnames are rejected."""
    with pytest.raises(ValueError, match="fully qualified"):
        validate_user_provided_url("https://chef")


def test_strip_path_when_requested() -> None:
    """Test that strip_path removes paths and fragments."""
    result = validate_user_provided_url(
        "https://api.example.com/v1/resource#fragment",
        strip_path=True,
    )
    assert result == "https://api.example.com"


def test_default_url_used_when_empty() -> None:
    """Test that default URL is used when base URL is empty."""
    result = validate_user_provided_url(
        "",
        default_url="https://api.example.com",
    )
    assert result == "https://api.example.com"


def test_default_url_required_when_empty() -> None:
    """Test empty URL without default raises an error."""
    with pytest.raises(ValueError, match="Base URL is required"):
        validate_user_provided_url("")


def test_allowlist_env_var_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test empty allowlist does not block valid URLs."""
    monkeypatch.delenv("SOUSCHEF_ALLOWED_HOSTNAMES", raising=False)
    assert (
        validate_user_provided_url("https://api.example.com")
        == "https://api.example.com"
    )


def test_allowlist_blocks_unlisted_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test allowlist rejects hosts that are not listed."""
    monkeypatch.setenv("SOUSCHEF_ALLOWED_HOSTNAMES", "api.example.com")
    with pytest.raises(ValueError, match="allowlist"):
        validate_user_provided_url("https://other.example.com")


def test_allowlist_with_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test wildcard allowlist entries."""
    monkeypatch.setenv("SOUSCHEF_ALLOWED_HOSTNAMES", "*.example.com")
    assert (
        validate_user_provided_url("https://api.example.com")
        == "https://api.example.com"
    )


@pytest.mark.parametrize(
    "env_value",
    [
        "api.example.com, api.example.org",
        "api.example.com,,api.example.org",
        " api.example.com ",
    ],
)
def test_allowlist_parsing(env_value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test allowlist parsing handles spacing and empty entries."""
    monkeypatch.setenv("SOUSCHEF_ALLOWED_HOSTNAMES", env_value)
    assert (
        validate_user_provided_url("https://api.example.com")
        == "https://api.example.com"
    )


def test_allowlist_env_var_respects_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test allowlist env var override parameter."""
    monkeypatch.setenv("CUSTOM_ALLOWLIST", "api.example.com")
    assert (
        validate_user_provided_url(
            "https://api.example.com", allowlist_env_var="CUSTOM_ALLOWLIST"
        )
        == "https://api.example.com"
    )


def test_username_password_rejected() -> None:
    """Test that URLs with embedded credentials are rejected."""
    with pytest.raises(ValueError, match="credentials"):
        validate_user_provided_url("https://user:pass@example.com")


def test_missing_hostname_rejected() -> None:
    """Test that URLs without a hostname are rejected."""
    with pytest.raises(ValueError, match="hostname"):
        validate_user_provided_url("https://")


def test_allowed_hosts_blocks_other_hosts() -> None:
    """Test provider-specific allowed hosts enforcement."""
    with pytest.raises(ValueError, match="not permitted"):
        validate_user_provided_url(
            "https://api.example.com",
            allowed_hosts={"api.redhat.com"},
        )


def test_allowed_hosts_allows_exact_host() -> None:
    """Test provider-specific allowed hosts allow matching host."""
    assert (
        validate_user_provided_url(
            "https://api.redhat.com",
            allowed_hosts={"api.redhat.com"},
        )
        == "https://api.redhat.com"
    )


def test_private_hostname_allows_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test private hostname check allows unresolved DNS entries."""

    def fake_getaddrinfo(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        "souschef.core.url_validation.socket.getaddrinfo", fake_getaddrinfo
    )

    assert _is_private_hostname("example.invalid") is False


def test_private_hostname_blocks_private_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test private hostname check blocks private IP resolutions."""

    def fake_getaddrinfo(*_args, **_kwargs):
        return [(0, 0, 0, "", ("10.0.0.1", 443))]

    monkeypatch.setattr(
        "souschef.core.url_validation.socket.getaddrinfo", fake_getaddrinfo
    )

    assert _is_private_hostname("example.invalid") is True


def test_private_hostname_allows_public_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test private hostname check allows public IP resolutions."""

    def fake_getaddrinfo(*_args, **_kwargs):
        return [(0, 0, 0, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(
        "souschef.core.url_validation.socket.getaddrinfo", fake_getaddrinfo
    )

    assert _is_private_hostname("example.invalid") is False


def test_private_hostname_oserror_fails_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test private hostname check fails open on OSError (network timeout, etc)."""

    def fake_getaddrinfo(*_args, **_kwargs):
        raise OSError("Network unreachable")

    monkeypatch.setattr(
        "souschef.core.url_validation.socket.getaddrinfo", fake_getaddrinfo
    )

    # Should return False (fail open) to allow requests when DNS unavailable
    assert _is_private_hostname("example.com") is False
