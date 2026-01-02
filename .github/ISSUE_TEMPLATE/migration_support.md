---
name: Migration Support Request
about: Get help with a specific Chef-to-Ansible migration project
title: '[MIGRATION] '
labels: ['migration-support', 'help-wanted']
assignees: ''

---

## 🚚 Migration Overview

**Brief Description**: What Chef infrastructure are you migrating?

**Migration Scale**:
- [ ] Single cookbook (< 10 recipes)
- [ ] Multiple cookbooks (10-50 recipes)
- [ ] Large infrastructure (50+ recipes)
- [ ] Enterprise-wide migration

**Timeline**: When do you need this migration completed?

## 🍳 Chef Environment

### Current Chef Setup
**Chef Version**: [e.g., 17.10.0]
**Chef Server/Solo/Zero**: [Which Chef deployment model?]
**Node Count**: [How many nodes are managed?]
**Operating Systems**: [Ubuntu 20.04, CentOS 7, Windows Server 2019, etc.]

### Cookbook Information
**Primary Cookbooks**:
```
# List your main cookbooks and their purposes
my-app-cookbook/          # Web application deployment
database-cookbook/        # MySQL/PostgreSQL management
monitoring-cookbook/      # Nagios/Prometheus setup
```

**Cookbook Dependencies**:
- Community cookbooks used: [e.g., nginx, mysql, java]
- Custom/wrapper cookbooks: [list them]
- Complex dependency chains: [describe any complex relationships]

### Chef Patterns Used
Which Chef patterns does your infrastructure use? (check all that apply)

- [ ] **Basic Resources** - packages, services, files, templates
- [ ] **Custom Resources/LWRPs** - custom resource definitions
- [ ] **Chef Search** - search for nodes, data bags, environments
- [ ] **Data Bags** - encrypted or plain data bags
- [ ] **Environments** - environment-specific configuration
- [ ] **Roles** - node roles and run lists
- [ ] **Custom Ohai Plugins** - custom system information gathering
- [ ] **Chef Handlers** - custom error/report handlers
- [ ] **Berkshelf/Policyfiles** - dependency management
- [ ] **Test Kitchen** - cookbook testing
- [ ] **InSpec** - compliance and testing
- [ ] **Application Cookbooks** - deploy resources, git checkouts

## 🎭 Target Ansible Environment

### Ansible Setup Goals
**Ansible Version**: [target version, e.g., 2.15+]
**Deployment Model**:
- [ ] Ansible Core (command line)
- [ ] AWX (open source)
- [ ] Ansible Automation Platform (Red Hat)
- [ ] Other: _______________

**Inventory Management**:
- [ ] Static inventory files
- [ ] Dynamic inventory (cloud, CMDB)
- [ ] AWX/AAP inventory sources
- [ ] Other: _______________

### Target Architecture
**Playbook Organization**:
- [ ] Single playbook per cookbook
- [ ] Role-based organization
- [ ] Collection-based organization
- [ ] Custom structure: _______________

**Variable Management**:
- [ ] Group vars / host vars
- [ ] Ansible Vault
- [ ] External variable sources
- [ ] AWX/AAP credentials

## 🔧 SousChef Usage

### What You've Tried
- [ ] Used CLI to analyze cookbooks: `souschef-cli structure /path/to/cookbook`
- [ ] Converted individual recipes: `souschef-cli recipe recipe.rb`
- [ ] Analyzed search patterns: MCP tool analysis
- [ ] Generated migration reports: used reporting tools
- [ ] Other: _______________

### Current Results
**What's Working Well**:
```
# Describe successful conversions or analyses
Basic package resources convert cleanly
Template parsing works for most ERB files
```

**Current Challenges**:
```
# What isn't working or needs help?
Custom resources not converting properly
Complex search queries need manual review
Data bag encryption needs strategy
```

### Specific SousChef Questions
- Are there Chef patterns SousChef doesn't handle well for your use case?
- Do you need help with specific MCP tools or CLI commands?
- Are there conversion results that need manual refinement?

## 🚧 Migration Challenges

### Technical Challenges
What specific technical challenges do you face?

- [ ] **Custom Resources** - complex LWRP/custom resource logic
- [ ] **Search Complexity** - complex Chef search patterns
- [ ] **Data Management** - data bags, attributes, encrypted data
- [ ] **Testing Strategy** - converting InSpec tests, kitchen tests
- [ ] **Deployment Patterns** - application deployment workflows
- [ ] **Infrastructure Complexity** - multi-tier applications
- [ ] **Performance** - large cookbook/recipe processing
- [ ] **Integration** - CI/CD, monitoring, logging integration

### Organizational Challenges
- [ ] **Team Training** - Ansible learning curve
- [ ] **Approval Process** - getting stakeholder buy-in
- [ ] **Downtime Windows** - coordinating migration timing
- [ ] **Documentation** - updating operational procedures
- [ ] **Tool Integration** - adapting existing toolchain

## 📊 Sample Code/Configuration

### Representative Chef Code
Please provide a sample of your Chef code that represents the complexity:

```ruby
# Paste a representative recipe or custom resource
# This helps us understand your specific patterns

application 'my-web-app' do
  path '/opt/myapp'
  repository 'https://github.com/company/myapp.git'
  revision node['myapp']['version']

  rails do
    database_master_role 'database_master'
    database_slave_role 'database_slave'
  end

  passenger_apache2 do
    server_aliases node['myapp']['server_aliases']
    docroot '/opt/myapp/public'
  end
end
```

### Desired Ansible Output
If you have ideas about how this should look in Ansible:

```yaml
# Your vision for the Ansible equivalent
- name: Deploy my-web-app
  git:
    repo: https://github.com/company/myapp.git
    dest: /opt/myapp
    version: "{{ myapp_version }}"
# ... additional tasks
```

## 🎯 Success Criteria

What would make this migration successful for you?

**Functional Requirements**:
- [ ] All current functionality preserved
- [ ] Performance equivalent or better
- [ ] Security posture maintained
- [ ] Monitoring/alerting continues working

**Operational Requirements**:
- [ ] Team can operate the new system
- [ ] Documentation is complete
- [ ] CI/CD pipelines work
- [ ] Rollback plan exists

**Timeline Goals**:
- Development environment: [when?]
- Staging environment: [when?]
- Production migration: [when?]

## 🤝 Support Needed

What kind of help would be most valuable?

- [ ] **SousChef Tool Guidance** - how to use specific tools effectively
- [ ] **Conversion Review** - review of generated Ansible code
- [ ] **Best Practices** - Ansible patterns and organization advice
- [ ] **Custom Development** - new SousChef features for your use case
- [ ] **Migration Strategy** - overall approach and planning
- [ ] **Training/Documentation** - team enablement resources

**Time Commitment Available**:
- [ ] Occasional questions and reviews
- [ ] Regular collaboration sessions
- [ ] Intensive migration project support

## 📞 Contact Preferences

How would you prefer to collaborate?

- [ ] GitHub issues and comments
- [ ] Email discussions
- [ ] Video calls/screen sharing
- [ ] Documentation and async review

## ☑️ Checklist

- [ ] I have described my Chef environment comprehensively
- [ ] I have outlined my Ansible goals and constraints
- [ ] I have provided representative code samples
- [ ] I have tried SousChef tools relevant to my use case
- [ ] I have specified what kind of support would be most helpful

---

**Note**: Migration support is provided on a best-effort basis by the community. For direct assistance, you can contact the maintainer at krpeacocke@gmail.com. Complex enterprise migrations may benefit from professional services or consulting.
