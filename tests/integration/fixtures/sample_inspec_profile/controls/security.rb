control 'security-baseline' do
  title 'Basic Security Configuration'
  desc 'Validates basic security settings for web server'
  impact 0.9

  describe user('www-data') do
    it { should exist }
    its('shell') { should eq '/usr/sbin/nologin' }
    its('home') { should eq '/var/www' }
  end

  describe group('www-data') do
    it { should exist }
  end

  describe file('/etc/nginx/sites-enabled/default') do
    it { should exist }
    its('content') { should_not match /server_tokens on/ }
  end
end

control 'system-resources' do
  title 'System Resource Validation'
  desc 'Ensures adequate system resources for web server'
  impact 0.7

  describe sys_info do
    its('fqdn') { should_not be_nil }
    its('hostname') { should_not be_nil }
  end

  describe etc_hosts do
    its('params') { should_not be_empty }
  end
end
