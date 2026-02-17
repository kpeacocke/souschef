# SousChef Conversion Examples

This directory contains realistic Chef cookbooks demonstrating SousChef's conversion capabilities for infrastructure, applications, and day-2 operations.

## Example Cookbooks

### 1. web-server — Complete Web Server Setup

**What it shows:**
- Package installation (`nginx`, dependencies)
- Service management (enable, start, restart)
- Template configuration (nginx.conf)
- File and directory creation with permissions
- User and group management
- Platform-specific conditional logic
- Custom resource usage

**Use cases:** Infrastructure provisioning, web application hosting

**Try it:**
```bash
# Parse the recipe
souschef-cli recipe examples/web-server/recipes/default.rb

# Convert template
souschef-cli template examples/web-server/templates/default/nginx.conf.erb

# Generate full playbook
souschef-cli cookbook examples/web-server
```

Expected output in `CONVERSION.md`.

---

### 2. database — Database Server Configuration

**What it shows:**
- Complex package dependencies (PostgreSQL, extensions)
- Service configuration and tuning
- Custom resources for database management
- Attribute-driven configuration
- Guards (`only_if`, `not_if`)
- Idempotency patterns

**Use cases:** Database provisioning, application data tier

**Try it:**
```bash
# Parse custom resource
souschef-cli resource examples/database/resources/database_user.rb

# Analyze attributes
souschef-cli attributes examples/database/attributes/default.rb

# Full conversion
souschef-cli cookbook examples/database
```

---

### 3. application — Application Deployment

**What it shows:**
- Git repository cloning and updates
- Application user and directory setup
- Environment-specific configurations
- Systemd service files
- Custom LWRPs for application lifecycle
- Deployment strategies (blue-green, rolling)

**Use cases:** Application deployment automation, CI/CD integration, day-2 operations

**Try it:**
```bash
# Parse deployment resource
souschef-cli resource examples/application/resources/app_deploy.rb

# Convert application template
souschef-cli template examples/application/templates/app.service.erb

# Full deployment playbook
souschef-cli cookbook examples/application
```

---

## Running Complete Conversions

### Single Recipe

```bash
# Convert and view Ansible tasks
souschef-cli recipe examples/web-server/recipes/default.rb

# Output includes:
# - Resource-to-task mappings
# - Handler generation
# - Variable extraction
```

### Full Cookbook

```bash
# Analyze entire cookbook
souschef-cli cookbook examples/web-server

# Generates:
# - playbook.yml (main playbook)
# - roles/ (if complex)
# - handlers/ (service notifications)
# - templates/ (Jinja2 versions)
# - vars/ (from attributes)
```

### With Validation

```bash
# Convert and validate
souschef-cli cookbook examples/web-server --validate

# Validation checks:
# - All resources converted
# - Guards properly mapped
# - File permissions preserved
# - Service dependencies correct
```

## Example Comparison: Chef vs Ansible

### Package Installation with Notification

**Chef (`web-server/recipes/default.rb`):**
```ruby
package 'nginx' do
  version '1.18.0-6ubuntu14.4'
  action :install
  notifies :restart, 'service[nginx]', :delayed
end

service 'nginx' do
  action [:enable, :start]
  supports restart: true, reload: true
end
```

**Generated Ansible:**
```yaml
- name: Install nginx
  ansible.builtin.package:
    name: nginx
    state: present
    version: '1.18.0-6ubuntu14.4'
  notify: restart nginx

- name: Ensure nginx is enabled and started
  ansible.builtin.service:
    name: nginx
    state: started
    enabled: yes

handlers:
  - name: restart nginx
    ansible.builtin.service:
      name: nginx
      state: restarted
```

### Template with Variables

**Chef (`web-server/templates/default/nginx.conf.erb`):**
```erb
worker_processes <%= node['nginx']['worker_processes'] %>;
worker_connections <%= node['nginx']['worker_connections'] %>;

server {
    listen <%= node['nginx']['port'] %>;
    server_name <%= node['nginx']['server_name'] %>;
}
```

**Generated Jinja2 (`templates/nginx.conf.j2`):**
```jinja2
worker_processes {{ nginx_worker_processes }};
worker_connections {{ nginx_worker_connections }};

server {
    listen {{ nginx_port }};
    server_name {{ nginx_server_name }};
}
```

