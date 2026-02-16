# Advanced Migration Workflows

This guide covers advanced patterns and workflows for complex Chef-to-Ansible migrations.

## Table of Contents

- [Multi-Cookbook Migration](#multi-cookbook-migration)
- [Chef Server Integration](#chef-server-integration)
- [Complex Dependency Handling](#complex-dependency-handling)
- [Incremental Migration Strategy](#incremental-migration-strategy)
- [CI/CD Integration](#cicd-integration)
- [Custom Resource Handling](#custom-resource-handling)
- [Advanced Guard Patterns](#advanced-guard-patterns)
- [Handler Chains](#handler-chains)

## Multi-Cookbook Migration

### Scenario: Migrate an Entire Chef Repository

When migrating multiple related cookbooks, maintain dependency order and shared state.

**Directory Structure:**
```
chef-repo/
├── cookbooks/
│   ├── base/          # Foundation cookbook
│   ├── webserver/     # Depends on base
│   ├── database/      # Depends on base
│   └── application/   # Depends on webserver + database
```

**Migration Script:**

```python
from pathlib import Path
from souschef.migration_v2 import MigrationOrchestrator, MigrationStatus
from souschef.storage.database import StorageManager

# Setup
storage = StorageManager(database_url="sqlite:///chef-repo-migration.db")
orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
    storage_manager=storage,
)

# Define migration order (dependency-first)
cookbooks = [
    "base",
    "database",
    "webserver",
    "application",
]

# Track results
migration_map = {}
failed_cookbooks = []

for cookbook_name in cookbooks:
    cookbook_path = f"/opt/chef-repo/cookbooks/{cookbook_name}"
    print(f"\n{'='*60}")
    print(f"Migrating: {cookbook_name}")
    print(f"{'='*60}")

    try:
        result = orchestrator.migrate_cookbook(
            cookbook_path,
            skip_validation=False,
        )

        # Save state
        migration_id = orchestrator.save_state(result)
        migration_map[cookbook_name] = {
            "migration_id": migration_id,
            "status": result.status,
            "playbooks": result.playbooks_generated,
            "metrics": result.metrics,
        }

        # Report
        if result.status == MigrationStatus.SUCCESS:
            print(f"✓ {cookbook_name}: SUCCESS")
            print(f"  - Recipes: {result.metrics.recipes_converted}/{result.metrics.recipes_total}")
            print(f"  - Tasks: {result.metrics.tasks_generated}")
        elif result.status == MigrationStatus.PARTIAL_SUCCESS:
            print(f"⚠ {cookbook_name}: PARTIAL SUCCESS")
            print(f"  - Warnings: {len(result.warnings)}")
            for warning in result.warnings[:3]:  # Show first 3
                print(f"    • {warning}")
        else:
            print(f"✗ {cookbook_name}: FAILED")
            failed_cookbooks.append(cookbook_name)
            for error in result.errors[:3]:
                print(f"    • {error}")

    except Exception as e:
        print(f"✗ {cookbook_name}: EXCEPTION - {e}")
        failed_cookbooks.append(cookbook_name)

# Summary
print(f"\n{'='*60}")
print("MIGRATION SUMMARY")
print(f"{'='*60}")
print(f"Total: {len(cookbooks)} cookbooks")
print(f"Successful: {len([c for c, m in migration_map.items() if m['status'] == MigrationStatus.SUCCESS])}")
print(f"Partial: {len([c for c, m in migration_map.items() if m['status'] == MigrationStatus.PARTIAL_SUCCESS])}")
print(f"Failed: {len(failed_cookbooks)}")

if failed_cookbooks:
    print(f"\nFailed cookbooks: {', '.join(failed_cookbooks)}")
    print("Review errors and retry individually.")

# Generate migration report
with open("migration-report.txt", "w") as f:
    f.write("Chef Repository Migration Report\n")
    f.write("="*60 + "\n\n")
    for cookbook, data in migration_map.items():
        f.write(f"\n{cookbook}:\n")
        f.write(f"  Status: {data['status'].name}\n")
        f.write(f"  Migration ID: {data['migration_id']}\n")
        f.write(f"  Playbooks: {len(data['playbooks'])}\n")
        metrics = data['metrics']
        f.write(f"  Metrics:\n")
        f.write(f"    - Recipes: {metrics.recipes_converted}/{metrics.recipes_total}\n")
        f.write(f"    - Resources: {metrics.resources_converted}/{metrics.resources_total}\n")
        f.write(f"    - Tasks: {metrics.tasks_generated}\n")
```

## Chef Server Integration

### Scenario: Query Chef Server for Node Information

Use Chef Server data to inform migration decisions.

```python
from souschef.api_clients import ChefServerClient
from souschef.migration_v2 import MigrationOrchestrator

# Connect to Chef Server
chef_client = ChefServerClient(
    server_url="https://chef.example.com",
    organization="production",
    client_name="migration-bot",
    client_key=open("/etc/chef/migration.pem").read(),
)

# Query nodes using a specific cookbook
print("Querying Chef Server for apache2 cookbook usage...")
nodes = chef_client.search_nodes(query="recipes:apache2*")

print(f"Found {nodes['total']} nodes using apache2 cookbook")

# Analyse node platforms
platforms = {}
for node_data in nodes['rows']:
    platform = node_data.get('platform', 'unknown')
    platforms[platform] = platforms.get(platform, 0) + 1

print("\nPlatform distribution:")
for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True):
    print(f"  {platform}: {count} nodes")

# Determine optimal target platform based on node count
if nodes['total'] > 100:
    target_platform = "aap"  # Large scale → AAP
    target_version = "2.4.0"
elif nodes['total'] > 20:
    target_platform = "awx"  # Medium scale → AWX
    target_version = "24.6.1"
else:
    target_platform = "tower"  # Small scale → Tower
    target_version = "3.8.5"

print(f"\nRecommended target: {target_platform} {target_version}")

# Migrate with appropriate target
orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform=target_platform,
    target_version=target_version,
    chef_server_url="https://chef.example.com",
    chef_organization="production",
    chef_client_name="migration-bot",
    chef_client_key=open("/etc/chef/migration.pem").read(),
)

result = orchestrator.migrate_cookbook("/opt/cookbooks/apache2")
print(f"\nMigration completed: {result.status}")
```

## Complex Dependency Handling

### Scenario: Cookbooks with External Dependencies

Handle cookbooks that depend on external resources or data bags.

```python
from souschef.migration_v2 import MigrationOrchestrator
from souschef.api_clients import ChefServerClient
import json

# Setup
chef_client = ChefServerClient(
    server_url="https://chef.example.com",
    organization="default",
    client_name="admin",
    client_key=open("/etc/chef/admin.pem").read(),
)

orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
)

# 1. Extract data bags referenced by cookbook
cookbook_path = "/opt/cookbooks/application"
print("Analysing cookbook dependencies...")

# Read recipe files to find data_bag() calls
import re
from pathlib import Path

data_bags_used = set()
for recipe_file in Path(cookbook_path).rglob("*.rb"):
    content = recipe_file.read_text()
    # Find data_bag() and data_bag_item() calls
    bags = re.findall(r"data_bag(?:_item)?\(['\"]([^'\"]+)['\"]", content)
    data_bags_used.update(bags)

print(f"Found data bags: {', '.join(data_bags_used)}")

# 2. Export data bags to Ansible variables
ansible_vars = {}
for bag_name in data_bags_used:
    print(f"Exporting data bag: {bag_name}")
    # In real scenario, query Chef Server for data bag contents
    # For now, create placeholder structure
    ansible_vars[f"{bag_name}_data"] = {
        "source": "chef_data_bag",
        "bag_name": bag_name,
        "items": [],  # Populate from Chef Server
    }

# Save as Ansible group_vars
output_dir = Path("/opt/ansible/group_vars")
output_dir.mkdir(parents=True, exist_ok=True)
with open(output_dir / "all.yml", "w") as f:
    f.write("# Migrated from Chef data bags\n")
    f.write("---\n")
    import yaml
    yaml.dump(ansible_vars, f, default_flow_style=False)

print(f"Exported data bags to {output_dir / 'all.yml'}")

# 3. Migrate cookbook
result = orchestrator.migrate_cookbook(cookbook_path)

# 4. Post-process playbooks to reference exported variables
for playbook_path in result.playbooks_generated:
    print(f"Post-processing: {playbook_path}")
    # Add reference to group_vars
    with open(playbook_path, "r") as f:
        content = f.read()

    # Add note about data bags
    note = (
        "\n# NOTE: This playbook references data from Chef data bags.\n"
        f"# See group_vars/all.yml for migrated data structures.\n"
    )

    with open(playbook_path, "w") as f:
        f.write(note + content)

print("Migration with dependency handling complete!")
```

## Incremental Migration Strategy

### Scenario: Gradual Migration with Coexistence

Migrate cookbooks incrementally while maintaining both Chef and Ansible infrastructure.

```python
from souschef.migration_v2 import MigrationOrchestrator, MigrationStatus
from datetime import datetime
import json

class IncrementalMigrationManager:
    """Manage incremental cookbook migrations."""

    def __init__(self, state_file="migration-state.json"):
        self.state_file = state_file
        self.state = self._load_state()
        self.orchestrator = MigrationOrchestrator(
            chef_version="15.10.91",
            target_platform="aap",
            target_version="2.4.0",
        )

    def _load_state(self):
        """Load migration state from file."""
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "migrated": {},
                "in_progress": {},
                "pending": [],
                "failed": {},
            }

    def _save_state(self):
        """Save migration state to file."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def register_cookbook(self, name, path, dependencies=None):
        """Register a cookbook for migration."""
        if name not in self.state["migrated"] and name not in self.state["pending"]:
            self.state["pending"].append({
                "name": name,
                "path": path,
                "dependencies": dependencies or [],
                "registered_at": datetime.utcnow().isoformat(),
            })
            self._save_state()
            print(f"Registered {name} for migration")

    def migrate_next(self):
        """Migrate the next cookbook in queue."""
        if not self.state["pending"]:
            print("No pending cookbooks")
            return None

        # Find cookbook with satisfied dependencies
        for i, cookbook in enumerate(self.state["pending"]):
            deps_satisfied = all(
                dep in self.state["migrated"]
                for dep in cookbook["dependencies"]
            )

            if deps_satisfied:
                # Remove from pending
                cookbook = self.state["pending"].pop(i)
                name = cookbook["name"]
                path = cookbook["path"]

                print(f"\nMigrating: {name}")
                print(f"Path: {path}")

                # Mark as in progress
                self.state["in_progress"][name] = {
                    **cookbook,
                    "started_at": datetime.utcnow().isoformat(),
                }
                self._save_state()

                try:
                    # Perform migration
                    result = self.orchestrator.migrate_cookbook(path)
                    migration_id = self.orchestrator.save_state(result)

                    # Update state based on result
                    if result.status in [MigrationStatus.SUCCESS, MigrationStatus.PARTIAL_SUCCESS]:
                        del self.state["in_progress"][name]
                        self.state["migrated"][name] = {
                            **cookbook,
                            "migration_id": migration_id,
                            "status": result.status.name,
                            "completed_at": datetime.utcnow().isoformat(),
                            "playbooks": result.playbooks_generated,
                        }
                        print(f"✓ Completed: {name}")
                    else:
                        del self.state["in_progress"][name]
                        self.state["failed"][name] = {
                            **cookbook,
                            "errors": result.errors,
                            "failed_at": datetime.utcnow().isoformat(),
                        }
                        print(f"✗ Failed: {name}")

                    self._save_state()
                    return result

                except Exception as e:
                    del self.state["in_progress"][name]
                    self.state["failed"][name] = {
                        **cookbook,
                        "errors": [str(e)],
                        "failed_at": datetime.utcnow().isoformat(),
                    }
                    self._save_state()
                    print(f"✗ Exception: {name} - {e}")
                    return None

        print("Remaining cookbooks have unsatisfied dependencies")
        return None

    def status(self):
        """Print migration status."""
        print("\n" + "="*60)
        print("INCREMENTAL MIGRATION STATUS")
        print("="*60)
        print(f"Migrated: {len(self.state['migrated'])}")
        print(f"In Progress: {len(self.state['in_progress'])}")
        print(f"Pending: {len(self.state['pending'])}")
        print(f"Failed: {len(self.state['failed'])}")

        if self.state["migrated"]:
            print("\n✓ Completed Cookbooks:")
            for name, data in self.state["migrated"].items():
                print(f"  - {name} ({data['status']})")

        if self.state["failed"]:
            print("\n✗ Failed Cookbooks:")
            for name, data in self.state["failed"].items():
                print(f"  - {name}")
                for error in data["errors"][:2]:
                    print(f"      {error}")

# Usage
manager = IncrementalMigrationManager()

# Register cookbooks with dependencies
manager.register_cookbook("base", "/opt/cookbooks/base")
manager.register_cookbook("webserver", "/opt/cookbooks/webserver", dependencies=["base"])
manager.register_cookbook("database", "/opt/cookbooks/database", dependencies=["base"])
manager.register_cookbook("app", "/opt/cookbooks/app", dependencies=["webserver", "database"])

# Migrate one at a time
while manager.state["pending"]:
    result = manager.migrate_next()
    if result is None:
        break

    # Review and approve before continuing
    input("\nPress Enter to migrate next cookbook (or Ctrl+C to stop)...")

manager.status()
```

## CI/CD Integration

### Scenario: Automated Migration Pipeline

Integrate cookbook migration into your CI/CD pipeline.

**GitLab CI Example (`.gitlab-ci.yml`):**

```yaml
stages:
  - validate
  - migrate
  - test
  - deploy

variables:
  CHEF_VERSION: "15.10.91"
  TARGET_PLATFORM: "aap"
  TARGET_VERSION: "2.4.0"

validate_cookbook:
  stage: validate
  script:
    - souschef validate-cookbook $CI_PROJECT_DIR
    - souschef assess-cookbook-migration $CI_PROJECT_DIR
  artifacts:
    reports:
      junit: assessment-report.xml
    paths:
      - assessment-report.json

migrate_cookbook:
  stage: migrate
  script:
    - |
      souschef v2 migrate $CI_PROJECT_DIR \
        --chef-version $CHEF_VERSION \
        --target-platform $TARGET_PLATFORM \
        --target-version $TARGET_VERSION \
        --skip-validation \
        --save-state > migration-result.json
    - migration_id=$(jq -r '.migration_id' migration-result.json)
    - echo "MIGRATION_ID=$migration_id" >> migrate.env
  artifacts:
    paths:
      - playbooks/
      - migration-result.json
    reports:
      dotenv: migrate.env

test_playbooks:
  stage: test
  script:
    - ansible-lint playbooks/*.yml
    - ansible-playbook --syntax-check playbooks/*.yml
    - |
      # Run molecule tests if available
      if [ -d "molecule" ]; then
        molecule test
      fi
  dependencies:
    - migrate_cookbook

deploy_to_aap:
  stage: deploy
  when: manual
  script:
    - |
      souschef deploy-migration-to-ansible-v2 \
        --migration-id $MIGRATION_ID \
        --ansible-server-url $AAP_URL \
        --ansible-username $AAP_USERNAME \
        --ansible-password $AAP_PASSWORD \
        --target-platform $TARGET_PLATFORM \
        --target-version $TARGET_VERSION
  dependencies:
    - migrate_cookbook
  environment:
    name: production
    url: https://aap.example.com
```

**GitHub Actions Example (`.github/workflows/migrate.yml`):**

```yaml
name: Cookbook Migration

on:
  push:
    paths:
      - 'cookbooks/**'
  workflow_dispatch:

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install SousChef
        run: |
          pip install souschef

      - name: Migrate Cookbook
        env:
          CHEF_SERVER_URL: ${{ secrets.CHEF_SERVER_URL }}
          CHEF_CLIENT_KEY: ${{ secrets.CHEF_CLIENT_KEY }}
        run: |
          souschef v2 migrate cookbooks/myapp \
            --chef-version 15.10.91 \
            --target-platform aap \
            --target-version 2.4.0 \
            --save-state

      - name: Upload Playbooks
        uses: actions/upload-artifact@v3
        with:
          name: ansible-playbooks
          path: playbooks/

      - name: Ansible Lint
        run: |
          pip install ansible-lint
          ansible-lint playbooks/*.yml

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          commit-message: "Migrate cookbook to Ansible"
          title: "Auto-migration: cookbooks/myapp"
          body: |
            Automated cookbook migration completed.

            Review generated playbooks before merging.
          branch: auto-migrate-${{ github.run_number }}
```

## Custom Resource Handling

### Scenario: Migrate Custom Resources

Handle cookbooks with custom Chef resources.

```python
from souschef.migration_v2 import MigrationOrchestrator
from souschef.parsers.resource import parse_custom_resource
from pathlib import Path

cookbook_path = Path("/opt/cookbooks/myapp")

# 1. Identify custom resources
custom_resources_dir = cookbook_path / "resources"
if custom_resources_dir.exists():
    print("Custom resources found:")
    for resource_file in custom_resources_dir.glob("*.rb"):
        print(f"  - {resource_file.stem}")

        # Parse custom resource
        try:
            resource_def = parse_custom_resource(str(resource_file))
            print(f"    Properties: {', '.join(resource_def.get('properties', {}).keys())}")
            print(f"    Actions: {', '.join(resource_def.get('actions', []))}")
        except Exception as e:
            print(f"    Error parsing: {e}")

# 2. Migrate cookbook
orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
)

result = orchestrator.migrate_cookbook(str(cookbook_path))

# 3. Review custom resource conversions
if result.metrics.custom_resources_converted > 0:
    print(f"\n✓ Converted {result.metrics.custom_resources_converted} custom resources")
    print("Review generated tasks for correctness")

# 4. Check for manual review items
if result.metrics.resources_manual_review > 0:
    print(f"\n⚠ {result.metrics.resources_manual_review} resources need manual review")
    print("These may include complex custom resource logic")

    # Export list of tasks needing review
    for playbook_path in result.playbooks_generated:
        with open(playbook_path, "r") as f:
            content = f.read()
            if "# MANUAL REVIEW" in content or "# REVIEW:" in content:
                print(f"\nReview needed in: {playbook_path}")
                # Extract lines with REVIEW markers
                for i, line in enumerate(content.split("\n"), 1):
                    if "REVIEW" in line:
                        print(f"  Line {i}: {line.strip()}")
```

## Advanced Guard Patterns

(Content continues with guard patterns, handler chains, etc.)

## See Also

- [Migration v2.0 API Reference](../api-reference/migration-v2.md)
- [Deployment Strategies](deployment.md)
- [Troubleshooting Guide](../user-guide/troubleshooting.md)
