# MySQL server recipe - Chef 14+ with custom resources

# Install MySQL server package
package 'mysql-server' do
  action :install
  version node['mysql']['version'] if node['mysql']['version']
end

# Create MySQL directories
[
  node['mysql']['data_dir'],
  node['mysql']['conf_dir'],
  File.dirname(node['mysql']['log_error']),
  File.dirname(node['mysql']['slow_query_log_file']),
  File.dirname(node['mysql']['log_bin'])
].each do |dir|
  directory dir do
    owner 'mysql'
    group 'mysql'
    mode '0755'
    recursive true
    action :create
  end
end

# Generate MySQL configuration
template node['mysql']['conf_file'] do
  source 'my.cnf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    port: node['mysql']['port'],
    bind_address: node['mysql']['bind_address'],
    socket: node['mysql']['socket'],
    data_dir: node['mysql']['data_dir'],
    pid_file: node['mysql']['pid_file'],
    max_connections: node['mysql']['max_connections'],
    max_allowed_packet: node['mysql']['max_allowed_packet'],
    innodb_buffer_pool_size: node['mysql']['innodb_buffer_pool_size'],
    innodb_log_file_size: node['mysql']['innodb_log_file_size'],
    innodb_file_per_table: node['mysql']['innodb_file_per_table'],
    log_error: node['mysql']['log_error'],
    slow_query_log: node['mysql']['slow_query_log'],
    slow_query_log_file: node['mysql']['slow_query_log_file'],
    long_query_time: node['mysql']['long_query_time'],
    log_bin: node['mysql']['log_bin'],
    server_id: node['mysql']['server_id']
  )
  notifies :restart, 'service[mysql]', :delayed
end

# Initialize MySQL data directory if needed
execute 'initialize-mysql' do
  command 'mysqld --initialize-insecure --user=mysql'
  not_if { ::File.exist?("#{node['mysql']['data_dir']}/mysql") }
  notifies :start, 'service[mysql]', :immediately
end

# Manage MySQL service
service 'mysql' do
  service_name node['mysql']['service_name']
  supports status: true, restart: true, reload: true
  action [:enable, :start]
end

# Secure MySQL installation
root_user = node['mysql']['root_user']
execute 'secure-mysql-installation' do
  command <<~MYSQL
    mysql -u #{root_user} <<-EOF
      DELETE FROM mysql.user WHERE User='';
      DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');
      DROP DATABASE IF EXISTS test;
      DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
      ALTER USER 'root'@'localhost' IDENTIFIED BY '#{node['mysql']['root_password']}';
      FLUSH PRIVILEGES;
    EOF
  MYSQL
  only_if "mysql -u #{root_user} -e \"SELECT 1\"", user: root_user
  sensitive true
end

# Create MySQL client configuration for root
template '/root/.my.cnf' do
  source 'root_my.cnf.erb'
  owner 'root'
  group 'root'
  mode '0600'
  variables(
    password: node['mysql']['root_password']
  )
  sensitive true
  only_if { node['mysql']['root_password'] }
end
