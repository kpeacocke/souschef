"""
Comprehensive unit tests for IR schema, versioning, and plugin architecture.

Tests cover:
- IR schema creation and manipulation
- Dependency validation and topological sorting
- Version management and compatibility
- Plugin registration and discovery
"""

from __future__ import annotations

import pytest

from souschef.ir import (
    IRAction,
    IRAttribute,
    IRGraph,
    IRGuard,
    IRNode,
    IRNodeType,
    IRVersion,
    IRVersionManager,
    PluginRegistry,
    SchemaMigration,
    SourceParser,
    SourceType,
    TargetGenerator,
    TargetType,
    get_plugin_registry,
    get_version_manager,
)


class TestIRVersion:
    """Test IR versioning functionality."""

    def test_version_parse_valid(self) -> None:
        """Test parsing valid version strings."""
        v1 = IRVersion.parse("1.0.0")
        assert v1.major == 1
        assert v1.minor == 0
        assert v1.patch == 0

        v2 = IRVersion.parse("2.5")
        assert v2.major == 2
        assert v2.minor == 5
        assert v2.patch == 0

    def test_version_parse_invalid(self) -> None:
        """Test parsing invalid version strings."""
        with pytest.raises(ValueError):
            IRVersion.parse("invalid")
        with pytest.raises(ValueError):
            IRVersion.parse("1")

    def test_version_comparison(self) -> None:
        """Test version comparison operators."""
        v1 = IRVersion(1, 0, 0)
        v2 = IRVersion(1, 1, 0)
        v3 = IRVersion(2, 0, 0)

        assert v1 < v2
        assert v2 < v3
        assert v1 <= v2
        assert v2 >= v1
        assert v3 > v2
        assert v1 == IRVersion(1, 0, 0)

    def test_version_compatibility(self) -> None:
        """Test version compatibility checking."""
        v1 = IRVersion(1, 0, 0)
        v2 = IRVersion(1, 5, 0)
        v3 = IRVersion(2, 0, 0)

        assert v1.is_compatible_with(v2)
        assert v2.is_compatible_with(v1)
        assert not v1.is_compatible_with(v3)

    def test_version_string_representation(self) -> None:
        """Test version string representation."""
        v = IRVersion(1, 2, 3)
        assert str(v) == "1.2.3"


class TestIRAttribute:
    """Test IR attribute functionality."""

    def test_create_attribute(self) -> None:
        """Test creating IR attributes."""
        attr = IRAttribute(
            name="port",
            value=8080,
            type_hint="int",
            required=True,
            description="Service port",
        )
        assert attr.name == "port"
        assert attr.value == 8080
        assert attr.type_hint == "int"
        assert attr.required is True

    def test_attribute_default_values(self) -> None:
        """Test attribute default values."""
        attr = IRAttribute(name="test", value="value")
        assert attr.type_hint == "any"
        assert attr.required is False


class TestIRGuard:
    """Test IR guard functionality."""

    def test_create_guard(self) -> None:
        """Test creating IR guards."""
        guard = IRGuard(
            condition="node['os'] == 'linux'",
            type="ruby",
            negated=False,
        )
        assert guard.condition == "node['os'] == 'linux'"
        assert guard.type == "ruby"
        assert guard.negated is False


class TestIRAction:
    """Test IR action functionality."""

    def test_create_action(self) -> None:
        """Test creating IR actions."""
        action = IRAction(
            name="install",
            type="package",
        )
        assert action.name == "install"
        assert action.type == "package"
        assert action.attributes == {}
        assert action.guards == []

    def test_add_attribute_to_action(self) -> None:
        """Test adding attributes to actions."""
        action = IRAction(name="install", type="package")
        attr = IRAttribute(name="package_name", value="nginx")
        action.attributes["package_name"] = attr
        assert "package_name" in action.attributes

    def test_action_to_dict(self) -> None:
        """Test serialising action to dictionary."""
        action = IRAction(
            name="install",
            type="package",
        )
        action.attributes["name"] = IRAttribute(
            name="name", value="nginx", type_hint="str"
        )
        result = action.to_dict()
        assert result["name"] == "install"
        assert result["type"] == "package"
        assert "name" in result["attributes"]


