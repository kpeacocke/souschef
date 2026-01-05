# Apache2 default recipe - Realistic Chef 15+ cookbook

# Install Apache package
package node['apache']['package'] do
  action :install
end

# Create necessary directories
directory node['apache']['log_dir'] do
  owner 'root'
  group 'root'
  mode '0755'
  recursive true
  action :create
end

directory "#{node['apache']['conf_dir']}/sites-available" do
  owner 'root'
  group 'root'
  mode '0755'
  action :create
end

directory "#{node['apache']['conf_dir']}/sites-enabled" do
  owner 'root'
  group 'root'
  mode '0755'
  action :create
end

# Configure Apache main config
template "#{node['apache']['conf_dir']}/apache2.conf" do
  source 'apache2.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    timeout: node['apache']['timeout'],
    keepalive: node['apache']['keepalive'],
    keepalive_timeout: node['apache']['keepalivetimeout'],
    log_dir: node['apache']['log_dir'],
    servertokens: node['apache']['servertokens'],
    serversignature: node['apache']['serversignature']
  )
  notifies :reload, 'service[apache2]', :delayed
end

# Enable default modules
node['apache']['default_modules'].each do |mod|
  execute "enable-module-#{mod}" do
    command "a2enmod #{mod}"
    not_if "test -L #{node['apache']['conf_dir']}/mods-enabled/#{mod}.load"
    notifies :reload, 'service[apache2]', :delayed
  end
end

# Configure ports
template "#{node['apache']['conf_dir']}/ports.conf" do
  source 'ports.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    listen_ports: node['apache']['listen_ports']
  )
  notifies :reload, 'service[apache2]', :delayed
end

# Manage Apache service
service 'apache2' do
  service_name node['apache']['service_name']
  supports status: true, restart: true, reload: true
  action [:enable, :start]
end

# Setup logrotate
include_recipe 'logrotate::default'

logrotate_app 'apache2' do
  path ["#{node['apache']['log_dir']}/*.log"]
  frequency 'daily'
  rotate 14
  options %w(missingok compress delaycompress notifempty sharedscripts)
  postrotate <<~SCRIPT
    if /etc/init.d/#{node['apache']['service_name']} status > /dev/null ; then
      /etc/init.d/#{node['apache']['service_name']} reload > /dev/null
    fi
  SCRIPT
end
