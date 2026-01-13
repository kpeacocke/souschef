# Terraform Provider

SousChef includes a Terraform provider that enables infrastructure-as-code management of Chef to Ansible migrations.

## Overview

The Terraform provider allows you to:

- **Manage migrations declaratively** - Define cookbook conversions in Terraform configuration
- **Track migration state** - Terraform tracks which cookbooks have been migrated
- **Assess before migrating** - Query migration complexity using data sources
- **Automate migration pipelines** - Integrate with CI/CD and GitOps workflows

## Installation

### Prerequisites

- Terraform >= 1.0
- SousChef CLI installed (>= 2.4.0) and available in PATH
- Go >= 1.21 (for building from source)

### Building from Source

```bash
cd terraform-provider
go mod download
go build -o terraform-provider-souschef
```

### Local Installation

```bash
# Create plugins directory
mkdir -p ~/.terraform.d/plugins/registry.terraform.io/kpeacocke/souschef/0.1.0/linux_amd64

# Copy binary
cp terraform-provider-souschef ~/.terraform.d/plugins/registry.terraform.io/kpeacocke/souschef/0.1.0/linux_amd64/
```

## Configuration

Configure the provider in your Terraform configuration:

```terraform
terraform {
  required_providers {
    souschef = {
      source  = "kpeacocke/souschef"
      version = "~> 0.1"
    }
  }
}

provider "souschef" {
  # Optional: specify custom souschef CLI path
  souschef_path = "/usr/local/bin/souschef"
}
```

If `souschef_path` is not specified, the provider will use `souschef` from your PATH.

## Resources

### souschef_migration

Manages a Chef cookbook to Ansible playbook migration.

**Example:**

```terraform
resource "souschef_migration" "web_server" {
  cookbook_path = "/path/to/chef/cookbooks/web_server"
  output_path   = "/path/to/ansible/playbooks"
  recipe_name   = "default"
}
```

**Arguments:**

- `cookbook_path` (Required, string) - Path to the Chef cookbook directory
- `output_path` (Required, string) - Directory where Ansible playbook will be written
- `recipe_name` (Optional, string) - Name of the recipe to convert. Defaults to "default"

**Attributes:**

- `id` (string) - Unique identifier for the migration (format: `cookbook-recipe`)
- `cookbook_name` (string) - Name of the cookbook
- `playbook_content` (string) - Generated Ansible playbook YAML content

**Resource Behavior:**

- **Create:** Converts the specified Chef recipe to an Ansible playbook
- **Read:** Verifies the playbook still exists and reads current content
- **Update:** Re-runs the conversion if cookbook_path or recipe_name changes
- **Delete:** Removes the generated Ansible playbook file

## Data Sources

### souschef_assessment

Fetches migration assessment for a Chef cookbook.

**Example:**

```terraform
data "souschef_assessment" "web_server" {
  cookbook_path = "/path/to/chef/cookbooks/web_server"
}

output "complexity" {
  value = data.souschef_assessment.web_server.complexity
}

output "estimated_hours" {
  value = data.souschef_assessment.web_server.estimated_hours
}
```

**Arguments:**

- `cookbook_path` (Required, string) - Path to the Chef cookbook directory

**Attributes:**

- `id` (string) - Unique identifier (cookbook path)
- `complexity` (string) - Migration complexity level: "Low", "Medium", or "High"
- `recipe_count` (number) - Number of recipes in the cookbook
- `resource_count` (number) - Total Chef resources across all recipes
- `estimated_hours` (number) - Estimated migration effort in hours
- `recommendations` (string) - Migration recommendations and best practices

## Usage Examples

### Basic Migration

Convert a single cookbook's default recipe:

```terraform
resource "souschef_migration" "database" {
  cookbook_path = "/chef/cookbooks/postgresql"
  output_path   = "/ansible/playbooks"
}
```

### Multiple Recipes

Migrate multiple recipes from the same cookbook:

```terraform
locals {
  web_cookbook = "/chef/cookbooks/web_server"
  recipes = ["default", "setup", "deploy", "configure"]
}

resource "souschef_migration" "web_recipes" {
  for_each = toset(local.recipes)

  cookbook_path = local.web_cookbook
  output_path   = "/ansible/playbooks"
  recipe_name   = each.value
}
```

### Conditional Migration Based on Assessment

Only migrate cookbooks with Low or Medium complexity:

```terraform
data "souschef_assessment" "app_server" {
  cookbook_path = "/chef/cookbooks/app_server"
}

resource "souschef_migration" "app_server" {
  count = contains(["Low", "Medium"], data.souschef_assessment.app_server.complexity) ? 1 : 0

  cookbook_path = data.souschef_assessment.app_server.cookbook_path
  output_path   = "/ansible/playbooks"
}

output "migration_status" {
  value = length(souschef_migration.app_server) > 0 ? "Migrated" : "Skipped (complexity: ${data.souschef_assessment.app_server.complexity})"
}
```

