# Migration v2.0 API Reference

The v2.0 Migration Orchestrator provides a high-level API for end-to-end Chef-to-Ansible migrations with persistent state tracking, real API integration, and comprehensive metrics.

## MigrationOrchestrator

The main orchestration class for cookbook migrations.

### Constructor

```python
from souschef.migration_v2 import MigrationOrchestrator

orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",  # or "awx", "tower"
    target_version="2.4.0",
    chef_server_url="https://chef.example.com",
    chef_organization="default",
    chef_client_name="migration-client",
    chef_client_key="/path/to/client.pem",
    ansible_server_url="https://aap.example.com",
    ansible_username="admin",
    ansible_password="password",
    storage_manager=None,  # Optional: custom storage backend
)
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chef_version` | `str` | Yes | Chef version (e.g., "15.10.91") |
| `target_platform` | `str` | Yes | Target platform: "aap", "awx", or "tower" |
| `target_version` | `str` | Yes | Platform version (e.g., "2.4.0") |
| `chef_server_url` | `str` | No | Chef Server URL for API queries |
| `chef_organization` | `str` | No | Chef organization name (default: "default") |
| `chef_client_name` | `str` | No | Chef client name for authentication |
| `chef_client_key` | `str` | No | Chef client private key (PEM format) |
| `ansible_server_url` | `str` | No | Ansible platform URL |
| `ansible_username` | `str` | No | Ansible platform username |
| `ansible_password` | `str` | No | Ansible platform password |
| `storage_manager` | `StorageManager` | No | Custom storage backend |

### Methods

#### migrate_cookbook

Perform complete cookbook migration with all phases.

```python
result = orchestrator.migrate_cookbook(
    cookbook_path="/path/to/cookbook",
    skip_validation=False,
    deploy=False,
)
```

**Parameters:**
- `cookbook_path` (str): Path to Chef cookbook directory
- `skip_validation` (bool): Skip playbook validation (default: False)
- `deploy` (bool): Deploy to target platform (default: False)

**Returns:** `MigrationResult` object containing:
- `migration_id`: Unique migration identifier
- `status`: Migration status (success/partial/failed)
- `metrics`: Conversion metrics
- `playbooks_generated`: List of generated playbook paths
- `validation_results`: Validation results (if not skipped)
- `deployment_status`: Deployment status (if deployed)
- `warnings`: List of warnings
- `errors`: List of errors
- `start_time`: Migration start timestamp
- `end_time`: Migration end timestamp
- `duration_seconds`: Total duration

**Example:**
```python
result = orchestrator.migrate_cookbook(
    "/opt/cookbooks/apache2",
    skip_validation=False,
    deploy=True,
)

if result.status == MigrationStatus.SUCCESS:
    print(f"Migration {result.migration_id} completed!")
    print(f"Generated {len(result.playbooks_generated)} playbooks")
    print(f"Duration: {result.duration_seconds:.2f}s")
else:
    print(f"Migration failed: {result.errors}")
```

#### save_state

Save migration state to persistent storage.

```python
migration_id = orchestrator.save_state(result)
```

**Parameters:**
- `result` (MigrationResult): Migration result to save

**Returns:** `str` - Migration ID for retrieval

**Example:**
```python
result = orchestrator.migrate_cookbook("/opt/cookbooks/nginx")
migration_id = orchestrator.save_state(result)
print(f"Saved migration state: {migration_id}")
```

#### load_state

Load migration state from persistent storage.

```python
result = orchestrator.load_state(migration_id)
```

**Parameters:**
- `migration_id` (str): Migration ID to load

**Returns:** `MigrationResult` object

**Raises:** `ValueError` if migration ID not found

**Example:**
```python
# Load previous migration
result = orchestrator.load_state("apache2-20260216-143022")
print(f"Loaded migration: {result.status}")
print(f"Playbooks: {result.playbooks_generated}")
```

## Data Models

### MigrationResult

Result of a migration operation.

**Attributes:**
- `migration_id` (str): Unique identifier
- `status` (MigrationStatus): SUCCESS, PARTIAL_SUCCESS, or FAILED
- `metrics` (ConversionMetrics): Detailed conversion metrics
- `playbooks_generated` (list[str]): Generated playbook paths
- `validation_results` (dict): Validation results
- `deployment_status` (dict): Deployment status
- `warnings` (list[str]): Non-fatal warnings
- `errors` (list[str]): Fatal errors
- `start_time` (str): ISO-8601 timestamp
- `end_time` (str): ISO-8601 timestamp
- `duration_seconds` (float): Total duration

