# Chef to Ansible migration - SousChef MCP 

An AI-powered MCP (Model Context Protocol) server that provides comprehensive Chef-to-Ansible migration capabilities for enterprise infrastructure transformation.

[![PyPI version](https://img.shields.io/pypi/v/mcp-souschef.svg)](https://pypi.org/project/mcp-souschef/)
[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen.svg)](htmlcov/index.html)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)

## Overview - Chef to Ansible features

SousChef is a complete enterprise-grade migration platform with 38 MCP tools organized across 9 major capability areas to facilitate Chef-to-Ansible AWX/AAP migrations. From cookbook analysis to deployment pattern conversion, including Chef Habitat to containerized deployments, SousChef provides everything needed for a successful infrastructure automation migration.

## Model Agnostic - Works with Any AI Model

**SousChef works with ANY AI model through the Model Context Protocol (MCP)**. The MCP architecture separates tools from models:

- **Red Hat AI** (Llama, IBM models)
- **Claude** (Anthropic)
- **GPT-4/GPT-3.5** (OpenAI)
- **GitHub Copilot** (Microsoft/OpenAI)
- **Local Models** (Ollama, llama.cpp, etc.)
- **Custom Enterprise Models**

**How it works:** You choose your AI model provider in your MCP client. SousChef provides the Chef/Ansible expertise through 38 specialized tools. The model calls these tools to help with your migration.

> See [config/CONFIGURATION.md](config/CONFIGURATION.md) for configuration examples with different model providers.

## Installation

```bash
# PyPI Installation
pip install mcp-souschef

# Development Installation
git clone https://github.com/kpeacocke/souschef.git
cd souschef
poetry install
```

