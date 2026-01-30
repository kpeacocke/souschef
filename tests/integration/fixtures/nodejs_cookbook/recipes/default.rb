# Node.js installation recipe - Chef 16+ unified mode

# Install prerequisites
package %w(curl ca-certificates gnupg) do
  action :install
end

# Add NodeSource repository
if platform_family?('debian')
  # Add repository key
  execute 'add-nodesource-key' do
    command "curl -fsSL #{node['nodejs']['repo']['key']} | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg"
    not_if { ::File.exist?('/usr/share/keyrings/nodesource.gpg') }
  end

  # Add repository
  file '/etc/apt/sources.list.d/nodesource.list' do
    content "deb [signed-by=/usr/share/keyrings/nodesource.gpg] #{node['nodejs']['repo']['url']} nodistro main\n"
    mode '0644'
    notifies :run, 'execute[apt-update]', :immediately
  end

  execute 'apt-update' do
    command 'apt-get update'
    action :nothing
  end
elsif platform_family?('rhel')
  # Add NodeSource RPM repository
  execute 'setup-nodesource-repo' do
    command "curl -fsSL https://rpm.nodesource.com/setup_#{node['nodejs']['version']} | bash -"
    not_if { ::File.exist?('/etc/yum.repos.d/nodesource-el.repo') }
  end
end

# Install Node.js
package 'nodejs' do
  action :install
  version node['nodejs']['version'] if node['nodejs']['version'] && node['nodejs']['install_method'] == 'package'
end

# Install global npm packages
node['nodejs']['npm_packages'].each do |pkg|
  execute "npm-install-#{pkg}" do
    command "npm install -g #{pkg}"
    not_if "npm list -g #{pkg}"
  end
end

# Create application user
user node['nodejs']['app']['user'] do
  comment 'Node.js application user'
  system true
  shell '/bin/false'
  home node['nodejs']['app']['dir']
  action :create
end

group node['nodejs']['app']['group'] do
  members [node['nodejs']['app']['user']]
  action :create
end

# Create application directory
directory node['nodejs']['app']['dir'] do
  owner node['nodejs']['app']['user']
  group node['nodejs']['app']['group']
  mode '0755'
  recursive true
  action :create
end

# Install PM2 if enabled
if node['nodejs']['pm2']['enabled']
  execute 'install-pm2' do
    command 'npm install -g pm2'
    not_if 'which pm2'
  end

  # Configure PM2 startup
  execute 'pm2-startup' do
    command "env PATH=$PATH:/usr/bin pm2 startup systemd -u #{node['nodejs']['app']['user']} --hp #{node['nodejs']['app']['dir']}"
    not_if { ::File.exist?("/etc/systemd/system/pm2-#{node['nodejs']['app']['user']}.service") }
  end
end
