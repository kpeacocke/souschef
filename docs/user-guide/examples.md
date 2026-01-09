# Real-World Migration Examples

Practical examples demonstrating Chef-to-Ansible migrations using SousChef tools, from simple packages to complex enterprise patterns.

## Example Structure

Each example follows this pattern:

1. **Chef Code** - Original Chef implementation
2. **Analysis** - SousChef tool usage to understand the code
3. **Conversion** - Automated conversion to Ansible
4. **Validation** - Testing and verification
5. **Best Practices** - Optimization and improvements

---

## Example 1: Simple Package Installation

### Chef Recipe

```ruby
# recipes/nginx.rb
package 'nginx' do
  action :install
end

service 'nginx' do
  action [:enable, :start]
end
```

### Analysis with SousChef

=== "MCP (AI Assistant)"
    ```
    Parse the recipe at recipes/nginx.rb and show me what resources it contains
    ```

=== "CLI"
    ```bash
    souschef-cli recipe recipes/nginx.rb
    ```

**Output:**
```
Resource 1: package[nginx]
  Action: install
Resource 2: service[nginx]
  Action: enable, start
```

### Conversion

=== "MCP (AI Assistant)"
    ```
    Generate an Ansible playbook from recipes/nginx.rb
    ```

=== "CLI"
    ```bash
    souschef-cli convert package nginx --action install > tasks/nginx.yml
    souschef-cli convert service nginx --action 'enable,start' >> tasks/nginx.yml
    ```

**Generated Ansible:**

```yaml
---
- name: Install nginx
  ansible.builtin.package:
    name: nginx
    state: present

- name: Enable and start nginx
  ansible.builtin.service:
    name: nginx
    enabled: true
    state: started
```

### Validation

```bash
# Validate the conversion
souschef-cli validate playbook --content "$(cat tasks/nginx.yml)"

# Test in development
ansible-playbook -i inventory/dev tasks/nginx.yml --check
ansible-playbook -i inventory/dev tasks/nginx.yml

# Verify idempotency
ansible-playbook -i inventory/dev tasks/nginx.yml --check
```

**Best Practice:** ✅ Direct conversion works perfectly for simple packages and services.

---

## Example 2: Template with Variables

### Chef Recipe

```ruby
# recipes/web.rb
template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    worker_processes: node['nginx']['workers'],
    worker_connections: node['nginx']['connections'],
    server_name: node['nginx']['server_name']
  )
  notifies :reload, 'service[nginx]', :delayed
end

service 'nginx' do
  action :nothing
end
```

**Chef Template (templates/nginx.conf.erb):**
```erb
user nginx;
worker_processes <%= @worker_processes %>;

events {
    worker_connections <%= @worker_connections %>;
}

http {
    server {
        listen 80;
        server_name <%= @server_name %>;
    }
}
```

### Conversion

```bash
# Parse template and convert
souschef-cli template templates/nginx.conf.erb --format json > template_analysis.json
```

**Generated Ansible:**

```yaml
# tasks/web.yml
- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: '0644'
  notify: Reload nginx

# handlers/main.yml
- name: Reload nginx
  ansible.builtin.service:
    name: nginx
    state: reloaded
```

**Jinja2 Template (templates/nginx.conf.j2):**
```jinja2
user nginx;
worker_processes {{ nginx_workers }};

events {
    worker_connections {{ nginx_connections }};
}

http {
    server {
        listen 80;
        server_name {{ nginx_server_name }};
    }
}
```

**Variables (group_vars/all.yml):**
```yaml
nginx_workers: 4
nginx_connections: 1024
nginx_server_name: example.com
```

---

## Example 3: Conditional Execution with Guards

### Chef Recipe

```ruby
# recipes/deploy.rb
execute 'deploy_application' do
  command '/opt/deploy.sh'
  user 'deploy'
  only_if { ::File.exist?('/opt/app/latest.tar.gz') }
  not_if { ::File.exist?('/opt/app/.deployed') }
end

file '/opt/app/.deployed' do
  action :create
  only_if { node['app']['environment'] == 'production' }
end
```

