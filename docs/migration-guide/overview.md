# Migration Guide Overview

This guide provides a comprehensive methodology for migrating from Chef to Ansible, leveraging SousChef's 38 MCP tools and proven enterprise practices.

## Migration Philosophy

!!! quote "Start Small, Scale Smart"
    Successful migrations follow an incremental approach: assess thoroughly, convert systematically, validate continuously, and deploy confidently.

### Core Principles

1. **Assessment First**: Understand your Chef infrastructure before converting
2. **Incremental Migration**: Start with simple cookbooks, build expertise
3. **Continuous Validation**: Test conversions at every step
4. **Automation-Driven**: Leverage SousChef tools for consistency
5. **Documentation**: Maintain clear records throughout the migration

---

## Migration Phases

The migration process follows five distinct phases, each building on the previous:

```mermaid
graph LR
    A[1. Discovery] --> B[2. Assessment]
    B --> C[3. Conversion]
    C --> D[4. Validation]
    D --> E[5. Deployment]

    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#f3e5f5
    style D fill:#e8f5e9
    style E fill:#fce4ec
```

### Phase 1: Discovery & Inventory

**Objective**: Catalog all Chef infrastructure and dependencies.

**Activities:**
- Inventory all cookbooks and their dependencies
- Identify Chef server configurations
- Document data bags and environments
- Map search queries and inventory sources
- Catalog InSpec profiles and tests
- Identify Habitat plans (if applicable)

**SousChef Tools:**
- `list_cookbook_structure` - Map cookbook organization
- `read_cookbook_metadata` - Extract dependency information
- `analyze_cookbook_dependencies` - Build dependency graphs
- `analyze_chef_databag_usage` - Document data bag usage
- `analyze_chef_environment_usage` - Catalog environments

**Deliverable**: Complete inventory document with dependency map.

---

### Phase 2: Assessment & Planning

**Objective**: Evaluate migration complexity and create execution plan.

**Activities:**
- Assess migration complexity per cookbook
- Identify risks and mitigation strategies
- Prioritize migration order based on dependencies
- Estimate effort and timeline
- Plan resource allocation
- Define success metrics

**SousChef Tools:**
- `assess_chef_migration_complexity` - Automated complexity scoring
- `analyze_cookbook_dependencies` - Determine migration order
- `generate_migration_plan` - Create detailed execution plan
- `generate_migration_report` - Stakeholder documentation

**Deliverable**: Migration plan with timeline, resources, and risk assessment.

**Assessment Criteria:**

| Complexity Factor | Low Risk | Medium Risk | High Risk |
|-------------------|----------|-------------|-----------|
| Cookbook size | < 5 recipes | 5-15 recipes | > 15 recipes |
| Custom resources | 0-2 | 3-5 | > 5 |
| Dependencies | 0-3 | 4-7 | > 7 |
| Data bag usage | None | 1-3 bags | > 3 bags |
| Search queries | 0-2 | 3-5 | > 5 |
| Guard complexity | Simple | Moderate | Complex/nested |

---

### Phase 3: Conversion & Transformation

**Objective**: Convert Chef cookbooks to Ansible playbooks.

**Activities:**
- Convert recipes to playbooks
- Transform custom resources to roles/modules
- Convert ERB templates to Jinja2
- Migrate data bags to Ansible variables/vault
- Transform environments to inventory groups
- Convert Chef search to dynamic inventory
- Generate AWX/AAP configurations (if applicable)
- Migrate Habitat to containers (if applicable)

**SousChef Tools:**

**Core Conversion:**
- `generate_playbook_from_recipe` - Recipe → playbook conversion
- `convert_resource_to_task` - Individual resource conversion
- `parse_template` - ERB → Jinja2 conversion
- `parse_custom_resource` - Custom resource analysis

**Data & Configuration:**
- `convert_chef_databag_to_vars` - Data bags → variables
- `generate_ansible_vault_from_databags` - Encrypted data migration
- `convert_chef_environment_to_inventory_group` - Environments → inventory
- `convert_chef_search_to_inventory` - Search → dynamic inventory

**Enterprise Integration:**
- `generate_awx_job_template_from_cookbook` - AWX job templates
- `generate_awx_workflow_from_chef_runlist` - AWX workflows
- `generate_awx_project_from_cookbooks` - AWX project structure

**Habitat Migration:**
- `parse_habitat_plan` - Analyze Habitat plans
- `convert_habitat_to_dockerfile` - Habitat → Docker
- `generate_compose_from_habitat` - Multi-service orchestration

