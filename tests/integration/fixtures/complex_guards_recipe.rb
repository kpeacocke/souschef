# Test recipe with complex guards for enhanced guard handling feature

# Array-based guards with multiple conditions
package 'postgresql' do
  action :install
  only_if ['test -f /etc/debian_version', 'which systemctl']
end

# Lambda/proc syntax guards
service 'postgresql' do
  action [:enable, :start]
  only_if { ::File.exist?('/var/lib/postgresql') }
end

# Not_if with array of conditions (all must be false to run)
directory '/var/log/app' do
  owner 'app'
  group 'app'
  mode '0755'
  not_if [
    'test -d /var/log/app',
    { ::File.directory?('/var/log/app') }
  ]
end

# Complex file existence with variable interpolation
template "#{node['app']['config_dir']}/database.yml" do
  source 'database.yml.erb'
  mode '0644'
  only_if { ::File.exist?("#{node['app']['config_dir']}") }
end

# Multiple guard types on same resource
execute 'migrate-database' do
  command 'rake db:migrate'
  cwd '/opt/app'
  only_if 'test -f /opt/app/Rakefile'
  not_if { File.exist?('/opt/app/.migrated') }
end

# Platform-specific guards
package 'apache2' do
  action :install
  only_if { platform_family?('debian') }
end

# Command existence checks
execute 'npm-install' do
  command 'npm install'
  cwd '/opt/myapp'
  only_if { system('which npm') }
  not_if { ::File.exist?('/opt/myapp/node_modules') }
end

# Nested conditionals with node attributes
file '/etc/app/feature-flag' do
  content 'enabled'
  only_if { node['app']['features']['new_ui'] == true }
  not_if 'test -f /etc/app/feature-flag'
end

# Backtick command execution
service 'nginx' do
  action :reload
  only_if { `pgrep nginx`.length > 0 }
end

# Lambda with complex logic
directory '/data/cache' do
  owner 'www-data'
  mode '0755'
  not_if do
    ::File.exist?('/data/cache') && ::File.directory?('/data/cache')
  end
end
