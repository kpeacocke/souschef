# Test recipe with Chef search patterns
# Find all web servers in production environment
web_servers = search(:node, "role:web AND environment:production")

web_servers.each do |server|
  log "Found web server: #{server.name}" do
    level :info
  end
end

# Search for database servers
db_servers = search(:node, "role:database")

# Configure load balancer with web servers
template "/etc/nginx/upstream.conf" do
  source "upstream.conf.erb"
  variables(
    servers: search(:node, "role:web AND chef_environment:production")
  )
  notifies :reload, "service[nginx]", :delayed
end

# Use partial search for efficiency
monitoring_nodes = partial_search(:node, "tags:monitoring",
  keys: {
    'name' => ['name'],
    'ip' => ['ipaddress'],
    'roles' => ['roles']
  }
)

# Check for specific platform
if search(:node, "platform:ubuntu").length > 0
  package "ubuntu-specific-package"
end

# Complex search with regex
web_nodes = search(:node, "hostname:~web.*\.example\.com")

# Environment-specific configuration
case node.chef_environment
when "production"
  app_servers = search(:node, "role:app AND chef_environment:production")
when "staging"
  app_servers = search(:node, "role:app AND chef_environment:staging")
end
