# SousChef: Multi-Platform to Ansible Migration + Ansible Upgrade Planning

Transform Chef, SaltStack, Puppet, PowerShell, and Bash automation to Ansible, and plan Ansible version upgrades. Works with any AI assistant via MCP (Model Context Protocol)—Claude, GPT-4, GitHub Copilot, Red Hat AI, local models, and more.

**Quick Facts:** MIT License | Python 3.10+ | 95 MCP Tools | 91% Test Coverage

[![GitHub release](https://img.shields.io/github/release/kpeacocke/souschef)](https://github.com/kpeacocke/souschef/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-green.svg)](htmlcov/index.html)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=kpeacocke_souschef&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=kpeacocke_souschef)

---
***Warning***
I did not hand craft 100k lines of code in two days while doing my actual day job (which, for the record, isn’t this). A lot of this is AI generated. Architected, hand edited, and personally sworn at yes, but the heavy hand of AI is all over this repo.

I’ve pushed it to include a *lot* of tests, and I run it through its paces before pushing, but some things may break, or may have always been broken. If you find something, raise it and I’ll fix it.

A fair bit of this relies on mocked Chef/AWX/AAP APIs because *shockingly* I don’t have a fleet of enterprise grade installs with enterprise grade data sitting around to test against. Buyer beware (doubly so, since you didn’t actually buy anything).

---

## What It Does

**Chef-to-Ansible Migration** — Convert cookbooks, recipes, custom resources, data bags, and Habitat plans to Ansible playbooks, roles, and containers. Supports infrastructure, applications, and day-2 operations.

**SaltStack-to-Ansible Migration** — Convert Salt states, pillars, and top.sls targeting to Ansible roles, variable files, Ansible Vault, and INI inventory. Assess complexity, generate phased migration plans, and produce executive reports.

**Puppet to Ansible Migration** — Convert Puppet manifests and module directories to Ansible playbooks using idiomatic `ansible.builtin` modules. Recognises 14 Puppet resource types; maps 10 to Ansible modules with AI-assisted conversion for complex constructs.

**PowerShell to Ansible Migration** — Convert Windows PowerShell provisioning scripts to idiomatic `ansible.windows` playbooks, roles, WinRM inventories, and AWX/AAP job templates.

**Bash Script Migration** — Convert provisioning Bash scripts to Ansible playbooks and roles with quality scoring, sensitive data detection, and AAP readiness hints.

**Ansible Upgrade Planning** — Assess compatibility, plan version upgrades, validate collections, identify breaking changes, and generate testing strategies.

## Installation & Setup

```bash
# Install from PyPI
pip install mcp-souschef

# Configure your MCP client (Claude Desktop example)
cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Restart your AI assistant and start using
# Ask: "What Chef migration tools are available?"
```

**Other MCP clients:** See [config/CONFIGURATION.md](config/CONFIGURATION.md) for VS Code Copilot, custom setups, and Docker deployment.

## Key Features

- **95 MCP tools** for Chef migration, SaltStack migration, Puppet migration, PowerShell migration, Bash script migration, and Ansible upgrades
- **Web UI** with interactive migration planner and visualisation (including Salt, Puppet, PowerShell, and Bash tabs)
- **CLI** for automation and CI/CD integration
- **Production-ready** with 91% test coverage and comprehensive validation
- **Model-agnostic** — works with any AI assistant supporting MCP
- **Chef Server ingestion** with dependency closure and offline bundle export

### Common Use Cases

**Chef Migration:**
- Convert cookbooks to Ansible playbooks and roles
- Migrate Chef Habitat apps to Docker containers
- Transform data bags to Ansible Vault
- Generate AWX/AAP job templates and workflows
- Convert InSpec tests to Ansible validation tasks
- Fetch cookbooks from Chef Server with run_list or policy selection

**SaltStack Migration:**
- Parse SLS state files and extract states, pillars, and grain references
- Convert Salt states to Ansible playbooks and role task files
- Migrate pillar data to Ansible `group_vars/` and Ansible Vault
- Generate Ansible inventory from `top.sls` targeting rules
- Batch-convert a full Salt state tree to an Ansible roles structure
- Assess migration complexity and generate phased migration plans

**Puppet Migration:**
- Convert Puppet manifests (`.pp`) and module directories to Ansible playbooks
- Recognise 14 Puppet resource types; map 10 to idiomatic `ansible.builtin` modules (`package`, `service`, `file`, `user`, `group`, `exec`, `cron`, `host`, `mount`, `ssh_authorized_key`)
- Warn about unsupported constructs (Hiera lookups, exported resources, `create_resources`) with manual-review guidance
- AI-assisted conversion for complex Puppet DSL that cannot be mapped automatically
- Convert individual Puppet resource declarations to standalone Ansible tasks

**PowerShell Migration:**
- Convert Windows PowerShell provisioning scripts to idiomatic Ansible playbooks
- Generate full Ansible roles with WinRM inventory and `group_vars`
- Map 28+ PowerShell patterns to `ansible.windows.*`, `community.windows.*`, `chocolatey.chocolatey.*`
- Generate AWX/AAP Windows job templates with WinRM credentials
- Analyse migration fidelity (0–100 %) with actionable recommendations
- Create complete `requirements.yml` for required Windows collections

**Bash Script Migration:**
- Convert provisioning Bash scripts to idiomatic Ansible playbooks
- Generate full Ansible roles from Bash scripts (tasks, handlers, defaults, meta)
- Detect and flag hardcoded secrets with ansible-vault guidance
- Identify CM escape calls (Salt, Puppet, Chef) embedded in Bash
- Get AAP-ready job template hints with Execution Environment recommendations
- Score migration quality (A–F) with ranked improvement suggestions

**Ansible Upgrades:**
- Assess Python and Ansible version compatibility
- Plan upgrades with breaking change analysis
- Validate collection compatibility
- Generate testing strategies
- Track end-of-life dates

**Both Infrastructure & Applications:**
- Infrastructure provisioning and configuration
- Application deployment automation
- Day-2 operations (backups, scaling, updates)
- CI/CD pipeline migration
- Multi-cloud automation

### Command-Line Examples

```bash
# Chef migration
souschef-cli recipe /path/to/recipe.rb
souschef-cli template /path/to/template.erb
souschef-cli convert package nginx --action install

# SaltStack migration
souschef-cli salt assess /srv/salt/states/
souschef-cli salt convert /srv/salt/states/webserver/init.sls
souschef-cli salt inventory /srv/salt/top.sls
souschef-cli salt batch-convert /srv/salt/states/ --output-dir ./ansible-roles/

# PowerShell migration
souschef-cli powershell-parse scripts/setup.ps1
souschef-cli powershell-convert scripts/setup.ps1 --output playbook.yml
souschef-cli powershell-role scripts/setup.ps1 --output-dir ./ansible-role

# Puppet migration
souschef-cli puppet parse manifests/site.pp
souschef-cli puppet convert manifests/site.pp --output playbook.yml
souschef-cli puppet convert-module modules/myapp --output-dir ./ansible-role

# Bash script migration
souschef bash parse scripts/bootstrap.sh
souschef bash convert scripts/deploy.sh --output playbook.yml
souschef bash role scripts/setup.sh --role-name myapp --output-dir ./roles

# Ansible upgrades
souschef ansible assess --environment-path /path/to/ansible
souschef ansible plan --current 2.9 --target 2.17
souschef ansible validate-collections --requirements-file requirements.yml

# Web UI
souschef ui  # Launch interactive dashboard
```

## Documentation

### Start Here

- **[Quick Start Guide](docs/getting-started/quick-start.md)** — Get running in 5 minutes
- **[Production Safety](docs/migration-guide/safety-and-validation.md)** — Validate migrations before deploying ⚠️
- **[User Guide](docs/user-guide/mcp-tools.md)** — All 95 tools explained with examples
- **[Chef Migration Guide](docs/migration-guide/overview.md)** — Step-by-step Chef-to-Ansible migration process
- **[Salt Migration Guide](docs/migration-guide/salt-migration.md)** — Step-by-step SaltStack-to-Ansible migration process
- **[Puppet Migration Guide](docs/migration-guide/puppet-migration.md)** — Puppet to Ansible conversion
- **[PowerShell Migration Guide](docs/migration-guide/powershell-migration.md)** — PowerShell to Windows Ansible conversion
- **[Ansible Upgrades](docs/user-guide/ansible-upgrades.md)** — Version upgrade planning workflows

### Reference

- **[API Documentation](docs/api-reference/)** — Complete technical reference
- **[Architecture Guide](docs/ARCHITECTURE.md)** — Code structure and design decisions
- **[Contributing Guide](CONTRIBUTING.md)** — Development standards and workflow
- **[Security Policy](SECURITY.md)** — Vulnerability reporting and security features
- **[Changelog](CHANGELOG.md)** — Complete release history

## Recent Updates

**v6.0.0** — v2 core foundation with enhanced migration capabilities

**v5.1.4** — Modular architecture, 91% test coverage, full type safety, production-ready

**v5.0.0** — Complete Ansible upgrade planning with version matrices and EOL tracking

## Contributing

```bash
# Development setup
git clone https://github.com/kpeacocke/souschef.git && cd souschef
poetry install
poetry run pytest           # Run tests
poetry run ruff check .     # Lint
poetry run mypy souschef    # Type check
```

**Standards:** Zero warnings policy, type hints required, 90%+ test coverage, Australian English spelling.

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete guidelines.

## Support

- **Issues:** [GitHub Issues](https://github.com/kpeacocke/souschef/issues)
- **Discussions:** [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- **Security:** See [SECURITY.md](SECURITY.md)

## License

MIT License — see [LICENSE](LICENSE) for details.
