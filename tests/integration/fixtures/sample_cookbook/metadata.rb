name 'nginx'
maintainer 'Chef Software, Inc.'
maintainer_email 'cookbooks@chef.io'
license 'Apache-2.0'
description 'Installs and configures nginx'
version '12.0.0'

depends 'logrotate', '>= 2.0.0'
depends 'systemd', '>= 5.0.0'

supports 'ubuntu'
supports 'debian'
supports 'centos'
supports 'redhat'
