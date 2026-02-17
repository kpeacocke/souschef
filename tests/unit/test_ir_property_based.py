"""
Property-based tests for IR schema using Hypothesis.

Uses Hypothesis for fuzz testing to ensure IR components handle
any input gracefully and maintain invariants.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from souschef.ir import (
    IRAction,
    IRAttribute,
    IRGraph,
    IRGuard,
    IRNode,
    IRNodeType,
    IRVersion,
    SourceType,
    TargetType,
)

# Strategies for generating IR data
node_id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=50
)
node_name_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_ ", min_size=1, max_size=100
)
version_strategy = st.integers(min_value=0, max_value=100)


class TestIRNodeCreation:
    """Property-based tests for IR node creation and serialisation."""

    @given(node_id_strategy, node_name_strategy)
    @settings(max_examples=50)
    def test_node_creation_always_succeeds(self, node_id: str, name: str) -> None:
        """Test that nodes can be created with any reasonable node_id and name."""
        node = IRNode(
            node_id=node_id,
            node_type=IRNodeType.RESOURCE,
            name=name,
            source_type=SourceType.CHEF,
        )
        assert node.node_id == node_id
        assert node.name == name
        assert not node.dependencies
        assert not node.actions

    @given(node_id_strategy, node_name_strategy)
    @settings(max_examples=50)
    def test_node_serialisation_roundtrip(self, node_id: str, name: str) -> None:
        """Test that node serialisation preserves data."""
        node = IRNode(
            node_id=node_id,
            node_type=IRNodeType.RESOURCE,
            name=name,
            source_type=SourceType.CHEF,
        )
        data = node.to_dict()

        assert data["node_id"] == node_id
        assert data["name"] == name
        assert data["node_type"] == "resource"
        assert data["source_type"] == "chef"

    @given(
        node_id_strategy,
        st.lists(node_id_strategy, max_size=10, unique=True),
    )
    @settings(max_examples=50)
    def test_node_dependencies_accumulation(
        self, node_id: str, dependencies: list[str]
    ) -> None:
        """Test that node dependencies can be accumulated without errors."""
        node = IRNode(
            node_id=node_id,
            node_type=IRNodeType.RESOURCE,
            name="test",
            source_type=SourceType.CHEF,
        )

        for dep in dependencies:
            node.add_dependency(dep)

        assert len(node.dependencies) == len(set(dependencies))

    @given(st.dictionaries(node_id_strategy, st.text(), max_size=20))
    @settings(max_examples=50)
    def test_node_variables_storage(self, variables: dict[str, str]) -> None:
        """Test that node variables can store arbitrary strings."""
        node = IRNode(
            node_id="test-node",
            node_type=IRNodeType.RESOURCE,
            name="test",
            source_type=SourceType.CHEF,
        )

        for key, value in variables.items():
            node.set_variable(key, value)

        assert len(node.variables) == len(variables)
        for key, value in variables.items():
            assert node.variables[key] == value


class TestIRAttributeCreation:
    """Property-based tests for IR attribute creation."""

    @given(
        st.text(min_size=1, max_size=50),
        st.integers() | st.text() | st.booleans() | st.none(),
    )
    @settings(max_examples=50)
    def test_attribute_values_always_accepted(self, name: str, value) -> None:
        """Test that attributes accept any value type."""
        attr = IRAttribute(name=name, value=value)
        assert attr.name == name
        assert attr.value == value

    @given(
        st.text(min_size=1, max_size=50),
        st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_attribute_type_hints_preserved(self, name: str, type_hint: str) -> None:
        """Test that attribute type hints are preserved."""
        attr = IRAttribute(name=name, value="test", type_hint=type_hint)
        assert attr.type_hint == type_hint


class TestIRActionCreation:
    """Property-based tests for IR action creation."""

    @given(
        st.text(min_size=1, max_size=50),
        st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_action_creation_always_succeeds(self, name: str, action_type: str) -> None:
        """Test that actions can be created with any name and type."""
        action = IRAction(name=name, type=action_type)
        assert action.name == name
        assert action.type == action_type
        assert not action.guards
        assert not action.requires

    @given(
        st.text(min_size=1, max_size=50),
        st.lists(
            st.text(min_size=1, max_size=50),
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_action_dependencies_accumulation(
        self, action_name: str, dependencies: list[str]
    ) -> None:
        """Test that actions can accumulate requires and notifies."""
        action = IRAction(name=action_name, type="test")
        action.requires.extend(dependencies)
        action.notifies.extend(dependencies)

        assert len(action.requires) == len(dependencies)
        assert len(action.notifies) == len(dependencies)

    @given(
        st.text(min_size=1, max_size=50),
        st.lists(
            st.text(min_size=1, max_size=100),
            max_size=3,
        ),
    )
    @settings(max_examples=50)
    def test_action_guards_accumulation(
        self, action_name: str, conditions: list[str]
    ) -> None:
        """Test that actions can accumulate guards."""
        action = IRAction(name=action_name, type="test")

        for condition in conditions:
            guard = IRGuard(condition=condition)
            action.guards.append(guard)

        assert len(action.guards) == len(conditions)


class TestIRVersionOperations:
    """Property-based tests for IR version operations."""

    @given(version_strategy, version_strategy, version_strategy)
    @settings(max_examples=50)
    def test_version_creation_always_succeeds(
        self, major: int, minor: int, patch: int
    ) -> None:
        """Test that versions can be created with any integers."""
        version = IRVersion(major=major, minor=minor, patch=patch)
        assert version.major == major
        assert version.minor == minor
        assert version.patch == patch

    @given(version_strategy, version_strategy, version_strategy)
    @settings(max_examples=50)
    def test_version_string_always_parseable(
        self, major: int, minor: int, patch: int
    ) -> None:
        """Test that version strings are always parseable."""
        version = IRVersion(major=major, minor=minor, patch=patch)
        version_str = str(version)

        parsed = IRVersion.parse(version_str)
        assert parsed.major == major
        assert parsed.minor == minor
        assert parsed.patch == patch

    @given(version_strategy, version_strategy, version_strategy)
    @settings(max_examples=50)
    def test_version_comparison_always_succeeds(
        self, major1: int, minor1: int, patch1: int
    ) -> None:
        """Test that version comparison always works."""
        ver1 = IRVersion(major=major1, minor=minor1, patch=patch1)
        ver2 = IRVersion(major=major1, minor=minor1, patch=patch1)

        # Identical versions should be equal
        assert ver1 == ver2
        assert ver1 >= ver2
        assert ver1 <= ver2
        assert ver1 <= ver2
        assert ver1 >= ver2

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_version_compatibility_consistent(self, major: int) -> None:
        """Test that version compatibility is consistent."""
        v1 = IRVersion(major=major, minor=0, patch=0)
        v2 = IRVersion(major=major, minor=1, patch=0)

        result1 = v1.is_compatible_with(v2)
        result2 = v2.is_compatible_with(v1)

        # Compatibility should be reflexive within same major
        assert result1 == result2
        assert result1 is True


class TestIRGraphOperations:
    """Property-based tests for IR graph operations."""

    @given(
        st.text(min_size=1, max_size=50),
        st.lists(
            node_id_strategy,
            max_size=10,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_graph_nodes_always_addable(
        self, graph_id: str, node_ids: list[str]
    ) -> None:
        """Test that nodes can always be added to graphs."""
        graph = IRGraph(
            graph_id=graph_id,
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        for node_id in node_ids:
            node = IRNode(
                node_id=node_id,
                node_type=IRNodeType.RESOURCE,
                name=f"node_{node_id}",
                source_type=SourceType.CHEF,
            )
            graph.add_node(node)

        assert len(graph.nodes) == len(node_ids)

    @given(st.lists(st.text(min_size=1, max_size=50), max_size=10, unique=True))
    @settings(max_examples=50)
    def test_graph_topological_order_always_succeeds_without_cycles(
        self, node_ids: list[str]
    ) -> None:
        """Test that topological order always succeeds without cycles."""
        if not node_ids:
            return

        graph = IRGraph(
            graph_id="topo-test",
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        for node_id in node_ids:
            node = IRNode(
                node_id=node_id,
                node_type=IRNodeType.RESOURCE,
                name=f"node_{node_id}",
                source_type=SourceType.CHEF,
            )
            graph.add_node(node)

        # Without adding dependencies, topological order should work
        order = graph.get_topological_order()
        assert len(order) == len(node_ids)
        assert set(order) == set(node_ids)

    @given(
        st.text(min_size=1, max_size=50),
        st.lists(
            node_id_strategy,
            min_size=2,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_graph_dependency_validation_always_returns_dict(
        self, graph_id: str, node_ids: list[str]
    ) -> None:
        """Test that dependency validation always returns a valid dict."""
        graph = IRGraph(
            graph_id=graph_id,
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        # Add first node
        node1 = IRNode(
            node_id=node_ids[0],
            node_type=IRNodeType.RESOURCE,
            name="first",
            source_type=SourceType.CHEF,
        )
        graph.add_node(node1)

        # Add node with unresolved dependency
        if len(node_ids) > 1:
            node2 = IRNode(
                node_id=node_ids[1],
                node_type=IRNodeType.RESOURCE,
                name="second",
                source_type=SourceType.CHEF,
            )
            node2.dependencies.append("nonexistent-node")
            graph.add_node(node2)

        # Validation should always return a dict
        result = graph.validate_dependencies()
        assert isinstance(result, dict)

    @given(
        st.text(min_size=1, max_size=50),
        st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.text(min_size=1, max_size=50),
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_graph_metadata_always_storable(
        self, graph_id: str, metadata: dict[str, str]
    ) -> None:
        """Test that metadata can be stored on graphs."""
        graph = IRGraph(
            graph_id=graph_id,
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        for key, value in metadata.items():
            graph.metadata[key] = value

        assert len(graph.metadata) == len(metadata)

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_graph_serialisation_always_succeeds(self, graph_id: str) -> None:
        """Test that graph serialisation always produces valid dict."""
        graph = IRGraph(
            graph_id=graph_id,
            source_type=SourceType.CHEF,
            target_type=TargetType.ANSIBLE,
            version="1.0.0",
        )

        data = graph.to_dict()

        assert isinstance(data, dict)
        assert "graph_id" in data
        assert "source_type" in data
        assert "target_type" in data
        assert "nodes" in data
