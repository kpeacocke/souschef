# SousChef MCP Server

AI-powered multi-platform to Ansible conversion and migration assistant.

## Overview

SousChef is a comprehensive MCP server that helps migrate Chef, SaltStack, Puppet, PowerShell, and Bash automation to Ansible playbooks and roles. It provides intelligent analysis, conversion, and validation capabilities for large-scale infrastructure-as-code migrations, plus Ansible upgrade planning.

## Features

- **Chef Migration**: Parse and analyse Chef cookbooks, recipes, attributes, and templates
- **SaltStack Migration**: Parse states/pillars/top files and convert to Ansible playbooks, roles, and inventory
- **Puppet Migration**: Convert `.pp` manifests and module directories to idiomatic Ansible playbooks
- **PowerShell Migration**: Convert Windows PowerShell provisioning scripts to `ansible.windows` automation
- **Bash Migration**: Convert provisioning Bash scripts to playbooks and reusable role structures
- **Intelligent Conversion**: Convert source resources to Ansible tasks with context awareness
- **Data Structure Mapping**: Convert Chef environments and data bags to Ansible inventory groups and variables
- **Compliance Testing**: Convert InSpec tests to Ansible testing playbooks
- **Migration Planning**: Generate detailed migration plans and effort assessments
- **Performance Profiling**: Analyse cookbook complexity and performance characteristics
- **Ansible Upgrade Planning**: Plan and validate Ansible version upgrades
- **CI/CD Pipeline Generation**: Create GitHub Actions, GitLab CI, and Jenkins pipelines
- **Comprehensive Reporting**: Generate detailed migration reports with findings and recommendations

## Documentation

For detailed usage instructions, API reference, and examples, visit the [SousChef Documentation](https://kpeacocke.github.io/souschef/).

## Configuration

The SousChef MCP server does not require any environment variables or secrets for basic operation. It works directly with Chef cookbook files provided to it.

## Examples

### Convert a Recipe to Ansible
The server can parse Chef recipes and convert them to Ansible task definitions:

```bash
convert_recipe_to_ansible /path/to/recipe.rb
```

### Assess Migration Complexity
Evaluate the effort required to migrate a cookbook:

```bash
assess_chef_migration_complexity /path/to/cookbook
```

### Generate Migration Plan
Create a detailed plan for migrating multiple cookbooks:

```bash
generate_migration_plan /path/to/cookbooks
```

## Tools

The SousChef MCP server provides a broad toolset for Chef, SaltStack, Puppet, PowerShell, Bash, and Ansible upgrade workflows:

- **Parsing Tools**: parse_recipe, parse_attributes, parse_template, parse_custom_resource, parse_habitat_plan, parse_inspec_profile, parse_salt_sls, parse_puppet_manifest, parse_bash_script, parse_powershell
- **Conversion Tools**: convert_resource_to_task, convert_cookbook_comprehensive, convert_all_cookbooks_comprehensive, convert_salt_to_ansible, convert_puppet_manifest_to_ansible, convert_bash_to_ansible, convert_powershell
- **Analysis Tools**: assess_chef_migration_complexity, analyse_cookbook_dependencies, analyse_chef_search_patterns
- **Validation Tools**: validate_conversion, validate_chef_server_connection, validate_ansible_collection_compatibility, analyze_powershell_fidelity
- **Planning Tools**: generate_migration_plan, generate_migration_report, plan_ansible_upgrade
- **Utilities**: list_directory, read_file, profile_cookbook_performance

## Requirements

- Python 3.10+
- Docker (for containerised deployment)
- Chef knowledge (for best results)

## License

MIT License - See LICENSE file in repository
