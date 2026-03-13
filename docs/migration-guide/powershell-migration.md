# PowerShell to Ansible Migration Guide

Enterprise guide for converting Windows PowerShell provisioning scripts to idiomatic Ansible playbooks, roles, and AWX/AAP job templates.

## Overview

SousChef's PowerShell migration feature automates the conversion of `.ps1` provisioning scripts to Windows Ansible automation using the `ansible.windows`, `community.windows`, and `chocolatey.chocolatey` collections.

The workflow follows five stages:

```
PowerShell Script → Parse → Convert → Generate Artefacts → Deploy to AAP
```

Each stage is supported by dedicated MCP tools and CLI commands, giving you full control over the migration whether you prefer conversational AI assistance or scripted pipelines.

### What Gets Converted

SousChef recognises **28+ PowerShell provisioning patterns** and maps them to idiomatic Ansible modules:

| PowerShell Cmdlet / Pattern | Ansible Module |
|-----------------------------|----------------|
| `Install-WindowsFeature`, `Add-WindowsFeature` | `ansible.windows.win_feature` |
| `Enable-WindowsOptionalFeature` | `ansible.windows.win_optional_feature` |
| `Remove-WindowsFeature`, `Uninstall-WindowsFeature` | `ansible.windows.win_feature` |
| `Start-Service`, `Stop-Service`, `Set-Service` | `ansible.windows.win_service` |
| `New-Service` | `ansible.windows.win_service` |
| `Set-ItemProperty` (registry) | `ansible.windows.win_regedit` |
| `New-Item` (registry key) | `ansible.windows.win_regedit` |
| `Remove-Item` (registry key) | `ansible.windows.win_regedit` |
| `Copy-Item` | `ansible.windows.win_copy` |
| `New-Item -ItemType Directory` | `ansible.windows.win_file` |
| `Remove-Item` (file/dir) | `ansible.windows.win_file` |
| `Set-Content`, `Add-Content` | `ansible.windows.win_copy` |
| MSI installs (`Start-Process msiexec`) | `ansible.windows.win_package` |
| `choco install`, `choco uninstall` | `chocolatey.chocolatey.win_chocolatey` |
| `New-LocalUser` | `ansible.windows.win_user` |
| `Add-LocalGroupMember` | `ansible.windows.win_group_membership` |
| `New-NetFirewallRule` | `ansible.windows.win_firewall_rule` |
| `Enable-NetFirewallRule`, `Disable-NetFirewallRule` | `ansible.windows.win_firewall_rule` |
| `Register-ScheduledTask` | `community.windows.win_scheduled_task` |
| `[Environment]::SetEnvironmentVariable` | `ansible.windows.win_environment` |
| `Install-Module` | `community.windows.win_psmodule` |
| `Import-Certificate`, `Import-PfxCertificate` | `community.windows.win_certificate_store` |
| `Enable-PSRemoting`, `winrm quickconfig` | `ansible.windows.win_shell` (with guidance) |
| `New-WebSite` (IIS) | `community.windows.win_iis_website` |
| DNS client configuration | `community.windows.win_dns_client` |
| ACL operations (`Set-Acl`) | `ansible.windows.win_acl` |
| Unrecognised commands | `ansible.windows.win_shell` (fallback with warning) |

Unrecognised commands are preserved as `ansible.windows.win_shell` fallbacks with source locations and confidence warnings — nothing is silently discarded.

---

## Prerequisites

### Control Node