**Deliverable**: Converted Ansible content with comprehensive test coverage.

---

### Phase 4: Validation & Testing

**Objective**: Verify conversion accuracy and functional equivalence.

**Activities:**
- Validate conversion syntax and semantics
- Test playbooks in development environment
- Generate and execute InSpec validations
- Perform security audits
- Benchmark performance
- Document discrepancies and workarounds

**SousChef Tools:**
- `validate_conversion` - Multi-dimensional validation
- `generate_inspec_from_recipe` - Generate validation tests
- `convert_inspec_to_test` - Convert existing InSpec to Ansible tests
- `profile_cookbook_performance` - Performance profiling

**Validation Dimensions:**

1. **Syntax Validation**
   - YAML syntax correctness
   - Jinja2 template validity
   - Python syntax (custom modules)

2. **Semantic Validation**
   - Logic equivalence to Chef
   - Variable usage correctness
   - Resource dependency preservation

3. **Best Practice Validation**
   - Ansible naming conventions
   - Idempotency verification
   - Task organization standards

4. **Security Validation**
   - Privilege escalation patterns
   - Sensitive data handling
   - Vault encryption verification

5. **Performance Validation**
   - Execution time benchmarks
   - Resource utilization
   - Optimization opportunities

**Deliverable**: Validated playbooks with test results and acceptance criteria met.

---

### Phase 5: Deployment & Cutover

**Objective**: Deploy Ansible content to production with minimal disruption.

**Activities:**
- Deploy to staging environment
- Execute parallel runs (Chef + Ansible)
- Perform blue/green or canary deployments
- Monitor and compare results
- Execute cutover plan
- Decommission Chef infrastructure
- Document lessons learned

**SousChef Tools:**
- `convert_chef_deployment_to_ansible_strategy` - Deployment patterns
- `generate_blue_green_deployment_playbook` - Zero-downtime deployments
- `generate_canary_deployment_strategy` - Gradual rollouts

**Deployment Strategies:**

=== "Blue/Green"
    **Best for**: Full environment swaps, quick rollback capability

    ```yaml
    # Blue environment (current)
    - hosts: blue_servers
      tasks:
        - name: Deploy current version

    # Green environment (new)
    - hosts: green_servers
      tasks:
        - name: Deploy new version
        - name: Run validation

    # Switch traffic
    - hosts: load_balancers
      tasks:
        - name: Point to green environment
    ```

=== "Canary"
    **Best for**: Gradual rollout with monitoring

    ```yaml
    # Stage 1: 10% traffic
    - hosts: canary_10pct
      tasks:
        - name: Deploy to 10% of fleet
        - name: Monitor metrics

    # Stage 2: 50% traffic
    - hosts: canary_50pct
      when: canary_10pct_success

    # Stage 3: 100% traffic
    - hosts: all_servers
      when: canary_50pct_success
    ```

=== "Parallel Run"
    **Best for**: Risk mitigation, comparison testing

    ```yaml
    # Run Chef (readonly/reporting mode)
    - hosts: all
      tasks:
        - name: Execute Chef in why-run mode
          command: chef-client --why-run
          register: chef_result

    # Run Ansible
    - hosts: all
      tasks:
        - name: Execute Ansible playbook
          include_role:
            name: migrated_cookbook
          register: ansible_result

    # Compare results
    - hosts: localhost
      tasks:
        - name: Analyze differences
          debug:
            msg: "Comparison: {{ chef_result }} vs {{ ansible_result }}"
    ```

**Deliverable**: Production deployment with monitoring and rollback procedures.

---

## Migration Patterns

### Pattern 1: Simple Cookbook (Low Complexity)

**Characteristics:**
- 1-3 recipes
- No custom resources
- Minimal dependencies
- No data bags or search

**Recommended Approach:**
1. Direct conversion with `generate_playbook_from_recipe`
2. Manual review and adjustment
3. Basic validation with `validate_conversion`
4. Deploy to dev/staging
5. Production deployment

**Timeline**: 1-2 days per cookbook

---

### Pattern 2: Standard Application Cookbook (Medium Complexity)

**Characteristics:**
- 5-10 recipes
- 1-3 custom resources
- Multiple dependencies
- Uses data bags and/or environments
- Some Chef search usage

