# SousChef: AI-Powered Chef-to-Ansible Migration & Upgrade Planning

Transform your Chef infrastructure to Ansible. SousChef provides intelligent cookbook analysis, automated conversion, and comprehensive Ansible upgrade planning—all via your favourite AI assistant.

**Status:** Actively maintained | **Version:** 5.1.4 | **Coverage:** 91% | **Python:** 3.10+ | **License:** MIT

[![GitHub release](https://img.shields.io/github/v/release/kpeacocke/souschef)](https://github.com/kpeacocke/souschef/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-green.svg)](htmlcov/index.html)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## What Does SousChef Do?

SousChef helps infrastructure teams migrate from Chef to Ansible and plan Ansible upgrades. It works with any AI assistant (Claude, GPT-4, GitHub Copilot, etc.) to provide expert guidance through MCP tools.

**Two core capabilities:**

1. **Chef-to-Ansible Migration** — Automatically convert cookbooks, recipes, attributes, custom resources, data bags, and Habitat plans to Ansible playbooks, roles, and Docker containers
2. **Ansible Upgrade Planning** — Assess your Ansible environment, identify breaking changes, validate collection compatibility, and create step-by-step upgrade plans

## Quick Start

### Installation

```bash
# From PyPI
pip install mcp-souschef

# Development
git clone https://github.com/kpeacocke/souschef.git
cd souschef
poetry install
```

### Setup Your MCP Client

Use the configuration files in `config/` for Claude Desktop, VS Code Copilot, or other MCP clients:

**Claude Desktop (macOS):**
```bash
cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
# Restart Claude Desktop
```

**VS Code + GitHub Copilot (requires VS Code 1.102+):**
```bash
cp config/vscode-copilot.json ~/.config/Code/User/mcp.json
# Reload VS Code
```

See [config/CONFIGURATION.md](config/CONFIGURATION.md) for platform-specific setup and model provider configurations.

### Start Using SousChef

1. Restart your MCP client
2. Ask: "What Chef migration tools are available?"
3. Begin analysing your cookbooks!

## Documentation Guide

**Choose your next step:**

- **New to SousChef?** Start with [User Guide](docs/user-guide/) — workflows, examples, and best practices
- **Contributing code?** Read [CONTRIBUTING.md](CONTRIBUTING.md) — standards, testing, setup
- **Understanding the code?** See [ARCHITECTURE.md](docs/ARCHITECTURE.md) — module structure, design decisions, decision tree
- **Security concerns?** Review [SECURITY.md](SECURITY.md) — vulnerability disclosure, security features
- **Full API reference?** See [API Reference](docs/api-reference/) — all MCP tools documented
- **Detailed release history?** See [CHANGELOG](CHANGELOG.md)

## What is SousChef?

SousChef is an MCP (Model Context Protocol) server that turns your AI assistant into a Chef-to-Ansible expert. It provides:

- **40+ MCP tools** for cookbook analysis, resource conversion, server integration
- **Web UI** with interactive migration planner and progress tracking
- **CLI** for script automation and CI/CD integration
- **5 Ansible upgrade tools** for version assessment and planning

### Web UI & Command-Line Interface

**Interactive Dashboard:**
```bash
# Launch the visual migration planner
souschef ui
# Visit http://localhost:9999 in your browser
```

**CLI Commands:**
```bash
# Analyse cookbooks and generate migration plans
souschef-cli recipe /path/to/recipe.rb
souschef-cli template /path/to/template.erb
souschef-cli convert package nginx --action install

# Ansible upgrade planning
souschef ansible assess --environment-path /path/to/ansible
souschef ansible plan --current 2.9 --target 2.17
souschef ansible validate-collections --requirements-file requirements.yml
```

See the [User Guide](docs/user-guide/) for comprehensive documentation.

## Core Capabilities

1. **Chef Cookbook Analysis** — Parse metadata, recipes, attributes, custom resources, templates
2. **Chef-to-Ansible Conversion** — Convert resources to tasks, recipes to playbooks, with intelligent module mapping
3. **Chef Server Integration** — Query nodes, extract roles/environments, validate connectivity
4. **Secrets Migration** — Convert data bags to Ansible variables or Vault-encrypted files
5. **Container Migration** — Convert Chef Habitat to production-ready Dockerfiles and docker-compose.yml
6. **Test Conversion** — Transform InSpec controls to Ansible assert tasks or Testinfra tests  
7. **AWX/AAP Integration** — Generate job templates, workflows, dynamic inventory from Chef data
8. **Ansible Upgrades** — Assess environments, plan upgrades, validate collections, breaking change analysis

## Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - Module structure and design decisions
- **[User Guide](docs/user-guide/)** - Comprehensive usage documentation
- **[Migration Guide](docs/migration-guide/)** - Step-by-step migration process
- **[API Reference](docs/api-reference/)** - Detailed tool documentation
- **[Ansible Upgrade Guide](docs/user-guide/ansible-upgrades.md)** - Upgrade planning workflows
- **[Terraform Provider](terraform-provider/README.md)** - Infrastructure-as-code for migrations

## What's New

### v5.1.4 (Current)
Modular architecture with 91% test coverage (3,500+ passing tests). Full type safety with mypy. Zero breaking changes from v5.0.

### v5.0.0
Complete Ansible upgrade system: Version compatibility assessment, EOL tracking, upgrade path planning with breaking change analysis, collection validation, and testing recommendations.

### v2.0.0
Intermediate Representation (IR) layer enables multi-tool support (future: Puppet, SaltStack → Ansible).

For detailed changes, see [CHANGELOG](CHANGELOG.md).

## Development

### Setup

```bash
poetry install
poetry run pytest                    # Run tests
poetry run ruff check .              # Lint
poetry run mypy souschef             # Type check
```

### Quality Standards

- **Zero warnings policy**: All code passes Ruff, mypy, Pylance without disabling checks
- **Type hints required**: Full type annotations in source code
- **Comprehensive tests**: Unit, integration, and property-based tests
- **Australian English**: All documentation uses Australian English spelling

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/kpeacocke/souschef/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- **Security**: See [SECURITY.md](SECURITY.md)

## License

MIT License - see [LICENSE](LICENSE) for details.
