# Parsers API

Chef artifact parsing modules for recipes, templates, resources, attributes, and more.

## Overview

The `souschef.parsers` package contains specialized parsers for different Chef artifact types. Each parser extracts structured data from Ruby-based Chef code.

---

## Parser Modules

The following parsers are available:

- **Recipe Parser** (`souschef.parsers.recipe`) - Parse Chef recipes
- **Template Parser** (`souschef.parsers.template`) - Extract ERB template variables
- **Resource Parser** (`souschef.parsers.resource`) - Parse custom resources
- **Attributes Parser** (`souschef.parsers.attributes`) - Parse attribute files
- **Metadata Parser** (`souschef.parsers.metadata`) - Parse cookbook metadata
- **InSpec Parser** (`souschef.parsers.inspec`) - Parse InSpec profiles
- **Habitat Parser** (`souschef.parsers.habitat`) - Parse Habitat plans
- **Ansible Inventory Parser** (`souschef.parsers.ansible_inventory`) - Parse Ansible inventory files and environments (NEW)
- **PowerShell Parser** (`souschef.parsers.powershell`) - Parse PowerShell provisioning scripts
- **Bash Parser** (`souschef.parsers.bash`) - Parse provisioning Bash scripts into a structured IR with 13 operation categories, confidence scores, sensitive data detection, and CM escape detection

For usage examples and patterns, see the [Examples Guide](../user-guide/examples.md).

---

## Common Parsing Patterns

### Ruby AST Parsing

All parsers use regular expressions and Ruby syntax analysis:

```python
import re
from pathlib import Path

class RecipeParser:
    """Parse Chef recipes."""

    RESOURCE_PATTERN = re.compile(
        r'^\s*(\w+)\s+([\'\"]([^'\"]+)[\'\"]|[\w-]+)\s+do',
        re.MULTILINE
    )

    def parse(self, content: str) -> dict:
        """Extract resources from recipe."""
        resources = []
        for match in self.RESOURCE_PATTERN.finditer(content):
            resource_type = match.group(1)
            resource_name = match.group(3) or match.group(2)
            resources.append({
                'type': resource_type,
                'name': resource_name
            })
        return {'resources': resources}
```

### Error Handling

```python
def parse_file(filepath: str) -> dict:
    """Parse file with error handling."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        return parse(content)
    except FileNotFoundError:
        raise ValueError(f"File not found: {filepath}")
    except UnicodeDecodeError:
        raise ValueError(f"Invalid encoding in file: {filepath}")
    except Exception as e:
        raise ValueError(f"Parse error: {e}")
```

---

## Usage Examples

### Recipe Parsing

```python
from souschef.parsers.recipe import parse_recipe_file

# Parse a recipe
result = parse_recipe_file('recipes/default.rb')

# Access parsed data
for resource in result['resources']:
    print(f"{resource['type']}: {resource['name']}")
```

### Template Variable Extraction

```python
from souschef.parsers.template import parse_template_file

# Parse ERB template
result = parse_template_file('templates/config.erb')

# List all variables
for var in result['variables']:
    print(f"Variable: {var}")
```

### Attribute Parsing

```python
from souschef.parsers.attributes import parse_attributes_file

# Parse attributes
result = parse_attributes_file('attributes/default.rb')

# Access attributes
for attr in result['attributes']:
    print(f"{attr['precedence']}['{attr['key']}']
 = {attr['value']}")
```

---

## Parser Performance

### Optimization Tips

1. **Compile Patterns Once**: Compile regex patterns at module level
2. **Stream Large Files**: Use iterators for large files
3. **Cache Results**: Cache parsed results when processing multiple times
4. **Parallel Processing**: Use multiprocessing for batch operations

```python
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

def parse_cookbook_parallel(cookbook_path: str) -> dict:
    """Parse all recipes in parallel."""
    recipes = list(Path(cookbook_path).glob('recipes/*.rb'))

    with ProcessPoolExecutor() as executor:
        results = executor.map(parse_recipe_file, recipes)

    return {'recipes': list(results)}
```

---

## Testing Parsers

See test suite for parser testing examples:

