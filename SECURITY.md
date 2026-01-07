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
- Denial of service through resource exhaustion with extremely large cookbooks

## Security Features

SousChef includes several built-in security considerations:

- **Path Traversal Protection**: File operations are validated to prevent directory traversal
- **Input Sanitization**: Chef cookbook parsing includes input validation
- **Error Handling**: Sensitive information is not leaked in error messages
- **Dependency Management**: Regular security updates for all dependencies

## Contact

For general security questions or concerns, please:

1. Check existing security advisories
2. Review this security policy
3. Contact the maintainer at krpeacocke@gmail.com

Thank you for helping keep SousChef secure! 