**Recommended Approach:**
1. Assess with `assess_chef_migration_complexity`
2. Plan migration order with `analyze_cookbook_dependencies`
3. Convert recipes systematically
4. Transform custom resources to roles
5. Migrate data bags to vars/vault
6. Convert search to dynamic inventory
7. Comprehensive validation
8. Staged deployment

**Timeline**: 1-2 weeks per cookbook

---

### Pattern 3: Enterprise Cookbook Suite (High Complexity)

**Characteristics:**
- 15+ recipes per cookbook
- 5+ custom resources
- Complex dependency chains
- Heavy data bag and search usage
- Multiple environments
- Requires AWX/AAP integration

**Recommended Approach:**
1. Detailed assessment with executive reporting
2. Create comprehensive migration plan
3. Pilot conversion with simple dependencies first
4. Incremental conversion by component
5. Build custom Ansible modules for complex resources
6. Implement dynamic inventory for search
7. Generate AWX project structure
8. Extensive testing including performance
9. Blue/green deployment to production

**Timeline**: 2-6 weeks per cookbook

---

### Pattern 4: Habitat to Container Migration

**Characteristics:**
- Habitat plan files (plan.sh)
- Service orchestration
- Multi-package dependencies
- Supervisor configuration

**Recommended Approach:**
1. Parse Habitat plans with `parse_habitat_plan`
2. Convert to Dockerfiles with `convert_habitat_to_dockerfile`
3. Generate docker-compose with `generate_compose_from_habitat`
4. Implement health checks and service dependencies
5. Migrate supervisor config to container orchestration
6. Deploy to Kubernetes/OpenShift (if applicable)

**Timeline**: 1-3 weeks per application

---

## Best Practices

### Do's ✅

1. **Start with Assessment**
   - Always run `assess_chef_migration_complexity` first
   - Document findings before conversion

2. **Follow Dependency Order**
   - Use `analyze_cookbook_dependencies` to determine migration sequence
   - Migrate dependency cookbooks before dependent cookbooks

3. **Validate Continuously**
   - Run `validate_conversion` after each conversion
   - Test in dev environment before moving to staging

4. **Use Version Control**
   - Commit Ansible content to Git immediately
   - Tag milestones and working versions

5. **Document Decisions**
   - Record why certain conversions were done manually
   - Document workarounds and limitations

6. **Test Idempotency**
   - Run playbooks multiple times to verify idempotency
   - Compare first run vs subsequent runs

7. **Profile Performance**
   - Use `profile_cookbook_performance` for large cookbooks
   - Identify and optimise bottlenecks

8. **Leverage InSpec**
   - Convert existing InSpec tests with `convert_inspec_to_test`
   - Generate new tests with `generate_inspec_from_recipe`

### Don'ts ❌

1. **Don't Skip Assessment**
   - Jumping directly to conversion often leads to rework
   - Understanding complexity upfront prevents surprises

2. **Don't Migrate Out of Order**
   - Migrating dependent cookbooks before dependencies causes failures
   - Always follow the dependency graph

3. **Don't Ignore Validation Errors**
   - Validation warnings often indicate real issues
   - Fix errors before proceeding to next cookbook

4. **Don't Convert Everything**
   - Some Chef patterns may not need direct conversion
   - Consider modernizing during migration (e.g., Habitat → containers)

5. **Don't Rush Production**
   - Thorough testing in dev/staging prevents production issues
   - Parallel runs provide confidence before cutover

6. **Don't Lose Chef Knowledge**
   - Document Chef-specific patterns for reference
   - Retain Chef expertise during transition period

7. **Don't Forget Security**
   - Encrypt sensitive data with Ansible Vault
   - Validate privilege escalation patterns
   - Audit converted playbooks for security issues

8. **Don't Work in Isolation**
   - Involve operations teams early
   - Share migration progress and learnings

---

## Success Metrics

Track these metrics to measure migration success:

### Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Conversion accuracy | > 95% | Automated validation pass rate |
| Idempotency | 100% | Repeat execution identical |
| Performance | ± 10% of Chef | Execution time comparison |
| Test coverage | > 90% | Tasks with validation tests |
| Migration velocity | Planned timeline ± 15% | Actual vs planned schedule |

### Qualitative Metrics

- **Team Confidence**: Operations team comfortable with Ansible
- **Documentation Quality**: Comprehensive and accessible
- **Rollback Readiness**: Clear procedures tested
- **Knowledge Transfer**: Team trained on Ansible patterns
- **Stakeholder Satisfaction**: Business needs met