### Conversion with Guard Handling

**Generated Ansible:**

```yaml
- name: Check for application archive
  ansible.builtin.stat:
    path: /opt/app/latest.tar.gz
  register: app_archive

- name: Check for deployment marker
  ansible.builtin.stat:
    path: /opt/app/.deployed
  register: deploy_marker

- name: Deploy application
  ansible.builtin.command:
    cmd: /opt/deploy.sh
  become: true
  become_user: deploy
  when:
    - app_archive.stat.exists
    - not deploy_marker.stat.exists

- name: Create deployment marker
  ansible.builtin.file:
    path: /opt/app/.deployed
    state: touch
    mode: '0644'
  when: app_environment == 'production'
```

**Best Practice:** ✅ Guards convert to `stat` checks + `when` conditions for clarity.

---

## Example 4: Data Bag Integration

### Chef Recipe

```ruby
# recipes/database.rb
db_secrets = data_bag_item('secrets', 'database')

postgresql_user 'app_user' do
  password db_secrets['password']
  action :create
end

template '/etc/app/database.yml' do
  source 'database.yml.erb'
  variables(
    host: db_secrets['host'],
    username: db_secrets['username'],
    password: db_secrets['password']
  )
  sensitive true
end
```

**Chef Data Bag (data_bags/secrets/database.json):**
```json
{
  "id": "database",
  "host": "db.example.com",
  "username": "app_user",
  "password": "secret123"
}
```

### Conversion

=== "MCP (AI Assistant)"
    ```
    Convert the data bag at data_bags/secrets/database.json
    to Ansible Vault
    ```

=== "CLI"
    ```bash
    # Convert data bag to vars
    souschef-cli databag-convert data_bags/secrets/database.json --vault
    ```

**Generated Ansible:**

```yaml
# tasks/database.yml
- name: Create database user
  community.postgresql.postgresql_user:
    name: app_user
    password: "{{ db_password }}"
    state: present
  no_log: true

- name: Deploy database configuration
  ansible.builtin.template:
    src: database.yml.j2
    dest: /etc/app/database.yml
    mode: '0600'
  no_log: true
```

**Ansible Vault (group_vars/all/vault.yml):**
```yaml
# Encrypted with: ansible-vault encrypt group_vars/all/vault.yml
db_host: db.example.com
db_username: app_user
db_password: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          66386439653865...
```

**Best Practice:** ✅ Always use `no_log: true` for sensitive data tasks.

---

## Example 5: Chef Search to Ansible Inventory

### Chef Recipe

```ruby
# recipes/haproxy.rb
backends = search(:node, "role:webserver AND chef_environment:#{node.chef_environment}")

template '/etc/haproxy/haproxy.cfg' do
  source 'haproxy.cfg.erb'
  variables(
    backends: backends.map { |n| n['ipaddress'] }
  )
  notifies :reload, 'service[haproxy]'
end
```

### Conversion

=== "MCP (AI Assistant)"
    ```
    Convert Chef search "role:webserver AND chef_environment:production"
    to Ansible dynamic inventory group named "webservers"
    ```

**Generated Ansible:**

```yaml
# playbooks/haproxy.yml
- name: Configure HAProxy
  hosts: haproxy
  tasks:
    - name: Deploy HAProxy configuration
      ansible.builtin.template:
        src: haproxy.cfg.j2
        dest: /etc/haproxy/haproxy.cfg
        mode: '0644'
      notify: Reload haproxy
  
  handlers:
    - name: Reload haproxy
      ansible.builtin.service:
        name: haproxy
        state: reloaded
```

**Jinja2 Template (templates/haproxy.cfg.j2):**
```jinja2
global
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend http-in
    bind *:80
    default_backend webservers

backend webservers
    balance roundrobin
{% for host in groups['webservers'] %}
    server {{ host }} {{ hostvars[host]['ansible_host'] }}:80 check
{% endfor %}
```

