"""Orchestration helpers for Puppet migration UI flows."""

from __future__ import annotations

from typing import Any

import souschef.converters.puppet_to_ansible as puppet_to_ansible
import souschef.parsers.puppet as puppet_parser
from souschef.api_clients import PuppetServerClient
from souschef.ir import (
    IRAction,
    IRAttribute,
    IRGraph,
    IRMetadata,
    IRNode,
    IRNodeType,
    SourceType,
    TargetType,
)


def parse_puppet_manifest(manifest_path: str) -> str:
    """Parse a Puppet manifest for UI analysis."""
    return puppet_parser.parse_puppet_manifest(manifest_path)


def parse_puppet_module(module_path: str) -> str:
    """Parse a Puppet module for UI analysis."""
    return puppet_parser.parse_puppet_module(module_path)


def convert_puppet_manifest_to_ansible(manifest_path: str) -> str:
    """Convert a Puppet manifest to Ansible YAML."""
    return puppet_to_ansible.convert_puppet_manifest_to_ansible(manifest_path)


def convert_puppet_module_to_ansible(module_path: str) -> str:
    """Convert a Puppet module to Ansible YAML."""
    return puppet_to_ansible.convert_puppet_module_to_ansible(module_path)


def convert_puppet_manifest_to_ansible_with_ai(
    manifest_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """Convert a Puppet manifest to Ansible YAML using AI assistance."""
    return puppet_to_ansible.convert_puppet_manifest_to_ansible_with_ai(
        manifest_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        base_url=base_url,
    )


def convert_puppet_module_to_ansible_with_ai(
    module_path: str,
    ai_provider: str = "anthropic",
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.3,
    max_tokens: int = 4000,
    project_id: str = "",
    base_url: str = "",
) -> str:
    """Convert a Puppet module to Ansible YAML using AI assistance."""
    return puppet_to_ansible.convert_puppet_module_to_ansible_with_ai(
        module_path,
        ai_provider=ai_provider,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        project_id=project_id,
        base_url=base_url,
    )


def get_puppet_ansible_module_map() -> dict[str, str]:
    """Return the Puppet to Ansible module mapping for UI display."""
    return puppet_to_ansible.get_puppet_ansible_module_map()


def _resource_node_type(resource_type: str) -> tuple[IRNodeType, bool]:
    """Map a Puppet resource type to an IR node type and review flag."""
    mapping = {
        "package": IRNodeType.PACKAGE,
        "service": IRNodeType.SERVICE,
        "file": IRNodeType.FILE,
        "user": IRNodeType.USER,
        "group": IRNodeType.GROUP,
    }
    normalised = resource_type.lower()
    if normalised in mapping:
        return mapping[normalised], False
    return IRNodeType.CUSTOM, True


def _catalog_resource_id(resource: dict[str, Any]) -> str:
    """Build a stable identifier for a compiled catalog resource."""
    return (
        f"{str(resource.get('type', 'unknown')).lower()}::"
        f"{resource.get('title', 'unknown')}"
    )


def _add_catalog_edges(graph: IRGraph, edges: list[dict[str, Any]]) -> None:
    """Translate catalog edges into IR dependencies."""
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, dict) or not isinstance(target, dict):
            continue
        source_id = _catalog_resource_id(source)
        target_id = _catalog_resource_id(target)
        target_node = graph.get_node(target_id)
        if target_node is not None and graph.get_node(source_id) is not None:
            target_node.add_dependency(source_id)


def _build_catalog_fidelity_report(resources: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a fidelity report for Puppet catalog imports."""
    mapped_resources = 0
    review_required = 0
    resource_types: dict[str, int] = {}

    for resource in resources:
        resource_type = str(resource.get("type", "unknown")).lower()
        _, needs_review = _resource_node_type(resource_type)
        resource_types[resource_type] = resource_types.get(resource_type, 0) + 1
        if needs_review:
            review_required += 1
        else:
            mapped_resources += 1

    total_resources = len(resources)
    coverage_percent = (
        100.0
        if total_resources == 0
        else round(
            (mapped_resources / total_resources) * 100,
            2,
        )
    )
    return {
        "total_resources": total_resources,
        "mapped_resources": mapped_resources,
        "review_required": review_required,
        "coverage_percent": coverage_percent,
        "resource_types": resource_types,
    }


def list_puppet_server_nodes(
    server_url: str,
    cert_path: str,
    key_path: str,
    environment: str = "",
    ca_path: str = "",
) -> dict[str, Any]:
    """List Puppet nodes for node selection in connector workflows."""
    client = PuppetServerClient(
        server_url=server_url,
        cert_path=cert_path,
        key_path=key_path,
        ca_path=ca_path or None,
    )
    nodes = client.list_nodes(environment=environment)
    node_names = [str(node.get("name", "")) for node in nodes if node.get("name")]
    return {
        "status": "success",
        "environment": environment,
        "count": len(node_names),
        "nodes": sorted(node_names),
    }


def import_puppet_catalog_to_ir(
    server_url: str,
    cert_path: str,
    key_path: str,
    node_name: str,
    environment: str = "",
    ca_path: str = "",
) -> dict[str, Any]:
    """Fetch a compiled Puppet catalog and map it to the shared IR."""
    client = PuppetServerClient(
        server_url=server_url,
        cert_path=cert_path,
        key_path=key_path,
        ca_path=ca_path or None,
    )
    catalog = client.get_catalog(node_name=node_name, environment=environment)
    resources = [
        resource
        for resource in catalog.get("resources", [])
        if isinstance(resource, dict)
    ]
    graph = IRGraph(
        graph_id=f"puppet-catalog::{node_name}",
        source_type=SourceType.PUPPET,
        target_type=TargetType.ANSIBLE,
        version="1.0.0",
    )

    for resource in resources:
        resource_type = str(resource.get("type", "custom"))
        node_type, needs_review = _resource_node_type(resource_type)
        metadata = IRMetadata(
            source_type=SourceType.PUPPET,
            source_file=str(resource.get("file", "catalog")),
            source_line=int(resource.get("line") or 0),
            original_id=str(resource.get("title", "unnamed")),
            requires_review=needs_review,
            notes=["Imported from Puppet compiled catalog"],
        )
        node = IRNode(
            node_id=_catalog_resource_id(resource),
            node_type=node_type,
            name=str(resource.get("title", "unnamed")),
            source_type=SourceType.PUPPET,
            metadata=metadata,
        )
        parameters = resource.get("parameters", {})
        if isinstance(parameters, dict):
            for key, value in parameters.items():
                node.add_attribute(str(key), IRAttribute(name=str(key), value=value))
        node.add_action(
            IRAction(
                name=f"catalog::{resource_type.lower()}",
                type=resource_type.lower(),
                metadata=metadata,
            )
        )
        graph.add_node(node)

    edges = [edge for edge in catalog.get("edges", []) if isinstance(edge, dict)]
    _add_catalog_edges(graph, edges)
    ir_payload = graph.to_dict()
    ir_payload["edges"] = edges
    return {
        "status": "success",
        "node": node_name,
        "environment": environment,
        "ir": ir_payload,
        "fidelity_report": _build_catalog_fidelity_report(resources),
    }