**Variables extracted to `vars/main.yml`:**
```yaml
---
nginx_worker_processes: 4
nginx_worker_connections: 1024
nginx_port: 80
nginx_server_name: "example.com"
```

### Guards to Conditionals

**Chef:**
```ruby
execute 'migrate-database' do
  command '/usr/local/bin/db-migrate'
  only_if { File.exist?('/var/lib/app/pending-migrations') }
  not_if { File.exist?('/var/lib/app/migration-complete') }
end
```

**Generated Ansible:**
```yaml
- name: Migrate database
  ansible.builtin.command: /usr/local/bin/db-migrate
  args:
    creates: /var/lib/app/migration-complete
  when:
    - lookup('fileglob', '/var/lib/app/pending-migrations') | length > 0
```

## Testing Conversions

### Using the Web UI

```bash
# Launch interactive interface
souschef ui

# Navigate to Cookbook Analysis
# Upload example cookbook archive
# View dependency graph
# Generate conversion report
```

### Using MCP Tools (via AI Assistant)

Ask your AI assistant:

```
Parse the web-server cookbook at examples/web-server and generate
an Ansible playbook. Then validate the conversion and show me any
potential issues.
```

The assistant will use:
1. `parse_cookbook_metadata` — Extract dependencies
2. `parse_recipe` — Convert recipes to tasks
3. `parse_template` — Convert ERB to Jinja2
4. `validate_conversion` — Check accuracy

### Manual Testing

```bash
# 1. Convert cookbook
souschef-cli cookbook examples/web-server --output /tmp/ansible-output

# 2. Review generated files
ls -la /tmp/ansible-output/

# 3. Test with ansible-lint
cd /tmp/ansible-output
ansible-lint playbook.yml

# 4. Test execution (requires test environment)
ansible-playbook -i inventory playbook.yml --syntax-check
ansible-playbook -i inventory playbook.yml --check  # Dry run
```

## Day-2 Operations Examples

### Backup Playbook Example

**Chef recipe pattern:**
```ruby
cron 'database-backup' do
  minute '0'
  hour '2'
  command '/usr/local/bin/backup-database.sh'
  user 'postgres'
end
```

**Generated Ansible:**
```yaml
- name: Schedule database backup
  ansible.builtin.cron:
    name: database-backup
    minute: "0"
    hour: "2"
    job: /usr/local/bin/backup-database.sh
    user: postgres
```

### Scaling Example

**Chef pattern with attributes:**
```ruby
# attributes/default.rb
default['app']['workers'] = 4

# recipes/scale.rb
execute 'scale-workers' do
  command "scale-app --workers #{node['app']['workers']}"
end
```

**Generated Ansible:**
```yaml
# vars/main.yml
app_workers: 4

# tasks/scale.yml
- name: Scale application workers
  ansible.builtin.command: "scale-app --workers {{ app_workers }}"
```

## Contributing Examples

When adding new examples:

1. **Create complete cookbook structure:**
   ```
   examples/your-example/
   ├── metadata.rb
   ├── recipes/
   │   └── default.rb
   ├── templates/
   │   └── default/
   ├── attributes/
   │   └── default.rb
   ├── resources/ (if applicable)
   └── CONVERSION.md (expected output)
   ```

2. **Include `CONVERSION.md`:**
   - Expected Ansible playbook output
   - Variable mappings
   - Handler definitions
   - Notes on complex conversions

3. **Add comments explaining Chef concepts:**
   ```ruby
   # Chef searches for nodes with role 'web'
   # SousChef converts this to Ansible dynamic inventory
   search(:node, 'role:web').each do |node|
     # ...
   end
   ```

4. **Test all files:**
   ```bash
   # Verify all examples convert successfully
   for dir in examples/*/; do
       souschef-cli cookbook "$dir" || echo "Failed: $dir"
   done
   ```

5. **Update this README** with new example description

## Getting Help

- **Conversion issues:** [GitHub Issues](https://github.com/kpeacocke/souschef/issues)
- **Questions:** [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- **Documentation:** [User Guide](../docs/user-guide/mcp-tools.md)

## Additional Examples Needed

We welcome contributions for:

- Multi-cookbook dependencies
- Chef Server integration examples
- Data bags and secrets management
- Habitat to Docker conversions
- InSpec test conversions
- AWX job template generation
- Complex enterprise patterns (15+ cookbooks, multiple environments)