> **For detailed installation instructions, MCP setup, and configuration, see [Installation & Setup](#installation--setup)**

## Core Capabilities

### 1. Chef Cookbook Analysis & Parsing
Complete cookbook introspection and analysis tools:

- **parse_template** - Parse ERB templates with Jinja2 conversion and variable extraction
- **parse_custom_resource** - Extract properties, attributes, and actions from custom resources and LWRPs
- **list_directory** - Navigate and explore cookbook directory structures
- **read_file** - Read cookbook files with error handling
- **read_cookbook_metadata** - Parse metadata.rb files for dependencies and cookbook information
- **parse_recipe** - Analyze Chef recipes and extract resources, actions, and properties
- **parse_attributes** - Parse attribute files with **advanced precedence resolution** (6 levels: default, force_default, normal, override, force_override, automatic)
- **list_cookbook_structure** - Display complete cookbook directory hierarchy

### 2. Chef-to-Ansible Conversion Engine
Advanced resource-to-task conversion with intelligent module selection:

- **convert_resource_to_task** - Transform individual Chef resources to Ansible tasks
- **generate_playbook_from_recipe** - Generate complete Ansible playbooks from Chef recipes
- **Enhanced Guard Handling** - Convert complex Chef guards to Ansible when/unless conditions
  - Array-based guards: `only_if ['condition1', 'condition2']`
  - Lambda/proc syntax: `only_if { ::File.exist?('/path') }`
  - Do-end blocks: `not_if do ... end`
  - Multiple guard types per resource with proper AND/OR logic
  - Platform checks, node attributes, file/directory existence, and command execution

### 3. Chef Search & Inventory Integration
Convert Chef search patterns to dynamic Ansible inventory:

- **convert_chef_search_to_inventory** - Transform Chef search queries to Ansible inventory groups
- **generate_dynamic_inventory_script** - Create dynamic inventory scripts from Chef server queries
- **analyze_chef_search_patterns** - Discover and analyze search usage in cookbooks

### 4. InSpec Integration & Validation
Complete InSpec-to-Ansible testing pipeline:

- **parse_inspec_profile** - Parse InSpec profiles and extract controls
- **convert_inspec_to_test** - Convert InSpec controls to Testinfra or Ansible assert tasks
- **generate_inspec_from_recipe** - Auto-generate InSpec validation from Chef recipes

### 5. Data Bags & Secrets Management
Chef data bags to Ansible vars/vault conversion:

- **convert_chef_databag_to_vars** - Transform data bags to Ansible variable files
- **generate_ansible_vault_from_databags** - Convert encrypted data bags to Ansible Vault
- **analyze_chef_databag_usage** - Analyze data bag usage patterns in cookbooks

### 6. Environment & Configuration Management
Chef environments to Ansible inventory groups:

- **convert_chef_environment_to_inventory_group** - Transform Chef environments to inventory
- **generate_inventory_from_chef_environments** - Generate complete inventory from environments
- **analyze_chef_environment_usage** - Analyze environment usage in cookbooks

### 7. AWX/Ansible Automation Platform Integration
Enterprise AWX/AAP configuration generation:

- **generate_awx_job_template_from_cookbook** - Create AWX job templates from cookbooks
- **generate_awx_workflow_from_chef_runlist** - Transform Chef run-lists to AWX workflows
- **generate_awx_project_from_cookbooks** - Generate AWX projects from cookbook collections
- **generate_awx_inventory_source_from_chef** - Create dynamic inventory sources from Chef server

### 8. Chef Habitat to Container Conversion
Modernize Habitat applications to containerized deployments:

- **parse_habitat_plan** - Parse Chef Habitat plan files (plan.sh) and extract package metadata, dependencies, build/install hooks, and service configuration
- **convert_habitat_to_dockerfile** - Convert Chef Habitat plans to production-ready Dockerfiles with security validation
- **generate_compose_from_habitat** - Generate docker-compose.yml from multiple Habitat plans for multi-service deployments

### 9. Advanced Deployment Patterns & Migration Assessment
Modern deployment strategies and migration planning:

- **convert_chef_deployment_to_ansible_strategy** - Convert deployment recipes to Ansible strategies
- **generate_blue_green_deployment_playbook** - Create blue/green deployment playbooks
- **generate_canary_deployment_strategy** - Generate canary deployment configurations

### 10. Conversion Validation Framework
Comprehensive validation of Chef-to-Ansible conversions:

- **validate_conversion** - Validate conversions across multiple dimensions
  - **Syntax Validation**: YAML, Jinja2, Python syntax checking
  - **Semantic Validation**: Logic equivalence, variable usage, resource dependencies
  - **Best Practice Checks**: Naming conventions, idempotency, task organization
  - **Security Validation**: Privilege escalation patterns, sensitive data handling
  - **Performance Recommendations**: Efficiency suggestions and optimizations

#### Validation Levels
- **ERROR**: Critical issues that will prevent execution
- **WARNING**: Potential problems or anti-patterns that may cause issues
- **INFO**: Suggestions for improvements and best practices

#### Validation Categories
- **Syntax**: Code structure and syntax correctness
- **Semantic**: Logical equivalence and meaning preservation
- **Best Practice**: Ansible community standards and patterns
- **Security**: Security considerations and recommendations
- **Performance**: Efficiency and optimization suggestions

#### Example Usage

```python
# Validate a resource conversion
validate_conversion(
    conversion_type="resource",
    result_content="""- name: Install nginx
  ansible.builtin.package:
    name: "nginx"
    state: present
""",
    output_format="text"  # Options: text, json, summary
)
```

Output formats:
- **text**: Detailed report with all findings grouped by severity
- **json**: Structured JSON for programmatic processing
- **summary**: Quick overview with counts only

- **analyze_chef_application_patterns** - Identify application deployment patterns
- **assess_chef_migration_complexity** - Comprehensive migration complexity assessment
- **generate_migration_plan** - Create detailed migration execution plans
- **analyze_cookbook_dependencies** - Analyze dependencies and migration order
- **generate_migration_report** - Generate executive and technical migration reports

## Migration Workflow

### Phase 1: Discovery & Assessment
```bash
# Assess migration complexity
assess_chef_migration_complexity /path/to/cookbooks

# Analyze cookbook dependencies
analyze_cookbook_dependencies /path/to/cookbook

# Generate migration plan
generate_migration_plan '{\"cookbooks\": [\"/path/to/cookbook1\", \"/path/to/cookbook2\"]}'
```

### Phase 2: Content Conversion
```bash
# Convert recipes to playbooks
generate_playbook_from_recipe /path/to/recipe.rb

# Convert data bags to Ansible Vault
generate_ansible_vault_from_databags /path/to/databags

# Convert environments to inventory
generate_inventory_from_chef_environments /path/to/environments
```

### Phase 3: AWX/AAP Integration
```bash
# Generate AWX job templates
generate_awx_job_template_from_cookbook /path/to/cookbook cookbook_name

# Create AWX workflows from run-lists
generate_awx_workflow_from_chef_runlist \"recipe[app::deploy]\" workflow_name

# Setup dynamic inventory from Chef server
generate_awx_inventory_source_from_chef https://chef.example.com production web_servers
```

### Phase 4: Habitat to Container Migration
```bash
# Parse Habitat plan
parse_habitat_plan /path/to/plan.sh

# Convert to Dockerfile
convert_habitat_to_dockerfile /path/to/plan.sh ubuntu:22.04

# Generate docker-compose for multiple services
generate_compose_from_habitat "/path/to/plan1.sh,/path/to/plan2.sh" my_network
```

### Phase 5: Validation & Testing
```bash
# Generate InSpec validation
generate_inspec_from_recipe /path/to/recipe.rb

# Convert existing InSpec to Ansible tests
convert_inspec_to_test /path/to/inspec_profile testinfra
```

## Enterprise Features

### Migration Assessment & Reporting
- **Complexity Analysis**: Automated assessment of migration effort and risk factors
- **Dependency Mapping**: Complete cookbook dependency analysis with migration ordering
- **Impact Analysis**: Resource usage patterns and conversion recommendations
- **Executive Reports**: Stakeholder-ready migration reports with timelines and costs

### Modern Deployment Patterns
- **Blue/Green Deployments**: Zero-downtime deployment strategies
- **Canary Releases**: Gradual rollout configurations
- **Application Patterns**: Modern containerized and cloud-native deployment patterns
- **Rollback Strategies**: Automated failure recovery procedures
- **Habitat to Container**: Convert Chef Habitat plans to Docker and Docker Compose configurations

### Enterprise Integration
- **AWX/AAP Ready**: Native Ansible Automation Platform integration
- **Dynamic Inventory**: Chef server integration for hybrid environments
- **Secrets Management**: Secure data bag to Vault conversion
- **Multi-Environment**: Production-ready inventory and variable management

## Installation & Setup

### Prerequisites
- Python 3.14+
- [Poetry](https://python-poetry.org/) for dependency management
- MCP-compatible client (Claude Desktop, VS Code with MCP extension, etc.)

### Quick Start

1. **Install SousChef**:
   ```bash
   pip install mcp-souschef
   ```

2. **Configure Your MCP Client**:

   Use the pre-configured files in the `config/` directory for quick setup with Claude Desktop, VS Code Copilot, or other MCP clients.

   ```bash
   # Example: Claude Desktop (macOS)
   cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

   ** See [config/CONFIGURATION.md](config/CONFIGURATION.md) for:**
   - Platform-specific setup (macOS/Linux/Windows)
   - Model provider configurations (Red Hat AI, OpenAI, local models)
   - Development setup
   - Troubleshooting

3. **Start Using SousChef**:
   - Restart your MCP client
   - Ask: "What Chef migration tools are available?"
   - Begin analyzing your cookbooks!

### Command Line Interface (CLI)

SousChef includes a standalone CLI for direct cookbook parsing and conversion:

```bash
# Basic usage examples
souschef-cli --help
souschef-cli recipe /path/to/recipe.rb
souschef-cli template /path/to/template.erb
souschef-cli convert package nginx --action install
souschef-cli cookbook /path/to/cookbook

# Parse and convert with output formats
souschef-cli recipe recipe.rb --format json
souschef-cli inspec-generate recipe.rb > validation.rb
souschef-cli inspec-convert controls.rb --format testinfra
```

**Available Commands:**
- `recipe` - Parse Chef recipe files and extract resources
- `template` - Convert ERB templates to Jinja2 with variable extraction
- `resource` - Parse custom resources and LWRPs
- `attributes` - Extract Chef attribute definitions
- `metadata` - Parse cookbook metadata.rb files
- `structure` - Display cookbook directory structure
- `convert` - Convert Chef resources to Ansible tasks
- `cookbook` - Comprehensive cookbook analysis
- `inspec-parse` - Parse InSpec profiles and controls
- `inspec-convert` - Convert InSpec to Testinfra/Ansible tests
- `inspec-generate` - Generate InSpec validation from recipes
- `ls` / `cat` - File system operations

### Development Setup

```bash
# Install dependencies
poetry install

# Install pre-commit hooks (one-time - auto-handles poetry.lock)
poetry run pre-commit install

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=souschef --cov-report=html

# Lint and format
poetry run ruff check .
poetry run ruff format .

# Type check
poetry run mypy souschef
```

### **Dependency Management**

Poetry manages dependencies with **automatic lock file synchronization**:

```bash
# Add dependencies
poetry add package-name              # Production
poetry add --group dev package-name  # Development

# Update lock file after manual pyproject.toml edits
poetry lock  # Poetry 2.x preserves versions automatically

# Update dependencies
poetry update package-name  # Specific package
poetry update              # All packages
```

**Automated Systems:**
-  Pre-commit hooks auto-update `poetry.lock` when `pyproject.toml` changes
-  CI validates lock file on every PR
-  Dependabot sends weekly dependency updates

See [CONTRIBUTING.md](CONTRIBUTING.md#-managing-dependencies) for detailed dependency management guide.

## Architecture & Design

### MCP Protocol Integration
SousChef leverages the Model Context Protocol (MCP) to provide seamless integration with AI assistants and development environments:

- **38 Specialized Tools**: Each migration capability exposed as dedicated MCP tool
- **Type-Safe Interfaces**: Full Python type hints for reliable AI interactions
- **Comprehensive Error Handling**: Graceful degradation and helpful error messages
- **Streaming Support**: Efficient handling of large cookbook conversions

### Testing Strategy
Following enterprise-grade testing standards with comprehensive test coverage:

- **Unit Tests**: Mock-based testing for individual functions (test_server.py, test_cli.py, test_mcp.py)
- **Integration Tests**: Real cookbook testing with fixtures (test_integration.py, test_integration_accuracy.py)
- **Property-Based Tests**: Hypothesis fuzz testing for edge cases (test_property_based.py)
- **Specialized Tests**: Enhanced guards (test_enhanced_guards.py), error handling (test_error_paths.py, test_error_recovery.py), real-world fixtures (test_real_world_fixtures.py)
- **Performance Tests**: Benchmarking and optimization validation (test_performance.py)
- **Snapshot Tests**: Regression testing for output stability (test_snapshots.py)
- **92% Coverage**: Comprehensive test coverage exceeding the 90% target for production readiness

### Quality Assurance
- **Zero Warnings Policy**: All code passes linting without disabling checks
- **Type Safety**: Complete type annotations throughout the codebase
- **Automated Testing**: CI/CD pipeline with comprehensive test suites
- **Documentation**: Detailed docstrings and usage examples

## Documentation

### Tool Reference
Each MCP tool includes comprehensive documentation:
- Purpose and use cases
- Parameter descriptions and types
- Return value specifications
- Usage examples and patterns
- Error handling behaviors

### Migration Guides
- **[Enterprise Migration Guide](docs/enterprise-migration.md)** - Complete methodology for large-scale migrations
- **[AWX Integration Guide](docs/awx-integration.md)** - Step-by-step AWX/AAP setup and configuration
- **[Testing Strategy Guide](docs/testing-strategy.md)** - Validation and testing approaches
- **[Best Practices](docs/best-practices.md)** - Recommended patterns and approaches

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup and workflow
- Code style and testing requirements
- Pull request process
- Issue reporting guidelines

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

### Completed 
-  Complete Chef cookbook parsing (recipes, attributes, metadata, templates)
-  InSpec profile parsing and conversion to Testinfra/Ansible tests
-  Chef resource to Ansible task conversion with module mapping
-  Data bags to Ansible Vault conversion
-  Chef environments to Ansible inventory conversion
-  Chef search patterns to dynamic inventory conversion
-  AWX/AAP job templates, workflows, and project generation
-  Blue/green and canary deployment pattern generation
-  Migration complexity assessment and planning tools
-  Comprehensive testing suite (unit, integration, property-based)
-  Command-line interface (CLI) for standalone usage
-  Enhanced Chef guard handling (arrays, lambda syntax, complex nested conditions)
-  Advanced attribute precedence resolution (6 levels with conflict detection)
-  Automated release management with Release Please
-  Automated branch cleanup for release PRs
-  Automated conversion validation and testing framework
-  Chef Habitat to containerized deployment conversion (parse_habitat_plan, convert_habitat_to_dockerfile, generate_compose_from_habitat)

### In Progress 
-  Enhanced error handling and user experience improvements
-  Documentation website and interactive examples
-  Performance optimizations for large-scale enterprise migrations
-  Technical debt reduction (15 functions tracked in [GitHub Issues](https://github.com/kpeacocke/souschef/issues?q=is%3Aissue+is%3Aopen+label%3Atechnical-debt))

### Planned 📅
- 📅 Integration with additional test frameworks (ServerSpec, Goss)
- 📅 Visual migration planning and dependency mapping interface
- 📅 Terraform provider for infrastructure state management
- 📅 Jenkins/GitLab CI pipeline generation

## 🙋‍♀️ Support & Community

- **Issues**: [GitHub Issues](https://github.com/kpeacocke/souschef/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- **Documentation**: [Wiki](https://github.com/kpeacocke/souschef/wiki)

---

**SousChef** - *Transforming infrastructure automation, one recipe at a time.* ✨
  desc 'Ensure package nginx is properly configured'
  impact 1.0

  describe package('nginx') do
    it { should be_installed }
  end
end

control 'service-nginx' do
  title 'Verify service nginx'
  desc 'Ensure service nginx is properly configured'
  impact 1.0

  describe service('nginx') do
    it { should be_running }
    it { should be_enabled }
  end
end

control 'template--etc-nginx-nginx.conf' do
  title 'Verify template /etc/nginx/nginx.conf'
  desc 'Ensure template /etc/nginx/nginx.conf is properly configured'
  impact 1.0

  describe file('/etc/nginx/nginx.conf') do
    it { should exist }
    its('mode') { should cmp '0644' }
    its('owner') { should eq 'root' }
    its('group') { should eq 'root' }
  end
end
```

#### Testinfra Integration

Convert to Python tests for CI/CD pipelines:

```bash
souschef-cli inspec-convert validation-controls.rb --format testinfra
```

```python
import pytest

def test_package_nginx(host):
    """Ensure package nginx is properly configured"""
    pkg = host.package("nginx")
    assert pkg.is_installed

def test_service_nginx(host):
    """Ensure service nginx is properly configured"""
    svc = host.service("nginx")
    assert svc.is_running
    assert svc.is_enabled

def test_template_etc_nginx_nginx_conf(host):
    """Ensure template /etc/nginx/nginx.conf is properly configured"""
    f = host.file("/etc/nginx/nginx.conf")
    assert f.exists
    assert oct(f.mode) == "0644"
    assert f.user == "root"
    assert f.group == "root"
```

#### Ansible Assert Integration

For Ansible playbook validation:

```bash
souschef-cli inspec-convert validation-controls.rb --format ansible_assert
```

```yaml
---
# Validation tasks converted from InSpec

- name: Verify package nginx
  ansible.builtin.assert:
    that:
      - ansible_facts.packages['nginx'] is defined
    fail_msg: "Ensure package nginx is properly configured validation failed"

- name: Verify service nginx
  ansible.builtin.assert:
    that:
      - services['nginx'].state == 'running'
      - services['nginx'].status == 'enabled'
    fail_msg: "Ensure service nginx is properly configured validation failed"
```

#### Benefits

- **Consistency Validation** - Ensure Chef and Ansible produce identical infrastructure state
- **AI Context Enhancement** - InSpec profiles help AI understand infrastructure intent
- **Automated Testing** - Generate tests automatically from Chef recipes
- **Multiple Test Formats** - Support for InSpec, Testinfra, and Ansible assert
- **CI/CD Integration** - Easy integration with existing test pipelines

### As an MCP Server

SousChef is designed to be used as an MCP server with AI assistants that support the Model Context Protocol.

#### Configure with Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "souschef": {
      "command": "poetry",
      "args": [
        "-C",
        "/path/to/souschef",
        "run",
        "souschef"
      ]
    }
  }
}
```

### Available Tools

#### `list_directory(path: str)`
List the contents of a directory.

**Example:**
```python
list_directory("/path/to/cookbooks")
# Returns: ['nginx', 'apache2', 'mysql']
```

#### `read_file(path: str)`
Read the contents of a file.

**Example:**
```python
read_file("/path/to/cookbook/recipes/default.rb")
# Returns: file contents as string
```

#### `read_cookbook_metadata(path: str)`
Parse Chef cookbook metadata.rb file.

**Example:**
```python
read_cookbook_metadata("/path/to/cookbook/metadata.rb")
# Returns:
# name: nginx
# maintainer: Chef Software, Inc.
# version: 8.0.0
# depends: logrotate, iptables
```

#### `parse_recipe(path: str)`
Parse a Chef recipe file and extract resources.

**Example:**
```python
parse_recipe("/path/to/cookbook/recipes/default.rb")
# Returns:
# Resource 1:
#   Type: package
#   Name: nginx
#   Action: install
```

#### `parse_attributes(path: str, resolve_precedence: bool = True)`
Parse a Chef attributes file and extract attribute definitions with precedence analysis.

**Chef Attribute Precedence** (lowest to highest):
1. `default` - Normal default value
2. `force_default` - Forced default, higher than regular default
3. `normal` - Normal attribute set by cookbook
4. `override` - Override values
5. `force_override` - Forced override, cannot be overridden
6. `automatic` - Automatically detected by Ohai (highest precedence)

When multiple attributes with the same path exist at different precedence levels, the highest precedence wins. The tool automatically resolves conflicts and reports which values were overridden.

**Parameters:**
- `path`: Path to the attributes (.rb) file
- `resolve_precedence`: If True (default), resolves conflicts and shows only winning values. If False, shows all attributes.

**Example:**
```python
# With precedence resolution (default)
parse_attributes("/path/to/cookbook/attributes/default.rb")
# Returns:
# Resolved Attributes (with precedence):
# ==================================================
#
# Attribute: nginx.port
#   Value: 443
#   Precedence: force_override (level 5)
#     Overridden values: default=80, normal=8080
#
# Attribute: nginx.ssl_port
#   Value: 443
#   Precedence: default (level 1)
#
# ==================================================
# Total attributes: 2
# Attributes with precedence conflicts: 1

