#!/usr/bin/env bash
# Script to create GitHub issues from technical debt inventory
# Usage: ./create-tech-debt-issues.sh
#
# Compatible with bash 3.2+ (macOS default)

set -e

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

echo "Creating technical debt issues..."

# Function Complexity Issues - sorted by complexity (highest first)
# Format: "function_name|complexity|line_number"
functions=(
    "_convert_resource_to_task_dict|17|2141"
    "parse_inspec_profile|17|3001"
    "_generate_inspec_from_resource|16|2925"
    "_generate_playbook_structure|15|1915"
    "_convert_inspec_to_testinfra|15|2806"
    "generate_inspec_from_recipe|15|3123"
    "_parse_inspec_control|14|2638"
    "_convert_inspec_to_ansible_assert|14|2876"
    "_generate_inventory_recommendations|13|1840"
    "_extract_inspec_describe_blocks|13|2718"
    "_parse_chef_search_query|12|1301"
    "_extract_recipe_variables|12|2028"
    "_extract_chef_guards|12|2364"
    "_generate_ansible_inventory_from_search|11|1427"
    "_extract_code_block_variables|11|192"
)

for entry in "${functions[@]}"; do
    IFS='|' read -r func complexity line <<< "$entry"

    echo "Creating issue for $func (complexity: $complexity)..."

    gh issue create \
        --title "[Tech Debt] Refactor $func to reduce complexity" \
        --label "technical-debt,refactoring,priority:medium" \
        --milestone "v2.0.0" \
        --body "## Current State

- **Function**: \`$func\`
- **Location**: \`souschef/server.py:$line\`
- **Complexity**: $complexity (threshold: 10)
- **Suppression**: \`# noqa: C901\`

## Why Does This Exist?

This function handles complex Chef-to-Ansible conversion logic with multiple edge cases and resource type mappings. The complexity is inherent to the comprehensive feature set.

## Impact

- Hard to understand and modify
- Difficult to test individual code paths
- Increases cognitive load for contributors

## Proposed Solution(s)

**Option 1: Extract Smaller Functions**
- Break into focused sub-functions (each < 10 complexity)
- Improve naming to clarify purpose
- Easier to test and maintain

**Option 2: Strategy Pattern**
- Create strategy objects for different cases
- Register strategies in a map
- Cleaner separation of concerns

**Option 3: State Machine**
- For parsing functions, use explicit state machine
- Clearer flow control
- Easier to extend

## Acceptance Criteria

- [ ] Complexity metric < 10 (or documented justification if not feasible)
- [ ] All existing tests pass
- [ ] New tests added for extracted functions
- [ ] No behavior changes
- [ ] Code review approved
- [ ] Documentation updated if needed

## References

- See \`TECHNICAL_DEBT.md\` for full context
- Related functions may have similar complexity issues" || echo "  Failed (may already exist)"

    sleep 1  # Rate limiting
done

echo ""
echo "✅ Technical debt issues created!"
echo ""
echo "View all tech debt: gh issue list --label technical-debt"
echo "Create project board: gh project create --title 'Technical Debt' --owner kpeacocke"
