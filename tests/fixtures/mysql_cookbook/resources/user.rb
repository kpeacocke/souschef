# Custom resource for managing MySQL users - Chef 14+ syntax
resource_name :mysql_user

property :username, String, name_property: true
property :host, String, default: 'localhost'
property :password, String, required: true, sensitive: true
property :database_host, String, default: 'localhost'
property :database_port, Integer, default: 3306
property :admin_user, String, default: 'root'
property :admin_password, String, required: true, sensitive: true
property :privileges, Array, default: ['ALL']
property :database, String, default: '*'
property :grant_option, [true, false], default: false

action :create do
  # Create user
  execute "create-mysql-user-#{new_resource.username}" do
    command <<~SQL
      mysql -h #{new_resource.database_host} -P #{new_resource.database_port} \
            -u #{new_resource.admin_user} -p#{new_resource.admin_password} -e "
      CREATE USER IF NOT EXISTS '#{new_resource.username}'@'#{new_resource.host}'
      IDENTIFIED BY '#{new_resource.password}';
      "
    SQL
    sensitive true
  end

  # Grant privileges
  grant_sql = if new_resource.grant_option
                "GRANT #{new_resource.privileges.join(', ')} ON #{new_resource.database}.* TO '#{new_resource.username}'@'#{new_resource.host}' WITH GRANT OPTION;"
              else
                "GRANT #{new_resource.privileges.join(', ')} ON #{new_resource.database}.* TO '#{new_resource.username}'@'#{new_resource.host}';"
              end

  execute "grant-privileges-#{new_resource.username}" do
    command <<~SQL
      mysql -h #{new_resource.database_host} -P #{new_resource.database_port} \
            -u #{new_resource.admin_user} -p#{new_resource.admin_password} -e "
      #{grant_sql}
      FLUSH PRIVILEGES;
      "
    SQL
    sensitive true
  end
end

action :drop do
  execute "drop-mysql-user-#{new_resource.username}" do
    command <<~SQL
      mysql -h #{new_resource.database_host} -P #{new_resource.database_port} \
            -u #{new_resource.admin_user} -p#{new_resource.admin_password} -e "
      DROP USER IF EXISTS '#{new_resource.username}'@'#{new_resource.host}';
      FLUSH PRIVILEGES;
      "
    SQL
    sensitive true
  end
end
