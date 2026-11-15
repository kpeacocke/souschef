# Puppet 8-style facts, Hiera, relationships, and virtual resources.
$worker_count = $facts['processors']['count']
$document_root = lookup('profile::web::document_root', { 'default_value' => '/srv/example' })

package { 'nginx':
  ensure => installed,
}

file { $document_root:
  ensure => directory,
  owner  => 'www-data',
  mode   => '0750',
}

service { 'nginx':
  ensure  => running,
  enable  => true,
  require => Package['nginx'],
}

@user { 'benchmark_deploy':
  ensure => present,
  shell  => '/bin/bash',
}

realize(User['benchmark_deploy'])