**Inventory (inventory/production/hosts.yml):**
```yaml
all:
  children:
    webservers:
      hosts:
        web01:
          ansible_host: 10.0.1.10
        web02:
          ansible_host: 10.0.1.11
        web03:
          ansible_host: 10.0.1.12
    haproxy:
      hosts:
        lb01:
          ansible_host: 10.0.1.20
```

**Best Practice:** ✅ Chef search converts to Ansible inventory groups with `groups[]` variable.

---

## Example 6: Custom Resource Migration

### Chef Custom Resource

```ruby
# resources/app_deploy.rb
property :app_name, String, name_property: true
property :version, String, required: true
property :user, String, default: 'deploy'
property :environment, Hash, default: {}

action :deploy do
  directory "/opt/apps/#{new_resource.app_name}" do
    owner new_resource.user
    mode '0755'
    recursive true
  end

  remote_file "/opt/apps/#{new_resource.app_name}/app-#{new_resource.version}.tar.gz" do
    source "https://releases.example.com/#{new_resource.app_name}-#{new_resource.version}.tar.gz"
    owner new_resource.user
    mode '0644'
  end

  execute "extract_app" do
    command "tar xzf app-#{new_resource.version}.tar.gz"
    cwd "/opt/apps/#{new_resource.app_name}"
    user new_resource.user
  end
end
```

**Chef Recipe Usage:**
```ruby
app_deploy 'myapp' do
  version '1.2.3'
  user 'app'
  environment(
    'DATABASE_URL' => 'postgresql://localhost/myapp'
  )
  action :deploy
end
```

### Conversion to Ansible Role

**Role Structure:**
```
roles/app_deploy/
├── defaults/
│   └── main.yml
├── tasks/
│   └── main.yml
└── templates/
    └── env.j2
```

**defaults/main.yml:**
```yaml
app_deploy_user: deploy
app_deploy_base_path: /opt/apps
app_deploy_environment: {}
```

**tasks/main.yml:**
```yaml
- name: Create application directory
  ansible.builtin.file:
    path: "{{ app_deploy_base_path }}/{{ app_name }}"
    state: directory
    owner: "{{ app_deploy_user }}"
    mode: '0755'

- name: Download application archive
  ansible.builtin.get_url:
    url: "https://releases.example.com/{{ app_name }}-{{ app_version }}.tar.gz"
    dest: "{{ app_deploy_base_path }}/{{ app_name }}/app-{{ app_version }}.tar.gz"
    owner: "{{ app_deploy_user }}"
    mode: '0644'

- name: Extract application
  ansible.builtin.unarchive:
    src: "{{ app_deploy_base_path }}/{{ app_name }}/app-{{ app_version }}.tar.gz"
    dest: "{{ app_deploy_base_path }}/{{ app_name }}"
    remote_src: true
    owner: "{{ app_deploy_user }}"
```

**Playbook Usage:**
```yaml
- name: Deploy application
  hosts: app_servers
  roles:
    - role: app_deploy
      vars:
        app_name: myapp
        app_version: 1.2.3
        app_deploy_user: app
        app_deploy_environment:
          DATABASE_URL: postgresql://localhost/myapp
```

**Best Practice:** ✅ Custom resources → Ansible roles with similar interface.

---

## Example 7: InSpec to Ansible Testing

### Chef InSpec Profile

```ruby
# controls/nginx.rb
control 'nginx-01' do
  impact 1.0
  title 'Verify nginx installation'
  desc 'Ensure nginx is installed and configured correctly'
  
  describe package('nginx') do
    it { should be_installed }
  end
  
  describe service('nginx') do
    it { should be_enabled }
    it { should be_running }
  end
  
  describe file('/etc/nginx/nginx.conf') do
    it { should exist }
    it { should be_file }
    its('owner') { should eq 'root' }
    its('mode') { should cmp '0644' }
  end
  
  describe port(80) do
    it { should be_listening }
  end
end
```

