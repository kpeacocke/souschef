control 'nginx-package' do
  title 'NGINX Package Installation'
  desc 'Verifies that the NGINX package is installed with correct version'
  impact 1.0

  describe package('nginx') do
    it { should be_installed }
    its('version') { should match /1\.(18|20|22)/ }
  end
end

control 'nginx-service' do
  title 'NGINX Service Configuration'
  desc 'Ensures NGINX service is running and enabled'
  impact 1.0

  describe service('nginx') do
    it { should be_running }
    it { should be_enabled }
  end

  describe port(80) do
    it { should be_listening }
    its('protocols') { should include 'tcp' }
  end
end

control 'nginx-config' do
  title 'NGINX Configuration Files'
  desc 'Validates NGINX configuration file structure and permissions'
  impact 0.8

  describe file('/etc/nginx/nginx.conf') do
    it { should exist }
    it { should be_file }
    its('mode') { should cmp '0644' }
    its('owner') { should eq 'root' }
    its('group') { should eq 'root' }
  end

  describe directory('/var/log/nginx') do
    it { should exist }
    it { should be_directory }
    its('owner') { should eq 'www-data' }
  end
end
