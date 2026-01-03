# Test recipe with guards and notifications
package 'nginx' do
  version '1.18.0-0ubuntu1'
  action :install
  only_if 'test -f /etc/debian_version'
end

service 'nginx' do
  action [:enable, :start]
  not_if do
    File.exist?('/tmp/nginx.disabled')
  end
end

template '/etc/nginx/nginx.conf' do
  source 'nginx.conf.erb'
  mode '0644'
  only_if 'systemctl is-active nginx'
  notifies :reload, 'service[nginx]', :delayed
end

file '/var/log/nginx/access.log' do
  owner 'www-data'
  group 'www-data'
  mode '0640'
  not_if 'test -f /var/log/nginx/access.log'
  action :create
end

execute 'test-nginx-config' do
  command 'nginx -t'
  action :nothing
  only_if do
    system('which nginx')
  end
  subscribes :run, 'template[/etc/nginx/nginx.conf]', :immediately
end
