# InSpec 5-style control with several resource types and matchers.
control 'benchmark-web-host' do
  impact 1.0
  title 'Web host baseline'
  describe package('nginx') do
    it { should be_installed }
  end
  describe service('nginx') do
    it { should be_enabled }
    it { should be_running }
  end
  describe port(8080) do
    it { should be_listening }
  end
  describe file('/etc/nginx/nginx.conf') do
    it { should exist }
    its('mode') { should cmp '0640' }
  end
end
