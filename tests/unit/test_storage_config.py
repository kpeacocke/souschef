"""Unit tests for storage configuration helpers."""

from souschef.storage import (
    DatabaseSettings,
    build_postgres_dsn,
    load_blob_settings,
    load_database_settings,
)


def test_load_database_settings_defaults():
    """Test database settings default values."""
    settings = load_database_settings(env={})

    assert settings.backend == "sqlite"
    assert settings.sqlite_path is None
    assert settings.postgres_host == "postgres"
    assert settings.postgres_port == 5432


def test_load_database_settings_postgres_aliases():
    """Test database backend alias normalisation."""
    settings = load_database_settings(env={"SOUSCHEF_DB_BACKEND": "postgresql"})

    assert settings.backend == "postgres"


def test_load_database_settings_invalid_backend_defaults():
    """Invalid backend values should default to sqlite."""
    settings = load_database_settings(env={"SOUSCHEF_DB_BACKEND": "invalid"})

    assert settings.backend == "sqlite"


def test_load_database_settings_empty_values():
    """Empty values should normalise to None where appropriate."""
    settings = load_database_settings(
        env={
            "SOUSCHEF_DB_BACKEND": "sqlite",
            "SOUSCHEF_DB_PATH": "   ",
            "SOUSCHEF_DB_DSN": "",
        }
    )

    assert settings.sqlite_path is None
    assert settings.postgres_dsn is None


def test_build_postgres_dsn_uses_override():
    """Test PostgreSQL DSN uses explicit DSN when provided."""
    settings = DatabaseSettings(
        backend="postgres",
        sqlite_path=None,
        postgres_dsn="postgresql://user:pass@host:5432/db",
        postgres_host="postgres",
        postgres_port=5432,
        postgres_name="souschef",
        postgres_user="souschef",
        postgres_password="souschef",
        postgres_sslmode="disable",
    )

    assert build_postgres_dsn(settings) == "postgresql://user:pass@host:5432/db"


def test_build_postgres_dsn_from_fields():
    """Test PostgreSQL DSN building from component fields."""
    settings = DatabaseSettings(
        backend="postgres",
        sqlite_path=None,
        postgres_dsn=None,
        postgres_host="db",
        postgres_port=5433,
        postgres_name="souschef",
        postgres_user="user",
        postgres_password="password",
        postgres_sslmode="require",
    )

    dsn = build_postgres_dsn(settings)
    assert dsn.startswith("postgresql://user:password@db:5433/souschef")
    assert "sslmode=require" in dsn


def test_load_blob_settings_defaults():
    """Test blob storage settings defaults."""
    settings = load_blob_settings(env={})

    assert settings.backend == "local"
    assert settings.s3_bucket == "souschef"
    assert settings.s3_region == "us-east-1"


def test_load_blob_settings_minio_alias():
    """Test blob storage backend alias normalisation."""
    settings = load_blob_settings(env={"SOUSCHEF_STORAGE_BACKEND": "minio"})

    assert settings.backend == "s3"


def test_load_blob_settings_invalid_backend_defaults():
    """Invalid blob backend values should default to local."""
    settings = load_blob_settings(env={"SOUSCHEF_STORAGE_BACKEND": "invalid"})

    assert settings.backend == "local"


def test_load_blob_settings_overrides():
    """Test blob storage settings with overrides."""
    settings = load_blob_settings(
        env={
            "SOUSCHEF_STORAGE_BACKEND": "s3",
            "SOUSCHEF_S3_BUCKET": "bucket",
            "SOUSCHEF_S3_REGION": "ap-southeast-2",
            "SOUSCHEF_S3_ENDPOINT": "http://minio:9000",
            "SOUSCHEF_S3_ACCESS_KEY": "key",
            "SOUSCHEF_S3_SECRET_KEY": "secret",
        }
    )

    assert settings.backend == "s3"
    assert settings.s3_bucket == "bucket"
    assert settings.s3_region == "ap-southeast-2"
    assert settings.s3_endpoint == "http://minio:9000"
    assert settings.s3_access_key == "key"
    assert settings.s3_secret_key == "secret"
