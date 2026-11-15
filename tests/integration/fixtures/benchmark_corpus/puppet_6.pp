# Puppet 6-style declarations.
package { 'nginx':
  ensure => installed,
}

service { 'nginx':
  ensure => running,
  enable => true,
}

file { '/var/www/example/index.html':
  ensure  => file,
  content => 'Managed by Puppet benchmark fixture',
  mode    => '0644',
}
