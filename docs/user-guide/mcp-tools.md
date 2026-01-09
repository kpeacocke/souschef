# MCP Tools Reference

SousChef provides **38 specialized MCP tools** organized across **9 capability areas** for comprehensive Chef-to-Ansible migration. Each tool is designed to work seamlessly with any AI model through the Model Context Protocol.

!!! tip "Working with MCP Tools"
    These tools are invoked through your AI assistant (Claude, GPT-4, Red Hat AI, local models, etc.). Simply describe what you need in natural language, and your AI assistant will use the appropriate tools.

## Quick Reference by Capability Area

| Capability | Tools | Use Case |
|------------|-------|----------|
| [Chef Cookbook Analysis](#1-chef-cookbook-analysis-parsing) | 8 tools | Parse and analyze Chef cookbooks, recipes, resources |
| [Conversion Engine](#2-chef-to-ansible-conversion-engine) | 3 tools | Convert Chef resources and recipes to Ansible |
| [Search & Inventory](#3-chef-search-inventory-integration) | 3 tools | Transform Chef search to Ansible inventory |
| [InSpec Integration](#4-inspec-integration-validation) | 3 tools | Convert InSpec tests to Ansible validation |
| [Data Bags & Secrets](#5-data-bags-secrets-management) | 3 tools | Migrate data bags to Ansible vars/vault |
| [Environments](#6-environment-configuration-management) | 3 tools | Convert Chef environments to inventory |
| [AWX/AAP Integration](#7-awxansible-automation-platform-integration) | 4 tools | Generate AWX job templates and workflows |
| [Habitat to Container](#8-chef-habitat-to-container-conversion) | 3 tools | Modernize Habitat to Docker/Compose |
| [Deployment & Assessment](#9-advanced-deployment-patterns-migration-assessment) | 8 tools | Migration planning and modern deployments |

---

## 1. Chef Cookbook Analysis & Parsing

Complete cookbook introspection and analysis tools for understanding your Chef infrastructure.

### parse_template

Parse ERB templates with automatic Jinja2 conversion and variable extraction.

**Parameters:**
- `template_path` (string, required): Path to the ERB template file

**Returns:**
- Converted Jinja2 template content
- List of extracted variables with types
- ERB-to-Jinja2 syntax mapping
- Conversion notes and warnings

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse the template at examples/database/templates/database.yml.erb
    and show me the Jinja2 conversion
    ```

=== "CLI"
    ```bash
    souschef-cli template examples/database/templates/database.yml.erb
    ```

**Common Use Cases:**
- Converting ERB templates to Jinja2 before playbook migration
- Identifying variables that need to be defined in Ansible
- Understanding template logic and dependencies

---

### parse_custom_resource

Extract properties, attributes, and actions from Chef custom resources and LWRPs.

**Parameters:**
- `resource_path` (string, required): Path to the custom resource file

**Returns:**
- Resource properties with types and defaults
- Available actions and their implementations
- Resource attributes and usage patterns
- Dependencies and requirements

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Analyze the custom resource at examples/database/resources/user.rb
    and explain what properties and actions it provides
    ```

=== "CLI"
    ```bash
    souschef-cli resource examples/database/resources/user.rb
    ```

**Common Use Cases:**
- Understanding custom resource interfaces
- Planning Ansible module or role equivalents
- Identifying resource dependencies

---

### list_directory

Navigate and explore cookbook directory structures with filtering.

**Parameters:**
- `directory_path` (string, required): Path to the directory
- `pattern` (string, optional): Glob pattern for filtering (e.g., "*.rb")

**Returns:**
- List of files and directories
- File types and sizes
- Directory structure overview

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    List all Ruby files in the examples/database cookbook
    ```

=== "CLI"
    ```bash
    souschef-cli ls examples/database --pattern "*.rb"
    ```

---

### read_file

Read cookbook files with comprehensive error handling.

**Parameters:**
- `file_path` (string, required): Path to the file
- `encoding` (string, optional): File encoding (default: utf-8)

**Returns:**
- File contents
- File metadata (size, modification time)
- Encoding information

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Read the contents of examples/database/metadata.rb
    ```

=== "CLI"
    ```bash
    souschef-cli cat examples/database/metadata.rb
    ```

---

### read_cookbook_metadata

Parse metadata.rb files for dependencies and cookbook information.

**Parameters:**
- `metadata_path` (string, required): Path to metadata.rb file

**Returns:**
- Cookbook name and version
- Dependencies with version constraints
- Maintainer information
- License and source repository
- Platform support

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse the metadata from examples/database/metadata.rb
    and show me all dependencies
    ```

=== "CLI"
    ```bash
    souschef-cli metadata examples/database/metadata.rb
    ```

**Common Use Cases:**
- Understanding cookbook dependencies
- Planning migration order
- Identifying platform requirements

---

### parse_recipe

Analyze Chef recipes and extract resources, actions, and properties.

**Parameters:**
- `recipe_path` (string, required): Path to the Chef recipe file

**Returns:**
- List of resources with types and names
- Resource properties and actions
- Guard conditions (only_if, not_if)
- Notifies and subscribes relationships
- Variables and attributes used

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse examples/database/recipes/default.rb and
    show me all the resources it contains
    ```

=== "CLI"
    ```bash
    souschef-cli recipe examples/database/recipes/default.rb
    ```

**Common Use Cases:**
- Understanding recipe structure
- Identifying conversion complexity
- Extracting resource dependencies

---

### parse_attributes

Parse attribute files with **advanced precedence resolution** across 6 levels.

**Parameters:**
- `attributes_path` (string, required): Path to the attributes file

**Returns:**
- Attributes organized by precedence level:
  - **default**: Standard defaults
  - **force_default**: Override default precedence
  - **normal**: Node-specific values
  - **override**: Override normal values
  - **force_override**: Highest priority overrides
  - **automatic**: System-discovered values
- Attribute paths and values
- Type information

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse examples/database/attributes/default.rb
    and show me the attribute precedence levels
    ```

=== "CLI"
    ```bash
    souschef-cli attributes examples/database/attributes/default.rb
    ```

**Common Use Cases:**
- Understanding attribute hierarchy
- Converting to Ansible variable precedence
- Identifying configuration patterns

---

### list_cookbook_structure

Display complete cookbook directory hierarchy.

**Parameters:**
- `cookbook_path` (string, required): Path to the cookbook root

**Returns:**
- Tree view of cookbook structure
- File counts by type
- Size information
- Standard vs custom directories

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Show me the complete structure of examples/database cookbook
    ```

=== "CLI"
    ```bash
    souschef-cli structure examples/database
    ```

---

## 2. Chef-to-Ansible Conversion Engine

Advanced resource-to-task conversion with intelligent Ansible module selection.

### convert_resource_to_task

Transform individual Chef resources to Ansible tasks with module mapping.

**Parameters:**
- `resource_type` (string, required): Chef resource type (e.g., "package", "service")
- `resource_name` (string, required): Resource name
- `properties` (object, optional): Resource properties as JSON
- `guards` (object, optional): Guard conditions (only_if, not_if)

**Returns:**
- Ansible task YAML
- Module selection reasoning
- Parameter mappings
- Guard-to-when conversions
- Idempotency notes

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert a Chef package resource named "nginx" with action "install"
    to an Ansible task
    ```

=== "CLI"
    ```bash
    souschef-cli convert package nginx --action install
    ```

**Supported Resource Types:**
- Package management: `package`, `apt_package`, `yum_package`
- Services: `service`, `systemd_unit`
- Files: `file`, `directory`, `template`, `cookbook_file`
- Users/Groups: `user`, `group`
- Execution: `execute`, `bash`, `script`
- And 50+ more Chef resources

---

### generate_playbook_from_recipe

Generate complete Ansible playbooks from Chef recipes.

**Parameters:**
- `recipe_path` (string, required): Path to the Chef recipe file
- `playbook_name` (string, optional): Custom playbook name

**Returns:**
- Complete Ansible playbook YAML
- Variable definitions
- Handler mappings
- Role structure recommendations
- Conversion notes

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate an Ansible playbook from examples/database/recipes/default.rb
    ```

=== "CLI"
    ```bash
    souschef-cli convert-recipe examples/database/recipes/default.rb > database.yml
    ```

**Features:**
- ✅ Automatic handler generation from notifies
- ✅ Variable extraction from attributes
- ✅ Guard condition conversion to when/unless
- ✅ Resource dependency preservation
- ✅ Best practice task naming

---

### Enhanced Guard Handling

Automatically convert complex Chef guard conditions to Ansible when/unless.

**Supported Guard Types:**

**Array-based guards:**
```ruby
# Chef
only_if ['test -f /path/file', 'systemctl is-active nginx']

# Ansible
when:
  - stat /path/file
  - "'active' in nginx_status.stdout"
```

**Lambda/proc syntax:**
```ruby
# Chef
only_if { ::File.exist?('/etc/nginx') }

# Ansible
when: nginx_config_dir.stat.exists
```

**Do-end blocks:**
```ruby
# Chef
not_if do
  ::File.exist?('/etc/app.conf') &&
  node['app']['version'] >= '2.0'
end

# Ansible
when: not (app_conf.stat.exists and app_version is version('2.0', '>='))
```

**Multiple guard types:**
- Platform checks: `node['platform']`
- Attribute checks: `node['app']['enabled']`
- File/directory existence
- Command execution results
- Complex boolean logic with AND/OR

---

## 3. Chef Search & Inventory Integration

Convert Chef search patterns to dynamic Ansible inventory.

### convert_chef_search_to_inventory

Transform Chef search queries to Ansible inventory groups.

**Parameters:**
- `search_query` (string, required): Chef search query (e.g., "role:webserver AND environment:production")
- `group_name` (string, required): Target Ansible inventory group name

**Returns:**
- Ansible inventory YAML/INI format
- Host variables mapping
- Group variable recommendations
- Dynamic inventory script template

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert Chef search "role:database AND chef_environment:production"
    to an Ansible inventory group named "production_databases"
    ```

---

### generate_dynamic_inventory_script

Create dynamic inventory scripts from Chef server queries.

**Parameters:**
- `chef_server_url` (string, required): Chef server URL
- `search_queries` (array, required): List of search queries with group names
- `output_format` (string, optional): "json" or "script" (default: script)

**Returns:**
- Executable Python script for dynamic inventory
- Chef API integration code
- Caching mechanism
- Error handling

---

### analyze_chef_search_patterns

Discover and analyze search usage in cookbooks.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook

**Returns:**
- All search patterns found in recipes
- Node attribute queries
- Data bag queries
- Inventory group recommendations

---

## 4. InSpec Integration & Validation

Complete InSpec-to-Ansible testing pipeline.

### parse_inspec_profile

Parse InSpec profiles and extract controls.

**Parameters:**
- `profile_path` (string, required): Path to InSpec profile directory

**Returns:**
- Profile metadata
- Control definitions
- Resource usage
- Dependencies

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse the InSpec profile at tests/inspec/database-profile
    ```

=== "CLI"
    ```bash
    souschef-cli inspec-parse tests/inspec/database-profile
    ```

---

### convert_inspec_to_test

Convert InSpec controls to Testinfra or Ansible assert tasks.

**Parameters:**
- `inspec_profile` (string, required): Path to InSpec profile
- `output_format` (string, required): "testinfra" or "ansible"

**Returns:**
- Converted test code
- Assertion mappings
- Resource equivalents
- Fixtures and setup code

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert InSpec profile at tests/inspec/nginx to Ansible assert tasks
    ```

=== "CLI"
    ```bash
    souschef-cli inspec-convert tests/inspec/nginx --format ansible
    ```

---

### generate_inspec_from_recipe

Auto-generate InSpec validation from Chef recipes.

**Parameters:**
- `recipe_path` (string, required): Path to Chef recipe

**Returns:**
- InSpec profile structure
- Controls for each resource
- Automated assertions
- Test coverage recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate InSpec tests from examples/database/recipes/default.rb
    ```

=== "CLI"
    ```bash
    souschef-cli inspec-generate examples/database/recipes/default.rb
    ```

---

## 5. Data Bags & Secrets Management

Chef data bags to Ansible vars/vault conversion.

### convert_chef_databag_to_vars

Transform data bags to Ansible variable files.

**Parameters:**
- `databag_path` (string, required): Path to data bag directory or file
- `output_format` (string, optional): "yaml" or "json" (default: yaml)

**Returns:**
- Ansible variable file content
- Variable naming conventions
- Encryption recommendations for sensitive data

---

### generate_ansible_vault_from_databags

Convert encrypted data bags to Ansible Vault.

**Parameters:**
- `databag_path` (string, required): Path to encrypted data bag
- `vault_password` (string, optional): Vault password for encryption

**Returns:**
- Ansible Vault encrypted file
- Vault ID recommendations
- Key management guidance

**Security Note:** Never log or display vault passwords. Use environment variables or secure prompts.

---

### analyze_chef_databag_usage

Analyze data bag usage patterns in cookbooks.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook

**Returns:**
- Data bag queries found
- Variable usage patterns
- Migration recommendations
- Vault encryption candidates

---

## 6. Environment & Configuration Management

Chef environments to Ansible inventory groups.

### convert_chef_environment_to_inventory_group

Transform Chef environments to inventory.

**Parameters:**
- `environment_file` (string, required): Path to Chef environment file (.rb or .json)
- `inventory_group_name` (string, required): Target inventory group name

**Returns:**
- Ansible inventory group with variables
- Environment-to-inventory mapping
- Variable precedence recommendations

---

### generate_inventory_from_chef_environments

Generate complete inventory from environments.

**Parameters:**
- `environments_dir` (string, required): Path to Chef environments directory

**Returns:**
- Multi-environment inventory structure
- Group_vars organization
- Host pattern recommendations

---

### analyze_chef_environment_usage

Analyze environment usage in cookbooks.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook

**Returns:**
- Environment-specific logic
- Attribute overrides by environment
- Migration impact analysis

---

## 7. AWX/Ansible Automation Platform Integration

Enterprise AWX/AAP configuration generation.

### generate_awx_job_template_from_cookbook

Create AWX job templates from cookbooks.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook
- `template_name` (string, required): AWX job template name
- `project_name` (string, optional): AWX project name
- `inventory_name` (string, optional): AWX inventory name

**Returns:**
- AWX job template JSON configuration
- Playbook requirements
- Variable prompts
- Credentials configuration

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate an AWX job template from examples/database cookbook
    named "Deploy Database Server"
    ```

---

### generate_awx_workflow_from_chef_runlist

Transform Chef run-lists to AWX workflows.

**Parameters:**
- `runlist` (string, required): Chef run-list (e.g., "recipe[app::deploy],recipe[app::configure]")
- `workflow_name` (string, required): AWX workflow template name

**Returns:**
- AWX workflow template JSON
- Job dependencies and ordering
- Success/failure paths
- Approval nodes recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Create an AWX workflow from Chef run-list
    "recipe[database::install],recipe[database::configure],recipe[app::deploy]"
    ```

---

### generate_awx_project_from_cookbooks

Generate AWX projects from cookbook collections.

**Parameters:**
- `cookbooks_dir` (string, required): Path to cookbooks directory
- `project_name` (string, required): AWX project name
- `scm_url` (string, optional): Git repository URL

**Returns:**
- AWX project configuration
- Directory structure for Git repository
- Requirements files (requirements.yml, requirements.txt)
- Project organization best practices

---

### generate_awx_inventory_source_from_chef

Create dynamic inventory sources from Chef server.

**Parameters:**
- `chef_server_url` (string, required): Chef server URL
- `environment` (string, optional): Chef environment filter
- `inventory_source_name` (string, required): AWX inventory source name

**Returns:**
- AWX inventory source configuration
- Custom dynamic inventory script
- Sync schedule recommendations
- Chef API credentials setup

---

## 8. Chef Habitat to Container Conversion

Modernize Habitat applications to containerized deployments.

### parse_habitat_plan

Parse Chef Habitat plan files (plan.sh) and extract package metadata.

**Parameters:**
- `plan_path` (string, required): Path to Habitat plan.sh file

**Returns:**
- Package name, origin, and version
- Build and runtime dependencies
- Build hooks (do_build, do_install, do_prepare)
- Service configuration and exports
- Configuration templates

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse the Habitat plan at /path/to/habitat/plan.sh
    ```

=== "CLI"
    ```bash
    souschef-cli habitat-parse /path/to/habitat/plan.sh
    ```

---

### convert_habitat_to_dockerfile

Convert Chef Habitat plans to production-ready Dockerfiles.

**Parameters:**
- `plan_path` (string, required): Path to Habitat plan.sh
- `base_image` (string, optional): Docker base image (default: ubuntu:22.04)
- `include_security_scan` (boolean, optional): Add security scanning (default: true)

**Returns:**
- Multi-stage Dockerfile
- Build dependencies management
- Security best practices (non-root user, minimal layers)
- Health checks and entry points
- .dockerignore recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert Habitat plan at /path/to/plan.sh to a Dockerfile
    using alpine:3.18 as base image
    ```

**Features:**
- ✅ Multi-stage builds for minimal image size
- ✅ Security scanning integration (Snyk, Trivy)
- ✅ Non-root user execution
- ✅ Health check configuration
- ✅ Environment variable mapping

---

### generate_compose_from_habitat

Generate docker-compose.yml from multiple Habitat plans.

**Parameters:**
- `plan_paths` (array, required): List of Habitat plan.sh paths
- `network_name` (string, optional): Docker network name
- `include_volumes` (boolean, optional): Add volume mounts (default: true)

**Returns:**
- docker-compose.yml for multi-service deployment
- Service dependencies and networking
- Volume and secret management
- Environment configuration
- Development vs production profiles

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate docker-compose.yml from Habitat plans:
    - /path/to/web/plan.sh
    - /path/to/api/plan.sh
    - /path/to/database/plan.sh
    using network name "myapp_network"
    ```

**Features:**
- ✅ Service orchestration and dependencies
- ✅ Health checks and restart policies
- ✅ Secrets management integration
- ✅ Development and production profiles
- ✅ Resource limits and constraints

---

## 9. Advanced Deployment Patterns & Migration Assessment

Modern deployment strategies and migration planning.

### convert_chef_deployment_to_ansible_strategy

Convert deployment recipes to Ansible strategies.

**Parameters:**
- `recipe_path` (string, required): Path to deployment recipe
- `strategy_type` (string, optional): "rolling", "blue_green", or "canary"

**Returns:**
- Ansible playbook with deployment strategy
- Pre/post deployment tasks
- Validation and rollback procedures
- Monitoring integration points

---

### generate_blue_green_deployment_playbook

Create blue/green deployment playbooks.

**Parameters:**
- `app_playbook` (string, required): Path to application playbook
- `load_balancer_type` (string, required): "haproxy", "nginx", or "aws_elb"

**Returns:**
- Blue/green deployment orchestration
- Load balancer switching logic
- Health check integration
- Rollback procedures

---

### generate_canary_deployment_strategy

Generate canary deployment configurations.

**Parameters:**
- `app_playbook` (string, required): Path to application playbook
- `canary_percentage` (number, optional): Initial canary percentage (default: 10)
- `increment_percentage` (number, optional): Traffic increment per stage (default: 25)

**Returns:**
- Canary deployment playbook
- Traffic splitting configuration
- Metrics collection points
- Automatic rollback triggers

---

### validate_conversion

Comprehensive validation of Chef-to-Ansible conversions across multiple dimensions.

**Parameters:**
- `conversion_type` (string, required): Type of conversion - "resource", "recipe", "playbook", "template"
- `original_content` (string, optional): Original Chef content for comparison
- `result_content` (string, required): Converted Ansible content to validate
- `output_format` (string, optional): Output format - "text" (default), "json", "summary"

**Returns:**
- Validation results organized by severity (ERROR, WARNING, INFO)
- Issues categorized by type:
  - **Syntax**: YAML, Jinja2, Python syntax validation
  - **Semantic**: Logic equivalence, variable usage, dependencies
  - **Best Practice**: Ansible conventions, idempotency, organization
  - **Security**: Privilege escalation, sensitive data handling
  - **Performance**: Efficiency recommendations and optimizations
- Overall validation status: PASSED or FAILED
- Actionable recommendations for each issue

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Validate the converted Ansible task for installing nginx
    and check for syntax errors and best practices
    ```

=== "CLI"
    ```bash
    souschef-cli validate resource --content "$(cat nginx_task.yml)" --format json
    ```

**Validation Levels:**

- **ERROR** :octicons-x-circle-fill-24:{ .error }: Critical issues preventing execution
- **WARNING** :octicons-alert-fill-24:{ .warning }: Potential problems or anti-patterns
- **INFO** :octicons-info-16:{ .info }: Improvement suggestions and best practices

**Output Formats:**

- **text**: Detailed human-readable report with all findings
- **json**: Structured JSON for CI/CD integration
- **summary**: Quick overview with counts only

---

### analyze_chef_application_patterns

Identify application deployment patterns.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook

**Returns:**
- Detected deployment patterns (monolithic, microservices, etc.)
- Infrastructure patterns
- Configuration management approaches
- Modernization recommendations

---

### assess_chef_migration_complexity

Comprehensive migration complexity assessment.

**Parameters:**
- `cookbooks_path` (string, required): Path to cookbooks directory or single cookbook
- `include_dependencies` (boolean, optional): Analyze dependencies (default: true)

**Returns:**
- Complexity score (1-10 scale)
- Risk factors and mitigation strategies
- Resource breakdown and conversion difficulty
- Estimated effort (hours/days)
- Recommended migration order
- Prerequisite identification

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Assess the migration complexity for all cookbooks in /path/to/cookbooks
    including dependency analysis
    ```

---

### generate_migration_plan

Create detailed migration execution plans.

**Parameters:**
- `cookbooks` (array, required): List of cookbook paths
- `include_timeline` (boolean, optional): Include timeline estimates (default: true)
- `include_resources` (boolean, optional): Include resource requirements (default: true)

**Returns:**
- Phase-by-phase migration plan
- Task breakdown with dependencies
- Timeline with milestones
- Resource allocation recommendations
- Risk management strategy
- Testing and validation checkpoints

---

### analyze_cookbook_dependencies

Analyze dependencies and determine optimal migration order.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook

**Returns:**
- Direct and transitive dependencies
- Dependency graph visualization (Mermaid format)
- Circular dependency detection
- Recommended migration sequence
- Version compatibility analysis

---

### generate_migration_report

Generate comprehensive migration reports for stakeholders.

**Parameters:**
- `assessment_data` (object, required): Output from assess_chef_migration_complexity
- `report_type` (string, optional): "executive" or "technical" (default: technical)
- `output_format` (string, optional): "markdown", "html", or "pdf" (default: markdown)

**Returns:**
- Executive summary (for executive reports)
- Technical details and implementation plan
- Cost/benefit analysis
- Risk assessment matrix
- Resource requirements
- Success metrics and KPIs

---

## Performance Profiling Tools

Profile cookbook parsing performance to optimize large-scale migrations.

### profile_cookbook_performance

Profile all parsing operations for an entire cookbook.

**Parameters:**
- `cookbook_path` (string, required): Path to cookbook root directory

**Returns:**
- Execution time for each operation (recipes, attributes, templates, resources)
- Peak memory usage
- Performance bottlenecks identification
- Optimization recommendations
- Before/after comparison support

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Profile the performance of parsing examples/database cookbook
    and identify any bottlenecks
    ```

=== "CLI"
    ```bash
    souschef-cli profile examples/database --output profile_report.txt
    ```

---

### profile_parsing_operation

Profile a specific parsing operation with detailed cProfile statistics.

**Parameters:**
- `operation_type` (string, required): "recipe", "attributes", "template", "resource", or "metadata"
- `file_path` (string, required): Path to the file to profile
- `detailed` (boolean, optional): Include cProfile statistics (default: false)

**Returns:**
- Execution time
- Peak memory usage
- Detailed function call statistics (if detailed=true)
- Top time-consuming functions
- Performance recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Profile parsing examples/database/recipes/default.rb
    with detailed statistics
    ```

=== "CLI"
    ```bash
    souschef-cli profile-operation recipe examples/database/recipes/default.rb --detailed
    ```

---

## Best Practices

### Tool Selection Guide

1. **Start with Assessment**: Use `assess_chef_migration_complexity` before detailed conversion
2. **Understand Structure**: Use `list_cookbook_structure` and `analyze_cookbook_dependencies` to map your cookbooks
3. **Parse Before Converting**: Always parse recipes/resources before conversion to understand complexity
4. **Validate Everything**: Use `validate_conversion` after each conversion step
5. **Test Incrementally**: Convert and test one recipe at a time

### Workflow Recommendations

**For New Migrations:**
1. `assess_chef_migration_complexity` - Get overall assessment
2. `generate_migration_plan` - Create execution plan
3. `analyze_cookbook_dependencies` - Determine order
4. Start conversions with `generate_playbook_from_recipe`
5. Validate with `validate_conversion`

**For AWX/AAP Deployments:**
1. Convert recipes to playbooks first
2. Use `generate_awx_job_template_from_cookbook` for each cookbook
3. Create workflows with `generate_awx_workflow_from_chef_runlist`
4. Set up dynamic inventory with `generate_awx_inventory_source_from_chef`

**For Habitat Migrations:**
1. Parse plans with `parse_habitat_plan`
2. Convert with `convert_habitat_to_dockerfile`
3. Orchestrate with `generate_compose_from_habitat`
4. Test and validate containers

### Performance Optimization

**For Large Cookbooks:**
- Use `profile_cookbook_performance` to identify bottlenecks
- Profile specific operations with `profile_parsing_operation --detailed`
- Batch similar conversions together
- Consider parallel processing for independent cookbooks

**Memory Management:**
- Profile memory usage before production migrations
- Monitor peak memory for large recipe files
- Implement chunking for very large cookbooks

---

## Related Documentation

- [CLI Usage](cli-usage.md) - Command-line interface for direct tool access
- [Examples](examples.md) - Real-world migration examples and patterns
- [Migration Guide](../migration-guide/overview.md) - Complete migration methodology
- [API Reference](../api-reference/server.md) - Technical implementation details

---

## Getting Help

If you encounter issues or need assistance with specific tools:

1. Check the [Troubleshooting](../getting-started/configuration.md#troubleshooting) section
2. Review [Examples](examples.md) for common patterns
3. See [Contributing](../contributing.md) to report issues or request features

!!! tip "AI Assistant Support"
    Your AI assistant has access to all these tools through MCP. Simply describe what you need in natural language, and it will use the appropriate tools to help you migrate your Chef infrastructure to Ansible.
