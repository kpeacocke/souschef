# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-02-17

### Added

* **v2.2:** Interactive CLI migration wizard with step-by-step guidance
* **v2.2:** Custom rule engine for resource conversion with user-defined mappings
* **v2.2:** Custom module generator for Ansible module scaffolding
* **v2.2:** Handler generation module for Ansible handler conversion

### Changed

* **documentation:** Aggressive documentation refactoring for clarity and conciseness
  - README: 185 → 165 lines with improved structure and status line
  - CONTRIBUTING: 722 → 587 lines, trimmed release process bloat (135 line reduction)
  - ARCHITECTURE: Replaced ASCII diagram with Mermaid flowchart
  - Added "Documentation Guide" with role-based routing for users
  - Standardised Australian English across all documentation
* **documentation:** Consolidated ansible_versions.py documentation with master-link pattern
* **documentation:** Condensed CodeQL section from 130 lines to 16 lines (87% reduction)

## [5.1.4] - 2026-02-14

### Fixed

* **security:** Upgrade pip to version 26.0 for security fixes
* **version:** Update version to 5.1.4 in pyproject.toml

## [5.1.3] - 2026-02-13

### Fixed

* **version:** Update version to 5.1.3 in pyproject.toml

## [5.1.2] - 2026-02-13

### Added

* **security:** Enhanced Trivy vulnerability scanning with improved report categories

### Fixed

* **ci:** Update branch verification logic and correct Trivy scan category
* **version:** Update version to 5.1.2 in pyproject.toml

## [5.1.1] - 2026-02-11

### Added

* **testing:** Comprehensive tests to boost coverage from 77% to 91%
  - 679 new tests for CLI, Ansible versions, assessment, and server modules
  - 72 tests for chef_server and __init__ modules
  - 60 tests for GitHub agent control (97% coverage)
  - 60 tests for migration_config and blob storage (95%+ coverage)
  - 1 comprehensive edge case tests for resource converter
  - 35 tests for ReDoS vulnerability fixes

### Fixed

* **security:** Fix ReDoS vulnerability in ansible inventory parser (S5852)
* **code-quality:** Eliminate code duplication in HTTP client (SonarCloud)
* **code-quality:** Convert caching.py to PEP 695 generic syntax (9 SonarCloud issues)
* **codeql:** Convert obsolete CodeQL suppressions to current syntax
* **codeql:** Remove non-functional CodeQL inline suppressions
* **path-security:** Harden path handling with enhanced validation
* **path-security:** Validate safe_join parts before path construction
* **version:** Update version to 5.1.1 in pyproject.toml

### Changed

* **security:** Enhanced security and code quality across multiple modules
* **documentation:** Add CodeQL alert suppression documentation

### Dependencies

* Bump production-dependencies group (2 updates)
* Bump pillow from 12.1.0 to 12.1.1
* Bump pip from 25.3 to 26.0
* Bump cryptography from 46.0.3 to 46.0.5
* Bump production-dependencies group (4 updates)
* Bump dev-dependencies group (3 updates)
* Bump actions/cache from 5.0.1 to 5.0.3
* Bump actions/checkout from 4.2.2 to 6.0.2
* Bump actions/github-script from 7.0.1 to 8.0.0
* Bump actions/setup-python from 6.1.0 to 6.2.0
* Bump github/codeql-action from 4.32.1 to 4.32.2

## [5.1.0] - 2026-02-10

### Added

* **v2.1:** Advanced features (guards, optimization, audit trail)
* **v2.0:** Complete resource and handler conversion system
* **v2.0:** Chef Server node discovery and inventory population
* **v2.0:** Complete CLI command suite for v2 migration
* **v2.0:** Deployment integration with real AWX/AAP API clients
* **v2.0:** Migration Orchestrator UI with simulation mode
* **v2.0:** Core Foundation with IR schema, versioning, and plugin architecture
* **ir:** Intermediate Representation module for multi-tool support
  - IRGraph: Directed acyclic graph representation of infrastructure
  - IRNode, IRAction, IRAttribute, IRGuard data structures
  - Plugin architecture: SourceParser, TargetGenerator, PluginRegistry
  - Version management and schema evolution
* **testing:** Comprehensive integration and property-based tests for IR module
* **documentation:** Comprehensive IR module documentation and ARCHITECTURE updates

### Changed

* **refactoring:** Modular architecture improvements for better maintainability
  - New `cookbook_analysis_security.py` module (275 lines, 11 security functions)
  - New `cookbook_analysis_utilities.py` module (61 lines, 3 utility functions)
  - Focus on path security, archive handling, and utility functions
* **documentation:** Updated markdown documentation for accuracy and consistency
* **qa:** Test coverage reporting updated to 91% (3,500+ passing tests)
* **architecture:** Code organised by concerns for improved maintainability

### Improved

* **code-quality:** Zero breaking changes - all refactoring maintains backward compatibility
* **type-safety:** Maintained full mypy compliance across all modules
* **testing:** All 3,500+ tests passing with 99.7% success rate

### Documentation

* See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for module organisation
* See [IR.md](docs/IR.md) for Intermediate Representation documentation

## [5.0.x] - Previous Releases

### Added

* **mcp:** Expose Chef Server and AI template conversion as MCP tools
  - `validate_chef_server_connection` - Test Chef Server REST API connectivity
  - `get_chef_nodes` - Query Chef Server for nodes matching search criteria
  - `convert_template_with_ai` - Convert ERB templates to Jinja2 with AI validation
* **cli:** Add three new command-line tools for Chef Server and template conversion
  - `validate-chef-server` - Command to validate Chef Server connectivity from CLI
  - `query-chef-nodes` - Command to query Chef Server nodes with JSON output support
  - `convert-template-ai` - Command to convert templates with optional AI enhancement
* **chef-server:** Implement Chef Server API integration for dynamic inventory
  - Query Chef server using REST API `/search/node` endpoint
  - Extract node data including roles, environment, platform, and IP addresses
  - Graceful fallback when Chef server is unavailable
  - Support for environment-based configuration via `CHEF_SERVER_URL` and `CHEF_NODE_NAME`
* **template-conversion:** Add AI-enhanced template conversion with validation
  - Convert ERB templates to Jinja2 with AI analysis of complex Ruby logic
  - Automatic fallback to rule-based conversion if AI service is unavailable
  - Detection of complex Ruby constructs requiring AI analysis
  - Security validation for sensitive template operations
* **ui:** Chef Server Settings page for managing server configuration
  - Interactive Chef Server connection validation in UI
  - Configuration input for server URL and node names
  - Live connection testing with user-friendly error messages
* **ui:** Complete local model validation in AI Settings page
  - Support for Ollama, llama.cpp, vLLM, and LM Studio servers
  - Validation checks for both Ollama and OpenAI-compatible APIs
  - UI configuration for local model server URL and model name
  - Automatic model availability detection
  - User-friendly error messages for troubleshooting
* **ansible-upgrades:** Comprehensive Ansible upgrade and planning system
  - 5 new CLI commands: `assess`, `plan`, `eol`, `validate-collections`, `detect-python`
  - 3 new UI pages: Environment Assessment, Upgrade Planning, Collection Validation
  - 5 new MCP tools for Ansible version management and upgrade planning
  - Breaking change analysis between Ansible versions
  - Collection compatibility validation with requirements.yml support
  - EOL status checking for Ansible versions
  - Python version detection and compatibility verification
  - Risk assessment with automated recommendations
  - Comprehensive testing strategy generation

### Changed

* **converters:** Replace Chef Server API placeholder with working implementation
* **server:** Update tool count from 35 to 38 public tools (40 total with internal utilities)
* **server:** Add 5 Ansible upgrade MCP tools: 43 public tools total (45 with internal utilities)
* **readme:** Add section 12 "Chef Server Integration & Dynamic Inventory"
* **ui:** Replace "not yet implemented" message with full local model support

### Fixed

* **converters:** Remove TODO comment from `get_chef_nodes()` - now fully implemented
* **server:** Properly expose Chef Server and template conversion functions as MCP tools
* **ui:** Remove "Local model validation not implemented yet" informational message
* **documentation:** Update tool counts and capability areas to reflect new features

## [3.3.0](https://github.com/kpeacocke/souschef/releases/tag/v3.3.0) (2026-01-30)

### Features

