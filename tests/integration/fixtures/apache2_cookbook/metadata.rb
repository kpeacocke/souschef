# Apache2 cookbook - Based on Chef Supermarket pattern
name 'apache2'
maintainer 'Test User'
maintainer_email 'test@example.com'
license 'Apache-2.0'
description 'Installs and configures Apache2 web server'
version '8.7.1'
chef_version '>= 15.0'

supports 'ubuntu', '>= 18.04'
supports 'debian', '>= 10.0'
supports 'centos', '>= 7.0'
supports 'redhat', '>= 7.0'

depends 'logrotate', '~> 2.2'

issues_url 'https://github.com/example/apache2/issues'
source_url 'https://github.com/example/apache2'