- Python 3.10+
- Ansible 2.14+ or AAP 2.3+
- Required Ansible collections (see [Installing Collections](#installing-collections))

### Windows Managed Nodes

- Windows Server 2016, 2019, or 2022 (Windows 10/11 also supported)
- WinRM enabled (HTTP port 5985 or HTTPS port 5986)
- PowerShell 5.1+
- A Windows-compatible machine credential configured in AWX/AAP (username/password or Kerberos)

### Installing Collections

Generate and install the `requirements.yml` for your script:

```bash
# Generate requirements.yml tailored to your script
souschef-cli powershell-requirements scripts/setup.ps1 -o requirements.yml

# Install with ansible-galaxy
ansible-galaxy collection install -r requirements.yml
```

Or install all Windows collections manually:

```bash
ansible-galaxy collection install ansible.windows community.windows chocolatey.chocolatey
```

---

## Quick Start

Migrate a PowerShell script in five commands:

```bash
# 1. Parse the script to understand what it does
souschef-cli powershell-parse scripts/setup.ps1 --format text

# 2. Check migration fidelity (what percentage can be automated)
souschef-cli powershell-fidelity scripts/setup.ps1 --format text

# 3. Convert to an Ansible playbook
souschef-cli powershell-convert scripts/setup.ps1 --output playbook.yml

# 4. Generate a complete role with all supporting files
souschef-cli powershell-role scripts/setup.ps1 --output-dir ./ansible-role

# 5. Run the playbook
ansible-playbook -i ansible-role/inventory/hosts ansible-role/site.yml
```

---

## End-to-End Migration Workflow

### Step 1: Parse and Assess

Start by understanding what your PowerShell script actually does:

```bash
souschef-cli powershell-parse scripts/setup.ps1 --format text
```

This shows every recognised provisioning action with type, parameters, and source location. Review the output to confirm the parser has correctly identified all operations.

Check the fidelity score to set expectations for the migration:

```bash
souschef-cli powershell-fidelity scripts/setup.ps1
```

A fidelity score of 80%+ means most of the work is automated. Scores below 60% suggest the script uses many custom or complex patterns that will need manual review.

### Step 2: Convert to Ansible

Convert the script to an Ansible playbook:

```bash
souschef-cli powershell-convert scripts/setup.ps1 \
    --playbook-name windows_setup \
    --hosts windows_servers \
    --output playbook.yml
```

Review `playbook.yml` and address any `win_shell` fallback tasks. The output includes comments with source line numbers so you can cross-reference the original script.

### Step 3: Generate Enterprise Artefacts

For production deployments, generate a complete Ansible role with all supporting files:

```bash
souschef-cli powershell-role scripts/setup.ps1 \
    --role-name iis_server \
    --playbook-name site \
    --hosts windows_servers \
    --output-dir ./ansible-role
```

This produces:

```
ansible-role/
├── roles/
│   └── iis_server/
│       ├── tasks/main.yml          # Converted tasks
│       ├── handlers/main.yml       # Service restart handlers
│       ├── defaults/main.yml       # Default variable values
│       ├── vars/main.yml           # Role variables
│       ├── meta/main.yml           # Collection dependencies
│       └── README.md               # Role documentation
├── site.yml                        # Top-level playbook
├── inventory/hosts                 # WinRM inventory
├── group_vars/windows.yml          # Windows group variables
└── requirements.yml                # Collection dependencies
```

### Step 4: Generate WinRM Inventory

If you need a standalone inventory file:

```bash
souschef-cli powershell-inventory \
    --hosts "win01.example.com,win02.example.com" \
    --output inventory/hosts
```

### Step 5: Test the Playbook

Before deploying to production, test against a non-production Windows host:

```bash
# Install collections
ansible-galaxy collection install -r requirements.yml

# Test connectivity
ansible windows -i inventory/hosts -m ansible.windows.win_ping

# Run in check mode (dry run)
ansible-playbook -i inventory/hosts site.yml --check

# Run for real
ansible-playbook -i inventory/hosts site.yml
```

### Step 6: Deploy to AWX/AAP

Generate and import an AWX job template:

```bash
souschef-cli powershell-job-template scripts/setup.ps1 \
    --name "Setup IIS Web Server" \
    --project windows-migration-project \
    --credential iis-winrm-credential \
    --output job_template.json
```

See [AWX/AAP Job Template Import](#awxaap-job-template-import) for full import instructions.

---

## Understanding Migration Fidelity Scores

The fidelity score is the percentage of actions that map to idiomatic Ansible modules automatically. It helps you understand the migration effort required before you start.

| Score | Interpretation | Expected Effort |
|-------|---------------|-----------------|
| 90–100% | Excellent — almost full automation | Minimal manual review |
| 75–89% | Good — most common patterns covered | Review win_shell fallbacks |
| 60–74% | Moderate — some custom patterns present | Moderate manual work |
| Below 60% | Low — many custom or complex patterns | Significant manual effort |

### Fidelity Report Example

```json
{
  "fidelity_score": 87.5,
  "total_actions": 40,
  "automated_actions": 35,
  "fallback_actions": 5,
  "review_required": [
    "Line 42: Invoke-Expression $cmd — unrecognised pattern",
    "Line 67: Custom DSC configuration block",
    "Line 88: COM object manipulation"
  ],
  "summary": "87.5% of actions map to idiomatic Ansible modules.",
  "recommendations": [
    "Review win_shell fallbacks at lines 42, 67, 88, 99, 120",
    "Consider ansible.windows.win_dsc for DSC resource blocks",
    "COM object operations may require custom Ansible modules"
  ]
}
```

### Improving Fidelity

When fidelity is lower than expected:

1. **Refactor complex conditionals** — split large `if/else` blocks into separate scripts before parsing
2. **Replace custom DSC blocks** — use `ansible.windows.win_dsc` directly in the converted playbook
3. **Handle `Invoke-Expression`** — replace with explicit cmdlets before parsing
4. **Modularise the script** — parse and convert smaller, focused scripts individually

---

## Enterprise Artefact Generation

### Windows Inventory (`inventory/hosts`)

Generated by `generate_windows_inventory_tool` / `powershell-inventory`:

```ini
[windows]
win01.example.com
win02.example.com

[windows:vars]
ansible_connection=winrm
ansible_winrm_transport=ssl
ansible_port=5986
ansible_winrm_server_cert_validation=ignore
ansible_user=ansible_svc
ansible_password={{ lookup('env', 'WIN_PASSWORD') }}
```

### Group Variables (`group_vars/windows.yml`)

Generated alongside the role:

```yaml
---
# Windows group variables
ansible_connection: winrm
ansible_winrm_transport: ssl
ansible_port: 5986
ansible_winrm_server_cert_validation: ignore
```

### Requirements File (`requirements.yml`)

Generated by `generate_windows_requirements` / `powershell-requirements`:

```yaml
---
collections:
  - name: ansible.windows
    version: ">=2.3.0"
  - name: community.windows
    version: ">=2.2.0"
  - name: chocolatey.chocolatey
    version: ">=1.5.0"
```

### AWX Job Template JSON

Generated by `generate_powershell_job_template` / `powershell-job-template` — a complete AWX-compatible JSON object with all fields pre-configured for Windows WinRM automation.

---

## AWX/AAP Job Template Import

### Using `awx-cli`

```bash
# Install the AWX CLI
pip install awxkit

# Configure connection
export TOWER_HOST=https://awx.example.com
export TOWER_USERNAME=admin
export TOWER_PASSWORD=secret

# Import the job template
awx job_templates create \
    --conf.host $TOWER_HOST \
    --conf.username $TOWER_USERNAME \
    --conf.password $TOWER_PASSWORD \
    < job_template.json
```

### Using the AWX REST API

```bash
curl -X POST \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $AWX_TOKEN" \
    -d @job_template.json \
    https://awx.example.com/api/v2/job_templates/
```

### Prerequisites in AWX/AAP

Before importing the job template, ensure these objects exist in AWX/AAP:

1. **Project**: A project pointing to the Git repository containing your generated role (e.g., `windows-migration-project`)
2. **Inventory**: A Windows inventory with WinRM connection variables (e.g., `windows-inventory`)
3. **Credential**: A Machine credential with Windows username/password (e.g., `windows-winrm-credential`)

---

## WinRM Configuration

### Enable WinRM on Windows Hosts

Run the following on each Windows managed node (requires Administrator):

```powershell
# Enable PSRemoting (enables WinRM)
Enable-PSRemoting -Force

# Configure HTTPS listener (recommended for production)
$cert = New-SelfSignedCertificate -DnsName $env:COMPUTERNAME -CertStoreLocation Cert:\LocalMachine\My
New-WSManInstance -ResourceURI winrm/config/Listener `
    -SelectorSet @{Address="*"; Transport="HTTPS"} `
    -ValueSet @{Hostname=$env:COMPUTERNAME; CertificateThumbprint=$cert.Thumbprint}

# Open firewall for WinRM HTTPS
netsh advfirewall firewall add rule name="WinRM HTTPS" dir=in action=allow protocol=TCP localport=5986
```

### Test WinRM Connectivity from Ansible

```bash
# Test from control node
ansible windows -i inventory/hosts -m ansible.windows.win_ping

# Test with explicit credentials
ansible windows -i inventory/hosts \
    -e "ansible_user=Administrator ansible_password=SecurePass123" \
    -m ansible.windows.win_ping
```

### Using Kerberos (Domain Environments)

For Active Directory environments, use Kerberos authentication instead of basic WinRM:

```ini
[windows:vars]
ansible_connection=winrm
ansible_winrm_transport=kerberos
ansible_port=5986
ansible_winrm_kerberos_delegation=true
```

Install the Kerberos Python library on the control node:

```bash
pip install pywinrm[kerberos]
```

---

## Troubleshooting

### WinRM Connection Refused

**Problem:** `ansible.windows.win_ping` fails with connection refused.

**Solutions:**

1. Verify WinRM is enabled: `winrm enumerate winrm/config/listener`
2. Check firewall: `Get-NetFirewallRule -Name "WINRM-*"`
3. Test port connectivity: `Test-NetConnection -ComputerName win01 -Port 5986`
4. Check WinRM service: `Get-Service WinRM`

### Certificate Validation Errors

**Problem:** SSL certificate validation fails.

**Solutions:**

1. Set `ansible_winrm_server_cert_validation=ignore` for self-signed certificates (non-production only)
2. Install a proper CA-signed certificate for production environments
3. Use HTTP transport on port 5985 (not recommended for production)

### Low Fidelity Score

**Problem:** Many `win_shell` fallbacks in converted playbook.

**Solutions:**

1. Run `powershell-fidelity` and review the `review_required` list
2. Refactor complex or obfuscated PowerShell before re-parsing
3. Replace `Invoke-Expression` with explicit cmdlets
4. Split large scripts into focused, single-purpose scripts

### Chocolatey Not Available on Target

**Problem:** `chocolatey.chocolatey.win_chocolatey` tasks fail because Chocolatey is not installed.

**Solution:** Add a task to install Chocolatey before the Chocolatey tasks:

```yaml
- name: Install Chocolatey
  ansible.windows.win_shell: |
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
  args:
    creates: C:\ProgramData\chocolatey\bin\choco.exe
```

### `win_dsc` Resource Not Found

**Problem:** Converted playbook uses `ansible.windows.win_dsc` but DSC resource is not installed.

**Solution:** Install the DSC resource module first:

```yaml
- name: Install DSC resource module
  community.windows.win_psmodule:
    name: xWebAdministration
    state: present
```

---

## See Also

- **[MCP Tools Reference](../user-guide/mcp-tools.md#powershell-migration)** — All 7 PowerShell migration MCP tools
- **[CLI Usage Guide](../user-guide/cli-usage.md#powershell-migration-commands)** — Command-line interface for all 7 commands
- **[Parsers API](../api-reference/parsers.md#powershell-parser)** — PowerShell parser technical reference
- **[Converters API](../api-reference/converters.md#powershell-converter)** — PowerShell converter and generators reference
- **[UI Guide](../user-guide/ui.md#powershell-migration)** — Web interface for PowerShell migration
- **[Migration Overview](overview.md)** — General Chef-to-Ansible migration guide
- **[AWX/AAP Integration](deployment.md)** — Deploying to AWX/AAP
