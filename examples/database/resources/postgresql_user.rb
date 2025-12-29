#
# Custom resource for managing PostgreSQL users
#

property :username, String, name_property: true
property :password, String, required: true, sensitive: true
property :superuser, [true, false], default: false
property :createdb, [true, false], default: false
property :createrole, [true, false], default: false
property :login, [true, false], default: true
property :replication, [true, false], default: false
property :connection_limit, Integer, default: -1

default_action :create

action :create do
  # Build CREATE ROLE command
  cmd = "CREATE ROLE #{new_resource.username}"
  cmd += " WITH LOGIN" if new_resource.login
  cmd += " SUPERUSER" if new_resource.superuser
  cmd += " CREATEDB" if new_resource.createdb
  cmd += " CREATEROLE" if new_resource.createrole
  cmd += " REPLICATION" if new_resource.replication
  cmd += " PASSWORD '#{new_resource.password}'"
  cmd += " CONNECTION LIMIT #{new_resource.connection_limit}"

  execute "create-user-#{new_resource.username}" do
    command "sudo -u postgres psql -c \"#{cmd}\""
    action :run
    sensitive true
    only_if { shell_out("sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='#{new_resource.username}'\"").stdout.strip != '1' }
  end
end

action :drop do
  execute "drop-user-#{new_resource.username}" do
    command "sudo -u postgres dropuser #{new_resource.username}"
    action :run
    only_if { shell_out("sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='#{new_resource.username}'\"").stdout.strip == '1' }
  end
end

action :update_password do
  execute "update-password-#{new_resource.username}" do
    command "sudo -u postgres psql -c \"ALTER ROLE #{new_resource.username} WITH PASSWORD '#{new_resource.password}'\""
    action :run
    sensitive true
  end
end
