"""Intermediate Representation (IR) schema documentation.

This file provides comprehensive documentation for the IR module,
including data structures, version management, and plugin architecture.
"""

# Intermediate Representation Module

The Intermediate Representation (IR) module provides a unified, abstract representation of infrastructure-as-code configurations from various source tools (Chef, Puppet, Salt, Bash, PowerShell) that can be converted to target systems (Ansible, Terraform, CloudFormation).

## Overview

The IR module consists of three key components:

1. **IR Schema** (`schema.py`): Core data structures for representing infrastructure
2. **IR Versioning** (`versioning.py`): Version management and schema evolution
3. **Plugin Architecture** (`plugin.py`): Extensible framework for parsers and generators

## IR Schema

### Core Concepts

The IR schema defines a unified representation of infrastructure configurations using a directed acyclic graph (DAG) of nodes, where each node represents a configurable entity or operation.

### Data Structures

#### IRNodeType

Enumeration of supported node types used to categorise different infrastructure constructs:

- `RECIPE`: Configuration management recipe or routine
- `RESOURCE`: Resource definition (package, service, file, etc.)
- `ATTRIBUTE`: Configuration attribute or parameter
- `VARIABLE`: Variable or constant definition
- `GUARD`: Conditional predicate or guard clause
- `HANDLER`: Event handler or notification target
- `ACTION`: Discrete operation or state change
- `POLICY`: Security or compliance policy
- `TEMPLATE`: Template or configuration file
- `FILE`: File resource
- `PACKAGE`: Package resource
- `SERVICE`: Service resource
- `USER`: User account resource
- `GROUP`: User group resource
- `CUSTOM`: Custom or user-defined resource type

#### SourceType & TargetType

Enumerations defining supported source and target tools:

**SourceType:**
- `CHEF`: Chef configuration management
- `PUPPET`: Puppet configuration management
- `SALT`: SaltStack configuration management
- `BASH`: Bash shell scripts
- `POWERSHELL`: PowerShell scripts
- `ANSIBLE`: Ansible playbooks (can be both source and target)

**TargetType:**
- `ANSIBLE`: Ansible playbooks
- `TERRAFORM`: Terraform infrastructure code
- `CLOUDFORMATION`: AWS CloudFormation templates

#### IRAttribute

Represents an attribute or parameter with type information:

```python
class IRAttribute:
    name: str                                      # Attribute name
    value: str | int | bool | dict | list | None # Attribute value
    type_hint: str = "any"                         # Type hint for validation
    required: bool = False                         # Whether attribute is required
    default_value: ... = None                      # Default value if not specified
    description: str = ""                          # Human-readable description
```

#### IRGuard

Represents a conditional guard or predicate:

```python
class IRGuard:
    condition: str                  # Condition expression
    type: str = "boolean"          # Condition type (boolean, shell, ruby, etc.)
    negated: bool = False          # Whether condition is negated
    metadata: IRMetadata           # Source tracking metadata
```

#### IRAction

Represents a discrete operation or state change:

```python
class IRAction:
    name: str                              # Action name
    type: str                              # Action type
    attributes: dict[str, IRAttribute]   # Action parameters
    guards: list[IRGuard]                # Conditional guards
    requires: list[str]                  # Node IDs this action depends on
    notifies: list[str]                  # Node IDs to notify after execution
    metadata: IRMetadata                 # Source tracking metadata
```

#### IRNode

Core IR node representing a configurable entity:

```python
class IRNode:
    node_id: str                          # Unique node identifier
    node_type: IRNodeType                # Type of node
    name: str                            # Human-readable name
    source_type: SourceType              # Original source tool
    actions: list[IRAction]              # Operations/actions
    attributes: dict[str, IRAttribute]   # Node parameters
    variables: dict[str, Any]            # Variables/values
    dependencies: list[str]              # Node IDs this depends on
    parent_id: str | None                # Optional parent node
    metadata: IRMetadata                 # Source tracking
    tags: dict[str, str]                 # Arbitrary tags/labels
```

#### IRGraph

Directed acyclic graph of nodes representing complete infrastructure:

```python
class IRGraph:
    graph_id: str                        # Graph identifier
    source_type: SourceType              # Original source tool
    target_type: TargetType              # Target conversion tool
    nodes: dict[str, IRNode]            # Nodes by ID
    metadata: dict[str, Any]            # Graph-level metadata
    created_at: str                      # Creation timestamp
    version: str                         # IR version string
```

