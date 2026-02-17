"""
Intermediate Representation (IR) schema for unified migration modeling.

Defines the core data structures for representing infrastructure-as-code constructs
from various source tools (Chef, Puppet, Salt, Bash, PowerShell) in a normalised format
that can be converted to target systems like Ansible.

This module provides:
- Type definitions for IR nodes and relationships
- Validation for IR consistency
- Serialisation/deserialisation support
- Version compatibility tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IRNodeType(str, Enum):
    """Enumeration of possible IR node types."""

    RECIPE = "recipe"
    RESOURCE = "resource"
    ATTRIBUTE = "attribute"
    VARIABLE = "variable"
    GUARD = "guard"
    HANDLER = "handler"
    ACTION = "action"
    POLICY = "policy"
    TEMPLATE = "template"
    FILE = "file"
    PACKAGE = "package"
    SERVICE = "service"
    USER = "user"
    GROUP = "group"
    CUSTOM = "custom"


class SourceType(str, Enum):
    """Enumeration of supported source tools."""

    CHEF = "chef"
    PUPPET = "puppet"
    SALT = "salt"
    BASH = "bash"
    POWERSHELL = "powershell"
    ANSIBLE = "ansible"


class TargetType(str, Enum):
    """Enumeration of supported target tools."""

    ANSIBLE = "ansible"
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"


@dataclass
class IRMetadata:
    """Metadata for IR nodes tracking source and context information."""

    source_type: SourceType
    source_file: str
    source_line: int = 0
    original_id: str | None = None
    confidence_score: float = 1.0
    requires_review: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class IRAttribute:
    """Represents an attribute or parameter in the IR."""

    name: str
    value: str | int | bool | dict[str, Any] | list[Any] | None
    type_hint: str = "any"
    required: bool = False
    default_value: str | int | bool | dict[str, Any] | list[Any] | None = None
    description: str = ""


@dataclass
class IRGuard:
    """Represents a conditional guard or predicate."""

    condition: str
    type: str = "boolean"  # boolean, shell, ruby, etc.
    negated: bool = False
    metadata: IRMetadata = field(
        default_factory=lambda: IRMetadata(
            source_type=SourceType.CHEF, source_file="", source_line=0
        )
    )


@dataclass
class IRAction:
    """Represents an action or operation to be executed."""

    name: str
    type: str
    attributes: dict[str, IRAttribute] = field(default_factory=dict)
    guards: list[IRGuard] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)  # List of node IDs
    notifies: list[str] = field(default_factory=list)  # List of node IDs
    metadata: IRMetadata = field(
        default_factory=lambda: IRMetadata(
            source_type=SourceType.CHEF, source_file="", source_line=0
        )
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialise action to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "attributes": {
                k: {
                    "value": v.value,
                    "type": v.type_hint,
                    "required": v.required,
                }
                for k, v in self.attributes.items()
            },
            "guards": [
                {
                    "condition": g.condition,
                    "type": g.type,
                    "negated": g.negated,
                }
                for g in self.guards
            ],
            "requires": self.requires,
            "notifies": self.notifies,
        }


@dataclass
class IRNode:
    """
    Core IR node representing a configurable entity or operation.

    Provides unified representation for constructs like Chef resources,
    Puppet manifests, Salt states, or Bash commands.
    """

    node_id: str
    node_type: IRNodeType
    name: str
    source_type: SourceType
    actions: list[IRAction] = field(default_factory=list)
    attributes: dict[str, IRAttribute] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    parent_id: str | None = None
    metadata: IRMetadata = field(
        default_factory=lambda: IRMetadata(
            source_type=SourceType.CHEF, source_file="", source_line=0
        )
    )
    tags: dict[str, str] = field(default_factory=dict)

    def add_action(self, action: IRAction) -> None:
        """Add an action to this node."""
        self.actions.append(action)

    def add_attribute(self, name: str, attr: IRAttribute) -> None:
        """Add an attribute to this node."""
        self.attributes[name] = attr

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable on this node."""
        self.variables[name] = value

    def add_dependency(self, node_id: str) -> None:
        """Add a dependency to another node."""
        if node_id not in self.dependencies:
            self.dependencies.append(node_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialise node to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "source_type": self.source_type.value,
            "actions": [action.to_dict() for action in self.actions],
            "attributes": {
                k: {
                    "value": v.value,
                    "type": v.type_hint,
                    "required": v.required,
                }
                for k, v in self.attributes.items()
            },
            "variables": self.variables,
            "dependencies": self.dependencies,
            "parent_id": self.parent_id,
            "tags": self.tags,
        }


@dataclass
class IRGraph:
    """
    Directed acyclic graph of IR nodes representing complete infrastructure.

    Manages relationships between nodes, validates dependencies, and supports
    serialisation for storage and transport.
    """

    graph_id: str
    source_type: SourceType
    target_type: TargetType
    nodes: dict[str, IRNode] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    version: str = "1.0.0"

    def add_node(self, node: IRNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> IRNode | None:
        """Retrieve a node by ID."""
        return self.nodes.get(node_id)

    def validate_dependencies(self) -> dict[str, list[str]]:
        """
        Validate that all dependencies reference existing nodes.

        Returns:
            Dictionary mapping node IDs to lists of unresolved dependencies.

        """
        unresolved: dict[str, list[str]] = {}
        for node_id, node in self.nodes.items():
            missing = [dep for dep in node.dependencies if dep not in self.nodes]
            if missing:
                unresolved[node_id] = missing
        return unresolved

    def get_topological_order(self) -> list[str]:
        """
        Get nodes in topological order (respecting dependencies).

        Returns:
            List of node IDs in dependency order.

        Raises:
            ValueError: If circular dependencies are detected.

        """
        visited: set[str] = set()
        visiting: set[str] = set()
        result: list[str] = []

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            if node_id in visiting:
                raise ValueError(f"Circular dependency detected involving {node_id}")

            visiting.add(node_id)
            node = self.nodes[node_id]
            for dep in node.dependencies:
                if dep in self.nodes:
                    visit(dep)
            visiting.remove(node_id)
            visited.add(node_id)
            result.append(node_id)

        for node_id in self.nodes:
            visit(node_id)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Serialise graph to dictionary."""
        return {
            "graph_id": self.graph_id,
            "source_type": self.source_type.value,
            "target_type": self.target_type.value,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "metadata": self.metadata,
            "created_at": self.created_at,
            "version": self.version,
        }
