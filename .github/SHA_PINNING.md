# GitHub Actions SHA Pinning

## Overview
This document tracks the SHA hashes used to pin GitHub Actions dependencies in our CI/CD workflows. Pinning to commit SHAs instead of tags provides enhanced security by preventing tag manipulation attacks.

## Pinned Actions Reference

### CI Workflow (.github/workflows/ci.yml) - PINNED ✅

| Action | Version Tag | Commit SHA | Notes |
|--------|-------------|------------|-------|
| actions/checkout | v6 | `8e8c483db84b4bee98b60c0593521ed34d9990e8` | Repository checkout |
| actions/setup-python | v6 | `83679a892e2d95755f2dac6acb0bfd1e9ac5d548` | Python environment setup |
| snok/install-poetry | v1 | `76e04a911780d5b312d89783f7b1cd627778900a` | Poetry installation |
| actions/cache | v5 | `9255dc7a253b0ccc959486e2bca901246202afeb` | Dependency caching |
| codecov/codecov-action | v5 | `671740ac38dd9b0130fbe1cec585b89eea48d3de` | Code coverage upload |
| trufflesecurity/trufflehog | main | `50aa4695becccb04c958215388cab34a75e0fd31` | Secret scanning |
| actions/upload-artifact | v6 | `b7c566a772e6b6bfb58ed0dc250532a479d7789f` | Artifact upload |

### SonarQube Workflow (.github/workflows/sonarqube.yml) - PINNED ✅

| Action | Version Tag | Commit SHA | Notes |
|--------|-------------|------------|-------|
| actions/checkout | v6 | `8e8c483db84b4bee98b60c0593521ed34d9990e8` | Repository checkout |
| actions/setup-python | v6 | `83679a892e2d95755f2dac6acb0bfd1e9ac5d548` | Python setup |
| snok/install-poetry | v1 | `76e04a911780d5b312d89783f7b1cd627778900a` | Poetry installation |
| actions/cache | v5 | `9255dc7a253b0ccc959486e2bca901246202afeb` | Dependency caching |
| actions/download-artifact | v4 | `fa0a91b85d4f404e444e00e005971372dc801d16` | Download coverage from CI |
| SonarSource/sonarqube-scan-action | v7.0.0 | `a31c9398be7ace6bbfaf30c0bd5d415f843d45e9` | SonarCloud static analysis |

### Snyk Workflow (.github/workflows/snyk.yml) - PARTIALLY PINNED ⚠️

| Action | Version Tag | Commit SHA | Notes |
|--------|-------------|------------|-------|
| actions/checkout | v6 | ⚠️ **Not pinned** | Repository checkout |
| actions/setup-python | v6 | ⚠️ **Not pinned** | Python setup |
| snok/install-poetry | v1 | `76e04a911780d5b312d89783f7b1cd627778900a` | Poetry installation |
| actions/cache | v5 | ⚠️ **Not pinned** | Dependency caching |
| snyk/actions/setup | v1.0.0 | `9adf32b1121593767fc3c057af55b55db032dc04` | Snyk setup |
| github/codeql-action/upload-sarif | v4 | ⚠️ **Not pinned** | SARIF upload |

### Release Workflow (.github/workflows/release.yml) - NOT PINNED ⚠️

| Action | Version Tag | Commit SHA | Notes |
|--------|-------------|------------|-------|
| actions/checkout | v6 | ⚠️ **Not pinned** | Repository checkout |
| actions/setup-python | v6 | ⚠️ **Not pinned** | Python setup |
| snok/install-poetry | v1 | `76e04a911780d5b312d89783f7b1cd627778900a` | Poetry installation |
| actions/cache | v5 | ⚠️ **Not pinned** | Dependency caching |
| actions/upload-artifact | v6 | ⚠️ **Not pinned** | Artifact upload |
| actions/download-artifact | v7 | ⚠️ **Not pinned** | Artifact download |
| pypa/gh-action-pypi-publish | v1.12.3 | `67339c736fd9354cd4f8cb0b744f2b82a74b5c70` | PyPI publishing |

### CodeQL Workflow (.github/workflows/codeql.yml) - NOT PINNED ⚠️

| Action | Version Tag | Commit SHA | Notes |
|--------|-------------|------------|-------|
| actions/checkout | v4 | ⚠️ **Not pinned** | Repository checkout |
| actions/setup-python | v6 | ⚠️ **Not pinned** | Python setup |
| github/codeql-action/init | v4 | ⚠️ **Not pinned** | CodeQL initialization |
| github/codeql-action/analyze | v4 | ⚠️ **Not pinned** | CodeQL analysis |
| actions/upload-artifact | v4 | ⚠️ **Not pinned** | Artifact upload |

### Other Workflows - NOT PINNED ⚠️

**release-please.yml:**
- googleapis/release-please-action@v4 - ⚠️ **Not pinned**

**post-release.yml:**
- actions/checkout@v6 - ⚠️ **Not pinned**
- actions/github-script@v8 - ⚠️ **Not pinned**

**poetry-lock-check.yml:**
- actions/checkout@v6 - ⚠️ **Not pinned**
- actions/setup-python@v6 - ⚠️ **Not pinned**
- snok/install-poetry@v1 - `76e04a911780d5b312d89783f7b1cd627778900a` ✅
- actions/github-script@v8 - ⚠️ **Not pinned**

**gitflow.yml:**
- actions/github-script@v8 - ⚠️ **Not pinned**

**pr-title.yml:**
- No external actions

## Security Benefits

1. **Immutable References**: Commit SHAs cannot be changed, unlike tags which can be moved or deleted
2. **Supply Chain Security**: Protects against compromised action repositories
3. **Audit Trail**: Clear record of exactly which version is running
4. **Dependabot Integration**: GitHub Dependabot can still update SHA-pinned actions

## Maintenance

### Updating Pinned Actions

When a new version is released:

1. **Find the new tag's SHA**:
   ```bash
   # For tags
   git ls-remote https://github.com/OWNER/REPO.git refs/tags/VERSION

   # For main branch
   git ls-remote https://github.com/OWNER/REPO.git HEAD
   ```

2. **Verify the release** on GitHub releases page

3. **Update the workflow**:
   ```yaml
   uses: owner/action@<new-sha> # vX.Y.Z
   ```

4. **Update this document** with the new SHA and version

### Automated Updates

- GitHub Dependabot can automatically create PRs to update SHA-pinned actions
- Configure in `.github/dependabot.yml` with:
  ```yaml
  version: 2
  updates:
    - package-ecosystem: "github-actions"
      directory: "/"
      schedule:
        interval: "weekly"
  ```

## Verification

The CI workflow has been validated:
- ✅ YAML syntax is correct
- ✅ All SHA hashes verified from GitHub releases
- ✅ Comment format: `@<sha> # <version>`

## References

- [GitHub Security Hardening Guide](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions)
- [Dependabot for GitHub Actions](https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot)
