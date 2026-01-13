# Terraform Provider for SousChef

This Terraform provider enables infrastructure-as-code management of Chef to Ansible migrations using SousChef.

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

## Example Usage

Complete example managing multiple cookbook migrations:

```terraform
terraform {
  required_providers {
    souschef = {
      source = "kpeacocke/souschef"
    }
  }
}

provider "souschef" {}

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
    cookbook      = "web_server"
    complexity    = data.souschef_assessment.web_server.complexity
    recipes       = data.souschef_assessment.web_server.recipe_count
    resources     = data.souschef_assessment.web_server.resource_count
    effort_hours  = data.souschef_assessment.web_server.estimated_hours
    recommendations = data.souschef_assessment.web_server.recommendations
  }
}
```

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
