# Chef to Ansible Migration & Ansible Upgrades - SousChef MCP

An AI-powered MCP (Model Context Protocol) server that provides comprehensive Chef-to-Ansible migration capabilities and Ansible upgrade planning for enterprise infrastructure transformation.

[![GitHub release](https://img.shields.io/github/v/release/kpeacocke/souschef)](https://github.com/kpeacocke/souschef/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-green.svg)](htmlcov/index.html)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)

## Overview

SousChef is a complete enterprise-grade platform with two major capabilities:

### 1. Chef to Ansible Migration (57 tools)

Complete enterprise-grade migration platform with **57 primary MCP tools** organised across **13 major capability areas** to facilitate Chef-to-Ansible AWX/AAP migrations and Ansible version upgrades. From cookbook analysis to deployment pattern conversion, including Chef Habitat to containerised deployments, Chef Server integration, CI/CD pipeline generation, and Ansible upgrade planning, SousChef provides everything needed for a successful infrastructure automation migration.

### 2. Ansible Upgrade Assessment & Planning (NEW - Available)

Comprehensive Ansible upgrade analysis and planning tools based on official Ansible-Python compatibility matrices:

- **Version Compatibility Assessment** - Validate Ansible and Python version compatibility
- **EOL Status Checking** - Track end-of-life dates and security support
- **Upgrade Path Planning** - Generate detailed upgrade plans with risk assessment
- **Collection Compatibility** - Validate collection versions against target Ansible releases
- **Breaking Change Analysis** - Identify and plan for breaking changes (e.g., 2.9 → 2.10 collections split)
- **Python Upgrade Impact** - Assess Python version upgrade requirements for control and managed nodes
- **Testing Plan Generation** - Generate comprehensive upgrade testing plans

> **✅ Feature Status**: Ansible upgrade features are now available with CLI commands, MCP tools, and web UI.
> See [Ansible Upgrade Integration Design](docs/ANSIBLE_UPGRADE_INTEGRATION.md) for full details.

### About Tool Counts

**Why 40 tools in the documentation but more in the server?**

The MCP server provides **48 total tools**. This documentation focuses on the **45 primary user-facing tools** that cover the main migration and upgrade capabilities. The remaining 3 tools are low-level filesystem operations used internally by the main tools.

As a user, you'll primarily interact with the documented tools. Your AI assistant may use the additional tools automatically when needed, but you don't need to know about them for successful migrations.

> **For developers:** See `souschef/server.py` for the complete list of all 43 registered tools.

## Model Agnostic - Works with Any AI Model

**SousChef works with ANY AI model through the Model Context Protocol (MCP)**. The MCP architecture separates tools from models:

- **Red Hat AI** (Llama, IBM models)
- **Claude** (Anthropic)
- **GPT-4/GPT-3.5** (OpenAI)
- **GitHub Copilot** (Microsoft/OpenAI)
- **Local Models** (Ollama, llama.cpp, etc.)
- **Custom Enterprise Models**

**How it works:** You choose your AI model provider in your MCP client. SousChef provides the Chef/Ansible expertise through 35 specialized tools. The model calls these tools to help with your migration.

> See [config/CONFIGURATION.md](config/CONFIGURATION.md) for configuration examples with different model providers.

## Quick Links

### Chef to Ansible Migration
- **[Terraform Provider](terraform-provider/README.md)** - Manage migrations with infrastructure-as-code
- **[User Guide](docs/user-guide/)** - Complete documentation
- **[Data Persistence Guide](docs/user-guide/data-persistence.md)** - History, caching, and storage backends
- **[API Reference](docs/api-reference/)** - Detailed tool documentation
- **[Migration Guide](docs/migration-guide/)** - Step-by-step migration process

### Ansible Upgrades (In Development)
- **[Ansible Upgrade Integration Design](docs/ANSIBLE_UPGRADE_INTEGRATION.md)** - Complete design and architecture
- **[Ansible Upgrade Matrix Implementation](docs/ANSIBLE_UPGRADE_MATRIX_IMPLEMENTATION.md)** - PDF data mapping and implementation
- **[Implementation Roadmap](docs/ANSIBLE_UPGRADE_ROADMAP.md)** - Detailed development timeline

## What's New in v4.2.0

**Ansible Upgrade & Planning Tools** - Complete upgrade assessment and planning capabilities:

- **5 New CLI Commands**: `ansible assess`, `plan`, `eol`, `validate-collections`, `detect-python` for comprehensive upgrade workflows
- **3 Interactive UI Pages**: Environment Assessment, Upgrade Planning, and Collection Validation interfaces
- **MCP Tool Integration**: Access upgrade planning programmatically through MCP server tools
- **Comprehensive Testing**: 1,954 passing tests with 91% coverage across all upgrade functionality
- **Type Safety**: Full mypy compliance with proper type hints for all new functions
- **Production Ready**: All quality gates passing - Ruff linting, mypy, and comprehensive test coverage

See [Ansible Upgrade Integration Design](docs/ANSIBLE_UPGRADE_INTEGRATION.md) for complete documentation.

## Previous Releases

### v4.1.0 - Security Hardening & Type Safety

Enterprise-grade improvements for production deployments:

- **GitHub Actions Security**: All external actions pinned to commit SHAs for supply chain protection
- **Type Safety**: Complete mypy type checking (0 errors) with full type hints across 57 source files
- **Fork Checkout Protection**: Privileged workflows explicitly checkout from main repository, never from forks
- **Python Support Expansion**: Now supports Python 3.10+ (added support for 3.10 and 3.11)
- **Code Quality**: Ruff linting with zero warnings, Australian English documentation standards

See [Release Notes](https://github.com/kpeacocke/souschef/releases/tag/v4.1.0) for full details.

### v3.4.0 - Chef Server Integration

**Chef Server Integration & AI-Enhanced Template Conversion** - Dynamic inventory and intelligent template conversion:

- **Chef Server Connectivity**: Validate Chef Server connections and query nodes with `validate_chef_server_connection` and `get_chef_nodes`
- **AI-Enhanced Templates**: Convert ERB to Jinja2 with AI validation using `convert_template_with_ai` for complex Ruby logic
- **CLI Commands**: New commands `validate-chef-server`, `query-chef-nodes`, and `convert-template-ai` for command-line access
- **Streamlit UI**: Chef Server Settings page for managing server configuration and validation

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
- **parse_recipe** - Analyse Chef recipes and extract resources, actions, and properties
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
- **analyse_chef_search_patterns** - Discover and analyse search usage in cookbooks

### 4. InSpec Integration & Validation

Complete InSpec-to-Ansible testing pipeline:

- **parse_inspec_profile** - Parse InSpec profiles and extract controls
- **convert_inspec_to_test** - Convert InSpec controls to Testinfra or Ansible assert tasks
- **generate_inspec_from_recipe** - Auto-generate InSpec validation from Chef recipes

### 5. Data Bags & Secrets Management

Chef data bags to Ansible vars/vault conversion:

- **convert_chef_databag_to_vars** - Transform data bags to Ansible variable files
- **generate_ansible_vault_from_databags** - Convert encrypted data bags to Ansible Vault
- **analyse_chef_databag_usage** - Analyse data bag usage patterns in cookbooks

### 6. Environment & Configuration Management

Chef environments to Ansible inventory groups:

- **convert_chef_environment_to_inventory_group** - Transform Chef environments to inventory
- **generate_inventory_from_chef_environments** - Generate complete inventory from environments
- **analyse_chef_environment_usage** - Analyse environment usage in cookbooks

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

### 10. CI/CD Pipeline Generation

Generate Jenkins, GitLab CI, and GitHub Actions workflows from Chef cookbook CI patterns:

- **generate_jenkinsfile_from_chef** - Generate Jenkinsfile (Declarative or Scripted) from Chef cookbook CI/CD patterns
- **generate_gitlab_ci_from_chef** - Generate .gitlab-ci.yml from Chef cookbook testing tools
- **generate_github_workflow_from_chef** - Generate GitHub Actions workflow from Chef cookbook CI/CD patterns

Automatically detects and converts:

- **Test Kitchen** configurations (.kitchen.yml) → Integration test stages
- **ChefSpec** tests (spec/) → Unit test stages
- **Cookstyle/Foodcritic** → Lint stages
- Multiple test suites → Parallel execution strategies

### 11. GitHub Copilot Agent Control

Manage GitHub Copilot agents working on repository issues with full pause/stop/resume capabilities:

- **assign_github_copilot_to_issue** - Assign Copilot agent to implement an issue
- **pause_github_copilot_agent** - Pause a running agent (can be resumed)
- **stop_github_copilot_agent** - Stop and cancel an agent assignment
- **resume_github_copilot_agent** - Resume a paused agent with optional new instructions
- **check_github_copilot_agent_status** - Check current agent state and activity

**Agent lifecycle management:**

1. **Assign** - Start Copilot working on an issue
2. **Monitor** - Check status and review progress
3. **Pause** - Temporarily pause for review or changes
4. **Resume** - Continue with optional new guidance
5. **Stop** - Cancel if requirements change

State is tracked via issue labels and comments, providing full visibility and control.

#### Example Usage - CI/CD Pipelines

```bash
# Generate Jenkins Declarative pipeline
souschef generate-jenkinsfile ./mycookbook

# Generate Jenkins Scripted pipeline
souschef generate-jenkinsfile ./mycookbook --pipeline-type scripted

# Generate GitLab CI configuration
souschef generate-gitlab-ci ./mycookbook

# Generate GitHub Actions workflow
souschef generate-github-workflow ./mycookbook

# Customise with options
souschef generate-gitlab-ci ./mycookbook --no-cache --no-artifacts
souschef generate-github-workflow ./mycookbook --workflow-name "My CI" --no-cache
```

#### Example Usage - GitHub Agent Control

```python
# From an AI assistant with SousChef MCP

# Assign Copilot to work on an issue
assign_github_copilot_to_issue(
    owner="myorg",
    repo="my-ansible-repo",
    issue_number=42,
    base_ref="main",
    custom_instructions="Focus on idempotency and error handling"
)

# Check agent status
check_github_copilot_agent_status(
    owner="myorg",
    repo="my-ansible-repo",
    issue_number=42
)

# Pause for review
pause_github_copilot_agent(
    owner="myorg",
    repo="my-ansible-repo",
    issue_number=42,
    reason="Need to review approach before continuing"
)

# Resume with new guidance
resume_github_copilot_agent(
    owner="myorg",
    repo="my-ansible-repo",
    issue_number=42,
    additional_instructions="Also add role dependencies"
)

# Stop if no longer needed
stop_github_copilot_agent(
    owner="myorg",
    repo="my-ansible-repo",
    issue_number=42,
    reason="Requirements changed - manual implementation needed"
)
```

#### Command Line Usage - CI/CD Pipelines

**MCP Tool Usage:**

```python
# From an AI assistant with SousChef MCP

# Generate Jenkins pipeline
generate_jenkinsfile_from_chef(
    cookbook_path="/path/to/cookbook",
    pipeline_type="declarative",  # or "scripted"
    enable_parallel="yes"  # or "no"
)

# Generate GitLab CI
generate_gitlab_ci_from_chef(
    cookbook_path="/path/to/cookbook",
    enable_cache="yes",  # or "no"
    enable_artifacts="yes"  # or "no"
)

# Generate GitHub Actions workflow
generate_github_workflow_from_chef(
    cookbook_path="/path/to/cookbook",
    workflow_name="Chef Cookbook CI",
    enable_cache="yes",  # or "no"
    enable_artifacts="yes"  # or "no"
)
```

### 11. Conversion Validation Framework

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

#### Validation Examples

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

- **analyse_chef_application_patterns** - Identify application deployment patterns
- **assess_chef_migration_complexity** - Comprehensive migration complexity assessment
- **generate_migration_plan** - Create detailed migration execution plans
- **analyse_cookbook_dependencies** - Analyse dependencies and migration order
- **generate_migration_report** - Generate executive and technical migration reports

### 12. Chef Server Integration & Dynamic Inventory

Dynamic inventory generation and Chef Server connectivity for hybrid environments:

- **validate_chef_server_connection** - Test Chef Server REST API connectivity and authentication
- **get_chef_nodes** - Query Chef Server for nodes matching search criteria, extracting roles, environment, platform, and IP information
- **convert_template_with_ai** - Convert ERB templates to Jinja2 with AI-based validation for complex Ruby logic

#### Chef Server Features

- **Connection Validation**: Test Chef Server connectivity before migrations
- **Dynamic Node Queries**: Search Chef Server by role, environment, or custom attributes
- **Node Metadata Extraction**: Retrieve IP addresses, FQDNs, platforms, and roles for inventory
- **AI-Enhanced Conversion**: Intelligent ERB→Jinja2 conversion with validation for complex Ruby constructs
- **Fallback Handling**: Graceful degradation when Chef Server is unavailable

#### Usage Examples

```bash
# Validate Chef Server connection
souschef validate-chef-server --server-url https://chef.example.com --node-name admin

# Query Chef Server for nodes
souschef query-chef-nodes --search-query "role:web_server" --json

# Convert template with AI assistance
souschef convert-template-ai /path/to/template.erb --ai --output /path/to/output.j2
```

#### MCP Tool Usage

```python
# Validate Chef Server from AI assistant
validate_chef_server_connection(
    server_url="https://chef.example.com",
    node_name="admin"
)

# Query nodes for dynamic inventory
get_chef_nodes(search_query="role:web_server AND environment:production")

# Convert template with AI validation
convert_template_with_ai(
    erb_path="/path/to/template.erb",
    use_ai_enhancement=True
)
```

### 13. Ansible Upgrade Assessment & Planning

Comprehensive Ansible version upgrade planning based on official Ansible-Python compatibility matrices:

- **detect_python_version** - Detect Python version in specified environment or system
- **assess_ansible_environment** - Assess current Ansible environment versions and configuration
- **generate_upgrade_plan** - Generate detailed upgrade plan with breaking changes, pre/post checks, and risk assessment
- **validate_collection_compatibility** - Validate Ansible collection compatibility against target Ansible versions
- **generate_upgrade_testing_plan** - Generate comprehensive upgrade testing plan

#### Upgrade Planning Features

- **Version Compatibility Checking**: Validate Ansible and Python version compatibility requirements
- **EOL Status Tracking**: Track end-of-life dates and security support windows
- **Safe Upgrade Paths**: Calculate safe upgrade paths with intermediate versions if needed
- **Breaking Change Analysis**: Identify breaking changes (e.g., collections split in 2.9→2.10)
- **Collection Validation**: Verify collection versions work with target Ansible releases
- **Python Impact Assessment**: Assess Python version upgrade requirements for control and managed nodes
- **Comprehensive Testing Plans**: Generate step-by-step testing procedures for upgrades

#### Upgrade Planning Examples

```bash
# Detect Python version in environment
detect_python_version /path/to/venv

# Assess current Ansible environment
assess_ansible_environment /path/to/ansible/env

# Generate upgrade plan from 2.14 to 2.17
generate_upgrade_plan 2.14 2.17 /path/to/ansible/env

# Validate collections for target version
validate_collection_compatibility '{"community.general": "3.0.0"}' 2.17

# Generate testing plan for upgrade
generate_upgrade_testing_plan /path/to/ansible/env
```

#### MCP Tool Usage

```python
# From an AI assistant with SousChef MCP

# Detect Python version
python_version = detect_python_version("/ansible/venv")

# Assess Ansible environment
assessment = assess_ansible_environment("/ansible/env")

# Generate upgrade plan
plan = generate_upgrade_plan(
    current_version="2.14",
    target_version="2.17"
)

# Check collection compatibility
compatibility = validate_collection_compatibility(
    collections={"community.general": "3.0.0"},
    ansible_version="2.17"
)

# Generate testing plan
testing_plan = generate_upgrade_testing_plan("/ansible/env")
```

**See [Ansible Upgrade Integration Design](docs/ANSIBLE_UPGRADE_INTEGRATION.md) for full details and compatibility matrix information.**

## Migration Workflow

### Phase 1: Discovery & Assessment

```bash
# Assess migration complexity
assess_chef_migration_complexity /path/to/cookbooks

# Analyse cookbook dependencies
analyse_cookbook_dependencies /path/to/cookbook

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

### Performance Profiling & Optimization

Profile cookbook parsing performance to identify bottlenecks and optimize large-scale migrations:

```bash
# Profile entire cookbook (all parsing operations)
souschef-cli profile /path/to/cookbook

# Save profiling report to file
souschef-cli profile /path/to/cookbook --output profile_report.txt

# Profile specific operations with detailed statistics
souschef-cli profile-operation recipe /path/to/recipe.rb --detailed
souschef-cli profile-operation attributes /path/to/attributes/default.rb
souschef-cli profile-operation template /path/to/template.erb

# MCP Tool Usage (from AI assistants)
profile_cookbook_performance /path/to/large_cookbook
profile_parsing_operation recipe /path/to/recipe.rb --detailed
```

### 10. Visual Migration Planning Interface

Interactive web-based interface for Chef-to-Ansible migration planning and Ansible upgrade management:

**Chef Migration Features:**
- **Cookbook Analysis Dashboard**: Interactive directory scanning with metadata parsing and complexity assessment
- **AI-Assisted Effort Estimation** (v3.3.0+):
  - **Manual Migration Estimate**: Full effort without AI assistance
  - **SousChef-Assisted Estimate**: 50% time reduction through automated boilerplate conversion
  - **Time Savings Display**: Clear comparison showing hours saved and efficiency percentage
  - **Visual Metrics**: Side-by-side metric cards for instant visual comparison
- **Migration Planning Wizard**: Step-by-step migration planning with dual effort scenarios and risk analysis
- **Dependency Mapping**: Visual dependency graphs showing cookbook relationships and migration ordering
- **Validation Reports**: Conversion validation results with syntax checking and best practice compliance
- **Progress Tracking**: Real-time migration progress with completion metrics and bottleneck identification
- **History and Persistence**: Stored analysis history, cached results, and downloadable artefacts (SQLite or PostgreSQL, plus S3-compatible storage)

**Ansible Upgrade Features (NEW):**
- **Environment Assessment**: Analyse current Ansible installation, Python compatibility, and installed collections
- **Upgrade Planning**: Interactive upgrade planning with version selection, breaking changes analysis, and risk assessment
- **Collection Validation**: Upload requirements.yml to validate collection compatibility with target Ansible versions
- **Visual Dashboards**: Progress bars, compatibility metrics, and exportable JSON reports for all upgrade assessments

**Launch the UI:**

```bash
# Using Poetry (development)
poetry run souschef ui

# Using pip (installed)
souschef ui

# Custom port
souschef ui --port 8080
```

**Run the UI in Docker:**

```bash
# Build the image
docker build -t souschef-ui .

# Run the container
docker run -p 9999:9999 souschef-ui

# Or use docker-compose
docker-compose up
```

**Run the MCP server in Docker (for MCP clients):**

```bash
# Build the MCP image
docker build -f Dockerfile.mcp -t souschef-mcp:latest .

# Run the MCP server over stdio
docker run -i --rm souschef-mcp:latest
```

Use the Docker configuration examples for your client:

- [config/claude-desktop-docker.json](config/claude-desktop-docker.json)
- [config/vscode-copilot-docker.json](config/vscode-copilot-docker.json)

**Run Published Image from GitHub Container Registry:**

SousChef provides two Docker images automatically published to GHCR on each release:

**1. Web UI Image:**

```bash
# Pull the latest UI image
docker pull ghcr.io/kpeacocke/mcp-souschef:latest

# Or pull a specific version
docker pull ghcr.io/kpeacocke/mcp-souschef:4.1.2

# Run the UI with your .env file
docker run -p 9999:9999 \
  --env-file .env \
  ghcr.io/kpeacocke/mcp-souschef:latest

# Or with docker-compose
cat > docker-compose.override.yml << 'EOF'
version: '3.8'
services:
  souschef-ui:
    image: ghcr.io/kpeacocke/mcp-souschef:latest
    build: ~
EOF
docker-compose up
```

**2. MCP Server Image (for AI clients):**

```bash
# Pull the latest MCP server image
docker pull ghcr.io/kpeacocke/souschef-mcp:latest

# Run the MCP server over stdio (for MCP clients)
docker run -i --rm ghcr.io/kpeacocke/souschef-mcp:latest
```

Use the published MCP image with your AI client:

- [config/claude-desktop-docker-ghcr.json](config/claude-desktop-docker-ghcr.json)
- [config/vscode-copilot-docker-ghcr.json](config/vscode-copilot-docker-ghcr.json)

**Container Images:**

- **Registry**: GitHub Container Registry (GHCR)
- **UI Image**: `ghcr.io/kpeacocke/mcp-souschef` (Streamlit web interface)
- **MCP Server Image**: `ghcr.io/kpeacocke/souschef-mcp` (stdio MCP protocol)
- **Available Tags**:
  - `latest` - Most recent release
  - `4.1.2` - Specific version (semver)
  - `4.1` - Latest patch of a minor version
  - `4` - Latest patch of a major version

**Why use GHCR?**

- Integrated with GitHub releases and CI/CD
- Faster pulls for users in GitHub ecosystem
- Security scanning and SBOM included
- Multi-platform support (amd64, arm64)

**Docker Environment Configuration:**

SousChef supports AI configuration via environment variables in Docker containers. Create a `.env` file in your project root:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your AI provider settings
nano .env
```

**Example .env file:**

```dotenv
# AI Configuration
SOUSCHEF_AI_PROVIDER=Anthropic (Claude)
SOUSCHEF_AI_MODEL=claude-3-5-sonnet-20241022
SOUSCHEF_AI_API_KEY=your-api-key-here
SOUSCHEF_AI_BASE_URL=
SOUSCHEF_AI_PROJECT_ID=
SOUSCHEF_AI_TEMPERATURE=0.7
SOUSCHEF_AI_MAX_TOKENS=4000
SOUSCHEF_ALLOWED_HOSTNAMES=api.example.com,*.example.org

# Streamlit Configuration (optional)
STREAMLIT_SERVER_PORT=9999
STREAMLIT_SERVER_HEADLESS=true
```

**Supported AI Providers:**

- `Anthropic (Claude)` - Anthropic Claude models
- `OpenAI (GPT)` - OpenAI GPT models
- `IBM Watsonx` - IBM Watsonx AI models
- `Red Hat Lightspeed` - Red Hat Lightspeed models

**Environment Variables:**

- `SOUSCHEF_AI_PROVIDER` - AI provider name (required)
- `SOUSCHEF_AI_MODEL` - Model name (required)
- `SOUSCHEF_AI_API_KEY` - API key for authentication (required)
- `SOUSCHEF_AI_BASE_URL` - Custom API base URL (optional)
- `SOUSCHEF_AI_PROJECT_ID` - Project ID for Watsonx (optional)
- `SOUSCHEF_AI_TEMPERATURE` - Model temperature 0.0-2.0 (optional, default: 0.7)
- `SOUSCHEF_AI_MAX_TOKENS` - Maximum tokens to generate (optional, default: 4000)
- `SOUSCHEF_ALLOWED_HOSTNAMES` - Comma-separated list of allowed hostnames for outbound API requests (optional)

**Persistent Storage Configuration (Docker Compose):**

All persistent storage paths are configurable via environment variables. Add these to your `.env` file to customise where data is stored:

```dotenv
# Docker Compose Volume Configuration (optional)
SOUSCHEF_DATA_DIR=./data/souschef       # SQLite database and analysis history
SOUSCHEF_STORAGE_DIR=./data/storage     # Generated artefacts and conversions
POSTGRES_DATA_DIR=./data/postgres       # PostgreSQL database files
MINIO_DATA_DIR=./data/minio             # MinIO object storage data
```

The storage paths default to `./data/` subdirectories (relative to docker-compose.yml) but can be set to any absolute or relative path. This allows you to:
- Store data on different volumes or network storage
- Easily backup and restore data by copying directories
- Share data between development and production environments

See [Docker Deployment Guide](docs/docker-deployment.md#persistent-storage-configuration) for detailed configuration options.

**Docker Compose (recommended for development):**

```bash
# Using PostgreSQL (default, production-ready)
docker compose up

# Or if you prefer SQLite (lightweight, local storage only):
# 1. Set in .env: SOUSCHEF_DB_BACKEND=sqlite
# 2. Run normally: docker compose up
```

**Database Options:**

- **PostgreSQL** (default):
  - Robust, production-ready database server
  - Recommended for all deployments
  - Better concurrency and performance
  - Data stored in `./data/postgres/`

- **SQLite**:
  - Lightweight, embedded database
  - Good for development and testing
  - Set `SOUSCHEF_DB_BACKEND=sqlite` in .env
  - Data stored in `./data/souschef/`

**Example with SQLite:**
```bash
# In .env, set:
SOUSCHEF_DB_BACKEND=sqlite
# Then start normally:
docker compose up
```

**Example with PostgreSQL (default):**
```yaml
version: '3.8'
services:
  souschef-ui:
    build: .
    ports:
      - "9999:9999"
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_PORT=9999
      - STREAMLIT_SERVER_HEADLESS=true
      - SOUSCHEF_DB_BACKEND=postgres
      - SOUSCHEF_DB_HOST=postgres
      - SOUSCHEF_DB_PORT=5432
      - SOUSCHEF_DB_NAME=souschef
      - SOUSCHEF_DB_USER=souschef
      - SOUSCHEF_DB_PASSWORD=souschef
    restart: unless-stopped
```

**Features:**

- Clean, professional design matching documentation standards
- Real-time cookbook analysis with progress indicators
- **Interactive dependency visualization** with Plotly graphs and NetworkX analysis
- **Static graph visualization** with matplotlib for reports and documentation
- **Real-time progress tracking** for all analysis operations
- Migration planning wizards with effort estimation
- Validation reporting dashboard with conversion quality metrics
- Cross-platform compatibility (Linux, macOS, Windows)

### Advanced UI Features

#### Interactive Dependency Visualization

The UI includes sophisticated dependency graph visualization powered by NetworkX and Plotly:

- **Graph Analysis**: Automatic detection of cookbook dependencies, circular references, and migration ordering
- **Interactive Exploration**: Zoom, pan, and hover over nodes to explore complex dependency relationships
- **Color Coding**: Visual distinction between cookbooks, dependencies, community cookbooks, and circular dependencies
- **Static Export**: Matplotlib-based static graphs for reports and documentation
- **Large Graph Support**: Optimised layouts for complex cookbook ecosystems

#### Real-Time Progress Tracking

All analysis operations include comprehensive progress feedback:

- **Progress Bars**: Visual progress indicators for long-running operations
- **Status Updates**: Real-time status messages during analysis phases
- **Operation Tracking**: Separate progress tracking for dependency analysis, validation, and migration planning
- **Error Handling**: Graceful error display with recovery suggestions

#### Enhanced User Experience

- **Responsive Design**: Clean, professional interface that works across different screen sizes
- **Export Options**: Download analysis results, graphs, and migration plans
- **Session Persistence**: Maintain analysis state across page refreshes
- **Quick Actions**: One-click access to common migration tasks

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
- MCP-compatible client (Claude Desktop, VS Code 1.102+ with GitHub Copilot, etc.)

### Quick Start

1. **Install SousChef**:

   ```bash
   pip install mcp-souschef
   ```

2. **Configure Your MCP Client**:

   Use the pre-configured files in the `config/` directory for quick setup with Claude Desktop, VS Code Copilot, or other MCP clients.

   **Claude Desktop** (macOS):

   ```bash
   cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   # Restart Claude Desktop
   ```

   **Claude Desktop (Docker - published image):**

   ```bash
   cp config/claude-desktop-docker-ghcr.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   # Restart Claude Desktop
   ```

   **VS Code + GitHub Copilot** (requires VS Code 1.102+):

   ```bash
   # macOS/Linux
   cp config/vscode-copilot.json ~/.config/Code/User/mcp.json

   # Windows
   copy config\vscode-copilot.json %APPDATA%\Code\User\mcp.json

   # Reload VS Code window, then trust the server when prompted
   ```

   **VS Code + GitHub Copilot (Docker - published image):**

   ```bash
   # macOS/Linux
   cp config/vscode-copilot-docker-ghcr.json ~/.config/Code/User/mcp.json

   # Windows
   copy config\vscode-copilot-docker-ghcr.json %APPDATA%\Code\User\mcp.json

   # Reload VS Code window, then trust the server when prompted
   ```

   **See [config/CONFIGURATION.md](config/CONFIGURATION.md) for:**
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

**Chef Migration:**
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

**Ansible Upgrades:**
- `ansible assess` - Assess current Ansible environment and version compatibility
- `ansible plan` - Generate detailed upgrade plan between Ansible versions
- `ansible eol` - Check end-of-life status for Ansible versions
- `ansible validate-collections` - Validate collection compatibility with target version
- `ansible detect-python` - Detect Python version in Ansible environment

**User Interfaces:**
- `ui` - Launch the Visual Migration Planning Interface

#### Ansible CLI Examples

**Environment Assessment:**
```bash
# Assess current Ansible environment
souschef ansible assess --environment-path /path/to/ansible

# Example output:
# - Detected Ansible version and Python version
# - Lists all installed collections
# - Warns about EOL versions
# - Exports results to JSON
```

**Upgrade Planning:**
```bash
# Generate upgrade plan from Ansible 2.9 to 2.17
souschef ansible plan --current 2.9 --target 2.17

# Example output:
# - Breaking changes by category
# - Deprecated features with alternatives
# - Collection compatibility analysis
# - Testing recommendations
# - Risk assessment
```

**EOL Status:**
```bash
# Check if Ansible 2.9 is end-of-life
souschef ansible eol --version 2.9

# Example output:
# - EOL status and date
# - Community/Core edition info
# - Recommended upgrade paths
```

**Collection Validation:**
```bash
# Validate collections from requirements.yml
souschef ansible validate-collections --requirements-file requirements.yml --ansible-version 2.17

# Example output:
# - Compatibility status for each collection
# - Breaking changes detected
# - Dependency conflicts
# - Recommended collection versions
```

**Python Detection:**
```bash
# Detect Python version in Ansible environment
souschef ansible detect-python --environment-path /path/to/ansible

# Example output:
# - Python version used by Ansible
# - Compatibility with target Ansible version
# - Required Python version for upgrade
```

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

- Pre-commit hooks auto-update `poetry.lock` when `pyproject.toml` changes
- CI validates lock file on every PR
- Dependabot sends weekly dependency updates

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
- **83% Coverage**: Comprehensive test coverage approaching the 90% target for production readiness

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

## Support & Community

- **Issues**: [GitHub Issues](https://github.com/kpeacocke/souschef/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- **Documentation**: [Wiki](https://github.com/kpeacocke/souschef/wiki)

---

## SousChef

- `default` - Default value if specified
- `required` - Whether the property is required (true/false)

**Action Extraction:**

- Modern format: `action :name do ... end`
- LWRP format: `actions :create, :delete, :update`
- Supports both formats and mixed declarations

### `convert_resource_to_task(resource_type: str, resource_name: str, action: str = "create", properties: str = "")`

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

```text
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
poetry run pytest tests/unit/test_server.py              # Core unit tests
poetry run pytest tests/unit/test_cli.py                 # CLI tests
poetry run pytest tests/e2e/test_mcp.py                  # MCP protocol tests
poetry run pytest tests/integration/test_integration.py         # Integration tests
poetry run pytest tests/integration/test_integration_accuracy.py # Accuracy validation
poetry run pytest tests/unit/test_enhanced_guards.py     # Guard conversion tests
poetry run pytest tests/unit/test_error_paths.py         # Error handling
poetry run pytest tests/unit/test_error_recovery.py      # Error recovery
poetry run pytest tests/integration/test_real_world_fixtures.py # Real-world cookbooks
poetry run pytest tests/unit/test_property_based.py      # Hypothesis fuzz tests
poetry run pytest tests/integration/test_performance.py         # Performance benchmarks
poetry run pytest tests/unit/test_snapshots.py           # Snapshot regression tests

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
  - Sample Chef cookbooks in `tests/integration/fixtures/`
   - Multiple cookbook types: apache2, docker, mysql, nodejs, legacy Chef 12, Habitat plans
   - Real-world metadata, recipes, attributes, and resources
   - Used across integration and accuracy testing

### Test Coverage

The project maintains 91% test coverage, exceeding the 90% target. Run coverage with HTML report:

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

Thank you for your interest in contributing to SousChef!

**Before you start**, please read the [**Architecture Guide**](docs/ARCHITECTURE.md) to understand where different code belongs and why. This is essential for understanding how to structure your contributions.

For complete contributing guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md), which includes:

- Development setup instructions
- Code standards and quality tools
- Testing requirements and patterns
- Commit conventions and PR process
- Release procedures

**Quick Checklist for Contributions:**

1. Read [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) to understand module structure
2. Ensure all tests pass: `poetry run pytest`
3. Code passes linting: `poetry run ruff check .`
4. Code is formatted: `poetry run ruff format .`
5. Type hints are complete: `poetry run mypy souschef`
6. Coverage maintained at 90%+
7. All functions have docstrings
8. Follow [conventional commits](CONTRIBUTING.md#commit-message-format)

Questions? Check [ARCHITECTURE.md](docs/ARCHITECTURE.md) for module responsibilities or [CONTRIBUTING.md](CONTRIBUTING.md) for the full developer guide.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