# Without precedence resolution (show all)
parse_attributes("/path/to/cookbook/attributes/default.rb", resolve_precedence=False)
# Returns:
# default[nginx.port] = 80
# normal[nginx.port] = 8080
# force_override[nginx.port] = 443
# default[nginx.ssl_port] = 443
```

**Use Cases:**
- Understanding attribute conflicts in complex cookbooks
- Debugging which attributes will actually be applied
- Planning attribute migrations to Ansible variables
- Identifying force_override attributes that need special handling

#### `list_cookbook_structure(path: str)`
List the structure of a Chef cookbook directory.

**Example:**
```python
list_cookbook_structure("/path/to/cookbook")
# Returns:
# recipes/
#   default.rb
#   install.rb
# attributes/
#   default.rb
# metadata/
#   metadata.rb
```

#### `parse_template(path: str)`
Parse a Chef ERB template file and convert it to Jinja2 format.

**Example:**
```python
parse_template("/path/to/cookbook/templates/default/nginx.conf.erb")
# Returns JSON with:
# {
#   "original_file": "/path/to/cookbook/templates/default/nginx.conf.erb",
#   "variables": [
#     "nginx']['port",
#     "nginx']['server_name",
#     "nginx']['ssl_enabled"
#   ],
#   "jinja2_template": "server {\n  listen {{ nginx']['port }};\n  {% if nginx']['ssl_enabled %}\n  ssl on;\n  {% endif %}\n}"
# }
```

**ERB to Jinja2 Conversion:**
- Variable output: `<%= var %>` → `{{ var }}`
- Instance variables: `<%= @var %>` → `{{ var }}`
- Node attributes: `<%= node['attr'] %>` → `{{ attr }}`
- Conditionals: `<% if cond %>` → `{% if cond %}`
- Unless: `<% unless cond %>` → `{% if not cond %}`
- Elsif: `<% elsif cond %>` → `{% elif cond %}`
- Else: `<% else %>` → `{% else %}`
- Loops: `<% arr.each do |item| %>` → `{% for item in arr %}`
- End blocks: `<% end %>` → `{% endif %}` or `{% endfor %}`

#### `parse_custom_resource(path: str)`
Parse a Chef custom resource or LWRP file and extract properties, attributes, and actions.

**Example:**
```python
parse_custom_resource("/path/to/cookbook/resources/app_config.rb")
# Returns JSON with:
# {
#   "resource_file": "/path/to/cookbook/resources/app_config.rb",
#   "resource_name": "app_config",
#   "resource_type": "custom_resource",  # or "lwrp"
#   "properties": [
#     {
#       "name": "config_name",
#       "type": "String",
#       "name_property": true
#     },
#     {
#       "name": "port",
#       "type": "Integer",
#       "default": "8080"
#     },
#     {
#       "name": "ssl_enabled",
#       "type": "[true, false]",
#       "default": "false"
#     }
#   ],
#   "actions": ["create", "delete"],
#   "default_action": "create"
# }
```

**Detected Resource Types:**
- **Custom Resource** (modern) - Uses `property` keyword
- **LWRP** (legacy) - Uses `attribute` keyword with `kind_of:`

**Property/Attribute Fields:**
- `name` - Property/attribute name
- `type` - Type constraint (String, Integer, Boolean, Array, Hash, etc.)
- `name_property` - Whether this is the resource's name property (true/false)
- `default` - Default value if specified
- `required` - Whether the property is required (true/false)

**Action Extraction:**
- Modern format: `action :name do ... end`
- LWRP format: `actions :create, :delete, :update`
- Supports both formats and mixed declarations

#### `convert_resource_to_task(resource_type: str, resource_name: str, action: str = "create", properties: str = "")`
Convert a Chef resource to an Ansible task.

**Example:**
```python
convert_resource_to_task("package", "nginx", "install")
# Returns:
# - name: Install package nginx
#   ansible.builtin.package:
#     name: "nginx"
#     state: "present"

