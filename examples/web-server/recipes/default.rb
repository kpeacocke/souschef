#
# Cookbook:: web-server
# Recipe:: default
#
# Complete nginx web server setup with SSL, custom resources, and platform awareness

# Constants
NGINX_SERVICE = 'service[nginx]'

# Create nginx user and group
group node['nginx']['group'] do
  action :create
  system true
end

user node['nginx']['user'] do
  group node['nginx']['group']
  system true
  shell '/bin/false'
  home '/var/www'
  action :create
end

# Install nginx package
package node['nginx']['package_name'] do
  version node['nginx']['version'] unless node['nginx']['version'].nil?
  action :install
end

# Create required directories
[
  node['nginx']['conf_dir'],
  "#{node['nginx']['conf_dir']}/sites-available",
  "#{node['nginx']['conf_dir']}/sites-enabled",
  "#{node['nginx']['conf_dir']}/conf.d",
  node['nginx']['root_dir'],
  '/var/log/nginx',
].each do |dir|
  directory dir do
    owner 'root'
    group 'root'
    mode '0755'
    action :create
    recursive true
  end
end

# Main nginx configuration
template "#{node['nginx']['conf_dir']}/nginx.conf" do
  source 'nginx.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    worker_processes: node['nginx']['worker_processes'],
    worker_connections: node['nginx']['worker_connections'],
    user: node['nginx']['user'],
    error_log: node['nginx']['error_log'],
    access_log: node['nginx']['access_log']
  )
  action :create
  notifies :reload, NGINX_SERVICE, :delayed
end

# SSL setup (only if enabled)
if node['nginx']['ssl']['enabled']
  directory "#{node['nginx']['conf_dir']}/ssl" do
    owner 'root'
    group 'root'
    mode '0700'
    action :create
  end

  # SSL certificate and key would normally be deployed here
  # For example purposes, we'll just create placeholders
  file node['nginx']['ssl']['cert_path'] do
    content '# SSL certificate goes here'
    owner 'root'
    group 'root'
    mode '0644'
    action :create
    only_if { node['environment'] == 'development' }
  end

  file node['nginx']['ssl']['key_path'] do
    content '# SSL private key goes here'
    owner 'root'
    group 'root'
    mode '0600'
    action :create
    sensitive true
    only_if { node['environment'] == 'development' }
  end
end

# Default site configuration
template "#{node['nginx']['conf_dir']}/sites-available/default" do
  source 'default-site.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    server_name: node['nginx']['server_name'],
    port: node['nginx']['port'],
    ssl_port: node['nginx']['ssl_port'],
    root_dir: node['nginx']['root_dir'],
    ssl_enabled: node['nginx']['ssl']['enabled'],
    ssl_cert: node['nginx']['ssl']['cert_path'],
    ssl_key: node['nginx']['ssl']['key_path']
  )
  action :create
  notifies :reload, NGINX_SERVICE, :delayed
end

# Enable default site
link "#{node['nginx']['conf_dir']}/sites-enabled/default" do
  to "#{node['nginx']['conf_dir']}/sites-available/default"
  action :create
  notifies :reload, NGINX_SERVICE, :delayed
end

# Default index page
file "#{node['nginx']['root_dir']}/index.html" do
  content <<-HTML
<!DOCTYPE html>
<html>
<head>
  <title>Welcome to nginx!</title>
</head>
<body>
  <h1>Welcome to nginx!</h1>
  <p>Server: #{node['hostname']}</p>
  <p>Platform: #{node['platform']} #{node['platform_version']}</p>
</body>
</html>
  HTML
  owner node['nginx']['user']
  group node['nginx']['group']
  mode '0644'
  action :create
end

# Configure nginx service
service node['nginx']['service_name'] do
  supports status: true, restart: true, reload: true
  action [:enable, :start]
  subscribes :restart, "package[#{node['nginx']['package_name']}]", :immediately
end

# Validate configuration before reload
execute 'validate-nginx-config' do
  command 'nginx -t'
  action :nothing
  subscribes :run, "template[#{node['nginx']['conf_dir']}/nginx.conf]", :immediately
end

# Set up log rotation
include_recipe 'logrotate::default' if node['recipes'].include?('logrotate')

# Custom resource example: nginx virtual host
nginx_vhost 'example-app' do
  server_name 'app.example.com'
  port 8080
  root_dir '/var/www/apps/example'
  ssl_enabled false
  action :create
  only_if { node['environment'] == 'production' }
end

# Firewall rules (platform-specific)
case node['platform_family']
when 'debian'
  execute 'enable-ufw-http' do
    command 'ufw allow 80/tcp'
    action :run
    only_if 'which ufw'
    not_if 'ufw status | grep -q "80/tcp.*ALLOW"'
  end

  execute 'enable-ufw-https' do
    command 'ufw allow 443/tcp'
    action :run
    only_if { node['nginx']['ssl']['enabled'] && shell_out('which ufw').exitstatus == 0 }
    not_if 'ufw status | grep -q "443/tcp.*ALLOW"'
  end
when 'rhel'
  execute 'enable-firewalld-http' do
    command 'firewall-cmd --permanent --add-service=http'
    action :run
    only_if 'systemctl is-active firewalld'
    notifies :run, 'execute[reload-firewalld]', :immediately
  end

  execute 'enable-firewalld-https' do
    command 'firewall-cmd --permanent --add-service=https'
    action :run
    only_if { node['nginx']['ssl']['enabled'] }
    only_if 'systemctl is-active firewalld'
    notifies :run, 'execute[reload-firewalld]', :immediately
  end

  execute 'reload-firewalld' do
    command 'firewall-cmd --reload'
    action :nothing
  end
else
  log 'firewall-not-configured' do
    message "Firewall configuration not implemented for platform family: #{node['platform_family']}"
    level :warn
  end
end

# Monitoring script
cookbook_file '/usr/local/bin/check-nginx.sh' do
  source 'check-nginx.sh'
  owner 'root'
  group 'root'
  mode '0755'
  action :create
end

# Cron job for monitoring
cron 'nginx-health-check' do
  minute '*/5'
  command '/usr/local/bin/check-nginx.sh'
  user 'root'
  action :create
end

# Performance tuning based on CPU count
bash 'optimize-nginx-workers' do
  code <<-BASH
    cpu_count=$(nproc)
    sed -i "s/worker_processes.*/worker_processes $cpu_count;/" #{node['nginx']['conf_dir']}/nginx.conf
  BASH
  action :run
  only_if { node['nginx']['worker_processes'] == 'auto' }
  notifies :reload, NGINX_SERVICE, :delayed
end

log 'nginx-setup-complete' do
  message "Nginx web server setup completed successfully on #{node['hostname']}"
  level :info
end
