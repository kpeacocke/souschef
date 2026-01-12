# ChefSpec unit test example
require 'chefspec'

describe 'sample_cookbook::default' do
  let(:chef_run) { ChefSpec::SoloRunner.new.converge(described_recipe) }

  it 'installs apache2 package' do
    expect(chef_run).to install_package('apache2')
  end

  it 'starts apache2 service' do
    expect(chef_run).to start_service('apache2')
  end
end
