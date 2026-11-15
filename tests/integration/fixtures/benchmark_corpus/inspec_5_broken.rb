# Deliberately incomplete control block.
control 'benchmark-incomplete' do
  describe package('nginx') do
    it { should be_installed }
