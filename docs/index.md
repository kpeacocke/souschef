# SousChef Documentation

An AI-powered MCP (Model Context Protocol) server that provides comprehensive Chef-to-Ansible migration and Ansible upgrade planning capabilities for enterprise infrastructure and application transformation.

[![PyPI version](https://img.shields.io/pypi/v/mcp-souschef.svg)](https://pypi.org/project/mcp-souschef/)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://github.com/kpeacocke/souschef/tree/main/htmlcov)

## Overview

SousChef is a complete enterprise-grade platform with two major capabilities:

### 1. Chef to Ansible Migration (38 tools)

Complete enterprise-grade migration platform with **38 primary MCP tools** organised across **9 major capability areas** to facilitate Chef-to-Ansible AWX/AAP migrations. From cookbook analysis to deployment pattern conversion, including Chef Habitat to containerised deployments and Chef Server integration, SousChef provides everything needed for a successful infrastructure automation migration.

### 2. Ansible Upgrade Assessment & Planning (5 tools)

Comprehensive Ansible upgrade analysis and planning tools based on official Ansible-Python compatibility matrices:

- **Version Compatibility Assessment** - Validate Ansible and Python version compatibility
- **EOL Status Checking** - Track end-of-life dates and security support
- **Upgrade Path Planning** - Generate detailed upgrade plans with risk assessment
- **Collection Compatibility** - Validate collection versions against target Ansible releases
- **Breaking Change Analysis** - Identify and plan for breaking changes (e.g., 2.9 → 2.10 collections split)
- **Python Upgrade Impact** - Assess Python version upgrade requirements for control and managed nodes
- **Testing Plan Generation** - Generate comprehensive upgrade testing plans

!!! info "About Tool Counts"
    **Complete tool inventory available in source code**

    The MCP server includes primary user-facing tools for Chef-to-Ansible migration and Ansible upgrade planning. This documentation focuses on the primary user-facing tools (38 migration + 5 upgrade) that cover the main capabilities.

    As a user, you'll primarily interact with the documented tools. Your AI assistant may use additional tools automatically when needed, but you don't need to know about them for successful migrations.

    See [api-reference/](api-reference/) and `souschef/server.py` for the complete authoritative list of all MCP tools.

## Model Agnostic - Works with Any AI Model

**SousChef works with ANY AI model through the Model Context Protocol (MCP)**. The MCP architecture separates tools from models:

- :material-robot: **Red Hat AI** (Llama, IBM models)
- :material-chat: **Claude** (Anthropic)
- :material-openai: **GPT-4/GPT-3.5** (OpenAI)
- :material-github: **GitHub Copilot** (Microsoft/OpenAI)
- :material-server: **Local Models** (Ollama, llama.cpp, etc.)
- :material-domain: **Custom Enterprise Models**

!!! tip "How it works"
    You choose your AI model provider in your MCP client. SousChef provides the Chef/Ansible expertise through specialized tools. The model calls these tools to help with your migration and upgrade planning.

## Core Capabilities

### :material-file-code: Chef Cookbook Analysis & Parsing
Complete cookbook introspection and analysis tools for understanding your Chef infrastructure.

[Learn more about parsing →](user-guide/mcp-tools.md#cookbook-analysis-parsing){ .md-button }

### :material-swap-horizontal: Chef-to-Ansible Conversion Engine
Advanced resource-to-task conversion with intelligent module selection and guard handling.

[Learn more about conversion →](user-guide/mcp-tools.md#resource-conversion){ .md-button }

### :material-check-circle: Validation & Testing
Comprehensive validation framework and InSpec integration for ensuring migration accuracy.

[Learn more about validation →](user-guide/mcp-tools.md#inspec-integration){ .md-button }

### :material-docker: Chef Habitat to Container Conversion
Modernise Habitat applications to containerised deployments with Docker and Compose.

[Learn more about Habitat conversion →](user-guide/mcp-tools.md#habitat){ .md-button }

### :material-update: Ansible Upgrade Assessment & Planning
Comprehensive Ansible upgrade planning based on official compatibility matrices and EOL tracking.

[Learn more about Ansible upgrades →](user-guide/ansible-upgrades.md){ .md-button }

### :material-web: Visual Migration Planning Interface
Interactive web-based interface for Chef-to-Ansible migration planning and visualisation.

[Learn more about the UI →](user-guide/ui.md){ .md-button }

## Quick Start

Get started with SousChef in minutes:

=== "Claude Desktop"

    ```bash
    # Install from PyPI
    pip install mcp-souschef

    # Configure Claude Desktop (macOS)
    cp config/claude-desktop.json ~/Library/Application\ Support/Claude/claude_desktop_config.json

    # Restart Claude and start using
    # Ask: "What Chef migration tools are available?"
    ```

=== "VS Code + Copilot"

    ```bash
    # Install from PyPI
    pip install mcp-souschef

    # Copy config to VS Code (macOS/Linux)
    cp config/vscode-copilot.json ~/.config/Code/User/mcp.json

    # Windows:
    # copy config\vscode-copilot.json %APPDATA%\Code\User\mcp.json

    # Reload VS Code, trust the server
    # Use tools in Copilot Chat:
    # "Analyze the cookbook at /path/to/cookbook"
    pip install mcp-souschef

    # Start using immediately
    souschef-cli cookbook /path/to/cookbook
    ```

=== "CLI (v2 Orchestrator)"

        ```bash
        # Run an end-to-end v2 migration
        souschef-cli v2 migrate \
            --cookbook-path /path/to/cookbook \
            --chef-version 15.10.91 \
            --target-platform aap \
            --target-version 2.4.0 \
            --save-state

        # Load the stored migration state later
        souschef-cli v2 status --migration-id mig-abc123
        ```

=== "Web UI"

    **Launch the Visual Interface:**
    ```bash
    # Using Poetry (development)
    poetry run souschef ui

    # Using pip (installed)
    souschef ui

    # Custom port
    souschef ui --port 8080
    ```

    **Features:**
    - Interactive cookbook analysis with archive upload
    - Real-time dependency visualisation
    - Migration planning wizards
    - Progress tracking and validation reports

    [Learn more about the UI →](user-guide/ui.md){ .md-button }

[Get started →](getting-started/installation.md){ .md-button .md-button--primary }

## Enterprise Features

- :material-chart-line: **Migration Assessment & Reporting** - Automated complexity analysis and executive reports
- :material-rocket: **Modern Deployment Patterns** - Blue/green, canary releases, and cloud-native strategies
- :material-key: **Secrets Management** - Secure data bag to Ansible Vault conversion
- :material-speedometer: **Performance Profiling** - Identify bottlenecks and optimise large-scale migrations

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

-   :material-api:{ .lg .middle } __v2.0 API Reference__

    ---

    Complete API documentation for the v2.0 Migration Orchestrator

    [:octicons-arrow-right-24: API reference](api-reference/migration-v2.md)

-   :material-cog-sync:{ .lg .middle } __Advanced Workflows__

    ---

    Complex migration patterns and integration strategies

    [:octicons-arrow-right-24: Advanced workflows](migration-guide/advanced-workflows.md)

-   :material-help-circle:{ .lg .middle } __Troubleshooting__

    ---

    Common issues and solutions for migrations

    [:octicons-arrow-right-24: Troubleshooting](user-guide/troubleshooting.md)

</div>

## Community & Support

- :material-github: **GitHub**: [kpeacocke/souschef](https://github.com/kpeacocke/souschef)
- :material-bug: **Issues**: [Report a bug](https://github.com/kpeacocke/souschef/issues)
- :material-forum: **Discussions**: [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)
- :material-book: **Wiki**: [Documentation](https://github.com/kpeacocke/souschef/wiki)

---

**SousChef** - *Transforming infrastructure automation, one recipe at a time.*
