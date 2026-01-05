# Node.js default attributes - Chef 16+ unified mode patterns
default['nodejs']['version'] = '18.x'
default['nodejs']['install_method'] = 'binary'
default['nodejs']['binary_checksum'] = nil
default['nodejs']['npm']['version'] = nil # nil uses npm bundled with node
default['nodejs']['npm_packages'] = []

# Repository settings for package installation
default['nodejs']['repo']['url'] = "https://deb.nodesource.com/node_#{node['nodejs']['version']}"
default['nodejs']['repo']['key'] = 'https://deb.nodesource.com/gpgkey/nodesource.gpg.key'

# Application defaults
default['nodejs']['app']['user'] = 'nodejs'
default['nodejs']['app']['group'] = 'nodejs'
default['nodejs']['app']['dir'] = '/opt/nodejs'
default['nodejs']['app']['environment'] = {
  'NODE_ENV' => 'production'
}

# PM2 process manager settings
default['nodejs']['pm2']['enabled'] = true
default['nodejs']['pm2']['max_memory_restart'] = '1G'
default['nodejs']['pm2']['instances'] = 'max'
default['nodejs']['pm2']['exec_mode'] = 'cluster'