### Key Operations

#### Dependency Validation

Validate that all node dependencies reference existing nodes:

```python
graph = IRGraph(...)
unresolved = graph.validate_dependencies()
# Returns: dict[str, list[str]] mapping node IDs to unresolved dependencies
```

#### Topological Sorting

Get nodes in dependency order (respecting all dependencies):

```python
topological_order = graph.get_topological_order()
# Returns: list[str] of node IDs in execution order
# Raises: ValueError if circular dependencies detected
```

#### Serialisation

Convert IR structures to JSON-compatible dictionaries:

```python
node_data = node.to_dict()
action_data = action.to_dict()
graph_data = graph.to_dict()

# Save to file
import json
with open('graph.json', 'w') as f:
    json.dump(graph_data, f, indent=2)
```

## IR Versioning

The versioning module manages IR schema evolution and compatibility checking.

### IRVersion

Represents a semantic version with comparison operators:

```python
class IRVersion:
    major: int      # Major version (breaking changes)
    minor: int      # Minor version (backward compatible features)
    patch: int      # Patch version (bug fixes)
```

**Version Compatibility:**
- Versions are compatible if major versions match
- Minor and patch versions can differ within same major version
- Example: 1.0.0 is compatible with 1.5.3, but not with 2.0.0

**Version Operations:**

```python
# Parsing
v = IRVersion.parse("1.2.3")

# String representation
print(v)  # "1.2.3"

# Comparison
v1 < v2
v1 <= v2
v1 == v2
v1 != v2
v1 >= v2
v1 > v2

# Compatibility checking
v1.is_compatible_with(v2)  # True if major versions match
```

### SchemaMigration

Defines a transformation path between two IR schema versions:

```python
class SchemaMigration:
    from_version: IRVersion                    # Starting version
    to_version: IRVersion                      # Target version
    transformation: Callable[[dict], dict]    # Transformation function
    description: str                           # Migration description
```

### IRVersionManager

Manages version compatibility and schema migrations:

```python
manager = get_version_manager()

# Register migrations
manager.register_migration(SchemaMigration(...))

# Find migration path
migrations = manager.get_migrations_path(IRVersion(1,0,0), IRVersion(1,5,0))

# Migrate data
migrated = manager.migrate_data(data, from_version, to_version)

# Check compatibility
is_compatible = manager.is_version_compatible(version)

# Get version information
info = manager.get_version_info()
```

## Plugin Architecture

The plugin architecture provides extensibility for adding support for new source tools and target platforms.

### SourceParser

Abstract base class for source tool parsers:

```python
class SourceParser(ABC):
    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """Return the source tool type."""

    @property
    @abstractmethod
    def supported_versions(self) -> list[str]:
        """Return supported versions of the source tool."""

    @abstractmethod
    def parse(self, source_path: str, **options) -> IRGraph:
        """Parse source configuration into IR."""

    @abstractmethod
    def validate(self, source_path: str) -> dict:
        """Validate source configuration without parsing."""

    def get_metadata(self) -> dict[str, str]:
        """Get parser metadata."""
```

### TargetGenerator

Abstract base class for target platform generators:

```python
class TargetGenerator(ABC):
    @property
    @abstractmethod
    def target_type(self) -> TargetType:
        """Return the target system type."""

    @property
    @abstractmethod
    def supported_versions(self) -> list[str]:
        """Return supported versions of the target system."""

    @abstractmethod
    def generate(self, graph: IRGraph, output_path: str, **options) -> None:
        """Generate target configuration from IR."""

    @abstractmethod
    def validate_ir(self, graph: IRGraph) -> dict:
        """Validate IR for compatibility with this target."""

    def get_metadata(self) -> dict[str, str]:
        """Get generator metadata."""
```

### PluginRegistry

Central registry for managing plugins:

```python
registry = get_plugin_registry()

# Register plugins
registry.register_parser(SourceType.CHEF, ChefParser)
registry.register_generator(TargetType.ANSIBLE, AnsibleGenerator)

# Retrieve plugins
parser = registry.get_parser(SourceType.CHEF)
generator = registry.get_generator(TargetType.ANSIBLE)

# List available plugins
parsers = registry.get_available_parsers()
generators = registry.get_available_generators()

# Get registry information
info = registry.get_registry_info()
```

## Implementing Custom Parsers

To add support for a new source tool:

