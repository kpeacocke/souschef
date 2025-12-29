#
# Cookbook:: database
# Recipe:: default
#
# PostgreSQL database server setup with custom resources

# Install PostgreSQL server
package "postgresql-#{node['postgresql']['version']}" do
  action :install
end

package "postgresql-contrib-#{node['postgresql']['version']}" do
  action :install
end

package 'postgresql-client' do
  action :install
end

# Ensure PostgreSQL service is running
service 'postgresql' do
  supports status: true, restart: true, reload: true
  action [:enable, :start]
end

# Configure PostgreSQL
template '/etc/postgresql/postgresql.conf' do
  source 'postgresql.conf.erb'
  owner 'postgres'
  group 'postgres'
  mode '0644'
  variables(
    config: node['postgresql']['config']
  )
  notifies :reload, 'service[postgresql]', :delayed
end

# Configure authentication
template '/etc/postgresql/pg_hba.conf' do
  source 'pg_hba.conf.erb'
  owner 'postgres'
  group 'postgres'
  mode '0640'
  notifies :reload, 'service[postgresql]', :delayed
end

# Create databases using custom resource
node['postgresql']['databases'].each do |db_name, db_config|
  postgresql_database db_name do
    owner db_config['owner']
    encoding db_config['encoding']
    template db_config['template']
    locale db_config['locale']
    action :create
    not_if "sudo -u postgres psql -lqt | cut -d \\| -f 1 | grep -qw #{db_name}"
  end
end

# Create users
node['postgresql']['users'].each do |username, user_config|
  postgresql_user username do
    password user_config['password']
    superuser user_config['superuser']
    createdb user_config['createdb']
    createrole user_config['createrole']
    action :create
    not_if "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='#{username}'\" | grep -q 1"
  end
end

# Set up backup directory
if node['postgresql']['backup']['enabled']
  directory node['postgresql']['backup']['dir'] do
    owner 'postgres'
    group 'postgres'
    mode '0700'
    recursive true
    action :create
  end

  # Backup script
  template '/usr/local/bin/pg-backup.sh' do
    source 'pg-backup.sh.erb'
    owner 'root'
    group 'root'
    mode '0755'
    variables(
      backup_dir: node['postgresql']['backup']['dir'],
      retention_days: node['postgresql']['backup']['retention_days']
    )
    action :create
  end

  # Cron job for daily backups
  cron 'postgresql-backup' do
    minute '0'
    hour '2'
    command '/usr/local/bin/pg-backup.sh'
    user 'postgres'
    action :create
  end
end

# Monitoring and maintenance
cron 'postgresql-vacuum' do
  minute '0'
  hour '3'
  weekday '0'
  command 'vacuumdb --all --analyze'
  user 'postgres'
  action :create
end

log 'postgresql-setup-complete' do
  message 'PostgreSQL database server configured successfully'
  level :info
end
