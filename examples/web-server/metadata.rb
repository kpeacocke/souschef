name 'web-server'
maintainer 'SousChef Examples'
maintainer_email 'examples@souschef.dev'
license 'Apache-2.0'
description 'Installs and configures nginx web server'
version '1.0.0'

supports 'ubuntu', '>= 18.04'
supports 'debian', '>= 10'
supports 'centos', '>= 7'
supports 'redhat', '>= 7'

depends 'logrotate', '~> 2.2'
depends 'systemd', '~> 3.0'
