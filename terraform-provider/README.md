# Terraform Provider for SousChef

This Terraform provider enables infrastructure-as-code management of Chef to Ansible migrations, Habitat to Docker conversions, and InSpec profile transformations using SousChef.

## Requirements

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- [Go](https://golang.org/doc/install) >= 1.21 (for building)
- [SousChef](https://github.com/kpeacocke/souschef) CLI installed (>= 2.4.0)

## Building

```bash
cd terraform-provider
go mod download
go build -o terraform-provider-souschef
```

## Installation

### Local Development

```bash
# Build the provider
go build -o terraform-provider-souschef

# Create terraform plugins directory
mkdir -p ~/.terraform.d/plugins/registry.terraform.io/kpeacocke/souschef/0.1.0/linux_amd64

# Copy binary
cp terraform-provider-souschef ~/.terraform.d/plugins/registry.terraform.io/kpeacocke/souschef/0.1.0/linux_amd64/
```

### Using the Provider

```terraform
terraform {
  required_providers {
    souschef = {
      source = "kpeacocke/souschef"
      version = "~> 0.1"
    }
  }
}

provider "souschef" {
  souschef_path = "/path/to/souschef"  # Optional, defaults to 'souschef' in PATH
}
```

## Resources

### `souschef_migration`

Manages a Chef cookbook to Ansible playbook migration.

```terraform
resource "souschef_migration" "my_cookbook" {
  cookbook_path = "/path/to/chef/cookbooks/my_cookbook"
  output_path   = "/path/to/ansible/playbooks"
  recipe_name   = "default"  # Optional, defaults to 'default'
}

output "playbook_content" {
  value = souschef_migration.my_cookbook.playbook_content
}
```

#### Attributes

- `cookbook_path` (Required) - Path to the Chef cookbook directory
- `output_path` (Required) - Directory where Ansible playbook will be written
- `recipe_name` (Optional) - Name of the recipe to convert (default: "default")
- `id` (Computed) - Unique identifier for the migration
- `cookbook_name` (Computed) - Name of the cookbook
- `playbook_content` (Computed) - Generated Ansible playbook YAML content

### `souschef_batch_migration`

Manages batch migration of multiple Chef recipes from a single cookbook to Ansible playbooks.

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

#### Attributes

- `cookbook_path` (Required) - Path to the Chef cookbook directory
- `output_path` (Required) - Directory where Ansible playbooks will be written
- `recipe_names` (Required) - List of recipe names to convert
- `id` (Computed) - Unique identifier for the batch migration
- `cookbook_name` (Computed) - Name of the cookbook
- `playbook_count` (Computed) - Number of playbooks generated
- `playbooks` (Computed) - Map of recipe names to playbook content

### `souschef_habitat_migration`

Manages conversion of Chef Habitat plans to Dockerfiles for containerised deployments.

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

#### Attributes

- `plan_path` (Required) - Path to the Habitat plan.sh file
- `output_path` (Required) - Directory where Dockerfile will be written
- `base_image` (Optional) - Base Docker image to use (default: ubuntu:latest)
- `id` (Computed) - Unique identifier for the migration
- `package_name` (Computed) - Name of the Habitat package
- `dockerfile_content` (Computed) - Generated Dockerfile content

### `souschef_inspec_migration`

Manages conversion of Chef InSpec profiles to various testing frameworks.

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

#### Attributes

- `profile_path` (Required) - Path to the InSpec profile directory
- `output_path` (Required) - Directory where converted tests will be written
- `output_format` (Required) - Output test framework (testinfra, serverspec, goss, or ansible)
- `id` (Computed) - Unique identifier for the migration
- `profile_name` (Computed) - Name of the InSpec profile
- `test_content` (Computed) - Generated test content

## Data Sources

### `souschef_assessment`

Fetches migration assessment for a Chef cookbook.

```terraform
data "souschef_assessment" "my_cookbook" {
  cookbook_path = "/path/to/chef/cookbooks/my_cookbook"
}

output "migration_complexity" {
  value = data.souschef_assessment.my_cookbook.complexity
}

output "estimated_hours" {
  value = data.souschef_assessment.my_cookbook.estimated_hours
}
```

#### Attributes

- `cookbook_path` (Required) - Path to the Chef cookbook directory
- `id` (Computed) - Unique identifier (cookbook path)
- `complexity` (Computed) - Migration complexity level (Low/Medium/High)
- `recipe_count` (Computed) - Number of recipes in cookbook
- `resource_count` (Computed) - Total Chef resources across all recipes
- `estimated_hours` (Computed) - Estimated migration effort in hours
- `recommendations` (Computed) - Migration recommendations and best practices

### `souschef_cost_estimate`

Fetches detailed cost estimation for migration projects, suitable for Terraform Cloud cost analysis features.

```terraform
data "souschef_cost_estimate" "my_cookbook" {
  cookbook_path         = "/path/to/chef/cookbooks/my_cookbook"
  developer_hourly_rate = 175.0  # Optional, default: 150 USD
  infrastructure_cost   = 1000.0 # Optional, default: 500 USD
}

output "total_cost" {
  value = data.souschef_cost_estimate.my_cookbook.total_project_cost_usd
}

output "labour_cost" {
  value = data.souschef_cost_estimate.my_cookbook.estimated_cost_usd
}
```

#### Attributes

- `cookbook_path` (Required) - Path to the Chef cookbook directory
- `developer_hourly_rate` (Optional) - Developer hourly rate in USD (default: 150)
- `infrastructure_cost` (Optional) - Additional infrastructure/tooling cost in USD (default: 500)
- `id` (Computed) - Unique identifier (cookbook path)
- `complexity` (Computed) - Migration complexity level
- `recipe_count` (Computed) - Number of recipes
- `resource_count` (Computed) - Total resources
- `estimated_hours` (Computed) - Estimated migration hours
- `estimated_cost_usd` (Computed) - Labour cost in USD
- `total_project_cost_usd` (Computed) - Total cost including infrastructure
- `recommendations` (Computed) - Cost-aware recommendations

## Example Usage

### Basic Single Migration

```terraform
terraform {
  required_providers {
    souschef = {
      source = "kpeacocke/souschef"
    }
  }
}

provider "souschef" {}

resource "souschef_migration" "database" {
  cookbook_path = "/chef/cookbooks/postgresql"
  output_path   = "/ansible/playbooks"
}
```

### Batch Migration with Cost Analysis

```terraform
# Get cost estimate before proceeding
data "souschef_cost_estimate" "web_server" {
  cookbook_path         = "/chef/cookbooks/web_server"
  developer_hourly_rate = 200.0
  infrastructure_cost   = 750.0
}

# Only proceed if cost is acceptable
resource "souschef_batch_migration" "web_server" {
  count = data.souschef_cost_estimate.web_server.total_project_cost_usd < 5000 ? 1 : 0

  cookbook_path = "/chef/cookbooks/web_server"
  output_path   = "/ansible/playbooks"
  recipe_names  = ["default", "setup", "deploy"]
}

output "migration_cost" {
  value = {
    total_usd       = data.souschef_cost_estimate.web_server.total_project_cost_usd
    labour_usd      = data.souschef_cost_estimate.web_server.estimated_cost_usd
    hours           = data.souschef_cost_estimate.web_server.estimated_hours
    complexity      = data.souschef_cost_estimate.web_server.complexity
    approved        = length(souschef_batch_migration.web_server) > 0
  }
}
```

### Habitat and InSpec Conversions

```terraform
# Convert Habitat plan to Dockerfile
resource "souschef_habitat_migration" "nginx" {
  plan_path   = "/habitat/plans/nginx/plan.sh"
  output_path = "/docker/nginx"
  base_image  = "ubuntu:22.04"
}

# Convert InSpec profile to TestInfra
resource "souschef_inspec_migration" "security_baseline" {
  profile_path  = "/inspec/profiles/cis-ubuntu"
  output_path   = "/tests/testinfra"
  output_format = "testinfra"
}

# Convert same profile to Ansible asserts for integration
resource "souschef_inspec_migration" "security_ansible" {
  profile_path  = "/inspec/profiles/cis-ubuntu"
  output_path   = "/tests/ansible"
  output_format = "ansible"
}
```

### Complete Migration Pipeline

```terraform
# Assess cookbook before migration
data "souschef_assessment" "web_server" {
  cookbook_path = "/chef/cookbooks/web_server"
}

# Only proceed with migration if complexity is Low or Medium
resource "souschef_migration" "web_server" {
  count = contains(["Low", "Medium"], data.souschef_assessment.web_server.complexity) ? 1 : 0

  cookbook_path = data.souschef_assessment.web_server.cookbook_path
  output_path   = "/ansible/playbooks"
  recipe_name   = "default"
}

# Migrate multiple recipes from same cookbook
resource "souschef_migration" "web_server_setup" {
  cookbook_path = "/chef/cookbooks/web_server"
  output_path   = "/ansible/playbooks"
  recipe_name   = "setup"
}

resource "souschef_migration" "web_server_deploy" {
  cookbook_path = "/chef/cookbooks/web_server"
  output_path   = "/ansible/playbooks"
  recipe_name   = "deploy"
}

# Output assessment results
output "migration_plan" {
  value = {
    cookbook        = "web_server"
    complexity      = data.souschef_assessment.web_server.complexity
    recipes         = data.souschef_assessment.web_server.recipe_count
    resources       = data.souschef_assessment.web_server.resource_count
    effort_hours    = data.souschef_assessment.web_server.estimated_hours
    recommendations = data.souschef_assessment.web_server.recommendations
  }
}
```

### Multi-Environment Migration

```terraform
locals {
  environments = {
    dev  = "/chef/cookbooks/dev"
    test = "/chef/cookbooks/test"
    prod = "/chef/cookbooks/prod"
  }
}

# Assess all environments
data "souschef_cost_estimate" "environments" {
  for_each = local.environments

  cookbook_path = each.value
}

# Migrate approved environments
resource "souschef_migration" "environments" {
  for_each = {
    for env, path in local.environments :
    env => path
    if data.souschef_cost_estimate.environments[env].complexity != "High"
  }

  cookbook_path = each.value
  output_path   = "/ansible/playbooks/${each.key}"
  recipe_name   = "default"
}

output "environment_costs" {
  value = {
    for env, cost_data in data.souschef_cost_estimate.environments :
    env => {
      total_usd  = cost_data.total_project_cost_usd
      complexity = cost_data.complexity
      migrated   = contains(keys(souschef_migration.environments), env)
    }
  }
}

## Development

### Testing

```bash
# Run unit tests
go test ./...

# Run acceptance tests (requires SousChef installed)
TF_ACC=1 go test ./... -v
```

### Contributing

See the main [SousChef CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

## License

See [LICENSE](../LICENSE).