```python
from souschef.ir import SourceParser, SourceType, IRGraph

class CustomToolParser(SourceParser):
    @property
    def source_type(self) -> SourceType:
        return SourceType.CUSTOM_TOOL

    @property
    def supported_versions(self) -> list[str]:
        return ["1.0", "2.0", "3.0"]

    def parse(self, source_path: str, **options) -> IRGraph:
        # Parse source configuration and build IR graph
        graph = IRGraph(
            graph_id="custom-tool-parse",
            source_type=self.source_type,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Add nodes to graph
        # ... parsing logic ...

        return graph

    def validate(self, source_path: str) -> dict:
        # Validate source configuration
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

# Register the parser
registry = get_plugin_registry()
registry.register_parser(SourceType.CUSTOM_TOOL, CustomToolParser)
```

## Implementing Custom Generators

To add support for a new target platform:

```python
from souschef.ir import TargetGenerator, TargetType, IRGraph

class CustomTargetGenerator(TargetGenerator):
    @property
    def target_type(self) -> TargetType:
        return TargetType.CUSTOM_TARGET

    @property
    def supported_versions(self) -> list[str]:
        return ["1.0", "2.0"]

    def generate(self, graph: IRGraph, output_path: str, **options) -> None:
        # Generate target configuration from IR graph
        # ... generation logic ...
        pass

    def validate_ir(self, graph: IRGraph) -> dict:
        # Validate IR for compatibility
        return {
            "compatible": True,
            "issues": [],
            "warnings": [],
        }

# Register the generator
registry = get_plugin_registry()
registry.register_generator(TargetType.CUSTOM_TARGET, CustomTargetGenerator)
```

## Best Practices

### IR Graph Design

1. **Use unique node IDs**: Ensure all nodes have globally unique identifiers within a graph
2. **Keep dependencies acyclic**: Avoid circular dependencies which will be detected and raise errors
3. **Set metadata**: Track source file and line number for better error reporting
4. **Use appropriate node types**: Choose node types that accurately reflect the infrastructure construct

### Dependency Management

1. **Explicit dependencies**: Always explicitly declare dependencies between nodes
2. **Avoid implicit ordering**: Don't rely on iteration order; use topological sorting for correct order
3. **Test circular detection**: Verify circular dependency detection works for your use cases

### Version Compatibility

1. **Semantic versioning**: Follow semantic versioning conventions for IR schema versions
2. **Test migrations**: Ensure schema migrations are tested thoroughly before deployment
3. **Document changes**: Document all schema changes and migration paths

## Example Workflow

```python
from souschef.ir import (
    IRGraph,
    IRNode,
    IRNodeType,
    IRAction,
    IRAttribute,
    SourceType,
    TargetType,
    get_plugin_registry,
)

# Create IR graph
graph = IRGraph(
    graph_id="example-001",
    source_type=SourceType.CHEF,
    target_type=TargetType.ANSIBLE,
    version="1.0.0",
)

# Add nodes
node1 = IRNode(
    node_id="install-nginx",
    node_type=IRNodeType.PACKAGE,
    name="Install nginx",
    source_type=SourceType.CHEF,
)
graph.add_node(node1)

node2 = IRNode(
    node_id="start-nginx",
    node_type=IRNodeType.SERVICE,
    name="Start nginx service",
    source_type=SourceType.CHEF,
)
node2.add_dependency("install-nginx")
graph.add_node(node2)

# Validate dependencies
unresolved = graph.validate_dependencies()
assert len(unresolved) == 0, "Unresolved dependencies found"

# Get topological order
order = graph.get_topological_order()
print(f"Execution order: {order}")
# Output: Execution order: ['install-nginx', 'start-nginx']

# Use plugin registry to convert
registry = get_plugin_registry()
parser = registry.get_parser(SourceType.CHEF)
generator = registry.get_generator(TargetType.ANSIBLE)

# Generate output
generator.generate(graph, output_path="./playbook.yml")
```

## Testing

The IR module includes comprehensive testing:

- **Unit tests**: Test IR schema, versioning, and plugin architecture
- **Integration tests**: Test real-world scenarios with complex dependencies
- **Property-based tests**: Fuzz testing with Hypothesis to ensure robustness

Run tests:

```bash
# Unit tests
poetry run pytest tests/unit/test_ir_schema.py
poetry run pytest tests/unit/test_ir_property_based.py

# Integration tests
poetry run pytest tests/integration/test_ir_integration.py

# All tests with coverage
poetry run pytest tests/ --cov=souschef.ir
```