convert_resource_to_task("service", "nginx", "start")
# Returns:
# - name: Start service nginx
#   ansible.builtin.service:
#     name: "nginx"
#     enabled: true
#     state: "started"

convert_resource_to_task("template", "/etc/nginx/nginx.conf.erb", "create")
# Returns:
# - name: Create template /etc/nginx/nginx.conf.erb
#   ansible.builtin.template:
#     src: "/etc/nginx/nginx.conf.erb"
#     dest: "/etc/nginx/nginx.conf"
#     mode: "0644"
```

**Supported Resource Types:**
- `package` → `ansible.builtin.package`
- `service` → `ansible.builtin.service`
- `template` → `ansible.builtin.template`
- `file` → `ansible.builtin.file`
- `directory` → `ansible.builtin.file` (with state: directory)
- `execute` → `ansible.builtin.command`
- `bash` → `ansible.builtin.shell`
- `user` → `ansible.builtin.user`
- `group` → `ansible.builtin.group`
- And more...

#### `parse_habitat_plan(plan_path: str)`
Parse a Chef Habitat plan file (plan.sh) and extract package metadata, dependencies, build/install hooks, and service configuration.

**Example:**
```python
parse_habitat_plan("/path/to/habitat/plan.sh")
# Returns JSON with:
# {
#   "package": {
#     "name": "nginx",
#     "origin": "core",
#     "version": "1.25.3",
#     "maintainer": "The Habitat Maintainers",
#     "description": "High-performance HTTP server"
#   },
#   "dependencies": {
#     "build": ["core/gcc", "core/make"],
#     "runtime": ["core/glibc", "core/openssl"]
#   },
#   "ports": [
#     {"name": "http", "value": "http.port"},
#     {"name": "https", "value": "http.ssl_port"}
#   ],
#   "binds": [
#     {"name": "database", "value": "postgresql.default"}
#   ],
#   "service": {
#     "run": "nginx -g 'daemon off;'",
#     "user": "nginx"
#   },
#   "callbacks": {
#     "do_build": "./configure --prefix=/usr/local\nmake",
#     "do_install": "make install",
#     "do_init": "mkdir -p /var/lib/nginx"
#   }
# }
```

**Extracted Information:**
- **Package metadata**: name, origin, version, maintainer, description
- **Dependencies**: Build-time and runtime package dependencies
- **Ports**: Exported port configurations for service discovery
- **Binds**: Service bindings to other Habitat services
- **Service configuration**: Run command, user, and initialization scripts
- **Build callbacks**: do_build, do_install, do_init, and other lifecycle hooks

**Use Cases:**
- Understanding Habitat application structure before containerization
- Extracting dependencies for Docker base image selection
- Planning port mappings for docker-compose configurations
- Analyzing service dependencies and orchestration needs

#### `convert_habitat_to_dockerfile(plan_path: str, base_image: str = "ubuntu:22.04")`
Convert a Chef Habitat plan to a production-ready Dockerfile with security validation.

**Example:**
```python
convert_habitat_to_dockerfile("/path/to/habitat/plan.sh", "ubuntu:22.04")
# Returns:
# # Dockerfile generated from Habitat plan
# # Original plan: plan.sh
# # Package: core/nginx
# # Version: 1.25.3
#
# FROM ubuntu:22.04
#
# LABEL maintainer="The Habitat Maintainers"
# LABEL version="1.25.3"
#
# # Install dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     make \
#     libssl-dev \
#     && rm -rf /var/lib/apt/lists/*
#
# # Build steps
# WORKDIR /usr/local/src
# RUN ./configure --prefix=/usr/local && \
#     make
#
# # Install steps
# RUN make install
#
# # Initialization steps
# RUN mkdir -p /var/lib/nginx
#
# # Runtime configuration
# EXPOSE 80
# EXPOSE 443
# USER nginx
# WORKDIR /usr/local
#
# CMD ["nginx", "-g", "daemon off;"]
```

**Parameters:**
- `plan_path`: Path to the Habitat plan.sh file
- `base_image`: Docker base image (default: ubuntu:22.04). Validated for security

**Features:**
- **Dependency mapping**: Converts Habitat dependencies to apt packages
- **Build optimization**: Multi-stage builds when applicable
- **Security scanning**: Detects dangerous patterns (curl|sh, eval, etc.)
- **Metadata preservation**: LABEL instructions for package info
- **User configuration**: Non-root user setup when specified
- **Port exposure**: Automatic EXPOSE directives from plan ports

**Security Warnings:**
The tool processes shell commands from Habitat plans and includes them in the Dockerfile. Only use with trusted Habitat plans from known sources. Review generated Dockerfiles before building images.

#### `generate_compose_from_habitat(plan_paths: str, network_name: str = "habitat_net")`
Generate docker-compose.yml from multiple Habitat plans for multi-service deployments.

**Example:**
```python
# Single service
generate_compose_from_habitat("/path/to/nginx/plan.sh", "myapp_network")
# Returns:
# version: '3.8'
# services:
#   nginx:
#     build:
#       context: .
#       dockerfile: Dockerfile.nginx
#     container_name: nginx
#     ports:
#       - "80:80"
#       - "443:443"
#     environment:
#       - HTTP=80
#       - HTTPS=443
#     networks:
#       - myapp_network
#
# networks:
#   myapp_network:
#     driver: bridge

