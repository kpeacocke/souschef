# Contributing to SousChef

Thank you for your interest in contributing to SousChef! This guide covers everything you need to know about our development workflow, CI/CD pipeline, and contribution standards.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Workflow](#development-workflow)
  - [Gitflow Branch Model](#gitflow-branch-model)
  - [Branch Types](#branch-types)
  - [Common Workflows](#common-workflows)
  - [Commit Message Conventions](#commit-message-conventions)
- [CI/CD Pipeline](#cicd-pipeline)
  - [Workflows Overview](#workflows-overview)
  - [Required Configuration](#required-configuration)
  - [Release Process](#release-process)
- [Setup Instructions](#setup-instructions)
  - [Local Development](#local-development)
  - [Branch Protection Rules](#branch-protection-rules)
  - [GitHub Secrets](#github-secrets)
  - [PyPI Publishing](#pypi-publishing)
- [Code Standards](#code-standards)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

---

## Quick Start

### Getting Started

```bash
# Clone the repository
git clone https://github.com/kpeacocke/souschef.git
cd souschef

# Create a feature branch (always from develop)
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name

# Install dependencies
poetry install

# Make your changes, then test
poetry run pytest --cov=souschef --cov-report=term-missing
poetry run ruff check .
poetry run ruff format .

# Commit and push
git add .
git commit -m "feat: add your feature"
git push -u origin feature/your-feature-name

# Create PR on GitHub: feature/your-feature-name → develop
```

### Before Submitting PR

-  All tests pass (`poetry run pytest`)
-  Code is linted (`poetry run ruff check .`)
-  Code is formatted (`poetry run ruff format .`)
-  Documentation updated if needed
-  Branch follows naming convention (`feature/*`, `bugfix/*`, etc.)
-  PR targets correct base branch

---

## Development Workflow

### Gitflow Branch Model

SousChef follows the **Gitflow** branching model for organized, scalable development.

#### Protected Branches

**`main`** - Production-ready code only
- Merges from: `release/*`, `hotfix/*`
- Direct commits:  Never
- Triggers: Release workflow on tags
- Protection: Requires PR approval + all status checks

**`develop`** - Integration branch for ongoing development
- Merges from: `feature/*`, `bugfix/*`, `release/*` (backmerge), `hotfix/*` (backmerge)
- Merges to: `main` (via release branches)
- Direct commits:  Rarely
- Protection: Requires PR approval + status checks

### Branch Types

| Branch Type | From | To | Naming | Example | Delete After |
|------------|------|-----|--------|---------|--------------|
| Feature | `develop` | `develop` | `feature/*` | `feature/add-parser` |  Yes |
| Bugfix | `develop` | `develop` | `bugfix/*` | `bugfix/fix-template` |  Yes |
| Release | `develop` | `main` + `develop` | `release/*` | `release/1.2.0` |  Yes |
| Hotfix | `main` | `main` + `develop` | `hotfix/*` | `hotfix/1.1.1` |  Yes |

#### Feature Branches (`feature/*`)

For new features or enhancements.

```bash
git checkout develop && git pull
git checkout -b feature/add-ansible-templates
# Work, commit, push
git push -u origin feature/add-ansible-templates
# Create PR: feature/add-ansible-templates → develop
```

**Examples**: `feature/chef-inspec-support`, `feature/improve-metadata-parser`

#### Bugfix Branches (`bugfix/*`)

For bug fixes in next release.

```bash
git checkout develop && git pull
git checkout -b bugfix/fix-recipe-parser
# Fix, commit, push
git push -u origin bugfix/fix-recipe-parser
# Create PR: bugfix/fix-recipe-parser → develop
```

**Examples**: `bugfix/template-variable-escaping`, `bugfix/metadata-version-detection`

#### Release Branches (`release/*`)

For release preparation. Only version bumps, bug fixes, and documentation allowed. No new features.

```bash
git checkout develop && git pull
git checkout -b release/1.2.0

# Bump version in pyproject.toml
sed -i 's/version = ".*"/version = "1.2.0"/' pyproject.toml
git commit -am "chore: bump version to 1.2.0"

git push -u origin release/1.2.0
# Create PR: release/1.2.0 → main

# After merge to main:
git checkout main && git pull
git tag v1.2.0
git push origin v1.2.0

# Backmerge to develop
git checkout develop
git merge release/1.2.0
git push

# Delete release branch
git branch -d release/1.2.0
git push origin --delete release/1.2.0
```

**Examples**: `release/1.2.0`, `release/2.0.0-beta.1`

#### Hotfix Branches (`hotfix/*`)

For emergency production fixes.

```bash
git checkout main && git pull
git checkout -b hotfix/1.1.1

# Fix critical issue
git add .
git commit -m "fix: critical security vulnerability"

# Bump version
sed -i 's/version = ".*"/version = "1.1.1"/' pyproject.toml
git commit -am "chore: bump version to 1.1.1"

git push -u origin hotfix/1.1.1
# Create PR: hotfix/1.1.1 → main

# After merge:
git checkout main && git pull
git tag v1.1.1
git push origin v1.1.1

# Backmerge to develop
git checkout develop
git merge hotfix/1.1.1
git push

# Delete hotfix branch
git branch -d hotfix/1.1.1
git push origin --delete hotfix/1.1.1
```

**Examples**: `hotfix/1.1.1`, `hotfix/1.2.3-security`

### Common Workflows

#### Keep Feature Branch Updated

```bash
git checkout feature/my-feature
git fetch origin
git merge origin/develop
# Resolve conflicts if any
git push
```

Or use rebase for cleaner history:

```bash
git checkout feature/my-feature
git fetch origin
git rebase origin/develop
# Resolve conflicts
git push --force-with-lease
```

#### Rename Non-Compliant Branch

```bash
# Local rename
git branch -m old-name feature/new-name

# Update remote
git push origin :old-name
git push -u origin feature/new-name
```

### Commit Message Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style (formatting)
- `refactor:` Code refactoring
- `test:` Test updates
- `chore:` Build/tooling changes
- `ci:` CI/CD changes

**Examples**:
```
feat: add support for Chef InSpec profiles
fix: correct template variable escaping
docs: update installation instructions
chore: bump version to 1.2.0
```

### Release Versioning

Follow [Semantic Versioning](https://semver.org/) (SemVer):

- **MAJOR** (`X.0.0`): Breaking changes
- **MINOR** (`1.X.0`): New features (backward compatible)
- **PATCH** (`1.1.X`): Bug fixes (backward compatible)

**Examples**:
- `1.0.0` - Initial stable release
- `1.1.0` - Added new parsers
- `1.1.1` - Fixed parsing bug
- `2.0.0` - Breaking API changes

**Pre-releases**: `1.2.0-beta.1`, `1.2.0-rc.1`

---

## CI/CD Pipeline

### Workflows Overview

#### 1. CI Workflow ([ci.yml](workflows/ci.yml))

**Triggers**: Push/PR to `main`, `develop`, `feature/**`, `bugfix/**`, `release/**`, `hotfix/**`

**Path Filtering**: Skips on doc-only changes (*.md, docs/, examples/, LICENSE)

**Jobs**:
- `test` - Linting (ruff) and testing with coverage (timeout: 15 min)
- `test-cli` - CLI functionality validation with fixture files (timeout: 10 min)
- `security` - pip-audit vulnerability scanning and TruffleHog secrets detection (timeout: 10 min)
- `build` - Package building and validation with twine (timeout: 10 min)

**Pipeline Protections**:
- Concurrency control: Cancels outdated workflow runs for the same PR/branch
- Fail-fast strategy: Stops all jobs if one fails
- Timeout protection: Jobs automatically fail if they exceed time limits
- Dependency caching: Caches Poetry dependencies to speed up builds
- Dynamic TruffleHog scanning: Compares against correct base branch (main/develop)
- Optimized Python setup: Poetry install automatically sets up the virtual environment

**Artifacts**: Distribution packages (retained 7 days)

#### 2. Gitflow Validation ([gitflow.yml](workflows/gitflow.yml))

**Triggers**: Push to any branch, PRs

**Jobs**:
- `validate-branch-name` - Ensures branch follows gitflow naming (timeout: 5 min)
- `validate-pr-base` - Ensures PR targets correct base branch (timeout: 5 min)
- `comment-pr-guidance` - Posts automated guidance on new PRs (timeout: 5 min)

**Enhanced Validation Rules**:
-  `feature/*`, `bugfix/*` → must target `develop`
-  `release/*`, `hotfix/*` → must target `main`
-  `support/*` → can target `develop` or `main`
-  `develop` → can only merge to `main`
-  `main` → blocked as source branch (wrong merge direction)
-  Branch names follow conventions

**Pipeline Protections**:
- Concurrency control: Cancels outdated validation runs

#### 3. Snyk Security Scan ([snyk.yml](workflows/snyk.yml))

**Triggers**: Push/PR to branches, weekly schedule (Mondays 2 AM UTC), manual dispatch

**Jobs**:
- `snyk-test` - Scans for vulnerabilities with high severity threshold (timeout: 15 min)
- `snyk-monitor` - Continuous monitoring on `main` branch only (timeout: 10 min)

**Pipeline Protections**:
- Concurrency control: Ensures only one scan per ref
- Enhanced error handling: Validates SNYK_TOKEN before running
- Conditional execution: Skips jobs if SNYK_TOKEN not configured
- Dependency caching: Caches Poetry dependencies
- Fork-safe: Works on fork PRs without failing

**Output**: SARIF uploaded to GitHub Security tab

**Requires**: `SNYK_TOKEN` secret

#### 4. SonarQube Analysis ([sonarqube.yml](workflows/sonarqube.yml))

**Triggers**: Push/PR to branches, manual dispatch

**Jobs**:
- `sonarqube` - Self-hosted SonarQube analysis with quality gate (timeout: 15 min)
- `sonarcloud` - SonarCloud analysis for public projects (timeout: 15 min)

**Pipeline Protections**:
- Concurrency control: Prevents duplicate analysis runs
- Conditional execution: Only runs if appropriate secrets are configured
- Fork-safe: Skips on fork PRs without secrets (prevents workflow failures)
- Dependency caching: Caches Poetry dependencies

**Features**: Coverage analysis from pytest, quality gate enforcement

**Requires**: `SONAR_TOKEN`, `SONAR_HOST_URL` (self-hosted only)

#### 5. Release Workflow ([release.yml](workflows/release.yml))

**Triggers**: Version tags (`v*`)

**Jobs**:
1. `test` - Full test suite and linting (timeout: 15 min)
2. `build` - Validates semver tag, checks version match, builds packages (timeout: 10 min)
3. `release` - Creates GitHub release with auto-generated notes (timeout: 10 min)
4. `publish-pypi` - Publishes to PyPI using trusted publishing (timeout: 10 min)

**Pipeline Protections**:
- Branch validation: Ensures tag is on `main` branch
- Concurrency control: Blocks duplicate releases
- Version output reuse: Passes version between jobs correctly
- Timeout protection: All jobs have time limits

**Requirements**:
- Tag format: `vX.Y.Z` (e.g., `v1.0.0`)
- Tag must be on `main` branch
- pyproject.toml version must match tag (without `v` prefix)
- PyPI environment configured

#### 6. Dependabot ([dependabot.yml](dependabot.yml))

**Schedule**: Weekly (Mondays 9 AM UTC)

**Updates**: Python dependencies (pip), GitHub Actions versions

**Features**:
- Groups minor/patch updates for cleaner changelog
- Auto-labels PRs by dependency type
- Limits concurrent PRs (10 Python, 5 Actions)
- Assigns reviewers instead of assignees (assignees deprecated)

**Pipeline Protections**:
- Automatic PR creation with conventional commit messages
- Groups related updates to reduce PR noise

### Required Configuration

#### GitHub Secrets

Settings → Secrets and variables → Actions

| Secret | Required For | Where to Get |
|--------|--------------|--------------|
| `SNYK_TOKEN` | Snyk | https://app.snyk.io/account |
| `SONAR_TOKEN` | SonarQube/Cloud | SonarQube settings |
| `SONAR_HOST_URL` | Self-hosted SonarQube | Your server URL |
| `CODECOV_TOKEN` | Codecov (optional) | https://codecov.io |

#### GitHub Environments

Settings → Environments → New environment

- **Name**: `pypi`
- **Reviewers**: (Optional) Add required reviewers for releases

#### Workflow Triggers Summary

| Workflow | Push | PR | Scheduled | Manual |
|----------|------|-----|-----------|--------|
| CI |  |  |  |  |
| Gitflow |  |  |  |  |
| Snyk |  |  |  Weekly |  |
| SonarQube |  |  |  |  |
| Release | Tag only |  |  |  |
| Dependabot |  |  |  Weekly |  |

### Release Process

#### 1. Update Version

```bash
# In pyproject.toml
version = "1.0.0"
```

#### 2. Create Release Branch

```bash
git checkout develop && git pull
git checkout -b release/1.0.0
# Edit pyproject.toml
git commit -am "chore: bump version to 1.0.0"
git push -u origin release/1.0.0
```

#### 3. Create PR to Main

Create PR: `release/1.0.0` → `main`

Wait for all checks to pass, get approval, merge.

#### 4. Tag the Release

```bash
git checkout main && git pull
git tag v1.0.0
git push origin v1.0.0
```

#### 5. Workflow Runs Automatically

- Validates tag format (`vX.Y.Z`)
- Checks version match
- Runs tests
- Builds package
- Creates GitHub release
- Publishes to PyPI

#### 6. Backmerge to Develop

```bash
git checkout develop
git merge release/1.0.0
git push
git branch -d release/1.0.0
git push origin --delete release/1.0.0
```

---

## Setup Instructions

### Local Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest --cov=souschef --cov-report=term-missing

# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Security scan
poetry run pip-audit

# Build package
poetry build
poetry run twine check dist/*
```

### Branch Protection Rules

#### For `main`

Settings → Branches → Add rule → Pattern: `main`

```
☑ Require pull request before merging
  ☑ Require 1 approval
  ☑ Dismiss stale approvals
☑ Require status checks:
  - test
  - test-cli
  - security
  - build
  - snyk-test
  - sonarqube (or sonarcloud)
  - validate-branch-name
  - validate-pr-base
☑ Require conversation resolution
☑ Require linear history
☑ Require signed commits (recommended)
☑ Include administrators
☑ Restrict pushes (optional - release managers only)
☑ Block force pushes
☑ Block deletions
```

#### For `develop`

Settings → Branches → Add rule → Pattern: `develop`

```
☑ Require pull request before merging
  ☑ Require 1 approval
☑ Require status checks:
  - test
  - test-cli
  - security
  - snyk-test
  - validate-branch-name
  - validate-pr-base
☑ Require conversation resolution
☑ Include administrators
☑ Block force pushes
☑ Block deletions
```

#### For `release/*` and `hotfix/*`

Settings → Branches → Add rules → Patterns: `release/*`, `hotfix/*`

```
☑ Require pull request before merging
  ☑ Require 1 approval
☑ Require status checks:
  - test
  - build
☑ Restrict pushes (optional - release managers only)
```

### GitHub Secrets

Navigate to: **Settings → Secrets and variables → Actions**

Click **New repository secret** for each:

1. **SNYK_TOKEN**
   - Get from: https://app.snyk.io/account
   - Required for vulnerability scanning

2. **SONAR_TOKEN**
   - Get from: Your SonarQube/SonarCloud instance settings
   - Required for code quality analysis

3. **SONAR_HOST_URL** (if using self-hosted)
   - Your SonarQube server URL
   - Example: `https://sonarqube.yourcompany.com`

4. **CODECOV_TOKEN** (optional)
   - Get from: https://codecov.io
   - For coverage reports

### PyPI Publishing

#### Configure Trusted Publishing

1. Go to: https://pypi.org/manage/account/publishing/
2. Click **Add a new publisher**
3. Fill in:
   - **PyPI Project Name**: `souschef`
   - **Owner**: `kpeacocke`
   - **Repository name**: `souschef`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Click **Add**

#### Create PyPI Environment

1. Navigate to: **Settings → Environments**
2. Click **New environment**
3. Name: `pypi`
4. (Optional) Add protection rules:
   - Required reviewers
   - Wait timer
   - Deployment branches

---

## Code Standards

All contributions must follow the project's coding standards outlined in [copilot-instructions.md](copilot-instructions.md):

### Key Requirements

-  **Zero warnings policy**: No errors or warnings without fixing them
-  **Type hints**: All function signatures (except pytest fixtures)
-  **Docstrings**: Google style for all functions, classes, modules
-  **Linting**: Pass `ruff check` with no violations
-  **Formatting**: Code formatted with `ruff format`
-  **100% coverage goal**: Aim for comprehensive test coverage
-  **Three test types**: Unit, integration, property-based
-  **Cross-platform**: Use `pathlib.Path` for file operations

### Before Submitting

Run the full test suite:

```bash
# Lint
poetry run ruff check .

# Format
poetry run ruff format .

# Test with coverage
poetry run pytest --cov=souschef --cov-report=term-missing

# Security scan
poetry run pip-audit
```

Or use the provided tasks:

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=souschef --cov-report=term-missing --cov-report=html

# Lint and test
# (runs lint first, then tests)
```

---

## Troubleshooting

### Branch Validation Errors

**Error**: "Branch name validation failed"

Your branch doesn't follow gitflow conventions.

**Fix**:
```bash
git branch -m feature/descriptive-name
git push origin :old-name feature/descriptive-name
git branch --set-upstream-to=origin/feature/descriptive-name
```

**Valid names**: `feature/*`, `bugfix/*`, `release/*`, `hotfix/*`

**Invalid names**: `my-feature`, `feat/something`, `fix-bug`

---

**Error**: "PR target validation failed"

Your PR targets the wrong branch.

**Fix**: Close PR and create new one with correct target:
- `feature/*`, `bugfix/*` → `develop`
- `release/*`, `hotfix/*` → `main`

### Release Errors

**Error**: "Tag does not follow semver format"

Tag must be exactly `vX.Y.Z` (e.g., `v1.0.0`).

**Invalid**: `v1.0.0-rc1`, `1.0.0`, `version-1.0.0`

**Valid**: `v1.0.0`, `v2.1.3`, `v1.0.0rc1`

---

**Error**: "Version does not match"

pyproject.toml version must match tag without `v` prefix.

**Example**: Tag `v1.0.0` requires `version = "1.0.0"` in pyproject.toml

### Workflow Errors

**Snyk fails**: Check `SNYK_TOKEN` secret is set with proper permissions

**SonarQube fails**: Check `SONAR_TOKEN` and `SONAR_HOST_URL` are set, project exists

**Dependabot no PRs**: Check `.github/dependabot.yml` syntax, verify dependencies are outdated

**Workflow timeout**: Job exceeded time limit. Check for:
- Hanging tests (add `pytest --timeout=60` to individual tests)
- Slow network operations (increase timeout if needed)
- Resource constraints (GitHub Actions runner limitations)

**Concurrency cancellation**: Expected behavior when pushing multiple commits rapidly. Latest run proceeds, older runs are cancelled.

**TruffleHog fails**: Secrets detected in code. Review the SARIF report in Security tab to identify and remove secrets. Use environment variables or GitHub Secrets instead.

**Branch validation fails**:
- `main` blocked as source: Don't create PRs from main branch
- Wrong target branch: Ensure feature/bugfix → develop, release/hotfix → main
- Check branch naming: Must follow gitflow conventions (feature/, bugfix/, etc.)

**Release validation fails**:
- "Tag not on main branch": Tags must be created on main branch commits
- Cherry-pick the commit to main or merge develop → main first

### Merge Conflicts

**Keep feature branch updated**:

```bash
git checkout feature/my-feature
git fetch origin
git merge origin/develop
# Resolve conflicts
git push
```

**Or use rebase**:

```bash
git fetch origin
git rebase origin/develop
# Resolve conflicts
git push --force-with-lease
```

---

## Resources

### Documentation
- Project README: [../README.md](../README.md)
- Coding Standards: [copilot-instructions.md](copilot-instructions.md)
- PR Template: [pull_request_template.md](pull_request_template.md)

### External Resources
- [Gitflow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Getting Help

- 🐛 **Bug reports**: Open an issue with the bug template
-  **Feature requests**: Open an issue with the feature template
- 💬 **Questions**: Use GitHub Discussions
-  **Security issues**: Follow [SECURITY.md](../SECURITY.md)

---

## Team Responsibilities

### Developers
- Create feature/bugfix branches from `develop`
- Keep branches up to date with `develop`
- Write comprehensive tests
- Follow coding standards
- Respond to review feedback
- Delete branches after merge

### Reviewers
- Review code quality and logic
- Ensure tests are adequate
- Check commit messages follow conventions
- Verify branch targets are correct
- Approve only when all checks pass

### Release Managers
- Create release branches from `develop`
- Coordinate release testing
- Merge to `main` and tag releases
- Backmerge to `develop`
- Monitor production deployments

### Maintainers
- Configure branch protection rules
- Monitor workflow runs
- Update CI/CD pipelines
- Enforce gitflow practices
- Manage secrets and environments

---

**Thank you for contributing to SousChef!** 🙏

Your improvements help make Chef-to-Ansible migrations easier for everyone.