class TestIRNode:
    """Test IR node functionality."""

    def test_create_node(self) -> None:
        """Test creating IR nodes."""
        node = IRNode(
            node_id="pkg_nginx",
            node_type=IRNodeType.PACKAGE,
            name="nginx",
            source_type=SourceType.CHEF,
        )
        assert node.node_id == "pkg_nginx"
        assert node.node_type == IRNodeType.PACKAGE
        assert node.name == "nginx"

    def test_add_action_to_node(self) -> None:
        """Test adding actions to nodes."""
        node = IRNode(
            node_id="test",
            node_type=IRNodeType.RESOURCE,
            name="test",
            source_type=SourceType.CHEF,
        )
        action = IRAction(name="install", type="package")
        node.add_action(action)
        assert len(node.actions) == 1
        assert node.actions[0] == action

    def test_add_attribute_to_node(self) -> None:
        """Test adding attributes to nodes."""
        node = IRNode(
            node_id="test",
            node_type=IRNodeType.RESOURCE,
            name="test",
            source_type=SourceType.CHEF,
        )
        attr = IRAttribute(name="version", value="1.0")
        node.add_attribute("version", attr)
        assert "version" in node.attributes

    def test_add_dependency(self) -> None:
        """Test adding dependencies to nodes."""
        node = IRNode(
            node_id="test",
            node_type=IRNodeType.RESOURCE,
            name="test",
            source_type=SourceType.CHEF,
        )
        node.add_dependency("dep1")
        node.add_dependency("dep2")
        node.add_dependency("dep1")  # Should not add duplicate
        assert len(node.dependencies) == 2

    def test_node_to_dict(self) -> None:
        """Test serialising node to dictionary."""
        node = IRNode(
            node_id="test",
            node_type=IRNodeType.RESOURCE,
            name="test",
            source_type=SourceType.CHEF,
        )
        result = node.to_dict()
        assert result["node_id"] == "test"
        assert result["node_type"] == "resource"
        assert result["source_type"] == "chef"