### Migration Pipeline with Multiple Cookbooks

Manage a complete migration project:

```terraform
locals {
  cookbooks = {
    database    = "/chef/cookbooks/postgresql"
    web_server  = "/chef/cookbooks/nginx"
    app_server  = "/chef/cookbooks/rails"
    monitoring  = "/chef/cookbooks/prometheus"
  }
  output_base = "/ansible/playbooks"
}

# Assess all cookbooks
data "souschef_assessment" "cookbooks" {
  for_each = local.cookbooks

  cookbook_path = each.value
}

# Migrate all cookbooks
resource "souschef_migration" "cookbooks" {
  for_each = local.cookbooks

  cookbook_path = each.value
  output_path   = local.output_base
  recipe_name   = "default"
}

# Generate migration report
output "migration_report" {
  value = {
    for name, assessment in data.souschef_assessment.cookbooks : name => {
      complexity      = assessment.complexity
      recipes         = assessment.recipe_count
      resources       = assessment.resource_count
      estimated_hours = assessment.estimated_hours
      playbook_path   = "${local.output_base}/${name}.yml"
      status          = "Completed"
    }
  }
}
```

### Integration with Version Control

Use Terraform to manage migration state while keeping playbooks in Git:

```terraform
resource "souschef_migration" "web_server" {
  cookbook_path = var.cookbook_path
  output_path   = "${path.module}/generated-playbooks"
  recipe_name   = var.recipe_name
}

# Write playbook to version control
resource "local_file" "playbook" {
  filename = "${path.module}/playbooks/${var.recipe_name}.yml"
  content  = souschef_migration.web_server.playbook_content
}
```

## Best Practices

### 1. Use Data Sources for Planning

Always assess cookbooks before migration:

```terraform
data "souschef_assessment" "cookbook" {
  cookbook_path = var.cookbook_path
}

# Use assessment data to make decisions
resource "souschef_migration" "cookbook" {
  count = data.souschef_assessment.cookbook.complexity != "High" ? 1 : 0
  # ...
}
```

### 2. Organize Output Directories

Structure output paths logically:

```terraform
resource "souschef_migration" "recipes" {
  for_each = var.recipes

  cookbook_path = var.cookbook_path
  output_path   = "${var.output_base}/${each.key}"
  recipe_name   = each.value
}
```

### 3. Track Migration State

Use Terraform state to track which cookbooks have been migrated:

```terraform
# backend.tf
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "chef-migration/terraform.tfstate"
    region = "us-east-1"
  }
}
```

### 4. Version Your Playbooks

Commit generated playbooks to version control:

```terraform
resource "souschef_migration" "app" {
  cookbook_path = var.cookbook_path
  output_path   = "${path.module}/generated"
}

resource "local_file" "app_playbook" {
  filename = "${path.module}/playbooks/${var.cookbook_name}.yml"
  content  = souschef_migration.app.playbook_content

  lifecycle {
    create_before_destroy = true
  }
}
```

### 5. Validate Before Apply

Use `terraform plan` to preview migrations:

```bash
terraform plan -out=migration.tfplan
# Review changes
terraform apply migration.tfplan
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Chef to Ansible Migration

on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install SousChef
        run: pip install mcp-souschef

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init
        working-directory: terraform

      - name: Terraform Plan
        run: terraform plan
        working-directory: terraform
```

### GitLab CI

```yaml
stages:
  - assess
  - migrate

assess:
  stage: assess
  script:
    - pip install mcp-souschef
    - terraform init
    - terraform plan

migrate:
  stage: migrate
  script:
    - terraform apply -auto-approve
  only:
    - main
```

## Troubleshooting

### Provider Not Found

If Terraform can't find the provider:

```bash
# Verify installation path
ls -la ~/.terraform.d/plugins/registry.terraform.io/kpeacocke/souschef/

# Run terraform init with debug logging
TF_LOG=DEBUG terraform init
```

### SousChef CLI Not Found

Ensure the CLI is in your PATH:

```bash
which souschef
# Or specify explicit path in provider config
```

### Permission Errors

Check read permissions on cookbook paths and write permissions on output paths:

```bash
ls -la /path/to/cookbooks
ls -la /path/to/output
```

## Limitations

- The provider requires the SousChef CLI to be installed (>= 2.4.0)
- Migrations run locally on the Terraform executor
- Large cookbooks may take significant time to convert
- The provider does not currently support remote execution

## Next Steps

- Review the [Migration Guide](../migration-guide/planning-migration.md) for best practices
- See [CLI Usage](cli-usage.md) for direct SousChef CLI commands
- Check [API Reference](../api-reference/converters.md) for programmatic usage

## Related Resources

- [Terraform Provider Development](https://developer.hashicorp.com/terraform/plugin)
- [HashiCorp Configuration Language](https://developer.hashicorp.com/terraform/language)
- [SousChef GitHub Repository](https://github.com/kpeacocke/souschef)
