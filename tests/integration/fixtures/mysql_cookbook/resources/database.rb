# Custom resource for managing MySQL databases - Chef 14+ syntax
resource_name :mysql_database

property :database_name, String, name_property: true
property :host, String, default: 'localhost'
property :port, Integer, default: 3306
property :user, String, default: 'root'
property :password, String, required: true, sensitive: true
property :charset, String, default: 'utf8mb4'
property :collation, String, default: 'utf8mb4_general_ci'

action :create do
  execute "create-database-#{new_resource.database_name}" do
    command <<~SQL
      mysql -h #{new_resource.host} -P #{new_resource.port} -u #{new_resource.user} -p#{new_resource.password} -e "
      CREATE DATABASE IF NOT EXISTS #{new_resource.database_name}
      CHARACTER SET #{new_resource.charset}
      COLLATE #{new_resource.collation};
      "
    SQL
    sensitive true
    not_if <<~CHECK
      mysql -h #{new_resource.host} -P #{new_resource.port} -u #{new_resource.user} -p#{new_resource.password} -e "
      SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='#{new_resource.database_name}'
      " | grep -q #{new_resource.database_name}
    CHECK
  end
end

action :drop do
  execute "drop-database-#{new_resource.database_name}" do
    command <<~SQL
      mysql -h #{new_resource.host} -P #{new_resource.port} -u #{new_resource.user} -p#{new_resource.password} -e "
      DROP DATABASE IF EXISTS #{new_resource.database_name};
      "
    SQL
    sensitive true
    only_if <<~CHECK
      mysql -h #{new_resource.host} -P #{new_resource.port} -u #{new_resource.user} -p#{new_resource.password} -e "
      SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='#{new_resource.database_name}'
      " | grep -q #{new_resource.database_name}
    CHECK
  end
end
