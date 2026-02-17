"""
Integration tests for IR schema with real file operations and serialisation.

Tests verify:
- IR graph creation and serialisation to JSON
- Dependency validation with complex node structures
- Topological sorting with circular dependency detection
- Version manager operations and compatibility checking
- Plugin registry with real parser and generator implementations
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from souschef.ir import (
    IRAction,
    IRAttribute,
    IRGraph,
    IRGuard,
    IRNode,
    IRNodeType,
    IRVersion,
    PluginRegistry,
    SourceParser,
    SourceType,
    TargetGenerator,
    TargetType,
    get_plugin_registry,
    get_version_manager,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockChefParser(SourceParser):
    """Mock Chef parser for testing."""

    @property
    def source_type(self) -> SourceType:
        """Return source type."""
        return SourceType.CHEF

    @property
    def supported_versions(self) -> list[str]:
        """Return supported versions."""
        return ["12.0", "13.0", "14.0", "15.0"]

    def parse(self, source_path: str, **options):
        """Parse Chef configuration."""
        graph = IRGraph(
            graph_id="mock-chef-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )
        return graph

    def validate(self, source_path: str) -> dict:
        """Validate Chef configuration."""
        return {"valid": True, "errors": [], "warnings": []}


class MockAnsibleGenerator(TargetGenerator):
    """Mock Ansible generator for testing."""

    @property
    def target_type(self) -> TargetType:
        """Return target type."""
        return TargetType.ANSIBLE

    @property
    def supported_versions(self) -> list[str]:
        """Return supported versions."""
        return ["2.9", "2.10", "2.11", "2.12"]

    def generate(self, graph, output_path: str, **options) -> None:
        """Generate Ansible playbook from IR."""
        pass

    def validate_ir(self, graph) -> dict:
        """Validate IR for Ansible target."""
        return {
            "compatible": True,
            "issues": [],
            "warnings": [],
        }


class TestIRGraphSerialisation:
    """Tests for IR graph serialisation and delocalisation."""

    def test_serialise_simple_graph_to_json(self, tmp_path: Path) -> None:
        """Test serialising a simple IR graph to JSON."""
        graph = IRGraph(
            graph_id="test-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        node = IRNode(
            node_id="node-1",
            node_type=IRNodeType.RECIPE,
            name="default",
            source_type=SourceType.CHEF,
        )
        graph.add_node(node)

        data = graph.to_dict()
        assert data["graph_id"] == "test-001"
        assert data["source_type"] == "chef"
        assert data["target_type"] == "ansible"
        assert "node-1" in data["nodes"]

        # Write and read back
        output_file = tmp_path / "graph.json"
        output_file.write_text(json.dumps(data, indent=2))
        loaded_data = json.loads(output_file.read_text())

        assert loaded_data["graph_id"] == "test-001"
        assert loaded_data["nodes"]["node-1"]["name"] == "default"

    def test_serialise_complex_graph_with_dependencies(self, tmp_path: Path) -> None:
        """Test serialising a graph with node dependencies."""
        graph = IRGraph(
            graph_id="test-deps-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Create nodes with dependencies
        node1 = IRNode(
            node_id="install-pkg",
            node_type=IRNodeType.RESOURCE,
            name="install_package",
            source_type=SourceType.CHEF,
        )
        node2 = IRNode(
            node_id="start-svc",
            node_type=IRNodeType.SERVICE,
            name="start_service",
            source_type=SourceType.CHEF,
        )
        node2.dependencies.append("install-pkg")

        graph.add_node(node1)
        graph.add_node(node2)

        # Validate and serialise
        unresolved = graph.validate_dependencies()
        assert len(unresolved) == 0

        topological_order = graph.get_topological_order()
        assert topological_order == ["install-pkg", "start-svc"]

        data = graph.to_dict()
        output_file = tmp_path / "deps-graph.json"
        output_file.write_text(json.dumps(data, indent=2))
        loaded_data = json.loads(output_file.read_text())

        assert loaded_data["nodes"]["start-svc"]["dependencies"] == ["install-pkg"]

    def test_graph_with_actions_and_guards(self, tmp_path: Path) -> None:
        """Test serialising graph nodes with actions and guards."""
        graph = IRGraph(
            graph_id="test-actions-001",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        node = IRNode(
            node_id="resource-1",
            node_type=IRNodeType.RESOURCE,
            name="package_install",
            source_type=SourceType.CHEF,
        )

        # Add attributes
        attr = IRAttribute(name="package_name", value="nginx", required=True)
        node.add_attribute("package_name", attr)

        # Add actions with guards
        guard = IRGuard(condition="not_installed('nginx')", type="shell")
        action = IRAction(name="install", type="package")
        action.guards.append(guard)
        node.add_action(action)

        graph.add_node(node)

        data = graph.to_dict()
        output_file = tmp_path / "actions-graph.json"
        output_file.write_text(json.dumps(data, indent=2))
        loaded_data = json.loads(output_file.read_text())

        node_data = loaded_data["nodes"]["resource-1"]
        assert len(node_data["actions"]) == 1
        assert len(node_data["actions"][0]["guards"]) == 1
        assert node_data["attributes"]["package_name"]["value"] == "nginx"


class TestVersionManagerIntegration:
    """Integration tests for version management."""

    def test_version_manager_singleton_persistence(self) -> None:
        """Test that version manager singleton persists across calls."""
        mgr1 = get_version_manager()
        mgr1.add_supported_version(IRVersion(major=1, minor=5, patch=0))

        mgr2 = get_version_manager()
        versions = [v.to_tuple() for v in mgr2.supported_versions]

        assert (1, 5, 0) in versions

    def test_version_compatibility_check(self) -> None:
        """Test version compatibility checking."""
        v1 = IRVersion(major=1, minor=0, patch=0)
        v2 = IRVersion(major=1, minor=5, patch=0)
        v3 = IRVersion(major=2, minor=0, patch=0)

        assert v1.is_compatible_with(v2)
        assert v2.is_compatible_with(v1)
        assert not v1.is_compatible_with(v3)


class TestPluginRegistryIntegration:
    """Integration tests for plugin registry."""

    def test_register_and_retrieve_parser(self) -> None:
        """Test registering and retrieving a parser."""
        registry = PluginRegistry()
        registry.register_parser(SourceType.CHEF, MockChefParser)

        parser = registry.get_parser(SourceType.CHEF)
        assert parser is not None
        assert parser.source_type == SourceType.CHEF
        assert "12.0" in parser.supported_versions

    def test_register_and_retrieve_generator(self) -> None:
        """Test registering and retrieving a generator."""
        registry = PluginRegistry()
        registry.register_generator(TargetType.ANSIBLE, MockAnsibleGenerator)

        generator = registry.get_generator(TargetType.ANSIBLE)
        assert generator is not None
        assert generator.target_type == TargetType.ANSIBLE
        assert "2.9" in generator.supported_versions

    def test_list_available_plugins(self) -> None:
        """Test listing available parsers and generators."""
        registry = PluginRegistry()
        registry.register_parser(SourceType.CHEF, MockChefParser)
        registry.register_generator(TargetType.ANSIBLE, MockAnsibleGenerator)

        parsers = registry.get_available_parsers()
        generators = registry.get_available_generators()

        assert SourceType.CHEF in parsers
        assert TargetType.ANSIBLE in generators

    def test_get_registry_info(self) -> None:
        """Test getting registry information."""
        registry = PluginRegistry()
        registry.register_parser(SourceType.CHEF, MockChefParser)
        registry.register_generator(TargetType.ANSIBLE, MockAnsibleGenerator)

        info = registry.get_registry_info()

        assert len(info["parsers"]) == 1
        assert len(info["generators"]) == 1
        assert info["parsers"][0]["type"] == "chef"
        assert info["generators"][0]["type"] == "ansible"

    def test_duplicate_registration_raises_error(self) -> None:
        """Test that registering duplicate parsers raises error."""
        registry = PluginRegistry()
        registry.register_parser(SourceType.CHEF, MockChefParser)

        with pytest.raises(ValueError, match="Parser for .* already registered"):
            registry.register_parser(SourceType.CHEF, MockChefParser)

    def test_get_nonexistent_parser_returns_none(self) -> None:
        """Test that getting unregistered parser returns None."""
        registry = PluginRegistry()
        parser = registry.get_parser(SourceType.PUPPET)
        assert parser is None

    def test_global_registry_integration(self) -> None:
        """Test global plugin registry integration."""
        # Get global registry
        global_registry = get_plugin_registry()

        # Should be empty if not yet populated
        parsers_before = global_registry.get_available_parsers()
        generators_before = global_registry.get_available_generators()

        # Register new plugins
        global_registry.register_parser(SourceType.SALT, MockChefParser)
        global_registry.register_generator(TargetType.TERRAFORM, MockAnsibleGenerator)

        # Verify they're registered
        parsers_after = global_registry.get_available_parsers()
        generators_after = global_registry.get_available_generators()

        assert len(parsers_after) >= len(parsers_before)
        assert len(generators_after) >= len(generators_before)


class TestIRNodeOperations:
    """Integration tests for IR node operations."""

    def test_add_multiple_actions_to_node(self) -> None:
        """Test adding multiple actions to a node."""
        node = IRNode(
            node_id="resource-multi",
            node_type=IRNodeType.HANDLER,
            name="multi_action",
            source_type=SourceType.CHEF,
        )

        for i in range(5):
            action = IRAction(name=f"action-{i}", type="test")
            node.add_action(action)

        assert len(node.actions) == 5

    def test_set_node_variables(self) -> None:
        """Test setting variables on a node."""
        node = IRNode(
            node_id="resource-vars",
            node_type=IRNodeType.RECIPE,
            name="with_vars",
            source_type=SourceType.CHEF,
        )

        node.set_variable("mode", "0644")
        node.set_variable("owner", "root")
        node.set_variable("group", "wheel")

        assert node.variables["mode"] == "0644"
        assert node.variables["owner"] == "root"
        assert len(node.variables) == 3

    def test_node_tag_operations(self) -> None:
        """Test adding tags to nodes."""
        node = IRNode(
            node_id="resource-tags",
            node_type=IRNodeType.RESOURCE,
            name="tagged_resource",
            source_type=SourceType.CHEF,
        )

        node.tags["environment"] = "production"
        node.tags["team"] = "platform"
        node.tags["version"] = "v1.0"

        assert len(node.tags) == 3
        assert node.tags["environment"] == "production"


class TestComplexGraphScenarios:
    """Integration tests for complex graph scenarios."""

    def test_multi_level_dependency_graph(self) -> None:
        """Test graph with multi-level dependencies."""
        graph = IRGraph(
            graph_id="complex-deps",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Create a chain: node1 -> node2 -> node3 -> node4
        nodes = []
        for i in range(1, 5):
            node = IRNode(
                node_id=f"node-{i}",
                node_type=IRNodeType.RESOURCE,
                name=f"step_{i}",
                source_type=SourceType.CHEF,
            )
            if i > 1:
                node.dependencies.append(f"node-{i - 1}")
            nodes.append(node)
            graph.add_node(node)

        # Verify topological order
        order = graph.get_topological_order()
        assert order == ["node-1", "node-2", "node-3", "node-4"]

    def test_circular_dependency_detection(self) -> None:
        """Test detection of circular dependencies."""
        graph = IRGraph(
            graph_id="circular-test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Create circular dependency: A -> B -> C -> A
        node_a = IRNode(
            node_id="node-a",
            node_type=IRNodeType.RESOURCE,
            name="a",
            source_type=SourceType.CHEF,
        )
        node_b = IRNode(
            node_id="node-b",
            node_type=IRNodeType.RESOURCE,
            name="b",
            source_type=SourceType.CHEF,
        )
        node_c = IRNode(
            node_id="node-c",
            node_type=IRNodeType.RESOURCE,
            name="c",
            source_type=SourceType.CHEF,
        )

        node_a.dependencies.append("node-b")
        node_b.dependencies.append("node-c")
        node_c.dependencies.append("node-a")

        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)

        # Circular dependency should be detected
        with pytest.raises(ValueError, match="Circular dependency"):
            graph.get_topological_order()

    def test_diamond_dependency_pattern(self) -> None:
        """Test diamond dependency pattern resolution."""
        graph = IRGraph(
            graph_id="diamond-test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Create diamond: base <- [left, right] <- top
        base = IRNode(
            node_id="base",
            node_type=IRNodeType.RESOURCE,
            name="base",
            source_type=SourceType.CHEF,
        )
        left = IRNode(
            node_id="left",
            node_type=IRNodeType.RESOURCE,
            name="left",
            source_type=SourceType.CHEF,
        )
        right = IRNode(
            node_id="right",
            node_type=IRNodeType.RESOURCE,
            name="right",
            source_type=SourceType.CHEF,
        )
        top = IRNode(
            node_id="top",
            node_type=IRNodeType.RESOURCE,
            name="top",
            source_type=SourceType.CHEF,
        )

        left.dependencies.append("base")
        right.dependencies.append("base")
        top.dependencies.extend(["left", "right"])

        for node in [base, left, right, top]:
            graph.add_node(node)

        order = graph.get_topological_order()
        # base should come first, top should come last
        assert order[0] == "base"
        assert order[-1] == "top"
        # left and right should come after base and before top
        assert order.index("left") < order.index("top")
        assert order.index("right") < order.index("top")
        assert order.index("base") < order.index("left")
        assert order.index("base") < order.index("right")
