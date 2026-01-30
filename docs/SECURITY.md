# Security

SousChef takes security seriously. This document outlines our security practices, how to report vulnerabilities, and the security features built into the project.

## Security Features

### Path Containment Validation

SousChef implements comprehensive path containment validation to prevent directory traversal attacks (CWE-22). All filesystem operations use validated paths that stay within trusted directories.

**Key Security Functions:**

- `_ensure_within_base_path()`: Validates that paths stay within a trusted base directory
- `_normalize_path()`: Normalizes paths and rejects null bytes (CWE-158 prevention)
- `_safe_join()`: Safely joins path components with traversal protection
- `safe_*()` wrappers: All filesystem operations (read, write, glob, etc.) enforce containment

**Protected Against:**

- Directory traversal attacks (`../../../etc/passwd`)
- Absolute path escapes (`/etc/passwd`)
- Symlink-based attacks (symlinks pointing outside base directory)
- Null byte injection (`file.rb\x00.txt`)
- URL encoding bypasses
- Double slash sequences

**Test Coverage:**

Comprehensive security tests in [tests/unit/test_security.py](../tests/unit/test_security.py):
- 42+ security-focused tests
- Path traversal attack scenarios
- Symlink attack prevention
- Null byte injection prevention
- Integration tests for complete workflows

### Input Validation

All user inputs are validated before use:

- **File paths**: Normalized and validated for containment
- **Configuration values**: Type-checked and range-validated
- **API inputs**: Schema validation using Pydantic models

### Dependency Security

SousChef uses several tools to maintain secure dependencies:

- **Poetry**: Dependency version pinning and resolution
- **pip-audit**: Automated vulnerability scanning in CI/CD
- **Snyk**: Continuous security monitoring (if configured)
- **Dependabot**: Automated dependency updates (GitHub)

**Checking Dependencies:**

```bash
# Audit installed packages for known vulnerabilities
poetry run pip-audit

# Check for outdated packages
poetry show --outdated

# Update dependencies
poetry update
```

### AI Integration Security

When using AI providers (Anthropic, OpenAI, etc.):

- **API Keys**: Never hardcoded; use environment variables or dotenv files
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

### Secure Defaults

- **File permissions**: Creates files with restrictive permissions
- **YAML parsing**: Safe loading (no arbitrary code execution)
- **Template rendering**: Sandboxed execution context
- **HTTP requests**: Timeouts to prevent hanging connections

## Reporting Security Vulnerabilities

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly:

**DO:**
- Email security reports to the maintainers (see SECURITY.md in root)
- Provide detailed reproduction steps
- Allow reasonable time for fixes before public disclosure
- Work with us to verify the fix

**DON'T:**
- Open public GitHub issues for security vulnerabilities
- Exploit vulnerabilities in production systems
- Share vulnerabilities publicly before fixes are released

**Response Timeline:**
- Initial response: Within 48 hours
- Triage and assessment: Within 1 week
- Fix development: Varies by severity
- Public disclosure: After fix is released

## Security Best Practices for Users

### Running SousChef Securely

1. **Workspace Isolation**
   ```bash
   # Run SousChef in an isolated directory
   mkdir ~/souschef-workspace
   cd ~/souschef-workspace

   # Set explicit workspace root
   export SOUSCHEF_WORKSPACE=$(pwd)
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

- ✅ Store API keys as GitHub Secrets
- ✅ Use minimal permissions for workflow tokens
- ✅ Pin dependency versions
- ✅ Run security scans on generated code
- ✅ Review workflow logs for sensitive data leaks
- ✅ Use separate API keys for CI/CD vs production

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

For the full license text, see [LICENSE](../LICENSE).
