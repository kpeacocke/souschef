# Quick Start Guide

Get up and running with SousChef in minutes. This guide walks you through your first Chef-to-Ansible migration.

## Prerequisites

Before you begin, make sure you have:

- [x] SousChef installed ([Installation guide](installation.md))
- [x] MCP client configured (Claude Desktop, VS Code, etc.)
- [x] A Chef cookbook to migrate

## Your First Migration

### Step 1: Analyze a Cookbook

Start by analyzing a Chef cookbook to understand its structure:

=== "Using MCP (AI Assistant)"

    Ask your AI assistant:
    ```
    Can you analyze the cookbook at /path/to/cookbook?
    ```

=== "Using CLI"

    ```bash
    souschef-cli cookbook /path/to/cookbook
    ```

The analysis will show:
- Cookbook structure and files
- Recipe resources and actions
- Attributes and their precedence
- Template variables
- Dependencies

### Step 2: Convert a Recipe to a Playbook

Convert your first Chef recipe to an Ansible playbook:

=== "Using MCP (AI Assistant)"

    ```
    Convert the recipe /path/to/cookbook/recipes/default.rb to an Ansible playbook
    ```

=== "Using CLI"

    ```bash
    souschef-cli recipe /path/to/cookbook/recipes/default.rb > playbook.yml
    ```

Example conversion:

**Chef Recipe** (`recipes/webserver.rb`):
```ruby
package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end

template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  variables({
    worker_processes: node['nginx']['workers']
  })
  notifies :reload, 'service[nginx]'
end
```

**Generated Ansible Playbook**:
```yaml
---
- name: Webserver cookbook playbook
  hosts: all
  become: yes

  tasks:
    - name: Install nginx
      ansible.builtin.package:
        name: nginx
        state: present

    - name: Enable and start nginx
      ansible.builtin.service:
        name: nginx
        enabled: yes
        state: started

    - name: Configure nginx
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      vars:
        worker_processes: "{{ nginx_workers }}"
      notify: Reload nginx

  handlers:
    - name: Reload nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
```

### Step 3: Validate the Conversion

Validate that the conversion is correct and follows best practices:

=== "Using MCP (AI Assistant)"

    ```
    Validate the playbook conversion for accuracy and best practices
    ```

=== "Using CLI"

    ```bash
    souschef-cli validate playbook.yml
    ```

The validation checks:
- ✅ Syntax correctness
- ✅ Semantic equivalence
- ✅ Best practices compliance
- ✅ Security considerations
- ✅ Performance optimizations

### Step 4: Test the Playbook

Before deploying, test your converted playbook:

```bash
# Syntax check
ansible-playbook playbook.yml --syntax-check

# Dry run
ansible-playbook playbook.yml --check

# Run on test environment
ansible-playbook playbook.yml -i test_inventory
```

## Common Migration Patterns

### Converting Data Bags to Variables

Convert Chef data bags to Ansible variables:

```
Convert the data bag /path/to/data_bags/users.json to Ansible variables
```

### Generating AWX Job Templates

Create AWX/AAP job templates from cookbooks:

```
Generate an AWX job template from the cookbook at /path/to/cookbook
```

### Converting InSpec Tests

Convert InSpec tests to Ansible validation:

```
Convert the InSpec profile /path/to/inspec to Ansible tests
```

## Example Workflows

### Complete Cookbook Migration

1. **Assess complexity**:
   ```
   Assess the migration complexity for /path/to/cookbook
   ```

2. **Generate migration plan**:
   ```
   Generate a migration plan for this cookbook
   ```

3. **Convert recipes**:
   ```
   Convert all recipes in this cookbook to playbooks
   ```

4. **Convert data bags**:
   ```
   Convert data bags to Ansible Vault
   ```

5. **Create AWX integration**:
   ```
   Generate AWX job templates for this cookbook
   ```

### Habitat to Container Migration

1. **Parse Habitat plan**:
   ```
   Parse the Habitat plan at /habitat/plan.sh
   ```

2. **Convert to Dockerfile**:
   ```
   Convert this Habitat plan to a Dockerfile using ubuntu:22.04
   ```

3. **Generate Compose**:
   ```
   Generate docker-compose.yml for these Habitat plans
   ```

## Tips for Success

!!! tip "Start Small"
    Begin with a simple cookbook that has few dependencies. This helps you understand the conversion process before tackling complex cookbooks.

!!! tip "Review Conversions"
    Always review generated playbooks for:

    - Correct module selection
    - Proper variable substitution
    - Guard condition conversion
    - Notification handling

!!! tip "Use Validation"
    Run the validation tool on every conversion to catch potential issues early.

!!! tip "Test Incrementally"
    Test converted playbooks in a development environment before production deployment.

## Next Steps

Now that you've completed your first migration, explore:

- **[MCP Tools Reference](../user-guide/mcp-tools.md)** - All 38 available tools
- **[CLI Usage Guide](../user-guide/cli-usage.md)** - Advanced CLI features
- **[Migration Guide](../migration-guide/overview.md)** - Complete migration methodology
- **[Examples](../user-guide/examples.md)** - Real-world migration examples

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [API Reference](../api-reference/server.md)
3. Ask your AI assistant for help
4. Open an issue on [GitHub](https://github.com/kpeacocke/souschef/issues)

## Troubleshooting

### Conversion Doesn't Match Expected Output

- Review the Chef recipe for complex guards or custom resources
- Check attribute precedence in the source cookbook
- Validate that template variables are correctly extracted

### Playbook Fails Ansible Lint

- Run the validation tool to identify issues
- Review Ansible best practices in the [User Guide](../user-guide/mcp-tools.md)
- Check for deprecated module usage

### Performance Issues with Large Cookbooks

- Use the profiling tools to identify bottlenecks:
  ```bash
  souschef-cli profile /path/to/large_cookbook
  ```
- Consider breaking large recipes into smaller, focused playbooks
- Review the [Performance Optimization](../user-guide/examples.md#performance-optimization) guide
