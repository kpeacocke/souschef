# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.4](https://github.com/kpeacocke/souschef/compare/v2.5.3...v2.5.4) (2026-01-15)


### Bug Fixes

* add missing permissions for releases in workflow configuration ([a6c2686](https://github.com/kpeacocke/souschef/commit/a6c2686cd95e88f290621ba66bd6d47a459d456f))
* remove unnecessary permissions for releases in workflow configuration ([a265f01](https://github.com/kpeacocke/souschef/commit/a265f016294cb9992c40443fde9f15f0b22117ba))
* update pyproject.toml version parsing to open in binary mode ([ee983b4](https://github.com/kpeacocke/souschef/commit/ee983b4c1467adb87a7c12cc72519054fba3337e))
* use correct GitHub Actions permissions for release-please ([ef33f43](https://github.com/kpeacocke/souschef/commit/ef33f43055eb20dd8b5c0645d52183c51b22ca5b))

## [2.5.2](https://github.com/kpeacocke/souschef/compare/v2.5.1...v2.5.2) (2026-01-15)


### Bug Fixes

* import souschef in test_cli.py ([#160](https://github.com/kpeacocke/souschef/issues/160)) ([901fb0e](https://github.com/kpeacocke/souschef/commit/901fb0e9e9f35518263c935951f44bf72202dc53))

## [2.5.1](https://github.com/kpeacocke/souschef/compare/v2.5.0...v2.5.1) (2026-01-15)


### Bug Fixes

* add missing souschef import in test_cli.py ([#158](https://github.com/kpeacocke/souschef/issues/158)) ([c15e9a2](https://github.com/kpeacocke/souschef/commit/c15e9a2f823db5ed060f3aeb8a6824cc529ce047))

## [2.5.0](https://github.com/kpeacocke/souschef/compare/v2.4.0...v2.5.0) (2026-01-15)


### Features

* UI & Container ([#155](https://github.com/kpeacocke/souschef/issues/155)) ([e266dd1](https://github.com/kpeacocke/souschef/commit/e266dd152d31b17233ffeed05cfa48d91b858c9b))

## [2.4.0](https://github.com/kpeacocke/souschef/compare/v2.3.1...v2.4.0) (2026-01-13)


### Features

* add coverage.xml path fixes and update coverage configuration ([4f225f6](https://github.com/kpeacocke/souschef/commit/4f225f6fbbb18f3638c0518e07c2d1ffff0621f8))
* add ServerSpec and Goss test framework converters ([#124](https://github.com/kpeacocke/souschef/issues/124)) ([3cedb08](https://github.com/kpeacocke/souschef/commit/3cedb089f2cb980b7279ee7839d208cb7a7b6a3a))
* enhance linting rules and update SonarCloud issue configurations ([52b499e](https://github.com/kpeacocke/souschef/commit/52b499ea0efd0f1c8a2c234d69a69813608c70ce))
* polish and ci generation and enhancements ([#133](https://github.com/kpeacocke/souschef/issues/133)) ([6e99528](https://github.com/kpeacocke/souschef/commit/6e99528ee840ba882a0756498a81004f9489a64c))
* streamline SonarCloud coverage generation and remove redundant steps ([22a0311](https://github.com/kpeacocke/souschef/commit/22a03111d0e72e106591b43091a4e68e884a8e16))
* terraform! ([#143](https://github.com/kpeacocke/souschef/issues/143)) ([9fc59fe](https://github.com/kpeacocke/souschef/commit/9fc59fe94450135219d618f5899dfa298230f939))
* workflow fixes ([#134](https://github.com/kpeacocke/souschef/issues/134)) ([ad72489](https://github.com/kpeacocke/souschef/commit/ad72489e952ebb7f714f8eb1c0110545459db487))
* workflow fixes ([#134](https://github.com/kpeacocke/souschef/issues/134)) ([#135](https://github.com/kpeacocke/souschef/issues/135)) ([565502f](https://github.com/kpeacocke/souschef/commit/565502f9963c1b0a157e395ce4b99d0ef0ed7e45))


### Bug Fixes

* improve SonarCloud configuration and workflow ([#137](https://github.com/kpeacocke/souschef/issues/137)) ([6b97a87](https://github.com/kpeacocke/souschef/commit/6b97a8761c11de5e815dbe18a6a341e4aaf0bf8b))
* workflows ([#139](https://github.com/kpeacocke/souschef/issues/139)) ([4a0ee77](https://github.com/kpeacocke/souschef/commit/4a0ee77c0d88afb35de3110d88e5a98968b6c992))

## [2.3.0](https://github.com/kpeacocke/souschef/compare/v2.2.0...v2.3.0) (2026-01-11)


### Features

* documentation ([#89](https://github.com/kpeacocke/souschef/issues/89)) ([988c863](https://github.com/kpeacocke/souschef/commit/988c8634425e059db118d4b4cdf78432a306a6fc))


### Bug Fixes

* CI use Python 3.14 ([#101](https://github.com/kpeacocke/souschef/issues/101)) ([9a9d5fb](https://github.com/kpeacocke/souschef/commit/9a9d5fba2336e5e1f59eb5c3237684cf848a7491))
* CI workflow must run on main branch for release-please trigger ([12de1dd](https://github.com/kpeacocke/souschef/commit/12de1ddc4fa614e2c9b06a536d1e851f9fb0185e))
* disable pymdownx.emoji to fix docs build ([#95](https://github.com/kpeacocke/souschef/issues/95)) ([556af01](https://github.com/kpeacocke/souschef/commit/556af01586282d73117073933f69ddf9aa8b5150))
* disable Snyk PR checks (test limit reached, main-only) ([d2ed4ba](https://github.com/kpeacocke/souschef/commit/d2ed4ba52af12ef5eca1c807eda3b1817bfc036b))
* downgrade Python to 3.13 for pymdownx.emoji compatibility ([#93](https://github.com/kpeacocke/souschef/issues/93)) ([1854aa6](https://github.com/kpeacocke/souschef/commit/1854aa64cb70dc30c69e30d49cf4f4b60611eefa))
* enable GitHub Pages in docs workflow ([#91](https://github.com/kpeacocke/souschef/issues/91)) ([48a2206](https://github.com/kpeacocke/souschef/commit/48a220665891e7bae681f18aadf49d510ead1d10))
* pyproject.toml Python version to 3.14 ([#103](https://github.com/kpeacocke/souschef/issues/103)) ([1c5bce3](https://github.com/kpeacocke/souschef/commit/1c5bce34f5f7d9960ab3dbffe1b85475ec8d7075))
* remove --strict flag from mkdocs build ([#97](https://github.com/kpeacocke/souschef/issues/97)) ([899faca](https://github.com/kpeacocke/souschef/commit/899faca27d46f09676c31aa9e13db29010176b4a))
* resolve all mkdocs warnings ([#99](https://github.com/kpeacocke/souschef/issues/99)) ([3eeb26c](https://github.com/kpeacocke/souschef/commit/3eeb26c683ffdff0d0a1d89ff2f01093c6f2bbb3))
* update CI and docs workflows to Python 3.14 ([d0fd569](https://github.com/kpeacocke/souschef/commit/d0fd569f5b231f9d77cd7644b08a27319081133b))
* update Python requirement to &gt;=3.14,&lt;4.0 (reverted by PR merge) ([2a2e305](https://github.com/kpeacocke/souschef/commit/2a2e3057da8486e9aab44ae8772160d6b1b62b7b))
* use GITHUB_TOKEN in release-please workflow ([#106](https://github.com/kpeacocke/souschef/issues/106)) ([3a57f97](https://github.com/kpeacocke/souschef/commit/3a57f979dd7126771474b9af0d2ecfd5383d5029))


### Reverts

* restore RELEASE_TOKEN in release-please workflow ([bbde735](https://github.com/kpeacocke/souschef/commit/bbde73512bffb50bb69302a2ec4e64929b350550))


### Documentation

* clarify release-please trigger mechanism ([2712049](https://github.com/kpeacocke/souschef/commit/2712049118ba0ebbe2ba16353cc4fa89bcfc3a16))

## [2.1.2](https://github.com/kpeacocke/souschef/compare/v2.1.1...v2.1.2) (2026-01-05)


### Bug Fixes

* Develop ([#51](https://github.com/kpeacocke/souschef/issues/51)) ([bb1fcea](https://github.com/kpeacocke/souschef/commit/bb1fcea0e1586feda509577a574dd034e735cac9))

## [2.1.1](https://github.com/kpeacocke/souschef/compare/v2.1.0...v2.1.1) (2026-01-05)


### Bug Fixes

* Merge pull request [#43](https://github.com/kpeacocke/souschef/issues/43) from kpeacocke/develop ([6d73b29](https://github.com/kpeacocke/souschef/commit/6d73b29d8814f6fd16802ba5f686caeb009cf85d))
* use push trigger for release-please to create releases ([6d73b29](https://github.com/kpeacocke/souschef/commit/6d73b29d8814f6fd16802ba5f686caeb009cf85d))
* use push trigger for release-please to create releases ([49b05c6](https://github.com/kpeacocke/souschef/commit/49b05c6afb421ee8e99d81d79ec554d5056bcf89))

## [2.1.0](https://github.com/kpeacocke/souschef/compare/v2.0.1...v2.1.0) (2026-01-05)


### Features

* auto-merge release PRs when checks pass ([7fd9f3f](https://github.com/kpeacocke/souschef/commit/7fd9f3f2b11f8c05b36b58eb55498b74693df6ed))


### Bug Fixes

* Merge pull request [#41](https://github.com/kpeacocke/souschef/issues/41) from kpeacocke/develop ([d539fc7](https://github.com/kpeacocke/souschef/commit/d539fc73cc6e04f9dd6d2e360aec05fd18fd0fa9))
* pass release tag through job outputs for workflow_dispatch ([ed7c74f](https://github.com/kpeacocke/souschef/commit/ed7c74fb27df93da42e8dbfe7ffb7b03409ee017))
* simplify release automation with auto-merge ([d539fc7](https://github.com/kpeacocke/souschef/commit/d539fc73cc6e04f9dd6d2e360aec05fd18fd0fa9))
* use env vars instead of direct input interpolation in run blocks ([c608150](https://github.com/kpeacocke/souschef/commit/c608150512eda51d62c428b88638d03262000303))

## [2.0.1](https://github.com/kpeacocke/souschef/compare/v2.0.0...v2.0.1) (2026-01-05)


### Bug Fixes

* Enhance release workflows to support manual triggering with tag input… ([0b3df0f](https://github.com/kpeacocke/souschef/commit/0b3df0f6ddd29d744fa1457faa4cdedf6e21077b))
* use check-regexp for CI and CodeQL check names ([3f56080](https://github.com/kpeacocke/souschef/commit/3f560808b4d1932113d34f9117100a51c48bfe18))

## [2.0.0](https://github.com/kpeacocke/souschef/compare/v1.0.0...v2.0.0) (2026-01-05)


### BREAKING CHANGES

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