* **assessment:** Add realistic AI-assisted effort estimates with 50% time reduction factor
* **metrics:** Enhance EffortMetrics class with SousChef-assisted effort properties
  - `estimated_days_with_souschef` - Effort reduction with AI assistance (50%)
  - `time_saved` - Days saved by using SousChef
  - `efficiency_gain_percent` - Percentage speedup
  - `estimated_hours_with_souschef` - Hours with AI assistance
  - `estimated_weeks_range_with_souschef` - Week range with AI assistance
  - `get_comparison_summary()` - Formatted comparison output
* **assessment:** Display side-by-side effort comparison in migration assessments
  - Manual Migration Effort (WITHOUT SousChef)
  - AI-Assisted Migration (WITH SousChef)
  - Time Saved and Efficiency Gains
* **ui:** Update Streamlit UI to show dual effort estimates
  - Summary metrics: Manual hours with delta showing AI-assisted savings
  - Individual cookbooks: 3-column layout (Complexity | Manual | With SousChef)
  - Metric cards with green delta indicators for visual comparison
  - Report generation with both manual and AI-assisted timelines

### Documentation

* Update UI documentation with effort estimation features
* Update assessment guide with realistic effort estimation model
* Add effort estimation model explanation to README
* Document 50% time reduction factor and assumptions

## [3.2.0](https://github.com/kpeacocke/souschef/releases/tag/v3.2.0) (2026-01-22)


### ⚠ BREAKING CHANGES

* Package name changed from 'souschef' to 'mcp-souschef' on PyPI

### Features

