# Terraform Provider

SousChef includes a Terraform provider that enables infrastructure-as-code management of Chef to Ansible migrations, Habitat to Docker conversions, and InSpec profile transformations.

## Overview

The Terraform provider allows you to:

- **Manage migrations declaratively** - Define cookbook conversions in Terraform configuration
- **Track migration state** - Terraform tracks which cookbooks have been migrated
- **Assess before migrating** - Query migration complexity and cost estimates using data sources
- **Automate migration pipelines** - Integrate with CI/CD and GitOps workflows
- **Batch process cookbooks** - Convert multiple recipes in one operation
- **Containerise Habitat plans** - Transform Chef Habitat plans to Dockerfiles
- **Convert testing frameworks** - Migrate InSpec profiles to modern test tools

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

**Resource Behaviour:**

- **Create:** Converts the specified Chef recipe to an Ansible playbook
- **Read:** Verifies the playbook still exists and reads current content
- **Update:** Re-runs the conversion if cookbook_path or recipe_name changes
- **Delete:** Removes the generated Ansible playbook file

### souschef_batch_migration

Manages batch migration of multiple Chef recipes from a single cookbook to Ansible playbooks.

**Example:**

```terraform
resource "souschef_batch_migration" "web_server" {
  cookbook_path = "/path/to/chef/cookbooks/web_server"
  output_path   = "/path/to/ansible/playbooks"
  recipe_names  = ["default", "setup", "deploy", "configure"]
}

output "playbook_count" {
  value = souschef_batch_migration.web_server.playbook_count
}

output "all_playbooks" {
  value = souschef_batch_migration.web_server.playbooks
}
```

**Arguments:**

- `cookbook_path` (Required, string) - Path to the Chef cookbook directory
- `output_path` (Required, string) - Directory where Ansible playbooks will be written
- `recipe_names` (Required, list of strings) - List of recipe names to convert

**Attributes:**

- `id` (string) - Unique identifier for the batch migration
- `cookbook_name` (string) - Name of the cookbook
- `playbook_count` (number) - Number of playbooks generated
- `playbooks` (map of strings) - Map of recipe names to playbook content

**Resource Behaviour:**

- **Create:** Converts all specified recipes to Ansible playbooks in one operation
- **Read:** Verifies all playbooks exist and reads current content
- **Update:** Re-runs conversion if cookbook_path or recipe_names change
- **Delete:** Removes all generated Ansible playbook files

### souschef_habitat_migration

Manages conversion of Chef Habitat plans to Dockerfiles for containerised deployments.

**Example:**

```terraform
resource "souschef_habitat_migration" "nginx" {
  plan_path   = "/path/to/habitat/nginx/plan.sh"
  output_path = "/path/to/docker"
  base_image  = "ubuntu:22.04"  # Optional, defaults to ubuntu:latest
}

output "dockerfile" {
  value = souschef_habitat_migration.nginx.dockerfile_content
}
```

**Arguments:**

- `plan_path` (Required, string) - Path to the Habitat plan.sh file
- `output_path` (Required, string) - Directory where Dockerfile will be written
- `base_image` (Optional, string) - Base Docker image to use (default: ubuntu:latest)

**Attributes:**

- `id` (string) - Unique identifier for the migration
- `package_name` (string) - Name of the Habitat package
- `dockerfile_content` (string) - Generated Dockerfile content

**Resource Behaviour:**

- **Create:** Converts Habitat plan to Dockerfile
- **Read:** Verifies Dockerfile exists and reads current content
- **Update:** Re-runs conversion if plan_path or base_image changes
- **Delete:** Removes the generated Dockerfile

### souschef_inspec_migration

Manages conversion of Chef InSpec profiles to various testing frameworks.

**Example:**

```terraform
resource "souschef_inspec_migration" "linux_baseline" {
  profile_path  = "/path/to/inspec/profiles/linux"
  output_path   = "/path/to/tests"
  output_format = "testinfra"  # Options: testinfra, serverspec, goss, ansible
}

output "test_content" {
  value = souschef_inspec_migration.linux_baseline.test_content
}
```

**Arguments:**

- `profile_path` (Required, string) - Path to the InSpec profile directory
- `output_path` (Required, string) - Directory where converted tests will be written
- `output_format` (Required, string) - Output test framework: `testinfra`, `serverspec`, `goss`, or `ansible`

**Attributes:**

