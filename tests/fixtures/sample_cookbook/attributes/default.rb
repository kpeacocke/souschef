#
# Cookbook:: nginx
# Attributes:: default
#

# Network configuration
default['nginx']['port'] = 80
default['nginx']['ssl_port'] = 443
default['nginx']['bind_address'] = '0.0.0.0'

# Worker configuration
default['nginx']['worker_processes'] = 'auto'
default['nginx']['worker_connections'] = 1024
override['nginx']['worker_rlimit_nofile'] = 65536

# Paths
default['nginx']['conf_dir'] = '/etc/nginx'
default['nginx']['log_dir'] = '/var/log/nginx'
default['nginx']['pid_file'] = '/var/run/nginx.pid'

# Security
default['nginx']['keepalive_timeout'] = 65
default['nginx']['client_max_body_size'] = '100m'
normal['nginx']['server_tokens'] = 'off'

# SSL Configuration
default['nginx']['ssl']['protocols'] = 'TLSv1.2 TLSv1.3'
default['nginx']['ssl']['ciphers'] = 'HIGH:!aNULL:!MD5'
default['nginx']['ssl']['prefer_server_ciphers'] = 'on'
