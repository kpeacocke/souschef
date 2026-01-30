#
# Cookbook:: nginx
# Recipe:: default
#
# Installs and configures nginx web server

package 'nginx' do
  action :install
  version '1.18.0-0ubuntu1'
end

service 'nginx' do
  supports status: true, restart: true, reload: true
  action [:enable, :start]
end

template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  action :create
  notifies :reload, 'service[nginx]', :delayed
end

directory '/var/www/html' do
  owner 'www-data'
  group 'www-data'
  mode '0755'
  action :create
  recursive true
end

file '/var/www/html/index.html' do
  content '<h1>Welcome to nginx!</h1>'
  owner 'www-data'
  group 'www-data'
  mode '0644'
  action :create
end

# Configure logrotate
include_recipe 'logrotate::default'

execute 'test-nginx-config' do
  command 'nginx -t'
  action :nothing
  subscribes :run, 'template[/etc/nginx/nginx.conf]', :immediately
end
