# Security

This document describes verified security controls and container dependency
practices. For supported versions and private vulnerability reporting, see the
[root security policy](../SECURITY.md).

## Security Features

### Path Containment Validation

SousChef provides path-containment helpers used by filesystem operations and
MCP tools that accept workspace paths.

**Key Security Functions:**

- `_ensure_within_base_path()`: Checks lexical and resolved paths against a trusted base
- `_normalize_path()`: Normalises paths and rejects null bytes (CWE-158)
- `_safe_join()`: Joins path components and checks the result remains within the base
- `safe_*()` wrappers: Provide containment checks for common filesystem operations

**Designed to prevent:**

- Directory traversal attacks (`../../../etc/passwd`)
- Absolute path escapes (`/etc/passwd`)
- Symlink escapes that resolve outside the base directory at validation time
- Null byte injection (`file.rb\x00.txt`)

These checks do not prevent races if another process changes filesystem entries
after validation. They also do not replace operating-system permissions or
careful workspace mounting.

**Relevant tests:**

Path traversal, symlink, and null-byte scenarios are covered in
`tests/unit/test_security.py` and related tool-specific tests.

### Input Validation

Security-sensitive inputs are validated at relevant tool boundaries:

- **File paths**: Normalised and validated for containment by path-based MCP
  tools and filesystem helpers
- **Configuration values**: Validated where tools define type and range rules
- **API inputs**: Request schemas are validated where Pydantic models are used

### Dependency Security

SousChef uses several tools to maintain secure dependencies:

- **Poetry**: Dependency version pinning and resolution
- **pip-audit**: Automated vulnerability scanning in CI/CD
- **Dependabot**: Automated dependency updates (GitHub)

CodeQL branch scans finish even when a newer push arrives, because the newer
run may skip analysis through changed-path filters. Superseded pull-request
scans are cancelled. SARIF artifacts and completion messages are produced only
after successful analysis; missing SARIF output then fails artifact upload.

Container builders and release tooling pin pip to **26.2.0** to address
CVE-2026-13346 (arbitrary file installation via malicious package indexes) and
CVE-2026-8643 (path traversal via malicious wheel entry point names). Rebuild and
redeploy container images to apply these fixes to existing deployments.
Production containers omit pip and Poetry altogether; their vendored
dependencies are not part of the application runtime.

Pillow is constrained to **13.0.0 or later** to address the 20 Dependabot alerts
affecting earlier releases. The UI uses Streamlit 1.66.1 or later, which supports
Pillow 13. UI and Pillow-dependent development packages require Python 3.11+;
the core MCP server retains Python 3.10 support.

CI policy for dependency auditing:

- Policy: `fail-on-any` (CI fails when any vulnerability is reported)
- Supported policies: `fail-on-any`, `report-only`
- Command: `poetry run pip-audit --strict`
- Exceptions: use explicit vulnerability allowlists with `--ignore-vuln` only when triaged and approved

**Checking Dependencies:**

```bash
# Audit installed packages for known vulnerabilities
poetry run pip-audit

# Check for outdated packages
poetry show --outdated

# Update dependencies
poetry update
```

### Container Dependency Policy

- Production base images are pinned by multi-platform digest.
  Dependabot checks Docker tags and digests weekly; review Python and operating
  system upgrades before merging them.
- MCP images use Alpine. System packages deliberately track the supported
  Alpine branch and are refreshed by uncached builds and `apk upgrade`.
  The approved, instruction-scoped Hadolint DL3018 exceptions avoid fragile
  exact package revisions against a moving repository. These builds are not
  fully reproducible at the operating-system package level.
- The UI uses Debian slim because Streamlit's Watchdog dependency provides
  glibc Linux wheels but no Alpine/musl wheels. Base-image updates deliver
  operating-system fixes without adding compilers or source-build exceptions.
- Third-party Python dependencies must have compatible wheels. Poetry enforces
  `installer.only-binary :all:`; missing wheels fail the build. MCP builds only
  the trusted local SousChef source into a wheel before offline installation.
- Dependencies are installed into an isolated application virtual environment.
  Only that environment is copied from the builder; pip and Poetry remain
  build-time tools. The base image's pip is uninstalled from production too.
  Install dependencies by rebuilding the image, not by running pip inside a
  production container.
- Containers run as UID/GID `1001:1001`. Compose, PR builds and releases use
  the Dockerfiles' defaults rather than independent interpreter overrides.
- CI builds all three production Dockerfiles on native AMD64 and ARM64 runners,
  exercises the MCP protocol or UI HTTP endpoint, and rejects fixable HIGH or
  CRITICAL container vulnerabilities. Uncached builds expose repository drift
  before publishing. Update the Alpine branch before its support ends.

