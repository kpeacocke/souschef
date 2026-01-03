# SousChef 🍳

An AI-powered MCP (Model Context Protocol) server that provides comprehensive Chef-to-Ansible migration capabilities for enterprise infrastructure transformation.

## Overview

SousChef is a complete enterprise-grade migration platform with 34 MCP tools organized across 8 major capability areas to facilitate Chef-to-Ansible AWX/AAP migrations. From cookbook analysis to deployment pattern conversion, SousChef provides everything needed for a successful infrastructure automation migration.

## 🚀 Core Capabilities

### 1. Chef Cookbook Analysis & Parsing
Complete cookbook introspection and analysis tools:

- **parse_template** - Parse ERB templates with Jinja2 conversion and variable extraction
- **parse_custom_resource** - Extract properties, attributes, and actions from custom resources and LWRPs
- **list_directory** - Navigate and explore cookbook directory structures
- **read_file** - Read cookbook files with error handling
- **read_cookbook_metadata** - Parse metadata.rb files for dependencies and cookbook information
- **parse_recipe** - Analyze Chef recipes and extract resources, actions, and properties
- **parse_attributes** - Parse attribute files (default, override, normal) with precedence analysis
- **list_cookbook_structure** - Display complete cookbook directory hierarchy

### 2. Chef-to-Ansible Conversion Engine
Advanced resource-to-task conversion with intelligent module selection:

- **convert_resource_to_task** - Transform individual Chef resources to Ansible tasks
- **generate_playbook_from_recipe** - Generate complete Ansible playbooks from Chef recipes

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

### 8. Advanced Deployment Patterns & Migration Assessment
Modern deployment strategies and migration planning:

- **convert_chef_deployment_to_ansible_strategy** - Convert deployment recipes to Ansible strategies
- **generate_blue_green_deployment_playbook** - Create blue/green deployment playbooks
- **generate_canary_deployment_strategy** - Generate canary deployment configurations
- **analyze_chef_application_patterns** - Identify application deployment patterns
- **assess_chef_migration_complexity** - Comprehensive migration complexity assessment
- **generate_migration_plan** - Create detailed migration execution plans
- **analyze_cookbook_dependencies** - Analyze dependencies and migration order
- **generate_migration_report** - Generate executive and technical migration reports

## 🎯 Migration Workflow

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

### Phase 4: Validation & Testing
```bash
# Generate InSpec validation
generate_inspec_from_recipe /path/to/recipe.rb

# Convert existing InSpec to Ansible tests
convert_inspec_to_test /path/to/inspec_profile testinfra
```

## 📊 Enterprise Features

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

