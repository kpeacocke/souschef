# Converters API

Chef-to-Ansible conversion modules for playbooks, resources, and templates.

## Overview

The `souschef.converters` package transforms parsed Chef artifacts into Ansible equivalents. Converters maintain logic and intent while adapting to Ansible idioms.

---

## Converter Modules

The following converters are available:

- **Playbook Converter** (`souschef.converters.playbook`) - Convert recipes to playbooks
- **Resource Converter** (`souschef.converters.resource`) - Convert Chef resources to Ansible tasks
- **Habitat Converter** (`souschef.converters.habitat`) - Convert Habitat plans to Docker

For detailed conversion patterns and examples, see the [Conversion Guide](../migration-guide/conversion.md).

---

## Conversion Patterns

### Resource-to-Task Mapping

```python
def convert_resource_to_task(resource: dict) -> dict:
    """Convert Chef resource to Ansible task.

    Args:
        resource: Parsed Chef resource

    Returns:
        Ansible task dictionary
    """
    task = {
        'name': f"Manage {resource['name']}",
        'ansible.builtin.package': {
            'name': resource['name'],
            'state': 'present' if resource['action'] == 'install' else 'absent'
        }
    }

    # Add guards as when conditions
    if resource.get('guards'):
        task['when'] = convert_guards(resource['guards'])

    return task
```

### Template Transformation

```python
def convert_erb_to_jinja2(erb_content: str) -> str:
    """Convert ERB template to Jinja2.

    Args:
        erb_content: ERB template content

    Returns:
        Jinja2 template content
    """
    # Variable interpolation: <%= @var %> → {{ var }}
    jinja2 = erb_content
    jinja2 = re.sub(r'<%=\s*@(\w+)\s*%>', r'{{ \1 }}', jinja2)

    # Conditionals: <% if @var %> → {% if var %}
    jinja2 = re.sub(r'<%\s*if\s+@(\w+)\s*%>', r'{% if \1 %}', jinja2)
    jinja2 = re.sub(r'<%\s*end\s*%>', r'{% endif %}', jinja2)

    # Loops: <% @items.each do |item| %> → {% for item in items %}
    jinja2 = re.sub(
        r'<%\s*@(\w+)\.each\s+do\s+\|(\w+)\|\s*%>',
        r'{% for \2 in \1 %}',
        jinja2
    )

    return jinja2
```

### Guard Conversion

```python
def convert_guards(guards: list) -> str:
    """Convert Chef guards to Ansible when clause.

    Args:
        guards: List of Chef guard conditions

    Returns:
        Ansible when condition
    """
    conditions = []

    for guard in guards:
        if guard['type'] == 'only_if':
            conditions.append(convert_condition(guard['condition']))
        elif guard['type'] == 'not_if':
            conditions.append(f"not ({convert_condition(guard['condition'])})")

    return ' and '.join(conditions)

def convert_condition(condition: str) -> str:
    """Convert Ruby condition to Ansible."""
    # File existence: File.exist?('/path') → stat_result.stat.exists
    if 'File.exist?' in condition:
        path = re.search(r"File\.exist\?\(['\"](.*?)['\"]\)", condition).group(1)
        return f"stat_{path.replace('/', '_')}.stat.exists"

    # Command success: system('command') → command_result.rc == 0
    if 'system(' in condition:
        return "command_result.rc == 0"

    return condition
```

---

## Usage Examples

### Basic Recipe Conversion

```python
from souschef.parsers.recipe import parse_recipe_file
from souschef.converters.playbook import convert_to_playbook

# Parse recipe
parsed = parse_recipe_file('recipes/webserver.rb')

# Convert to playbook
playbook = convert_to_playbook(parsed)

# Write output
with open('webserver.yml', 'w') as f:
    f.write(playbook)
```

### Custom Resource to Role

```python
from souschef.parsers.resource import parse_custom_resource
from souschef.converters.resource import convert_to_role

# Parse custom resource
resource = parse_custom_resource('resources/app_config.rb')

# Convert to Ansible role
role = convert_to_role(resource)

# Generate role structure
create_role_structure('roles/app_config', role)
```

### Habitat to Docker

```python
from souschef.parsers.habitat import parse_habitat_plan
from souschef.converters.habitat import convert_to_dockerfile

# Parse Habitat plan
plan = parse_habitat_plan('habitat/plan.sh')

# Convert to Dockerfile
dockerfile = convert_to_dockerfile(plan)

# Write Dockerfile
with open('Dockerfile', 'w') as f:
    f.write(dockerfile)
```

---

## Conversion Strategies

### Direct Mapping

For simple, one-to-one conversions:

```python
RESOURCE_MAP = {
    'package': 'ansible.builtin.package',
    'service': 'ansible.builtin.service',
    'file': 'ansible.builtin.file',
    'directory': 'ansible.builtin.file',
    'template': 'ansible.builtin.template',
}

def map_resource(resource_type: str) -> str:
    """Map Chef resource to Ansible module."""
    return RESOURCE_MAP.get(resource_type, 'ansible.builtin.command')
```

### Complex Logic Preservation

For complex conversions requiring multiple tasks:

```python
def convert_complex_resource(resource: dict) -> list[dict]:
    """Convert complex resource to multiple tasks."""
    tasks = []

    # Pre-conditions
    if resource.get('guards'):
        tasks.extend(convert_guard_checks(resource['guards']))

    # Main action
    tasks.append(convert_main_action(resource))

    # Notifications
    if resource.get('notifies'):
        tasks.extend(convert_notifications(resource['notifies']))

    return tasks
```

---

## Validation

### Syntax Validation

```python
import yaml

def validate_playbook_syntax(playbook_yaml: str) -> bool:
    """Validate generated playbook syntax."""
    try:
        yaml.safe_load(playbook_yaml)
        return True
    except yaml.YAMLError as e:
        print(f"YAML syntax error: {e}")
        return False
```

### Semantic Validation

```python
def validate_conversion_logic(chef_resource: dict, ansible_task: dict) -> bool:
    """Validate that logic is preserved."""
    # Check action mapping
    if chef_resource['action'] == 'install':
        assert ansible_task['package']['state'] == 'present'
    elif chef_resource['action'] == 'remove':
        assert ansible_task['package']['state'] == 'absent'

    # Check guards converted to when clauses
    if chef_resource.get('guards'):
        assert 'when' in ansible_task

    return True
```

---

## Testing Converters

See test suite for converter testing:

- **Unit tests**: [tests/test_server.py](https://github.com/kpeacocke/souschef/blob/main/tests/test_server.py)
- **Integration tests**: [tests/test_integration.py](https://github.com/kpeacocke/souschef/blob/main/tests/test_integration.py)
- **Accuracy tests**: [tests/test_integration_accuracy.py](https://github.com/kpeacocke/souschef/blob/main/tests/test_integration_accuracy.py)

---

## See Also

- **[Server API](server.md)** - MCP server using converters
- **[Parsers API](parsers.md)** - Parse Chef artifacts first
- **[Conversion Guide](../migration-guide/conversion.md)** - Conversion techniques
- **[Examples](../user-guide/examples.md)** - Real-world conversions