**Methods:**
- `to_dict()`: Serialize to dictionary
- `from_dict(data)`: Deserialize from dictionary

### ConversionMetrics

Detailed conversion metrics.

**Attributes:**
- `recipes_total` (int): Total recipes processed
- `recipes_converted` (int): Successfully converted recipes
- `recipes_failed` (int): Failed recipes
- `resources_total` (int): Total resources processed
- `resources_converted` (int): Successfully converted resources
- `resources_manual_review` (int): Resources needing review
- `tasks_generated` (int): Total Ansible tasks generated
- `handlers_generated` (int): Total handlers generated
- `handlers_skipped` (int): Handlers skipped (not applicable)
- `guards_converted` (int): Guard conditions converted
- `attributes_converted` (int): Attributes converted
- `attributes_skipped` (int): Attributes skipped (unsupported)
- `templates_converted` (int): Templates converted (ERB→Jinja2)
- `files_copied` (int): Static files copied
- `custom_resources_converted` (int): Custom resources converted

**Methods:**
- `to_dict()`: Serialize to dictionary
- `from_dict(data)`: Deserialize from dictionary

### MigrationStatus

Enumeration of migration statuses.

**Values:**
- `SUCCESS`: Migration completed without errors
- `PARTIAL_SUCCESS`: Migration completed with warnings
- `FAILED`: Migration failed with errors

## CLI Commands

### v2 migrate

Migrate a cookbook using v2.0 orchestrator.

```bash
souschef v2 migrate /path/to/cookbook \
    --chef-version 15.10.91 \
    --target-platform aap \
    --target-version 2.4.0 \
    --save-state \
    --deploy
```

**Options:**
- `--chef-version`: Chef version (required)
- `--target-platform`: Target platform: aap, awx, tower (required)
- `--target-version`: Platform version (required)
- `--chef-server-url`: Chef Server URL
- `--chef-organization`: Chef organization
- `--chef-client-name`: Chef client name
- `--chef-client-key`: Path to client key
- `--ansible-server-url`: Ansible platform URL
- `--ansible-username`: Ansible username
- `--ansible-password`: Ansible password
- `--skip-validation`: Skip playbook validation
- `--deploy`: Deploy to target platform
- `--save-state`: Save migration state

### v2 status

View saved migration state.

```bash
souschef v2 status <migration-id>
```

**Example:**
```bash
# View migration details
souschef v2 status apache2-20260216-143022
```

## MCP Tools

### migrate_cookbook_v2

Migrate a cookbook using v2.0 orchestrator via MCP protocol.

**Parameters:**
- `cookbook_path` (str): Path to cookbook
- `chef_version` (str): Chef version
- `target_platform` (str): Target platform
- `target_version` (str): Platform version
- `chef_server_url` (str, optional): Chef Server URL
- `skip_validation` (bool): Skip validation
- `deploy` (bool): Deploy to platform
- `save_state` (bool): Save state to storage

**Returns:** JSON with migration result

**Example:**
```json
{
  "tool": "migrate_cookbook_v2",
  "arguments": {
    "cookbook_path": "/opt/cookbooks/apache2",
    "chef_version": "15.10.91",
    "target_platform": "aap",
    "target_version": "2.4.0",
    "skip_validation": false,
    "deploy": true,
    "save_state": true
  }
}
```

### get_migration_status_v2

Retrieve saved migration state.

**Parameters:**
- `migration_id` (str): Migration ID to retrieve

**Returns:** JSON with migration result

**Example:**
```json
{
  "tool": "get_migration_status_v2",
  "arguments": {
    "migration_id": "apache2-20260216-143022"
  }
}
```

### deploy_migration_to_ansible_v2

Deploy a migrated cookbook to Ansible platform.

**Parameters:**
- `migration_id` (str): Migration ID to deploy
- `ansible_server_url` (str): Ansible platform URL
- `ansible_username` (str): Username
- `ansible_password` (str): Password
- `target_platform` (str): Platform type
- `target_version` (str): Platform version

**Returns:** JSON with deployment status

## Integration Examples

### Basic Migration

```python
from souschef.migration_v2 import MigrationOrchestrator

# Create orchestrator
orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
)

# Migrate cookbook
result = orchestrator.migrate_cookbook("/opt/cookbooks/apache2")

# Check results
print(f"Status: {result.status}")
print(f"Recipes converted: {result.metrics.recipes_converted}")
print(f"Tasks generated: {result.metrics.tasks_generated}")
```

### Migration with Chef Server