### Conversion

=== "MCP (AI Assistant)"
    ```
    Convert InSpec profile at tests/inspec/nginx to Ansible assert tasks
    ```

=== "CLI"
    ```bash
    souschef-cli inspec-convert tests/inspec/nginx --format ansible_assert
    ```

**Generated Ansible Tests:**

```yaml
# tests/verify.yml
- name: Verify nginx installation
  hosts: webservers
  gather_facts: true
  tasks:
    - name: Check nginx package
      ansible.builtin.package_facts:
      
    - name: Assert nginx is installed
      ansible.builtin.assert:
        that:
          - "'nginx' in ansible_facts.packages"
        fail_msg: "nginx package is not installed"
        success_msg: "nginx package is installed"
    
    - name: Get nginx service status
      ansible.builtin.service_facts:
      
    - name: Assert nginx service is enabled and running
      ansible.builtin.assert:
        that:
          - ansible_facts.services['nginx.service'].state == 'running'
          - ansible_facts.services['nginx.service'].status == 'enabled'
        fail_msg: "nginx service is not running or enabled"
    
    - name: Check nginx config file
      ansible.builtin.stat:
        path: /etc/nginx/nginx.conf
      register: nginx_conf
    
    - name: Assert nginx config exists with correct permissions
      ansible.builtin.assert:
        that:
          - nginx_conf.stat.exists
          - nginx_conf.stat.isreg
          - nginx_conf.stat.pw_name == 'root'
          - nginx_conf.stat.mode == '0644'
        fail_msg: "nginx.conf not found or has incorrect permissions"
    
    - name: Check nginx is listening on port 80
      ansible.builtin.wait_for:
        port: 80
        timeout: 5
```

---

## Example 8: Habitat to Docker Migration

### Habitat Plan

```bash
# habitat/plan.sh
pkg_name=myapp
pkg_origin=example
pkg_version="1.0.0"
pkg_maintainer="DevOps Team <devops@example.com>"
pkg_license=("Apache-2.0")
pkg_upstream_url="https://example.com/myapp"

pkg_deps=(
  core/node
  core/nginx
)

pkg_build_deps=(
  core/git
)

pkg_exports=(
  [port]=http.port
)

pkg_exposes=(port)

do_build() {
  npm install --production
  npm run build
}

do_install() {
  cp -r dist/* "${pkg_prefix}/"
  cp -r node_modules "${pkg_prefix}/"
}
```

### Conversion

=== "MCP (AI Assistant)"
    ```
    Convert Habitat plan at habitat/plan.sh to Dockerfile
    using node:18-alpine as base image
    ```

**Generated Dockerfile:**

```dockerfile
# Multi-stage build for minimal image size
FROM node:18-alpine AS builder

WORKDIR /build

# Install build dependencies
RUN apk add --no-cache git

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --production

# Copy source
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:18-alpine

# Install nginx
RUN apk add --no-cache nginx

# Create non-root user
RUN addgroup -g 1001 app && \
    adduser -D -u 1001 -G app app

WORKDIR /app

# Copy built application
COPY --from=builder --chown=app:app /build/dist ./dist
COPY --from=builder --chown=app:app /build/node_modules ./node_modules

# Configure nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Switch to non-root user
USER app

# Start application
CMD ["node", "dist/server.js"]
```

**Generated docker-compose.yml:**

```yaml
version: '3.8'

services:
  myapp:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - PORT=8080
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 3s
      retries: 3
    restart: unless-stopped
    networks:
      - app_network

networks:
  app_network:
    driver: bridge
```

---

## Example 9: AWX Job Template Generation

### Chef Cookbook

Starting with a database cookbook containing installation and configuration recipes.

### Conversion

=== "MCP (AI Assistant)"
    ```
    Generate an AWX job template from examples/database cookbook
    named "Deploy PostgreSQL Database"
    ```

