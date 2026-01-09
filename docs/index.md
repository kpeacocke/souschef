# SousChef Documentation

An AI-powered MCP (Model Context Protocol) server that provides comprehensive Chef-to-Ansible migration capabilities for enterprise infrastructure transformation.

[![PyPI version](https://img.shields.io/pypi/v/mcp-souschef.svg)](https://pypi.org/project/mcp-souschef/)
[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen.svg)](https://github.com/kpeacocke/souschef/tree/main/htmlcov)

## Overview

SousChef is a complete enterprise-grade migration platform with **38 MCP tools** organized across **9 major capability areas** to facilitate Chef-to-Ansible AWX/AAP migrations. From cookbook analysis to deployment pattern conversion, including Chef Habitat to containerized deployments, SousChef provides everything needed for a successful infrastructure automation migration.

## Model Agnostic - Works with Any AI Model

**SousChef works with ANY AI model through the Model Context Protocol (MCP)**. The MCP architecture separates tools from models:

- :material-robot: **Red Hat AI** (Llama, IBM models)
- :material-chat: **Claude** (Anthropic)
- :material-openai: **GPT-4/GPT-3.5** (OpenAI)
- :material-github: **GitHub Copilot** (Microsoft/OpenAI)
- :material-server: **Local Models** (Ollama, llama.cpp, etc.)
- :material-domain: **Custom Enterprise Models**

!!! tip "How it works"
    You choose your AI model provider in your MCP client. SousChef provides the Chef/Ansible expertise through 38 specialized tools. The model calls these tools to help with your migration.

## Core Capabilities

### :material-file-code: Chef Cookbook Analysis & Parsing
Complete cookbook introspection and analysis tools for understanding your Chef infrastructure.

[Learn more about parsing →](user-guide/mcp-tools.md#chef-cookbook-analysis-parsing){ .md-button }

### :material-swap-horizontal: Chef-to-Ansible Conversion Engine
Advanced resource-to-task conversion with intelligent module selection and guard handling.

[Learn more about conversion →](user-guide/mcp-tools.md#chef-to-ansible-conversion-engine){ .md-button }

### :material-cloud: AWX/Ansible Automation Platform Integration
Enterprise AWX/AAP configuration generation with job templates and workflows.

[Learn more about AWX integration →](user-guide/mcp-tools.md#awx-ansible-automation-platform-integration){ .md-button }

### :material-docker: Chef Habitat to Container Conversion
Modernize Habitat applications to containerized deployments with Docker and Compose.

[Learn more about Habitat conversion →](user-guide/mcp-tools.md#chef-habitat-to-container-conversion){ .md-button }

### :material-check-circle: Validation & Testing
Comprehensive validation framework and InSpec integration for ensuring migration accuracy.

[Learn more about validation →](user-guide/mcp-tools.md#conversion-validation-framework){ .md-button }

## Quick Start

Get started with SousChef in minutes:

```bash
# Install from PyPI
pip install mcp-souschef

# Configure your MCP client
cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Start using with your AI assistant
# Ask: "What Chef migration tools are available?"
```

[Get started →](getting-started/installation.md){ .md-button .md-button--primary }

## Enterprise Features

- :material-chart-line: **Migration Assessment & Reporting** - Automated complexity analysis and executive reports
- :material-rocket: **Modern Deployment Patterns** - Blue/green, canary releases, and cloud-native strategies
- :material-key: **Secrets Management** - Secure data bag to Ansible Vault conversion
- :material-speedometer: **Performance Profiling** - Identify bottlenecks and optimize large-scale migrations

## What's Next?

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } __Installation__

    ---

    Install SousChef and configure your MCP client

    [:octicons-arrow-right-24: Get started](getting-started/installation.md)

-   :material-lightning-bolt:{ .lg .middle } __Quick Start__

    ---

    Start migrating Chef cookbooks in minutes

    [:octicons-arrow-right-24: Quick start](getting-started/quick-start.md)

-   :material-book-open-variant:{ .lg .middle } __User Guide__

    ---

    Explore MCP tools and CLI usage

    [:octicons-arrow-right-24: User guide](user-guide/mcp-tools.md)

-   :material-map:{ .lg .middle } __Migration Guide__

    ---

    Plan and execute your Chef-to-Ansible migration

    [:octicons-arrow-right-24: Migration guide](migration-guide/overview.md)

</div>

## Community & Support

- :material-github: **GitHub**: [kpeacocke/souschef](https://github.com/kpeacocke/souschef)
- :material-bug: **Issues**: [Report a bug](https://github.com/kpeacocke/souschef/issues)
- :material-forum: **Discussions**: [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- :material-book: **Wiki**: [Documentation](https://github.com/kpeacocke/souschef/wiki)

---

**SousChef** - *Transforming infrastructure automation, one recipe at a time.* ✨