- `id` (string) - Unique identifier for the migration
- `profile_name` (string) - Name of the InSpec profile
- `test_content` (string) - Generated test content

**Output Formats:**

| Format | Extension | Description |
|--------|-----------|-------------|
| `testinfra` | `.py` | Python-based infrastructure testing |
| `serverspec` | `.rb` | Ruby-based server testing |
| `goss` | `.yaml` | YAML-based quick validation |
| `ansible` | `.yml` | Ansible assert/test tasks |

**Resource Behaviour:**

- **Create:** Converts InSpec profile to target test framework
- **Read:** Verifies test file exists and reads current content
- **Update:** Re-runs conversion if profile_path or output_format changes
- **Delete:** Removes the generated test file

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

### souschef_cost_estimate

Fetches detailed cost estimation for migration projects, suitable for Terraform Cloud cost analysis features.

**Example:**

```terraform
data "souschef_cost_estimate" "web_server" {
  cookbook_path         = "/path/to/chef/cookbooks/web_server"
  developer_hourly_rate = 175.0  # Optional, default: 150 USD
  infrastructure_cost   = 1000.0 # Optional, default: 500 USD
}

output "total_cost" {
  value = data.souschef_cost_estimate.web_server.total_project_cost_usd
}

output "labour_cost" {
  value = data.souschef_cost_estimate.web_server.estimated_cost_usd
}

output "breakdown" {
  value = {
    hours      = data.souschef_cost_estimate.web_server.estimated_hours
    labour     = data.souschef_cost_estimate.web_server.estimated_cost_usd
    infra      = 1000.0
    total      = data.souschef_cost_estimate.web_server.total_project_cost_usd
    complexity = data.souschef_cost_estimate.web_server.complexity
  }
}
```

**Arguments:**

- `cookbook_path` (Required, string) - Path to the Chef cookbook directory
- `developer_hourly_rate` (Optional, number) - Developer hourly rate in USD (default: 150)
- `infrastructure_cost` (Optional, number) - Additional infrastructure/tooling cost in USD (default: 500)

**Attributes:**

- `id` (string) - Unique identifier (cookbook path)
- `complexity` (string) - Migration complexity level
- `recipe_count` (number) - Number of recipes
- `resource_count` (number) - Total resources
- `estimated_hours` (number) - Estimated migration hours
- `estimated_cost_usd` (number) - Labour cost in USD (hours × hourly_rate)
- `total_project_cost_usd` (number) - Total cost including infrastructure
- `recommendations` (string) - Cost-aware recommendations

**Cost Calculation:**

- **Labour Cost** = `estimated_hours` × `developer_hourly_rate`
- **Total Cost** = `labour_cost` + `infrastructure_cost`

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

### Batch Migration with Cost Analysis

Migrate multiple recipes only if cost is acceptable:

```terraform
# Get cost estimate before proceeding
data "souschef_cost_estimate" "web_server" {
  cookbook_path         = "/chef/cookbooks/web_server"
  developer_hourly_rate = 200.0
  infrastructure_cost   = 750.0
}

# Only proceed if total cost is under budget
resource "souschef_batch_migration" "web_server" {
  count = data.souschef_cost_estimate.web_server.total_project_cost_usd < 5000 ? 1 : 0

  cookbook_path = "/chef/cookbooks/web_server"
  output_path   = "/ansible/playbooks"
  recipe_names  = ["default", "setup", "deploy", "configure"]
}

output "migration_decision" {
  value = {
    total_cost_usd  = data.souschef_cost_estimate.web_server.total_project_cost_usd
    labour_cost_usd = data.souschef_cost_estimate.web_server.estimated_cost_usd
    hours           = data.souschef_cost_estimate.web_server.estimated_hours
    complexity      = data.souschef_cost_estimate.web_server.complexity
    approved        = length(souschef_batch_migration.web_server) > 0
    reason          = length(souschef_batch_migration.web_server) > 0 ? "Within budget" : "Cost exceeds $5,000 limit"
  }
}
```

### Habitat to Docker Conversion

Convert Habitat plans to containerised applications:

```terraform
# Convert Habitat plan to Dockerfile
resource "souschef_habitat_migration" "nginx" {
  plan_path   = "/habitat/plans/nginx/plan.sh"
  output_path = "/docker/nginx"
  base_image  = "ubuntu:22.04"
}

resource "souschef_habitat_migration" "postgresql" {
  plan_path   = "/habitat/plans/postgresql/plan.sh"
  output_path = "/docker/postgresql"
  base_image  = "postgres:15-alpine"
}

output "dockerfiles" {
  value = {
    nginx      = souschef_habitat_migration.nginx.dockerfile_content
    postgresql = souschef_habitat_migration.postgresql.dockerfile_content
  }
}
```

