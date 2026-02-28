"""Tests for storage/config.py uncovered lines."""

from souschef.storage.config import (
    _empty_to_none,
    _normalise_backend,
    load_blob_settings,
    load_database_settings,
)


def test_normalise_backend_empty_string():
    """Test _normalise_backend returns default for empty string (line 43)."""
    result = _normalise_backend("", {"postgresql": "postgres"}, "sqlite")
    assert result == "sqlite"


def test_normalise_backend_whitespace_only():
    """Test _normalise_backend with whitespace-only string."""
    result = _normalise_backend("   ", {"postgresql": "postgres"}, "default")
    assert result == "default"


def test_empty_to_none_none_input():
    """Test _empty_to_none with None input."""
    result = _empty_to_none(None)
    assert result is None


def test_empty_to_none_empty_string():
    """Test _empty_to_none with empty string."""
    result = _empty_to_none("")
    assert result is None


def test_empty_to_none_whitespace():
    """Test _empty_to_none with whitespace."""
    result = _empty_to_none("   ")
    assert result is None


def test_empty_to_none_valid_string():
    """Test _empty_to_none with valid string."""
    result = _empty_to_none("value")
    assert result == "value"


def test_load_database_settings_defaults():
    """Test database settings with default environment."""
    settings = load_database_settings(env={})

    # Should use defaults
    assert settings.backend == "sqlite"


def test_load_database_settings_with_env():
    """Test database settings with custom environment."""
    env = {
        "SOUSCHEF_DB_BACKEND": "postgres",
        "SOUSCHEF_DB_HOST": "localhost",
        "SOUSCHEF_DB_PORT": "5432",
    }

    settings = load_database_settings(env=env)

    # Should use provided values
    assert settings.backend == "postgres"
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432


def test_load_blob_settings_defaults():
    """Test blob settings with default environment."""
    settings = load_blob_settings(env={})

    # Should use defaults
    assert settings is not None


def test_load_blob_settings_s3():
    """Test blob settings with S3 configuration."""
    env = {
        "SOUSCHEF_BLOB_BACKEND": "s3",
        "SOUSCHEF_S3_BUCKET": "my-bucket",
        "SOUSCHEF_S3_REGION": "us-east-1",
    }

    settings = load_blob_settings(env=env)

    # Should have blob settings
    assert settings is not None
    assert settings.s3_bucket == "my-bucket"
    assert settings.s3_region == "us-east-1"
