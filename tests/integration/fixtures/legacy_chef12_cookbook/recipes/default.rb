# Legacy Chef 12 recipe - old syntax patterns

# Old-style includes
include_recipe 'apt'
include_recipe 'build-essential'

# Install dependencies using old attribute syntax
node[:legacy_app][:dependencies].each do |pkg|
  package pkg do
    action :install
  end
end

# Create user with old syntax
user node[:legacy_app][:app_user] do
  comment 'Application user'
  home node[:legacy_app][:install_dir]
  shell '/bin/bash'
  system true
end

group node[:legacy_app][:app_group] do
  members [node[:legacy_app][:app_user]]
end

# Create directories with old guard syntax
directory node[:legacy_app][:install_dir] do
  owner node[:legacy_app][:app_user]
  group node[:legacy_app][:app_group]
  mode 0755
  recursive true
  not_if do
    File.directory?(node[:legacy_app][:install_dir])
  end
end

# Old-style template
template "#{node[:legacy_app][:install_dir]}/config.conf" do
  source 'config.conf.erb'
  owner node[:legacy_app][:app_user]
  group node[:legacy_app][:app_group]
  mode 0644
  variables(
    :app_name => node[:legacy_app][:app_name],
    :version => node[:legacy_app][:version]
  )
  notifies :restart, "service[#{node[:legacy_app][:app_name]}]"
end

# Old-style file resource
file "#{node[:legacy_app][:install_dir]}/README" do
  content <<-EOF
    This is #{node[:legacy_app][:app_name]} version #{node[:legacy_app][:version]}
    Installed in #{node[:legacy_app][:install_dir]}
  EOF
  owner node[:legacy_app][:app_user]
  group node[:legacy_app][:app_group]
  mode 0644
end

# Old-style execute with string guard
execute 'setup-application' do
  command "#{node[:legacy_app][:install_dir]}/bin/setup.sh"
  user node[:legacy_app][:app_user]
  cwd node[:legacy_app][:install_dir]
  not_if "test -f #{node[:legacy_app][:install_dir]}/.setup_complete"
end

# Old-style service definition
service node[:legacy_app][:app_name] do
  supports :status => true, :restart => true, :reload => true
  action [:enable, :start]
end

# Old-style bash resource
bash 'download-application' do
  user 'root'
  cwd '/tmp'
  code <<-EOH
    wget http://example.com/#{node[:legacy_app][:package_name]}-#{node[:legacy_app][:version]}.tar.gz
    tar -xzf #{node[:legacy_app][:package_name]}-#{node[:legacy_app][:version]}.tar.gz
    cp -r #{node[:legacy_app][:package_name]}/* #{node[:legacy_app][:install_dir]}/
  EOH
  not_if { File.exists?("#{node[:legacy_app][:install_dir]}/version.txt") }
end
