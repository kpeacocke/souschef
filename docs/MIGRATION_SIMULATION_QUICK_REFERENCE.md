# Migration Simulation - Quick Reference

**Three new MCP tools now available for testing Chef→Ansible migrations across all version combinations.**

## Available Version Combinations (18 total)

### Chef Origins
- **12.19.36** - Supports both SHA-1 and SHA-256 authentication
- **14.15.6** - SHA-256 only, deprecated SHA-1
- **15.10.91** - Latest (Feb 2026), SHA-256 mandatory, FIPS support

### Target Platforms
- **Tower 3.8.5** - Legacy (virtualenv only)
- **AWX 20.1.0** - Pre-EE model (virtualenv)
- **AWX 21.0.0** - EE transition (both models supported)
- **AWX 22.0.0** - Full EE support
- **AWX 24.6.1** - Current AWX (EE required, July 2024)
- **AAP 2.4.0** - AAP current (EE required + content signing)

## Tool 1: List All Combinations

```
list_migration_version_combinations()
```

Returns all 18 supported combinations with execution model, Ansible version, and feature requirements.

**Example Response**:
```json
{
  "combinations": [
    {
      "chef_version": "12.19.36",
      "target_platform": "tower",
      "target_version": "3.8.5",
      "execution_model": "custom_virtualenv",
      "ansible_version": "2.9.0",
      "requires_fips": false,
      "requires_signing": false
    },
    ...
  ],
  "total": 18
}
```

## Tool 2: Get Version Info

```
get_version_combination_info(
  chef_version,     # "12.19.36", "14.15.6", or "15.10.91"
  target_platform,  # "tower", "awx", or "aap"
  target_version    # e.g., "24.6.1", "2.4.0"
)
```

Returns detailed info about a specific version combination including authentication protocol, available API endpoints, job template structure, and feature requirements.

**Examples**:

### Legacy Migration
```
get_version_combination_info("12.19.36", "tower", "3.8.5")
→ SHA-1/SHA-256 auth, virtualenv model, Ansible 2.9.0
```

### Current Production
```
get_version_combination_info("14.15.6", "awx", "24.6.1")
→ SHA-256 auth, execution_environment required, Ansible 2.16.0
```

### Latest Platform
```
get_version_combination_info("15.10.91", "aap", "2.4.0")
→ SHA-256 (FIPS), execution_environment required, content signing enabled, Ansible 2.15.0
```

## Tool 3: Configure Simulation

```
configure_migration_simulation(
  chef_version,     # Source Chef version
  target_platform,  # Destination platform
  target_version,   # Platform version
  fips_mode         # "yes" or "no" (optional)
)
```

Creates a configured simulation ready for testing. Returns mock endpoint configuration, job template template, mock headers, and feature flags.

**Response includes**:
- Authentication protocol to use
- Execution model (virtualenv vs execution_environment)
- Required Ansible version
- Available API endpoints to mock
- Job template structure
- Mock HTTP response headers
- Feature flags (FIPS, signing, EE)

## Key Functional Differences

### Authentication Protocol Changes
- **Chef 12.x**: Supports both SHA-1 (protocol 1.0) and SHA-256 (protocol 1.3)
- **Chef 14.x+**: SHA-256 only (protocol 1.3)
- **Chef 15.x**: SHA-256 mandatory, FIPS compliance required

### Execution Model Changes
- **Pre-AWX 21**: Use `custom_virtualenv: "/path/to/venv"` field
- **AWX 21+**: Use `execution_environment: <ID>` field (required)
- **AAP 2.4+**: Use `execution_environment` + `content_signing: true`

### API Endpoint Availability
- **Tower 3.8**: `/api/v2/` basic endpoints
- **AWX 20**: Tower endpoints + `/api/v2/custom_virtualenvs/`
- **AWX 21+**: Adds `/api/v2/execution_environments/`, removes custom_virtualenvs
- **AWX 24.6+**: Adds `/api/v2/mesh_visualizer/`
- **AAP 2.4+**: Adds `/api/v2/instances/`, `/api/v2/content_signing/`

## Real-World Scenarios

### Scenario 1: Migrate Chef Cookbooks from Tower 3.8
```
tool: list_migration_version_combinations()
→ Shows Chef 12.x or 14.x → Tower 3.8.5 uses virtualenv model

tool: get_version_combination_info("12.19.36", "tower", "3.8.5")
→ Auth: SHA-1/SHA-256, Execution: virtualenv, Ansible: 2.9.0

tool: configure_migration_simulation("12.19.36", "tower", "3.8.5")
→ Ready to mock Tower 3.8 APIs with virtualenv configuration
```

### Scenario 2: Upgrade to AWX 24.6.1 (Current)
```
tool: get_version_combination_info("14.15.6", "awx", "24.6.1")
→ Auth: SHA-256, Execution: execution_environment (REQUIRED), Ansible: 2.16.0

tool: configure_migration_simulation("14.15.6", "awx", "24.6.1")
→ Ready to test with:
  - SHA-256 authentication
  - Execution environment references
  - Modern AWX 24.6.1 API endpoints
  - Ansible 2.16.0 compatibility
```

### Scenario 3: Latest Chef to Latest AAP
```
tool: get_version_combination_info("15.10.91", "aap", "2.4.0")
→ Auth: SHA-256 + FIPS, Execution: EE required, Signing: enabled, Ansible: 2.15.0

tool: configure_migration_simulation("15.10.91", "aap", "2.4.0", fips_mode="yes")
→ Full modern stack:
  - FIPS-compliant SHA-256 authentication
  - Execution environments (mandatory)
  - Content signing for supply chain security
  - All AAP 2.4.0 API endpoints
  - Ansible 2.15.0 core
```

## Testing Your Migration

1. **List options**: Use `list_migration_version_combinations()` to see all possibilities
2. **Get details**: Use `get_version_combination_info()` for your specific combination
3. **Configure mock**: Use `configure_migration_simulation()` to set up testing
4. **Run conversion**: Execute your Chef→Ansible conversion with mocked APIs
5. **Validate**: Confirm generated playbooks work with target Ansible version

## Important Notes

### Version Stability
- **Chef APIs**: Functionally stable across 12.x-15.x (only auth protocol changes)
- **AWX APIs**: Breaking change at 21.x (virtualenv → execution_environment model)
- **AAP**: Additional features but compatible with AWX API

### This Implementation Covers
✅ All 18 valid Chef→Ansible version combinations
✅ Execution model differences (virtualenv vs EE)
✅ Authentication protocol variations
✅ Feature availability per version
✅ Ansible version requirements
✅ API endpoint availability

### Not Yet Implemented (Future)
⏳ Actual mock API responses
⏳ Full migration execution with mocks
⏳ Validation engine for generated playbooks
⏳ Test recording and replay

