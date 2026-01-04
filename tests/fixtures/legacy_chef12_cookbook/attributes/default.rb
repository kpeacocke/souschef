# Legacy Chef 12 attributes - old syntax patterns
default[:legacy_app][:app_name] = 'myapp'
default[:legacy_app][:app_user] = 'app'
default[:legacy_app][:app_group] = 'app'
default[:legacy_app][:install_dir] = '/opt/myapp'
default[:legacy_app][:version] = '1.0.0'

# Old-style platform conditionals
if platform?('ubuntu')
  default[:legacy_app][:package_name] = 'myapp-deb'
elsif platform?('centos', 'redhat')
  default[:legacy_app][:package_name] = 'myapp-rpm'
end

# Old array syntax
default[:legacy_app][:dependencies] = [
  'libssl-dev',
  'libcurl4-openssl-dev',
  'build-essential'
]
