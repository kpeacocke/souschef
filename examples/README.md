# SousChef Conversion Examples

This directory contains example Chef cookbooks that demonstrate SousChef's conversion capabilities.

## Available Examples

### 1. web-server - Complete Web Server Setup
A realistic nginx web server cookbook showing:
- Package installation
- Service management
- Template configuration
- File and directory creation
- User and group management
- Conditional logic based on platform
- Custom resource usage

### 2. database - Database Server Configuration
A PostgreSQL database server cookbook demonstrating:
- Complex package dependencies
- Service configuration
- Custom resources for database management
- Attribute-driven configuration
- Guards (only_if, not_if)

### 3. application - Application Deployment
An application deployment cookbook showing:
- Git repository cloning
- Application user setup
- Environment-specific configurations
- Systemd service files
- Custom LWRPs

## Usage

Each example directory contains:
- `metadata.rb` - Cookbook metadata
- `recipes/default.rb` - Main recipe
- `templates/` - ERB templates
- `attributes/` - Default attributes
- `resources/` - Custom resources (if applicable)
- `CONVERSION.md` - Expected Ansible conversion output

## Testing Conversions

You can use these examples to test SousChef's conversion tools:

```python
# Parse the recipe
parse_recipe("examples/web-server/recipes/default.rb")

# Convert individual resources
convert_resource_to_task("package", "nginx", "install")

# Parse templates
parse_template("examples/web-server/templates/default/nginx.conf.erb")

# Parse custom resources
parse_custom_resource("examples/application/resources/app_deploy.rb")
```

## Contributing Examples

When adding new examples:
1. Create a complete, realistic cookbook structure
2. Include a CONVERSION.md showing expected Ansible output
3. Add comments explaining Chef concepts
4. Test all files with SousChef tools
