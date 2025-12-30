# SousChef CLI Quick Reference

Command-line interface for parsing and converting Chef cookbooks.

## Installation

```bash
# Install with uv
cd /path/to/souschef
uv sync

# Verify installation
souschef-cli --version
souschef-cli --help
```

## Commands

### Parse Recipe
Parse a Chef recipe file and extract resources.

```bash
souschef-cli recipe path/to/recipe.rb
souschef-cli recipe path/to/recipe.rb --format json
```

**Output:** List of resources with types, names, actions, and properties

### Parse Template
Convert Chef ERB templates to Jinja2 format.

```bash
souschef-cli template path/to/template.erb
souschef-cli template path/to/template.erb --format json
```

**Output:** JSON with extracted variables and Jinja2 template

### Parse Custom Resource
Parse Chef custom resources and LWRPs.

```bash
souschef-cli resource path/to/custom_resource.rb
souschef-cli resource path/to/custom_resource.rb --format json
```

**Output:** JSON with resource properties, attributes, and actions

### Parse Attributes
Extract Chef attribute definitions.

```bash
souschef-cli attributes path/to/attributes.rb
souschef-cli attributes path/to/attributes.rb --format json
```

**Output:** List of attributes with names and default values

### Parse InSpec Profile
Parse InSpec controls and extract test information.

```bash
souschef-cli inspec-parse path/to/inspec/profile/
souschef-cli inspec-parse path/to/control.rb
souschef-cli inspec-parse path/to/control.rb --format json
```

**Output:** JSON with parsed InSpec controls, describe blocks, and expectations

### Convert InSpec to Tests
Convert InSpec controls to Testinfra or Ansible assert format.

```bash
# Convert to Testinfra (default)
souschef-cli inspec-convert path/to/control.rb
souschef-cli inspec-convert path/to/inspec/profile/ --format testinfra

# Convert to Ansible assert tasks
souschef-cli inspec-convert path/to/control.rb --format ansible_assert
```

**Output:**
- `testinfra`: Python pytest code with host fixtures
- `ansible_assert`: YAML assert tasks for Ansible playbooks

### Generate InSpec from Recipe
Generate InSpec controls from Chef recipe resources.

```bash
souschef-cli inspec-generate path/to/recipe.rb
souschef-cli inspec-generate path/to/recipe.rb --format json
```

**Output:** InSpec controls that validate the Chef recipe resources

### Parse Metadata
Parse cookbook metadata.rb file.

```bash
souschef-cli metadata path/to/metadata.rb
```

**Output:** Cookbook name, version, maintainer, and dependencies

### List Cookbook Structure
Display the directory structure of a Chef cookbook.

```bash
souschef-cli structure path/to/cookbook
```

**Output:** Tree view of cookbook files and directories

### Convert Resource
Convert Chef resources to Ansible tasks.

```bash
# Package installation
souschef-cli convert package nginx --action install
souschef-cli convert package nginx --action install --format json

# Service management
souschef-cli convert service nginx --action start
souschef-cli convert service nginx --action enable

# Template creation
souschef-cli convert template /etc/nginx/nginx.conf --action create

# File operations
souschef-cli convert file /tmp/test.txt --action create
souschef-cli convert file /tmp/test.txt --action delete
```

**Output:** Ansible task in YAML or JSON format

### Analyze Cookbook
Comprehensive analysis of an entire Chef cookbook.

```bash
# Full analysis
souschef-cli cookbook path/to/cookbook

# Dry run (show what would be done)
souschef-cli cookbook path/to/cookbook --dry-run

# Specify output directory
souschef-cli cookbook path/to/cookbook --output /tmp/ansible-playbook
```

**Output:** Summary of metadata, recipes, resources, templates, and attributes

### File Operations

```bash
# List directory contents
souschef-cli ls path/to/directory

# Read file contents
souschef-cli cat path/to/file
```

## Output Formats

Most commands support the `--format` flag:

- `text` - Human-readable text (default for most commands)
- `json` - Structured JSON output (default for templates and resources)
- `yaml` - YAML output (for conversions)

## Examples

### Basic Workflow

```bash
# 1. Analyze cookbook structure
souschef-cli structure /path/to/nginx-cookbook

# 2. Parse metadata
souschef-cli metadata /path/to/nginx-cookbook/metadata.rb

# 3. Parse recipe
souschef-cli recipe /path/to/nginx-cookbook/recipes/default.rb

# 4. Convert specific resources
souschef-cli convert package nginx --action install > tasks/install.yml
souschef-cli convert service nginx --action start > tasks/service.yml

# 5. Parse and convert templates
souschef-cli template /path/to/nginx-cookbook/templates/default/nginx.conf.erb
# 6. Generate InSpec validation
souschef-cli inspec-generate /path/to/nginx-cookbook/recipes/default.rb > validation/controls.rb

# 7. Convert existing InSpec to tests
souschef-cli inspec-convert validation/controls.rb --format testinfra > tests/test_nginx.py# 6. Generate InSpec validation
souschef-cli inspec-generate /path/to/nginx-cookbook/recipes/default.rb > validation/controls.rb

# 7. Convert existing InSpec to tests
souschef-cli inspec-convert validation/controls.rb --format testinfra > tests/test_nginx.py```

### Advanced Usage

```bash
# Parse recipe with JSON for programmatic use
souschef-cli recipe recipe.rb --format json | jq '.resources[] | select(.type=="package")'

# Full cookbook analysis
souschef-cli cookbook /cookbooks/nginx > nginx-analysis.txt

# Convert multiple resources
for resource in package service template; do
  souschef-cli convert $resource nginx > ${resource}.yml
done

# InSpec workflow - Chef to Ansible to validation
souschef-cli recipe nginx.rb --format json > chef-resources.json
souschef-cli inspec-generate nginx.rb > validation.rb
souschef-cli inspec-convert validation.rb --format testinfra > test_nginx.py

# Parse and analyze InSpec profiles
souschef-cli inspec-parse /profiles/baseline --format json | jq '.controls_count'
```

## Help

Get help for any command:

```bash
souschef-cli --help
souschef-cli recipe --help
souschef-cli convert --help
```

## See Also

- [README.md](README.md) - Full project documentation
- [examples/](examples/) - Complete cookbook examples
- [examples/web-server/CONVERSION.md](examples/web-server/CONVERSION.md) - Detailed conversion guide
