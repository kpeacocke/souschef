#
# Cookbook:: database
# Attributes:: default
#

# PostgreSQL version
default['postgresql']['version'] = '14'

# Connection settings
default['postgresql']['config']['listen_addresses'] = 'localhost'
default['postgresql']['config']['port'] = 5432
default['postgresql']['config']['max_connections'] = 100
default['postgresql']['config']['shared_buffers'] = '256MB'

# Performance tuning
default['postgresql']['config']['effective_cache_size'] = '1GB'
default['postgresql']['config']['work_mem'] = '16MB'
default['postgresql']['config']['maintenance_work_mem'] = '128MB'

# Logging
default['postgresql']['config']['logging_collector'] = 'on'
default['postgresql']['config']['log_directory'] = 'pg_log'
default['postgresql']['config']['log_filename'] = 'postgresql-%Y-%m-%d_%H%M%S.log'

# Replication
default['postgresql']['config']['wal_level'] = 'replica'
default['postgresql']['config']['max_wal_senders'] = 3

# Database setup
default['postgresql']['databases'] = {
  'app_production' => {
    'owner' => 'app_user',
    'encoding' => 'UTF8',
    'template' => 'template0',
    'locale' => 'en_US.UTF-8'
  }
}

# Users
default['postgresql']['users'] = {
  'app_user' => {
    'password' => 'changeme',
    'superuser' => false,
    'createdb' => true,
    'createrole' => false
  }
}

# Backup settings
default['postgresql']['backup']['enabled'] = true
default['postgresql']['backup']['dir'] = '/var/backups/postgresql'
default['postgresql']['backup']['retention_days'] = 7
