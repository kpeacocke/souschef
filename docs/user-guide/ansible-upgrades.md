# Ansible Upgrade Planning & Assessment

SousChef provides comprehensive tools for planning and executing Ansible version upgrades across your infrastructure and application automation. This guide covers version assessment, compatibility validation, and upgrade planning for both infrastructure and application automation deployments.

## Overview

Ansible powers infrastructure provisioning, application deployment, configuration management, and day-2 operations. When upgrading Ansible versions, you need to:

- Assess current Ansible and Python version compatibility
- Identify end-of-life (EOL) versions requiring urgent upgrades
- Plan safe upgrade paths with minimal disruption to infrastructure AND applications
- Validate collection compatibility against target versions
- Understand breaking changes between versions
- Generate comprehensive testing plans for infrastructure and application workloads

SousChef's upgrade planning tools automate this analysis and provide actionable recommendations.

## Quick Start

### Check Your Current Environment

Ask your AI assistant:

```
What version of Ansible am I running, and is it EOL?
```

Your assistant will use the `assess_ansible_environment` tool to:
- Detect Ansible Core and Python versions
- Check EOL status
- Identify compatibility issues
- Provide upgrade recommendations

### Generate an Upgrade Plan

Ask your AI assistant:

```
Plan an upgrade from Ansible 2.9 to Ansible 2.17
```

Your assistant will use the `generate_upgrade_plan` tool to:
- Calculate the safest upgrade path
- Identify breaking changes (e.g., 2.9 → 2.10 collections split)
- Estimate effort and timeline
- Provide step-by-step upgrade instructions
- Generate testing recommendations for infrastructure, apps, and day-2 operations

### Validate Collection Compatibility

Ask your AI assistant:

```
Check if my collections are compatible with Ansible 2.16
```

Your assistant will use the `validate_collection_compatibility` tool to:
- Parse your `requirements.yml`
- Check each collection against target Ansible version
- Identify incompatible collections
- Recommend compatible versions

## Available Tools

### 1. assess_ansible_environment

**Purpose**: Scan an Ansible environment and assess version compatibility.

**What it does**:
- Detects Ansible Core and Python versions from ansible.cfg, inventory, and installed packages
- Checks Python compatibility for control nodes and managed nodes
- Identifies EOL software requiring immediate attention
- Provides upgrade recommendations

**Use cases**:
- Initial environment assessment before upgrade planning
- Regular compatibility audits
- Identifying technical debt (EOL versions)

**Example usage**:
```
Assess the Ansible environment at /etc/ansible
```

### 2. check_ansible_eol_status

**Purpose**: Check if an Ansible version is end-of-life or approaching EOL.

**What it does**:
- Looks up EOL dates from official Ansible lifecycle data
- Calculates time remaining until EOL
- Warns about versions past EOL (security risk)
- Provides upgrade urgency recommendations

**Use cases**:
- Quick EOL status checks
- Security compliance audits
- Planning upgrade timelines

**Example usage**:
```
Is Ansible 2.9 still supported?
```

### 3. generate_upgrade_plan

**Purpose**: Create a detailed, step-by-step Ansible upgrade plan.

**What it does**:
- Calculates the safest upgrade path (may include intermediate versions)
- Identifies all breaking changes between versions
- Provides pre-upgrade checklist (backup strategies, testing requirements)
- Generates upgrade steps with rollback procedures
- Estimates effort in person-days
- Assesses risk level (Low/Medium/High)
- Includes testing strategy for infrastructure, applications, and operational playbooks

**Use cases**:
- Complete upgrade project planning
- Risk assessment for change management
- Resource estimation for capacity planning

**Example usage**:
```
Generate a complete upgrade plan from Ansible 2.9 to 2.17
```

### 4. validate_collection_compatibility

**Purpose**: Validate Ansible collections against a target Ansible version.

**What it does**:
- Parses `collections/requirements.yml`
- Checks each collection's compatibility with target Ansible version
- Identifies collections that need updates
- Recommends compatible collection versions
- Warns about deprecated collections

**Use cases**:
- Pre-upgrade collection validation
- Dependency conflict resolution
- Migration from ansible-base 2.10+ to ansible-core