---

## Common Challenges & Solutions

### Challenge: Complex Chef Guards

**Problem**: Chef guards with Ruby blocks don't convert cleanly

**Solution**:
- Use SousChef's enhanced guard handling
- For complex guards, convert to Ansible facts and conditions
- Example:
  ```ruby
  # Chef
  only_if { ::File.exist?('/path') && node['attr'] == 'value' }

  # Ansible
  when:
    - path_check.stat.exists
    - ansible_local.attr == 'value'
  ```

### Challenge: Custom Resource Complexity

**Problem**: Complex custom resources have no Ansible equivalent

**Solution**:
- Convert simple resources to roles
- Build custom Ansible modules for complex logic
- Use `parse_custom_resource` to understand interface
- Preserve behaviour, not implementation

### Challenge: Chef Search Patterns

**Problem**: Sophisticated search queries hard to replicate

**Solution**:
- Use `convert_chef_search_to_inventory` for patterns
- Implement dynamic inventory scripts
- Consider AWS/Azure dynamic inventory if cloud-based
- Cache inventory for performance

### Challenge: Data Bag Encryption

**Problem**: Chef encrypted data bags use different encryption

**Solution**:
- Use `generate_ansible_vault_from_databags`
- Decrypt Chef data bags, re-encrypt with Ansible Vault
- Update key management procedures
- Test encrypted variable access thoroughly

### Challenge: Environment-Specific Logic

**Problem**: Chef environments affect attribute precedence

**Solution**:
- Convert to inventory group_vars structure
- Use `convert_chef_environment_to_inventory_group`
- Leverage Ansible's variable precedence (group_vars, host_vars)
- Document variable precedence mapping

---

## Migration Checklist

Use this checklist to track progress through migration phases:

### Pre-Migration
- [ ] Inventory all Chef cookbooks
- [ ] Document dependencies
- [ ] Identify Habitat plans (if any)
- [ ] Catalog data bags and environments
- [ ] Establish baseline metrics (performance, reliability)

### Assessment Phase
- [ ] Run complexity assessment for each cookbook
- [ ] Generate dependency graph
- [ ] Create migration plan with timeline
- [ ] Identify risks and mitigation strategies
- [ ] Allocate resources (people, environments)
- [ ] Define success criteria

### Conversion Phase
- [ ] Set up Git repository for Ansible content
- [ ] Convert cookbooks in dependency order
- [ ] Transform custom resources
- [ ] Migrate data bags to variables/vault
- [ ] Convert environments to inventory
- [ ] Generate AWX configurations (if applicable)
- [ ] Convert Habitat to containers (if applicable)

### Validation Phase
- [ ] Validate syntax for all converted content
- [ ] Test in development environment
- [ ] Generate and execute InSpec tests
- [ ] Verify idempotency
- [ ] Perform security audit
- [ ] Benchmark performance
- [ ] Document any workarounds

### Deployment Phase
- [ ] Deploy to staging environment
- [ ] Execute parallel Chef/Ansible runs
- [ ] Validate results match Chef
- [ ] Test rollback procedures
- [ ] Deploy to production (blue/green or canary)
- [ ] Monitor post-deployment
- [ ] Decommission Chef infrastructure
- [ ] Document lessons learned

---

## Next Steps

Now that you understand the overall migration methodology:

1. **[Assessment](assessment.md)** - Learn how to assess cookbook complexity and create migration plans
2. **[Conversion](conversion.md)** - Dive deep into conversion techniques and patterns
3. **[Deployment](deployment.md)** - Master deployment strategies and AWX/AAP integration

Or explore specific topics:

- [MCP Tools Reference](../user-guide/mcp-tools.md) - All 38 available tools
- [CLI Usage](../user-guide/cli-usage.md) - Command-line workflow
- [Examples](../user-guide/examples.md) - Real-world migration patterns

---

## Additional Resources

- **SousChef Documentation**: Full tool reference and examples
- **Ansible Best Practices**: [docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)
- **AWX Documentation**: [ansible.readthedocs.io/projects/awx/](https://ansible.readthedocs.io/projects/awx/)
- **InSpec Documentation**: [docs.chef.io/inspec/](https://docs.chef.io/inspec/)

!!! success "Ready to Migrate?"
    With SousChef's 38 tools and this methodology, you have everything needed for a successful Chef-to-Ansible migration. Start with assessment, follow the phases, and leverage automation throughout the process.
