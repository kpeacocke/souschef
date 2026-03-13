# CLI Usage Guide

SousChef provides a powerful command-line interface for direct cookbook parsing, conversion, and analysis without requiring an MCP client or AI assistant.

!!! tip "When to Use CLI vs MCP"
    - **CLI**: Direct parsing, automation scripts, CI/CD pipelines, quick analysis
    - **MCP**: Complex migrations, AI-assisted conversions, interactive planning, advanced workflows

## Installation

The CLI is automatically installed with SousChef:

```bash
# PyPI installation
pip install mcp-souschef

# Verify installation
souschef-cli --help
```

## Quick Reference

| Command | Purpose | Example |
|---------|---------|---------|
| [`recipe`](#recipe) | Parse Chef recipe files | `souschef-cli recipe default.rb` |
| [`template`](#template) | Convert ERB to Jinja2 | `souschef-cli template nginx.conf.erb` |
| [`resource`](#resource) | Parse custom resources | `souschef-cli resource user.rb` |
| [`attributes`](#attributes) | Parse attribute files | `souschef-cli attributes default.rb` |
| [`metadata`](#metadata) | Parse cookbook metadata | `souschef-cli metadata metadata.rb` |
| [`structure`](#structure) | Display cookbook tree | `souschef-cli structure /path/to/cookbook` |
| [`convert`](#convert) | Convert resources to tasks | `souschef-cli convert package nginx` |
| [`cookbook`](#cookbook) | Analyze entire cookbook | `souschef-cli cookbook /path/to/cookbook` |
| [`inspec-parse`](#inspec-parse) | Parse InSpec profiles | `souschef-cli inspec-parse profile/` |
| [`inspec-convert`](#inspec-convert) | Convert InSpec to tests | `souschef-cli inspec-convert profile/` |
| [`inspec-generate`](#inspec-generate) | Generate InSpec from recipe | `souschef-cli inspec-generate recipe.rb` |
| [`profile`](#profile) | Profile cookbook performance | `souschef-cli profile /path/to/cookbook` |
| [`profile-operation`](#profile-operation) | Profile specific operation | `souschef-cli profile-operation recipe default.rb` |
| [`ls`](#ls) | List directory contents | `souschef-cli ls recipes/` |
| [`cat`](#cat) | Display file contents | `souschef-cli cat default.rb` |
| [`v2 migrate`](#v2-migrate) | Run v2 migration orchestration | `souschef-cli v2 migrate --cookbook-path cookbooks/app` |
| [`v2 status`](#v2-status) | Load v2 migration state | `souschef-cli v2 status --migration-id mig-abc123` |
| [`puppet parse`](#puppet-parse) | Parse Puppet manifest | `souschef puppet parse manifests/site.pp` |
| [`puppet parse-module`](#puppet-parse-module) | Parse Puppet module directory | `souschef puppet parse-module modules/nginx` |
| [`puppet convert`](#puppet-convert) | Convert Puppet manifest to playbook | `souschef puppet convert manifests/site.pp -o playbook.yml` |
| [`puppet convert-module`](#puppet-convert-module) | Convert Puppet module to playbook | `souschef puppet convert-module modules/nginx -o role.yml` |
| [`puppet list-types`](#puppet-list-types) | List supported Puppet resource types | `souschef puppet list-types` |

---

## Core Commands

### recipe

Parse Chef recipe files and extract resources, guards, and dependencies.

**Syntax:**
```bash
souschef-cli recipe PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to the Chef recipe (.rb) file
- `--format`: Output format - `text` (default) or `json`

**Examples:**

=== "Basic Usage"
    ```bash
    souschef-cli recipe examples/database/recipes/default.rb
    ```

=== "JSON Output"
    ```bash
    souschef-cli recipe examples/database/recipes/default.rb --format json
    ```

=== "Save to File"
    ```bash
    souschef-cli recipe default.rb --format json > recipe_analysis.json
    ```

**Output Format:**

```
Recipe: default.rb
==================

Resource 1:
  Type: package
  Name: postgresql
  Action: install
  Properties:
    - version: 12.3

Resource 2:
  Type: service
  Name: postgresql
  Action: enable, start
  Notifies: restart postgresql (delayed)
```

**Use Cases:**
- Understanding recipe structure before conversion
- Extracting resource lists for documentation
- Identifying dependencies and notification chains
- Automation scripts for bulk analysis

---

### template

Parse ERB templates and convert to Jinja2 with variable extraction.

**Syntax:**
```bash
souschef-cli template PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to the ERB template file
- `--format`: Output format - `json` (default) or `text`

**Examples:**

=== "Convert Template"
    ```bash
    souschef-cli template templates/default/nginx.conf.erb
    ```

=== "Extract Variables"
    ```bash
    souschef-cli template nginx.conf.erb --format json | jq '.variables'
    ```

**Output Format (JSON):**

```json
{
  "original_template": "<%= @port %>",
  "jinja2_template": "{{ port }}",
  "variables": ["port", "server_name", "root_path"],
  "conversion_notes": [
    "Converted <%= var %> to {{ var }}",
    "Converted <% if condition %> to {% if condition %}"
  ]
}
```

**ERB to Jinja2 Conversion Examples:**

| ERB Syntax | Jinja2 Syntax |
|------------|---------------|
| `<%= @variable %>` | `{{ variable }}` |
| `<% if @enabled %>` | `{% if enabled %}` |
| `<% @items.each do \|item\| %>` | `{% for item in items %}` |
| `<%# comment %>` | `{# comment #}` |

---

### resource

Parse custom Chef resources and LWRPs to extract properties and actions.

**Syntax:**
```bash
souschef-cli resource PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to custom resource (.rb) file
- `--format`: Output format - `json` (default) or `text`

**Examples:**

```bash
# Parse custom resource
souschef-cli resource resources/database_user.rb

# Get properties list
souschef-cli resource resources/app_config.rb --format json | jq '.properties'
```

**Output Format (JSON):**

```json
{
  "resource_type": "database_user",
  "properties": [
    {
      "name": "username",
      "type": "String",
      "required": true,
      "default": null
    },
    {
      "name": "password",
      "type": "String",
      "required": false,
      "default": "changeme"
    }
  ],
  "actions": ["create", "delete"],
  "default_action": "create"
}
```

---

### v2 migrate

Run the v2 migration orchestrator for a cookbook.

**Syntax:**
```bash
souschef-cli v2 migrate \
  --cookbook-path PATH \
  --chef-version VERSION \
  --target-platform PLATFORM \
  --target-version VERSION
```

**Options:**
- `--cookbook-path` (required): Path to the Chef cookbook directory
- `--chef-version` (required): Chef Infra Client version (e.g., 15.10.91)
- `--target-platform` (required): Target platform (`tower`, `awx`, `aap`)
- `--target-version` (required): Target platform version (e.g., 2.4.0)
- `--skip-validation`: Skip playbook validation
- `--save-state`: Persist migration state to storage
- `--analysis-id`: Link to an existing analysis ID
- `--output-type`: History output type (`playbook`, `role`, `collection`)
- `--format`: Output format (`json` default, `text`)
- `--output`: Save result to file instead of stdout

**Examples:**

=== "Basic Migration"
    ```bash
    souschef-cli v2 migrate \
      --cookbook-path cookbooks/nginx \
      --chef-version 15.10.91 \
      --target-platform aap \
      --target-version 2.4.0
    ```

=== "Save State"
    ```bash
    souschef-cli v2 migrate \
      --cookbook-path cookbooks/nginx \
      --chef-version 15.10.91 \
      --target-platform aap \
      --target-version 2.4.0 \
      --save-state
    ```

---

### v2 status

Load a saved v2 migration state by ID.

**Syntax:**
```bash
souschef-cli v2 status --migration-id MIGRATION_ID
```

**Options:**
- `--migration-id` (required): Migration ID to load from storage
- `--limit`: Maximum number of history entries to scan (default: 500)
- `--format`: Output format (`json` default, `text`)
- `--output`: Save result to file instead of stdout

**Example:**
```bash
souschef-cli v2 status --migration-id mig-abc123
```

---

### attributes

Parse Chef attribute files with precedence level detection.

**Syntax:**
```bash
souschef-cli attributes PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to attributes (.rb) file
- `--format`: Output format - `text` (default) or `json`

**Examples:**

```bash
# Parse attributes
souschef-cli attributes attributes/default.rb

# Show only override-level attributes
souschef-cli attributes default.rb --format json | jq '.override'
```

**Output Format:**

```
Attributes: default.rb
=====================

Default Level:
  app.port = 8080
  app.workers = 4

Override Level:
  app.environment = "production"

Normal Level:
  app.enabled = true
```

**Precedence Levels Detected:**
- `default` - Standard defaults
- `force_default` - Override default precedence
- `normal` - Node-specific values
- `override` - Override normal values
- `force_override` - Highest priority
- `automatic` - System-discovered values

---

### metadata

Parse cookbook metadata.rb files for dependencies and version information.

**Syntax:**
```bash
souschef-cli metadata PATH
```

**Options:**
- `PATH` (required): Path to metadata.rb file

**Example:**

```bash
souschef-cli metadata examples/database/metadata.rb
```

**Output Format:**

```
Cookbook: database
Version: 2.1.0
Maintainer: DevOps Team <devops@example.com>
License: Apache-2.0

Dependencies:
  - postgresql (>= 1.0.0)
  - apt (~> 7.0)

Supports:
  - ubuntu (>= 18.04)
  - centos (>= 7.0)
```

---

### structure

Display complete cookbook directory hierarchy.

**Syntax:**
```bash
souschef-cli structure PATH
```

**Options:**
- `PATH` (required): Path to cookbook root directory

**Example:**

```bash
souschef-cli structure examples/database
```

**Output Format:**

```
database/
├── metadata.rb
├── README.md
├── attributes/
│   └── default.rb
├── recipes/
│   ├── default.rb
│   ├── install.rb
│   └── configure.rb
├── templates/
│   └── default/
│       ├── database.yml.erb
│       └── init.sql.erb
└── resources/
    └── user.rb

Summary:
  Recipes: 3
  Attributes: 1
  Templates: 2
  Resources: 1
```

---

### convert

Convert individual Chef resources to Ansible tasks.

**Syntax:**
```bash
souschef-cli convert RESOURCE_TYPE RESOURCE_NAME [OPTIONS]
```

**Options:**
- `RESOURCE_TYPE` (required): Chef resource type (package, service, template, etc.)
- `RESOURCE_NAME` (required): Resource name
- `--action`: Chef action (default: create)
- `--properties`: Additional properties as JSON string
- `--format`: Output format - `yaml` (default) or `json`

**Examples:**

=== "Package Resource"
    ```bash
    souschef-cli convert package nginx --action install
    ```

    Output:
    ```yaml
    - name: Install nginx
      ansible.builtin.package:
        name: nginx
        state: present
    ```

=== "Service Resource"
    ```bash
    souschef-cli convert service nginx --action 'enable,start'
    ```

    Output:
    ```yaml
    - name: Enable and start nginx
      ansible.builtin.service:
        name: nginx
        enabled: true
        state: started
    ```

=== "Template Resource"
    ```bash
    souschef-cli convert template /etc/nginx/nginx.conf \
      --action create \
      --properties '{"source": "nginx.conf.erb", "owner": "root", "mode": "0644"}'
    ```

    Output:
    ```yaml
    - name: Create /etc/nginx/nginx.conf
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        mode: '0644'
    ```

=== "File Resource"
    ```bash
    souschef-cli convert file /var/log/app.log \
      --action create \
      --properties '{"owner": "app", "group": "app", "mode": "0644"}'
    ```

**Supported Resource Types:**

| Chef Resource | Ansible Module | Notes |
|---------------|----------------|-------|
| `package` | `ansible.builtin.package` | Cross-platform package management |
| `service` | `ansible.builtin.service` | Service state management |
| `template` | `ansible.builtin.template` | Template file deployment |
| `file` | `ansible.builtin.file` | File/directory management |
| `directory` | `ansible.builtin.file` | Directory creation |
| `user` | `ansible.builtin.user` | User account management |
| `group` | `ansible.builtin.group` | Group management |
| `execute` | `ansible.builtin.command` | Command execution |
| `bash` | `ansible.builtin.shell` | Shell script execution |
| `git` | `ansible.builtin.git` | Git repository management |
| `cron` | `ansible.builtin.cron` | Cron job management |
| `mount` | `ansible.posix.mount` | Filesystem mounting |

---

### cookbook

Comprehensive analysis of entire Chef cookbook.

**Syntax:**
```bash
souschef-cli cookbook COOKBOOK_PATH [OPTIONS]
```

**Options:**
- `COOKBOOK_PATH` (required): Path to cookbook root directory
- `--output`, `-o`: Output directory for results
- `--dry-run`: Show what would be analyzed without processing

**Example:**

```bash
souschef-cli cookbook examples/database
```

**Output:**

```
Analyzing cookbook: database
==================================================

[LIST] Metadata:
--------------------------------------------------
Cookbook: database
Version: 2.1.0
Dependencies: postgresql (>= 1.0.0), apt (~> 7.0)

Structure:
--------------------------------------------------
database/
├── metadata.rb
├── recipes/ (3 files)
├── attributes/ (1 file)
├── templates/ (2 files)
└── resources/ (1 file)

[USER]‍[CHEF] Recipes:
--------------------------------------------------
  default.rb:
    Resource 1: package[postgresql]
    Resource 2: service[postgresql]
    Resource 3: template[/etc/postgresql/postgresql.conf]
    ... (7 more resources)

[CONFIG] Custom Resources:
--------------------------------------------------
  user.rb:
    Type: database_user
    Properties: 3
    Actions: create, delete

[FILE] Templates:
--------------------------------------------------
  database.yml.erb:
    Variables: 4
    port, host, username, password
```

---

## InSpec Commands

### inspec-parse

Parse InSpec profiles and extract control definitions.

**Syntax:**
```bash
souschef-cli inspec-parse PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to InSpec profile directory or .rb control file
- `--format`: Output format - `json` (default) or `text`

**Example:**

```bash
souschef-cli inspec-parse tests/inspec/nginx-profile
```

**Output Format (JSON):**

```json
{
  "profile": "nginx-baseline",
  "version": "1.0.0",
  "controls": [
    {
      "id": "nginx-01",
      "title": "Verify nginx installation",
      "impact": 1.0,
      "tests": [
        "Package nginx should be installed",
        "Service nginx should be running"
      ]
    }
  ]
}
```

---

### inspec-convert

Convert InSpec controls to Testinfra or Ansible assert tasks.

**Syntax:**
```bash
souschef-cli inspec-convert PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to InSpec profile directory or .rb control file
- `--format`: Output format - `testinfra` (default), `ansible_assert`, `serverspec`, or `goss`

**Examples:**

=== "Convert to Testinfra"
    ```bash
    souschef-cli inspec-convert tests/inspec/nginx-profile --format testinfra
    ```

    Output:
    ```python
    def test_nginx_installed(host):
        nginx = host.package("nginx")
        assert nginx.is_installed

    def test_nginx_running(host):
        nginx = host.service("nginx")
        assert nginx.is_running
        assert nginx.is_enabled
    ```

=== "Convert to Ansible Assert"
    ```bash
    souschef-cli inspec-convert tests/inspec/nginx-profile --format ansible_assert
    ```

    Output:
    ```yaml
    - name: Verify nginx installation
      assert:
        that:
          - "'nginx' in ansible_facts.packages"
        fail_msg: "nginx package is not installed"

    - name: Verify nginx service
      assert:
        that:
          - nginx_service.status.ActiveState == "active"
        fail_msg: "nginx service is not running"
    ```

=== "Convert to ServerSpec"
    ```bash
    souschef-cli inspec-convert tests/inspec/nginx-profile --format serverspec
    ```

    Output:
    ```ruby
    # frozen_string_literal: true
    require 'serverspec'

    describe package('nginx') do
      it { should be_installed }
    end

    describe service('nginx') do
      it { should be_running }
      it { should be_enabled }
    end
    ```

=== "Convert to Goss"
    ```bash
    souschef-cli inspec-convert tests/inspec/nginx-profile --format goss
    ```

    Output:
    ```yaml
    package:
      nginx:
        installed: true
    service:
      nginx:
        enabled: true
        running: true
    ```

---

### inspec-generate

Generate InSpec controls from Chef recipes.

**Syntax:**
```bash
souschef-cli inspec-generate PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to Chef recipe (.rb) file
- `--format`: Output format - `text` (default) or `json`

**Example:**

```bash
souschef-cli inspec-generate recipes/default.rb > controls/generated.rb
```

**Output Format:**

```ruby
control 'package-nginx' do
  impact 1.0
  title 'Verify nginx package installation'
  desc 'Generated from recipe: default.rb'

  describe package('nginx') do
    it { should be_installed }
  end
end

control 'service-nginx' do
  impact 1.0
  title 'Verify nginx service state'
  desc 'Generated from recipe: default.rb'

  describe service('nginx') do
    it { should be_enabled }
    it { should be_running }
  end
end
```

---

## Performance Commands

### profile

Profile entire cookbook parsing performance.

**Syntax:**
```bash
souschef-cli profile COOKBOOK_PATH [OPTIONS]
```

**Options:**
- `COOKBOOK_PATH` (required): Path to cookbook root directory
- `--output`, `-o`: Save report to file instead of stdout

**Example:**

```bash
souschef-cli profile examples/database --output perf_report.txt
```

**Output Format:**

```
Cookbook Performance Report
===========================
Cookbook: database
Date: 2026-01-09 12:00:00

Operation Summary:
--------------------------------------------------
Recipes:        0.234s  (3 files)   78ms avg
Attributes:     0.045s  (1 file)    45ms avg
Templates:      0.089s  (2 files)   44ms avg
Resources:      0.012s  (1 file)    12ms avg
--------------------------------------------------
Total Time:     0.380s
Peak Memory:    45.2 MB

Performance Recommendations:
• Recipe parsing is optimal (< 100ms per file)
• No performance issues detected
• Total parse time within acceptable range

Detailed Breakdown:
--------------------------------------------------
recipes/default.rb       89ms   12.3 MB
recipes/install.rb       78ms   10.1 MB
recipes/configure.rb     67ms   11.8 MB
attributes/default.rb    45ms   4.2 MB
templates/database.yml   44ms   2.1 MB
templates/init.sql       45ms   2.3 MB
resources/user.rb        12ms   3.1 MB
```

---

### profile-operation

Profile a specific parsing operation with detailed statistics.

**Syntax:**
```bash
souschef-cli profile-operation OPERATION PATH [OPTIONS]
```

**Options:**
- `OPERATION` (required): Operation type - `recipe`, `attributes`, `resource`, or `template`
- `PATH` (required): Path to file to parse
- `--detailed`: Show detailed function call statistics (cProfile data)

**Examples:**

=== "Basic Profiling"
    ```bash
    souschef-cli profile-operation recipe recipes/default.rb
    ```

    Output:
    ```
    Operation: recipe
    File: recipes/default.rb

    Execution Time: 89.4ms
    Peak Memory: 12.3 MB

    Status: [OK] Performance is good
    ```

=== "Detailed Profiling"
    ```bash
    souschef-cli profile-operation recipe recipes/default.rb --detailed
    ```

    Output:
    ```
    Operation: recipe
    File: recipes/default.rb

    Execution Time: 89.4ms
    Peak Memory: 12.3 MB

    Top Functions by Time:
    ──────────────────────────────────────────────
    45.2ms  parse_resource_block
    12.1ms  extract_properties
    8.7ms   resolve_guards
    6.3ms   parse_ruby_ast
    ...

    Function Call Statistics:
    ──────────────────────────────────────────────
    parse_resource_block:     15 calls
    extract_properties:       45 calls
    resolve_guards:          12 calls

    Status: [OK] Performance is good
    ```

---

## Utility Commands

### ls

List directory contents with filtering.

**Syntax:**
```bash
souschef-cli ls PATH [--pattern PATTERN]
```

**Options:**
- `PATH` (required): Path to directory
- `--pattern`: Glob pattern for filtering (e.g., "*.rb")

**Examples:**

```bash
# List all files
souschef-cli ls recipes/

# List only Ruby files
souschef-cli ls recipes/ --pattern "*.rb"

# List templates
souschef-cli ls templates/default/ --pattern "*.erb"
```

---

### cat

Display file contents.

**Syntax:**
```bash
souschef-cli cat PATH
```

**Options:**
- `PATH` (required): Path to file

**Example:**

```bash
souschef-cli cat recipes/default.rb
```

---

## Bash Script Migration Commands

Convert provisioning Bash scripts — and scripts that escape from Salt, Puppet, or Chef into raw Bash — directly to idiomatic Ansible playbooks or roles ready for AAP.

### bash parse

Parse a Bash script and display detected provisioning patterns.

**Syntax:**
```bash
souschef bash parse SCRIPT_PATH [OPTIONS]
```

**Options:**
- `SCRIPT_PATH` (required): Path to the Bash script to analyse
- `--output`, `-o`: Save output to file instead of stdout

**What it detects:**

| Category | Examples |
|----------|----------|
| Packages | `apt-get install`, `yum install`, `dnf install`, `pip install` |
| Services | `systemctl start/enable`, `service restart` |
| File writes | `echo … > /path`, heredocs, `tee` |
| Downloads | `curl -o`, `wget` |
| Users | `useradd`, `usermod`, `userdel` |
| Groups | `groupadd`, `groupmod` |
| File permissions | `chmod`, `chown`, `chgrp` |
| Git operations | `git clone`, `git pull`, `git checkout` |
| Archives | `tar -x`, `unzip` |
| sed operations | `sed -i` (in-place edits) |
| Cron jobs | `crontab`, cron.d writes |
| Firewall rules | `ufw`, `firewall-cmd`, `iptables` |
| Hostname | `hostnamectl set-hostname` |
| Environment vars | `export VAR=value` |
| Sensitive data | Passwords, API keys, private key material (value redacted) |
| CM escapes | `salt-call`, `puppet apply`, `chef-client` embedded in Bash |

**Examples:**

```bash
# Analyse and print to stdout
souschef bash parse scripts/bootstrap.sh

# Save analysis to file
souschef bash parse scripts/bootstrap.sh --output analysis.txt
```

**Example output:**
```
Package Installs:
  Line 4: [apt] nginx, python3, python3-pip → ansible.builtin.apt (confidence: 90%)
Service Control:
  Line 8: systemctl enable nginx (confidence: 95%)
Users:
  Line 10: create — useradd -m -s /bin/bash appuser (confidence: 90%)
Sensitive Data:
  Line 14: [password] Use ansible-vault to encrypt this value
CM Escapes:
  Line 22: [salt] salt-call state.apply — Replace with native Ansible equivalent
Idempotency Risks:
  Line 14: [unconditional_write] File write without existence check may overwrite existing config
```

---

### bash convert

Convert a Bash script to an Ansible playbook.

**Syntax:**
```bash
souschef bash convert SCRIPT_PATH [OPTIONS]
```

**Options:**
- `SCRIPT_PATH` (required): Path to the Bash script to convert
- `--output`, `-o`: Save output to file instead of stdout
- `--format`: Output format — `yaml` (playbook only, default) or `json` (full response including quality score and AAP hints)

**Examples:**

```bash
# Convert and print playbook to stdout
souschef bash convert scripts/deploy.sh

# Save playbook YAML to file
souschef bash convert scripts/deploy.sh --output playbook.yml

# Full JSON response with quality score and AAP hints
souschef bash convert scripts/deploy.sh --format json | jq .quality_score
```

**Example playbook output:**
```yaml
# Generated by SousChef from deploy.sh
---
- name: Converted from Bash script
  hosts: all
  become: true
  tasks:

  - name: Install packages via apt
    ansible.builtin.apt:
      name:
        - nginx
        - python3
      state: present

  - name: Enable service nginx
    ansible.builtin.service:
      name: nginx
      state: started
      enabled: true

  - name: Manage user appuser
    ansible.builtin.user:
      name: appuser
      state: present
```

**Quality score (JSON format):**
```json
{
  "quality_score": {
    "grade": "B",
    "total_operations": 8,
    "structured_operations": 7,
    "shell_fallbacks": 1,
    "coverage_pct": 87,
    "idempotency_score": 77,
    "improvements": [
      "Encrypt secrets with ansible-vault",
      "Replace CM tool calls with native Ansible modules"
    ]
  }
}
```

**AAP hints (JSON format):**
```json
{
  "aap_hints": {
    "suggested_ee": "registry.redhat.io/ansible-automation-platform/ee-supported-rhel8:latest",
    "suggested_credentials": ["Machine"],
    "become_enabled": true,
    "timeout": 3600,
    "survey_variables": [
      {"name": "APP_PORT", "type": "text", "default": "8080", "required": false}
    ],
    "notes": [
      "Script contains hardcoded credentials — use ansible-vault",
      "Script contains salt calls — review for native Ansible equivalents"
    ]
  }
}
```

---

### bash role

Generate a complete Ansible role directory structure from a Bash script.

**Syntax:**
```bash
souschef bash role SCRIPT_PATH [OPTIONS]
```

**Options:**
- `SCRIPT_PATH` (required): Path to the Bash script to convert
- `--role-name`: Name for the generated role (default: `bash_converted`)
- `--output-dir`: Directory to write role files to (default: print to stdout)

**Generated role structure:**
```
<role-name>/
├── tasks/
│   ├── main.yml        # imports all category task files
│   ├── packages.yml    # package install tasks
│   ├── services.yml    # service management tasks
│   ├── users.yml       # user and group management tasks
│   ├── files.yml       # file write and permission tasks
│   └── misc.yml        # git, archives, sed, cron, firewall, hostname
├── handlers/
│   └── main.yml        # service restart handlers
├── defaults/
│   └── main.yml        # env vars as Ansible defaults; secrets stubbed with vault comment
├── vars/
│   └── main.yml        # empty placeholder
├── meta/
│   └── main.yml        # role metadata (author, description, licence)
└── README.md           # auto-generated role documentation
```

**Examples:**

```bash
# Print role files to stdout
souschef bash role scripts/setup_webserver.sh --role-name webserver

# Write role tree to disk
souschef bash role scripts/setup_webserver.sh \
    --role-name webserver \
    --output-dir ./roles

# Use the role immediately in a playbook
cat > site.yml << 'EOF'
---
- name: Deploy webserver
  hosts: webservers
  roles:
    - webserver
EOF
ansible-playbook site.yml -e @vault.yml
```

**Example `defaults/main.yml` output:**
```yaml
# defaults/main.yml — generated by SousChef
---
# DB_PASSWORD: ''  # TODO: set via ansible-vault
APP_PORT: '8080'
APP_ENV: 'production'
```

---

## Puppet Migration Commands

Convert Puppet manifests and module directories to Ansible playbooks using `ansible.builtin` modules.

### puppet parse

Parse a Puppet manifest file and display all discovered resources, classes, and variables.

**Syntax:**
```bash
souschef puppet parse MANIFEST_PATH [OPTIONS]
```

**Options:**
- `MANIFEST_PATH` (required): Path to the Puppet manifest (`.pp`) file
- `--output`, `-o`: Save output to file instead of stdout

**What it detects:**

| Category | Examples |
|----------|----------|
| Resources | `package`, `service`, `file`, `user`, `group`, `exec`, `cron`, `host`, `mount` |
| Classes | Class definitions with parameters |
| Variables | Variable assignments |
| Unsupported | Hiera lookups, exported resources, `create_resources`, `inline_template` |

**Examples:**

```bash
# Parse a manifest and print to stdout
souschef puppet parse manifests/site.pp

# Save analysis to file
souschef puppet parse manifests/webserver.pp --output analysis.txt
```

---

### puppet parse-module

Parse a Puppet module directory and analyse all manifests.

**Syntax:**
```bash
souschef puppet parse-module MODULE_PATH [OPTIONS]
```

**Options:**
- `MODULE_PATH` (required): Path to the Puppet module directory
- `--output`, `-o`: Save output to file instead of stdout

**Examples:**

```bash
souschef puppet parse-module modules/nginx
souschef puppet parse-module modules/postgresql --output analysis.txt
```

---

### puppet convert

Convert a Puppet manifest to an Ansible playbook.

**Syntax:**
```bash
souschef puppet convert MANIFEST_PATH [OPTIONS]
```

**Options:**
- `MANIFEST_PATH` (required): Path to the Puppet manifest (`.pp`) file
- `--output`, `-o`: Path to save the generated playbook YAML

**Puppet → Ansible module mapping:**

| Puppet Resource | Ansible Module |
|-----------------|----------------|
| `package` | `ansible.builtin.package` |
| `service` | `ansible.builtin.service` |
| `file` | `ansible.builtin.file` / `copy` / `template` |
| `user` | `ansible.builtin.user` |
| `group` | `ansible.builtin.group` |
| `exec` | `ansible.builtin.command` |
| `cron` | `ansible.builtin.cron` |
| `host` | `ansible.builtin.lineinfile` |
| `mount` | `ansible.posix.mount` |
| `ssh_authorized_key` | `ansible.posix.authorized_key` |

**Examples:**

```bash
# Print playbook to stdout
souschef puppet convert manifests/webserver.pp

# Save playbook to file
souschef puppet convert manifests/webserver.pp --output playbook.yml
```

**Example output:**
```yaml
---
- name: Converted from manifests/webserver.pp
  hosts: all
  gather_facts: true
  tasks:
    - name: "package[nginx]"
      ansible.builtin.package:
        name: nginx
        state: present

    - name: "service[nginx]"
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true
```

---

### puppet convert-module

Convert an entire Puppet module directory to an Ansible playbook.

**Syntax:**
```bash
souschef puppet convert-module MODULE_PATH [OPTIONS]
```

**Options:**
- `MODULE_PATH` (required): Path to the Puppet module directory
- `--output`, `-o`: Path to save the generated playbook YAML
- `--output-dir`: Save individual playbook files per manifest into this directory

**Examples:**

```bash
# Convert module to a single consolidated playbook
souschef puppet convert-module modules/nginx --output nginx_playbook.yml

# Save per-manifest playbooks into a directory
souschef puppet convert-module modules/myapp --output-dir ./roles/myapp
```

---

### puppet list-types

List all Puppet resource types that SousChef can convert automatically.

**Syntax:**
```bash
souschef puppet list-types
```

**Example output:**
```
Supported Puppet Resource Types
================================
package  → ansible.builtin.package
service  → ansible.builtin.service
file     → ansible.builtin.file / copy / template
user     → ansible.builtin.user
group    → ansible.builtin.group
exec     → ansible.builtin.command
cron     → ansible.builtin.cron
host     → ansible.builtin.lineinfile
mount    → ansible.posix.mount
ssh_authorized_key → ansible.posix.authorized_key
```

---

## Output Formats

### Text Format

Human-readable format with structured sections.

**Best for:**
- Console output
- Quick inspection
- Log files

**Example:**
```
Resource 1:
  Type: package
  Name: nginx
  Action: install
```

### JSON Format

Machine-readable structured data.

**Best for:**
- Automation scripts
- CI/CD pipelines
- Data processing

**Example:**
```json
{
  "resources": [
    {
      "type": "package",
      "name": "nginx",
      "action": "install"
    }
  ]
}
```

**Processing JSON:**

```bash
# Extract specific fields with jq
souschef-cli recipe default.rb --format json | jq '.resources[].name'

# Count resources
souschef-cli recipe default.rb --format json | jq '.resources | length'

# Filter by resource type
souschef-cli recipe default.rb --format json | jq '.resources[] | select(.type=="package")'
```

---

## Common Workflows

### Bulk Recipe Analysis

Analyze multiple recipes in a directory:

```bash
for recipe in recipes/*.rb; do
  echo "Analyzing: $recipe"
  souschef-cli recipe "$recipe" --format json > "analysis/$(basename "$recipe" .rb).json"
done
```

### Generate Migration Report

Create comprehensive migration analysis:

```bash
#!/bin/bash
COOKBOOK_PATH="$1"
OUTPUT_DIR="migration_report"

mkdir -p "$OUTPUT_DIR"

# Analyze structure
souschef-cli structure "$COOKBOOK_PATH" > "$OUTPUT_DIR/structure.txt"

# Parse all recipes
for recipe in "$COOKBOOK_PATH/recipes"/*.rb; do
  name=$(basename "$recipe" .rb)
  souschef-cli recipe "$recipe" --format json > "$OUTPUT_DIR/recipe_${name}.json"
done

# Profile performance
souschef-cli profile "$COOKBOOK_PATH" --output "$OUTPUT_DIR/performance.txt"

echo "Migration report generated in $OUTPUT_DIR"
```

### Convert All Resources

Extract and convert all resources from a recipe:

```bash
#!/bin/bash
RECIPE="$1"

# Parse recipe to JSON
souschef-cli recipe "$RECIPE" --format json > recipe_parsed.json

# Extract resource list and convert each
jq -r '.resources[] | "\(.type) \(.name)"' recipe_parsed.json | \
while read -r type name; do
  echo "Converting: $type[$name]"
  souschef-cli convert "$type" "$name"
done
```

### CI/CD Pipeline Integration

Validate cookbook structure in CI:

```bash
#!/bin/bash
set -e

COOKBOOK_PATH="$1"

echo "Validating cookbook structure..."
souschef-cli structure "$COOKBOOK_PATH" || exit 1

echo "Parsing recipes..."
for recipe in "$COOKBOOK_PATH/recipes"/*.rb; do
  souschef-cli recipe "$recipe" --format json || exit 1
done

echo "Profiling performance..."
souschef-cli profile "$COOKBOOK_PATH" --output performance.txt

# Fail if performance is poor (example threshold)
if grep -q "SLOW" performance.txt; then
  echo "ERROR: Performance issues detected"
  exit 1
fi

echo "[OK] All validations passed"
```

---

## Shell Completion

Enable shell completion for faster command entry:

=== "Bash"
    ```bash
    # Add to ~/.bashrc
    eval "$(_SOUSCHEF_CLI_COMPLETE=bash_source souschef-cli)"
    ```

=== "Zsh"
    ```zsh
    # Add to ~/.zshrc
    eval "$(_SOUSCHEF_CLI_COMPLETE=zsh_source souschef-cli)"
    ```

=== "Fish"
    ```fish
    # Add to ~/.config/fish/completions/souschef-cli.fish
    eval (env _SOUSCHEF_CLI_COMPLETE=fish_source souschef-cli)
    ```

---

## PowerShell Migration Commands

Convert PowerShell provisioning scripts to Windows Ansible automation using `ansible.windows`, `community.windows`, and `chocolatey.chocolatey` collections.

### powershell-parse

Parse a PowerShell provisioning script and extract structured actions.

**Syntax:**
```bash
souschef-cli powershell-parse PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to the PowerShell script (`.ps1` file)
- `--format`: Output format — `json` (default) or `text`

**Example:**

```bash
souschef-cli powershell-parse scripts/setup.ps1
```

**Output Format (JSON):**

```json
{
  "source": "/absolute/path/to/setup.ps1",
  "actions": [
    {
      "action_type": "windows_feature_install",
      "params": {
        "feature_name": "Web-Server",
        "include_management_tools": true
      },
      "confidence": "high",
      "source_line": 3,
      "requires_elevation": true
    }
  ],
  "warnings": [],
  "metrics": {
    "windows_feature_install": 1,
    "registry_set": 2
  }
}
```

---

### powershell-convert

Convert a PowerShell provisioning script to an Ansible playbook.

**Syntax:**
```bash
souschef-cli powershell-convert PATH [--playbook-name NAME] [--hosts PATTERN] [--output FILE] [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to the PowerShell script (`.ps1` file)
- `--playbook-name`: Name for the generated Ansible play (default: `powershell_migration`)
- `--hosts`: Ansible inventory group or host pattern (default: `windows`)
- `--output`, `-o`: Write the generated playbook YAML to this file path
- `--format`: Output format for the full result — `json` (default) or `text`

**Examples:**

=== "Basic conversion"
    ```bash
    souschef-cli powershell-convert scripts/setup.ps1
    ```

=== "Save to file"
    ```bash
    souschef-cli powershell-convert scripts/setup.ps1 \
        --playbook-name iis_setup \
        --hosts windows_servers \
        --output playbook.yml
    ```

**Output (saved to file):**

```
Playbook written to: playbook.yml
Tasks generated: 12 (win_shell fallbacks: 2)
Warnings: 2
```

---

### powershell-inventory

Generate a WinRM-ready Ansible inventory for Windows managed nodes.

**Syntax:**
```bash
souschef-cli powershell-inventory [--hosts HOSTS] [--winrm-port PORT] [--no-ssl] [--output FILE]
```

**Options:**
- `--hosts`: Comma-separated Windows host names or IPs (default: placeholder)
- `--winrm-port`: WinRM port (default: `5986` for HTTPS)
- `--no-ssl`: Use HTTP transport instead of HTTPS (port `5985`)
- `--output`, `-o`: Write inventory to this file path

**Examples:**

=== "Generate to stdout"
    ```bash
    souschef-cli powershell-inventory \
        --hosts "win01.example.com,win02.example.com"
    ```

=== "Save to file"
    ```bash
    souschef-cli powershell-inventory \
        --hosts "win01.example.com,win02.example.com" \
        --output inventory/hosts
    ```

**Output:**

```ini
[windows]
win01.example.com
win02.example.com

[windows:vars]
ansible_connection=winrm
ansible_winrm_transport=ssl
ansible_port=5986
ansible_winrm_server_cert_validation=ignore
```

---

### powershell-requirements

Generate `requirements.yml` with required Ansible collections for Windows automation.

**Syntax:**
```bash
souschef-cli powershell-requirements [PATH] [--output FILE]
```

**Options:**
- `PATH` (optional): Path to a PowerShell script. When provided, tailors the output to the collections actually needed.
- `--output`, `-o`: Write `requirements.yml` to this file path

**Examples:**

=== "Tailored to script"
    ```bash
    souschef-cli powershell-requirements scripts/setup.ps1 -o requirements.yml
    ```

=== "All Windows collections"
    ```bash
    souschef-cli powershell-requirements -o requirements.yml
    ```

**Output:**

```yaml
---
collections:
  - name: ansible.windows
    version: ">=2.3.0"
  - name: community.windows
    version: ">=2.2.0"
  - name: chocolatey.chocolatey
    version: ">=1.5.0"
```

---

### powershell-role

Generate a complete Ansible role from a PowerShell script.

**Syntax:**
```bash
souschef-cli powershell-role PATH [--role-name NAME] [--playbook-name NAME] [--hosts PATTERN] [--output-dir DIR]
```

**Options:**
- `PATH` (required): Path to the PowerShell script (`.ps1` file)
- `--role-name`: Name for the generated Ansible role (default: `windows_provisioning`)
- `--playbook-name`: Base name for the top-level playbook file (default: `site`)
- `--hosts`: Ansible inventory host/group pattern (default: `windows`)
- `--output-dir`, `-o`: Write all role files under this directory

**Example:**

```bash
souschef-cli powershell-role scripts/setup.ps1 \
    --role-name iis_server \
    --output-dir ./ansible-role
```

**Output:**

```
Role files written to: ./ansible-role
Files generated: 10
```

**Generated structure:**

```
ansible-role/
├── roles/
│   └── iis_server/
│       ├── tasks/main.yml
│       ├── handlers/main.yml
│       ├── defaults/main.yml
│       ├── vars/main.yml
│       ├── meta/main.yml
│       └── README.md
├── site.yml
├── inventory/hosts
├── group_vars/windows.yml
└── requirements.yml
```

---

### powershell-job-template

Generate an AWX/AAP Windows job template from a PowerShell script.

**Syntax:**
```bash
souschef-cli powershell-job-template PATH [--name NAME] [--playbook FILE] [--inventory NAME] [--project NAME] [--credential NAME] [--environment ENV] [--no-survey] [--output FILE]
```

**Options:**
- `PATH` (required): Path to the PowerShell script (`.ps1` file)
- `--name`: Display name for the AWX job template (default: `Windows PowerShell Migration`)
- `--playbook`: Playbook file relative to project root (default: `site.yml`)
- `--inventory`: Inventory name or ID in AWX (default: `windows-inventory`)
- `--project`: Project name or ID in AWX (default: `windows-migration-project`)
- `--credential`: Windows credential name in AWX (default: `windows-winrm-credential`)
- `--environment`: Target environment label (default: `production`)
- `--no-survey`: Skip survey spec generation
- `--output`, `-o`: Write job template JSON to this file path

**Example:**

```bash
souschef-cli powershell-job-template scripts/setup.ps1 \
    --name "Setup IIS Web Server" \
    --credential iis-winrm-credential \
    --output job_template.json
```

**Output (stdout):**

```
=== AWX Job Template JSON ===
{ ... }

=== Import Command ===
awx job_templates create --conf.host https://awx.example.com ...

=== Action Summary ===
Script: setup.ps1
Actions: 12 total (10 automated, 2 manual review)
```

---

### powershell-fidelity

Analyse migration fidelity for a PowerShell provisioning script.

**Syntax:**
```bash
souschef-cli powershell-fidelity PATH [--format FORMAT]
```

**Options:**
- `PATH` (required): Path to the PowerShell script (`.ps1` file)
- `--format`: Output format — `json` (default) or `text`

**Example:**

```bash
souschef-cli powershell-fidelity scripts/setup.ps1
souschef-cli powershell-fidelity scripts/setup.ps1 --format text
```

**Output Format (JSON):**

```json
{
  "fidelity_score": 87.5,
  "total_actions": 40,
  "automated_actions": 35,
  "fallback_actions": 5,
  "review_required": [
    "Line 42: Invoke-Expression $cmd - unrecognised pattern"
  ],
  "summary": "87.5% of actions map to idiomatic Ansible modules.",
  "recommendations": [
    "Review win_shell fallbacks at lines 42, 67, 88, 99, 120",
    "Consider using ansible.windows.win_command for known executables"
  ]
}
```

---

## Troubleshooting

### Command Not Found

**Problem:** `souschef-cli: command not found`

**Solutions:**

1. Ensure SousChef is installed:
   ```bash
   pip install mcp-souschef
   ```

2. Check if command is in PATH:
   ```bash
   which souschef-cli
   ```

3. Use Python module directly:
   ```bash
   python -m souschef.cli --help
   ```

### Parse Errors

**Problem:** Recipe parsing fails with syntax errors

**Solutions:**

1. Verify Ruby syntax:
   ```bash
   ruby -c recipe.rb
   ```

2. Check file encoding:
   ```bash
   file -i recipe.rb
   ```

3. Try with error handling:
   ```bash
   souschef-cli recipe recipe.rb 2>&1 | tee error.log
   ```

### Performance Issues

**Problem:** Slow parsing for large cookbooks

**Solutions:**

1. Profile to identify bottlenecks:
   ```bash
   souschef-cli profile /path/to/cookbook --output perf.txt
   cat perf.txt
   ```

2. Profile specific slow operations:
   ```bash
   souschef-cli profile-operation recipe slow_recipe.rb --detailed
   ```

3. Consider chunking large files or parallelizing

---

## Related Documentation

- [MCP Tools Reference](mcp-tools.md) - AI-assisted tool usage
- [Examples](examples.md) - Real-world migration patterns
- [Migration Guide](../migration-guide/overview.md) - Complete migration methodology
- [API Reference](../api-reference/cli.md) - Technical CLI implementation

---

## Getting Help

```bash
# General help
souschef-cli --help

# Command-specific help
souschef-cli recipe --help
souschef-cli convert --help

# Version information
souschef-cli --version
```

For issues or feature requests, see [Contributing](../contributing.md).
