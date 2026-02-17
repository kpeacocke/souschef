---
name: Bug Report
about: Report a bug to help us improve SousChef
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''

---

## Bug Description

A clear and concise description of what the bug is.

## Steps to Reproduce

Steps to reproduce the behavior:

1. Run command: `souschef-cli ...` or use MCP tool: `...`
2. With input file: `...` (please attach or paste relevant parts)
3. Expected behavior: `...`
4. Actual behavior: `...`

## Minimal Example

Please provide a minimal Chef cookbook or file that reproduces the issue:

```ruby
# Example Chef code that causes the issue
package 'nginx' do
  action :install
end
```

## Environment

- **SousChef Version**: [e.g., 0.1.0]
- **Python Version**: [e.g., 3.14.1]
- **Operating System**: [e.g., Ubuntu 22.04, macOS 13.0, Windows 11]
- **Installation Method**: [e.g., poetry, pip, from source]

## Output/Error Messages

```
Paste the complete error message or unexpected output here
```

## Expected Behavior

A clear and concise description of what you expected to happen.

## Additional Context

Add any other context about the problem here:

- Are you migrating from a specific Chef version?
- Does this affect a particular type of cookbook structure?
- Any workarounds you've found?
- Related issues or discussions?

## Checklist

- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have provided a minimal example that reproduces the issue
- [ ] I have included the complete error message/output
- [ ] I have specified my environment details
- [ ] I have tested with the latest version of SousChef

---

**Note**: For security vulnerabilities, please see our [Security Policy](../SECURITY.md) instead of creating a public issue.
