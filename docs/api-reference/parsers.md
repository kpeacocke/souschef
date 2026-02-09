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

## See Also

- **[Server API](server.md)** - MCP server using parsers
- **[Converters API](converters.md)** - Convert parsed data
- **[Core Utilities](../api-reference/core.md)** - Shared utilities
- **[Examples](../user-guide/examples.md)** - Real-world parsing examples
