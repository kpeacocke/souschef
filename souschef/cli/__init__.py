"""CLI module initialization."""

from souschef.cli.migration_wizard import (
    generate_migration_config,
    setup_wizard,
    validate_inputs,
)

__all__ = [
    "setup_wizard",
    "validate_inputs",
    "generate_migration_config",
]