- **Unit tests**: [tests/unit/test_server.py](https://github.com/kpeacocke/souschef/blob/main/tests/unit/test_server.py)
- **Integration tests**: [tests/integration/test_integration.py](https://github.com/kpeacocke/souschef/blob/main/tests/integration/test_integration.py)
- **Property-based tests**: [tests/unit/test_property_based.py](https://github.com/kpeacocke/souschef/blob/main/tests/unit/test_property_based.py)

---

---

## PowerShell Parser

**Module:** `souschef.parsers.powershell`

Parses PowerShell provisioning scripts (`.ps1`) and extracts structured actions for conversion to Ansible tasks. Uses pattern matching against 28+ common Windows provisioning cmdlets to produce a structured intermediate representation.

### Supported Action Types

| Action Type | PowerShell Pattern | Notes |
|-------------|-------------------|-------|
| `windows_feature_install` | `Install-WindowsFeature`, `Add-WindowsFeature` | Includes management tools flag |
| `windows_optional_feature_enable` | `Enable-WindowsOptionalFeature` | Online/offline modes |
| `windows_feature_remove` | `Remove-WindowsFeature`, `Uninstall-WindowsFeature` | |
| `windows_optional_feature_disable` | `Disable-WindowsOptionalFeature` | |
| `windows_service_start` | `Start-Service` | |
| `windows_service_stop` | `Stop-Service` | |
| `windows_service_configure` | `Set-Service -StartupType` | |
| `windows_service_create` | `New-Service` | |
| `registry_set` | `Set-ItemProperty` (HKLM/HKCU) | |
| `registry_create_key` | `New-Item` (registry path) | |
| `registry_remove_key` | `Remove-Item` (registry path) | |
| `file_copy` | `Copy-Item` | |
| `directory_create` | `New-Item -ItemType Directory` | |
| `file_remove` | `Remove-Item` (file/dir) | |
| `file_write` | `Set-Content`, `Add-Content` | |
| `msi_install` | `Start-Process msiexec` | |
| `chocolatey_install` | `choco install` | |
| `chocolatey_uninstall` | `choco uninstall` | |
| `user_create` | `New-LocalUser` | |
| `user_modify` | `Set-LocalUser` | |
| `user_remove` | `Remove-LocalUser` | |
| `group_member_add` | `Add-LocalGroupMember` | |
| `group_member_remove` | `Remove-LocalGroupMember` | |
| `firewall_rule_create` | `New-NetFirewallRule` | |
| `firewall_rule_enable` | `Enable-NetFirewallRule` | |
| `firewall_rule_disable` | `Disable-NetFirewallRule` | |
| `firewall_rule_remove` | `Remove-NetFirewallRule` | |
| `scheduled_task_register` | `Register-ScheduledTask` | |
| `scheduled_task_unregister` | `Unregister-ScheduledTask` | |
| `environment_set` | `[Environment]::SetEnvironmentVariable` | |
| `psmodule_install` | `Install-Module` | |
| `certificate_import` | `Import-Certificate`, `Import-PfxCertificate` | |
| `winrm_enable` | `Enable-PSRemoting`, `winrm quickconfig` | |
| `iis_website_create` | `New-WebSite` | |
| `dns_client_set` | DNS client cmdlets | |
| `acl_set` | `Set-Acl` | |
| `win_shell` | Unrecognised commands | Fallback with warning |

### Python Usage

```python
from souschef.parsers.powershell import parse_powershell_script, parse_powershell_content
import json

# Parse from file path
result_json = parse_powershell_script("/path/to/setup.ps1")
result = json.loads(result_json)

print(f"Actions found: {len(result['actions'])}")
print(f"Warnings: {len(result['warnings'])}")
print(f"Metrics: {result['metrics']}")

for action in result["actions"]:
    print(f"  Line {action['source_line']}: {action['action_type']} (confidence: {action['confidence']})")

# Parse from inline content
script_content = """
Install-WindowsFeature Web-Server -IncludeManagementTools
Set-Service -Name W3SVC -StartupType Automatic
"""
result_json = parse_powershell_content(script_content, source="<inline>")
result = json.loads(result_json)
```

### Return Structure

```python
{
    "source": "/absolute/path/to/setup.ps1",
    "actions": [
        {
            "action_type": "windows_feature_install",
            "params": {
                "feature_name": "Web-Server",
                "include_management_tools": True,
            },
            "confidence": "high",
            "source_line": 1,
            "requires_elevation": True
        }
    ],
    "warnings": [],
    "metrics": {
        "windows_feature_install": 1,
        "windows_service_configure": 1
    }
}
```

---

## See Also

- **[Server API](server.md)** - MCP server using parsers
- **[Converters API](converters.md)** - Convert parsed data
- **[Core Utilities](../api-reference/core.md)** - Shared utilities
- **[Examples](../user-guide/examples.md)** - Real-world parsing examples