### InSpec Profile Transformation

Convert InSpec profiles to multiple test frameworks:

```terraform
locals {
  inspec_profile = "/inspec/profiles/cis-ubuntu-22.04"
}

# Convert to TestInfra for Python-based testing
resource "souschef_inspec_migration" "testinfra" {
  profile_path  = local.inspec_profile
  output_path   = "/tests/testinfra"
  output_format = "testinfra"
}

# Convert to Ansible asserts for integration testing
resource "souschef_inspec_migration" "ansible" {
  profile_path  = local.inspec_profile
  output_path   = "/tests/ansible"
  output_format = "ansible"
}

# Convert to Goss for quick validation
resource "souschef_inspec_migration" "goss" {
  profile_path  = local.inspec_profile
  output_path   = "/tests/goss"
  output_format = "goss"
}

output "test_frameworks" {
  value = {
    testinfra = souschef_inspec_migration.testinfra.test_content
    ansible   = souschef_inspec_migration.ansible.test_content
    goss      = souschef_inspec_migration.goss.test_content
  }
}
```

### Complete Multi-Environment Migration

Manage migrations across multiple environments with cost controls:

```terraform
locals {
  environments = {
    dev  = "/chef/cookbooks/dev"
    test = "/chef/cookbooks/test"
    prod = "/chef/cookbooks/prod"
  }
  hourly_rate = 180.0
  infra_cost  = 800.0
}

# Get cost estimates for all environments
data "souschef_cost_estimate" "environments" {
  for_each = local.environments

  cookbook_path         = each.value
  developer_hourly_rate = local.hourly_rate
  infrastructure_cost   = local.infra_cost
}

# Migrate environments that aren't High complexity and under $10k
resource "souschef_batch_migration" "environments" {
  for_each = {
    for env, path in local.environments :
    env => path
    if data.souschef_cost_estimate.environments[env].complexity != "High" &&
       data.souschef_cost_estimate.environments[env].total_project_cost_usd < 10000
  }

  cookbook_path = each.value
  output_path   = "/ansible/playbooks/${each.key}"
  recipe_names  = ["default", "config", "deploy"]
}

output "environment_analysis" {
  value = {
    for env, cost_data in data.souschef_cost_estimate.environments :
    env => {
      total_cost_usd = cost_data.total_project_cost_usd
      labour_hours   = cost_data.estimated_hours
      complexity     = cost_data.complexity
      migrated       = contains(keys(souschef_batch_migration.environments), env)
      playbook_count = try(souschef_batch_migration.environments[env].playbook_count, 0)
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

### 1. Use Cost Estimates for Budget Planning

Always estimate costs before committing to large migrations:

```terraform
data "souschef_cost_estimate" "cookbook" {
  cookbook_path         = var.cookbook_path
  developer_hourly_rate = var.hourly_rate
  infrastructure_cost   = var.infra_cost
}

# Make data-driven decisions
locals {
  should_migrate = (
    data.souschef_cost_estimate.cookbook.total_project_cost_usd < var.budget &&
    data.souschef_cost_estimate.cookbook.complexity != "High"
  )
}
```

### 2. Use Batch Migrations for Efficiency

Convert multiple recipes in one operation instead of individually:

```terraform
# [YES] Efficient - single batch operation
resource "souschef_batch_migration" "recipes" {
  cookbook_path = "/chef/cookbooks/app"
  output_path   = "/ansible/playbooks"
  recipe_names  = ["default", "setup", "deploy", "config"]
}

# [NO] Inefficient - multiple separate operations
resource "souschef_migration" "default" {
  cookbook_path = "/chef/cookbooks/app"
  output_path   = "/ansible/playbooks"
  recipe_name   = "default"
}
# ... repeated for each recipe
```

### 3. Organise Output Directories Logically

Structure output paths for clarity:

```terraform
resource "souschef_batch_migration" "services" {
  for_each = var.services

  cookbook_path = "/chef/cookbooks/${each.key}"
  output_path   = "/ansible/playbooks/${each.key}"
  recipe_names  = each.value.recipes
}
```

### 4. Version Your Generated Artefacts

Commit generated playbooks and Dockerfiles to version control:

```terraform
resource "souschef_habitat_migration" "app" {
  plan_path   = var.plan_path
  output_path = "${path.module}/generated/docker"
}

