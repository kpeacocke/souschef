# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0](https://github.com/kpeacocke/souschef/compare/v1.0.0...v2.0.0) (2026-01-05)


### ⚠ BREAKING CHANGES

* Package name changed from 'souschef' to 'mcp-souschef' on PyPI

### Features

* Add issue and pull request templates for better contribution guidance ([5b050d2](https://github.com/kpeacocke/souschef/commit/5b050d2072557a85fe022bddc3b53f2349864c2b))
* add MCP protocol integration tests ([5bb99aa](https://github.com/kpeacocke/souschef/commit/5bb99aa2968aa261232416e66e416f86a5b32e08))
* Add Ruby feature to devcontainer configuration with specified version and gem installation ([76b44be](https://github.com/kpeacocke/souschef/commit/76b44be72ec9f8832c3b3c8048af048511d44970))
* Add technical debt issue template and automation script for tracking complexity violations ([3b02614](https://github.com/kpeacocke/souschef/commit/3b02614aa892e61a750bc5873e4a83ef5e18f8aa))
* configure mutation testing with mutmut ([0325230](https://github.com/kpeacocke/souschef/commit/0325230aca418a8da3b6f46e42c8df668debd390))
* implement automated versioning with Release Please ([986d158](https://github.com/kpeacocke/souschef/commit/986d158573d120ba9c496d807ae29dacf3546db2))
* implement automated versioning with Release Please ([3dff543](https://github.com/kpeacocke/souschef/commit/3dff543dd89c19b04f24e4621ebd03f9b497d7cb))
* install Snyk CLI in devcontainer ([602ca09](https://github.com/kpeacocke/souschef/commit/602ca09e9f83940106ea978c0f3a88e571d2cf83))
* make something happen ([d103e9d](https://github.com/kpeacocke/souschef/commit/d103e9d5b962a17843af93a8bbc00b78a560150c))
* **testing:** Add comprehensive performance and load tests ([#28](https://github.com/kpeacocke/souschef/issues/28)) ([a494db4](https://github.com/kpeacocke/souschef/commit/a494db4f7ce8e76cff8eb98f02eadf4b603ae4c1))
* **testing:** Add comprehensive real-world Chef cookbook fixtures ([#27](https://github.com/kpeacocke/souschef/issues/27)) ([1a1a63c](https://github.com/kpeacocke/souschef/commit/1a1a63c21a1198c15c0da0fef0c4ccad0ddac81f))
* **tests:** Add comprehensive error handling and edge case tests for CLI and server functionality ([28b8f01](https://github.com/kpeacocke/souschef/commit/28b8f0194761b756ea2d4e876e2ac35fc4d2f3ba))
* Update devcontainer configuration and enhance technical debt issue script ([fa5e336](https://github.com/kpeacocke/souschef/commit/fa5e336962fa84b1ce5ae30062eb260dafee2b80))


### Bug Fixes

* correct parameter name for Codecov action to support multiple coverage files ([c211780](https://github.com/kpeacocke/souschef/commit/c211780badb38648c4a380203f3acb57a9fe8857))
* detect architecture for Snyk CLI installation ([e4162fe](https://github.com/kpeacocke/souschef/commit/e4162fe0a99cd636447f9c9b7008861d63e8ccdb))
* install clipboard utilities for Snyk ([f0424d1](https://github.com/kpeacocke/souschef/commit/f0424d138b8b85b3da4c229376277aaad30ca7d3))
* resolve all ruff warnings and allow E501 in server.py ([082aaf1](https://github.com/kpeacocke/souschef/commit/082aaf1646a46ce3a6fb01979517525bf5b03a68))
* update Node.js to version 22 for SonarLint ([7553d41](https://github.com/kpeacocke/souschef/commit/7553d4187972355fb821ed766c71e1e7b5089123))


### Reverts

* keep Node.js at 'lts' version ([dbc5c50](https://github.com/kpeacocke/souschef/commit/dbc5c50e6f7246fb732308e436995b54cd60bcf3))


### Documentation

* add comprehensive testing improvement roadmap ([a4655d7](https://github.com/kpeacocke/souschef/commit/a4655d7d738152f1747bf871fc0ac4ea80630b08))
* correct breaking change version bump example for pre-1.0.0 ([4570ca0](https://github.com/kpeacocke/souschef/commit/4570ca0cb6eb57cb2009dc120d0579fffeadc172))

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