* Add advanced Chef attribute precedence resolution ([#54](https://github.com/kpeacocke/souschef/issues/54)) ([8c16485](https://github.com/kpeacocke/souschef/commit/8c164851ec33eb3a1d9fe9521d2157d60062491f))
* add batch migration, Habitat/InSpec conversions, and cost estimation ([5044d08](https://github.com/kpeacocke/souschef/commit/5044d08fdf31036526b22fc99e16bf5eeeff405c))
* Add comprehensive performance profiling system ([4141051](https://github.com/kpeacocke/souschef/commit/4141051ce685e1b1dec4d3d03ed5b78a204140b6))
* Add containerization support for SousChef UI ([2779a73](https://github.com/kpeacocke/souschef/commit/2779a73ab8bc7b8dfe4ab6aba87178691c94d3bf))
* Add containerization support for SousChef UI ([f75ef95](https://github.com/kpeacocke/souschef/commit/f75ef954f5cdfd02771f355dac7075a9174442e2))
* Add containerization support for SousChef UI ([#169](https://github.com/kpeacocke/souschef/issues/169)) ([290aadb](https://github.com/kpeacocke/souschef/commit/290aadb22e43ca0435a5951af56983204a094e3d))
* add convert-recipe and assess-cookbook CLI commands ([8330f04](https://github.com/kpeacocke/souschef/commit/8330f046e635d4174c4edc5feb7bfa46f3570b54))
* add coverage configuration for testing ([c69a4c3](https://github.com/kpeacocke/souschef/commit/c69a4c3f2c8fbafebf8ff98bba7f2cac7f7b3779))
* add coverage.xml path fixes and update coverage configuration ([4f225f6](https://github.com/kpeacocke/souschef/commit/4f225f6fbbb18f3638c0518e07c2d1ffff0621f8))
* add Docker CLI and docker.sock mounting to devcontainer ([49413c5](https://github.com/kpeacocke/souschef/commit/49413c5abb36390603c82ef12f5b134dd060692d))
* Add functions for parsing Chef migration assessments and cookbook metadata ([a5e7d5a](https://github.com/kpeacocke/souschef/commit/a5e7d5acd5d31f5a4aa3814508acacb9d8c34528))
* add GitLab CI configuration and comprehensive tests for error handling ([28a21db](https://github.com/kpeacocke/souschef/commit/28a21dbc7237282f8fce8217e296665ddb6a2eaf))
* Add health check function to UI app ([1e7ec72](https://github.com/kpeacocke/souschef/commit/1e7ec7278443629b633c447c7dd1c7c08815fb2b))
* add MCP configuration examples for various clients ([49b858c](https://github.com/kpeacocke/souschef/commit/49b858c01b382f46f2579ee35864d451e02abc93))
* add MCP protocol integration tests ([5bb99aa](https://github.com/kpeacocke/souschef/commit/5bb99aa2968aa261232416e66e416f86a5b32e08))
* add mutation testing workflow and enhance CI/CD processes ([4366367](https://github.com/kpeacocke/souschef/commit/4366367cbff93b67ae652bbacb8add77471934be))
* add ServerSpec and Goss test framework converters ([39cc599](https://github.com/kpeacocke/souschef/commit/39cc599a1a6439e10103c05d6781399886554a9b))
* add ServerSpec and Goss test framework converters ([#124](https://github.com/kpeacocke/souschef/issues/124)) ([3cedb08](https://github.com/kpeacocke/souschef/commit/3cedb089f2cb980b7279ee7839d208cb7a7b6a3a))
* add SonarLint configuration for SonarCloud integration ([ad9d804](https://github.com/kpeacocke/souschef/commit/ad9d804b9eb81b14acf45a32485b83aedb635ef2))
* add support for Chef remote_file resource conversion ([6ede6c3](https://github.com/kpeacocke/souschef/commit/6ede6c3909ced1506c5ec588e2c8706c19249120))
* add support for Chef remote_file resource conversion ([#66](https://github.com/kpeacocke/souschef/issues/66)) ([e292c3a](https://github.com/kpeacocke/souschef/commit/e292c3a779293b013ba1746a67c1d5ca3e0e8e96))
* add terraform provider for infrastructure state management ([721f250](https://github.com/kpeacocke/souschef/commit/721f250c0399b526265db7c44e3e0ea5fe6acf61))
* Add Terraform Provider for Infrastructure State Management ([#142](https://github.com/kpeacocke/souschef/issues/142)) ([fcc4151](https://github.com/kpeacocke/souschef/commit/fcc4151058f5c227d425a4085ef7c5bbaa496418))
* add types for networkx and update dependencies in poetry files ([b1d2315](https://github.com/kpeacocke/souschef/commit/b1d231590bdd69db5904d09b563d1fa38b91a8f6))
* ai enhancement & ui refinement ([#245](https://github.com/kpeacocke/souschef/issues/245)) ([7ab5fd2](https://github.com/kpeacocke/souschef/commit/7ab5fd2ce41f47640e6c105a2030f1648beb3cf2))
* **assessment:** enhance error handling with input validation and recovery suggestions ([ef8e501](https://github.com/kpeacocke/souschef/commit/ef8e501d07f3fc6fa6c06b9dfdb7cb8fd2a4baea))
* auto-merge release PRs when checks pass ([7fd9f3f](https://github.com/kpeacocke/souschef/commit/7fd9f3f2b11f8c05b36b58eb55498b74693df6ed))
* **ci:** Add GitHub Actions workflow generation ([2a1faff](https://github.com/kpeacocke/souschef/commit/2a1faff19a35f933a504602901e0b314cd85092b))
* **ci:** Add Jenkins and GitLab CI pipeline generation ([d7c3e12](https://github.com/kpeacocke/souschef/commit/d7c3e12acf412280b6ad593d9d8ea2cd9f4b90f6))
* **cli:** Add generate-jenkinsfile and generate-gitlab-ci commands ([b198b5c](https://github.com/kpeacocke/souschef/commit/b198b5cca00f98645fb26ba08db9334fec35160d))
* Complete UI design cleanup and documentation ([75fec48](https://github.com/kpeacocke/souschef/commit/75fec48fdde7c9d1512c04885ca8a203b3e419c2))
* configure devcontainer to mount docker.sock from host ([30277f9](https://github.com/kpeacocke/souschef/commit/30277f90be4b0d26d068861faa2a8104e25e7189))
* configure mutation testing with mutmut ([0325230](https://github.com/kpeacocke/souschef/commit/0325230aca418a8da3b6f46e42c8df668debd390))
* documentation ([#89](https://github.com/kpeacocke/souschef/issues/89)) ([988c863](https://github.com/kpeacocke/souschef/commit/988c8634425e059db118d4b4cdf78432a306a6fc))
* enhance CI workflows with Terraform provider tests and Go setup ([139634b](https://github.com/kpeacocke/souschef/commit/139634b2434ff17a63b8d2df41e0ed6636cb1a84))
* enhance linting rules and update SonarCloud issue configurations ([52b499e](https://github.com/kpeacocke/souschef/commit/52b499ea0efd0f1c8a2c234d69a69813608c70ce))
* enhance logging and security measures in Dockerfile and application code ([ca9a06d](https://github.com/kpeacocke/souschef/commit/ca9a06dca0a8ee7dbc0185c51a6668292a36af43))
* Enhance SousChef with AI Integration and Improved Resource Conversion ([5a31314](https://github.com/kpeacocke/souschef/commit/5a313146ea10b5885235529e16d2dd685f6e4450))
* enhance workflows and validation framework for better compatibility and error handling ([e2281e3](https://github.com/kpeacocke/souschef/commit/e2281e324509caf64275800685a0c81c5ee70d8c))
* **errors:** add enhanced error handling framework with actionable recovery suggestions ([a7445ca](https://github.com/kpeacocke/souschef/commit/a7445ca4fd08632574218e3acc55e3665cf840f5))
* Feature/enhanced guard handling ([#53](https://github.com/kpeacocke/souschef/issues/53)) ([1576684](https://github.com/kpeacocke/souschef/commit/157668499262689a4abf6187433788e3468b2dca))
* Feature/validation framework ([#56](https://github.com/kpeacocke/souschef/issues/56)) ([0f7dbc6](https://github.com/kpeacocke/souschef/commit/0f7dbc6d3215acfdbde476330cc139f22db51d5c))
* habitat-containers ([#57](https://github.com/kpeacocke/souschef/issues/57)) ([2f537c9](https://github.com/kpeacocke/souschef/commit/2f537c98383784e06a2a529fb655a9d062a69022))
* implement automated versioning with Release Please ([986d158](https://github.com/kpeacocke/souschef/commit/986d158573d120ba9c496d807ae29dacf3546db2))
* implement automated versioning with Release Please ([3dff543](https://github.com/kpeacocke/souschef/commit/3dff543dd89c19b04f24e4621ebd03f9b497d7cb))
* Improve test coverage and fix code quality issues ([53410cb](https://github.com/kpeacocke/souschef/commit/53410cb48e8fb402caaa1cce144a5b34db10fc76))
* make something happen ([d103e9d](https://github.com/kpeacocke/souschef/commit/d103e9d5b962a17843af93a8bbc00b78a560150c))
* mkdocs-documentation ([#88](https://github.com/kpeacocke/souschef/issues/88)) ([8abb92d](https://github.com/kpeacocke/souschef/commit/8abb92d690f00c9c4dcbe282c5e836c12644c9df))
* modular remodel ([#59](https://github.com/kpeacocke/souschef/issues/59)) ([c1186eb](https://github.com/kpeacocke/souschef/commit/c1186ebe2f8f986663bb42376a8f4941a4f1d962))
* modular-architecture ([#58](https://github.com/kpeacocke/souschef/issues/58)) ([3ea4051](https://github.com/kpeacocke/souschef/commit/3ea40517364d6a5f7946cccccb8dacd9567aae4b))
* polish and ci generation and enhancements ([#133](https://github.com/kpeacocke/souschef/issues/133)) ([6e99528](https://github.com/kpeacocke/souschef/commit/6e99528ee840ba882a0756498a81004f9489a64c))
* Release v3.0.0 ([#185](https://github.com/kpeacocke/souschef/issues/185)) ([e8b5b28](https://github.com/kpeacocke/souschef/commit/e8b5b28ddc9ab5f8b8e79bf28ecacd5986127f1d))
* **server:** enhance error handling for MCP tools with validation and recovery suggestions ([25c1a24](https://github.com/kpeacocke/souschef/commit/25c1a24542583d7f4b2ab3a7ec6cdb04892d2288))
* so many fixes, it's a feature ([#78](https://github.com/kpeacocke/souschef/issues/78)) ([096742b](https://github.com/kpeacocke/souschef/commit/096742b4c889202b015b393fc90012a87b824bd6))
* streamline SonarCloud coverage generation and remove redundant steps ([22a0311](https://github.com/kpeacocke/souschef/commit/22a03111d0e72e106591b43091a4e68e884a8e16))
* terraform! ([#143](https://github.com/kpeacocke/souschef/issues/143)) ([9fc59fe](https://github.com/kpeacocke/souschef/commit/9fc59fe94450135219d618f5899dfa298230f939))
* **testing:** Add comprehensive performance and load tests ([#28](https://github.com/kpeacocke/souschef/issues/28)) ([a494db4](https://github.com/kpeacocke/souschef/commit/a494db4f7ce8e76cff8eb98f02eadf4b603ae4c1))
* **testing:** Add comprehensive real-world Chef cookbook fixtures ([#27](https://github.com/kpeacocke/souschef/issues/27)) ([1a1a63c](https://github.com/kpeacocke/souschef/commit/1a1a63c21a1198c15c0da0fef0c4ccad0ddac81f))
* **tests:** Add comprehensive error handling and edge case tests for CLI and server functionality ([28b8f01](https://github.com/kpeacocke/souschef/commit/28b8f0194761b756ea2d4e876e2ac35fc4d2f3ba))
* UI & Container ([#155](https://github.com/kpeacocke/souschef/issues/155)) ([e266dd1](https://github.com/kpeacocke/souschef/commit/e266dd152d31b17233ffeed05cfa48d91b858c9b))
* ui-containerization ([4b59ef0](https://github.com/kpeacocke/souschef/commit/4b59ef008877b2b244ce019b4983f90233a49407))
* ui-containerization ([4352da9](https://github.com/kpeacocke/souschef/commit/4352da90af163a7ff78ab693ccf0e5c32b00e445))
* ui-containerization ([969f901](https://github.com/kpeacocke/souschef/commit/969f9012898c801b2f4d8fb64f217703cff669e8))
* ui-containerization ([af6769a](https://github.com/kpeacocke/souschef/commit/af6769a460e9be89fcbd7f0c7ab344a71c41cc0f))
* ui-containerization ([b3df2cb](https://github.com/kpeacocke/souschef/commit/b3df2cb5455da830e481774d788e799d0502160a))
* ui-containerization ([e8b5b28](https://github.com/kpeacocke/souschef/commit/e8b5b28ddc9ab5f8b8e79bf28ecacd5986127f1d))
* ui-containerization ([d53fe5f](https://github.com/kpeacocke/souschef/commit/d53fe5fc0fb82b2f43f7c6df5668bb4ef56c8307))
* update release-please-action to specific version for improved stability ([cebf3d9](https://github.com/kpeacocke/souschef/commit/cebf3d96c3b2bce1d072cbe3f9196fd57d0307a3))
* update Terraform provider tests to use dynamic souschef path variable ([8f85355](https://github.com/kpeacocke/souschef/commit/8f8535571ddab87d710856e1a8b33e7fcbf254f8))
* workflow fixes ([#134](https://github.com/kpeacocke/souschef/issues/134)) ([ad72489](https://github.com/kpeacocke/souschef/commit/ad72489e952ebb7f714f8eb1c0110545459db487))
* workflow fixes ([#134](https://github.com/kpeacocke/souschef/issues/134)) ([#135](https://github.com/kpeacocke/souschef/issues/135)) ([565502f](https://github.com/kpeacocke/souschef/commit/565502f9963c1b0a157e395ce4b99d0ef0ed7e45))
* workflow fixes ([#134](https://github.com/kpeacocke/souschef/issues/134)) ([#136](https://github.com/kpeacocke/souschef/issues/136)) ([2a5b709](https://github.com/kpeacocke/souschef/commit/2a5b70917ad3f95b96842afc17d457b368f077e0))


### Bug Fixes

* Add build dependencies to Dockerfile ([9c2e732](https://github.com/kpeacocke/souschef/commit/9c2e732ed4c4c5027eb5b42f103a668544069f1f))
* Add build dependencies to Dockerfile ([98c06bb](https://github.com/kpeacocke/souschef/commit/98c06bb34cfd21b6a3b4884c7423f894f6ccf0cc))
* add cleanup logic for auto-sync branches in post-release workflow ([b7bf6a1](https://github.com/kpeacocke/souschef/commit/b7bf6a18d5d4c03a681d3175dc381f58368c3f26))
* add enablement parameter to configure-pages action ([56e0f75](https://github.com/kpeacocke/souschef/commit/56e0f75d2a6630b9b6fdd74a83a3b8cb2bc0e127))
* add explicit job permissions for release-please workflow ([b2525b6](https://github.com/kpeacocke/souschef/commit/b2525b68a5ec1f13872afdeb43b06ddb51a5217e))
* add issues: write permission for release creation ([dfbf8c3](https://github.com/kpeacocke/souschef/commit/dfbf8c38a53742693135d77f5eb42204400e2930))
* add missing build dependencies for Docker container ([2a2532a](https://github.com/kpeacocke/souschef/commit/2a2532aa599a138031a8d7b64e90d4357c2ddaff))
* add missing permissions for releases in workflow configuration ([a6c2686](https://github.com/kpeacocke/souschef/commit/a6c2686cd95e88f290621ba66bd6d47a459d456f))
* add missing souschef import in test_cli.py ([b402b18](https://github.com/kpeacocke/souschef/commit/b402b184cbe1cdf8ef436b3a4371be4de7749e9c))
* add missing souschef import in test_cli.py ([#158](https://github.com/kpeacocke/souschef/issues/158)) ([c15e9a2](https://github.com/kpeacocke/souschef/commit/c15e9a2f823db5ed060f3aeb8a6824cc529ce047))
* add Python setup to validate job and id-token permission for PyPI attestations ([59ee988](https://github.com/kpeacocke/souschef/commit/59ee98885a8351b16830b939005a7824bae232c0))
* add PyYAML as production dependency for Goss output ([2b1e651](https://github.com/kpeacocke/souschef/commit/2b1e6515d486d31bdbad52e166e257fbf110c11b))
* add sync confirmation message in post-release workflow ([ad9d804](https://github.com/kpeacocke/souschef/commit/ad9d804b9eb81b14acf45a32485b83aedb635ef2))
* add type annotations to pattern extraction ([4a360d4](https://github.com/kpeacocke/souschef/commit/4a360d43260048b0c2228c52a48f68afd81daa1a))
* add VERSION constant to constants.py for health check ([cdd29d3](https://github.com/kpeacocke/souschef/commit/cdd29d31c1996428684123bac78a984279e80da4))
* Apply code formatting and linting fixes ([895b6ea](https://github.com/kpeacocke/souschef/commit/895b6ea1b8af66be9aaee67b5577479f94c80e54))
* build job must checkout release tag, not main ([57fc362](https://github.com/kpeacocke/souschef/commit/57fc362c3bba1e5bb87e27b98790850da93797e8))
* change Release Please trigger to workflow_run ([ea87cef](https://github.com/kpeacocke/souschef/commit/ea87cef1d7b981c16af3f5dae48a8d48ea118e12))
* change release-please trigger back to push ([4d5baed](https://github.com/kpeacocke/souschef/commit/4d5baed463058bc45ba96e11d2d74f850b37c0ff))
* change release-please trigger to workflow_run ([f7ac7f4](https://github.com/kpeacocke/souschef/commit/f7ac7f4442d30bcd149371177505b25a337c136f))
* checkout correct commit in SonarCloud workflow ([19463f2](https://github.com/kpeacocke/souschef/commit/19463f2e5b6a33f7e8b420f331f4b06c3261dc76))
* CI Python 3.14 and doc permalinks ([#121](https://github.com/kpeacocke/souschef/issues/121)) ([9667286](https://github.com/kpeacocke/souschef/commit/96672864faed976cceab1b6b7e6fd49196f23e84))
* CI Python 3.14 and doc permalinks ([#121](https://github.com/kpeacocke/souschef/issues/121)) ([#122](https://github.com/kpeacocke/souschef/issues/122)) ([ca5fc5e](https://github.com/kpeacocke/souschef/commit/ca5fc5e270ee966e6358968a77ae9f99d11f176e))
* CI runs on all main pushes, release-please waits for CI then auto-merges ([2f6275a](https://github.com/kpeacocke/souschef/commit/2f6275a1fed74342e1fded28694ce3cb2e7adfa1))
* CI use Python 3.14 ([#101](https://github.com/kpeacocke/souschef/issues/101)) ([9a9d5fb](https://github.com/kpeacocke/souschef/commit/9a9d5fba2336e5e1f59eb5c3237684cf848a7491))
* CI use Python 3.14 to match pyproject.toml ([73a1c4e](https://github.com/kpeacocke/souschef/commit/73a1c4ec5ffb7369d35a86949ceda23ba1d83353))
* CI workflow must run on main branch for release-please trigger ([12de1dd](https://github.com/kpeacocke/souschef/commit/12de1ddc4fa614e2c9b06a536d1e851f9fb0185e))
* code duplication ([#62](https://github.com/kpeacocke/souschef/issues/62)) ([7b6bc03](https://github.com/kpeacocke/souschef/commit/7b6bc0324cf700d2a91000e86a6e8fa3aec656ed))
* code duplication ([#62](https://github.com/kpeacocke/souschef/issues/62)) ([#63](https://github.com/kpeacocke/souschef/issues/63)) ([0d1a72d](https://github.com/kpeacocke/souschef/commit/0d1a72ddaf43e96e2ed0a8d410afab848aa318a7))
* code smells ([#60](https://github.com/kpeacocke/souschef/issues/60)) ([2a73940](https://github.com/kpeacocke/souschef/commit/2a73940d084eb45d902938d080b3122100857ebf))
* code smells ([#60](https://github.com/kpeacocke/souschef/issues/60)) ([#61](https://github.com/kpeacocke/souschef/issues/61)) ([17c2f7a](https://github.com/kpeacocke/souschef/commit/17c2f7a3a4eba1ef231e27511869511e29f39f6f))
* correct import name for assess_chef_migration_complexity ([b38715e](https://github.com/kpeacocke/souschef/commit/b38715e0138e08389b9038c36e06890e2215bcf7))
* correct release-please workflow trigger and manifest version ([789d6c7](https://github.com/kpeacocke/souschef/commit/789d6c71bbbb94a1fe6a225e81deb7ff17bbf288))
* correct workflow trigger for release-please ([a1c6552](https://github.com/kpeacocke/souschef/commit/a1c65525bd4e91c37367db573ec6ce19018e4ae0))
* correct YAML syntax in post-release workflow ([fcfa23d](https://github.com/kpeacocke/souschef/commit/fcfa23d0a0dd9abc4a82d9017c0606d878877d78))
* coverage and linting ([#186](https://github.com/kpeacocke/souschef/issues/186)) ([b3df2cb](https://github.com/kpeacocke/souschef/commit/b3df2cb5455da830e481774d788e799d0502160a))
* create PR for main-to-develop sync instead of direct push ([a743edd](https://github.com/kpeacocke/souschef/commit/a743edd15f65295609c4bb0ab828b428de41def3))
* Develop ([#51](https://github.com/kpeacocke/souschef/issues/51)) ([bb1fcea](https://github.com/kpeacocke/souschef/commit/bb1fcea0e1586feda509577a574dd034e735cac9))
* disable pymdownx.emoji extension instead of downgrading Python ([63cd5d8](https://github.com/kpeacocke/souschef/commit/63cd5d8a480c56a61687293e09bd8afa0a8a23bd))
* disable pymdownx.emoji to fix docs build ([#95](https://github.com/kpeacocke/souschef/issues/95)) ([556af01](https://github.com/kpeacocke/souschef/commit/556af01586282d73117073933f69ddf9aa8b5150))
* disable PyPI attestations to resolve publishing failures ([fb5b085](https://github.com/kpeacocke/souschef/commit/fb5b0857f040f929aa8482667965907cec8acb91))
* disable Snyk PR checks (test limit reached, main-only) ([d2ed4ba](https://github.com/kpeacocke/souschef/commit/d2ed4ba52af12ef5eca1c807eda3b1817bfc036b))
* downgrade Python to 3.13 for pymdownx.emoji compatibility ([3b11ea3](https://github.com/kpeacocke/souschef/commit/3b11ea32ee82eb81c0bfe3a2734df7566a27305f))
* downgrade Python to 3.13 for pymdownx.emoji compatibility ([#93](https://github.com/kpeacocke/souschef/issues/93)) ([1854aa6](https://github.com/kpeacocke/souschef/commit/1854aa64cb70dc30c69e30d49cf4f4b60611eefa))
* duplication ([#64](https://github.com/kpeacocke/souschef/issues/64)) ([0b3ba07](https://github.com/kpeacocke/souschef/commit/0b3ba07b96335bc63097f46429c2553fd7efca25))
* enable Docker access in devcontainer ([0f68256](https://github.com/kpeacocke/souschef/commit/0f682560117534ad15dfcfbe695ada3c81470b41))
* enable emoji rendering in documentation ([#115](https://github.com/kpeacocke/souschef/issues/115)) ([d700c4a](https://github.com/kpeacocke/souschef/commit/d700c4a6c7d7b6fd9d9925ff7daab3466bb529ff))
* enable emoji rendering with correct Material extensions ([bbe4b6d](https://github.com/kpeacocke/souschef/commit/bbe4b6d12cd781bcf1e1eb96e94bf14f1147240d))
* enable GitHub Pages in docs workflow ([#91](https://github.com/kpeacocke/souschef/issues/91)) ([48a2206](https://github.com/kpeacocke/souschef/commit/48a220665891e7bae681f18aadf49d510ead1d10))
* enable GitHub Pages in docs workflow ([#91](https://github.com/kpeacocke/souschef/issues/91)) ([#92](https://github.com/kpeacocke/souschef/issues/92)) ([1f8bf2c](https://github.com/kpeacocke/souschef/commit/1f8bf2cd30ea0c4e095bf9d138f257e960897b08))
* enable SonarQube analysis on both develop and main branches ([2b3b3f4](https://github.com/kpeacocke/souschef/commit/2b3b3f4484ae9b9da7054e1362273bcb24fad2ed))
* enable SonarQube analysis on PRs by removing branch filter ([b29f3f3](https://github.com/kpeacocke/souschef/commit/b29f3f37eb6969b25a7c3ed833fc7a6a7e5d70d4))
* enforce CI and SonarCloud validation for all release triggers ([114fa5e](https://github.com/kpeacocke/souschef/commit/114fa5ecbcb312bce5f862086dd0e40b59837256))
* enhance Chef guard handling and attribute precedence in README ([f0b280b](https://github.com/kpeacocke/souschef/commit/f0b280b7ff86cb826d162273b6f124023303a607))
* Enhance release workflows to support manual triggering with tag input… ([0b3df0f](https://github.com/kpeacocke/souschef/commit/0b3df0f6ddd29d744fa1457faa4cdedf6e21077b))
* Enhance TAR file extraction with error handling and add cookbook-specific conversion tests ([0911ab2](https://github.com/kpeacocke/souschef/commit/0911ab26a8df8bb5d774186502933b653386d68a))
* ensure absolute path for souschef CLI in Terraform tests ([9f9f7b5](https://github.com/kpeacocke/souschef/commit/9f9f7b514a0c65e61adfdddcb0579494ac32be64))
* handle config file errors gracefully in AI settings and remove unused import in cookbook analysis ([5260576](https://github.com/kpeacocke/souschef/commit/5260576fa8acbb0394915ec8a07b3251a3f5de4c))
* Hotfix/workflow failures ([#246](https://github.com/kpeacocke/souschef/issues/246)) ([b0364ad](https://github.com/kpeacocke/souschef/commit/b0364adf3ad1e538ef0668cce6a3ad0fad5b5ba2))
* implement proper JSON output for assess-cookbook CLI command ([306d392](https://github.com/kpeacocke/souschef/commit/306d3927184379631a5b7b043fa8f2a00ccb7ded))
* import souschef in test_cli.py ([a8aeedf](https://github.com/kpeacocke/souschef/commit/a8aeedf2880c0a2851b6bbfc29e5537f748059bc))
* import souschef in test_cli.py ([#160](https://github.com/kpeacocke/souschef/issues/160)) ([901fb0e](https://github.com/kpeacocke/souschef/commit/901fb0e9e9f35518263c935951f44bf72202dc53))
* improve post-release workflow and README badge ([#166](https://github.com/kpeacocke/souschef/issues/166)) ([2114dd0](https://github.com/kpeacocke/souschef/commit/2114dd05650ff6f1ddafe9a1198360752a644e4d))
* improve post-release workflow and README badge ([#166](https://github.com/kpeacocke/souschef/issues/166)) ([2114dd0](https://github.com/kpeacocke/souschef/commit/2114dd05650ff6f1ddafe9a1198360752a644e4d))
* improve post-release workflow robustness ([7007c7d](https://github.com/kpeacocke/souschef/commit/7007c7d89d8f215add5a78c44c7ef6dddf09d521))
* improve post-release workflow robustness ([f0d24aa](https://github.com/kpeacocke/souschef/commit/f0d24aa43e1703d789d37bcd213bc7e3331b1d95))
* improve post-release workflow robustness ([64046b2](https://github.com/kpeacocke/souschef/commit/64046b21cbb61b88e5f1181014ecffe5bf55ea5f))
* improve Ruby block balance check with word boundaries ([107f4bc](https://github.com/kpeacocke/souschef/commit/107f4bc1dfb5fbaf54459bc6e6caf84ff41855da))
* improve SonarCloud configuration and workflow ([#137](https://github.com/kpeacocke/souschef/issues/137)) ([6b97a87](https://github.com/kpeacocke/souschef/commit/6b97a8761c11de5e815dbe18a6a341e4aaf0bf8b))
* improve SonarCloud configuration section header clarity ([a66855a](https://github.com/kpeacocke/souschef/commit/a66855a504759d7daf5515bb1fa7d79d1285a6da))
* make PyPI publishing optional ([#111](https://github.com/kpeacocke/souschef/issues/111)) ([ba1842b](https://github.com/kpeacocke/souschef/commit/ba1842bf7de9cb53799505b6bbf197d9e221edbd))
* make PyPI publishing optional ([#111](https://github.com/kpeacocke/souschef/issues/111)) ([#112](https://github.com/kpeacocke/souschef/issues/112)) ([04efe8c](https://github.com/kpeacocke/souschef/commit/04efe8cba4bfaaacf4d059fdc8fe3b73c1ad17ec))
* make PyPI publishing optional with continue-on-error ([345d1fd](https://github.com/kpeacocke/souschef/commit/345d1fdf75669cc58218ac11a33b241167bba04e))
* Merge consecutive RUN instructions in Dockerfile ([b87ffa6](https://github.com/kpeacocke/souschef/commit/b87ffa62d800aebe21e05f98fefd81c0d950d5bf))
* Merge pull request [#41](https://github.com/kpeacocke/souschef/issues/41) from kpeacocke/develop ([d539fc7](https://github.com/kpeacocke/souschef/commit/d539fc73cc6e04f9dd6d2e360aec05fd18fd0fa9))
* Merge pull request [#43](https://github.com/kpeacocke/souschef/issues/43) from kpeacocke/develop ([6d73b29](https://github.com/kpeacocke/souschef/commit/6d73b29d8814f6fd16802ba5f686caeb009cf85d))
* pass release tag through job outputs for workflow_dispatch ([ed7c74f](https://github.com/kpeacocke/souschef/commit/ed7c74fb27df93da42e8dbfe7ffb7b03409ee017))
* perms again ([#74](https://github.com/kpeacocke/souschef/issues/74)) ([96cb425](https://github.com/kpeacocke/souschef/commit/96cb425885a739cf87680037cad425dc85739be6))
* perms again ([#74](https://github.com/kpeacocke/souschef/issues/74)) ([#75](https://github.com/kpeacocke/souschef/issues/75)) ([e8f107b](https://github.com/kpeacocke/souschef/commit/e8f107b98c900274fa9c9583c35895a70e585d57))
* post-release workflow should only trigger after releases, not on every push to main ([9bd1d92](https://github.com/kpeacocke/souschef/commit/9bd1d9230f7229c53a00210e152df8ed7cc43ff8))
* post-release workflow timing ([4c3a77c](https://github.com/kpeacocke/souschef/commit/4c3a77cfc5c58487a0fc38fea627de714bacedf9))
* prevent duplicate release-please runs by checking both workflows succeeded ([d0c0081](https://github.com/kpeacocke/souschef/commit/d0c00816f37617ed231808312b447a8a6c798563))
* PyPI publishing not working ([909bc91](https://github.com/kpeacocke/souschef/commit/909bc91059b12840f853d07d4fbda2e986d09acd))
* pyproject.toml Python version to 3.14 ([#103](https://github.com/kpeacocke/souschef/issues/103)) ([1c5bce3](https://github.com/kpeacocke/souschef/commit/1c5bce34f5f7d9960ab3dbffe1b85475ec8d7075))
* reduce code duplication in validation.py ([5ed9c09](https://github.com/kpeacocke/souschef/commit/5ed9c09de9dba2383219492e5ec7a2975d47427c))
* Refine comments and error handling in AI settings and cookbook analysis modules ([9a4adf6](https://github.com/kpeacocke/souschef/commit/9a4adf6aa1ba61634f5c6e0a3bae9574f261c9da))
* release manifest ([#189](https://github.com/kpeacocke/souschef/issues/189)) ([4352da9](https://github.com/kpeacocke/souschef/commit/4352da90af163a7ff78ab693ccf0e5c32b00e445))
* release permissions ([#72](https://github.com/kpeacocke/souschef/issues/72)) ([fa8240e](https://github.com/kpeacocke/souschef/commit/fa8240ef5909baed77f1bc2f3d7ed9333b485d36))
* Release Please workflow to unblock releases ([#82](https://github.com/kpeacocke/souschef/issues/82)) ([63a9fa7](https://github.com/kpeacocke/souschef/commit/63a9fa758cbb39a94e0084c2b8c9352b7262a576))
* Release Please workflow to unblock releases ([#82](https://github.com/kpeacocke/souschef/issues/82)) ([#83](https://github.com/kpeacocke/souschef/issues/83)) ([e256277](https://github.com/kpeacocke/souschef/commit/e2562775b7ac7a1ffba2a735457c4710a0023362))
* release process ([#190](https://github.com/kpeacocke/souschef/issues/190)) ([4b59ef0](https://github.com/kpeacocke/souschef/commit/4b59ef008877b2b244ce019b4983f90233a49407))
* release workflow ([#70](https://github.com/kpeacocke/souschef/issues/70)) ([24e43b6](https://github.com/kpeacocke/souschef/commit/24e43b6b9c7d1d6adbdfa0e806782da1ac8f7fea))
* release workflow ([#70](https://github.com/kpeacocke/souschef/issues/70)) ([#71](https://github.com/kpeacocke/souschef/issues/71)) ([42ef4a3](https://github.com/kpeacocke/souschef/commit/42ef4a3ba0c19d4695313ba6160d7191c59d6ff5))
* release workflow must checkout tag in build job ([#113](https://github.com/kpeacocke/souschef/issues/113)) ([0eeea81](https://github.com/kpeacocke/souschef/commit/0eeea814c4ea844be3cd5c5755c2935ae3dcd0e0))
* release workflow must checkout tag in build job ([#113](https://github.com/kpeacocke/souschef/issues/113)) ([#114](https://github.com/kpeacocke/souschef/issues/114)) ([91fd1d3](https://github.com/kpeacocke/souschef/commit/91fd1d3afd8d0141a1c62c31d4996993b6d4090b))
* release workflows failing due to YAML syntax errors and flawed trigger logic ([2664b94](https://github.com/kpeacocke/souschef/commit/2664b9452922597c69f0c45dedad554af135877e))
* release-please workflow trigger fixes ([9f5f860](https://github.com/kpeacocke/souschef/commit/9f5f8603e155411bc48d74f3ecba0313e63e8bbf))
* remove --strict flag from mkdocs build ([22047a7](https://github.com/kpeacocke/souschef/commit/22047a7ecea098b4e872fe1f5586048efc66a353))
* remove --strict flag from mkdocs build ([#97](https://github.com/kpeacocke/souschef/issues/97)) ([899faca](https://github.com/kpeacocke/souschef/commit/899faca27d46f09676c31aa9e13db29010176b4a))
* Remove 'examples' from sonar.sources to streamline source code configuration ([16a36e8](https://github.com/kpeacocke/souschef/commit/16a36e8faccc7d8a71e553db272bc585f6a44621))
* remove code duplication from server.py ([c1a1253](https://github.com/kpeacocke/souschef/commit/c1a1253b00865169965c12af043a7fcd96c5ab20))
* remove continue-on-error from PyPI publishing to surface real errors ([2666351](https://github.com/kpeacocke/souschef/commit/2666351b38456159af311a5bc39ecb2997158d88))
* remove unnecessary permissions for releases in workflow configuration ([a265f01](https://github.com/kpeacocke/souschef/commit/a265f016294cb9992c40443fde9f15f0b22117ba))
* repair release-please workflow and versioning ([c5907b4](https://github.com/kpeacocke/souschef/commit/c5907b4823cfea11995cdd5c88290034d838428b))
* repair release-please workflow and versioning ([3b63808](https://github.com/kpeacocke/souschef/commit/3b63808cf9efd84857e913f33f3ac9b52952e57f))
* resolve all 10 mkdocs warnings ([cbc13fa](https://github.com/kpeacocke/souschef/commit/cbc13fa4bec6fd0071b4e94f4562a7183f9081a7))
* resolve all mkdocs warnings ([#99](https://github.com/kpeacocke/souschef/issues/99)) ([3eeb26c](https://github.com/kpeacocke/souschef/commit/3eeb26c683ffdff0d0a1d89ff2f01093c6f2bbb3))
* resolve all SonarQube code quality issues ([62b1d5b](https://github.com/kpeacocke/souschef/commit/62b1d5b5d9a3271f736fe9fedac08d157804ef93))
* resolve merge conflict in release-please workflow ([fff6f31](https://github.com/kpeacocke/souschef/commit/fff6f317de3566cc8c2e43ebfcb80bc9364bfb8e))
* resolve mypy type errors in _parse_properties function ([a0ee21c](https://github.com/kpeacocke/souschef/commit/a0ee21ce0399d111341ee0e6c0c4d7786db8e259))
* resolve YAML validation warnings and floating point comparison ([d1c8f73](https://github.com/kpeacocke/souschef/commit/d1c8f736c465c414788243c29241eb3d13844a88))
* restore automatic release-please workflow on main branch pushes ([2eca058](https://github.com/kpeacocke/souschef/commit/2eca0587ce89f8b4229b39d8961b369fe041983f))
* restore working server.py from c1186eb (e2281e3 introduced syntax errors) ([fdd25c2](https://github.com/kpeacocke/souschef/commit/fdd25c2284d682a5314b4092e3ae130e12f5fcdb))
* simplify release automation with auto-merge ([d539fc7](https://github.com/kpeacocke/souschef/commit/d539fc73cc6e04f9dd6d2e360aec05fd18fd0fa9))
* simplify Release Please to trigger on push and let it handle its own logic ([e51e022](https://github.com/kpeacocke/souschef/commit/e51e022fc23cacc199bca80dd4606691df21b612))
* simplify release-please workflow trigger ([ff976f2](https://github.com/kpeacocke/souschef/commit/ff976f26a2ff3295cadb332a80ee992f6044fe72))
* sonar scan ([#187](https://github.com/kpeacocke/souschef/issues/187)) ([af6769a](https://github.com/kpeacocke/souschef/commit/af6769a460e9be89fcbd7f0c7ab344a71c41cc0f))
* sonar scanning ([#188](https://github.com/kpeacocke/souschef/issues/188)) ([969f901](https://github.com/kpeacocke/souschef/commit/969f9012898c801b2f4d8fb64f217703cff669e8))
* swap CLI and MCP server entry points ([7da2e47](https://github.com/kpeacocke/souschef/commit/7da2e47b3de47d63dca37ad73bc1b92cdeda6332))
* sync release workflows and bump version to 2.4.0 ([0eeb099](https://github.com/kpeacocke/souschef/commit/0eeb099fd5492d15550338d594e9ed01df47cb79))
* trigger Release Please on direct push to main to ensure releases are created ([db42894](https://github.com/kpeacocke/souschef/commit/db42894ccf27b18a23b088ef624e3331d3041942))
* triggers ([#68](https://github.com/kpeacocke/souschef/issues/68)) ([6f2ca0d](https://github.com/kpeacocke/souschef/commit/6f2ca0d3d989e798c30a1c6591c1f7b37c7dfa77))
* triggers ([#68](https://github.com/kpeacocke/souschef/issues/68)) ([#69](https://github.com/kpeacocke/souschef/issues/69)) ([6a6c83f](https://github.com/kpeacocke/souschef/commit/6a6c83f5c4b4f5b295f4af159e1f334e5c7c5543))
* update CI and docs workflows to Python 3.14 ([d0fd569](https://github.com/kpeacocke/souschef/commit/d0fd569f5b231f9d77cd7644b08a27319081133b))
* update CI Python version to 3.14 to match coverage upload condition ([710833a](https://github.com/kpeacocke/souschef/commit/710833a1af50403f6a2c30ac44f4368534081114))
* update CI workflows to improve branch validation and consistency ([33e000f](https://github.com/kpeacocke/souschef/commit/33e000f5d0d4799d6579cc1f7f263e6b6b071e4d))
* update CLI commands in CI workflows to use 'souschef' instead of 'souschef-cli' ([21a8bb2](https://github.com/kpeacocke/souschef/commit/21a8bb2482dd9eee8540ce35191f27c09f32c66a))
* update CodeQL suppression comments from lgtm to codeql syntax ([ca0e55e](https://github.com/kpeacocke/souschef/commit/ca0e55e1ee36e5d7ccaed4202314ab4e53a6f583))
* Update error message for unsupported Red Hat domain in AI settings ([78a4ed7](https://github.com/kpeacocke/souschef/commit/78a4ed7e691edc9bff75bed023df0bbb0c989bd9))
* update GH_TOKEN reference in release workflow to use github.token ([a989008](https://github.com/kpeacocke/souschef/commit/a98900836527afdc9a1ba58f07c916f81ff986c9))
* update GH_TOKEN reference in release workflow to use github.token ([#76](https://github.com/kpeacocke/souschef/issues/76)) ([8b4b49a](https://github.com/kpeacocke/souschef/commit/8b4b49a003dff90353d98a57c21539682366e3bd))
* Update import statements for AI libraries to improve type checking ([15ef651](https://github.com/kpeacocke/souschef/commit/15ef65146aa9d0e617f3a164790d2a2ac3c4a49a))
* update manifest and versions to v2.7.3 ([e4092c4](https://github.com/kpeacocke/souschef/commit/e4092c4156501c8bcfd9de0d85dfac672ca930a6))
* update post-release workflow to handle pull requests and sync main to develop ([dd26be9](https://github.com/kpeacocke/souschef/commit/dd26be9e6bce9ce61c3975329483172f2eb7458e))
* update post-release workflow to handle pull requests and sync main to develop ([#162](https://github.com/kpeacocke/souschef/issues/162)) ([30e0b99](https://github.com/kpeacocke/souschef/commit/30e0b99af0e9b351085b18919aaea684cd95ef42))
* update post-release workflow to trigger on release and reset develop to main ([e0bdee5](https://github.com/kpeacocke/souschef/commit/e0bdee5dad92906a8c1b7b9d8a1b7e7df2396cb8))
* update pyproject.toml to require Python &gt;=3.14 ([dd112aa](https://github.com/kpeacocke/souschef/commit/dd112aa6084c6b1bac6762ebadab767b18ef24fe))
* update pyproject.toml version parsing to open in binary mode ([ee983b4](https://github.com/kpeacocke/souschef/commit/ee983b4c1467adb87a7c12cc72519054fba3337e))
* update pyproject.toml with additional metadata and classifiers ([fa2dbe3](https://github.com/kpeacocke/souschef/commit/fa2dbe34403b5ce647475780fb7148d46a35a3ff))
* update Python requirement to &gt;=3.14,&lt;4.0 (reverted by PR merge) ([2a2e305](https://github.com/kpeacocke/souschef/commit/2a2e3057da8486e9aab44ae8772160d6b1b62b7b))
* update Python version to &gt;=3.14,&lt;4.0 ([fc4c1ea](https://github.com/kpeacocke/souschef/commit/fc4c1ea3a2b65b303c2f0b230860499fedf775c7))
* update README badge to show GitHub release version instead of PyPI ([5a7a070](https://github.com/kpeacocke/souschef/commit/5a7a070942f89e20a8582fbe13c4068f5cef23a3))
* Update sonar.sources and exclusions for improved code analysis ([f94d94d](https://github.com/kpeacocke/souschef/commit/f94d94d6709621557ca92c505fefd21d12d13818))
* update SonarQube workflow to trigger on Main Branch Validation ([ccd428d](https://github.com/kpeacocke/souschef/commit/ccd428d88dee1f0ea28b268cb658be43c8b6a3c9))
* update token reference in release workflow to use github.token ([4e11a9a](https://github.com/kpeacocke/souschef/commit/4e11a9afe318ae81af88f417e26913a5d3461543))
* update token references in release workflow to use secrets.RELEASE_TOKEN ([80f7e3f](https://github.com/kpeacocke/souschef/commit/80f7e3f72340b0aa241b37d56075e5cde5430cda))
* update VERSION to 2.7.3 ([bbdce85](https://github.com/kpeacocke/souschef/commit/bbdce8543d2878c54bff065ab4d3ff4747c957db))
* use # symbol for doc permalinks instead of ¶ ([e0a61f8](https://github.com/kpeacocke/souschef/commit/e0a61f891835868db546ecab959935336269fbf9))
* use 1.24.x for Go version in GitHub Actions ([d939f4e](https://github.com/kpeacocke/souschef/commit/d939f4e7cb491ad4d81be130dfffa15536b5d97a))
* use check-regexp for CI and CodeQL check names ([3f56080](https://github.com/kpeacocke/souschef/commit/3f560808b4d1932113d34f9117100a51c48bfe18))
* use correct GitHub Actions permissions for release-please ([ef33f43](https://github.com/kpeacocke/souschef/commit/ef33f43055eb20dd8b5c0645d52183c51b22ca5b))
* use dynamic fixture paths in Terraform provider tests ([18973d6](https://github.com/kpeacocke/souschef/commit/18973d678e060257f59d0a236fa1c31e1814c3d7))
* use env vars instead of direct input interpolation in run blocks ([c608150](https://github.com/kpeacocke/souschef/commit/c608150512eda51d62c428b88638d03262000303))
* use environment variable for souschef path in cost estimate test ([fdccbac](https://github.com/kpeacocke/souschef/commit/fdccbac6d3a4890e50d8167e25da2081e2a59afa))
* use getFixturePath() in assessment and migration tests ([8ca52ed](https://github.com/kpeacocke/souschef/commit/8ca52ed5718706b447e4651810b5eac5c349a35e))
* use GITHUB_TOKEN in release-please workflow ([#106](https://github.com/kpeacocke/souschef/issues/106)) ([3a57f97](https://github.com/kpeacocke/souschef/commit/3a57f979dd7126771474b9af0d2ecfd5383d5029))
* use GITHUB_TOKEN instead of RELEASE_TOKEN in release-please workflow ([029c914](https://github.com/kpeacocke/souschef/commit/029c9143bd93777244d4c44c78d2ffe3e792ee0f))
* use GITHUB_TOKEN instead of RELEASE_TOKEN to fix permission issues ([b4b81a7](https://github.com/kpeacocke/souschef/commit/b4b81a760c608393a179d272f94cc76b2bc4af36))
* use push trigger for release-please to create releases ([6d73b29](https://github.com/kpeacocke/souschef/commit/6d73b29d8814f6fd16802ba5f686caeb009cf85d))
* use push trigger for release-please to create releases ([49b05c6](https://github.com/kpeacocke/souschef/commit/49b05c6afb421ee8e99d81d79ec554d5056bcf89))
* use rebase instead of merge to avoid sync commit clutter ([193881b](https://github.com/kpeacocke/souschef/commit/193881b8dee5ee1e1a91bf4bb290f83662c6d807))
* use RELEASE_TOKEN for release-please to enable release creation ([6deffab](https://github.com/kpeacocke/souschef/commit/6deffabc3d9de52b5d9d85df134bea3d679f7ae4))
* use safe dictionary access for control title ([15f1501](https://github.com/kpeacocke/souschef/commit/15f150172733bcedf64b454b3201ea8ed6b31235))
* various issues ([e4c2ae0](https://github.com/kpeacocke/souschef/commit/e4c2ae0c3f01a06ec3d16754937c53d948a31ee5))
* verify and relocate coverage.xml for SonarCloud analysis ([2b68570](https://github.com/kpeacocke/souschef/commit/2b68570d57bd15643b9cbe74cc0913be0347de6d))
* workflows ([#139](https://github.com/kpeacocke/souschef/issues/139)) ([4a0ee77](https://github.com/kpeacocke/souschef/commit/4a0ee77c0d88afb35de3110d88e5a98968b6c992))


### Reverts

* restore RELEASE_TOKEN in release-please workflow ([bbde735](https://github.com/kpeacocke/souschef/commit/bbde73512bffb50bb69302a2ec4e64929b350550))
* restore specific YAML custom tags for security ([eef6d32](https://github.com/kpeacocke/souschef/commit/eef6d3213a72c6ec278f13026e921adba921469d))


### Documentation

* add comprehensive Terraform provider documentation to docs/ ([16973ff](https://github.com/kpeacocke/souschef/commit/16973ffaf78321a2ac0f3c025d025bb7257fb621))
* add comprehensive Terraform provider documentation with Australian English ([734a975](https://github.com/kpeacocke/souschef/commit/734a975782b90958fdf765a55bf79313aae8aff8))
* add comprehensive testing improvement roadmap ([a4655d7](https://github.com/kpeacocke/souschef/commit/a4655d7d738152f1747bf871fc0ac4ea80630b08))
* add ServerSpec and Goss examples to user documentation ([7eb85dd](https://github.com/kpeacocke/souschef/commit/7eb85ddc615469993ea001e5cf14e9f4c67f48c4))
* clarify release-please trigger mechanism ([2712049](https://github.com/kpeacocke/souschef/commit/2712049118ba0ebbe2ba16353cc4fa89bcfc3a16))
* clarify Terraform provider alpha status and CLI requirements ([fc8305d](https://github.com/kpeacocke/souschef/commit/fc8305de1cb979186bd9a1ad72089c59ac3a3f6f))
* clean up temporary docs and update roadmap ([d934b76](https://github.com/kpeacocke/souschef/commit/d934b763125124e8fad0a921c468a95d3e0f0ea5))
* correct breaking change version bump example for pre-1.0.0 ([4570ca0](https://github.com/kpeacocke/souschef/commit/4570ca0cb6eb57cb2009dc120d0579fffeadc172))
* document Phase 3 completion and tech debt elimination ([26d9c9c](https://github.com/kpeacocke/souschef/commit/26d9c9c9b2c265073fd086974f564e5223830f21))
* mark Phase 1 complete - all HIGH priority tech debt addressed ([36251dd](https://github.com/kpeacocke/souschef/commit/36251dd1a8223348cdc1baea67ede1a9cbd1f69d))
* **readme:** add guard parser to Phase 1 completions ([e7c33cf](https://github.com/kpeacocke/souschef/commit/e7c33cf9a46e72a29ff64aad57793f9288c82119))
* **readme:** update roadmap to reflect completed error handling and technical debt Phase 1 ([45f5bcb](https://github.com/kpeacocke/souschef/commit/45f5bcb883d74156a601a2c62d57b8979907877b))
* remove alpha warnings - CLI commands now implemented ([60541ed](https://github.com/kpeacocke/souschef/commit/60541ed4a894bd9128a67e41107c7c9dcc1ede68))
* update Phase 2 completion status ([76cb303](https://github.com/kpeacocke/souschef/commit/76cb303f63e8db08012864fa5392b115c9bd4fc1))
* update Phase 2 progress - 2/5 complete ([7bf89cc](https://github.com/kpeacocke/souschef/commit/7bf89cc474b8a8ffc5de55c09d504e15900f7aee))
* update progress tracking for guard parser completion ([12c66d7](https://github.com/kpeacocke/souschef/commit/12c66d7e08543d15e3a03723e13343cd8dd0d588))
* update Python version badge to 3.14+ ([967ffa6](https://github.com/kpeacocke/souschef/commit/967ffa61d42c47e4ba82e3a0e1e73cb8bf83ba04))
* Update README with CI/CD pipeline generation feature ([5d6e618](https://github.com/kpeacocke/souschef/commit/5d6e618dab0eb2e4be78c50aeb12ec8f665433d5))
* Update README with Docker containerization instructions ([bdfde8a](https://github.com/kpeacocke/souschef/commit/bdfde8a6768d1a0d99ef73873ab7a31ed9936b5d))
* Update roadmap and add profiling examples ([f3eb5ae](https://github.com/kpeacocke/souschef/commit/f3eb5ae3fa39f5699b484ad7e9093ffd544f3fc0))
* update technical debt progress - Phase 1 complete ([f0073cb](https://github.com/kpeacocke/souschef/commit/f0073cbe606385fccb1110a1e7815e39c57a4607))

## [2.8.2](https://github.com/kpeacocke/souschef/compare/v2.8.0...v2.8.2) (2026-01-22)


### Miscellaneous Chores

* manual version alignment to restore release automation

## [2.7.3](https://github.com/kpeacocke/souschef/compare/v2.7.2...v2.7.3) (2026-01-16)


### Bug Fixes

* improve post-release workflow robustness ([7007c7d](https://github.com/kpeacocke/souschef/commit/7007c7d89d8f215add5a78c44c7ef6dddf09d521))

## [2.7.2](https://github.com/kpeacocke/souschef/compare/v2.7.1...v2.7.2) (2026-01-16)


### Bug Fixes

* add missing build dependencies for Docker container ([2a2532a](https://github.com/kpeacocke/souschef/commit/2a2532aa599a138031a8d7b64e90d4357c2ddaff))

## [2.7.1](https://github.com/kpeacocke/souschef/compare/v2.7.0...v2.7.1) (2026-01-16)


### Bug Fixes

* disable PyPI attestations to resolve publishing failures ([fb5b085](https://github.com/kpeacocke/souschef/commit/fb5b0857f040f929aa8482667965907cec8acb91))

## [2.7.0](https://github.com/kpeacocke/souschef/compare/v2.6.1...v2.7.0) (2026-01-16)


### Features

* configure devcontainer to mount docker.sock from host ([30277f9](https://github.com/kpeacocke/souschef/commit/30277f90be4b0d26d068861faa2a8104e25e7189))

## [2.6.1](https://github.com/kpeacocke/souschef/compare/v2.6.0...v2.6.1) (2026-01-16)


### Bug Fixes

* add VERSION constant to constants.py for health check ([cdd29d3](https://github.com/kpeacocke/souschef/commit/cdd29d31c1996428684123bac78a984279e80da4))
* release-please workflow trigger fixes ([9f5f860](https://github.com/kpeacocke/souschef/commit/9f5f8603e155411bc48d74f3ecba0313e63e8bbf))

## [2.6.0](https://github.com/kpeacocke/souschef/compare/v2.5.8...v2.6.0) (2026-01-16)


### Features

* Add containerization support for SousChef UI ([2779a73](https://github.com/kpeacocke/souschef/commit/2779a73ab8bc7b8dfe4ab6aba87178691c94d3bf))
* Add containerization support for SousChef UI ([#169](https://github.com/kpeacocke/souschef/issues/169)) ([290aadb](https://github.com/kpeacocke/souschef/commit/290aadb22e43ca0435a5951af56983204a094e3d))


### Bug Fixes

* Add build dependencies to Dockerfile ([9c2e732](https://github.com/kpeacocke/souschef/commit/9c2e732ed4c4c5027eb5b42f103a668544069f1f))
* Add build dependencies to Dockerfile ([98c06bb](https://github.com/kpeacocke/souschef/commit/98c06bb34cfd21b6a3b4884c7423f894f6ccf0cc))
* Merge consecutive RUN instructions in Dockerfile ([b87ffa6](https://github.com/kpeacocke/souschef/commit/b87ffa62d800aebe21e05f98fefd81c0d950d5bf))

## [2.5.8](https://github.com/kpeacocke/souschef/compare/v2.5.7...v2.5.8) (2026-01-15)


### Bug Fixes

* correct YAML syntax in post-release workflow ([fcfa23d](https://github.com/kpeacocke/souschef/commit/fcfa23d0a0dd9abc4a82d9017c0606d878877d78))
* post-release workflow should only trigger after releases, not on every push to main ([9bd1d92](https://github.com/kpeacocke/souschef/commit/9bd1d9230f7229c53a00210e152df8ed7cc43ff8))
* post-release workflow timing ([4c3a77c](https://github.com/kpeacocke/souschef/commit/4c3a77cfc5c58487a0fc38fea627de714bacedf9))

## [2.5.7](https://github.com/kpeacocke/souschef/compare/v2.5.6...v2.5.7) (2026-01-15)


### Bug Fixes

* improve post-release workflow and README badge ([#166](https://github.com/kpeacocke/souschef/issues/166)) ([2114dd0](https://github.com/kpeacocke/souschef/commit/2114dd05650ff6f1ddafe9a1198360752a644e4d))
* improve post-release workflow and README badge ([#166](https://github.com/kpeacocke/souschef/issues/166)) ([2114dd0](https://github.com/kpeacocke/souschef/commit/2114dd05650ff6f1ddafe9a1198360752a644e4d))

## [2.5.6](https://github.com/kpeacocke/souschef/compare/v2.5.5...v2.5.6) (2026-01-15)


### Bug Fixes

* update pyproject.toml with additional metadata and classifiers ([fa2dbe3](https://github.com/kpeacocke/souschef/commit/fa2dbe34403b5ce647475780fb7148d46a35a3ff))

## [2.5.5](https://github.com/kpeacocke/souschef/compare/v2.5.4...v2.5.5) (2026-01-15)


### Bug Fixes

* add Python setup to validate job and id-token permission for PyPI attestations ([59ee988](https://github.com/kpeacocke/souschef/commit/59ee98885a8351b16830b939005a7824bae232c0))

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
- Major version bump to v3
- Enhanced AI integration features
- Improved Chef to Ansible conversion accuracy

### Changed
- Updated dependencies
- Refactored internal modules for better performance

### Fixed
- Various bug fixes and improvements
