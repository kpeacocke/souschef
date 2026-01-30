# Docker installation recipe - Chef 17+ with unified mode

# Remove old Docker packages
%w(docker docker-engine docker.io containerd runc).each do |pkg|
  package pkg do
    action :remove
  end
end

# Install prerequisites
package %w(
  apt-transport-https
  ca-certificates
  curl
  gnupg
  lsb-release
) do
  action :install
end

# Add Docker repository
if platform_family?('debian')
  directory '/etc/apt/keyrings' do
    owner 'root'
    group 'root'
    mode '0755'
    recursive true
    action :create
  end

  execute 'add-docker-gpg-key' do
    command "curl -fsSL --proto =https #{node['docker']['repo_url']}/#{node['platform']}/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
    not_if { ::File.exist?('/etc/apt/keyrings/docker.gpg') }
  end

  file '/etc/apt/keyrings/docker.gpg' do
    mode '0644'
  end

  execute 'add-docker-repository' do
    command <<~BASH
      echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      #{node['docker']['repo_url']}/#{node['platform']} $(lsb_release -cs) stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
    BASH
    not_if { ::File.exist?('/etc/apt/sources.list.d/docker.list') }
    notifies :run, 'execute[apt-update-docker]', :immediately
  end

  execute 'apt-update-docker' do
    command 'apt-get update'
    action :nothing
  end
end

# Install Docker packages
%w(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin).each do |pkg|
  package pkg do
    action :install
  end
end

# Configure Docker daemon
directory '/etc/docker' do
  owner 'root'
  group 'root'
  mode '0755'
  action :create
end

file '/etc/docker/daemon.json' do
  content lazy { node['docker']['daemon'].to_json }
  owner 'root'
  group 'root'
  mode '0644'
  notifies :restart, 'service[docker]', :delayed
end

# Manage Docker service
service 'docker' do
  action [:enable, :start]
  supports status: true, restart: true, reload: false
end

# Add users to docker group
node['docker']['users'].each do |username|
  execute "add-#{username}-to-docker-group" do
    command "usermod -aG docker #{username}"
    only_if "id -u #{username}"
    not_if "id -nG #{username} | grep -qw docker"
  end
end

# Install Docker Compose standalone (if requested)
if node['docker']['compose']['install_method'] == 'binary'
  compose_version = node['docker']['compose']['version']
  remote_file '/usr/local/bin/docker-compose' do
    source "https://github.com/docker/compose/releases/download/v#{compose_version}/docker-compose-linux-x86_64"
    owner 'root'
    group 'root'
    mode '0755'
    action :create
    not_if { ::File.exist?('/usr/local/bin/docker-compose') }
  end
end

# Create Docker networks (custom networks would be defined via attributes)
# execute 'create-app-network' do
#   command 'docker network create app-network'
#   not_if 'docker network ls | grep -q app-network'
# end
