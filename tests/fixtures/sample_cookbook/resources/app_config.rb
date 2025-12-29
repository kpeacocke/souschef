# Custom resource for managing application configuration
property :config_name, String, name_property: true
property :port, Integer, default: 8080
property :host, String, default: 'localhost'
property :ssl_enabled, [true, false], default: false
property :workers, Integer, default: 4
property :timeout, Integer, default: 30

default_action :create

action :create do
  template "/etc/app/#{new_resource.config_name}.conf" do
    source 'app_config.erb'
    variables(
      port: new_resource.port,
      host: new_resource.host,
      ssl_enabled: new_resource.ssl_enabled,
      workers: new_resource.workers
    )
    notifies :restart, 'service[app]'
  end
end

action :delete do
  file "/etc/app/#{new_resource.config_name}.conf" do
    action :delete
  end
end
