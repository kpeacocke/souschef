"""
Intermediate Representation (IR) package for unified infrastructure migration.

Provides:
- IR schema for normalised representation of infrastructure configurations
- Versioning system for IR evolution and compatibility
- Plugin architecture for source parsers and target generators
"""

from .plugin import (
    PluginRegistry,
    SourceParser,
    TargetGenerator,
    get_plugin_registry,
)
from .schema import (
    IRAction,
    IRAttribute,
    IRGraph,
    IRGuard,
    IRMetadata,
    IRNode,
    IRNodeType,
    SourceType,
    TargetType,
)
from .versioning import (
    IRVersion,
    IRVersionManager,
    SchemaMigration,
    get_version_manager,
)

__all__ = [
    # Schema
    "IRNodeType",
    "SourceType",
    "TargetType",
    "IRMetadata",
    "IRAttribute",
    "IRGuard",
    "IRAction",
    "IRNode",
    "IRGraph",
    # Versioning
    "IRVersion",
    "IRVersionManager",
    "SchemaMigration",
    "get_version_manager",
    # Plugin architecture
    "SourceParser",
    "TargetGenerator",
    "PluginRegistry",
    "get_plugin_registry",
]
