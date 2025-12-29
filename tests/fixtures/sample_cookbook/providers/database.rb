# LWRP provider for database management
action :create do
  execute "create_database" do
    command "createdb -h #{new_resource.host} -p #{new_resource.port} -U #{new_resource.username} #{new_resource.db_name}"
    not_if "psql -h #{new_resource.host} -p #{new_resource.port} -U #{new_resource.username} -lqt | cut -d \\| -f 1 | grep -qw #{new_resource.db_name}"
  end
end

action :drop do
  execute "drop_database" do
    command "dropdb -h #{new_resource.host} -p #{new_resource.port} -U #{new_resource.username} #{new_resource.db_name}"
    only_if "psql -h #{new_resource.host} -p #{new_resource.port} -U #{new_resource.username} -lqt | cut -d \\| -f 1 | grep -qw #{new_resource.db_name}"
  end
end

action :backup do
  execute "backup_database" do
    command "pg_dump -h #{new_resource.host} -p #{new_resource.port} -U #{new_resource.username} #{new_resource.db_name} > /backup/#{new_resource.db_name}.sql"
  end
end
