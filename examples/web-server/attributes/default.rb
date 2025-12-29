#
# Cookbook:: web-server
# Attributes:: default
#

# Nginx configuration
default['nginx']['version'] = '1.18.0'
default['nginx']['port'] = 80
default['nginx']['ssl_port'] = 443
default['nginx']['worker_processes'] = 'auto'
default['nginx']['worker_connections'] = 1024
default['nginx']['keepalive_timeout'] = 65

# Server configuration
default['nginx']['server_name'] = 'localhost'
default['nginx']['root_dir'] = '/var/www/html'
default['nginx']['user'] = 'www-data'
default['nginx']['group'] = 'www-data'

# SSL configuration
default['nginx']['ssl']['enabled'] = false
default['nginx']['ssl']['cert_path'] = '/etc/nginx/ssl/server.crt'
default['nginx']['ssl']['key_path'] = '/etc/nginx/ssl/server.key'
default['nginx']['ssl']['protocols'] = 'TLSv1.2 TLSv1.3'

# Logging
default['nginx']['access_log'] = '/var/log/nginx/access.log'
default['nginx']['error_log'] = '/var/log/nginx/error.log'
default['nginx']['log_level'] = 'warn'

# Performance tuning
default['nginx']['gzip']['enabled'] = true
default['nginx']['gzip']['comp_level'] = 6
default['nginx']['gzip']['types'] = 'text/plain text/css application/json application/javascript text/xml'

# Platform-specific
case node['platform_family']
when 'debian'
  default['nginx']['package_name'] = 'nginx'
  default['nginx']['service_name'] = 'nginx'
  default['nginx']['conf_dir'] = '/etc/nginx'
when 'rhel'
  default['nginx']['package_name'] = 'nginx'
  default['nginx']['service_name'] = 'nginx'
  default['nginx']['conf_dir'] = '/etc/nginx'
end