resource "local_file" "dockerfile" {
  filename = "${path.module}/docker/Dockerfile"
  content  = souschef_habitat_migration.app.dockerfile_content

  lifecycle {
    create_before_destroy = true
  }
}
```

### 5. Use Data Sources for Conditional Logic

Make intelligent decisions based on assessment data:

```terraform
data "souschef_assessment" "cookbook" {
  cookbook_path = var.cookbook_path
}

# Only proceed with migration if complexity is acceptable
resource "souschef_migration" "cookbook" {
  count = contains(["Low", "Medium"], data.souschef_assessment.cookbook.complexity) ? 1 : 0
  # ...
}
```

### 6. Validate Before Applying

Always review Terraform plans before execution:

```bash
terraform plan -out=migration.tfplan
# Review changes carefully
terraform show migration.tfplan
# Apply only after verification
terraform apply migration.tfplan
```

### 7. Test Converted Artefacts

Validate generated playbooks and Dockerfiles:

```terraform
# Generate test playbook
resource "souschef_migration" "test" {
  cookbook_path = var.cookbook_path
  output_path   = "/tmp/test-playbooks"
  recipe_name   = "default"
}

# Run validation
resource "null_resource" "validate_playbook" {
  provisioner "local-exec" {
    command = "ansible-playbook --syntax-check /tmp/test-playbooks/default.yml"
  }

  depends_on = [souschef_migration.test]
}

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

## Limitations

- The provider requires the SousChef CLI to be installed (>= 2.4.0)
- Migrations run locally on the Terraform executor
- Large cookbooks may take significant time to convert
- The provider does not currently support remote execution
- Habitat conversions require valid plan.sh files
- InSpec migrations support four output formats (testinfra, serverspec, goss, ansible)
- Cost estimates are approximations based on cookbook complexity

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

Ensure the CLI is in your PATH or explicitly configured:

```bash
# Check CLI availability
which souschef
souschef --version

# Or specify explicit path in provider config
provider "souschef" {
  souschef_path = "/usr/local/bin/souschef"
}
```

### Permission Errors

Check read permissions on cookbook paths and write permissions on output paths:

```bash
# Verify cookbook access
ls -la /path/to/cookbooks

# Verify output directory permissions
ls -la /path/to/output
mkdir -p /path/to/output  # Create if needed
```

### Conversion Failures

If migrations fail, check the SousChef CLI directly:

```bash
# Test recipe conversion
souschef convert-recipe --cookbook-path /path/to/cookbook \
  --output-path /tmp/test --recipe-name default

# Test Habitat conversion
souschef convert-habitat --plan-path /path/to/plan.sh \
  --output-path /tmp/test

# Test InSpec conversion
souschef convert-inspec --profile-path /path/to/profile \
  --output-path /tmp/test --format testinfra
```

### Cost Estimate Accuracy

Cost estimates are approximations. For precise estimates:

```terraform
# Get detailed assessment
data "souschef_assessment" "detailed" {
  cookbook_path = var.cookbook_path
}

# Calculate custom estimates
locals {
  custom_hours = (
    data.souschef_assessment.detailed.estimated_hours *
    var.complexity_multiplier
  )
  custom_cost = local.custom_hours * var.hourly_rate
}
```

### Performance Issues

For large cookbooks or batch migrations:

```terraform
# Process in smaller batches
resource "souschef_batch_migration" "batch_1" {
  cookbook_path = var.cookbook_path
  output_path   = var.output_path
  recipe_names  = slice(var.all_recipes, 0, 5)
}

resource "souschef_batch_migration" "batch_2" {
  cookbook_path = var.cookbook_path
  output_path   = var.output_path
  recipe_names  = slice(var.all_recipes, 5, 10)
}
```

## Next Steps

- Review the [Migration Guide](../migration-guide/planning-migration.md) for best practices
- See [CLI Usage](cli-usage.md) for direct SousChef CLI commands
- Check [API Reference](../api-reference/converters.md) for programmatic usage

## Related Resources

- [Terraform Provider Development](https://developer.hashicorp.com/terraform/plugin)
- [HashiCorp Configuration Language](https://developer.hashicorp.com/terraform/language)
- [SousChef GitHub Repository](https://github.com/kpeacocke/souschef)
