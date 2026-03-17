# Converters API

Multi-platform-to-Ansible conversion modules for playbooks, resources, scripts, and templates.

## Overview

The `souschef.converters` package transforms parsed source artefacts into Ansible equivalents. Converters maintain logic and intent while adapting to Ansible idioms.

---

## Converter Modules

The following converters are available:

- **Playbook Converter** (`souschef.converters.playbook`) - Convert recipes to playbooks
- **Resource Converter** (`souschef.converters.resource`) - Convert Chef resources to Ansible tasks
- **Habitat Converter** (`souschef.converters.habitat`) - Convert Habitat plans to Docker
- **PowerShell Converter** (`souschef.converters.powershell`) - Convert PowerShell scripts to Windows Ansible tasks
- **PowerShell Generators** (`souschef.generators.powershell`) - Generate enterprise Windows automation artefacts
- **Bash-to-Ansible Converter** (`souschef.converters.bash_to_ansible`) - Convert Bash scripts to Ansible playbooks or roles, with quality scoring and AAP hints

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

---

## PowerShell Converter

**Module:** `souschef.converters.powershell`

Transforms parsed PowerShell action IR into idiomatic Ansible tasks using `ansible.windows.*`, `community.windows.*`, and `chocolatey.chocolatey.*` collection modules. Maintains idempotency guarantees by mapping each action type to the appropriate Ansible module with correct state parameters.

### Action Type to Ansible Module Mapping

| Action Type | Ansible Module |
|-------------|---------------|
| `windows_feature_install` | `ansible.windows.win_feature` |
| `windows_feature_remove` | `ansible.windows.win_feature` |
| `windows_optional_feature_enable` | `ansible.windows.win_optional_feature` |
| `windows_optional_feature_disable` | `ansible.windows.win_optional_feature` |
| `windows_service_start` | `ansible.windows.win_service` |
| `windows_service_stop` | `ansible.windows.win_service` |
| `windows_service_configure` | `ansible.windows.win_service` |
| `windows_service_create` | `ansible.windows.win_service` |
| `registry_set` | `ansible.windows.win_regedit` |
| `registry_create_key` | `ansible.windows.win_regedit` |
| `registry_remove_key` | `ansible.windows.win_regedit` |
| `file_copy` | `ansible.windows.win_copy` |
| `directory_create` | `ansible.windows.win_file` |
| `file_remove` | `ansible.windows.win_file` |
| `file_write` | `ansible.windows.win_copy` |
| `msi_install` | `ansible.windows.win_package` |
| `chocolatey_install` | `chocolatey.chocolatey.win_chocolatey` |
| `chocolatey_uninstall` | `chocolatey.chocolatey.win_chocolatey` |
| `user_create` | `ansible.windows.win_user` |
| `user_modify` | `ansible.windows.win_user` |
| `user_remove` | `ansible.windows.win_user` |
| `group_member_add` | `ansible.windows.win_group_membership` |
| `group_member_remove` | `ansible.windows.win_group_membership` |
| `firewall_rule_create` | `ansible.windows.win_firewall_rule` |
| `firewall_rule_enable` | `ansible.windows.win_firewall_rule` |
| `firewall_rule_disable` | `ansible.windows.win_firewall_rule` |
| `firewall_rule_remove` | `ansible.windows.win_firewall_rule` |
| `scheduled_task_register` | `community.windows.win_scheduled_task` |
| `scheduled_task_unregister` | `community.windows.win_scheduled_task` |
| `environment_set` | `ansible.windows.win_environment` |
| `psmodule_install` | `community.windows.win_psmodule` |
| `certificate_import` | `community.windows.win_certificate_store` |
| `winrm_enable` | `ansible.windows.win_shell` |
| `iis_website_create` | `community.windows.win_iis_website` |
| `dns_client_set` | `community.windows.win_dns_client` |
| `acl_set` | `ansible.windows.win_acl` |
| `win_shell` | `ansible.windows.win_shell` (fallback) |

### Python Usage

```python
from souschef.converters.powershell import (
    convert_powershell_to_ansible,
    convert_powershell_content_to_ansible,
)
import json

# Convert from file path
result_json = convert_powershell_to_ansible(
    "/path/to/setup.ps1",
    playbook_name="windows_setup",
    hosts="windows_servers",
)
result = json.loads(result_json)

print(result["playbook_yaml"])
print(f"Tasks: {result['tasks_generated']}")
print(f"Fallbacks: {result['win_shell_fallbacks']}")

# Convert from inline content
script = "Install-WindowsFeature Web-Server -IncludeManagementTools"
result_json = convert_powershell_content_to_ansible(
    script,
    playbook_name="iis_setup",
    hosts="windows",
)
```

