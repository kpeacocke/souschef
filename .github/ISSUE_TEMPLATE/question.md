---
name: Question / Help
about: Ask a question or get help using SousChef
title: '[QUESTION] '
labels: ['question', 'help-wanted']
assignees: ''

---

## Question

What would you like help with? Please be as specific as possible.

## Context

**What are you trying to do?**
- [ ] Convert a specific Chef cookbook to Ansible
- [ ] Understand how a particular Chef construct maps to Ansible
- [ ] Set up SousChef in my environment
- [ ] Integrate SousChef with other tools
- [ ] Use SousChef CLI for a specific task
- [ ] Use SousChef as an MCP server
- [ ] Other: _______________

**Chef/Ansible Experience Level:**
- [ ] New to both Chef and Ansible
- [ ] Experienced with Chef, new to Ansible
- [ ] Experienced with Ansible, new to Chef
- [ ] Experienced with both

## Details

### Chef Information (if applicable)
**Chef Version**: [e.g., 17.x, 18.x]
**Cookbook Structure**:
```
# Describe your cookbook structure or paste relevant files
cookbooks/
  my-cookbook/
    recipes/
      default.rb
    attributes/
      default.rb
```

**Specific Chef Code**:
```ruby
# Paste the Chef code you're working with
service 'apache2' do
  action [:enable, :start]
end
```

### What You've Tried
- [ ] Read the README and documentation
- [ ] Tried the CLI: `souschef-cli ...`
- [ ] Used MCP tools: `...`
- [ ] Searched existing issues
- [ ] Consulted Chef/Ansible documentation

**Commands you've run**:
```bash
# Paste commands and their output
souschef-cli recipe my-recipe.rb
```

**Current results**:
```
# What output are you getting?
```

## Expected Outcome

What result are you hoping to achieve?

**For conversion questions**:
```yaml
# What Ansible output are you expecting?
- name: Example task
  service:
    name: apache2
    state: started
    enabled: yes
```

## Environment

- **SousChef Version**: [e.g., 0.1.0]
- **Python Version**: [e.g., 3.14.1]
- **Operating System**: [e.g., Ubuntu 22.04]
- **Installation Method**: [e.g., poetry, pip]

## Additional Resources

Are there specific resources you've consulted?

- [ ] [SousChef README](../README.md)
- [ ] [Contributing Guide](../CONTRIBUTING.md)
- [ ] Chef documentation: [link]
- [ ] Ansible documentation: [link]
- [ ] Other: _______________

## Checklist

- [ ] I have searched existing issues and discussions
- [ ] I have provided enough context about what I'm trying to do
- [ ] I have included relevant code examples
- [ ] I have specified my environment and SousChef version
- [ ] I have described what I've already tried

---

**Note**: This is for usage questions and help. For bugs, please use the bug report template. For new features, use the feature request template.
