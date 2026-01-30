# Simple custom resource with minimal properties
property :name, String, name_property: true
property :enabled, [true, false], default: true

action :enable do
  log "Enabling #{new_resource.name}"
end

action :disable do
  log "Disabling #{new_resource.name}"
end