### AI Integration Considerations

When using AI providers (Anthropic, OpenAI, etc.):

- **API Keys**: Supply keys through configured credential settings or explicit
  tool parameters; do not commit them to source control
- **Structured Outputs**: Pydantic schemas for type-safe AI responses
- **Error Handling**: Graceful degradation when AI services are unavailable
- **Rate Limiting**: Respect provider rate limits

**Best Practices:**

```bash
# Store API keys in .env file (never commit to git)
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here

# Add .env to .gitignore
echo ".env" >> .gitignore
```

## Reporting Security Vulnerabilities

Use the private reporting channels and disclosure guidance in the
[root security policy](../SECURITY.md). No response or remediation timeline is
promised.

## Security Best Practices for Users

### Running SousChef Securely

1. **Workspace Isolation**
   ```bash
   # Run SousChef in an isolated directory
   mkdir ~/souschef-workspace
   cd ~/souschef-workspace

   # Set explicit workspace root
   export SOUSCHEF_WORKSPACE_ROOT=$(pwd)
   ```

2. **Least Privilege**
   - Don't run SousChef as root unless absolutely necessary
   - Use dedicated service accounts for CI/CD integration
   - Limit filesystem permissions on output directories

3. **API Key Management**
   ```bash
   # Use environment variables
   export ANTHROPIC_API_KEY="your-key"

   # Or use .env file (never commit!)
   echo "ANTHROPIC_API_KEY=your-key" > .env
   chmod 600 .env
   ```

4. **Network Security**
   - Use HTTPS for all API communications
   - Verify SSL certificates
   - Use firewall rules to restrict outbound connections if needed
   - Configure `SOUSCHEF_ALLOWED_HOSTNAMES` to allowlist approved outbound hosts

5. **Input Validation**
   - Validate cookbook sources before conversion
   - Review generated Ansible playbooks before execution
   - Test conversions in non-production environments first

### Secure CI/CD Integration

```yaml
# Example GitHub Actions security configuration
- name: Install SousChef
  run: |
    pip install mcp-souschef[all]

- name: Run conversion
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    souschef convert --input cookbooks/ --output playbooks/

- name: Security scan output
  run: |
    ansible-lint playbooks/
```

**Security Checklist:**

- Store API keys as GitHub Secrets
- Use minimal permissions for workflow tokens
- Pin dependency versions
- Run security scans on generated code
- Review workflow logs for sensitive data leaks
- Use separate API keys for CI/CD vs production

## Security Testing

SousChef includes comprehensive security testing:

```bash
# Run security tests
poetry run pytest tests/unit/test_security.py -v

# Run all tests with coverage
poetry run pytest --cov=souschef --cov-report=html

# Check for vulnerable dependencies
poetry run pip-audit
```

### Writing Security Tests

When contributing, include security tests for:

- New filesystem operations
- User input handling
- External API integrations
- Configuration parsing

Example:

```python
def test_path_validation_prevents_traversal():
    """Ensure path validation blocks directory traversal."""
    base = Path("/safe/workspace")
    attack_path = base / ".." / ".." / "etc" / "passwd"

    with pytest.raises(ValueError, match="Path traversal"):
        _ensure_within_base_path(attack_path, base)
```

## Known Limitations

### Current Scope

- **Path validation**: Enforced for MCP server operations; CLI tools should validate at entry points
- **Template execution**: ERB template parsing is read-only; no code execution
- **AI responses**: Validated through Pydantic schemas but still untrusted input

### Future Enhancements

Planned security improvements:

- [ ] Rate limiting for AI API calls
- [ ] Content security policy for web UI
- [ ] Audit logging for sensitive operations
- [ ] Encrypted storage for API keys
- [ ] RBAC (Role-Based Access Control) for multi-user scenarios

## Security Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE-22 (Path Traversal)**: https://cwe.mitre.org/data/definitions/22.html
- **CWE-158 (Null Byte Injection)**: https://cwe.mitre.org/data/definitions/158.html
- **Python Security**: https://python.readthedocs.io/en/stable/library/security_warnings.html

## Security Acknowledgements

We thank the security researchers and contributors who help keep SousChef secure. Responsible disclosures are acknowledged in release notes (with permission).

## License and Disclaimer

SousChef is provided "as-is" under the MIT License. Users are responsible for:

- Validating generated code before execution
- Securing API credentials
- Maintaining secure deployment environments
- Testing in non-production environments first

For the full license text, see: https://github.com/kpeacocke/souschef/blob/main/LICENSE
