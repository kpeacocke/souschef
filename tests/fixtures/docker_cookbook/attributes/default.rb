# Docker default attributes - Chef 17+
default['docker']['version'] = '24.0'
default['docker']['install_method'] = 'repository'
default['docker']['repo_url'] = 'https://download.docker.com/linux'

# Docker daemon configuration
default['docker']['daemon']['log-driver'] = 'json-file'
default['docker']['daemon']['log-opts'] = {
  'max-size' => '10m',
  'max-file' => '3'
}
default['docker']['daemon']['storage-driver'] = 'overlay2'
default['docker']['daemon']['userland-proxy'] = false
default['docker']['daemon']['default-address-pools'] = [
  {
    'base' => '172.20.0.0/16',
    'size' => 24
  }
]

# Docker Compose
default['docker']['compose']['version'] = '2.23.0'
default['docker']['compose']['install_method'] = 'binary'

# User management
default['docker']['users'] = []

# Registry configuration
default['docker']['registry']['mirrors'] = []
default['docker']['registry']['insecure-registries'] = []
