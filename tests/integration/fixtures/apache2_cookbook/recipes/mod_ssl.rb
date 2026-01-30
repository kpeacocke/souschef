# Apache2 SSL module recipe

# Install SSL module
package 'ssl-cert' do
  action :install
end

# Enable SSL module
execute 'enable-ssl-module' do
  command 'a2enmod ssl'
  not_if "test -L #{node['apache']['conf_dir']}/mods-enabled/ssl.load"
  notifies :reload, 'service[apache2]', :delayed
end

# Configure SSL
template "#{node['apache']['conf_dir']}/mods-available/ssl.conf" do
  source 'ssl.conf.erb'
  owner 'root'
  group 'root'
  mode '0644'
  variables(
    ssl_protocols: 'all -SSLv3 -TLSv1 -TLSv1.1',
    ssl_ciphers: 'HIGH:!aNULL:!MD5:!3DES'
  )
  notifies :reload, 'service[apache2]', :delayed
end

# Enable default SSL site only if certificate exists
execute 'enable-default-ssl' do
  command 'a2ensite default-ssl'
  only_if { ::File.exist?('/etc/ssl/certs/ssl-cert-snakeoil.pem') }
  not_if "test -L #{node['apache']['conf_dir']}/sites-enabled/default-ssl.conf"
  notifies :reload, 'service[apache2]', :delayed
end
