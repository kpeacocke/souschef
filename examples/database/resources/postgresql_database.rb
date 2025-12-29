#
# Custom resource for managing PostgreSQL databases
#

property :database_name, String, name_property: true
property :owner, String, required: true
property :encoding, String, default: 'UTF8'
property :template, String, default: 'template0'
property :locale, String, default: 'en_US.UTF-8'
property :tablespace, String
property :connection_limit, Integer, default: -1

default_action :create

action :create do
  cmd = "CREATE DATABASE #{new_resource.database_name}"
  cmd += " OWNER #{new_resource.owner}"
  cmd += " ENCODING '#{new_resource.encoding}'"
  cmd += " TEMPLATE #{new_resource.template}"
  cmd += " LC_COLLATE='#{new_resource.locale}'"
  cmd += " LC_CTYPE='#{new_resource.locale}'"
  cmd += " TABLESPACE #{new_resource.tablespace}" if new_resource.tablespace
  cmd += " CONNECTION LIMIT #{new_resource.connection_limit}"

  execute "create-database-#{new_resource.database_name}" do
    command "sudo -u postgres psql -c \"#{cmd}\""
    action :run
    only_if { shell_out("sudo -u postgres psql -lqt | cut -d \\| -f 1 | grep -qw #{new_resource.database_name}").exitstatus != 0 }
  end
end

action :drop do
  execute "drop-database-#{new_resource.database_name}" do
    command "sudo -u postgres dropdb #{new_resource.database_name}"
    action :run
    only_if { shell_out("sudo -u postgres psql -lqt | cut -d \\| -f 1 | grep -qw #{new_resource.database_name}").exitstatus == 0 }
  end
end

action :backup do
  backup_file = "/var/backups/postgresql/#{new_resource.database_name}_#{Time.now.strftime('%Y%m%d_%H%M%S')}.sql"

  directory '/var/backups/postgresql' do
    owner 'postgres'
    group 'postgres'
    mode '0700'
    recursive true
  end

  execute "backup-database-#{new_resource.database_name}" do
    command "sudo -u postgres pg_dump #{new_resource.database_name} > #{backup_file}"
    action :run
  end

  file backup_file do
    owner 'postgres'
    group 'postgres'
    mode '0600'
  end
end
