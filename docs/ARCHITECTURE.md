# SousChef Architecture Declaration

**Version:** 2.0
**Last Updated:** 2026-03-06
**Status:** Approved & Enforced via SonarCloud

This document is the **authoritative architectural declaration** for SousChef. All code must adhere to the structure, dependencies, and boundaries defined here.

## Quick Navigation

- [Architectural Vision](#architectural-vision)
- [Layered Architecture](#layered-architecture)
- [Container Definitions](#container-definitions)
- [Dependency Matrix](#dependency-matrix)
- [Module Placement Rules](#module-placement-rules)
- [SonarCloud Enforcement](#sonarcloud-enforcement)
- [Growth Guidelines](#growth-guidelines)

## Architectural Vision

SousChef is evolving from a Chef-to-Ansible converter into a **multi-source, multi-target infrastructure-as-code transformation platform** with enterprise features:

### Transformation Capabilities (Current & Planned)
- ✅ **Chef** → Ansible (current)
- ✅ **Puppet** → Ansible (current)
- 🔄 **Salt** → Ansible (planned)
- ✅ **Bash scripts** → Ansible
- ✅ **PowerShell scripts** → Ansible
- 🔄 **Multi-target**: Ansible, Terraform, CloudFormation (via IR)

### Enterprise Features (Planned)
- 🔄 **REST API** - Programmatic access to all capabilities
- 🔄 **Authentication & RBAC** - Role-based access control
- 🔄 **Audit Logging** - Compliance and change tracking
- 🔄 **Team Collaboration** - Multi-user workflows
- 🔄 **Performance Benchmarking** - Profiling and optimisation metrics
- 🔄 **Integrations** - GitHub, GitLab, AWX, Jira, Slack
- 🔄 **UI Enhancements** - Dark mode, accessibility, analytics, AI recommendations

### Design Principles
1. **Separation of Concerns** - Each container handles one responsibility
2. **Dependency Discipline** - Lower layers never depend on higher layers
3. **Plugin Architecture** - Extensible parser/generator framework via IR
4. **API-First** - All features accessible via REST API
5. **Security by Design** - Auth, RBAC, and audit at the core
6. **Observable** - Performance metrics, logging, and analytics throughout

## Layered Architecture

SousChef follows a **strict layered architecture** where dependencies only flow downward. Higher layers can depend on lower layers, but never the reverse.

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 7: User Interfaces                                    │
│ cli/, ui/, server.py (MCP)                                  │
│ (Depends on: orchestrators, api)                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 6: Orchestration                                      │
│ orchestrators/, assessment.py, deployment.py                │
│ (Depends on: parsers, converters, generators, integrations) │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: Integration & API                                  │
│ api/, integrations/                                         │
│ (Depends on: auth, audit, storage, orchestrators)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: Services                                           │
│ auth/, audit/, benchmarking/                                │
│ (Depends on: core, storage)                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Domain Logic                                       │
│ parsers/, converters/, generators/                          │
│ (Depends on: core, ir, storage, filesystem)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Data & Infrastructure                              │
│ storage/, filesystem/, ir/                                  │
│ (Depends on: core)                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Foundation                                         │
│ core/                                                       │
│ (No dependencies - provides utilities, constants, errors)   │
└─────────────────────────────────────────────────────────────┘
```

## Container Definitions

### Layer 1: Foundation

#### `core/` - Shared Utilities
**Purpose:** Foundation layer providing reusable utilities, constants, and base classes.
**Status:** ✅ Exists
**Dependencies:** None (foundation layer)
**Contains:**
- `constants.py` - Application-wide constants
- `errors.py` - Custom exception classes
- `path_utils.py` - Path normalization and validation
- `ruby_utils.py` - Ruby value parsing utilities
- `validation.py` - Input validation helpers
- `ansible_versions.py` - Ansible version compatibility data
- `metrics.py` - Effort/timeline calculation utilities
- `logging.py` - Logging configuration
- `caching.py` - Caching mechanisms

**Rules:**
- ❌ NEVER import from any other souschef module
- ✅ Only import from Python stdlib and third-party libraries
- ✅ Keep logic minimal - utilities only, no business logic

---

### Layer 2: Data & Infrastructure

#### `storage/` - Data Persistence
**Purpose:** Database and blob storage abstractions.
**Status:** ✅ Exists (database.py, blob.py)
**Dependencies:** `core/`
**Contains:**
- `database.py` - PostgreSQL/SQLite database access
- `blob.py` - Object storage (MinIO/S3) access
- `models.py` - Data models and ORM definitions

**Rules:**
- ✅ Can import from: `core/`
- ❌ Cannot import from: any other containers

#### `filesystem/` - File Operations
**Purpose:** Safe file system operations with validation.
**Status:** ✅ Exists
**Dependencies:** `core/`
**Contains:**
- `operations.py` - Directory/file operations with safety checks

**Rules:**
- ✅ Can import from: `core/`
- ❌ Cannot import from: any other containers

#### `ir/` - Intermediate Representation
**Purpose:** Abstract, tool-agnostic representation of infrastructure configurations.
**Status:** ✅ Exists
**Dependencies:** `core/`
**Contains:**
- `schema.py` - IRGraph, IRNode, IRAction data structures
- `versioning.py` - Version management and schema evolution
- `plugin.py` - SourceParser/TargetGenerator plugin framework

**Rules:**
- ✅ Can import from: `core/`
- ❌ Cannot import from: any other containers
- 🎯 **Key Design:** Tool-agnostic - no Chef/Puppet/Ansible-specific code

---

### Layer 3: Domain Logic

#### `parsers/` - Input Parsing
**Purpose:** Extract structured data from source configuration management tools.
**Status:** ✅ Exists (Chef parsers, PowerShell parser, Bash parser, Puppet parser); 🔄 Planned (Salt)
**Dependencies:** `core/`, `ir/`, `filesystem/`
**Contains:**
- `recipe.py` - Chef recipe parser
- `metadata.py` - Chef metadata parser
- `attributes.py` - Chef attributes parser
- `template.py` - ERB template parser
- `habitat.py` - Habitat plan parser
- `inspec.py` - InSpec profile parser
- `ansible_inventory.py` - Ansible inventory parser
- ✅ `puppet.py` - Puppet manifest parser (15 resource types, unsupported construct detection)
- 🔄 `salt.py` - Salt state parser (planned)
- ✅ `bash.py` - Bash script parser (13 operation categories, confidence scoring, sensitive data detection)
- ✅ `powershell.py` - PowerShell script parser

**Rules:**
- ✅ Can import from: `core/`, `ir/`, `filesystem/`
- ❌ Cannot import from: `converters/`, `generators/`, `orchestrators/`, `api/`, `ui/`, `cli/`
- 🎯 **Key Design:** Read-only - extract structure without transformation

#### `converters/` - Transformation Logic
**Purpose:** Transform parsed data into intermediate or target formats.
**Status:** ✅ Exists (Chef→Ansible, PowerShell→Ansible, Bash→Ansible, Puppet→Ansible); 🔄 Planned (multi-target)
**Dependencies:** `core/`, `parsers/`, `ir/`
**Contains:**
- `playbook.py` - Recipe → Ansible playbook
- `resource.py` - Resource → Ansible task
- `habitat.py` - Habitat → Docker
- `template.py` - ERB → Jinja2
- `conversion_rules.py` - Transformation rules engine
- ✅ `puppet_to_ansible.py` - Puppet → Ansible (15 resource types + AI-assisted conversion)
- 🔄 `salt_to_ansible.py` - Salt → Ansible (planned)
- ✅ `powershell.py` - PowerShell → Ansible (exists)
- ✅ `bash_to_ansible.py` - Bash → Ansible (exists)

**Rules:**
- ✅ Can import from: `core/`, `parsers/`, `ir/`
- ❌ Cannot import from: `generators/`, `orchestrators/`, `api/`, `ui/`, `cli/`
- 🎯 **Key Design:** Pure transformation - no I/O, no orchestration

#### `generators/` - Output Generation
**Purpose:** Generate target configuration files from IR or converter output.
**Status:** ✅ Exists (repo.py, powershell.py)
**Dependencies:** `core/`, `converters/`, `ir/`, `filesystem/`
**Contains:**
- `repo.py` - Ansible repository structure generation
- ✅ `powershell.py` - Windows inventory, group_vars, requirements.yml, role skeleton, AWX job template, fidelity report
- 🔄 `terraform.py` - Terraform module generation (planned)
- 🔄 `cloudformation.py` - CloudFormation template generation (planned)

**Rules:**
- ✅ Can import from: `core/`, `converters/`, `ir/`, `filesystem/`
- ❌ Cannot import from: `orchestrators/`, `api/`, `ui/`, `cli/`

---

### Layer 4: Services

#### `auth/` - Authentication & Authorization
**Purpose:** User authentication, role-based access control (RBAC).
**Status:** 🔄 Planned
**Dependencies:** `core/`, `storage/`
**Contains:**
- `authentication.py` - User login/logout, session management
- `rbac.py` - Role and permission management
- `tokens.py` - JWT token generation and validation
- `policies.py` - Access policy definitions

**Rules:**
- ✅ Can import from: `core/`, `storage/`
- ❌ Cannot import from: domain logic, orchestrators, integrations, UI

#### `audit/` - Audit Logging
**Purpose:** Compliance, change tracking, audit trail.
**Status:** 🔄 Planned
**Dependencies:** `core/`, `storage/`, `auth/`
**Contains:**
- `logger.py` - Audit event logging
- `events.py` - Audit event definitions
- `compliance.py` - Compliance report generation

**Rules:**
- ✅ Can import from: `core/`, `storage/`, `auth/`
- ❌ Cannot import from: domain logic, orchestrators, integrations, UI

#### `benchmarking/` - Performance Metrics
**Purpose:** Performance profiling, benchmarking, optimisation metrics.
**Status:** ✅ Exists (profiling.py - needs migration)
**Dependencies:** `core/`, `storage/`
**Contains:**
- `profiler.py` - Code execution profiling
- `metrics.py` - Performance metric collection
- `reports.py` - Benchmark report generation

**Rules:**
- ✅ Can import from: `core/`, `storage/`
- ❌ Cannot import from: domain logic, orchestrators, integrations, UI

---

### Layer 5: Integration & API

#### `integrations/` - External Systems
**Purpose:** Integration with GitHub, GitLab, AWX, Jira, Slack, etc.
**Status:** ✅ Partial (github/); 🔄 Planned (others)
**Dependencies:** `core/`, `auth/`, `audit/`, `storage/`
**Contains:**
- `github/` - GitHub API client and workflows
- 🔄 `gitlab.py` - GitLab API integration (planned)
- 🔄 `awx.py` - AWX/Tower API client (planned)
- 🔄 `jira.py` - Jira issue tracking (planned)
- 🔄 `slack.py` - Slack notifications (planned)

**Rules:**
- ✅ Can import from: `core/`, `auth/`, `audit/`, `storage/`
- ❌ Cannot import from: domain logic (parsers/converters), orchestrators, UI

#### `api/` - REST API
**Purpose:** RESTful API for programmatic access to all platform capabilities.
**Status:** 🔄 Planned
**Dependencies:** `core/`, `auth/`, `audit/`, `storage/`, `orchestrators/`
**Contains:**
- `routes/` - API endpoint definitions
- `schemas.py` - Request/response schemas (Pydantic)
- `middleware.py` - Authentication, rate limiting, CORS
- `docs.py` - OpenAPI/Swagger documentation

**Rules:**
- ✅ Can import from: `core/`, `auth/`, `audit/`, `storage/`, `orchestrators/`
- ❌ Cannot import from: `cli/`, `ui/`, `server.py` (MCP)
- 🎯 **Key Design:** Stateless, RESTful, versioned (/v1/, /v2/)

---

### Layer 6: Orchestration

#### `orchestrators/` - Workflow Coordination
**Purpose:** High-level workflows coordinating parsers, converters, generators.
**Status:** ✅ Partial (assessment.py, deployment.py as top-level); 🔄 Needs refactor
**Dependencies:** `core/`, `parsers/`, `converters/`, `generators/`, `integrations/`, `storage/`
**Contains:**
- `migration.py` - End-to-end migration workflows
- `analysis.py` - Codebase analysis orchestration
- `validation.py` - Multi-stage validation workflows
- `deployment.py` - Deployment orchestration (refactored from top-level)
- `assessment.py` - Assessment workflows (refactored from top-level)

**Rules:**
- ✅ Can import from: `core/`, `parsers/`, `converters/`, `generators/`, `integrations/`, `storage/`, `auth/`, `audit/`, `benchmarking/`
- ❌ Cannot import from: `api/`, `cli/`, `ui/`, `server.py`
- 🎯 **Key Design:** Coordinates lower layers, implements business workflows

---

### Layer 7: User Interfaces

#### `cli/` - Command-Line Interface
**Purpose:** Terminal-based user interface.
**Status:** ✅ Exists (cli.py, cli_v2_commands.py, cli_registry.py - needs consolidation)
**Dependencies:** `orchestrators/`, `api/` (optional)
**Contains:**
- `commands/` - CLI command implementations
- `interactive.py` - Interactive mode (prompts, wizards)

**Rules:**
- ✅ Can import from: `orchestrators/`, `api/` (if using REST API), `core/`
- ❌ Cannot import from: `ui/`, `server.py`, domain logic directly
- 🎯 **Key Design:** Thin wrapper around orchestrators

#### `ui/` - Web User Interface
**Purpose:** Browser-based dashboard and visualizations.
**Status:** ✅ Exists (Streamlit); 🔄 Planned enhancements (Next.js, analytics, dark mode)
**Dependencies:** `api/`, `orchestrators/`
**Contains:**
- `app.py` - Main Streamlit application
- `pages/` - Dashboard pages
- `components/` - Reusable UI components
- 🔄 `analytics.py` - Usage analytics and insights (planned)
- 🔄 `recommendations.py` - AI-powered smart recommendations (planned)
- 🔄 `themes.py` - Dark mode and accessibility themes (planned)

**Rules:**
- ✅ Can import from: `api/`, `orchestrators/` (for direct calls during prototyping), `core/`
- ❌ Cannot import from: `cli/`, `server.py`, domain logic directly
- 🎯 **Key Design:** API-first - all actions call REST API (when available)

#### `server.py` - MCP Server (Top-Level File)
**Purpose:** Model Context Protocol server entry point.
**Status:** ✅ Exists
**Dependencies:** `orchestrators/`, `core/`
**Contains:**
- MCP tool registration using FastMCP
- Tool wrapper functions calling orchestrators

**Rules:**
- ✅ Can import from: `orchestrators/`, `core/`
- ❌ Cannot import from: `cli/`, `ui/`, domain logic directly
- 🎯 **Key Design:** Thin MCP wrapper around orchestrators

---

## Dependency Matrix

This matrix defines which containers **CAN** import from which other containers. Use this when implementing Phase 2 in SonarCloud.

**Legend:**
- ✅ = Allowed dependency
- ❌ = Forbidden dependency
- 🔄 = Conditional (e.g., only during certain phases)

| From ↓ / To → | core | storage | filesystem | ir | parsers | converters | generators | auth | audit | benchmarking | integrations | api | orchestrators | cli | ui | server.py |
|---------------|------|---------|------------|----|---------| -----------|-----------|------|-------|--------------|--------------|-----|---------------|-----|----|-----------|
| **core** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **storage** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **filesystem** | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **ir** | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **parsers** | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **converters** | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **generators** | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **auth** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **audit** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **benchmarking** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **integrations** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **api** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **orchestrators** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **cli** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🔄 | ✅ | ✅ | ❌ | ❌ |
| **ui** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 🔄 | ❌ | ✅ | ❌ |
| **server.py** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |

### Matrix Validation Rules

**Foundation Layer (core):**
- ✅ Can import: Only Python stdlib and third-party libraries
- ❌ Cannot import: Any souschef module

**Data Layer (storage, filesystem, ir):**
- ✅ Can import: `core/` only
- ❌ Cannot import: Any higher layer

**Domain Layer (parsers, converters, generators):**
- ✅ Can import: `core/`, `ir/`, `filesystem/` (parsers, generators only), `parsers/` (converters only), `converters/` (generators only)
- ❌ Cannot import: Services, integrations, orchestrators, UI layers

**Service Layer (auth, audit, benchmarking):**
- ✅ Can import: `core/`, `storage/`, sometimes each other (audit→auth)
- ❌ Cannot import: Domain logic, orchestrators, UI layers

**Integration & API Layer:**
- ✅ Can import: Foundation, data, services, orchestrators (API only)
- ❌ Cannot import: Domain logic directly, UI layers

**Orchestration Layer:**
- ✅ Can import: All lower layers except API/UI interfaces
- ❌ Cannot import: `api/`, `cli/`, `ui/`, `server.py`

**UI Layer (cli, ui, server.py):**
- ✅ Can import: `orchestrators/`, `api/` (UI only), `core/`
- ❌ Cannot import: Domain logic directly, other UI containers

---

## Module Placement Rules

Use this decision tree when creating new code:

```
NEW FEATURE/CODE
     │
     ├─ Is it a utility/constant/base class?
     │  └─ YES → core/
     │
     ├─ Does it store/retrieve data?
     │  └─ YES → storage/ or filesystem/
     │
     ├─ Does it parse input files?
     │  └─ YES → parsers/ (e.g., parsers/puppet.py)
     │
     ├─ Does it transform data without I/O?
     │  └─ YES → converters/ or generators/
     │
     ├─ Is it authentication/authorization?
     │  └─ YES → auth/
     │
     ├─ Is it audit logging/compliance?
     │  └─ YES → audit/
     │
     ├─ Is it performance profiling?
     │  └─ YES → benchmarking/
     │
     ├─ Is it an external system integration?
     │  └─ YES → integrations/ (e.g., integrations/gitlab.py)
     │
     ├─ Is it a REST API endpoint?
     │  └─ YES → api/routes/
     │
     ├─ Does it coordinate multiple lower layers?
     │  └─ YES → orchestrators/
     │
     └─ Is it a user interface?
        ├─ CLI? → cli/commands/
        ├─ Web? → ui/pages/ or ui/components/
        └─ MCP? → server.py (top-level file)
```

### Examples

**Puppet Support (Implemented):**
1. ✅ `parsers/puppet.py` - Parse Puppet manifests → structured data (15 resource types)
2. ✅ `converters/puppet_to_ansible.py` - Puppet → Ansible via `ansible.builtin` modules
3. ✅ `ui/pages/puppet_migration.py` - Streamlit UI page for manifest/module conversion
4. ✅ 8 MCP tools in `server.py` — parse, convert, list types, AI-assisted conversion
5. ✅ CLI commands via `souschef puppet` subcommand group
6. 🔄 `orchestrators/migration.py` - Full Puppet workflow orchestration (planned)
7. 🔄 `api/routes/puppet.py` - REST endpoints for Puppet conversion (planned)

**Adding RBAC:**
1. `auth/rbac.py` - Role and permission management
2. `auth/policies.py` - Policy definitions
3. `api/middleware.py` - Update to enforce RBAC on endpoints
4. `audit/logger.py` - Log permission checks
5. `ui/components/permissions.py` - UI for role assignment

**Adding Dark Mode:**
1. `ui/themes.py` - Theme definitions and switcher
2. `ui/components/*.py` - Update components to use theme context
3. `api/routes/user_preferences.py` - Store user theme preference

---

## SonarCloud Enforcement

### Phase 1: Container-Level (Current)
**Status:** ✅ Implemented in UI

Containers defined:
- `souschef/core`
- `souschef/parsers`
- `souschef/converters`
- `souschef/filesystem`
- `souschef/ir`

**Next Steps:**
1. Add remaining containers to Phase 1:
   - `souschef/storage`
   - `souschef/generators`
   - `souschef/auth` (create skeleton)
   - `souschef/audit` (create skeleton)
   - `souschef/benchmarking` (migrate profiling.py)
   - `souschef/integrations` (existing github/)
   - `souschef/api` (create skeleton)
   - `souschef/orchestrators` (create + migrate assessment.py, deployment.py)
   - `souschef/cli` (consolidate existing files)
   - `souschef/ui`

2. Define relationships in SonarCloud UI based on Dependency Matrix above

### Phase 2: File-Level (Future)
Define individual modules within containers for granular enforcement

**Example:**
- `souschef/parsers/recipe.py` can depend on `souschef/core/path_utils.py`
- `souschef/parsers/recipe.py` **cannot** depend on `souschef/converters/playbook.py`

---

## Growth Guidelines

### When Adding New Capabilities

**1. Start with Architecture**
- Is this a new container or fits in existing?
- What dependencies does it need?
- Check Dependency Matrix for violations

**2. Create Container Skeleton (if new)**
```python
# souschef/newcontainer/__init__.py
"""
NewContainer: Brief description

Purpose: What this container does
Dependencies: Which containers it can import from
Rules: What it cannot do
"""

__version__ = "1.0.0"
```

**3. Update Architecture Document**
- Add to Container Definitions
- Update Dependency Matrix
- Add to Module Placement Rules decision tree

**4. Implement with Discipline**
- Follow dependency rules strictly
- Write tests in `tests/unit/test_newcontainer.py`
- Update integration tests if needed

**5. Update SonarCloud**
- Add container to architecture definition
- Define allowed dependencies
- Verify no violations detected

### When Refactoring Existing Code

**Current Violations to Fix:**

1. **Top-Level Files** (assessment.py, deployment.py, ansible_upgrade.py, profiling.py)
   - **Issue:** Not in containers, hard to govern
   - **Solution:** Migrate to `orchestrators/` or appropriate container
   - **Timeline:** v2.1 refactor sprint

2. **CLI Consolidation** (cli.py, cli_v2_commands.py, cli_registry.py)
   - **Issue:** Fragmented CLI code
   - **Solution:** Consolidate into `cli/` container
   - **Timeline:** v2.1 refactor sprint

3. **Profiling Migration** (profiling.py → benchmarking/)
   - **Issue:** Not in proper service container
   - **Solution:** Move to `benchmarking/profiler.py`
   - **Timeline:** v2.0 completion

### Migration Checklist

When moving code between containers:

- [ ] Verify new location follows Dependency Matrix
- [ ] Update all imports in dependent modules
- [ ] Move tests to mirror new structure
- [ ] Update API documentation if endpoints change
- [ ] Add deprecation notices for old imports (if public API)
- [ ] Update SonarCloud architecture definition
- [ ] Run full test suite
- [ ] Update CHANGELOG.md

---

## Related Documentation

- **CONTRIBUTING.md** - Development workflow and code standards
- **sonar-project.properties** - SonarCloud configuration
- **README.md** - Project overview and quickstart
- **.github/copilot-instructions.md** - AI coding assistant guidelines

---

**Questions?** Open a GitHub discussion or consult the maintainers before violating architectural boundaries!

**Last Review:** 2026-03-06 by @kpeacocke
