# MCP Tools Reference

SousChef provides **24 specialised MCP tools** for comprehensive Chef-to-Ansible migration. Each tool is designed to work seamlessly with any AI model through the Model Context Protocol.

!!! tip "Working with MCP Tools"
    These tools are invoked through your AI assistant (Claude, GPT-4, Red Hat AI, local models, etc.). Simply describe what you need in natural language, and your AI assistant will use the appropriate tools.

!!! info "About the Tool Count"
    **Why 24 tools here but the server shows more?**

    The MCP server actually provides **34 total tools** (32 public + 2 internal). This guide documents the **24 primary tools** you'll use for migrations. The remaining 10 are:

    - **Internal filesystem operations** - Low-level file reading and directory listing used by other tools
    - **Helper utilities** - Supporting functions that other tools call

    Your AI assistant may use these additional tools automatically behind the scenes (e.g., when a tool needs to read a file, it calls the internal file reading tool). You don't need to invoke them directly - just use the 24 documented tools and let your AI assistant handle the rest.

## Quick Reference by Capability Area

| Capability | Tools | Use Case |
|------------|-------|----------|
| [Cookbook Analysis & Parsing](#cookbook-analysis-parsing) | 8 tools | Parse and analyze Chef cookbooks, recipes, resources |
| [Resource Conversion](#resource-conversion) | 1 tool | Convert Chef resources to Ansible tasks |
| [InSpec Integration](#inspec-integration) | 2 tools | Convert InSpec tests and generate from recipes |
| [Data Bags](#data-bags) | 2 tools | Migrate data bags to Ansible vars/vault |
| [Environments](#environments) | 3 tools | Convert Chef environments to inventory |
| [Migration Assessment](#migration-assessment) | 5 tools | Assess complexity and plan migrations |
| [Habitat](#habitat) | 1 tool | Parse Habitat plans |
| [Performance](#performance) | 2 tools | Profile and optimise parsing operations |

---

## Cookbook Analysis & Parsing

Complete cookbook introspection and analysis tools for understanding your Chef infrastructure.

### parse_template

Parse ERB templates with automatic Jinja2 conversion and variable extraction.

**What it does**: Converts Chef's ERB template files (Ruby-style templates) into Ansible's Jinja2 format. ERB and Jinja2 are both template languages that let you embed variables and logic into configuration files. In Chef you write `<%= hostname %>`, in Ansible it's `{{ hostname }}`. This tool automatically translates between the two syntaxes.

**Why you need this**: Chef cookbooks often contain dozens of template files for configs like `nginx.conf`, `httpd.conf`, `database.yml`, etc. Manually converting each one is tedious and error-prone. This tool does it instantly.

**What you get**:
- The converted Jinja2 template ready for Ansible
- A complete list of all variables referenced in the template
- Information about what those variables need to be defined as in your playbook

**Real-world example**: Your Chef template `templates/default/app.conf.erb` with Chef ERB syntax automatically becomes an Ansible-ready `app.conf.j2` with proper Jinja2 syntax, plus you get a list like "Variables needed: app_port, app_user, app_home".

**Parameters:**
- `path` (string, required): Path to the ERB template file

**Returns:**
- JSON string with extracted variables and Jinja2-converted template

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

---

### parse_custom_resource

Extract properties, attributes, and actions from Chef custom resources and LWRPs.

**What it does**: Analyses Chef custom resources (the Ruby files in your `resources/` directory) and extracts all the properties, actions, and configuration they define. Custom resources are reusable Chef components that encapsulate complex operations.

**Why you need this**: Custom resources are often the most complex parts of a Chef cookbook. Understanding what properties they accept and what actions they perform is critical for converting them to Ansible modules or roles. Without this tool, you'd need to manually read through Ruby code and trace execution paths.

**What you get**:
- Complete list of all properties the resource accepts (like `property :port, Integer`)
- All actions the resource can perform (like `:create`, `:delete`, `:configure`)
- Default values and validation rules
- Metadata about the resource's purpose

**Real-world example**: Your `resources/database_user.rb` file defines a custom Chef resource. This tool extracts that it has properties like `username`, `password`, `privileges`, and actions like `:create` and `:drop`, helping you understand what Ansible tasks you need to write.

**Parameters:**
- `path` (string, required): Path to the custom resource (.rb) file

**Returns:**
- JSON string with extracted properties, actions, and metadata

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

---

### list_directory

Navigate and explore cookbook directory structures.

**What it does**: Lists all files and directories in a given path, like the Unix `ls` command. Simple but essential for exploring unfamiliar cookbooks.

**Why you need this**: When you're migrating a cookbook you didn't write (or wrote years ago), you need to understand what's in it. This tool helps you discover recipes, templates, resources, and other files you need to convert.

**What you get**: A list of all files and directories in the specified location, making it easy to explore the cookbook structure.

**Real-world example**: Running this on `cookbooks/database/` shows you there are `recipes/`, `templates/`, `attributes/`, and `resources/` directories, helping you plan your migration strategy.

**Parameters:**
- `path` (string, required): Path to the directory

**Returns:**
- List of filenames in the directory, or an error message

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    List all files in the examples/database cookbook
    ```

=== "CLI"
    ```bash
    souschef-cli ls examples/database
    ```

---

### read_file

Read cookbook files with comprehensive error handling.

**What it does**: Reads and displays the contents of any file in your cookbook, like the Unix `cat` command. Provides detailed error messages if the file doesn't exist or can't be read.

**Why you need this**: Before converting Chef code, you often need to examine the actual content of recipes, metadata files, or configuration files. This tool makes that easy without leaving your AI assistant.

**What you get**: The complete contents of the file, with helpful error messages if something goes wrong (like "File not found" or "Permission denied").

**Real-world example**: Reading `metadata.rb` shows you the cookbook's dependencies, version, and description before you start migration planning.

**Parameters:**
- `path` (string, required): Path to the file

**Returns:**
- The contents of the file, or an error message

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

**What it does**: Reads and parses the `metadata.rb` file in a Chef cookbook, extracting structured information about the cookbook's name, version, dependencies, supported platforms, and more.

**Why you need this**: The metadata file is the "package.json" or "requirements.txt" of Chef cookbooks. It tells you what other cookbooks this one depends on, which is crucial for understanding migration order and complexity. Raw Ruby metadata files are hard to parse by eye.

**What you get**:
- Cookbook name and version
- All dependencies (like `depends 'apt', '>= 2.0'`)
- Supported platforms (like `supports 'ubuntu', '>= 18.04'`)
- License and maintainer information
- Long description of what the cookbook does

**Real-world example**: Parsing `database/metadata.rb` reveals it depends on the `postgresql` and `apt` cookbooks, so you need to migrate or handle those dependencies in Ansible too.

**Parameters:**
- `path` (string, required): Path to metadata.rb file

**Returns:**
- Formatted string with extracted metadata

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

---

### parse_recipe

Analyze Chef recipes and extract resources, actions, and properties.
**What it does**: Reads a Chef recipe file (the `.rb` files in `recipes/` directory) and extracts every resource declared in it, including the resource type, name, action, and all properties. Think of it as a Chef recipe translator that converts Ruby code into structured data.

**Why you need this**: Chef recipes are written in Ruby DSL, which can be difficult to convert to Ansible YAML by hand, especially for large recipes with dozens of resources. This tool breaks down the recipe into individual components you can convert one by one.

**What you get**:
- Every resource in the recipe (like `package 'nginx'`, `service 'nginx'`, `template '/etc/nginx.conf'`)
- The action for each resource (`:install`, `:start`, `:create`)
- All properties (like `source`, `variables`, `mode`)
- Guard conditions (like `only_if`, `not_if`)

**Real-world example**: Parsing `recipes/default.rb` shows it installs 5 packages, configures 3 services, and creates 8 template files. You can now convert each resource to an Ansible task systematically.
**Parameters:**
- `path` (string, required): Path to the Chef recipe (.rb) file

**Returns:**
- Formatted string with extracted Chef resources and their properties

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse examples/database/recipes/default.rb and
    show me all the resources and their actions
    ```

=== "CLI"
    ```bash
    souschef-cli recipe examples/database/recipes/default.rb
    ```

---

### parse_attributes

Parse Chef attributes files and extract attribute definitions with precedence.

**What it does**: Reads Chef attributes files (the `.rb` files in `attributes/` directory) and extracts all attribute definitions. Chef attributes are like variables that configure your cookbook. This tool handles Chef's complex 15-level precedence system (default, force_default, normal, override, force_override, automatic).

**Why you need this**: Chef's attribute precedence system is notoriously complex. Understanding which attribute value "wins" when multiple are defined is critical for correct Ansible variable migration. This tool resolves precedence automatically so you know exactly what values your Chef recipes will actually use.

**What you get**:
- All attributes defined in the file (like `default['nginx']['port'] = 80`)
- The precedence level of each attribute
- The final resolved value when precedence is enabled
- Equivalent Ansible variable structure

**Real-world example**: Your attributes file defines `default['app']['port'] = 3000` and `override['app']['port'] = 8080`. This tool tells you that `8080` wins due to override precedence, so your Ansible vars should use `app_port: 8080`.

**Parameters:**
- `path` (string, required): Path to the attributes (.rb) file
- `resolve_precedence` (boolean, optional, default: true): If true, resolves precedence conflicts and shows only winning values

**Returns:**
- Formatted string with extracted attributes

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse the attributes file at examples/database/attributes/default.rb
    and show me all attributes with their precedence levels
    ```

=== "CLI"
    ```bash
    souschef-cli attributes examples/database/attributes/default.rb
    ```

---

### list_cookbook_structure

List the structure of a Chef cookbook directory.

**What it does**: Scans an entire Chef cookbook directory and presents a structured view of all recipes, templates, resources, attributes, files, and other components. Like a "table of contents" for your cookbook.

**Why you need this**: Before migrating a cookbook, you need to understand its size and complexity. This tool gives you a bird's-eye view of everything that needs conversion, helping you estimate effort and plan your approach.

**What you get**:
- Complete directory tree of the cookbook
- Count of recipes, templates, resources, etc.
- File paths for each component
- Quick overview of cookbook complexity

**Real-world example**: Running this on your `database` cookbook shows it has 3 recipes, 8 templates, 2 custom resources, and 1 attributes file. You now know you need to create an Ansible role with 3 task files, 8 Jinja2 templates, and variable definitions.

**Parameters:**
- `path` (string, required): Path to the cookbook root directory

**Returns:**
- Formatted string showing the cookbook structure

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Show me the structure of the examples/database cookbook
    ```

=== "CLI"
    ```bash
    souschef-cli structure examples/database
    ```

---

## Resource Conversion

### convert_resource_to_task

Convert a Chef resource to an Ansible task with automatic module selection.

**What it does**: Takes a single Chef resource (like `package 'nginx'`) and converts it to the equivalent Ansible task with the appropriate module. Automatically selects the best Ansible module for the Chef resource type and handles property mapping.

**Why you need this**: Chef and Ansible have different syntax and different module names. Chef's `package` becomes Ansible's `apt`, `yum`, or `package`. Chef's `service` has different properties than Ansible's `service`. This tool knows all the mappings and handles the conversion automatically, including tricky cases like guards (`only_if`, `not_if`) becoming Ansible's `when` conditions.

**What you get**:
- Valid Ansible YAML task ready to use
- Correct module selection (e.g., `apt` vs `yum` based on context)
- Properties translated to Ansible syntax
- Guards converted to `when` conditions
- Comments explaining the conversion

**Real-world example**: Chef's `package 'nginx' do action :install end` becomes Ansible's `- name: Install nginx\n  apt:\n    name: nginx\n    state: present`. All syntax differences handled automatically.

**Parameters:**
- `resource_type` (string, required): The Chef resource type (e.g., 'package', 'service')
- `resource_name` (string, required): The name of the resource
- `action` (string, optional, default: "create"): The Chef action (e.g., 'install', 'start')
- `properties` (string, optional): Additional resource properties as a string representation

**Returns:**
- YAML representation of the equivalent Ansible task

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert a Chef package resource named 'nginx' with action 'install'
    to an Ansible task
    ```

=== "CLI"
    ```bash
    souschef-cli convert package nginx --action install
    ```

---

## InSpec Integration

### convert_inspec_to_test

Convert InSpec controls to Ansible test format.

**What it does**: Converts Chef InSpec test suites (compliance and testing code) into Ansible-compatible testing formats like Testinfra (Python-based), Ansible's built-in `assert` module, ServerSpec (Ruby-based), or Goss (YAML-based). InSpec is Chef's testing framework - think of it like unit tests for infrastructure.

**Why you need this**: If your Chef cookbooks have InSpec tests (they should!), you want to preserve that testing in Ansible. These tests verify your infrastructure is configured correctly. This tool automatically converts InSpec's Ruby-based syntax to multiple testing formats, saving hours of manual test rewriting.

**What you get**:
- InSpec controls converted to Testinfra, Ansible assert, ServerSpec, or Goss format
- All test cases preserved with equivalent checks
- Directory structure for test organisation
- Ready-to-run test files

**Real-world example**: Your InSpec test `describe service('nginx') do it { should be_running } end` becomes:
- Testinfra: `def test_nginx_running(host): assert host.service("nginx").is_running`
- Ansible: `assert: that: "'nginx' in services"`
- ServerSpec: `describe service('nginx') do it { should be_running } end`
- Goss: `service: nginx: running: true`

**Parameters:**
- `inspec_path` (string, required): Path to InSpec profile or control file
- `output_format` (string, optional, default: "testinfra"): Output format ('testinfra', 'ansible_assert', 'serverspec', or 'goss')

**Returns:**
- Converted test code in specified format, or error message

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert the InSpec profile at examples/database/inspec
    to Ansible testinfra format
    ```

=== "CLI"
    ```bash
    souschef-cli inspec-convert examples/database/inspec --format testinfra
    ```

---

### generate_inspec_from_recipe

Generate InSpec controls from a Chef recipe to validate conversions.

**What it does**: Analyses a Chef recipe and automatically generates InSpec test cases that verify what the recipe does. If your recipe installs nginx and starts it, this tool creates tests that check nginx is installed and running. This is test generation, not conversion.

**Why you need this**: Many Chef cookbooks lack proper tests. This tool creates tests from your recipes automatically, which you can then run before and after migration to verify your Ansible conversion works identically to the original Chef code. It's your safety net.

**What you get**:
- Complete InSpec test suite generated from recipe resources
- Tests for packages installed, services running, files created, etc.
- Validation that your Ansible conversion has the same effect as Chef
- Confidence that nothing was missed in migration

**Real-world example**: Your recipe installs `postgresql` and creates `/etc/postgresql/postgresql.conf`. This tool generates InSpec tests checking package installation and file existence. Run these tests before migration (Chef) and after (Ansible) to verify identical results.

**Parameters:**
- `recipe_path` (string, required): Path to the Chef recipe file

**Returns:**
- Generated InSpec control code, or error message

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate InSpec controls from examples/database/recipes/default.rb
    to validate the Ansible conversion
    ```

=== "CLI"
    ```bash
    souschef-cli inspec-generate examples/database/recipes/default.rb
    ```

---

## Data Bags

### convert_chef_databag_to_vars

Convert Chef data bags to Ansible variables or vault.

**What it does**: Converts Chef data bags (JSON files storing configuration data) into Ansible variables or Ansible Vault encrypted files. Data bags are Chef's way of storing data separately from cookbooks - things like database passwords, API keys, user lists, etc.

**Why you need this**: Chef data bags and Ansible variables serve the same purpose but use different formats and locations. Chef uses JSON in `data_bags/`, Ansible uses YAML in `group_vars/`, `host_vars/`, or `vault/`. This tool handles the conversion and knows when to use encrypted vaults for sensitive data.

**What you get**:
- Chef data bag JSON converted to Ansible YAML variables
- Automatic detection of sensitive data (passwords, keys) with vault encryption
- Proper variable naming (Chef's `data_bag_item` becomes Ansible's `group_vars`)
- Correct file structure for Ansible inventory

**Real-world example**: Your Chef data bag `data_bags/secrets/database.json` with `{"id": "database", "password": "secret123"}` becomes Ansible vault `group_vars/all/vault.yml` with `vault_database_password: secret123` properly encrypted.

**Parameters:**
- `databag_content` (string, required): The JSON content of the data bag
- `databag_name` (string, required): Name of the data bag
- `item_name` (string, optional, default: "default"): Name of the data bag item
- `is_encrypted` (boolean, optional, default: false): Whether the data bag is encrypted
- `target_scope` (string, optional, default: "group_vars"): Target scope ('group_vars', 'host_vars', or 'vault')

**Returns:**
- Converted Ansible variables in YAML format

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert this Chef data bag to Ansible vars:
    {"id": "db_config", "host": "localhost", "port": 5432}
    Name it "database" and target group_vars scope
    ```

---

### analyze_chef_databag_usage

Analyze data bag usage in cookbooks and provide migration recommendations.
**What it does**: Scans your Chef cookbook to find everywhere data bags are referenced (like `data_bag_item('users', 'admin')`), analyses how they're used, and recommends the best Ansible approach for each use case.

**Why you need this**: Data bags are often scattered throughout recipes, templates, and attributes. Finding all references manually is tedious and error-prone. This tool finds them all and, crucially, recommends whether each should become group_vars, host_vars, or encrypted vault based on usage patterns.

**What you get**:
- Complete list of all data bag references in the cookbook
- What data each reference accesses
- Migration recommendation for each (group_vars, host_vars, or vault)
- Impact analysis (how many recipes/files need updating)

**Real-world example**: Analysis reveals your cookbook accesses `data_bag('users')` in 5 recipes and `data_bag_item('secrets', 'api_key')` in 2 templates. Tool recommends: users → group_vars (shared across servers), api_key → vault (sensitive credential).
**Parameters:**
- `cookbook_path` (string, required): Path to the cookbook directory
- `databags_path` (string, optional): Path to the data bags directory

**Returns:**
- Analysis report with usage patterns and migration recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Analyze data bag usage in examples/database cookbook
    and suggest how to migrate them to Ansible
    ```

---

## Environments

### convert_chef_environment_to_inventory_group

Convert a Chef environment to an Ansible inventory group.

**What it does**: Converts a Chef environment file (like `environments/production.rb`) into an Ansible inventory group with equivalent settings. Chef environments separate configurations for dev/staging/production; Ansible uses inventory groups for the same purpose.

**Why you need this**: Chef environments define environment-specific settings like cookbook versions, attribute overrides, and node constraints. Ansible achieves this through inventory groups and group_vars. This tool translates between the two systems, preserving your environment isolation.

**What you get**:
- Ansible inventory group for the environment (e.g., `[production]`)
- Group variables matching Chef environment attributes
- Cookbook version constraints translated to role/collection versions
- Ready-to-use inventory structure

**Real-world example**: Your Chef `environments/production.rb` defining `override_attributes['app']['port'] = 8080` and `cookbook_versions['nginx'] = '= 2.0.0'` becomes Ansible inventory group `[production]` with `group_vars/production.yml` containing `app_port: 8080` and role version pinning.

**Parameters:**
- `environment_content` (string, required): The content of the Chef environment file
- `environment_name` (string, required): Name of the environment
- `include_constraints` (boolean, optional, default: true): Include cookbook version constraints

**Returns:**
- Ansible inventory group configuration in YAML format

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Convert the production Chef environment to an Ansible inventory group
    ```

---

### generate_inventory_from_chef_environments

Generate complete Ansible inventory from Chef environments directory.

**What it does**: Scans an entire directory of Chef environment files and generates a complete Ansible inventory structure with all environments as groups, including all variables and settings. Does for all environments what `convert_chef_environment_to_inventory_group` does for one.

**Why you need this**: Instead of converting environments one-by-one, this tool processes your entire `environments/` directory at once, creating a complete, production-ready Ansible inventory. Saves significant time when you have multiple environments (dev, test, staging, production, DR, etc.).

**What you get**:
- Complete Ansible inventory in YAML or INI format
- All Chef environments as inventory groups
- All group_vars files for each environment
- Proper inventory structure following Ansible best practices
- Ready to use with ansible-playbook

**Real-world example**: Your Chef `environments/` with `dev.rb`, `staging.rb`, and `production.rb` becomes Ansible `inventory/` with hosts file defining `[dev]`, `[staging]`, `[production]` groups, plus `group_vars/dev.yml`, `group_vars/staging.yml`, `group_vars/production.yml` with respective settings.

**Parameters:**
- `environments_directory` (string, required): Path to the environments directory
- `output_format` (string, optional, default: "yaml"): Output format ('yaml' or 'ini')

**Returns:**
- Complete Ansible inventory configuration

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate an Ansible inventory from all Chef environments
    in the environments/ directory, output as YAML
    ```

---

### analyze_chef_environment_usage

Analyze environment usage in cookbooks and suggest migration strategy.
**What it does**: Examines how your Chef cookbook uses environments (like `node.chef_environment` or `node.environment`), identifies patterns, and recommends the best Ansible inventory strategy for your use case.

**Why you need this**: Different cookbooks use Chef environments in different ways - some for simple dev/prod split, others for complex multi-tenant setups. This tool understands these patterns and recommends whether you need simple inventory groups, multiple inventory files, or dynamic inventory scripts.

**What you get**:
- All environment references in cookbook code
- Usage patterns identified (simple vs complex)
- Recommended Ansible inventory architecture
- Migration complexity assessment
- Step-by-step migration strategy

**Real-world example**: Analysis shows your cookbook checks `node.chef_environment == 'production'` in 3 recipes to conditionally configure replication. Tool recommends: use inventory groups with `when: inventory_hostname in groups['production']` in your Ansible playbooks.
**Parameters:**
- `cookbook_path` (string, required): Path to the cookbook directory
- `environments_path` (string, optional): Path to the environments directory

**Returns:**
- Analysis report with usage patterns and migration recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Analyze how the examples/database cookbook uses Chef environments
    and suggest an Ansible migration approach
    ```

---

## Migration Assessment

### assess_chef_migration_complexity

Assess the complexity of migrating Chef cookbooks to Ansible.

**What it does**: Analyses one or more Chef cookbooks and calculates a complexity score based on factors like number of resources, custom resources, Ruby code complexity, guard conditions, community cookbook dependencies, and template usage. Think of it as a "how hard will this migration be?" calculator.

**Why you need this**: Before starting a migration, you need realistic effort estimates for planning, budgeting, and resource allocation. This tool prevents surprises by identifying complexity factors upfront. A cookbook with 10 simple resources is very different from one with 50 resources, 5 custom LWRPs, and heavy Ruby logic.

**What you get**:
- Overall complexity score (Low/Medium/High/Very High)
- Breakdown by complexity factor (resources, custom code, dependencies, etc.)
- Estimated effort in person-hours or days
- Risk factors (things likely to cause problems)
- Recommended migration approach based on complexity

**Real-world example**: Assessing your `database` cookbook returns "Medium complexity (32 hours estimated)" because it has 25 resources, 2 custom resources, and depends on 3 community cookbooks. This helps you plan sprint capacity and team allocation.

**Parameters:**
- `cookbook_paths` (string, required): Comma-separated paths to cookbook directories
- `migration_scope` (string, optional, default: "full"): Scope of migration ('full', 'partial', or 'analysis_only')
- `target_platform` (string, optional, default: "ansible_awx"): Target platform ('ansible_awx', 'ansible_tower', or 'ansible_core')

**Returns:**
- Comprehensive complexity assessment with scores and recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Assess the migration complexity for the examples/database cookbook
    targeting Ansible AWX
    ```

---

### generate_migration_plan

Generate a detailed migration plan for Chef to Ansible conversion.

**What it does**: Creates a comprehensive, phased migration plan with specific tasks, timeline, dependencies, and milestones. Goes beyond just complexity assessment to give you an actionable project plan.

**Why you need this**: Migrating Chef to Ansible isn't just technical conversion - it's a project requiring planning, sequencing, testing, and validation. This tool generates a realistic plan considering your chosen strategy (phased rollout vs big bang), timeline constraints, and dependencies between cookbooks.

**What you get**:
- Phase-by-phase migration plan (e.g., Phase 1: Assessment, Phase 2: Core cookbooks, Phase 3: Applications)
- Specific tasks for each phase with effort estimates
- Dependency-aware sequencing (migrate base cookbooks before dependent ones)
- Testing and validation checkpoints
- Rollback contingency plans
- Timeline with milestones

**Real-world example**: For a 12-week timeline and phased strategy, the plan might say: Weeks 1-2 (Assessment + tooling setup), Weeks 3-6 (Convert base cookbooks: apt, users, security), Weeks 7-10 (Convert application cookbooks: database, web-server), Weeks 11-12 (Testing + deployment).

**Parameters:**
- `cookbook_paths` (string, required): Comma-separated paths to cookbook directories
- `migration_strategy` (string, optional, default: "phased"): Migration strategy ('phased', 'big_bang', or 'parallel_run')
- `timeline_weeks` (integer, optional, default: 12): Timeline for migration in weeks

**Returns:**
- Detailed migration plan with phases, tasks, and timeline

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate a phased migration plan for examples/database
    with a 12-week timeline
    ```

---

### analyze_cookbook_dependencies

Analyze dependencies between cookbooks to determine migration order.
**What it does**: Maps out the dependency graph of your Chef cookbooks (which cookbooks depend on which others) and recommends the optimal order to migrate them. Uses the `depends` declarations in metadata.rb plus analysis of actual cookbook usage patterns.

**Why you need this**: You can't migrate cookbooks in random order - if cookbook A depends on cookbook B, you must migrate B first. With dozens of cookbooks and complex dependency chains, figuring this out manually is time-consuming and error-prone. This tool does the analysis automatically and handles circular dependencies.

**What you get**:
- Complete dependency graph showing all cookbook relationships
- Recommended migration order (which to do first, second, third, etc.)
- Circular dependency detection and resolution strategies
- Groupings of cookbooks that can be migrated in parallel
- Critical path analysis (dependencies that would block everything else)

**Real-world example**: Analysis reveals: `base` cookbook has no dependencies (migrate first), `database` depends on `base` (migrate second), `application` depends on both `base` and `database` (migrate last). Attempting to migrate `application` first would fail.
**Parameters:**
- `cookbook_paths` (string, required): Comma-separated paths to cookbook directories

**Returns:**
- Dependency analysis with recommended migration order

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Analyze dependencies between all cookbooks in the examples/ directory
    and suggest the order for migration
    ```

---

### generate_migration_report

Generate a comprehensive migration report.

**What it does**: Creates a complete migration report combining complexity assessment, dependency analysis, conversion details, testing coverage, and recommendations. Outputs as Markdown (for engineers), HTML (for sharing), or JSON (for automation/integrations).

**Why you need this**: Stakeholders, managers, and auditors need documentation of the migration. This tool generates executive summaries, technical details, risk assessments, and recommendations in presentation-ready formats. It's your "migration in a document" for getting buy-in and tracking progress.

**What you get**:
- Executive summary with effort estimates and risks
- Detailed technical analysis of each cookbook
- Conversion coverage (what's automated vs manual)
- Testing strategy and coverage percentages
- Recommended approach and timeline
- Resource requirements (team size, skills needed)
- Success criteria and validation checkpoints

**Real-world example**: Generated HTML report shows: 15 cookbooks analyzed, total estimated effort 420 hours over 14 weeks, 3 high-risk items identified (custom Chef providers requiring manual porting), recommended phased approach starting with base infrastructure. This document becomes your migration proposal.

**Parameters:**
- `cookbook_paths` (string, required): Comma-separated paths to cookbook directories
- `report_format` (string, optional, default: "markdown"): Report format ('markdown', 'html', or 'json')
- `include_technical_details` (string, optional, default: "yes"): Include technical details ('yes' or 'no')

**Returns:**
- Comprehensive migration report in specified format

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Generate a comprehensive migration report for examples/database
    in markdown format with full technical details
    ```

---

### validate_conversion

Validate converted Ansible code against original Chef code.

**What it does**: Compares your converted Ansible playbook/role with the original Chef recipe to verify they're functionally equivalent. Checks that all resources were converted, properties are correct, guard conditions are preserved, and nothing was missed or misinterpreted.

**Why you need this**: Automated conversion is fast but needs validation. This tool catches mistakes like: forgetting to convert a guard condition, using wrong Ansible module parameters, missing template variables, or incorrect action mappings. It's your quality assurance for conversion accuracy.

**What you get**:
- Line-by-line comparison of Chef vs Ansible
- List of any missing or incorrectly converted resources
- Property/parameter mapping verification
- Guard condition translation checks
- Overall conversion accuracy percentage
- Specific suggestions for fixing issues found

**Real-world example**: Validation reveals: 18 of 20 Chef resources correctly converted, but 2 issues: (1) Chef's `not_if` guard on package resource missing equivalent Ansible `when` condition, (2) Template variable `node['app']['port']` not mapped to `{{ app_port }}`. You can now fix these specific issues.

**Parameters:****
- `conversion_type` (string, required): Type of conversion ('recipe_to_playbook', 'databag_to_vars', etc.)
- `result_content` (string, required): The converted Ansible content
- `output_format` (string, optional, default: "text"): Output format ('text', 'json', or 'yaml')

**Returns:**
- Validation report with any issues or suggestions

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Validate this converted Ansible playbook against the original
    Chef recipe to ensure accuracy
    ```

---

## Habitat

### parse_habitat_plan

Parse Habitat plan files for container conversion.

**What it does**: Reads and parses Chef Habitat `plan.sh` files (Bash scripts that define how to build Habitat packages) and extracts all the configuration, dependencies, build steps, and runtime settings. Habitat is Chef's application automation solution that packages apps with their dependencies.

**Why you need this**: Chef Habitat is being deprecated, and many organisations are migrating Habitat applications to containers (Docker/Kubernetes). This tool extracts all information from Habitat plans so you can convert them to Dockerfiles, docker-compose files, or Kubernetes manifests without manually reverse-engineering the plan.sh scripts.

**What you get**:
- Package name, version, and maintainer info
- All dependencies (pkg_deps) and build dependencies (pkg_build_deps)
- Build steps and configuration
- Exposed ports and volume mounts
- Runtime configuration and hooks
- Service dependencies and bindings
- Everything needed to write an equivalent Dockerfile

**Real-world example**: Your `habitat/plan.sh` for a web application shows it depends on `core/node`, exposes port 3000, runs build command `npm install`, and has startup hook `node server.js`. This tool extracts all details you need to create a `FROM node:lts` Dockerfile with correct CMD and EXPOSE directives.

**Parameters:**
- `plan_path` (string, required): Path to the Habitat plan.sh file

**Returns:**
- Parsed Habitat plan information in JSON format

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Parse the Habitat plan at examples/web-server/habitat/plan.sh
    ```

---

## Performance

### profile_cookbook_performance

Profile cookbook parsing performance and generate optimization report.
**What it does**: Measures how long it takes to parse all components of a Chef cookbook (recipes, templates, resources, attributes) and identifies bottlenecks. Provides detailed timing data and recommendations for optimising slow operations.

**Why you need this**: For large cookbooks (hundreds of files), parsing can be slow. When you're migrating dozens of cookbooks, every second counts. This tool identifies which parsing operations are slowest (usually large recipe files or complex ERB templates) and suggests optimisations like parallelisation, caching, or breaking up large files.

**What you get**:
- Total parsing time for the entire cookbook
- Per-file timing data (which recipes/templates are slowest)
- Bottleneck identification (what's taking the most time)
- Memory usage statistics
- Optimisation recommendations (e.g., "Consider splitting recipes/default.rb - 2,500 lines taking 3.2 seconds")
- Comparison against cookbook size benchmarks

**Real-world example**: Profiling your 50-recipe cookbook shows total parse time of 12 seconds, with `recipes/deploy.rb` alone taking 4 seconds due to 1,000 resources. Tool recommends splitting this recipe into logical sub-recipes (deploy_setup.rb, deploy_app.rb, deploy_finalize.rb) to improve parsing and conversion performance.
**Parameters:**
- `cookbook_path` (string, required): Path to the cookbook directory

**Returns:**
- Performance report with timing, bottlenecks, and optimization recommendations

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Profile the parsing performance of examples/database cookbook
    and suggest optimizations
    ```

=== "CLI"
    ```bash
    souschef-cli profile examples/database
    ```

---

### profile_parsing_operation

Profile a single parsing operation in detail.

**What it does**: Provides deep performance analysis of parsing a single file with microsecond-level timing, memory allocation tracking, and detailed execution traces. Like a performance profiler specifically for SousChef parsing operations.

**Why you need this**: When a specific file is causing performance problems, this tool shows exactly where the time is spent - Ruby parsing, AST traversal, property extraction, or conversion logic. Essential for troubleshooting performance issues or contributing performance improvements to SousChef.

**What you get**:
- Microsecond-precision timing for the operation
- Breakdown of time spent in each parsing phase
- Memory allocation and peak usage
- Function call counts and hotspots
- Detailed execution trace (if detailed=true)
- Comparative metrics (how this file compares to typical files of same type)
- Specific performance recommendations

**Real-world example**: Profiling parsing of `recipes/complex.rb` shows: Total time 850ms, with 600ms spent in Ruby AST parsing (slow), 200ms in resource extraction (normal), 50ms in output formatting (fast). Recommendation: This recipe has unusually complex Ruby metaprogramming slowing AST parsing - consider simplifying or expect manual conversion of metaprogrammed sections.

**Parameters:****
- `operation` (string, required): Operation to profile ('recipe', 'template', 'resource', 'attributes')
- `file_path` (string, required): Path to the file to parse
- `detailed` (boolean, optional, default: false): Include detailed profiling information

**Returns:**
- Detailed performance metrics for the specified operation

**Example Usage:**

=== "MCP (AI Assistant)"
    ```
    Profile parsing the recipe at examples/database/recipes/default.rb
    with detailed metrics
    ```

=== "CLI"
    ```bash
    souschef-cli profile-operation recipe examples/database/recipes/default.rb --detailed
    ```

---

## Best Practices

### Tool Selection

- **Start with analysis**: Use `parse_*` and `analyze_*` tools to understand your Chef infrastructure before converting
- **Validate conversions**: Always use `validate_conversion` after converting resources or recipes
- **Profile large cookbooks**: Use `profile_cookbook_performance` for cookbooks with many recipes

### Error Handling

All tools provide detailed error messages with suggestions:
- File not found errors include path verification tips
- Parse errors show line numbers and context
- Validation errors explain what needs fixing

### Workflow Recommendations

1. **Discovery**: Use `list_cookbook_structure` and `read_cookbook_metadata`
2. **Analysis**: Use `assess_chef_migration_complexity` and `analyze_cookbook_dependencies`
3. **Planning**: Use `generate_migration_plan`
4. **Conversion**: Use `convert_*` tools for individual resources
5. **Validation**: Use `generate_inspec_from_recipe` and `validate_conversion`
6. **Assessment**: Use `generate_migration_report`

---

## See Also

- **[CLI Usage Guide](cli-usage.md)** - Command-line interface for all tools
- **[Examples](examples.md)** - Real-world usage examples
- **[Migration Guide](../migration-guide/overview.md)** - Step-by-step migration process
- **[Configuration](../getting-started/configuration.md)** - Configure SousChef for your environment
