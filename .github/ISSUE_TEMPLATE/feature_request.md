---
name: Feature Request
about: Suggest a new feature for SousChef
title: '[FEATURE] '
labels: ['enhancement', 'needs-triage']
assignees: ''

---

## Feature Description

A clear and concise description of the feature you'd like to see added.

## Problem Statement

What problem does this feature solve? Is your feature request related to a problem?

**Example**: "I'm always frustrated when trying to convert Chef [specific resource/pattern] because..."

## Proposed Solution

Describe the solution you'd like:

- What should the new feature do?
- How should it work?
- What would the interface look like?

**For MCP Tools**:
```python
# Example of how the new tool might work
@mcp.tool()
def new_tool_name(parameter: str) -> str:
    """Description of what this tool would do."""
    pass
```

**For CLI Commands**:
```bash
# Example of proposed CLI usage
souschef-cli new-command input.rb --option value
```

## Use Cases

Describe specific use cases where this feature would be helpful:

1. **Use Case 1**: Converting cookbooks that use [specific pattern]
2. **Use Case 2**: Migrating from [specific Chef setup] to Ansible
3. **Use Case 3**: Handling [specific migration scenario]

## Chef Context

If this relates to Chef functionality:

- **Chef Resource/Pattern**: What Chef construct needs better support?
- **Chef Version**: Any specific Chef version requirements?
- **Common Usage**: How is this typically used in Chef cookbooks?

**Example Chef code this would help with**:
```ruby
# Paste relevant Chef code here
custom_resource 'my_app' do
  property :version, String, required: true
  action :deploy
end
```

## Ansible Context

If this relates to Ansible conversion:

- **Target Ansible Module**: What Ansible module(s) should this map to?
- **Ansible Best Practice**: How should this be implemented in Ansible?
- **Playbook Structure**: How should this appear in generated playbooks?

**Expected Ansible output**:
```yaml
# What the converted Ansible code should look like
- name: Deploy my_app
  my_app_module:
    version: "{{ app_version }}"
    state: present
```

## Alternative Solutions

Describe alternatives you've considered:

- Workarounds you're currently using
- Other tools or approaches
- Manual conversion steps

## Feature Category

What type of feature is this? (check all that apply)

- [ ] **New MCP Tool** - Add a new tool to the MCP server
- [ ] **CLI Enhancement** - Improve or add CLI commands
- [ ] **Parser Improvement** - Better parsing of Chef constructs
- [ ] **Conversion Logic** - New Chef-to-Ansible mappings
- [ ] **Migration Workflow** - Migration planning and reporting
- [ ] **Testing/InSpec** - Testing and validation features
- [ ] **AWX/AAP Integration** - Ansible Automation Platform features
- [ ] **Documentation** - Improve docs or examples
- [ ] **Performance** - Speed or efficiency improvements
- [ ] **Other** - Please specify

## Priority/Impact

- **Priority**: How important is this feature to you? (Low/Medium/High)
- **Impact**: How many users would benefit from this? (Few/Some/Many)
- **Complexity**: How complex do you think this would be to implement? (Simple/Medium/Complex)

## Related Issues/Discussions

Link any related issues or discussions:

- Related to issue #XXX
- Discussed in #XXX
- Similar to #XXX

## Additional Context

Add any other context, screenshots, examples, or references:

- Links to Chef documentation
- Examples from other migration tools
- Community discussions or blog posts
- Screenshots or diagrams

## ☑️ Checklist

- [ ] I have searched existing issues and feature requests
- [ ] I have clearly described the problem this feature solves
- [ ] I have provided concrete examples and use cases
- [ ] I have considered how this fits with existing SousChef functionality
- [ ] I have thought about the user experience and interface design

---

**Thank you for helping improve SousChef!** 🙏

Feature requests help us understand what the community needs most. Even if you can't implement it yourself, your idea might inspire someone else to contribute!
