#
# Custom resource for managing nginx virtual hosts
#

# Constants
WEB_USER = 'www-data'
NGINX_SERVICE = 'service[nginx]'

property :site_name, String, name_property: true
property :server_name, String, required: true
property :port, Integer, default: 80
property :ssl_port, Integer, default: 443
property :root_dir, String, required: true
property :ssl_enabled, [true, false], default: false
property :ssl_cert, String
property :ssl_key, String
property :php_enabled, [true, false], default: false
property :custom_config, String, default: ''

default_action :create

action :create do
  # Create document root
  directory new_resource.root_dir do
    owner WEB_USER
    group WEB_USER
    mode '0755'
    recursive true
    action :create
  end

  # Create site configuration
  template "/etc/nginx/sites-available/#{new_resource.site_name}" do
    source 'vhost.conf.erb'
    cookbook 'web-server'
    variables(
      server_name: new_resource.server_name,
      port: new_resource.port,
      ssl_port: new_resource.ssl_port,
      root_dir: new_resource.root_dir,
      ssl_enabled: new_resource.ssl_enabled,
      ssl_cert: new_resource.ssl_cert,
      ssl_key: new_resource.ssl_key,
      php_enabled: new_resource.php_enabled,
      custom_config: new_resource.custom_config
    )
    action :create
    notifies :reload, NGINX_SERVICE, :delayed
  end

  # Enable site
  link "/etc/nginx/sites-enabled/#{new_resource.site_name}" do
    to "/etc/nginx/sites-available/#{new_resource.site_name}"
    action :create
    notifies :reload, NGINX_SERVICE, :delayed
  end

  # Create default index if it doesn't exist
  file "#{new_resource.root_dir}/index.html" do
    content "<h1>#{new_resource.server_name}</h1>"
    owner WEB_USER
    group WEB_USER
    mode '0644'
    action :create_if_missing
  end
end

action :delete do
  # Disable site
  link "/etc/nginx/sites-enabled/#{new_resource.site_name}" do
    action :delete
    notifies :reload, NGINX_SERVICE, :delayed
  end

  # Remove configuration
  file "/etc/nginx/sites-available/#{new_resource.site_name}" do
    action :delete
    notifies :reload, NGINX_SERVICE, :delayed
  end
end

action :disable do
  link "/etc/nginx/sites-enabled/#{new_resource.site_name}" do
    action :delete
    notifies :reload, NGINX_SERVICE, :delayed
  end
end

action :enable do
  link "/etc/nginx/sites-enabled/#{new_resource.site_name}" do
    to "/etc/nginx/sites-available/#{new_resource.site_name}"
    action :create
    notifies :reload, NGINX_SERVICE, :delayed
  end
end
