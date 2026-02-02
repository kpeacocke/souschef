"""Storage configuration helpers for SousChef."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


@dataclass(frozen=True)
class DatabaseSettings:
    """Database configuration settings."""

    backend: str
    sqlite_path: Path | None
    postgres_dsn: str | None
    postgres_host: str
    postgres_port: int
    postgres_name: str
    postgres_user: str
    postgres_password: str
    postgres_sslmode: str


@dataclass(frozen=True)
class BlobSettings:
    """Blob storage configuration settings."""

    backend: str
    s3_bucket: str
    s3_region: str
    s3_endpoint: str | None
    s3_access_key: str | None
    s3_secret_key: str | None


def _normalise_backend(value: str, aliases: Mapping[str, str], default: str) -> str:
    """Normalise backend names with aliases and defaults."""
    candidate = value.strip().lower()
    if not candidate:
        return default
    if candidate in aliases:
        return aliases[candidate]
    return candidate


def _empty_to_none(value: str | None) -> str | None:
    """Convert empty strings to None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def load_database_settings(
    env: Mapping[str, str] | None = None,
) -> DatabaseSettings:
    """
    Load database settings from environment variables.

    Args:
        env: Optional environment mapping for testing.

    Returns:
        DatabaseSettings instance.

    """
    source = env if env is not None else os.environ

    backend = _normalise_backend(
        source.get("SOUSCHEF_DB_BACKEND", "sqlite"),
        {"postgresql": "postgres", "postgre": "postgres"},
        "sqlite",
    )
    if backend not in {"sqlite", "postgres"}:
        backend = "sqlite"

    sqlite_path_raw = _empty_to_none(source.get("SOUSCHEF_DB_PATH"))
    sqlite_path = Path(sqlite_path_raw) if sqlite_path_raw else None

    postgres_dsn = _empty_to_none(source.get("SOUSCHEF_DB_DSN"))

    postgres_host = source.get("SOUSCHEF_DB_HOST", "postgres")
    postgres_port = int(source.get("SOUSCHEF_DB_PORT", "5432"))
    postgres_name = source.get("SOUSCHEF_DB_NAME", "souschef")
    postgres_user = source.get("SOUSCHEF_DB_USER", "souschef")
    postgres_password = source.get("SOUSCHEF_DB_PASSWORD", "souschef")
    postgres_sslmode = source.get("SOUSCHEF_DB_SSLMODE", "disable")

    return DatabaseSettings(
        backend=backend,
        sqlite_path=sqlite_path,
        postgres_dsn=postgres_dsn,
        postgres_host=postgres_host,
        postgres_port=postgres_port,
        postgres_name=postgres_name,
        postgres_user=postgres_user,
        postgres_password=postgres_password,
        postgres_sslmode=postgres_sslmode,
    )


def build_postgres_dsn(settings: DatabaseSettings) -> str:
    """
    Build a PostgreSQL DSN from settings.

    Args:
        settings: Database settings to build the DSN from.

    Returns:
        PostgreSQL DSN string.

    """
    if settings.postgres_dsn:
        return settings.postgres_dsn

    user = quote_plus(settings.postgres_user)
    password = quote_plus(settings.postgres_password)
    host = settings.postgres_host
    port = settings.postgres_port
    name = settings.postgres_name
    sslmode = quote_plus(settings.postgres_sslmode)

    return f"postgresql://{user}:{password}@{host}:{port}/{name}?sslmode={sslmode}"


def load_blob_settings(env: Mapping[str, str] | None = None) -> BlobSettings:
    """
    Load blob storage settings from environment variables.

    Args:
        env: Optional environment mapping for testing.

    Returns:
        BlobSettings instance.

    """
    source = env if env is not None else os.environ

    backend = _normalise_backend(
        source.get("SOUSCHEF_STORAGE_BACKEND", "local"),
        {"minio": "s3"},
        "local",
    )
    if backend not in {"local", "s3"}:
        backend = "local"

    s3_bucket = source.get("SOUSCHEF_S3_BUCKET", "souschef")
    s3_region = source.get("SOUSCHEF_S3_REGION", "us-east-1")
    s3_endpoint = _empty_to_none(source.get("SOUSCHEF_S3_ENDPOINT"))
    s3_access_key = _empty_to_none(source.get("SOUSCHEF_S3_ACCESS_KEY"))
    s3_secret_key = _empty_to_none(source.get("SOUSCHEF_S3_SECRET_KEY"))

    return BlobSettings(
        backend=backend,
        s3_bucket=s3_bucket,
        s3_region=s3_region,
        s3_endpoint=s3_endpoint,
        s3_access_key=s3_access_key,
        s3_secret_key=s3_secret_key,
    )
