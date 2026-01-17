include_recipe 'nodejs'

nodejs_npm "301" do
  version node['301']['version']
end
