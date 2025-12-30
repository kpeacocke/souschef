# SousChef 🍳

An AI-powered MCP (Model Context Protocol) server that assists with analyzing and converting Chef cookbooks to Ansible playbooks.

## Features

### Chef Cookbook Analysis
- **Parse Metadata** - Extract cookbook metadata (name, version, dependencies, etc.)
- **Parse Recipes** - Analyze Chef resources, actions, and properties
- **Parse Attributes** - Extract default, override, and normal attributes
- **Parse Custom Resources** - Extract properties, attributes, and actions from custom resources and LWRPs
- **List Cookbook Structure** - Display the directory structure of Chef cookbooks
- **File Operations** - Read files and list directories

### Chef to Ansible Conversion
- **Convert Resources** - Transform Chef resources to Ansible tasks with proper module mapping
- **Action Mapping** - Automatically map Chef actions (install, start, create) to Ansible states
- **Module Selection** - Intelligently select appropriate Ansible modules for each resource type
- **YAML Generation** - Output valid Ansible task YAML ready for playbooks
- **Template Parsing** - Parse ERB templates and convert to Jinja2 format with variable extraction

### InSpec Integration & Validation
- **Parse InSpec Profiles** - Extract controls, describe blocks, and test expectations from InSpec profiles
- **Convert InSpec to Tests** - Transform InSpec controls to Testinfra (Python) or Ansible assert tasks
- **Generate InSpec from Chef** - Create InSpec validation controls from Chef recipes automatically
- **Validation Workflow** - Complete Chef → Ansible → InSpec validation pipeline
- **Multi-format Support** - Handle single control files or complete InSpec profile directories

### Coming Soon
- Full playbook generation from recipes
- Chef guards and notifications conversion
- Complex attribute precedence handling
- Chef search and data bags conversion

## Installation

### Prerequisites
- Python 3.14+
- [uv](https://github.com/astral-sh/uv) for dependency management

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd souschef
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Run the server directly:
   ```bash
   uv run souschef
   ```

   Or run as a Python module:
   ```bash
   uv run python -m souschef.server
   ```

4. Run tests to verify installation:
   ```bash
   uv run pytest
   ```

## Usage

### Command Line Interface

SousChef provides a convenient CLI for local usage without needing an MCP client.

See **[CLI.md](CLI.md)** for complete CLI documentation and examples.

**Quick Start:**

```bash
# Install the CLI
uv sync

# Parse a Chef recipe
souschef-cli recipe path/to/recipe.rb

# Parse an ERB template and convert to Jinja2
souschef-cli template path/to/template.erb

# Convert a Chef resource to Ansible task
souschef-cli convert package nginx --action install

# Parse InSpec profiles and controls
souschef-cli inspec-parse path/to/inspec/profile/

# Convert InSpec to Testinfra tests
souschef-cli inspec-convert controls.rb --format testinfra

# Generate InSpec validation from Chef recipe
souschef-cli inspec-generate recipe.rb

# Analyze an entire cookbook
souschef-cli cookbook path/to/cookbook

# Get help
souschef-cli --help
```

### Conversion Examples

The `examples/` directory contains complete Chef cookbooks demonstrating conversion capabilities:

- **[web-server](examples/web-server/)** - Complete nginx web server setup with:
  - Package installation, service management, templates
  - Custom resources (nginx_vhost)
  - Platform-specific logic (Debian/RHEL)
  - SSL configuration, guards, notifications
  - [Full conversion guide](examples/web-server/CONVERSION.md)

- **[database](examples/database/)** - PostgreSQL database server with:
  - Database and user management custom resources
  - Complex configuration templates
  - Backup automation with cron jobs
  - Guard conditions and idempotency

See [examples/README.md](examples/README.md) for detailed usage.

### InSpec Validation Workflow

SousChef provides complete integration with InSpec for validating your Chef to Ansible conversions, ensuring that your infrastructure automation maintains the same desired state regardless of the tool used.

#### Complete Workflow Example

```bash
# 1. Start with a Chef recipe
cat > nginx-recipe.rb << 'EOF'
package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end

template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  action :create
end
EOF

# 2. Convert Chef recipe to Ansible playbook (manual or automated)
# ... your conversion process ...

# 3. Generate InSpec validation controls from the original Chef recipe
souschef-cli inspec-generate nginx-recipe.rb > validation-controls.rb

# 4. Run InSpec validation against your infrastructure
inspec exec validation-controls.rb -t ssh://your-server

# 5. Convert InSpec controls to Testinfra for CI/CD integration
souschef-cli inspec-convert validation-controls.rb --format testinfra > test_nginx.py

# 6. Run tests with pytest
pytest test_nginx.py --hosts='ssh://your-server'
```

#### Generated InSpec Controls

From the Chef recipe above, SousChef generates:

```ruby
# InSpec controls generated from Chef recipe
control 'package-nginx' do
  title 'Verify package nginx'
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
- **Testing**: 100% test coverage goal using pytest
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

The project maintains 99%+ test coverage. Run coverage with HTML report:

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

## Roadmap

- [x] Add server entry point and runner
- [x] Implement Chef → Ansible resource conversion (basic)
- [x] Support template conversion (ERB → Jinja2)
- [x] Parse custom Chef resources/LWRPs
- [ ] Generate complete Ansible playbooks from recipes
- [ ] Handle Chef guards (only_if, not_if) and notifications
- [ ] Support complex attribute precedence and merging
- [ ] Add conversion validation and testing
- [ ] Handle Chef search and data bags
