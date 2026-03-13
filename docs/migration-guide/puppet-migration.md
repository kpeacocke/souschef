# Puppet to Ansible Migration Guide

Enterprise guide for converting Puppet manifests and module directories to idiomatic Ansible playbooks using `ansible.builtin` modules.

## Overview

SousChef's Puppet migration feature automates the conversion of `.pp` Puppet manifests and module directories to Ansible automation.

The workflow follows four stages:

```
Puppet Manifest / Module → Parse → Convert → Deploy to AAP
```

Each stage is supported by dedicated MCP tools, CLI commands, and a web UI page, giving you full control over the migration whether you prefer conversational AI assistance or scripted pipelines.

### What Gets Converted

SousChef recognises **14 Puppet resource types**. Ten are fully mapped to idiomatic Ansible modules; four (`augeas`, `filebucket`, `notify`, `tidy`) are recognised and produce `ansible.builtin.debug` placeholder tasks with manual-review guidance.

**Fully mapped resource types:**

| Puppet Resource | Ansible Module | Notes |
|-----------------|----------------|-------|
| `package` | `ansible.builtin.package` | `ensure => installed/absent` → `state: present/absent` |
| `service` | `ansible.builtin.service` | `ensure => running`, `enable => true` |
| `file` (absent/directory) | `ansible.builtin.file` | `ensure => absent/directory` |
| `file` (with `content`) | `ansible.builtin.copy` | Inline content |
| `file` (with `source`) | `ansible.builtin.template` | Template reference |
| `user` | `ansible.builtin.user` | UID, groups, shell, home |
| `group` | `ansible.builtin.group` | GID, members |
| `exec` | `ansible.builtin.command` | Idempotency warning added |
| `cron` | `ansible.builtin.cron` | Schedule, command, user |
| `host` | `ansible.builtin.lineinfile` | `/etc/hosts` entry (with warning) |
| `mount` | `ansible.posix.mount` | Device, path, fstype, options |
| `ssh_authorized_key` | `ansible.posix.authorized_key` | Key, user, state |

**Recognised but not auto-converted:** `augeas`, `filebucket`, `notify`, `tidy` — each produces an `ansible.builtin.debug` placeholder task with a guidance message.

Unsupported constructs are never silently discarded — each one becomes a `debug` placeholder task with a `msg` field explaining what manual work is needed.

### What Cannot Be Converted Automatically

The following Puppet DSL constructs require manual review or AI-assisted conversion:

| Construct | Reason |
|-----------|--------|
| `hiera()` / `lookup()` | Hiera lookups require knowledge of your Hiera hierarchy |
| `create_resources()` | Dynamic resource creation without static structure |
| `generate()` | External command execution at compile time |
| `inline_template()` | Embedded Ruby logic |
| `defined()` | Conditional compile-time checks |
| Virtual resources (`@type { }`) | Deferred resource realisation |
| Exported resources (`@@type { }`) | Cross-node resource sharing |
| Resource collection (`<| |>`) | Dynamic resource collection |

For these constructs, use `convert_puppet_manifest_to_ansible_with_ai` or the AI-Assisted Convert button in the web UI.

---

## Prerequisites

### Control Node

- Python 3.10+
- Ansible 2.14+ or AAP 2.3+

### For `mount` resources

The `ansible.posix.mount` module requires the `ansible.posix` collection:

```bash
ansible-galaxy collection install ansible.posix
```

---

## Migration Workflow

### Step 1 — Parse the Manifest

Start by understanding what your manifest contains before converting.

=== "MCP (AI Assistant)"
    ```
    Parse my Puppet manifest at manifests/site.pp and show me all resources
    and any unsupported constructs
    ```

=== "CLI"
    ```bash
    souschef puppet parse manifests/site.pp
    ```

=== "Web UI"
    Navigate to **Chef** → **Puppet Migration**, select **Manifest File Path**,
    enter the path, and click **Parse**.

The parse output tells you:

- Which resources will convert automatically
- Which constructs need manual review or AI assistance
- Variable names and class definitions for reference

### Step 2 — Convert Standard Resources

If the manifest has no unsupported constructs, convert directly:

=== "MCP (AI Assistant)"
    ```
    Convert my Puppet manifest at manifests/webserver.pp to an Ansible playbook
    ```

=== "CLI"
    ```bash
    souschef puppet convert manifests/webserver.pp --output playbook.yml
    ```

=== "Web UI"
    Click **Convert to Ansible**. The playbook appears in the preview panel.
    Click **Download Playbook** to save.

### Step 3 — Handle Complex Constructs (AI-Assisted)

For manifests with Hiera lookups or other unsupported constructs:

=== "MCP (AI Assistant)"
    ```
    Convert manifests/complex.pp to Ansible — it uses Hiera lookups.
    Use AI assistance and explain what each placeholder needs.
    ```

=== "CLI"
    ```bash
    # AI-assisted conversion is available via MCP or Web UI
    # For CLI pipelines, convert first then review placeholders manually:
    souschef puppet convert manifests/complex.pp --output playbook.yml
    ```

=== "Web UI"
    Expand **AI Settings**, enter your API key and choose a provider,
    then click **AI-Assisted Convert**.

### Step 4 — Convert a Full Module

For Puppet modules with multiple manifests:

=== "MCP (AI Assistant)"
    ```
    Convert the Puppet module at modules/nginx to an Ansible playbook
    ```

=== "CLI"
    ```bash
    # Single consolidated playbook
    souschef puppet convert-module modules/nginx --output nginx.yml

    # Per-manifest output files
    souschef puppet convert-module modules/nginx --output-dir ./roles/nginx
    ```