class TestIRGraph:
    """Test IR graph functionality."""

    def test_create_graph(self) -> None:
        """Test creating IR graphs."""
        graph = IRGraph(
            graph_id="cookbook_nginx",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        assert graph.graph_id == "cookbook_nginx"
        assert len(graph.nodes) == 0

    def test_add_node_to_graph(self) -> None:
        """Test adding nodes to graphs."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        node = IRNode(
            node_id="test",
            node_type=IRNodeType.PACKAGE,
            name="nginx",
            source_type=SourceType.CHEF,
        )
        graph.add_node(node)
        assert graph.get_node("test") == node

    def test_validate_dependencies_no_errors(self) -> None:
        """Test dependency validation with no unresolved dependencies."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        node1 = IRNode(
            node_id="node1",
            node_type=IRNodeType.PACKAGE,
            name="nginx",
            source_type=SourceType.CHEF,
        )
        node2 = IRNode(
            node_id="node2",
            node_type=IRNodeType.SERVICE,
            name="nginx",
            source_type=SourceType.CHEF,
        )
        node2.add_dependency("node1")
        graph.add_node(node1)
        graph.add_node(node2)

        unresolved = graph.validate_dependencies()
        assert len(unresolved) == 0

    def test_validate_dependencies_with_errors(self) -> None:
        """Test dependency validation with unresolved dependencies."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        node = IRNode(
            node_id="node1",
            node_type=IRNodeType.PACKAGE,
            name="nginx",
            source_type=SourceType.CHEF,
        )
        node.add_dependency("missing_node")
        graph.add_node(node)

        unresolved = graph.validate_dependencies()
        assert "node1" in unresolved
        assert "missing_node" in unresolved["node1"]

    def test_topological_order_no_dependencies(self) -> None:
        """Test topological ordering with no dependencies."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        node1 = IRNode(
            node_id="1",
            node_type=IRNodeType.PACKAGE,
            name="pkg1",
            source_type=SourceType.CHEF,
        )
        node2 = IRNode(
            node_id="2",
            node_type=IRNodeType.PACKAGE,
            name="pkg2",
            source_type=SourceType.CHEF,
        )
        graph.add_node(node1)
        graph.add_node(node2)

        order = graph.get_topological_order()
        assert len(order) == 2
        assert "1" in order
        assert "2" in order

    def test_topological_order_with_dependencies(self) -> None:
        """Test topological ordering with dependencies."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        node1 = IRNode(
            node_id="1",
            node_type=IRNodeType.PACKAGE,
            name="pkg1",
            source_type=SourceType.CHEF,
        )
        node2 = IRNode(
            node_id="2",
            node_type=IRNodeType.PACKAGE,
            name="pkg2",
            source_type=SourceType.CHEF,
        )
        node2.add_dependency("1")
        graph.add_node(node1)
        graph.add_node(node2)

        order = graph.get_topological_order()
        assert order.index("1") < order.index("2")

    def test_topological_order_circular_dependency(self) -> None:
        """Test topological ordering detects circular dependencies."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
        )
        node1 = IRNode(
            node_id="1",
            node_type=IRNodeType.PACKAGE,
            name="pkg1",
            source_type=SourceType.CHEF,
        )
        node2 = IRNode(
            node_id="2",
            node_type=IRNodeType.PACKAGE,
            name="pkg2",
            source_type=SourceType.CHEF,
        )
        node1.add_dependency("2")
        node2.add_dependency("1")
        graph.add_node(node1)
        graph.add_node(node2)

        with pytest.raises(ValueError, match="Circular dependency"):
            graph.get_topological_order()

    def test_graph_to_dict(self) -> None:
        """Test serialising graph to dictionary."""
        graph = IRGraph(
            graph_id="test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )
        node = IRNode(
            node_id="test",
            node_type=IRNodeType.PACKAGE,
            name="nginx",
            source_type=SourceType.CHEF,
        )
        graph.add_node(node)

        result = graph.to_dict()
        assert result["graph_id"] == "test"
        assert result["version"] == "1.0.0"
        assert "test" in result["nodes"]


class TestIRVersionManager:
    """Test IR version manager functionality."""

    def test_version_manager_creation(self) -> None:
        """Test creating version manager."""
        manager = IRVersionManager()
        assert manager.current_version == IRVersion(1, 0)

    def test_add_supported_version(self) -> None:
        """Test adding supported versions."""
        manager = IRVersionManager()
        v2 = IRVersion(1, 1)
        manager.add_supported_version(v2)
        assert v2 in manager.supported_versions

    def test_is_version_compatible(self) -> None:
        """Test version compatibility checking."""
        manager = IRVersionManager()
        v1 = IRVersion(1, 0, 0)
        v2 = IRVersion(2, 0, 0)

        assert manager.is_version_compatible(v1)
        assert not manager.is_version_compatible(v2)

    def test_register_migration(self) -> None:
        """Test registering migrations."""
        manager = IRVersionManager()

        def transform(data):
            return data

        migration = SchemaMigration(
            from_version=IRVersion(1, 0),
            to_version=IRVersion(1, 1),
            transformation=transform,
        )
        manager.register_migration(migration)
        assert len(manager.migrations) == 1

    def test_get_migrations_path(self) -> None:
        """Test finding migration paths."""
        manager = IRVersionManager()

        def transform(data):
            return data

        migration = SchemaMigration(
            from_version=IRVersion(1, 0),
            to_version=IRVersion(1, 1),
            transformation=transform,
        )
        manager.register_migration(migration)

        path = manager.get_migrations_path(IRVersion(1, 0), IRVersion(1, 1))
        assert len(path) == 1
        assert path[0] == migration

    def test_version_manager_info(self) -> None:
        """Test getting version manager info."""
        manager = IRVersionManager()
        info = manager.get_version_info()
        assert "current_version" in info
        assert "supported_versions" in info


class TestPluginRegistry:
    """Test plugin registry functionality."""

    def test_register_parser(self) -> None:
        """Test registering parsers."""
        registry = PluginRegistry()

        class MockParser(SourceParser):
            @property
            def source_type(self) -> SourceType:
                return SourceType.CHEF

            @property
            def supported_versions(self) -> list[str]:
                return ["14.0", "15.0"]

            def parse(self, source_path: str, **options):
                pass

            def validate(self, source_path: str):
                pass

        registry.register_parser(SourceType.CHEF, MockParser)
        assert SourceType.CHEF in registry.get_available_parsers()

    def test_register_generator(self) -> None:
        """Test registering generators."""
        registry = PluginRegistry()

        class MockGenerator(TargetGenerator):
            @property
            def target_type(self) -> TargetType:
                return TargetType.ANSIBLE

            @property
            def supported_versions(self) -> list[str]:
                return ["2.10", "2.11"]

            def generate(self, graph: IRGraph, output_path: str, **options):
                pass

            def validate_ir(self, graph: IRGraph):
                pass

        registry.register_generator(TargetType.ANSIBLE, MockGenerator)
        assert TargetType.ANSIBLE in registry.get_available_generators()

    def test_get_parser(self) -> None:
        """Test getting registered parser."""
        registry = PluginRegistry()

        class MockParser(SourceParser):
            @property
            def source_type(self) -> SourceType:
                return SourceType.CHEF

            @property
            def supported_versions(self) -> list[str]:
                return ["14.0"]

            def parse(self, source_path: str, **options):
                pass

            def validate(self, source_path: str):
                pass

        registry.register_parser(SourceType.CHEF, MockParser)
        parser = registry.get_parser(SourceType.CHEF)
        assert parser is not None
        assert isinstance(parser, SourceParser)

    def test_get_parser_not_found(self) -> None:
        """Test getting unregistered parser returns None."""
        registry = PluginRegistry()
        parser = registry.get_parser(SourceType.PUPPET)
        assert parser is None

    def test_registry_info(self) -> None:
        """Test getting registry information."""
        registry = PluginRegistry()

        class MockParser(SourceParser):
            @property
            def source_type(self) -> SourceType:
                return SourceType.CHEF

            @property
            def supported_versions(self) -> list[str]:
                return ["14.0"]

            def parse(self, source_path: str, **options):
                pass

            def validate(self, source_path: str):
                pass

        registry.register_parser(SourceType.CHEF, MockParser)
        info = registry.get_registry_info()
        assert "parsers" in info
        assert len(info["parsers"]) == 1

    def test_duplicate_parser_registration(self) -> None:
        """Test duplicate parser registration raises error."""
        registry = PluginRegistry()

        class MockParser(SourceParser):
            @property
            def source_type(self) -> SourceType:
                return SourceType.CHEF

            @property
            def supported_versions(self) -> list[str]:
                return ["14.0"]

            def parse(self, source_path: str, **options):
                pass

            def validate(self, source_path: str):
                pass

        registry.register_parser(SourceType.CHEF, MockParser)
        with pytest.raises(ValueError, match="already registered"):
            registry.register_parser(SourceType.CHEF, MockParser)


class TestGlobalInstances:
    """Test global singleton instances."""

    def test_get_version_manager(self) -> None:
        """Test getting global version manager."""
        manager = get_version_manager()
        assert isinstance(manager, IRVersionManager)
        # Should return same instance
        assert manager is get_version_manager()

    def test_get_plugin_registry(self) -> None:
        """Test getting global plugin registry."""
        registry = get_plugin_registry()
        assert isinstance(registry, PluginRegistry)
        # Should return same instance
        assert registry is get_plugin_registry()
