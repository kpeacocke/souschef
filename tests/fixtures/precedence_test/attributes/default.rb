# Test fixture demonstrating Chef attribute precedence
# This file shows how different precedence levels work

# Default attributes (lowest precedence)
default['app']['port'] = 3000
default['app']['host'] = 'localhost'
default['app']['debug'] = false

# Force default (higher than default)
force_default['app']['workers'] = 4

# Normal attributes (middle precedence)
normal['app']['timeout'] = 30
normal['app']['port'] = 8080  # Conflicts with default

# Override attributes
override['app']['workers'] = 8  # Conflicts with force_default
override['app']['log_level'] = 'info'

# Force override (cannot be overridden)
force_override['app']['port'] = 443  # Wins over all other port definitions

# Automatic attributes (highest precedence - set by Ohai)
automatic['app']['hostname'] = 'production-server'
