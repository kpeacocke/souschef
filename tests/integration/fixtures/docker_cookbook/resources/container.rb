# Custom resource for managing Docker containers - Chef 17+ unified mode
unified_mode true

resource_name :docker_container

property :container_name, String, name_property: true
property :image, String, required: true
property :tag, String, default: 'latest'
property :command, [String, Array]
property :ports, Hash, default: {}
property :volumes, Hash, default: {}
property :environment, Hash, default: {}
property :network, String
property :restart_policy, String, default: 'unless-stopped'
property :detach, [true, false], default: true
property :remove_on_stop, [true, false], default: false
property :user, String
property :working_dir, String
property :labels, Hash, default: {}
property :hostname, String
property :memory_limit, String
property :cpu_shares, Integer

action :run do
  # Pull image if needed
  # ⚠️ SECURITY WARNING - TEST FIXTURE ONLY - ANTI-PATTERN EXAMPLE
  # This code demonstrates INSECURE string interpolation in shell commands.
  # String interpolation can lead to command injection if user-controlled values
  # (like image names from web requests) are used without proper validation.
  #
  # SECURE ALTERNATIVE: Use array form for commands:
  #   execute "pull-docker-image-#{new_resource.image}" do
  #     command ["docker", "pull", "#{new_resource.image}:#{new_resource.tag}"]
  #   end
  #
  # This test fixture is intentionally insecure to verify the converter
  # can handle real-world Chef code patterns. DO NOT copy this pattern.
  execute "pull-docker-image-#{new_resource.image}" do
    command "docker pull #{new_resource.image}:#{new_resource.tag}"
    not_if "docker images | grep -q #{new_resource.image}"
  end

  # Build docker run command
  docker_command = ['docker', 'run']
  docker_command << '--detach' if new_resource.detach
  docker_command << '--rm' if new_resource.remove_on_stop
  docker_command << "--name #{new_resource.container_name}"
  docker_command << "--restart #{new_resource.restart_policy}"
  docker_command << "--network #{new_resource.network}" if new_resource.network
  docker_command << "--hostname #{new_resource.hostname}" if new_resource.hostname
  docker_command << "--user #{new_resource.user}" if new_resource.user
  docker_command << "--workdir #{new_resource.working_dir}" if new_resource.working_dir
  docker_command << "--memory #{new_resource.memory_limit}" if new_resource.memory_limit
  docker_command << "--cpu-shares #{new_resource.cpu_shares}" if new_resource.cpu_shares

  new_resource.ports.each do |host_port, container_port|
    docker_command << "-p #{host_port}:#{container_port}"
  end

  new_resource.volumes.each do |host_path, container_path|
    docker_command << "-v #{host_path}:#{container_path}"
  end

  new_resource.environment.each do |key, value|
    docker_command << "-e #{key}=#{value}"
  end

  new_resource.labels.each do |key, value|
    docker_command << "--label #{key}=#{value}"
  end

  docker_command << "#{new_resource.image}:#{new_resource.tag}"

  if new_resource.command
    cmd = new_resource.command.is_a?(Array) ? new_resource.command.join(' ') : new_resource.command
    docker_command << cmd
  end

  execute "run-docker-container-#{new_resource.container_name}" do
    command docker_command.join(' ')
    not_if "docker ps -a | grep -q #{new_resource.container_name}"
  end
end

action :stop do
  execute "stop-docker-container-#{new_resource.container_name}" do
    command "docker stop #{new_resource.container_name}"
    only_if "docker ps | grep -q #{new_resource.container_name}"
  end
end

action :remove do
  execute "remove-docker-container-#{new_resource.container_name}" do
    command "docker rm -f #{new_resource.container_name}"
    only_if "docker ps -a | grep -q #{new_resource.container_name}"
  end
end

action :restart do
  execute "restart-docker-container-#{new_resource.container_name}" do
    command "docker restart #{new_resource.container_name}"
    only_if "docker ps | grep -q #{new_resource.container_name}"
  end
end
