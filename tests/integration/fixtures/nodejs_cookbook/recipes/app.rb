# Node.js application deployment recipe - Chef 16+ unified mode

# Ensure Node.js is installed
include_recipe 'nodejs::default'

# Application deployment directory
app_dir = "#{node['nodejs']['app']['dir']}/current"

directory app_dir do
  owner node['nodejs']['app']['user']
  group node['nodejs']['app']['group']
  mode '0755'
  recursive true
  action :create
end

# Deploy application code (simplified - would use git/deploy resource in production)
directory "#{app_dir}/app" do
  owner node['nodejs']['app']['user']
  group node['nodejs']['app']['group']
  mode '0755'
  action :create
end

# Create package.json
file "#{app_dir}/package.json" do
  content <<~JSON
    {
      "name": "example-app",
      "version": "1.0.0",
      "main": "server.js",
      "dependencies": {
        "express": "^4.18.0"
      },
      "scripts": {
        "start": "node server.js"
      }
    }
  JSON
  owner node['nodejs']['app']['user']
  group node['nodejs']['app']['group']
  mode '0644'
end

# Install npm dependencies
execute 'npm-install-dependencies' do
  command 'npm install --production'
  cwd app_dir
  user node['nodejs']['app']['user']
  group node['nodejs']['app']['group']
  environment node['nodejs']['app']['environment']
  not_if { ::File.exist?("#{app_dir}/node_modules") }
end

# Create PM2 ecosystem file
if node['nodejs']['pm2']['enabled']
  template "#{app_dir}/ecosystem.config.js" do
    source 'ecosystem.config.js.erb'
    owner node['nodejs']['app']['user']
    group node['nodejs']['app']['group']
    mode '0644'
    variables(
      app_name: 'example-app',
      script: "#{app_dir}/server.js",
      instances: node['nodejs']['pm2']['instances'],
      exec_mode: node['nodejs']['pm2']['exec_mode'],
      max_memory_restart: node['nodejs']['pm2']['max_memory_restart'],
      env: node['nodejs']['app']['environment']
    )
  end

  # Start/restart application with PM2
  execute 'pm2-start-app' do
    command "pm2 startOrRestart #{app_dir}/ecosystem.config.js --update-env"
    user node['nodejs']['app']['user']
    environment({ 'HOME' => node['nodejs']['app']['dir'] })
    cwd app_dir
  end

  execute 'pm2-save' do
    command 'pm2 save'
    user node['nodejs']['app']['user']
    environment({ 'HOME' => node['nodejs']['app']['dir'] })
  end
end

# Create systemd service (alternative to PM2)
unless node['nodejs']['pm2']['enabled']
  template '/etc/systemd/system/nodejs-app.service' do
    source 'nodejs-app.service.erb'
    owner 'root'
    group 'root'
    mode '0644'
    variables(
      user: node['nodejs']['app']['user'],
      group: node['nodejs']['app']['group'],
      working_directory: app_dir,
      exec_start: '/usr/bin/node server.js',
      environment: node['nodejs']['app']['environment']
    )
    notifies :run, 'execute[systemctl-daemon-reload]', :immediately
    notifies :restart, 'service[nodejs-app]', :delayed
  end

  execute 'systemctl-daemon-reload' do
    command 'systemctl daemon-reload'
    action :nothing
  end

  service 'nodejs-app' do
    action [:enable, :start]
  end
end