# Multiple services with dependencies
generate_compose_from_habitat(
    "/path/to/backend/plan.sh,/path/to/postgres/plan.sh",
    "app_network"
)
# Returns:
# version: '3.8'
# services:
#   backend:
#     build:
#       context: .
#       dockerfile: Dockerfile.backend
#     container_name: backend
#     ports:
#       - "8080:8080"
#     environment:
#       - PORT=8080
#     depends_on:
#       - postgres
#     networks:
#       - app_network
#
#   postgres:
#     build:
#       context: .
#       dockerfile: Dockerfile.postgres
#     container_name: postgres
#     ports:
#       - "5432:5432"
#     environment:
#       - POSTGRESQL=5432
#     volumes:
#       - postgres_data:/var/lib/app
#     networks:
#       - app_network
#
# networks:
#   app_network:
#     driver: bridge
#
# volumes:
#   postgres_data:
```

**Parameters:**
- `plan_paths`: Comma-separated paths to plan.sh files for multiple services
- `network_name`: Docker network name for service communication (default: habitat_net)

**Features:**
- **Multi-service orchestration**: Combines multiple Habitat plans into one compose file
- **Automatic dependencies**: Creates depends_on from Habitat service binds
- **Volume detection**: Identifies services needing persistent storage from do_init callbacks
- **Network isolation**: Configures bridge networks for service communication
- **Port management**: Maps ports from Habitat exports to Docker compose
- **Environment variables**: Generates environment configuration from port definitions

**Use Cases:**
- Converting multi-service Habitat applications to Docker Compose
- Creating development environments from production Habitat plans
- Simplifying container orchestration for local testing
- Migration path from Habitat to Kubernetes (via docker-compose)

## Development

### Project Structure

```
souschef/
├── souschef/
│   ├── __init__.py
│   └── server.py          # MCP server implementation
├── tests/
│   ├── __init__.py
│   └── test_server.py     # Comprehensive test suite
├── .devcontainer/         # VS Code dev container config
├── .github/
│   └── copilot-instructions.md  # Copilot development guidelines
├── pyproject.toml         # Project configuration
└── README.md
```

### Development Standards

SousChef uses a modern Python toolchain for code quality:

- **Ruff**: Primary linter and formatter (replaces Black, isort, flake8)
  ```bash
  poetry run ruff check .    # Lint code
  poetry run ruff format .   # Format code
  ```

- **mypy**: Static type checking for CI/CD
  ```bash
  poetry run mypy souschef   # Type check source code
  ```

- **Pylance**: Real-time VS Code type checking and intellisense
  - Configured in `.vscode/settings.json`
  - Provides immediate feedback during development

- **pytest**: Testing framework with coverage reporting
  ```bash
  poetry run pytest --cov=souschef --cov-report=term-missing
  ```

**Quality Requirements:**
- Zero warnings from all tools (Ruff, mypy, Pylance)
- Type hints required for all functions
- Google-style docstrings
- 92% test coverage (exceeds 90% target)

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed development guidelines.

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=souschef --cov-report=term-missing --cov-report=html

# Run specific test suites
poetry run pytest tests/test_server.py              # Core unit tests
poetry run pytest tests/test_cli.py                 # CLI tests
poetry run pytest tests/test_mcp.py                 # MCP protocol tests
poetry run pytest tests/test_integration.py         # Integration tests
poetry run pytest tests/test_integration_accuracy.py # Accuracy validation
poetry run pytest tests/test_enhanced_guards.py     # Guard conversion tests
poetry run pytest tests/test_error_paths.py         # Error handling
poetry run pytest tests/test_error_recovery.py      # Error recovery
poetry run pytest tests/test_real_world_fixtures.py # Real-world cookbooks
poetry run pytest tests/test_property_based.py      # Hypothesis fuzz tests
poetry run pytest tests/test_performance.py         # Performance benchmarks
poetry run pytest tests/test_snapshots.py           # Snapshot regression tests

# Run with benchmarks
poetry run pytest --benchmark-only

# Check code quality
poetry run ruff check .        # Linting
poetry run ruff format .       # Formatting
poetry run mypy souschef       # Type checking
```

