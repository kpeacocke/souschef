# MySQL default attributes
default['mysql']['version'] = '8.0'
default['mysql']['service_name'] = 'mysql'
default['mysql']['data_dir'] = '/var/lib/mysql'
default['mysql']['conf_dir'] = '/etc/mysql'
default['mysql']['conf_file'] = "#{node['mysql']['conf_dir']}/my.cnf"
default['mysql']['socket'] = '/var/run/mysqld/mysqld.sock'
default['mysql']['pid_file'] = '/var/run/mysqld/mysqld.pid'
default['mysql']['port'] = 3306
default['mysql']['bind_address'] = '127.0.0.1'

# Root credentials - would use Chef Vault in production
default['mysql']['root_password'] = 'changeme'
default['mysql']['debian_password'] = 'changeme'

# InnoDB settings
default['mysql']['innodb_buffer_pool_size'] = '256M'
default['mysql']['innodb_log_file_size'] = '64M'
default['mysql']['innodb_file_per_table'] = 1
default['mysql']['innodb_flush_log_at_trx_commit'] = 1
default['mysql']['innodb_flush_method'] = 'O_DIRECT'

# Connection settings
default['mysql']['max_connections'] = 151
default['mysql']['max_allowed_packet'] = '16M'
default['mysql']['thread_cache_size'] = 8
default['mysql']['query_cache_size'] = '16M'
default['mysql']['query_cache_limit'] = '1M'

# Logging
default['mysql']['log_error'] = '/var/log/mysql/error.log'
default['mysql']['slow_query_log'] = 1
default['mysql']['slow_query_log_file'] = '/var/log/mysql/slow.log'
default['mysql']['long_query_time'] = 2

# Binary logging for replication
default['mysql']['log_bin'] = '/var/log/mysql/mysql-bin.log'
default['mysql']['expire_logs_days'] = 10
default['mysql']['max_binlog_size'] = '100M'
default['mysql']['server_id'] = 1
