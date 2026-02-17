# SousChef: Chef-to-Ansible Migration & Ansible Upgrade Planning

Transform Chef automation to Ansible and plan Ansible version upgrades. Works with any AI assistant via MCP (Model Context Protocol)—Claude, GPT-4, GitHub Copilot, Red Hat AI, local models, and more.

**Quick Facts:** MIT License | Python 3.10+ | 43 MCP Tools | 91% Test Coverage

[![GitHub release](https://img.shields.io/github/v/release/kpeacocke/souschef)](https://github.com/kpeacocke/souschef/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-green.svg)](htmlcov/index.html)

## What It Does

**Chef-to-Ansible Migration** — Convert cookbooks, recipes, custom resources, data bags, and Habitat plans to Ansible playbooks, roles, and containers. Supports infrastructure, applications, and day-2 operations.

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

- **43 MCP tools** for Chef migration and Ansible upgrades
- **Web UI** with interactive migration planner and visualisation
- **CLI** for automation and CI/CD integration
- **Production-ready** with 91% test coverage and comprehensive validation
- **Model-agnostic** — works with any AI assistant supporting MCP

### Common Use Cases

**Chef Migration:**
- Convert cookbooks to Ansible playbooks and roles
- Migrate Chef Habitat apps to Docker containers
- Transform data bags to Ansible Vault
- Generate AWX/AAP job templates and workflows
- Convert InSpec tests to Ansible validation tasks

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
- **[User Guide](docs/user-guide/mcp-tools.md)** — All 43 tools explained with examples
- **[Migration Guide](docs/migration-guide/overview.md)** — Step-by-step migration process
- **[Ansible Upgrades](docs/user-guide/ansible-upgrades.md)** — Version upgrade planning workflows

### Reference

- **[API Documentation](docs/api-reference/)** — Complete technical reference
- **[Architecture Guide](docs/ARCHITECTURE.md)** — Code structure and design decisions
- **[Contributing Guide](CONTRIBUTING.md)** — Development standards and workflow
- **[Security Policy](SECURITY.md)** — Vulnerability reporting and security features
- **[Changelog](CHANGELOG.md)** — Complete release history

## Recent Updates

**v5.1.4** — Modular architecture, 91% test coverage, full type safety, production-ready

**v5.0.0** — Complete Ansible upgrade planning with version matrices and EOL tracking

**v2.0.0** — Intermediate Representation (IR) layer for multi-tool support

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
