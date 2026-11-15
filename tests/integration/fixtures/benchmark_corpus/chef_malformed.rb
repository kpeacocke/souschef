package 'nginx' do
  action :install
  notifies :restart, 'service[nginx]'
