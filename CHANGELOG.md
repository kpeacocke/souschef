# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial MCP server implementation with 34 tools across 8 major capability areas
- Chef cookbook analysis and parsing (recipes, attributes, metadata, templates, custom resources)
- Chef-to-Ansible conversion engine for resources and playbooks
- Chef search to Ansible dynamic inventory conversion
- InSpec integration and validation framework
- Data bags to Ansible Vars/Vault conversion
- Chef environments to Ansible inventory groups conversion
- AWX/Ansible Automation Platform integration tooling
- Advanced deployment patterns (blue/green, canary)
- Migration assessment and planning tools
- Comprehensive test suite with 93% coverage (unit, integration, property-based tests)
- Command-line interface (CLI) for standalone usage
- GitHub workflows for CI/CD, gitflow validation, and releases
- Development container configuration for consistent development environment

### Security
- Integrated security scanning with Snyk and SonarQube
- Secret detection with TruffleHog
- Dependency vulnerability checking with pip-audit

## [0.1.0] - TBD

- Initial release (pending first tag)

[Unreleased]: https://github.com/kpeacocke/souschef/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kpeacocke/souschef/releases/tag/v0.1.0