**Generated AWX Job Template (JSON):**

```json
{
  "name": "Deploy PostgreSQL Database",
  "description": "Converted from Chef cookbook: database",
  "job_type": "run",
  "inventory": "Production",
  "project": "Ansible Playbooks",
  "playbook": "database/site.yml",
  "credential": "SSH - Production",
  "verbosity": 1,
  "extra_vars": {
    "postgresql_version": "14",
    "postgresql_listen_addresses": "*",
    "postgresql_max_connections": 100
  },
  "ask_variables_on_launch": true,
  "ask_limit_on_launch": true,
  "survey_enabled": true,
  "survey_spec": {
    "name": "Database Deployment Survey",
    "description": "Configure PostgreSQL deployment parameters",
    "spec": [
      {
        "question_name": "PostgreSQL Version",
        "question_description": "PostgreSQL major version to install",
        "required": true,
        "type": "multiplechoice",
        "variable": "postgresql_version",
        "choices": ["12", "13", "14", "15"],
        "default": "14"
      },
      {
        "question_name": "Max Connections",
        "question_description": "Maximum number of client connections",
        "required": true,
        "type": "integer",
        "variable": "postgresql_max_connections",
        "min": 20,
        "max": 1000,
        "default": 100
      }
    ]
  }
}
```

**AWX CLI Usage:**
```bash
# Create job template
awx job_templates create \
  --name "Deploy PostgreSQL Database" \
  --job_type run \
  --inventory "Production" \
  --project "Ansible Playbooks" \
  --playbook "database/site.yml" \
  --extra_vars @job_template_vars.json
```

---

## Common Patterns & Solutions

### Pattern: Iterating Over Arrays

**Chef:**
```ruby
node['packages'].each do |pkg|
  package pkg do
    action :install
  end
end
```

**Ansible:**
```yaml
- name: Install packages
  ansible.builtin.package:
    name: "{{ item }}"
    state: present
  loop: "{{ packages }}"
```

### Pattern: Platform-Specific Actions

**Chef:**
```ruby
case node['platform']
when 'ubuntu', 'debian'
  package 'apache2'
when 'centos', 'redhat'
  package 'httpd'
end
```

**Ansible:**
```yaml
- name: Install web server (Debian)
  ansible.builtin.apt:
    name: apache2
    state: present
  when: ansible_os_family == 'Debian'

- name: Install web server (RedHat)
  ansible.builtin.yum:
    name: httpd
    state: present
  when: ansible_os_family == 'RedHat'
```

### Pattern: File Ownership and Permissions

**Chef:**
```ruby
file '/opt/app/config.yaml' do
  owner 'app'
  group 'app'
  mode '0600'
  content lazy { Chef::JSONCompat.to_json_pretty(node['app']['config']) }
end
```

**Ansible:**
```yaml
- name: Create application config
  ansible.builtin.copy:
    content: "{{ app_config | to_nice_yaml }}"
    dest: /opt/app/config.yaml
    owner: app
    group: app
    mode: '0600'
```

---

## Troubleshooting Guide

### Issue: Complex Ruby Logic Doesn't Convert

**Problem:** Chef recipe contains complex Ruby code that can't be directly converted.

**Solution:**
```ruby
# Chef - Complex Ruby logic
ruby_block 'complex_calculation' do
  block do
    result = node['values'].map { |v| v * 2 }.sum
    node.run_state['calculated_value'] = result
  end
end
```

**Ansible - Use set_fact:**
```yaml
- name: Perform complex calculation
  ansible.builtin.set_fact:
    calculated_value: "{{ values | map('int') | map('multiply', 2) | sum }}"
```

Or create custom module for very complex logic.

### Issue: Notification Chains

**Problem:** Complex notification dependencies in Chef.

**Chef:**
```ruby
template '/etc/app/config.yml' do
  notifies :restart, 'service[app]', :delayed
  notifies :run, 'execute[reload_cache]', :immediately
end

execute 'reload_cache' do
  command '/usr/bin/reload_cache.sh'
  action :nothing
end

service 'app' do
  action :nothing
end
```

