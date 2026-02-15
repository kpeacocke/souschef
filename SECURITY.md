# Security Policy

## Supported Versions

We currently support the following versions of SousChef with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of SousChef seriously. If you discover a security vulnerability, please follow these steps:

### Private Disclosure

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report vulnerabilities privately using one of the following methods:

1. **GitHub Security Advisories** (preferred): Use the "Security" tab in the GitHub repository to privately report vulnerabilities
2. **Email**: Send details to krpeacocke@gmail.com

### What to Include

When reporting a vulnerability, please include:

- **Description**: A clear description of the vulnerability
- **Impact**: Potential impact and attack scenarios
- **Reproduction**: Step-by-step instructions to reproduce the issue
- **Environment**: Python version, SousChef version, and operating system
- **Proof of Concept**: If applicable, include a minimal proof of concept

### Response Timeline

- **Initial Response**: We aim to acknowledge receipt within 48 hours
- **Investigation**: We will investigate and provide an initial assessment within 7 days
- **Resolution**: Critical vulnerabilities will be addressed within 30 days
- **Disclosure**: We follow coordinated disclosure practices

### Recognition

Security researchers who responsibly disclose vulnerabilities may be:

- Credited in the security advisory (if desired)
- Listed in our contributors section
- Recognized in release notes

## Security Best Practices

### For Users

When using SousChef:

- **Keep Updated**: Always use the latest version
- **Validate Input**: Verify Chef cookbook sources before parsing
- **Sandbox Environment**: Run migrations in isolated environments first
- **Access Control**: Limit access to production cookbooks and generated playbooks

### For Contributors

When contributing to SousChef:

- **Code Review**: All changes require security-focused review
- **Dependencies**: Keep dependencies updated and audit regularly
- **Input Validation**: Validate all user inputs, especially file paths
- **Secrets Management**: Never commit secrets or credentials
- **Testing**: Include security test cases for new features

## Scope

This security policy covers:

- **Core MCP Server**: The main SousChef server implementation
- **CLI Tool**: The souschef-cli command-line interface
- **Dependencies**: Known vulnerabilities in project dependencies

## Out of Scope

The following are typically out of scope:

- Issues in third-party Chef cookbooks being parsed
- Vulnerabilities in generated Ansible playbooks (user responsibility to review)
- Infrastructure security (deployment environments)

## Security Features

SousChef implements multiple layers of security protection:

### Path Security (CWE-22, CWE-61)

- **Path Traversal Protection**: File operations are validated against base paths to prevent directory traversal attacks
- **Symlink Detection**: Defense-in-depth protection detects and blocks symbolic link attacks by checking the entire path ancestry
- **Path Length Validation**: Maximum path length of 4096 characters prevents buffer-based attacks
- **Path Normalisation**: All file paths are normalised before use to prevent bypass attempts

### Input Validation

- **Chef Cookbook Parsing**: Comprehensive input validation for all Chef artifacts (recipes, attributes, metadata, templates)
- **Request Size Limits**:
  - Maximum 4096 characters for file paths
  - Maximum 20 Habitat plan paths per request
  - Maximum 8192 characters for plan path lists
- **Resource Exhaustion Prevention**: Request size limits prevent denial-of-service attacks

### HTTP Client Security (CWE-400)

- **Timeout Limits**: HTTP requests limited to 1-300 seconds to prevent hung connections
- **Retry Limits**: Maximum 0-10 retry attempts to prevent retry storms
- **Backoff Validation**: Backoff factor limited to 0.1-10 seconds to prevent DoS amplification

### Command Injection Prevention (CWE-78)

- **Habitat Pattern Blocking**: Default deny for dangerous shell patterns in Habitat plan conversion:
  - Shell piping: `curl|sh`, `wget|sh`
  - Code evaluation: `eval`
  - Command substitution with untrusted input
- **Explicit Override**: Dangerous patterns require explicit `allow_dangerous_patterns=True` parameter
- **Variable Sanitisation**: Habitat variables are safely replaced with container paths

### Error Handling

- **Information Disclosure Prevention**: Sensitive information is not leaked in error messages
- **Safe Error Propagation**: Errors are caught and wrapped with safe, user-friendly messages
- **Stack Trace Protection**: Stack traces are logged but not exposed to end users

### Dependency Management

- **Regular Security Updates**: All dependencies are regularly audited and updated
- **Vulnerability Scanning**: Automated security scanning with Snyk and CodeQL
- **Dependency Pinning**: Lock files ensure reproducible builds with known-good versions

### Automated Vulnerability Scanning

SousChef includes comprehensive automated vulnerability scanning for all Docker images:

**Trivy Vulnerability Scanning:**

- **Release Process**: All Docker images (UI and MCP) are scanned with Trivy during release builds
- **Smart Filtering**: Scanning is configured to report only actionable vulnerabilities:
  - **Severity Filter**: Only CRITICAL and HIGH severity issues are reported
  - **Fix Availability Filter**: Only vulnerabilities with available fixes are shown (`ignore-unfixed: true`)
  - **Reduces Noise**: Upstream Alpine/Python base image issues without patches don't clutter the report
- **GitHub Security Integration**: All scan results are uploaded to the GitHub Security tab for tracking
- **Configuration**: See [.trivyignore](.trivyignore) for vulnerability filtering strategy

**How This Works:**

1. **Pull Base Image**: Fresh Alpine Linux and Python images pulled on each release
2. **Build Docker Image**: Multi-stage build compiles application with all dependencies
3. **Scan with Trivy**: Comprehensive vulnerability database scan
4. **Smart Reporting**: Only CRITICAL/HIGH with available fixes are reported
5. **Auto-Resolution**: When upstream packages are patched, next rebuild automatically picks them up

**Viewing Scan Results:**

- GitHub UI: Navigate to the repository's **Security** tab → **Code scanning alerts**
- Command Line: Pull image and run Trivy locally with same configuration

**For Users:**

- All published images (ghcr.io/kpeacocke/souschef:*) have undergone vulnerability scanning
- When vulnerabilities are fixed upstream, new releases will automatically include patches
- See [GitHub Security Advisories](https://github.com/kpeacocke/souschef/security/advisories) for detailed CVE information

## Contact

For general security questions or concerns, please:

1. Check existing security advisories
2. Review this security policy
3. Contact the maintainer at krpeacocke@gmail.com

Thank you for helping keep SousChef secure!