**Example usage**:
```
Validate collections in requirements.yml against Ansible 2.16
```

### 5. plan_ansible_upgrade

**Purpose**: High-level upgrade planning with version path calculation.

**What it does**:
- Recommends optimal upgrade sequence
- Identifies intermediate versions if needed
- Highlights major milestones (e.g., 2.9 → 2.10 collections migration)
- Provides timeline estimates
- Integrates Python version requirements

**Use cases**:
- Strategic upgrade planning
- Multi-version upgrade roadmaps
- Briefing executives and stakeholders

**Example usage**:
```
What's the best way to upgrade from Ansible 2.9 to the latest version?
```

## Common Upgrade Scenarios

### Scenario 1: Upgrading from Legacy Ansible 2.9

**Challenge**: Ansible 2.9 reached EOL in 2022. The 2.9 → 2.10 transition introduced the collections split, a major architectural change.

**Workflow**:

1. **Assess current state**:
   ```
   Assess my Ansible 2.9 environment at /etc/ansible
   ```

2. **Check EOL urgency**:
   ```
   Is Ansible 2.9 still supported?
   ```

3. **Generate upgrade plan**:
   ```
   Plan an upgrade from Ansible 2.9 to 2.16
   ```

   The plan will include:
   - Pre-upgrade: Migrate to `ansible.builtin` namespace for core modules
   - Python version upgrade (probably needed for control node)
   - Collection migration strategy
   - Testing requirements for infrastructure, application deployments, and operational automation

4. **Validate collections**:
   ```
   Validate my collections against Ansible 2.16
   ```

5. **Execute upgrade** following the generated plan

### Scenario 2: Staying Current with Minor Upgrades

**Challenge**: You're on Ansible 2.14 and want to upgrade to 2.16 to stay current.

**Workflow**:

1. **Generate upgrade plan**:
   ```
   Plan an upgrade from Ansible 2.14 to 2.16
   ```

2. **Validate collections**:
   ```
   Check collection compatibility with Ansible 2.16
   ```

3. **Review breaking changes** (typically minimal for minor upgrades)

4. **Execute upgrade** with lower risk than major version jumps

### Scenario 3: Python Version Constraints

**Challenge**: Your Ansible version requires Python 2.7, but managed nodes are upgrading to Python 3.

**Workflow**:

1. **Assess environment**:
   ```
   Assess my Ansible environment
   ```

2. **Plan Python-compatible upgrade**:
   ```
   Plan an upgrade that supports Python 3.9 on managed nodes
   ```

3. **Validate collections** for Python 3 compatibility

4. **Execute phased rollout**:
   - Upgrade control node first
   - Test with mixed Python environment
   - Upgrade managed nodes

### Scenario 4: Application Deployment Automation

**Challenge**: You use Ansible to deploy and manage applications, not just infrastructure. Application playbooks may have dependencies on specific collection versions, roles, or modules.

**Workflow**:

1. **Assess environment with application focus**:
   ```
   Assess my Ansible environment, focusing on application deployment playbooks
   ```

2. **Generate upgrade plan**:
   ```
   Plan an upgrade from Ansible 2.12 to 2.16, including application deployment considerations
   ```

3. **Validate application-critical collections**:
   ```
   Validate collections used in application deployments against Ansible 2.16
   ```

4. **Test application deployments**:
   - Run application playbooks in staging environment
   - Validate CI/CD pipeline integration
   - Test day-2 operations (scaling, updates, rollbacks)
   - Verify monitoring and logging playbooks

5. **Execute phased rollout**:
   - Upgrade non-production environments first
   - Test application deployments thoroughly
   - Gradual production rollout

## Best Practices

### Before Upgrading

1. **Backup everything**:
   - Export current Ansible configuration
   - Backup inventory files
   - Version control all playbooks and roles
   - Document current state

2. **Test in non-production first**:
   - Create identical staging environment
   - Run full test suite
   - Test infrastructure provisioning
   - Test application deployments
   - Test day-2 operations (backups, scaling, updates)
   - Validate CI/CD pipelines

3. **Review breaking changes carefully**:
   - Read Ansible porting guides
   - Test deprecated module replacements
   - Update jinja2 templates if needed
   - Check collection changelogs

