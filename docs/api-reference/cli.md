# CLI API

Command-line interface implementation for SousChef.

## Overview

The `souschef.cli` module provides a command-line interface for Chef-to-Ansible conversion using the Click framework. All commands are accessible via the `souschef-cli` entry point.

---

## CLI Commands

See the [CLI Usage Guide](../user-guide/cli-usage.md) for complete documentation of all available commands with examples.

---

## Usage Examples

### Basic Command Usage

```bash
# Parse a recipe
souschef-cli recipe recipes/default.rb

# Convert with JSON output
souschef-cli recipe recipes/default.rb --format json

# Convert to playbook
souschef-cli convert-recipe recipes/default.rb > playbook.yml
```

### Piping Commands

```bash
# Parse and filter
souschef-cli recipe recipes/default.rb | grep "package"

# Convert and validate
souschef-cli convert-recipe recipes/default.rb | ansible-playbook --syntax-check

# Batch processing
find cookbooks/ -name "*.rb" | xargs -I {} souschef-cli recipe {}
```

### Output Formats

```bash
# Text output (default)
souschef-cli recipe recipes/default.rb --format text

# JSON for programmatic use
souschef-cli recipe recipes/default.rb --format json | jq '.resources'

# YAML output
souschef-cli recipe recipes/default.rb --format yaml
```

---

## Click Integration

SousChef uses Click for CLI implementation:

```python
import click
from souschef.parsers.recipe import RecipeParser

@click.command()
@click.argument('recipe_path', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['text', 'json', 'yaml']), default='text')
def recipe(recipe_path: str, format: str) -> None:
    """Parse a Chef recipe."""
    parser = RecipeParser(recipe_path)
    result = parser.parse()
    click.echo(format_output(result, format))
```

Benefits:
- Automatic help generation
- Type validation
- Shell completion support
- Click context management

---

## Error Handling

CLI commands handle errors consistently:

```python
try:
    result = parse_recipe(recipe_path)
    click.echo(result)
except FileNotFoundError:
    click.echo(f"Error: File not found: {recipe_path}", err=True)
    sys.exit(1)
except Exception as e:
    click.echo(f"Error: {e}", err=True)
    sys.exit(1)
```

---

## Shell Completion

Enable shell completion for faster CLI usage:

```bash
# Bash
eval "$(_SOUSCHEF_CLI_COMPLETE=bash_source souschef-cli)"

# Zsh
eval "$(_SOUSCHEF_CLI_COMPLETE=zsh_source souschef-cli)"

# Fish
eval (env _SOUSCHEF_CLI_COMPLETE=fish_source souschef-cli)
```

Add to shell rc file for persistence:

```bash
echo 'eval "$(_SOUSCHEF_CLI_COMPLETE=bash_source souschef-cli)"' >> ~/.bashrc
```

---

## See Also

- **[Server API](server.md)** - MCP server implementation
- **[Parsers API](parsers.md)** - Parsing modules
- **[CLI Usage Guide](../user-guide/cli-usage.md)** - User documentation
- **[Click Documentation](https://click.palletsprojects.com/)** - CLI framework