### Test Types

The project includes comprehensive test coverage across multiple dimensions:

1. **Unit Tests** (`test_server.py`, `test_cli.py`, `test_mcp.py`)
   - Mock-based tests for individual functions
   - Test error handling and edge cases
   - Fast execution, isolated from filesystem
   - MCP protocol compliance testing

2. **Integration Tests** (`test_integration.py`, `test_integration_accuracy.py`)
   - Real file operations with test fixtures
   - Validate parsing with actual Chef cookbook files
   - Parameterized tests for various scenarios
   - Accuracy validation for conversions

3. **Property-Based Tests** (`test_property_based.py`)
   - Uses Hypothesis for fuzz testing
   - Generates random inputs to find edge cases
   - Ensures functions handle any input gracefully

4. **Specialized Test Suites**
   - **Enhanced Guards** (`test_enhanced_guards.py`): Complex guard condition conversion
   - **Error Handling** (`test_error_paths.py`, `test_error_recovery.py`): Comprehensive error scenarios
   - **Real-World Fixtures** (`test_real_world_fixtures.py`): Production cookbook patterns
   - **Performance** (`test_performance.py`): Benchmarking and optimization
   - **Snapshots** (`test_snapshots.py`): Regression testing for output stability

5. **Test Fixtures**
   - Sample Chef cookbooks in `tests/fixtures/`
   - Multiple cookbook types: apache2, docker, mysql, nodejs, legacy Chef 12, Habitat plans
   - Real-world metadata, recipes, attributes, and resources
   - Used across integration and accuracy testing

### Test Coverage

The project maintains 92% test coverage, exceeding the 90% target. Run coverage with HTML report:

```bash
poetry run pytest --cov=souschef --cov-report=html
open htmlcov/index.html  # View detailed coverage report
```

### Mutation Testing

To verify test quality with mutation testing:

```bash
poetry run mutmut run
poetry run mutmut results
```

### VS Code Tasks

The project includes several VS Code tasks:
- **Run Tests** - Execute test suite
- **Run Tests with Coverage** - Generate coverage reports
- **Lint (Ruff)** - Check code quality
- **Format (Ruff)** - Auto-format code
- **Lint & Test** - Run both linting and tests

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass
2. Code coverage maintained at 90%+
3. Code passes ruff linting
4. All functions have type hints and docstrings
5. Follow the development standards in `.github/copilot-instructions.md`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**SousChef** - *Ansible automation, one recipe at a time.* ✨
