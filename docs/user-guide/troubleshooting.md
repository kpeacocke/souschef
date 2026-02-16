# Troubleshooting Guide

Common issues and solutions for Chef-to-Ansible migrations.

## Table of Contents

- [Migration Failures](#migration-failures)
- [Conversion Issues](#conversion-issues)
- [Validation Errors](#validation-errors)
- [Deployment Problems](#deployment-problems)
- [Performance Issues](#performance-issues)
- [Chef Server Connectivity](#chef-server-connectivity)
- [Storage and State](#storage-and-state)

## Migration Failures

### Issue: Cookbook Not Found

**Symptoms:**
```
ValueError: Cookbook path does not exist: /path/to/cookbook
```

**Solutions:**

1. **Verify path is correct:**
   ```bash
   ls -la /path/to/cookbook
   ```

2. **Check cookbook structure:**
   ```bash
   # Valid cookbooks must have metadata.rb or metadata.json
   ls /path/to/cookbook/metadata.*
   ```

3. **Use absolute paths:**
   ```python
   from pathlib import Path
   cookbook_path = Path("/opt/cookbooks/myapp").resolve()
   result = orchestrator.migrate_cookbook(str(cookbook_path))
   ```

### Issue: Migration Hangs or Times Out

**Symptoms:**
- Migration process appears frozen
- No output for extended period
- Process eventually times out

**Solutions:**

1. **Check for large files:**
   ```bash
   find /path/to/cookbook -type f -size +10M
   ```
   Large template files can slow parsing. Consider excluding or optimizing them.

2. **Increase timeout (if using MCP):**
   ```json
   {
     "command": ["souschef"],
     "args": ["--timeout", "300"]
   }
   ```

3. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   result = orchestrator.migrate_cookbook(cookbook_path)
   ```

4. **Break into smaller chunks:**
   ```python
   # Migrate recipes individually
   from souschef.server import parse_recipe, generate_playbook_from_recipe
  
   for recipe in Path(cookbook_path / "recipes").glob("*.rb"):
       playbook = generate_playbook_from_recipe(str(recipe))
       # Process each playbook
   ```

### Issue: Partial Success with Warnings

**Symptoms:**
```
Status: PARTIAL_SUCCESS
Warnings: 12 resources need manual review
```

**Solutions:**

1. **Review specific warnings:**
   ```python
   result = orchestrator.migrate_cookbook(cookbook_path)
   
   if result.status == MigrationStatus.PARTIAL_SUCCESS:
       for warning in result.warnings:
           print(f"⚠ {warning}")
   ```

2. **Identify problematic resources:**
   ```python
   # Check metrics for manual review items
   print(f"Manual review needed: {result.metrics.resources_manual_review}")
   
   # Review generated playbooks for REVIEW markers
   import re
   for playbook_path in result.playbooks_generated:
       with open(playbook_path) as f:
           content = f.read()
           review_markers = re.findall(r"# REVIEW:.*", content)
           if review_markers:
               print(f"\n{playbook_path}:")
               for marker in review_markers:
                   print(f"  {marker}")
   ```

3. **Common manual review cases:**
   - Complex Ruby guards: `only_if { complex_ruby_expression }`
   - Custom resource properties not directly mappable
   - Nested attribute references
   - Dynamic resource names

## Conversion Issues

### Issue: Guards Not Converting Properly

**Symptoms:**
```
# REVIEW: manual guard conversion needed: node['platform'] == 'ubuntu' && custom_method?
when: ansible_check_mode
```

**Solutions:**

1. **Simplify Chef guards:**
   
   Instead of:
   ```ruby
   only_if { node['platform'] == 'ubuntu' && custom_method? }
   ```
   
   Split into separate checks:
   ```ruby
   only_if { node['platform'] == 'ubuntu' }
   # Handle custom_method? separately
   ```

2. **Use standard Chef idioms:**
   ```ruby
   # Good: Standard file existence
   only_if { File.exist?('/etc/nginx/nginx.conf') }
   
   # Problematic: Custom logic
   only_if { my_helper_method && File.readable?('/etc/app.conf') }
   ```

3. **Post-process guards manually:**
   ```python
   import yaml
   
   for playbook_path in result.playbooks_generated:
       with open(playbook_path) as f:
           playbook = yaml.safe_load(f)
       
       # Find and fix guard conditions
       for play in playbook:
           for task in play.get('tasks', []):
               if 'when' in task and 'REVIEW' in str(task['when']):
                   # Manual fix logic
                   print(f"Fix needed: {task['name']}")
   ```

### Issue: Handlers Not Generated

**Symptoms:**
- Chef `notifies` present but no Ansible handlers created
- Playbook runs but services don't restart

**Solutions:**

1. **Check notification syntax:**
   ```ruby
   # Correct
   notifies :restart, 'service[nginx]', :delayed
   
   # Problematic (non-standard)
   notifies :restart, resources(:service => 'nginx')
   ```

2. **Verify handler section:**
   ```bash
   # Check if handlers section exists
   grep -A 5 "^handlers:" playbook.yml
   ```

3. **Manual handler addition:**
   ```yaml
   # Add to playbook
   handlers:
     - name: Restart nginx
       ansible.builtin.service:
         name: nginx
         state: restarted
   ```

### Issue: Template Conversion Fails

**Symptoms:**
```
Error: Failed to convert template: invalid ERB syntax
```

**Solutions:**

1. **Validate ERB templates:**
   ```bash
   # Check ERB syntax
   erb -T - -P template.erb > /dev/null
   ```

2. **Fix common ERB issues:**
   ```ruby
   # Problematic: Unclosed tags
   <%= node['attribute']
   
   # Fixed
   <%= node['attribute'] %>
   ```

3. **Skip problematic templates:**
   ```python
   # Copy as-is and mark for manual conversion
   import shutil
   from pathlib import Path
   
   templates_dir = Path(cookbook_path) / "templates"
   for template in templates_dir.rglob("*.erb"):
       try:
           # Attempt conversion
           convert_template_to_jinja2(str(template))
       except Exception as e:
           print(f"Skipping {template.name}: {e}")
           # Copy for manual review
           shutil.copy(template, f"manual-review/{template.name}")
   ```

## Validation Errors

### Issue: Playbook Fails ansible-lint

**Symptoms:**
```
[701] Role info should contain platforms
[206] Variables should have spaces before and after: {{ var }}
```

**Solutions:**

1. **Auto-fix with ansible-lint:**
   ```bash
   ansible-lint --fix playbook.yml
   ```

2. **Common fixes:**

   **Missing spaces in Jinja2:**
   ```yaml
   # Before
   path: {{app_dir}}/config
   
   # After
   path: "{{ app_dir }}/config"
   ```

   **Quote all Jinja2 expressions:**
   ```yaml
   # Before
   when: {{ condition }}
   
   # After
   when: "{{ condition }}"
   ```

3. **Configure ansible-lint exceptions:**
   ```yaml
   # .ansible-lint
   skip_list:
     - '701'  # Allow missing platforms in role
     - '106'  # Allow certain variable naming
   ```

### Issue: Syntax Errors in Generated Playbooks

**Symptoms:**
```bash
$ ansible-playbook playbook.yml --syntax-check
ERROR! Syntax Error while loading YAML.
```

**Solutions:**

1. **Validate YAML:**
   ```bash
   yamllint playbook.yml
   ```

2. **Common YAML issues:**

   **Incorrect indentation:**
   ```yaml
   # Wrong
   - name: Task
   ansible.builtin.package:
     name: nginx
   
   # Correct
   - name: Task
     ansible.builtin.package:
       name: nginx
   ```

   **Unquoted special characters:**
   ```yaml
   # Wrong
   when: status == "running: active"
   
   # Correct
   when: 'status == "running: active"'
   ```

3. **Use validation in code:**
   ```python
   from souschef.core.validation import ValidationEngine
   
   engine = ValidationEngine()
   for playbook in result.playbooks_generated:
       engine.validate_playbook_file(playbook)
       
       if engine.results:
           for error in engine.results:
               print(f"{error.level}: {error.message}")
   ```

## Deployment Problems

### Issue: Cannot Connect to Ansible Platform

**Symptoms:**
```
ConnectionError: Failed to connect to https://aap.example.com
```

**Solutions:**

1. **Verify connectivity:**
   ```bash
   curl -k https://aap.example.com/api/v2/ping
   ```

2. **Check credentials:**
   ```python
   from souschef.api_clients import AAPClient
   
   client = AAPClient(
       server_url="https://aap.example.com",
       username="admin",
       password="password",
       verify_ssl=False,  # Only for testing!
   )
   
   try:
       version = client.get_api_version()
       print(f"Connected! Version: {version}")
   except Exception as e:
       print(f"Connection failed: {e}")
   ```

3. **Update SSL certificates:**
   ```bash
   # For self-signed certificates
   export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
   ```

### Issue: Inventory Creation Fails

**Symptoms:**
```
Failed to create inventory: 400 Bad Request
```

**Solutions:**

1. **Check inventory name:**
   ```python
   # Invalid: spaces, special characters
   inv = client.create_inventory("My App Inventory")
   
   # Valid: underscores, hyphens
   inv = client.create_inventory("my-app-inventory")
   ```

2. **Verify permissions:**
   ```bash
   # Check user permissions
   curl -k -u admin:password \
     https://aap.example.com/api/v2/users/self/
   ```

3. **Use organization parameter:**
   ```python
   inv = client.create_inventory(
       name="my-inventory",
       organization=1,  # Specify organization ID
   )
   ```

### Issue: Job Template Creation Fails

**Symptoms:**
```
Failed to create job template: missing required field 'inventory'
```

**Solutions:**

1. **Ensure dependencies exist:**
   ```python
   # Create in order
   inv = client.create_inventory("my-inv")
   proj = client.create_project("my-project", scm_type="git", 
                                scm_url="https://github.com/org/repo")
   
   # Wait for project sync
   import time
   time.sleep(5)
   
   # Then create job template
   jt = client.create_job_template(
       name="my-job",
       inventory=inv['id'],
       project=proj['id'],
       playbook="site.yml",
   )
   ```

2. **Check required fields:**
   ```python
   jt = client.create_job_template(
       name="deploy-app",
       inventory=1,
       project=2,
       playbook="playbooks/deploy.yml",
       job_type="run",  # Required
   )
   ```

## Performance Issues

### Issue: Migration Takes Too Long

**Symptoms:**
- Large cookbooks (100+ recipes) take hours
- System becomes unresponsive

**Solutions:**

1. **Skip validation during migration:**
   ```python
   result = orchestrator.migrate_cookbook(
       cookbook_path,
       skip_validation=True,  # Validate separately
   )
   
   # Validate later
   from souschef.core.validation import ValidationEngine
   engine = ValidationEngine()
   for playbook in result.playbooks_generated:
       engine.validate_playbook_file(playbook)
   ```

2. **Parallelize recipe processing:**
   ```python
   from concurrent.futures import ThreadPoolExecutor
   from pathlib import Path
   
   recipes = list(Path(cookbook_path / "recipes").glob("*.rb"))
   
   def migrate_recipe(recipe_path):
       return generate_playbook_from_recipe(str(recipe_path))
   
   with ThreadPoolExecutor(max_workers=4) as executor:
       playbooks = list(executor.map(migrate_recipe, recipes))
   ```

3. **Use profiling:**
   ```python
   from souschef.profiling import profile_migration
   
   result = profile_migration(
       cookbook_path=cookbook_path,
       output_file="migration-profile.json",
   )
   
   # Review slow operations
   import json
   with open("migration-profile.json") as f:
       profile = json.load(f)
       # Analyse timing data
   ```

### Issue: High Memory Usage

**Symptoms:**
- Process uses >2GB RAM
- System swapping/OOM errors

**Solutions:**

1. **Process recipes individually:**
   ```python
   for recipe in Path(cookbook_path / "recipes").glob("*.rb"):
       playbook = generate_playbook_from_recipe(str(recipe))
       # Write immediately and free memory
       with open(f"playbooks/{recipe.stem}.yml", "w") as f:
           f.write(playbook)
       del playbook  # Explicit cleanup
   ```

2. **Disable caching:**
   ```python
   import os
   os.environ["SOUSCHEF_DISABLE_CACHE"] = "1"
   ```

3. **Limit concurrent operations:**
   ```python
   # Reduce parallelism
   with ThreadPoolExecutor(max_workers=2) as executor:
       # Process with fewer workers
       pass
   ```

## Chef Server Connectivity

### Issue: Authentication Failed

**Symptoms:**
```
401 Unauthorized: Authentication failed - check your Chef Server credentials
```

**Solutions:**

1. **Verify client key:**
   ```bash
   # Check key format
   head -n 1 /path/to/client.pem
   # Should be: -----BEGIN RSA PRIVATE KEY-----
   
   # Verify key is valid
   openssl rsa -in /path/to/client.pem -check
   ```

2. **Check client name:**
   ```python
   # Client name must match Chef Server
   client = ChefServerClient(
       server_url="https://chef.example.com",
       organization="default",
       client_name="migration-client",  # Must exist on Chef Server
       client_key=open("/etc/chef/migration.pem").read(),
   )
   ```

3. **Test connection:**
   ```python
   from souschef.core.chef_server import _validate_chef_server_connection
   
   success, message = _validate_chef_server_connection(
       server_url="https://chef.example.com",
       client_name="migration-client",
       organisation="default",
       client_key_path="/etc/chef/migration.pem",
   )
   
   if not success:
       print(f"Connection failed: {message}")
   ```

### Issue: Node Search Returns No Results

**Symptoms:**
```
nodes = chef_client.search_nodes("role:webserver")
# nodes['total'] == 0
```

**Solutions:**

1. **Verify search syntax:**
   ```python
   # Correct search queries
   nodes = chef_client.search_nodes("role:webserver")  # By role
   nodes = chef_client.search_nodes("name:app-*")     # By name pattern
   nodes = chef_client.search_nodes("recipes:apache2") # By recipe
   nodes = chef_client.search_nodes("platform:ubuntu") # By platform
   ```

2. **Check organization:**
   ```python
   # Ensure correct organization
   client = ChefServerClient(
       server_url="https://chef.example.com",
       organization="production",  # Not "default"
       client_name="migration-client",
       client_key=key_content,
   )
   ```

3. **Test with wildcard:**
   ```python
   # Get all nodes
   nodes = chef_client.search_nodes("*:*")
   print(f"Total nodes: {nodes['total']}")
   ```

## Storage and State

### Issue: Cannot Save Migration State

**Symptoms:**
```
Error: Failed to save migration state to database
```

**Solutions:**

1. **Check database connection:**
   ```python
   from souschef.storage.database import StorageManager
   
   storage = StorageManager(database_url="sqlite:///migrations.db")
   
   # Test connection
   try:
       with storage.get_session() as session:
           print("Database connected!")
   except Exception as e:
       print(f"Database error: {e}")
   ```

2. **Initialize database:**
   ```python
   # Create tables
   storage.init_db()
   ```

3. **Check permissions:**
   ```bash
   # For SQLite
   ls -la migrations.db
   chmod 664 migrations.db
   
   # For PostgreSQL
   psql -U user -d migrations -c "SELECT 1"
   ```

### Issue: Migration ID Not Found

**Symptoms:**
```
ValueError: Migration apache2-20260216-143022 not found
```

**Solutions:**

1. **List available migrations:**
   ```python
   # Query storage directly
   with storage.get_session() as session:
       results = session.query(MigrationState).all()
       for result in results:
           print(f"ID: {result.migration_id}, Status: {result.status}")
   ```

2. **Verify migration was saved:**
   ```python
   result = orchestrator.migrate_cookbook(cookbook_path)
   migration_id = orchestrator.save_state(result)
   
   # Immediately verify
   loaded = orchestrator.load_state(migration_id)
   assert loaded.migration_id == migration_id
   ```

3. **Check database file location:**
   ```bash
   # Find SQLite database
   find . -name "*.db" -type f
   
   # Use absolute path
   storage = StorageManager(
       database_url="sqlite:////absolute/path/to/migrations.db"
   )
   ```

## Getting Help

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Now run migration
result = orchestrator.migrate_cookbook(cookbook_path)
```

### Capture Detailed Error Information

```python
import traceback

try:
    result = orchestrator.migrate_cookbook(cookbook_path)
except Exception as e:
    print("="*60)
    print("DETAILED ERROR INFORMATION")
    print("="*60)
    print(f"Exception type: {type(e).__name__}")
    print(f"Exception message: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("="*60)
```

### Report Issues

When reporting issues, include:

1. **SousChef version:**
   ```bash
   souschef --version
   ```

2. **Environment:**
   - OS and version
   - Python version
   - Chef version being migrated
   - Target Ansible platform and version

3. **Minimal reproduction:**
   - Smallest cookbook that reproduces the issue
   - Exact command or code that fails
   - Full error message and traceback

4. **Migration result (if available):**
   ```python
   import json
   print(json.dumps(result.to_dict(), indent=2))
   ```

## See Also

- [Migration v2.0 API Reference](../api-reference/migration-v2.md)
- [Advanced Workflows](../migration-guide/advanced-workflows.md)
- [User Guide](../user-guide/examples.md)
