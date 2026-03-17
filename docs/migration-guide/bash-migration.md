# Bash to Ansible Migration Guide

This guide covers migrating provisioning-style Bash scripts to Ansible using SousChef.

## Overview

SousChef supports end-to-end Bash migration workflows for scripts that configure Linux hosts and application runtimes. It provides:

- Script parsing with operation categorisation and confidence scoring
- Playbook conversion with quality scoring and shell fallback visibility
- Role generation with a full role layout suitable for CI/CD
- Detection of sensitive values with vault-oriented guidance
- AAP readiness hints for job template and execution environment setup

If you are running a broader migration programme, use this guide with the shared migration phases in [Migration Overview](overview.md).

## Supported Workflows

### Parse Bash scripts

Use parsing first to understand what will map cleanly to Ansible and what will require manual review.

- Package installs and upgrades
- Service enable/start/restart operations
- File writes and file permission operations
- Downloads, archives, and Git operations
- User/group and cron operations
- Firewall and hostname operations
- Shell variable extraction and sensitive data detection

### Convert to playbook

Generate an Ansible playbook that maps directly supported operations to idiomatic modules and isolates unsupported lines into explicit shell fallback tasks.

### Generate role

Create a reusable role structure including task files, handlers, defaults, metadata, and role documentation.

## MCP Tools

SousChef exposes three Bash migration MCP tools:

- `parse_bash_script`
- `convert_bash_to_ansible`
- `generate_ansible_role_from_bash`

See [MCP Tools Reference](../user-guide/mcp-tools.md#bash-script-migration) for detailed parameter and output documentation.

## CLI Examples

Use the `souschef` command group for Bash migration.

```bash
# Parse a script and inspect detected operations
souschef bash parse scripts/bootstrap.sh

# Convert to a playbook
souschef bash convert scripts/bootstrap.sh --output playbook.yml

# Generate a role
souschef bash role scripts/bootstrap.sh --role-name web_bootstrap --output-dir ./roles
```

## UI Workflow

The web interface provides a dedicated **Bash Script Migration** page where you can:

- Paste script content or upload a `.sh`/`.bash` file
- Analyse detected operations and confidence
- Review shell fallbacks and sensitive data warnings
- Convert to a playbook or generate a role
- Download generated artefacts

See [UI Guide](../user-guide/ui.md#bash-script-migration-page) for the page-level walkthrough.

## Recommended Migration Process

1. Parse the script and review operation coverage.
2. Resolve sensitive value handling before conversion (for example, switch to Ansible Vault variables).
3. Convert to a playbook and inspect shell fallback tasks.
4. Refactor fallback tasks into native modules where practical.
5. Generate a role for reusable scripts used across environments.
6. Validate with syntax checks and dry runs before production rollout.

## Validation Checklist

Before production use:

- Run `ansible-playbook --syntax-check` on generated playbooks
- Run with `--check` against a test inventory
- Confirm idempotency by running the playbook at least twice
- Replace hardcoded secrets with vault-encrypted variables
- Reduce shell fallback tasks where module alternatives exist

## Troubleshooting

### Too many shell fallback tasks

Cause: Script includes compound shell logic or niche commands without direct module mappings.

Action:

- Break large script blocks into discrete operations
- Replace shell package/service/file commands with native Ansible modules
- Re-run conversion and compare quality score improvements

### Sensitive value warnings

Cause: Script contains inline secrets or key material.

Action:

- Move secret values to encrypted variable files
- Reference values through vault variables in the generated playbook/role

### Low quality score

Cause: High fallback ratio, non-idempotent commands, or opaque inline scripting.

Action:

- Refactor script commands into declarative module equivalents
- Add explicit idempotency guards where shell tasks remain necessary

## Related Guides

- [Migration Overview](overview.md)
- [Conversion Guide](conversion.md)
- [Safety and Validation](safety-and-validation.md)
- [MCP Tools Reference](../user-guide/mcp-tools.md#bash-script-migration)
- [CLI Usage](../user-guide/cli-usage.md)

## Reviewer Note

If this page is newly introduced in a branch, `mkdocs build --strict` may show an informational line that the page has no git logs yet. This is expected before the file is committed and does not indicate a broken documentation link or build failure.
