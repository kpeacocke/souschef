# Apache2 default attributes
default['apache']['package'] = 'apache2'
default['apache']['service_name'] = 'apache2'
default['apache']['conf_dir'] = '/etc/apache2'
default['apache']['log_dir'] = '/var/log/apache2'
default['apache']['error_log'] = "#{node['apache']['log_dir']}/error.log"
default['apache']['access_log'] = "#{node['apache']['log_dir']}/access.log"

# Version-specific attributes (Chef 15+)
default['apache']['version'] = '2.4'
default['apache']['listen_ports'] = [80, 443]
default['apache']['contact'] = 'webmaster@localhost'
default['apache']['timeout'] = 300
default['apache']['keepalive'] = 'On'
default['apache']['keepaliverequests'] = 100
default['apache']['keepalivetimeout'] = 5

# Module management
default['apache']['default_modules'] = %w(
  status
  alias
  auth_basic
  authn_file
  authz_groupfile
  authz_host
  authz_user
  autoindex
  dir
  env
  mime
  negotiation
  setenvif
  log_config
  logio
)

# Platform-specific attributes
case node['platform_family']
when 'rhel', 'fedora'
  default['apache']['package'] = 'httpd'
  default['apache']['service_name'] = 'httpd'
  default['apache']['conf_dir'] = '/etc/httpd'
  default['apache']['log_dir'] = '/var/log/httpd'
when 'debian'
  default['apache']['package'] = 'apache2'
  default['apache']['service_name'] = 'apache2'
end

# Security settings
default['apache']['servertokens'] = 'Prod'
default['apache']['serversignature'] = 'Off'
default['apache']['traceenable'] = 'Off'
