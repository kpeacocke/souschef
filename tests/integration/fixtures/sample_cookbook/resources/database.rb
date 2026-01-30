# LWRP-style resource for database management
actions :create, :drop, :backup
default_action :create

attribute :db_name, kind_of: String, name_attribute: true
attribute :username, kind_of: String, required: true
attribute :password, kind_of: String, required: true
attribute :host, kind_of: String, default: 'localhost'
attribute :port, kind_of: Integer, default: 5432
attribute :encoding, kind_of: String, default: 'UTF8'