```python
orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
    chef_server_url="https://chef.example.com",
    chef_organization="production",
    chef_client_name="migration-bot",
    chef_client_key=open("/etc/chef/migration.pem").read(),
)

result = orchestrator.migrate_cookbook("/opt/cookbooks/webapp")
```

### Migration with Deployment

```python
orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
    ansible_server_url="https://aap.example.com",
    ansible_username="admin",
    ansible_password="password",
)

# Migrate and deploy
result = orchestrator.migrate_cookbook(
    "/opt/cookbooks/database",
    deploy=True,
)

if result.deployment_status:
    print(f"Deployed: {result.deployment_status['success']}")
```

### Migration with State Persistence

```python
from souschef.storage.database import StorageManager

# Create storage manager
storage = StorageManager(database_url="sqlite:///migrations.db")

orchestrator = MigrationOrchestrator(
    chef_version="15.10.91",
    target_platform="aap",
    target_version="2.4.0",
    storage_manager=storage,
)

# Migrate with state saving
result = orchestrator.migrate_cookbook("/opt/cookbooks/nginx")
migration_id = orchestrator.save_state(result)

# Later: retrieve state
loaded_result = orchestrator.load_state(migration_id)
print(f"Loaded migration from {loaded_result.start_time}")
```

## Error Handling

### Common Errors

**ValueError: Invalid cookbook path**
```python
try:
    result = orchestrator.migrate_cookbook("/nonexistent/path")
except ValueError as e:
    print(f"Invalid cookbook: {e}")
```

**RuntimeError: API connection failed**
```python
result = orchestrator.migrate_cookbook("/opt/cookbooks/app", deploy=True)
if result.status == MigrationStatus.FAILED:
    for error in result.errors:
        if "connection" in error.lower():
            print("Check network connectivity to Ansible platform")
```

**ValidationError: Invalid playbook**
```python
result = orchestrator.migrate_cookbook("/opt/cookbooks/app")
if result.validation_results.get("errors"):
    print("Validation errors found:")
    for error in result.validation_results["errors"]:
        print(f"  - {error}")
```

## Best Practices

### 1. Always Save State

```python
result = orchestrator.migrate_cookbook(cookbook_path)
migration_id = orchestrator.save_state(result)
# Store migration_id for later reference
```

### 2. Validate Before Deploying

```python
# First: migrate and validate
result = orchestrator.migrate_cookbook(
    cookbook_path,
    skip_validation=False,
    deploy=False,
)

# Check validation
if not result.validation_results.get("errors"):
    # Then: deploy separately
    # ... deployment logic
```

### 3. Handle Partial Success

```python
result = orchestrator.migrate_cookbook(cookbook_path)

if result.status == MigrationStatus.PARTIAL_SUCCESS:
    print("Migration completed with warnings:")
    for warning in result.warnings:
        print(f"  - {warning}")

    # Review resources needing manual attention
    if result.metrics.resources_manual_review > 0:
        print(f"{result.metrics.resources_manual_review} resources need manual review")
```

### 4. Use Appropriate Storage

```python
# Development: SQLite
storage = StorageManager(database_url="sqlite:///migrations.db")

# Production: PostgreSQL
storage = StorageManager(
    database_url="postgresql://user:pass@localhost/migrations"
)

orchestrator = MigrationOrchestrator(..., storage_manager=storage)
```

## Performance Considerations

### Large Cookbooks

For large cookbooks (>50 recipes), consider:

```python
# Skip validation during initial migration
result = orchestrator.migrate_cookbook(
    cookbook_path,
    skip_validation=True,
)

# Validate later with dedicated tool
from souschef.core.validation import ValidationEngine
engine = ValidationEngine()
for playbook in result.playbooks_generated:
    engine.validate_playbook_file(playbook)
```

### Batch Migrations

```python
cookbooks = ["/opt/cookbooks/app1", "/opt/cookbooks/app2", "/opt/cookbooks/app3"]
results = []

for cookbook in cookbooks:
    result = orchestrator.migrate_cookbook(cookbook)
    migration_id = orchestrator.save_state(result)
    results.append((cookbook, migration_id, result.status))

# Summary
successful = sum(1 for _, _, status in results if status == MigrationStatus.SUCCESS)
print(f"Migrated {successful}/{len(cookbooks)} cookbooks successfully")
```

## See Also

- [Migration Guide Overview](../migration-guide/overview.md)
- [Deployment Strategies](../migration-guide/deployment.md)
- [Data Persistence](../user-guide/data-persistence.md)
- [CLI Usage](../user-guide/cli-usage.md)