### Enterprise Integration
- **AWX/AAP Ready**: Native Ansible Automation Platform integration
- **Dynamic Inventory**: Chef server integration for hybrid environments
- **Secrets Management**: Secure data bag to Vault conversion
- **Multi-Environment**: Production-ready inventory and variable management

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.14+
- [Poetry](https://python-poetry.org/) for dependency management
- MCP-compatible client (Claude Desktop, VS Code with MCP extension, etc.)

### Quick Start

1. **Clone and setup**:
   ```bash
   git clone https://github.com/your-org/souschef
   cd souschef
   poetry install
   ```

2. **Configure MCP client** (Claude Desktop example):
   ```json
   {
     \"mcpServers\": {
       \"souschef\": {
         \"command\": \"poetry\",
         \"args\": [\"--directory\", \"/path/to/souschef\", \"run\", \"souschef\"],
         \"env\": {}
       }
     }
   }
   ```

3. **Start using SousChef**:
   Ask your MCP client: "Analyze the cookbook at /path/to/my/cookbook" or "Convert this Chef recipe to an Ansible playbook"

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

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=souschef --cov-report=html

# Lint and format
poetry run ruff check .
poetry run ruff format .
```
## 🏗️ Architecture & Design

### MCP Protocol Integration
SousChef leverages the Model Context Protocol (MCP) to provide seamless integration with AI assistants and development environments:

- **34 Specialized Tools**: Each migration capability exposed as dedicated MCP tool
- **Type-Safe Interfaces**: Full Python type hints for reliable AI interactions
- **Comprehensive Error Handling**: Graceful degradation and helpful error messages
- **Streaming Support**: Efficient handling of large cookbook conversions

### Testing Strategy
Following enterprise-grade testing standards:

- **Unit Tests**: Mock-based testing for individual functions (tests/test_server.py)
- **Integration Tests**: Real cookbook testing with fixtures (tests/test_integration.py)
- **Property-Based Tests**: Hypothesis fuzz testing for edge cases (tests/test_property_based.py)
- **82% Coverage**: Comprehensive test coverage with goal of 95% for production readiness

### Quality Assurance
- **Zero Warnings Policy**: All code passes linting without disabling checks
- **Type Safety**: Complete type annotations throughout the codebase
- **Automated Testing**: CI/CD pipeline with comprehensive test suites
- **Documentation**: Detailed docstrings and usage examples

## 📚 Documentation

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

## 🚀 Roadmap

### Completed ✅
- ✅ Complete Chef cookbook parsing (recipes, attributes, metadata, templates)
- ✅ InSpec profile parsing and conversion to Testinfra/Ansible tests
- ✅ Chef resource to Ansible task conversion with module mapping
- ✅ Data bags to Ansible Vault conversion
- ✅ Chef environments to Ansible inventory conversion
- ✅ Chef search patterns to dynamic inventory conversion
- ✅ AWX/AAP job templates, workflows, and project generation
- ✅ Blue/green and canary deployment pattern generation
- ✅ Migration complexity assessment and planning tools
- ✅ Comprehensive testing suite (unit, integration, property-based)
- ✅ Command-line interface (CLI) for standalone usage

### In Progress 🔄
- 🔄 Enhanced error handling and user experience improvements
- 🔄 Documentation website and interactive examples
- 🔄 Performance optimizations for large-scale enterprise migrations
- 🔄 Technical debt reduction (15 functions tracked in [GitHub Issues](https://github.com/kpeacocke/souschef/issues?q=is%3Aissue+is%3Aopen+label%3Atechnical-debt))

### Planned 📅
- 📅 Chef Habitat to containerized deployment conversion
- 📅 Integration with additional test frameworks (ServerSpec, Goss)
- 📅 Visual migration planning and dependency mapping interface
- 📅 Terraform provider for infrastructure state management
- 📅 Jenkins/GitLab CI pipeline generation
- 📅 Advanced Chef guard handling (only_if, not_if conditions)
- 📅 Complex attribute precedence and merging logic
- 📅 Conversion validation and testing framework

## 🙋‍♀️ Support & Community

- **Issues**: [GitHub Issues](https://github.com/your-org/souschef/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/souschef/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/souschef/wiki)

---

**SousChef** - *Transforming infrastructure automation, one recipe at a time.* 🍳✨
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
      "command": "uv",
      "args": [
        "--directory",
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

#### `parse_attributes(path: str)`
Parse a Chef attributes file and extract attribute definitions.

**Example:**
```python
parse_attributes("/path/to/cookbook/attributes/default.rb")
# Returns:
# default[nginx.port] = 80
# default[nginx.ssl_port] = 443
```

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

- **Code Quality**: Zero warnings policy, type hints required, Google-style docstrings
- **Testing**: High test coverage (82%) using pytest with goal of 100%
- **Linting**: Code must pass `ruff check` with no violations
- **Formatting**: Code must be formatted with `ruff format`

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for detailed development guidelines.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=souschef --cov-report=term-missing --cov-report=html

# Run only unit tests (mocked)
uv run pytest tests/test_server.py

# Run only integration tests (real files)
uv run pytest tests/test_integration.py

# Run property-based tests
uv run pytest tests/test_property_based.py

# Run with benchmarks
uv run pytest --benchmark-only

# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .
```

### Test Types

The project includes multiple types of tests:

1. **Unit Tests** (`test_server.py`)
   - Mock-based tests for individual functions
   - Test error handling and edge cases
   - Fast execution, isolated from filesystem

2. **Integration Tests** (`test_integration.py`)
   - Real file operations with test fixtures
   - Validate parsing with actual Chef cookbook files
   - Parameterized tests for various scenarios
   - Performance benchmarks with pytest-benchmark

3. **Property-Based Tests** (`test_property_based.py`)
   - Uses Hypothesis for fuzz testing
   - Generates random inputs to find edge cases
   - Ensures functions handle any input gracefully

4. **Test Fixtures**
   - Sample Chef cookbook in `tests/fixtures/sample_cookbook/`
   - Real-world metadata, recipes, and attributes
   - Used for integration testing

### Test Coverage

The project maintains 82% test coverage with a goal of 95%+. Run coverage with HTML report:

```bash
uv run pytest --cov=souschef --cov-report=html
open htmlcov/index.html  # View detailed coverage report
```

### Mutation Testing

To verify test quality with mutation testing:

```bash
uv run mutmut run
uv run mutmut results
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
2. Code coverage remains at 100%
3. Code passes ruff linting
4. All functions have type hints and docstrings
5. Follow the development standards in `.github/copilot-instructions.md`

## License

TBD

---

**SousChef** - *Transforming infrastructure automation, one recipe at a time.* 🍳✨