**Ansible - Use handlers and flush:**
```yaml
- name: Deploy configuration
  ansible.builtin.template:
    src: config.yml.j2
    dest: /etc/app/config.yml
  notify:
    - Reload cache
    - Restart app

- name: Flush handlers if config changed
  meta: flush_handlers

# handlers/main.yml
- name: Reload cache
  ansible.builtin.command: /usr/bin/reload_cache.sh

- name: Restart app
  ansible.builtin.service:
    name: app
    state: restarted
```

### Issue: Chef Attributes Precedence

**Problem:** Complex attribute precedence in Chef doesn't map directly.

**Chef:**
```ruby
default['app']['port'] = 8080
override['app']['port'] = 9090  # Takes precedence
```

**Ansible - Use variable precedence:**
```yaml
# group_vars/all.yml (lowest precedence)
app_port: 8080

# group_vars/production.yml (higher precedence)
app_port: 9090

# host_vars/app01.yml (highest precedence)
app_port: 9091
```

---

## Performance Optimization

### Tip 1: Batch Package Installations

**Before:**
```yaml
- name: Install package 1
  ansible.builtin.package:
    name: nginx
    state: present

- name: Install package 2
  ansible.builtin.package:
    name: git
    state: present
```

**After:**
```yaml
- name: Install packages
  ansible.builtin.package:
    name:
      - nginx
      - git
    state: present
```

### Tip 2: Use Blocks for Error Handling

```yaml
- name: Deploy with rollback capability
  block:
    - name: Deploy new version
      ansible.builtin.copy:
        src: app-v2.jar
        dest: /opt/app/app.jar
        backup: true
      register: deploy_result

    - name: Restart application
      ansible.builtin.service:
        name: app
        state: restarted

  rescue:
    - name: Rollback on failure
      ansible.builtin.copy:
        src: "{{ deploy_result.backup_file }}"
        dest: /opt/app/app.jar
        remote_src: true

    - name: Restart with old version
      ansible.builtin.service:
        name: app
        state: restarted
```

### Tip 3: Parallel Execution with Strategy

```yaml
- name: Deploy to web servers
  hosts: webservers
  strategy: free  # Don't wait for all hosts
  tasks:
    - name: Deploy application
      ansible.builtin.copy:
        src: app.jar
        dest: /opt/app/
```

---

## Best Practices Checklist

- [ ] Use `validate_conversion` after each major conversion
- [ ] Test idempotency (run playbook twice, second run should show no changes)
- [ ] Use `no_log: true` for tasks handling sensitive data
- [ ] Organize playbooks into roles for reusability
- [ ] Use handlers for service restarts
- [ ] Implement proper error handling with blocks
- [ ] Tag tasks for selective execution
- [ ] Use `check_mode` for dry runs
- [ ] Document variable requirements in README
- [ ] Store secrets in Ansible Vault
- [ ] Use inventory groups instead of hardcoded hosts
- [ ] Implement health checks after deployments

---

## Related Documentation

- [MCP Tools Reference](mcp-tools.md) - Complete tool documentation
- [CLI Usage](cli-usage.md) - Command-line workflows
- [Migration Guide](../migration-guide/overview.md) - Migration methodology
- [Assessment Guide](../migration-guide/assessment.md) - Complexity assessment
- [Conversion Guide](../migration-guide/conversion.md) - Detailed conversion techniques

---

## Getting Additional Help

If you encounter patterns not covered here:

1. **Search the documentation** for similar patterns
2. **Use SousChef's AI assistant** to analyze your specific code
3. **Check Ansible docs** for module equivalents
4. **Test incrementally** - convert one resource at a time
5. **Contribute back** - share your solutions with the community

!!! tip "Share Your Examples"
    Have a complex migration pattern you solved? Consider contributing it to the documentation! See [Contributing](../contributing.md) for details.
