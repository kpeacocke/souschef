# Web Server Cookbook - Conversion Guide

This document shows how the Chef cookbook converts to Ansible playbook structure.

## Overview

**Chef Cookbook**: `web-server`
**Ansible Role**: `web_server`

## File Mapping

### Metadata
- Chef: `metadata.rb` → Ansible: `meta/main.yml`

### Attributes
- Chef: `attributes/default.rb` → Ansible: `defaults/main.yml`

### Recipes
- Chef: `recipes/default.rb` → Ansible: `tasks/main.yml`

### Templates
- Chef: `templates/default/*.erb` → Ansible: `templates/*.j2`

### Custom Resources
- Chef: `resources/nginx_vhost.rb` → Ansible: Custom module or included task file

## Conversion Examples

### 1. Package Installation

**Chef:**
```ruby
package node['nginx']['package_name'] do
  version node['nginx']['version'] unless node['nginx']['version'].nil?
  action :install
end
```

**Ansible:**
```yaml
- name: Install nginx
  ansible.builtin.package:
    name: "{{ nginx_package_name }}"
    state: present
    version: "{{ nginx_version | default(omit) }}"
```

### 2. Service Management

**Chef:**
```ruby
service node['nginx']['service_name'] do
  supports status: true, restart: true, reload: true
  action [:enable, :start]
  subscribes :restart, "package[#{node['nginx']['package_name']}]", :immediately
end
```

**Ansible:**
```yaml
- name: Enable and start nginx service
  ansible.builtin.service:
    name: "{{ nginx_service_name }}"
    state: started
    enabled: true
  notify: restart nginx
```

### 3. Template Rendering

**Chef:**
```ruby
template "#{node['nginx']['conf_dir']}/nginx.conf" do
  source 'nginx.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    worker_processes: node['nginx']['worker_processes'],
    worker_connections: node['nginx']['worker_connections']
  )
  notifies :reload, 'service[nginx]', :delayed
end
```

**Ansible:**
```yaml
- name: Configure nginx
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: "{{ nginx_conf_dir }}/nginx.conf"
    owner: root
    group: root
    mode: '0644'
  notify: reload nginx
```

### 4. Conditional Resources (Guards)

**Chef:**
```ruby
file node['nginx']['ssl']['cert_path'] do
  content '# SSL certificate goes here'
  owner 'root'
  group 'root'
  mode '0644'
  action :create
  only_if { node['environment'] == 'development' }
end
```

**Ansible:**
```yaml
- name: Create SSL certificate placeholder
  ansible.builtin.file:
    path: "{{ nginx_ssl_cert_path }}"
    state: file
    owner: root
    group: root
    mode: '0644'
  when: environment == 'development'
```

### 5. Platform-Specific Logic

**Chef:**
```ruby
case node['platform_family']
when 'debian'
  execute 'enable-ufw-http' do
    command 'ufw allow 80/tcp'
    action :run
    only_if 'which ufw'
  end
when 'rhel'
  execute 'enable-firewalld-http' do
    command 'firewall-cmd --permanent --add-service=http'
    action :run
    only_if 'systemctl is-active firewalld'
  end
end
```

**Ansible:**
```yaml
- name: Enable HTTP in UFW (Debian)
  community.general.ufw:
    rule: allow
    port: '80'
    proto: tcp
  when: ansible_os_family == 'Debian'

- name: Enable HTTP in firewalld (RHEL)
  ansible.posix.firewalld:
    service: http
    permanent: true
    state: enabled
  when: ansible_os_family == 'RedHat'
  notify: reload firewalld
```

### 6. Custom Resource Usage

**Chef:**
```ruby
nginx_vhost 'example-app' do
  server_name 'app.example.com'
  port 8080
  root_dir '/var/www/apps/example'
  ssl_enabled false
  action :create
end
```

**Ansible (using include_role or include_tasks):**
```yaml
- name: Configure nginx virtual host for example-app
  include_tasks: nginx_vhost.yml
  vars:
    vhost_name: example-app
    vhost_server_name: app.example.com
    vhost_port: 8080
    vhost_root_dir: /var/www/apps/example
    vhost_ssl_enabled: false
```

### 7. Notifications and Handlers

**Chef:**
```ruby
template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  notifies :reload, 'service[nginx]', :delayed
end

service 'nginx' do
  action [:enable, :start]
end
```

**Ansible:**
```yaml
# tasks/main.yml
- name: Configure nginx
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
  notify: reload nginx

# handlers/main.yml
- name: reload nginx
  ansible.builtin.service:
    name: nginx
    state: reloaded
```

## Complete Playbook Structure

```
web_server/
├── meta/
│   └── main.yml              # Dependencies and role info
├── defaults/
│   └── main.yml              # Default variables
├── vars/
│   └── main.yml              # Other variables
├── tasks/
│   ├── main.yml              # Main tasks
│   ├── install.yml           # Installation tasks
│   ├── configure.yml         # Configuration tasks
│   └── nginx_vhost.yml       # Virtual host management
├── templates/
│   ├── nginx.conf.j2
│   └── default-site.conf.j2
├── handlers/
│   └── main.yml              # Service handlers
└── files/
    └── check-nginx.sh        # Static files
```

## Notes

1. **Idempotency**: Both Chef and Ansible are idempotent, but Ansible makes this more explicit
2. **Testing**: Chef uses Test Kitchen; Ansible uses Molecule
3. **Attributes vs Variables**: Chef attributes map to Ansible variables
4. **Resources vs Modules**: Chef resources map to Ansible modules
5. **Custom Resources**: May need custom Ansible modules or reusable task files
