control 'simple-test' do
  describe package('vim') do
    it { should be_installed }
  end
end