4. **Communicate with your team**:
   - Share upgrade plan with stakeholders
   - Schedule maintenance windows
   - Plan rollback procedures
   - Document new features and changes

### During Upgrade

1. **Follow the generated plan sequentially**
2. **Upgrade control node first**, then managed nodes
3. **Validate at each step** with smoke tests
4. **Keep detailed notes** of any issues encountered
5. **Test critical playbooks** after each intermediate version

### After Upgrade

1. **Run comprehensive test suites**:
   - Infrastructure provisioning tests
   - Application deployment tests
   - Day-2 operations tests
   - Integration tests with other tools

2. **Update documentation**:
   - Document new Ansible version
   - Update playbook examples with new syntax
   - Note deprecated features to avoid
   - Update CI/CD pipeline configs

3. **Monitor for issues**:
   - Watch for deprecation warnings
   - Monitor application deployment success rates
   - Check log aggregation for errors
   - Review automation metrics

4. **Plan regular upgrades**:
   - Schedule quarterly compatibility reviews
   - Stay within 2-3 minor versions of current
   - Upgrade before EOL dates
   - Keep dependencies current

## Understanding Breaking Changes

### Ansible 2.9 → 2.10 (Major)

**Collections Split**: The biggest change in Ansible history.

- **What changed**: Core modules moved to `ansible.builtin` collection
- **Impact**: Playbooks that don't specify collection names will break
- **Fix**: Prefix all core modules with `ansible.builtin.` or update playbooks
- **Application impact**: Review all application deployment playbooks for module namespace changes

### Ansible 2.10 → 2.11 (Minor)

- Python 2.7 support dropped on control nodes
- Some modules deprecated
- New collection versions required

### Ansible 2.11 → 2.12 (Minor)

- Python 3.8+ required on control nodes
- Module defaults handling changes
- Collection dependency resolution improved

### Ansible 2.12+ (Minor Updates)

Each minor version typically includes:
- Deprecation warnings for future removal
- New collection requirements
- Security fixes
- Performance improvements

Check the `generate_upgrade_plan` output for version-specific breaking changes.

## Troubleshooting

### "Module not found" after upgrade

**Cause**: Collection not installed or module moved to different collection.

**Solution**:
1. Check if module is in `ansible.builtin` collection
2. Install required collection: `ansible-galaxy collection install <collection>`
3. Update module FQCN in playbooks

### "Python version incompatible" errors

**Cause**: Ansible version doesn't support installed Python version.

**Solution**:
1. Check Python requirements: `assess_ansible_environment`
2. Upgrade Python to compatible version
3. Update `ansible_python_interpreter` in inventory
4. Test with multiple Python versions if managing mixed environments

### "Collection incompatible" warnings

**Cause**: Collection version doesn't support target Ansible version.

**Solution**:
1. Run: `validate_collection_compatibility`
2. Update `requirements.yml` with compatible versions
3. Reinstall: `ansible-galaxy collection install -r requirements.yml --force`

### Application deployments fail after upgrade

**Cause**: Playbooks may rely on deprecated features, specific module versions, or changed defaults.

**Solution**:
1. Review playbook for deprecated syntax
2. Test in staging with verbose output: `ansible-playbook -vvv`
3. Check collection changelogs for breaking changes
4. Update application-specific roles/modules
5. Validate CI/CD pipeline integration
6. Test rollback procedures

## Additional Resources

- **Ansible Porting Guides**: Official migration guides between versions
- **Collection Documentation**: Check individual collection changelogs
- **SousChef Architecture**: See [ARCHITECTURE.md](../ARCHITECTURE.md) for implementation details
- **API Reference**: See [ansible_upgrade.py API docs](../api-reference/) for technical details

## Getting Help

If you encounter issues:

1. Review the generated upgrade plan for specific guidance
2. Check Ansible release notes and porting guides
3. Test in isolated environment before production
4. Open a [GitHub issue](https://github.com/kpeacocke/souschef/issues) with details
5. Ask in [GitHub Discussions](https://github.com/kpeacocke/souschef/discussions)

For security-related Ansible version issues, see [SECURITY.md](../../SECURITY.md).
