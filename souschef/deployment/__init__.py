"""Deployment module for AWX/AAP integration and deployment strategies."""

from souschef.deployment import (
    analyze_chef_application_patterns,
    convert_chef_deployment_to_ansible_strategy,
    generate_awx_inventory_source_from_chef,
    generate_awx_job_template_from_cookbook,
    generate_awx_project_from_cookbooks,
    generate_awx_workflow_from_chef_runlist,
    generate_blue_green_deployment_playbook,
    generate_canary_deployment_strategy,
)

__all__ = [
    "generate_awx_job_template_from_cookbook",
    "generate_awx_workflow_from_chef_runlist",
    "generate_awx_project_from_cookbooks",
    "generate_awx_inventory_source_from_chef",
    "convert_chef_deployment_to_ansible_strategy",
    "generate_blue_green_deployment_playbook",
    "generate_canary_deployment_strategy",
    "analyze_chef_application_patterns",
]
