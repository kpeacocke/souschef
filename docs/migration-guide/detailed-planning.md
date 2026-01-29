# Detailed Migration Planning Guide

This guide provides comprehensive questions and considerations for planning a complex Chef-to-Ansible migration. Use this alongside the GitHub issue templates for larger or more complex migration projects.

## Table of Contents
1. [Chef Environment Assessment](#chef-environment-assessment)
2. [Target Ansible Architecture](#target-ansible-architecture)
3. [Technical Migration Challenges](#technical-migration-challenges)
4. [Organisational & Change Management](#organisational--change-management)
5. [SousChef Integration Strategy](#souschef-integration-strategy)
6. [Success Metrics](#success-metrics)

## Chef Environment Assessment

### Current Deployment Model
- Chef Server / Chef Zero / Chef Solo?
- Number of managed nodes
- Operating systems in scope
- Multi-datacenter or single environment?
- Geographic distribution of infrastructure

### Cookbook Inventory
**Questions to answer:**

1. **How many cookbooks total?**
   - How many are community cookbooks?
   - How many are custom/organisational cookbooks?
   - What's the dependency graph complexity?

2. **What types of cookbooks exist?**
   - Infrastructure cookbooks (networking, monitoring, logging)
   - Application cookbooks (web apps, databases, caching)
   - Wrapper/orchestration cookbooks
   - Policy/enforcement cookbooks
   - Testing/compliance cookbooks (InSpec)

3. **Cookbook complexity indicators:**
   - Average lines of code per recipe?
   - Number of custom resources?
   - Heavy use of Chef search?
   - Data bag dependencies?
   - Attribute precedence complexity?

### Chef Patterns and Features Used

**Data Management:**
- Data bags (encrypted or plain?)
- Attributes (node, default, override precedence?)
- Environments
- Roles (how are they structured?)
- Berkshelf / Policyfiles for dependency management?

**Resource Patterns:**
- Basic resources (service, package, file, template)
- Custom resources / Light-weight Resource Providers (LWRPs)
- Ruby blocks for custom logic
- Notifications and subscriptions patterns
- Guards and conditional execution
- Run-time generated resources

**Advanced Features:**
- Chef search (simple lookups vs. complex queries?)
- Custom Ohai plugins
- Chef handlers for post-run actions
- Compliance as code (InSpec integration)
- Chef provisioning / machine resources
- Test Kitchen integration

**Application Patterns:**
- Deployment resources (deploy, git checkouts)
- Source control integrations
- File rendering from templates
- Application-specific resource types
- Multi-tier application orchestration

## Target Ansible Architecture

### Deployment Model Decision
**Choose your Ansible deployment model:**

**Option 1: Ansible Core**
- Best for: Simple, CLI-driven deployments
- Tools: Ansible, ansible-playbook, ad-hoc commands
- Complexity: Lower operational overhead
- Learning curve: Moderate

**Option 2: AWX (Open Source)**
- Best for: Team collaboration, UI-based management
- Tools: AWX UI, REST API, RBAC
- Complexity: Moderate operational overhead
- Learning curve: Higher, but more discoverable

**Option 3: Ansible Automation Platform (Red Hat)**
- Best for: Enterprise environments, support requirements
- Tools: AAP UI, REST API, advanced features
- Complexity: Significant operational overhead
- Learning curve: Highest, but with support available

### Inventory Strategy
- **Static inventory**: YAML files, ini files, static configuration
- **Dynamic inventory**: Cloud providers, CMDB, IPAM
- **Hybrid inventory**: Static + dynamic sources
- **Inventory organisation**: Geographic, functional, by app tier?
- **Variable scoping**: How will you manage group_vars, host_vars?

### Variable and Secret Management
- **Variable sources**:
  - group_vars / host_vars
  - Playbook/role defaults
  - External variable files
  - AWX/AAP credential stores
  
- **Secret management**:
  - Ansible Vault for simple encryption
  - External vault systems (HashiCorp Vault)
  - Cloud provider secret managers
  - AWX/AAP credential handling
  
- **Precedence strategy**: How will you handle variable precedence conflicts?

### Playbook Organisation
**Choose a structure:**

**Option 1: Playbook per cookbook**
```
playbooks/
  web-app.yml          # Replaces web-app cookbook
  database.yml         # Replaces database cookbook
  monitoring.yml       # Replaces monitoring cookbook
```

**Option 2: Role-based**
```
roles/
  web_server/
  database_server/
  monitoring_agent/
  load_balancer/
```

**Option 3: Collection-based (Professional)**
```
collections/
  company.infrastructure/
    roles/
    plugins/
    modules/
  company.applications/
    roles/
    playbooks/
```

**Decision factors:**
- Team expertise level
- Project complexity
- Code reusability requirements
- Maintenance burden

## Technical Migration Challenges

### Custom Resources and Providers
**Assessment:**
- How many custom resources exist?
- How complex is their logic?
- Are they well-documented?

**Migration paths:**
1. **Direct mapping** - If Ansible module exists
2. **Custom module** - Develop Ansible equivalent
3. **Shell/script tasks** - Temporary solution
4. **Ansible plugin** - For complex logic

**Example mapping exercise:**

```ruby
# Chef custom resource
custom_resource 'app_deploy' do
  property :version, String, required: true
  property :config_path, String
  action :deploy
end
```

**Possible Ansible equivalents:**
```yaml
# Option 1: Use existing Ansible module
- name: Deploy application
  community.app_modules.deploy:
    version: "{{ app_version }}"
    config: "{{ app_config_path }}"

# Option 2: Create custom Ansible module
- name: Deploy application
  my_company.infrastructure.app_deploy:
    version: "{{ app_version }}"
    config: "{{ app_config_path }}"

# Option 3: Use shell commands (temporary)
- name: Deploy application
  shell: |
    /opt/app/deploy.sh --version {{ app_version }}
```

### Data Management Complexity

**Chef data bags → Ansible equivalents:**

```ruby
# Chef: Encrypted data bag lookup
db_config = data_bag_item('secrets', 'database')
```

**Ansible approaches:**
```yaml
# Option 1: Ansible Vault
# roles/app/defaults/encrypted.yml (encrypted with ansible-vault)
db_password: !vault-encrypted

# Option 2: External secret store
- name: Get secrets from vault
  hashicorp.vault.vault_write:
    path: secret/data/database
    
# Option 3: AWX credential store
- name: Use AAP credentials
  vars:
    db_password: "{{ vault_db_password }}"
```

**Critical questions:**
- What secrets are currently encrypted?
- Where will they stored post-migration?
- How will rotation be handled?
- What audit/compliance requirements exist?

### Chef Search Replacement

**Chef search pattern:**
```ruby
# Find all database nodes
db_nodes = search(:node, 'role:database_master')
db_nodes.each do |node|
  # Configure replication
end
```

**Ansible equivalents:**

```yaml
# Option 1: Ansible inventory groups
- name: Configure replication on master
  hosts: database_master
  tasks:
    - name: Setup replication
      # ...

# Option 2: Dynamic inventory groups
- name: Get database masters from CMDB
  api_query:
    url: "{{ cmdb_api }}/nodes?role=database_master"
  register: db_masters

# Option 3: Host facts based query
- hosts: all
  gather_facts: yes
  tasks:
    - name: Configure replication on masters
      hosts: "{{ groups['all'] | selectattr('ansible_facts.role', 'equalto', 'database_master') }}"
```

### Testing and Validation Strategy

**Chef → Ansible testing migration:**

| Chef | Ansible |
|------|---------|
| Test Kitchen | Molecule |
| ChefSpec (unit) | Pytest, Testinfra |
| InSpec (compliance) | Ansible Lint, Custom playbooks |
| Foodcritic (style) | Ansible Lint, yamllint |

**Migration path:**
1. Extract current InSpec tests
2. Convert to Ansible-native testing
3. Integrate into CI/CD
4. Run alongside Chef during transition (parallel testing)

## Organisational & Change Management

### Stakeholder Alignment
**Questions to address with stakeholders:**

1. **Business motivation**
   - Why migrate from Chef to Ansible?
   - What are the expected benefits?
   - What are the risks and constraints?

2. **Timeline and resources**
   - How long can migration take?
   - How many people are available?
   - What's the critical path?

3. **Operational impact**
   - Can services be interrupted?
   - What's the acceptable downtime?
   - Who approves changes?

### Team Training and Enablement

**Knowledge gap assessment:**
- How many people know Chef?
- How many know Ansible?
- What's the learning curve tolerance?

**Training path:**
1. **Ansible basics** - Architecture, modules, roles, playbooks
2. **Ansible best practices** - Code organisation, variable scoping
3. **Your specific setup** - Custom modules, integrations, workflows
4. **Hands-on labs** - Practice converting cookbooks
5. **Parallel operations** - Run Chef and Ansible together during transition

### Rollback Strategy

**Plan for reversions:**
- How do you roll back if Ansible deployment fails?
- Can you run Chef and Ansible in parallel?
- What's the maximum rollback time?
- How will you validate rollback success?

**Common approaches:**
1. **Blue-green deployment** - Run both systems, switch traffic
2. **Canary deployment** - Roll out to subset, monitor, expand
3. **Parallel runs** - Chef and Ansible together (eventually remove Chef)
4. **Feature flags** - Gradually enable Ansible-managed services

## SousChef Integration Strategy

### Using SousChef for Analysis

**Discovery phase:**
```bash
# Analyse cookbook structure
souschef-cli structure /path/to/cookbook

# Parse individual recipes
souschef-cli recipe recipes/default.rb

# Extract dependencies
souschef-cli dependencies cookbook/
```

**Output usage:**
- Understand cookbook complexity
- Identify custom resources
- Find Chef search patterns
- Extract attribute dependencies

### Conversion Workflow

**1. Assessment**
- Use SousChef to analyse current cookbooks
- Identify patterns that need custom handling
- Plan resource mappings
- Document exceptions

**2. Initial conversion**
- Use SousChef tools to generate skeleton playbooks
- Review generated code for accuracy
- Identify gaps and custom requirements
- Iteratively refine

**3. Validation**
- Compare converted playbooks against original
- Test in non-production environments
- Validate idempotency
- Performance testing

**4. Refinement**
- Optimise generated code
- Add error handling
- Improve structure and readability
- Documentation updates

### Handling SousChef Limitations

**What SousChef handles well:**
- Basic Chef resources
- Template conversion
- Metadata extraction
- Recipe structure analysis

**What needs manual work:**
- Complex Chef search queries
- Custom resource logic
- Ad-hoc Ruby blocks
- Complex attribute merging
- Encrypted data bags

**Strategy:**
- Use SousChef for initial structure
- Manually refine complex areas
- Document custom mappings
- Share learnings with team

## Success Metrics

### Technical Success Criteria

**Functional equivalence:**
- [ ] All resources are converted or mapped
- [ ] All services start and remain running
- [ ] Configuration is applied correctly
- [ ] Templating produces same output
- [ ] Service health checks pass

**Operational parity:**
- [ ] Performance is equivalent or better
- [ ] Security posture maintained
- [ ] Compliance requirements met
- [ ] Backup/restore procedures work
- [ ] Monitoring/alerting intact

**Quality metrics:**
- [ ] Playbook code quality (ansible-lint)
- [ ] YAML formatting standards
- [ ] Variable naming consistency
- [ ] Documentation completeness

### Timeline Milestones

**Phase 1: Planning & Preparation** (Weeks 1-2)
- [ ] Assessment complete
- [ ] Architecture designed
- [ ] Team trained
- [ ] Pilot cookbooks selected
- [ ] Success criteria defined

**Phase 2: Pilot Migration** (Weeks 3-6)
- [ ] Convert 2-3 simple cookbooks
- [ ] Validate conversions
- [ ] Refine processes
- [ ] Document learnings
- [ ] Get feedback

**Phase 3: Scale** (Weeks 7-12)
- [ ] Convert remaining cookbooks
- [ ] Integrate into CI/CD
- [ ] Performance testing
- [ ] Security validation
- [ ] Preparation for rollout

**Phase 4: Parallel Running** (Weeks 13-16)
- [ ] Deploy Ansible alongside Chef
- [ ] Run both management systems
- [ ] Monitor for discrepancies
- [ ] Validate idempotency
- [ ] Train operations team

**Phase 5: Cutover & Cleanup** (Weeks 17-20)
- [ ] Switch to Ansible-only
- [ ] Monitor for issues
- [ ] Decommission Chef
- [ ] Archive migration artifacts
- [ ] Document final state

### Risk Assessment

**High-risk areas for your migration:**
- Custom resources complexity?
- Data bag encryption handling?
- Critical business services dependency?
- Team Ansible expertise level?
- Rollback procedure complexity?

**Mitigation strategies:**
- Extra testing for high-risk areas
- Dedicated team for complex conversions
- Extended parallel running period
- Conservative rollout schedule
- Strong monitoring and alerting

---

**Need help?** Create a [Migration Support Request](../ISSUE_TEMPLATE/migration_support.md) on GitHub or consult the SousChef documentation.
