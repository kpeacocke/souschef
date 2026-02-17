"""Chef to Ansible converters."""

from souschef.converters.conversion_rules import (
    ConversionRule,
    RuleEngine,
    RulePriority,
    RuleType,
    build_default_rule_engine,
    create_custom_rule,
    create_package_rule,
    create_service_rule,
)
from souschef.converters.custom_module_generator import (
    analyse_resource_complexity,
    build_module_collection,
    extract_module_interface,
    generate_ansible_module_scaffold,
    generate_module_documentation,
    generate_module_manifest,
    validate_module_code,
)
from souschef.converters.habitat import (
    convert_habitat_to_dockerfile,
    generate_compose_from_habitat,
)
from souschef.converters.handler_generation import (
    build_handler_routing_table,
    detect_handler_patterns,
    generate_ansible_handler_from_chef,
    generate_handler_conversion_report,
    parse_chef_handler_class,
)
from souschef.converters.playbook import (
    analyse_chef_search_patterns,
    convert_chef_search_to_inventory,
    generate_dynamic_inventory_script,
    generate_playbook_from_recipe,
)
from souschef.converters.resource import convert_resource_to_task

__all__ = [
    "convert_resource_to_task",
    "generate_playbook_from_recipe",
    "convert_chef_search_to_inventory",
    "generate_dynamic_inventory_script",
    "analyse_chef_search_patterns",
    "convert_habitat_to_dockerfile",
    "generate_compose_from_habitat",
    "parse_chef_handler_class",
    "detect_handler_patterns",
    "generate_ansible_handler_from_chef",
    "build_handler_routing_table",
    "generate_handler_conversion_report",
    "analyse_resource_complexity",
    "extract_module_interface",
    "generate_ansible_module_scaffold",
    "generate_module_documentation",
    "generate_module_manifest",
    "validate_module_code",
    "build_module_collection",
    "ConversionRule",
    "RuleEngine",
    "RuleType",
    "RulePriority",
    "create_package_rule",
    "create_service_rule",
    "create_custom_rule",
    "build_default_rule_engine",
]
