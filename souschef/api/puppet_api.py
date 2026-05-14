"""Puppet migration API facade."""

from souschef.orchestrators.puppet import (
    convert_puppet_manifest_to_ansible,
    convert_puppet_manifest_to_ansible_with_ai,
    convert_puppet_module_to_ansible,
    convert_puppet_module_to_ansible_with_ai,
    get_puppet_ansible_module_map,
    import_puppet_catalog_to_ir,
    list_puppet_server_nodes,
    parse_puppet_manifest,
    parse_puppet_module,
)

__all__ = [
    "convert_puppet_manifest_to_ansible",
    "convert_puppet_manifest_to_ansible_with_ai",
    "convert_puppet_module_to_ansible",
    "convert_puppet_module_to_ansible_with_ai",
    "get_puppet_ansible_module_map",
    "import_puppet_catalog_to_ir",
    "list_puppet_server_nodes",
    "parse_puppet_manifest",
    "parse_puppet_module",
]