=== "Web UI"
    Select **Module Directory Path**, enter the module path,
    and click **Convert to Ansible**.

### Step 5 — Review and Refine

Generated playbooks require review before production use:

1. **Replace `debug` placeholders**: Search for `ansible.builtin.debug` tasks and implement the correct Ansible module for each
2. **Resolve Hiera variables**: Replace Hiera lookup references with Ansible variables or vault-encrypted values
3. **Review `exec` idempotency**: Add `creates`, `when`, or `changed_when` conditions to `ansible.builtin.command` tasks
4. **Test in staging**: Run the playbook against a non-production environment first

---

## Puppet Resource Mapping Reference

### package

```puppet
# Puppet
package { 'nginx':
  ensure => installed,
}
```

```yaml
# Ansible
- name: "package[nginx]"
  ansible.builtin.package:
    name: nginx
    state: present
```

### service

```puppet
# Puppet
service { 'nginx':
  ensure => running,
  enable => true,
}
```

```yaml
# Ansible
- name: "service[nginx]"
  ansible.builtin.service:
    name: nginx
    state: started
    enabled: true
```

### file (directory)

```puppet
# Puppet
file { '/etc/nginx/conf.d':
  ensure => directory,
  owner  => 'root',
  mode   => '0755',
}
```

```yaml
# Ansible
- name: "file[/etc/nginx/conf.d]"
  ansible.builtin.file:
    path: /etc/nginx/conf.d
    state: directory
    owner: root
    mode: "0755"
```

### file (content)

```puppet
# Puppet
file { '/etc/motd':
  ensure  => file,
  content => "Managed by Ansible\n",
}
```

```yaml
# Ansible
- name: "file[/etc/motd]"
  ansible.builtin.copy:
    dest: /etc/motd
    content: "Managed by Ansible\n"
```

### exec

```puppet
# Puppet
exec { 'db-migrate':
  command => '/usr/bin/rake db:migrate',
  path    => '/usr/local/bin:/usr/bin',
}
```

```yaml
# Ansible
- name: "exec[db-migrate]"
  ansible.builtin.command:
    cmd: /usr/bin/rake db:migrate
  # WARNING: exec resources may not be idempotent. Add 'creates',
  # 'when', or 'changed_when' to prevent repeated execution.
```

### user

```puppet
# Puppet
user { 'deploy':
  ensure => present,
  uid    => 1001,
  shell  => '/bin/bash',
  home   => '/home/deploy',
}
```

```yaml
# Ansible
- name: "user[deploy]"
  ansible.builtin.user:
    name: deploy
    state: present
    uid: 1001
    shell: /bin/bash
    home: /home/deploy
```

---

## Common Patterns and Pitfalls

### Hiera Variables

Puppet code that uses `hiera()` or `lookup()` will produce placeholder tasks. After conversion, replace the placeholders with Ansible variables sourced from group_vars, host_vars, or Ansible Vault:

```yaml
# Generated placeholder
- name: "UNSUPPORTED: Hiera lookup"
  ansible.builtin.debug:
    msg: "Manual conversion required: hiera('db_password') — replace with an Ansible variable"

# Manually converted
- name: Set database password
  ansible.builtin.set_fact:
    db_password: "{{ vault_db_password }}"
```

### `exec` Idempotency

Puppet `exec` resources are inherently imperative. The converter wraps them in `ansible.builtin.command` but adds a warning comment. Always add an idempotency guard:

```yaml
# Add 'creates' for file-producing commands
- name: "exec[generate-cert]"
  ansible.builtin.command:
    cmd: openssl req -x509 -nodes -newkey rsa:2048 -keyout /etc/ssl/server.key -out /etc/ssl/server.crt
    creates: /etc/ssl/server.crt
```

### Class Parameters

Puppet class parameters become Ansible variables. Document them in `defaults/main.yml` or `group_vars/`:

```puppet
# Puppet class
class nginx (
  $port    = 80,
  $worker  = 4,
) { ... }
```

```yaml
# Ansible equivalent in defaults/main.yml
nginx_port: 80
nginx_workers: 4
```

---

## CLI Reference

```bash
# Parse a manifest
souschef puppet parse manifests/site.pp

# Parse a module
souschef puppet parse-module modules/nginx

# Convert a manifest to playbook
souschef puppet convert manifests/site.pp --output playbook.yml

# Convert a module to playbook
souschef puppet convert-module modules/nginx --output nginx.yml

# List all supported resource types
souschef puppet list-types
```

---

## MCP Tools Reference

| Tool | Purpose |
|------|---------|
| `parse_puppet_manifest` | Parse a manifest file |
| `parse_puppet_module` | Parse a module directory |
| `convert_puppet_manifest_to_ansible` | Convert manifest → playbook |
| `convert_puppet_module_to_ansible` | Convert module → playbook |
| `convert_puppet_resource_to_task` | Convert single resource → task |
| `list_puppet_supported_resource_types` | List all supported types |
| `convert_puppet_manifest_to_ansible_with_ai` | AI-assisted manifest conversion |
| `convert_puppet_module_to_ansible_with_ai` | AI-assisted module conversion |

---

## See Also

- **[MCP Tools Reference](../user-guide/mcp-tools.md#puppet-migration)** — Full tool documentation with examples
- **[CLI Usage Guide](../user-guide/cli-usage.md#puppet-migration-commands)** — Command-line reference
- **[Web UI Guide](../user-guide/ui.md#puppet-migration)** — Web interface walkthrough
- **[Architecture Guide](../ARCHITECTURE.md)** — How the Puppet pipeline fits the architecture