### Return Structure

```python
{
    "status": "success",
    "playbook_yaml": "---\n- name: windows_setup\n  hosts: windows_servers\n  ...",
    "tasks_generated": 12,
    "win_shell_fallbacks": 2,
    "warnings": [
        "Line 42: Unrecognised pattern — falling back to win_shell"
    ],
    "source": "/absolute/path/to/setup.ps1"
}
```

---

## PowerShell Generators

**Module:** `souschef.generators.powershell`

Generates enterprise Windows Ansible artefacts from parsed PowerShell IR. All generators accept the parsed IR dict returned by `parse_powershell_script` / `parse_powershell_content`.

### `generate_windows_inventory`

Generates a WinRM-ready INI-format Ansible inventory.

```python
from souschef.generators.powershell import generate_windows_inventory

inventory = generate_windows_inventory(
    hosts=["win01.example.com", "win02.example.com"],
    winrm_port=5986,
    use_ssl=True,
    validate_certs=False,
)
# Returns INI string ready to save as inventory/hosts
```

### `generate_windows_group_vars`

Generates `group_vars/windows.yml` with WinRM connection variables.

```python
from souschef.generators.powershell import generate_windows_group_vars

group_vars = generate_windows_group_vars(winrm_port=5986, use_ssl=True)
# Returns YAML string for group_vars/windows.yml
```

### `generate_ansible_requirements`

Generates `requirements.yml` with required Ansible collections.

```python
from souschef.generators.powershell import generate_ansible_requirements
import json

# Tailored to a specific parsed script
parsed_ir = json.loads(parse_powershell_script("/path/to/setup.ps1"))
requirements = generate_ansible_requirements(parsed_ir)

# All Windows collections (no IR provided)
requirements = generate_ansible_requirements(None)
# Returns YAML string for requirements.yml
```

### `generate_powershell_role_structure`

Generates a complete Ansible role skeleton with all supporting files.

```python
from souschef.generators.powershell import generate_powershell_role_structure
import json

parsed_ir = json.loads(parse_powershell_script("/path/to/setup.ps1"))
files = generate_powershell_role_structure(
    parsed_ir,
    role_name="iis_server",
    playbook_name="site",
    hosts="windows_servers",
)
# Returns dict mapping relative_path -> file_content
# e.g. {"roles/iis_server/tasks/main.yml": "---\n- name: ...", ...}
```

### `generate_powershell_awx_job_template`

Generates an AWX/AAP-compatible job template JSON with optional survey spec.

```python
from souschef.generators.powershell import generate_powershell_awx_job_template
import json

parsed_ir = json.loads(parse_powershell_script("/path/to/setup.ps1"))
result = generate_powershell_awx_job_template(
    parsed_ir,
    job_template_name="Setup IIS Web Server",
    playbook="site.yml",
    inventory="windows-inventory",
    project="windows-migration-project",
    credential="iis-winrm-credential",
    environment="production",
    include_survey=True,
)
# Returns formatted text block with JSON, CLI command, and action summary
```

### `analyze_powershell_migration_fidelity`

Analyses migration fidelity and produces actionable recommendations.

```python
from souschef.generators.powershell import analyze_powershell_migration_fidelity
import json

parsed_ir = json.loads(parse_powershell_script("/path/to/setup.ps1"))
report = json.loads(analyze_powershell_migration_fidelity(parsed_ir))

print(f"Fidelity score: {report['fidelity_score']}%")
print(f"Automated: {report['automated_actions']} / {report['total_actions']}")
for rec in report["recommendations"]:
    print(f"  - {rec}")
```

---

## Testing Converters

See test suite for converter testing:

- **Unit tests**: [tests/unit/test_server.py](https://github.com/kpeacocke/souschef/blob/main/tests/unit/test_server.py)
- **Integration tests**: [tests/integration/test_integration.py](https://github.com/kpeacocke/souschef/blob/main/tests/integration/test_integration.py)
- **Accuracy tests**: [tests/integration/test_integration_accuracy.py](https://github.com/kpeacocke/souschef/blob/main/tests/integration/test_integration_accuracy.py)

---

## See Also

- **[Server API](server.md)** - MCP server using converters
- **[Parsers API](parsers.md)** - Parse Chef artifacts first
- **[Conversion Guide](../migration-guide/conversion.md)** - Conversion techniques
- **[PowerShell Migration Guide](../migration-guide/powershell-migration.md)** - End-to-end PowerShell migration
- **[Examples](../user-guide/examples.md)** - Real-world conversions
