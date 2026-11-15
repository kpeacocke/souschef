# InSpec 4-style control file.
control 'benchmark-package' do
  impact 0.7
  title 'Required web package is installed'
  describe package('nginx') do
    it { should be_installed }
  end
end
