# GitHub Actions SHA Pinning

## Overview
This document tracks the SHA hashes used to pin GitHub Actions dependencies in our CI/CD workflows. Pinning to commit SHAs instead of tags provides enhanced security by preventing tag manipulation attacks.

## Pinned Actions (Updated: 2025-01-XX)

### Primary CI Workflow (.github/workflows/ci.yml)

| Action | Version Tag | Commit SHA | Notes |
|--------|-------------|------------|-------|
| actions/checkout | v6 | `8e8c483db84b4bee98b60c0593521ed34d9990e8` | Repository checkout |
| actions/setup-python | v6 | `83679a892e2d95755f2dac6acb0bfd1e9ac5d548` | Python environment setup |
| snok/install-poetry | v1 | `76e04a911780d5b312d89783f7b1cd627778900a` | Poetry installation |
| actions/cache | v5 | `9255dc7a253b0ccc959486e2bca901246202afeb` | Dependency caching |
| codecov/codecov-action | v5 | `671740ac38dd9b0130fbe1cec585b89eea48d3de` | Code coverage upload |
| trufflesecurity/trufflehog | main | `50aa4695becccb04c958215388cab34a75e0fd31` | Secret scanning |
| actions/upload-artifact | v6 | `b7c566a772e6b6bfb58ed0dc250532a479d7789f` | Artifact upload |

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
